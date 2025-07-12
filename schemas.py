# schemas.py
from pydantic import BaseModel
from typing import Optional

class ResumeLogCreate(BaseModel):
    name: Optional[str]
    email: str
    role: Optional[str]
    level: Optional[str]
    # experience_years: Optional[float]
    final_score: Optional[float]
    status: Optional[str]

class EmailRequest(BaseModel):
    email: str
    name: str
    status: str
    best_role: str
    score: float


from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class JobOut(BaseModel):
    id: int
    title: str
    description: Optional[str]
    department: Optional[str]
    location: Optional[str]
    deadline: datetime

    class Config:
        orm_mode = True

class JobCreate(BaseModel):
    title: str
    description: Optional[str]
    department: Optional[str]
    location: Optional[str]
    deadline: datetime


