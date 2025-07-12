
from fastapi import FastAPI, File, UploadFile, Depends, HTTPException,Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from resume_screening_core import analyze_resume
from database import get_db, init_db
from schemas import ResumeLogCreate, EmailRequest
from crud import save_resume_log, get_all_logs, delete_log_by_email
from models import ResumeLog
import shutil, os, tempfile, smtplib, datetime
from email.mime.text import MIMEText
import datetime
import tempfile
import shutil
import os
from fastapi import UploadFile, File, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models import ResumeLog
from resume_screening_core import analyze_resume
from database import get_db


from models import Job
from schemas import JobOut

from sqlalchemy import select
from datetime import datetime
from schemas import JobCreate
from models import Job

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup():
    await init_db()

from dotenv import load_dotenv
import os
load_dotenv() 

@app.post("/screen")
async def screen_resume(file: UploadFile = File(...), job_id: int = Form(None), db: AsyncSession = Depends(get_db)):
    try:
        # Save the uploaded resume temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix="." + file.filename.split('.')[-1]) as tmp:
            shutil.copyfileobj(file.file, tmp)
            tmp_path = tmp.name

        # Analyze the resume
        result = analyze_resume(tmp_path)
        print("🧠 Analyzed result:", result)  # Debug log

        # Save the uploaded resume permanently
        email = result.get("email", "unknown")
        extension = os.path.splitext(file.filename)[1]
        safe_email = email.replace("/", "_").replace("\\", "_")
        os.makedirs("uploaded_resumes", exist_ok=True)
        saved_path = os.path.join("uploaded_resumes", f"{safe_email}{extension}")
        shutil.copyfile(tmp_path, saved_path)

        # Cleanup temp file
        os.unlink(tmp_path)

        # Store log in database
        new_log = ResumeLog(
            name=result.get("name"),
            email=email,
            role=result.get("best_role"),
            experience_level=result.get("level"),
            # experience_years=result.get("experience_years", 0),
            final_score=result.get("final_score", 0),
            status=result.get("status", "Unknown"),
            timestamp=datetime.utcnow(),
            job_id=job_id 
        )
        db.add(new_log)
        await db.commit()

        return result

    except Exception as e:
        import traceback
        traceback.print_exc()  # Log full error to console
        raise HTTPException(status_code=500, detail=f"Resume screening failed: {str(e)}")





@app.post("/send-email")
async def send_email(req: EmailRequest):
    sender_email = os.getenv("SENDER_EMAIL")
    sender_password = os.getenv("SENDER_PASSWORD")

    if req.status.lower() == "accepted":
        body = f"""
Dear {req.name},

Thank you for applying to the {req.best_role} position at Empowerverse.

You have been shortlisted for the next stage of our recruitment process. We’ll contact you soon!

Warm regards,  
HR Team  
Empowerverse
"""
    else:
        body = f"""
Dear {req.name},

Thank you for your interest in the {req.best_role} position at Empowerverse.

We regret to inform you that we will not be moving forward with your application at this time.

We wish you all the best in your job search.

Sincerely,  
HR Team  
Empowerverse
"""

    msg = MIMEText(body)
    msg["Subject"] = "Internship Application Status"
    msg["From"] = sender_email
    msg["To"] = req.email

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, req.email, msg.as_string())
        return {"message": "Email sent"}
    except Exception as e:
        return {"error": str(e)}

@app.get("/resumes/{email}")
def view_resume(email: str):
    folder = "uploaded_resumes"
    safe_email = email.replace("/", "_").replace("\\", "_")
    for ext in [".pdf", ".docx"]:
        resume_path = os.path.join(folder, f"{safe_email}{ext}")
        if os.path.exists(resume_path):
            media_type = "application/pdf" if ext == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            return FileResponse(path=resume_path, media_type=media_type, filename=f"{safe_email}{ext}")
    raise HTTPException(status_code=404, detail="Resume not found.")

# @app.get("/logs")
# async def get_logs(db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(ResumeLog))
#     logs = result.scalars().all()
#     return [log.__dict__ for log in logs]

from sqlalchemy.orm import joinedload
from models import ResumeLog

@app.get("/logs")
async def get_logs(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ResumeLog).options(joinedload(ResumeLog.job))  # ✅ load related job
    )
    logs = result.scalars().all()

    response = []
    for log in logs:
        response.append({
            "name": log.name,
            "email": log.email,
            "role": log.role,
            "experience_level": log.experience_level,
            "final_score": log.final_score,
            "status": log.status,
            "timestamp": log.timestamp,
            "job_title": log.job.title if log.job else "—",  # ✅ this is what your frontend needs
        })

    return response



@app.delete("/logs/{email}")
async def delete_log(email: str, db: AsyncSession = Depends(get_db)):
    safe_email = email.replace("/", "_").replace("\\", "_")
    result = await db.execute(select(ResumeLog).where(ResumeLog.email == email))
    log = result.scalars().first()
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")
    await db.delete(log)
    await db.commit()
    for ext in [".pdf", ".docx"]:
        path = os.path.join("uploaded_resumes", f"{safe_email}{ext}")
        if os.path.exists(path):
            os.remove(path)
    return {"message": "Log and resume deleted successfully"}




# @app.get("/jobs", response_model=list[JobOut])
# async def get_active_jobs(db: AsyncSession = Depends(get_db)):
#     result = await db.execute(select(Job).where(Job.deadline > datetime.utcnow()))
#     jobs = result.scalars().all()
#     return jobs
@app.get("/jobs", response_model=list[JobOut])
async def get_active_jobs(db: AsyncSession = Depends(get_db)):
    now = datetime.utcnow()
    print("🕒 Current UTC time:", now)

    result = await db.execute(select(Job).where(Job.deadline > now))
    jobs = result.scalars().all()
    print("📋 Jobs returned to frontend:", jobs)
    return jobs


@app.post("/jobs")
async def create_job(job: JobCreate, db: AsyncSession = Depends(get_db)):
    new_job = Job(**job.dict())
    db.add(new_job)
    await db.commit()
    return {"message": "Job created successfully"}

@app.delete("/jobs/{job_id}")
async def delete_job(job_id: int, db: AsyncSession = Depends(get_db)):
    job = await db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    await db.delete(job)
    await db.commit()
    return {"message": "Job deleted"}



if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)