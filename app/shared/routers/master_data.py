import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.shared.models.master_data import Department, DepartmentJob
from typing import List
from pydantic import BaseModel

router = APIRouter(prefix="/master", tags=["Master Data"])

class DepartmentOut(BaseModel):
    id: str
    name: str
    # name_hi: str | None = None
    # name_pa: str | None = None

    class Config:
        from_attributes = True

class DepartmentJobOut(BaseModel):
    id: str
    name: str
    # name_hi: str | None = None
    # name_pa: str | None = None
    department_id: str

    class Config:
        from_attributes = True

@router.get("/departments", response_model=List[DepartmentOut])
async def get_departments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department))
    return result.scalars().all()

@router.get("/departments/{dept_id}/jobs", response_model=List[DepartmentJobOut])
async def get_jobs_by_department(dept_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(DepartmentJob).filter(DepartmentJob.department_id == dept_id))
    return result.scalars().all()

# @router.post("/seed", status_code=status.HTTP_201_CREATED)
# async def seed_master_data(db: AsyncSession = Depends(get_db)):
#     """
#     Initial seed data based on the provided design.
#     """
#     data = {
#         "Custom Development": [
#             "MERN Full Stack Developer", "Python Developer", "Mobile App Developer", 
#             "Java Developer", "PHP Developer", "Node.js Developer", "React Native Developer"
#         ],
#         "Designing Team": [
#             "UI/UX Designer", "Graphic Designer", "Web Designer", 
#             "Motion Graphics Artist", "Product Designer"
#         ],
#         "Sales Team": [
#             "Business Development Manager", "Sales Executive", "Account Manager", 
#             "Inside Sales Specialist", "Pre-Sales Engineer"
#         ],
#         "HR Administration": [
#             "HR Manager", "Talent Acquisition Specialist", "Admin Executive", 
#             "Office Coordinator", "Employee Relations Specialist"
#         ],
#         "QA Team": [
#             "QA Engineer", "Automation Tester", "Manual Tester", 
#             "Performance Tester", "Security Analyst"
#         ],
#         "Digital Marketing": [
#             "SEO Specialist", "Content Writer", "Social Media Manager", 
#             "PPC Expert", "Digital Marketing Executive", "Email Marketer"
#         ],
#         "Operations": [
#             "Operations Manager", "Project Coordinator", "Data Entry Operator", 
#             "Logistics Coordinator", "Supply Chain Analyst"
#         ],
#         "Technical Support": [
#             "Customer Support Executive", "Technical Support Engineer", 
#             "IT Support Specialist", "Desktop Support Engineer"
#         ],
#         "Management": [
#             "Product Manager", "Team Lead", "Delivery Manager", 
#             "Scrum Master", "Business Analyst"
#         ]
#     }
    
#     for dept_name, job_names in data.items():
#         # Check if department exists
#         result = await db.execute(select(Department).filter(Department.name == dept_name))
#         dept = result.scalar_one_or_none()
#         if not dept:
#             dept = Department(id=str(uuid.uuid4()), name=dept_name)
#             db.add(dept)
#             await db.flush()
        
#         for job_name in job_names:
#             # Check if job exists in this department
#             result = await db.execute(select(DepartmentJob).filter(
#                 DepartmentJob.name == job_name, 
#                 DepartmentJob.department_id == dept.id
#             ))
#             job = result.scalar_one_or_none()
#             if not job:
#                 job = DepartmentJob(id=str(uuid.uuid4()), name=job_name, department_id=dept.id)
#                 db.add(job)
    
#     await db.commit()
#     return {"message": "Master data seeded successfully"}
