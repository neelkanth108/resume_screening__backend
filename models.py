
from sqlalchemy import Column, Integer, String, Float, DateTime,ForeignKey
from database import Base  # ✅ Use Base from your database.py
from datetime import datetime
from sqlalchemy import Date  # at the top
from sqlalchemy.orm import relationship

class ResumeLog(Base):
    __tablename__ = "resume_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, index=True)
    role = Column(String, nullable=True)
    experience_level = Column(String, nullable=True)
    final_score = Column(Float, nullable=True)
    status = Column(String, nullable=True)

    job_id = Column(Integer, ForeignKey("jobs.id"))
    job = relationship("Job", backref="resumes")
    # experience_years = Column(Float, nullable=True)  # Re-enable if needed

from sqlalchemy import Column, Integer, String, DateTime
from database import Base
import datetime

class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    department = Column(String)
    location = Column(String)
    deadline = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)







