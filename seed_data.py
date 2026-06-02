"""
Seed script to populate the database with dummy data.
Run with: python seed_data.py
"""
import asyncio
import uuid
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from database import AsyncSessionLocal, engine, Base
from models.user import User, UserRole, JobType, CompanyType
from models.job import JobPosting
from models.resume import Resume
from services.auth_service import hash_password
import json

# Dummy data
SEEKERS_DATA = [
    {
        "first_name": "Amit",
        "last_name": "Kumar",
        "email": "amit.kumar@example.com",
        "phone": "9876543210",
        "password": "password123",
        "industry": "Technology",
        "job_role": "Software Engineer",
        "job_type": JobType.wfh,
        "salary_range": "8-12 LPA",
    },
    {
        "first_name": "Priya",
        "last_name": "Singh",
        "email": "priya.singh@example.com",
        "phone": "9876543211",
        "password": "password123",
        "industry": "Finance",
        "job_role": "Data Analyst",
        "job_type": JobType.hybrid,
        "salary_range": "6-10 LPA",
    },
    {
        "first_name": "Rajesh",
        "last_name": "Patel",
        "email": "rajesh.patel@example.com",
        "phone": "9876543212",
        "password": "password123",
        "industry": "Healthcare",
        "job_role": "Product Manager",
        "job_type": JobType.in_office,
        "salary_range": "10-15 LPA",
    },
    {
        "first_name": "Deepika",
        "last_name": "Sharma",
        "email": "deepika.sharma@example.com",
        "phone": "9876543213",
        "password": "password123",
        "industry": "E-commerce",
        "job_role": "UX Designer",
        "job_type": JobType.wfh,
        "salary_range": "7-11 LPA",
    },
    {
        "first_name": "Vikram",
        "last_name": "Desai",
        "email": "vikram.desai@example.com",
        "phone": "9876543214",
        "password": "password123",
        "industry": "Consulting",
        "job_role": "Senior Consultant",
        "job_type": JobType.hybrid,
        "salary_range": "12-18 LPA",
    }
]

RECRUITERS_DATA = [
    {
        "first_name": "Rohit",
        "last_name": "Verma",
        "email": "rohit.verma@techcorp.com",
        "phone": "8765432101",
        "password": "password123",
        "company_type": CompanyType.company,
        "company_name": "TechCorp Solutions",
    },
    {
        "first_name": "Neha",
        "last_name": "Gupta",
        "email": "neha.gupta@financeplus.com",
        "phone": "8765432102",
        "password": "password123",
        "company_type": CompanyType.company,
        "company_name": "FinancePlus Inc",
    },
    {
        "first_name": "Arjun",
        "last_name": "Malhotra",
        "email": "arjun.malhotra@healthtech.com",
        "phone": "8765432103",
        "password": "password123",
        "company_type": CompanyType.company,
        "company_name": "HealthTech Innovations",
    },
    {
        "first_name": "Sanjana",
        "last_name": "Rao",
        "email": "sanjana.rao@ecomm.com",
        "phone": "8765432104",
        "password": "password123",
        "company_type": CompanyType.company,
        "company_name": "ECommerce Global",
    },
    {
        "first_name": "Aditya",
        "last_name": "Nair",
        "email": "aditya.nair@consulting.com",
        "phone": "8765432105",
        "password": "password123",
        "company_type": CompanyType.company,
        "company_name": "Consulting Partners LLP",
    },
     {
        "first_name": "Vikram",
        "last_name": "Desai",
        "email": "vikram.desai@example.com",
        "phone": "9876543214",
        "password": "password123",
        "industry": "Consulting",
        "job_role": "Senior Consultant",
        "job_type": JobType.hybrid,
        "salary_range": "12-18 LPA",
    },
]

