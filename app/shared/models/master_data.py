import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

def _uuid():
    return str(uuid.uuid4())

class Department(Base):
    __tablename__ = "departments"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(100), nullable=False, unique=True)
    # name_hi = Column(String(100), nullable=True)
    # name_pa = Column(String(100), nullable=True)
    
    jobs = relationship("DepartmentJob", back_populates="department", cascade="all, delete-orphan")

class DepartmentJob(Base):
    __tablename__ = "department_jobs"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(100), nullable=False)
    # name_hi = Column(String(255), nullable=True)
    # name_pa = Column(String(255), nullable=True)
    department_id = Column(UUID(as_uuid=False), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False)

    department = relationship("Department", back_populates="jobs")
