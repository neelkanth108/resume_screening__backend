import pdfplumber
import docx
import re
from sentence_transformers import SentenceTransformer, util
from pyresparser import ResumeParser
import nltk
import os
import csv
# import os
from datetime import datetime
# Download NLTK resources (run once)
# nltk.download('stopwords')
# nltk.download('punkt')
# nltk.download('wordnet')

# Load embedding model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Job roles and skill requirements
JOB_ROLES = {
    "Machine Learning Engineer": "Develop and deploy machine learning models using Python, TensorFlow, and PyTorch.",
    "Frontend Developer": "Create responsive websites using HTML, CSS, JavaScript and frameworks like React.",
    "Backend Developer": "Build scalable backend systems using Python, FastAPI, and SQL/NoSQL."
}

ROLE_SKILLS = {
    "Machine Learning Engineer": {"Python", "NumPy", "Pandas", "Scikit-learn", "TensorFlow", "PyTorch"},
    "Frontend Developer": {"HTML", "CSS", "JavaScript", "React.js", "UI/UX"},
    "Backend Developer": {"Python", "SQL", "MongoDB", "FastAPI", "Django"}
}

DYNAMIC_THRESHOLDS = {
    "Machine Learning Engineer": {"junior": 0.65, "mid": 0.75, "senior": 0.80},
    "Frontend Developer": {"junior": 0.60, "mid": 0.70, "senior": 0.75},
    "Backend Developer": {"junior": 0.65, "mid": 0.72, "senior": 0.78}
}

# Extract text from resume
def extract_text(file_path):
    if file_path.endswith(".pdf"):
        with pdfplumber.open(file_path) as pdf:
            return "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    elif file_path.endswith(".docx"):
        doc = docx.Document(file_path)
        return "\n".join([para.text for para in doc.paragraphs])
    else:
        return ""


# Extract email from text
def extract_email(text):
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group(0) if match else None

# Semantic similarity score between resume and job role
def compute_match_score(resume_text, job_text):
    embeddings = model.encode([resume_text, job_text], convert_to_tensor=True)
    similarity = util.pytorch_cos_sim(embeddings[0], embeddings[1])
    return similarity.item()

# Resume parsing
def parse_resume(file_path):
    try:
        return ResumeParser(file_path).get_extracted_data()
    except:
        return {}

# Adjust experience for internships or training
def adjust_experience(exp_years, text):
    try:
        exp_years = float(exp_years)
    except:
        exp_years = 0

    if exp_years == 0 and any(word in text.lower() for word in ["intern", "training", "club"]):
        exp_years = 0.5

    return exp_years

# Classify experience level
def get_experience_level(exp_years):
    if exp_years >= 3:
        return "senior"
    elif exp_years >= 1:
        return "mid"
    else:
        return "junior"



def log_result(name, email, role, level, final_score, status):
    file_exists = os.path.isfile("resume_screening_log.csv")
    with open("resume_screening_log.csv", mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow([
                "Timestamp", "Name", "Email", "Role","Level",
                "Final Score",  "Status"
            ])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            name, email, role, level, 
            round(final_score, 2),status
        ])


# Skill match scoring
def compute_skill_match(resume_skills, job_role):
    required = ROLE_SKILLS.get(job_role, set())
    matched = set(resume_skills or []) & required
    return len(matched) / len(required) if required else 0, list(matched)

def extract_skills_fallback(text):
    resume_words = set(re.findall(r'\b\w[\w+\.#]*\b', text.lower()))
    known_skills = set(
        skill.lower() for skills in ROLE_SKILLS.values() for skill in skills
    )
    found = [skill for skill in known_skills if skill.lower() in resume_words]
    return list(set(found))

# Main analysis pipeline
def analyze_resume(file_path):
    resume_text = extract_text(file_path)
    data = parse_resume(file_path)

    name = data.get("name")
    if not name or len(name.strip()) < 2:
        # Try to extract from the first few lines
        first_lines = resume_text.strip().splitlines()[:5]
        for line in first_lines:
            if line.strip() and len(line.split()) <= 4:
                name = line.strip()
                break
        if not name:
            name = "Candidate"

    # name = data.get("name", "Candidate")
    email = data.get("email") or extract_email(resume_text)
    skills = data.get("skills", [])
    if not skills: 
        skills = extract_skills_fallback(resume_text)

    raw_exp = data.get("total_experience", 0)
    exp_years = adjust_experience(raw_exp, resume_text)
    level = get_experience_level(exp_years)

    match_scores = {role: compute_match_score(resume_text, desc) for role, desc in JOB_ROLES.items()}
    best_role = max(match_scores, key=match_scores.get)
    sem_score = match_scores[best_role]
    skill_score, matched_skills = compute_skill_match(skills, best_role)

    final_score = 0.6 * sem_score + 0.4 * skill_score
    threshold = DYNAMIC_THRESHOLDS[best_role][level]
    status = "ACCEPTED" if final_score >= threshold else "REJECTED"
    log_result(name, email, best_role, level, final_score, status)

    return {
        "name": name,
        "email": email,
        "best_role": best_role,
        "experience_years": exp_years,
        "level": level,
        "semantic_score": round(sem_score, 2),
        "skill_score": round(skill_score, 2),
        "final_score": round(final_score, 2),
        "status": status,
        "matched_skills": matched_skills
    }