JOBS_DATA = [
    {
        "title": "Senior Software Engineer",
        "description": "We are looking for an experienced software engineer to lead our backend team.",
        "required_skills": ["Python", "FastAPI", "PostgreSQL", "AWS", "Docker"],
        "experience_required": "5+ years",
        "job_type": JobType.wfh,
        "salary_range": "15-25 LPA",
        "industry": "Technology",
    },
    {
        "title": "Full Stack Developer",
        "description": "Join our innovative team building next-gen web applications.",
        "required_skills": ["React", "Node.js", "MongoDB", "TypeScript", "REST APIs"],
        "experience_required": "3-4 years",
        "job_type": JobType.hybrid,
        "salary_range": "10-15 LPA",
        "industry": "Technology",
    },
    {
        "title": "Data Analyst",
        "description": "Analyze financial data and create insights for decision making.",
        "required_skills": ["SQL", "Python", "Tableau", "Excel", "Statistics"],
        "experience_required": "2-3 years",
        "job_type": JobType.in_office,
        "salary_range": "8-12 LPA",
        "industry": "Finance",
    },
    {
        "title": "Machine Learning Engineer",
        "description": "Build ML models for healthcare predictions.",
        "required_skills": ["Python", "TensorFlow", "Scikit-learn", "SQL", "AWS"],
        "experience_required": "4-5 years",
        "job_type": JobType.hybrid,
        "salary_range": "12-20 LPA",
        "industry": "Healthcare",
    },
    {
        "title": "UI/UX Designer",
        "description": "Design beautiful and intuitive interfaces for our mobile app.",
        "required_skills": ["Figma", "UI Design", "Prototyping", "User Research", "Wireframing"],
        "experience_required": "2-3 years",
        "job_type": JobType.wfh,
        "salary_range": "8-12 LPA",
        "industry": "E-commerce",
    },
    {
        "title": "Product Manager",
        "description": "Lead product strategy for our consulting platform.",
        "required_skills": ["Product Strategy", "Data Analysis", "User Research", "Leadership", "Roadmapping"],
        "experience_required": "4+ years",
        "job_type": JobType.hybrid,
        "salary_range": "12-18 LPA",
        "industry": "Consulting",
    },
    {
        "title": "DevOps Engineer",
        "description": "Manage infrastructure and deployment pipelines.",
        "required_skills": ["Kubernetes", "Docker", "CI/CD", "AWS", "Terraform"],
        "experience_required": "3-4 years",
        "job_type": JobType.wfh,
        "salary_range": "12-18 LPA",
        "industry": "Technology",
    },
    {
        "title": "Financial Analyst",
        "description": "Analyze market trends and provide investment recommendations.",
        "required_skills": ["Financial Analysis", "Excel", "SQL", "Bloomberg Terminal", "Statistics"],
        "experience_required": "2-3 years",
        "job_type": JobType.in_office,
        "salary_range": "10-15 LPA",
        "industry": "Finance",
    },
]

RESUME_TEMPLATES = [
    {
        "name": "Software Engineer Resume",
        "parsed_text": """Amit Kumar
Senior Software Engineer
amit.kumar@example.com | 9876543210

EXPERIENCE
TechCorp Solutions (2020-Present) | Senior Software Engineer
- Led backend development using Python and FastAPI
- Designed and implemented microservices architecture
- Worked with PostgreSQL, Redis, and AWS

Previous Company (2018-2020) | Software Engineer
- Developed REST APIs and integrated with frontend teams
- Implemented database optimization strategies

SKILLS
Python, FastAPI, PostgreSQL, AWS, Docker, Kubernetes, REST APIs, Git, Agile

EDUCATION
B.Tech Computer Science | IIT Delhi (2018)
""",
        "parsed_json": {
            "skills": ["Python", "FastAPI", "PostgreSQL", "AWS", "Docker", "Kubernetes"],
            "experience": "4+ years",
            "education": "B.Tech Computer Science",
        }
    },
    {
        "name": "Data Analyst Resume",
        "parsed_text": """Priya Singh
Data Analyst
priya.singh@example.com | 9876543211

EXPERIENCE
FinancePlus Inc (2021-Present) | Senior Data Analyst
- Created dashboards and reports using Tableau
- Performed statistical analysis on financial data
- Optimized SQL queries for large datasets

DataCorp (2019-2021) | Data Analyst
- Built ETL pipelines using Python
- Provided insights for business decisions

SKILLS
SQL, Python, Tableau, Excel, Statistics, Data Visualization, Pandas, NumPy

EDUCATION
Bachelor of Science in Statistics | Delhi University (2019)
""",
        "parsed_json": {
            "skills": ["SQL", "Python", "Tableau", "Excel", "Statistics"],
            "experience": "3+ years",
            "education": "B.S. Statistics",
        }
    },
    {
        "name": "Product Manager Resume",
        "parsed_text": """Rajesh Patel
Product Manager
rajesh.patel@example.com | 9876543212

EXPERIENCE
Healthcare Tech (2019-Present) | Senior Product Manager
- Owned product roadmap and strategy
- Led cross-functional teams (engineering, design, marketing)
- Increased user retention by 40%

Previous Startup (2017-2019) | Product Manager
- Built product from scratch to 100K users
- Conducted user research and user testing

SKILLS
Product Strategy, Leadership, User Research, Data Analysis, Roadmapping, Agile

EDUCATION
MBA from ISB | B.Tech from NIT
""",
        "parsed_json": {
            "skills": ["Product Strategy", "Leadership", "User Research", "Data Analysis"],
            "experience": "5+ years",
            "education": "MBA - ISB",
        }
    },
    {
        "name": "UI/UX Designer Resume",
        "parsed_text": """Deepika Sharma
UX/UI Designer
deepika.sharma@example.com | 9876543213

EXPERIENCE
ECommerce Global (2021-Present) | Senior UX Designer
- Designed mobile app interfaces for 2M+ users
- Conducted user research and usability testing
- Created design systems and prototypes

Design Studio (2019-2021) | UI/UX Designer
- Worked on multiple web and mobile projects
- Collaborated with product and engineering teams

SKILLS
Figma, UI Design, User Research, Prototyping, Wireframing, Adobe XD, Interaction Design

EDUCATION
Diploma in Graphic Design | National Institute of Design (NID)
""",
        "parsed_json": {
            "skills": ["Figma", "UI Design", "User Research", "Prototyping", "Wireframing"],
            "experience": "4+ years",
            "education": "Diploma - NID",
        }
    },
    {
        "name": "Consultant Resume",
        "parsed_text": """Vikram Desai
Senior Consultant
vikram.desai@example.com | 9876543214

EXPERIENCE
Consulting Partners LLP (2018-Present) | Senior Consultant
- Led consulting projects for Fortune 500 companies
- Provided strategic recommendations to C-level executives
- Managed teams of 5-10 consultants

McKinsey & Co (2016-2018) | Consultant
- Worked on strategy, operations, and digital transformation projects
- Analyzed market trends and competitive landscapes

SKILLS
Strategic Consulting, Project Management, Data Analysis, Presentation, Leadership

EDUCATION
MBA from IIMA | B.Com from Delhi University
""",
        "parsed_json": {
            "skills": ["Strategic Consulting", "Project Management", "Data Analysis", "Leadership"],
            "experience": "6+ years",
            "education": "MBA - IIMA",
        }
    },
]


