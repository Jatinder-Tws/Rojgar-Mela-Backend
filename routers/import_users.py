import io
import string
import random
import pandas as pd
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database import get_db
from models.user import User, UserRole, JobType
from models.imported_user_password import ImportedUserPassword
from services.auth_service import hash_password

router = APIRouter(
    prefix="/import",
    tags=["Import"],
)

def generate_random_password(length=10):
    characters = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(random.choice(characters) for _ in range(length))

def clean_value(val):
    if pd.isna(val):
        return None
    return str(val).strip()

@router.post("/seekers")
async def import_seekers(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading Excel file: {str(e)}")

    imported_count = 0
    skipped_count = 0

    for index, row in df.iterrows():
        email = clean_value(row.get('Email Address'))
        if not email:
            skipped_count += 1
            continue
            
        # Check if user already exists
        result = await db.execute(select(User).filter(User.email == email))
        existing_user = result.scalars().first()
        if existing_user:
            skipped_count += 1
            continue

        full_name = clean_value(row.get('Full Name')) or ""
        name_parts = full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        plain_password = generate_random_password()
        hashed_password = hash_password(plain_password)

        new_user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=clean_value(row.get('Mobile Number')) or "",
            hashed_password=hashed_password,
            role=UserRole.seeker,
            is_verified=True,
            
            father_or_mother_name=clean_value(row.get("Father's / Mother's Name")),
            gender=clean_value(row.get('Gender')),
            address=clean_value(row.get('Address')),
            highest_qualification=clean_value(row.get('Highest Qualification')),
            stream_specialization=clean_value(row.get('Stream / Specialization')),
            college_institute_name=clean_value(row.get('College / Institute Name')),
            preferred_job_sector=clean_value(row.get('Preferred Job / Sector')),
            experience=clean_value(row.get('Total Experience')),
        )
        
        db.add(new_user)
        await db.flush()  # to get new_user.id
        
        imported_password = ImportedUserPassword(
            user_id=new_user.id,
            email=email,
            plain_password=plain_password
        )
        db.add(imported_password)
        
        imported_count += 1

    await db.commit()
    return {"message": "Seekers imported successfully", "imported": imported_count, "skipped": skipped_count}

@router.post("/providers")
async def import_providers(file: UploadFile = File(...), db: AsyncSession = Depends(get_db)):
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="Only Excel files are supported")
    
    try:
        contents = await file.read()
        df = pd.read_excel(io.BytesIO(contents))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error reading Excel file: {str(e)}")

    imported_count = 0
    skipped_count = 0

    for index, row in df.iterrows():
        email = clean_value(row.get('Email Address'))
        if not email:
            skipped_count += 1
            continue
            
        # Check if user already exists
        result = await db.execute(select(User).filter(User.email == email))
        existing_user = result.scalars().first()
        if existing_user:
            skipped_count += 1
            continue

        full_name = clean_value(row.get('Full Name:')) or clean_value(row.get('Full Name')) or ""
        name_parts = full_name.split(" ", 1)
        first_name = name_parts[0]
        last_name = name_parts[1] if len(name_parts) > 1 else ""

        plain_password = generate_random_password()
        hashed_password = hash_password(plain_password)

        new_user = User(
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=clean_value(row.get('Contact Number')) or "",
            hashed_password=hashed_password,
            role=UserRole.provider,
            is_verified=True,
            
            company_name=clean_value(row.get('Company / Organization Name')),
            industry=clean_value(row.get('Industry / Sector')),
            company_location=clean_value(row.get('Location (City, State)')),
            job_roles_offering=clean_value(row.get('Job Roles Offering')),
            specific_requirements=clean_value(row.get('Any specific requirement for candidates?')),
        )
        
        db.add(new_user)
        await db.flush()  # to get new_user.id
        
        imported_password = ImportedUserPassword(
            user_id=new_user.id,
            email=email,
            plain_password=plain_password
        )
        db.add(imported_password)
        
        imported_count += 1

    await db.commit()
    return {"message": "Providers imported successfully", "imported": imported_count, "skipped": skipped_count}
