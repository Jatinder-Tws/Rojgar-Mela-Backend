import sys
import os
import asyncio

# Add the current directory to sys.path so we can import local modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import AsyncSessionLocal
from models.master_data import Department, DepartmentJob
from sqlalchemy import select

async def seed():
    async with AsyncSessionLocal() as db:
        try:
            data = {
                "Custom Development": [
                    "MERN Full Stack Developer", "Python Developer", "Mobile App Developer", 
                    "Java Developer", "PHP Developer", "Node.js Developer", "React Native Developer"
                ],
                "Designing Team": [
                    "UI/UX Designer", "Graphic Designer", "Web Designer", 
                    "Motion Graphics Artist", "Product Designer"
                ],
                "Sales Team": [
                    "Business Development Manager", "Sales Executive", "Account Manager", 
                    "Inside Sales Specialist", "Pre-Sales Engineer"
                ],
                "HR Administration": [
                    "HR Manager", "Talent Acquisition Specialist", "Admin Executive", 
                    "Office Coordinator", "Employee Relations Specialist"
                ],
                "QA Team": [
                    "QA Engineer", "Automation Tester", "Manual Tester", 
                    "Performance Tester", "Security Analyst"
                ],
                "Digital Marketing": [
                    "SEO Specialist", "Content Writer", "Social Media Manager", 
                    "PPC Expert", "Digital Marketing Executive", "Email Marketer"
                ],
                "Operations": [
                    "Operations Manager", "Project Coordinator", "Data Entry Operator", 
                    "Logistics Coordinator", "Supply Chain Analyst"
                ],
                "Technical Support": [
                    "Customer Support Executive", "Technical Support Engineer", 
                    "IT Support Specialist", "Desktop Support Engineer"
                ],
                "Management": [
                    "Product Manager", "Team Lead", "Delivery Manager", 
                    "Scrum Master", "Business Analyst"
                ]
            }
            
            print("Starting async seed process...")
            
            for dept_name, job_names in data.items():
                # Check if department exists
                result = await db.execute(select(Department).filter(Department.name == dept_name))
                dept = result.scalars().first()
                
                if not dept:
                    dept = Department(name=dept_name)
                    db.add(dept)
                    await db.flush()
                    print(f"Added Department: {dept_name}")
                else:
                    print(f"Department exists: {dept_name}")
                
                for job_name in job_names:
                    # Check if job exists in this department
                    job_result = await db.execute(select(DepartmentJob).filter(
                        DepartmentJob.name == job_name, 
                        DepartmentJob.department_id == dept.id
                    ))
                    job = job_result.scalars().first()
                    
                    if not job:
                        job = DepartmentJob(name=job_name, department_id=dept.id)
                        db.add(job)
                        print(f"  - Added Job: {job_name}")
            
            await db.commit()
            print("\nSeed process completed successfully!")
            
        except Exception as e:
            print(f"\nError seeding data: {e}")
            await db.rollback()
        finally:
            await db.close()

if __name__ == "__main__":
    asyncio.run(seed())