async def seed_database():
    """Seed the database with dummy data."""
    async with AsyncSessionLocal() as session:
        try:
            # Create seekers
            print("Creating job seekers...")
            seekers = []
            for seeker_data in SEEKERS_DATA:
                hashed_pwd = hash_password(seeker_data.pop("password"))
                seeker = User(
                    **seeker_data,
                    hashed_password=hashed_pwd,
                    role=UserRole.seeker,
                    is_verified=True,
                    onboarding_complete=True,
                    auto_apply_enabled=True,
                )
                session.add(seeker)
                seekers.append(seeker)
            await session.flush()
            print(f"✓ Created {len(seekers)} job seekers")

            # Create resumes for seekers
            print("Creating resumes...")
            for i, seeker in enumerate(seekers):
                resume_data = RESUME_TEMPLATES[i]
                resume = Resume(
                    user_id=seeker.id,
                    filename=f"{seeker.first_name}_{seeker.last_name}_resume.pdf",
                    file_path=f"/uploads/{seeker.id}/resume.pdf",
                    file_size_bytes=102400,
                    parsed_text=resume_data["parsed_text"],
                    parsed_json=resume_data["parsed_json"],
                )
                session.add(resume)
            await session.flush()
            print(f"✓ Created {len(seekers)} resumes")

            # Create recruiters
            print("Creating recruiters...")
            recruiters = []
            for recruiter_data in RECRUITERS_DATA:
                hashed_pwd = hash_password(recruiter_data.pop("password"))
                recruiter = User(
                    **recruiter_data,
                    hashed_password=hashed_pwd,
                    role=UserRole.provider,
                    is_verified=True,
                    onboarding_complete=True,
                )
                session.add(recruiter)
                recruiters.append(recruiter)
            await session.flush()
            print(f"✓ Created {len(recruiters)} recruiters")

            # Create job postings
            print("Creating job postings...")
            job_count = 0
            for recruiter in recruiters:
                # Each recruiter posts 1-2 jobs
                num_jobs = 1 if recruiter == recruiters[-1] else 2
                for i in range(num_jobs):
                    job_data = JOBS_DATA[job_count % len(JOBS_DATA)]
                    job = JobPosting(
                        provider_id=recruiter.id,
                        title=job_data["title"],
                        description=job_data["description"],
                        required_skills=job_data["required_skills"],
                        experience_required=job_data["experience_required"],
                        job_type=job_data["job_type"],
                        salary_range=job_data["salary_range"],
                        industry=job_data["industry"],
                        posted_by_name=f"{recruiter.first_name} {recruiter.last_name}",
                        is_active=True,
                    )
                    session.add(job)
                    job_count += 1
            await session.flush()
            print(f"✓ Created {job_count} job postings")

            # Commit all changes
            await session.commit()
            print("\n✅ Database seeded successfully!")
            print(f"Summary:")
            print(f"  - Job Seekers: {len(seekers)}")
            print(f"  - Resumes: {len(seekers)}")
            print(f"  - Recruiters: {len(recruiters)}")
            print(f"  - Job Postings: {job_count}")

        except Exception as e:
            await session.rollback()
            print(f"❌ Error seeding database: {e}")
            raise


async def main():
    """Main entry point."""
    print("🌱 Starting database seed...\n")
    await seed_database()


if __name__ == "__main__":
    asyncio.run(main())
