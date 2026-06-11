from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, EmailStr

from database import get_db
from schemas.auth import UserOut, TokenResponse
from controllers.superadmin_controller import (
    register_superadmin as ctrl_register_superadmin,
    login_superadmin as ctrl_login_superadmin,
)

router = APIRouter(prefix="/superadmin", tags=["superadmin"])


class SuperAdminRegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    phone: str
    password: str
    secret_key: str


class SuperAdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register_superadmin(body: SuperAdminRegisterRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_register_superadmin(body, db)


@router.post("/login", response_model=TokenResponse)
async def login_superadmin(body: SuperAdminLoginRequest, db: AsyncSession = Depends(get_db)):
    return await ctrl_login_superadmin(body, db)
