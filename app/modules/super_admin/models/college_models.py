import uuid
from datetime import datetime
from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, text
)
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import relationship

from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class College(Base):
    __tablename__ = "colleges"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    slug = Column(String(255), unique=True, nullable=False, index=True)
    college_id_code = Column(String(100), nullable=True, index=True)  # Scraped ID, e.g., "CV-101"
    name = Column(String(255), unique=True, nullable=False, index=True)
    type = Column(String(100), nullable=True, default="Online / Distance")  # Private, Govt, Deemed, etc.
    country = Column(String(100), nullable=True, default="India", index=True)
    city = Column(String(100), nullable=True, index=True)
    state = Column(String(100), nullable=True, index=True)
    full_address = Column(Text, nullable=True)
    established_year = Column(Integer, nullable=True)
    cv_rating = Column(Float, nullable=True, default=0.0)
    total_reviews = Column(Integer, nullable=False, default=0, server_default=text("0"))
    total_courses = Column(Integer, nullable=False, default=0, server_default=text("0"))
    total_specializations = Column(Integer, nullable=False, default=0, server_default=text("0"))
    min_fee = Column(Numeric(12, 2), nullable=True)
    max_fee = Column(Numeric(12, 2), nullable=True)
    approvals_summary = Column(Text, nullable=True)
    whatsapp = Column(String(50), nullable=True)
    helpline = Column(String(50), nullable=True)
    official_admission_link = Column(Text, nullable=True)
    prospectus_pdf = Column(Text, nullable=True)
    college_vidya_url = Column(Text, nullable=True)
    about_overview = Column(Text, nullable=True)
    banner_image = Column(String(500), nullable=True)
    logo_image = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default=text("true"))

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    courses = relationship("CollegeCourse", back_populates="college", cascade="all, delete-orphan", lazy="selectin")
    specializations = relationship("CollegeSpecialization", back_populates="college", cascade="all, delete-orphan", lazy="selectin")
    approvals = relationship("CollegeApproval", back_populates="college", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    emi_loan = relationship("CollegeEmiLoan", back_populates="college", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    admission_exam = relationship("CollegeAdmissionExam", back_populates="college", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    placement = relationship("CollegePlacementPartner", back_populates="college", uselist=False, cascade="all, delete-orphan", lazy="selectin")
    faculty = relationship("CollegeFaculty", back_populates="college", cascade="all, delete-orphan", lazy="selectin")


class CollegeCourse(Base):
    __tablename__ = "college_courses"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    college_id = Column(UUID(as_uuid=False), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True)
    course_name = Column(String(150), nullable=False, index=True)  # e.g., "MBA", "MCA", "BBA"
    display_name = Column(String(255), nullable=True)  # e.g., "Master of Business Administration (Online)"
    course_slug = Column(String(200), nullable=True)
    duration = Column(String(100), nullable=True)  # e.g., "2 Years"
    duration_months = Column(Integer, nullable=True)  # e.g., 24
    base_total_fee = Column(Numeric(12, 2), nullable=True)
    base_per_semester_fee = Column(Numeric(12, 2), nullable=True)
    base_annual_fee = Column(Numeric(12, 2), nullable=True)
    one_time_fee = Column(Numeric(12, 2), nullable=True)
    other_fees_breakdown = Column(Text, nullable=True)
    est_monthly_emi = Column(Numeric(12, 2), nullable=True)
    specializations_count = Column(Integer, nullable=False, default=0, server_default=text("0"))
    course_url = Column(Text, nullable=True)
    eligibility = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    college = relationship("College", back_populates="courses")
    specializations = relationship("CollegeSpecialization", back_populates="college_course", cascade="all, delete-orphan", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("college_id", "course_name", name="uq_college_course_name"),
    )


class CollegeSpecialization(Base):
    __tablename__ = "college_specializations"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    college_id = Column(UUID(as_uuid=False), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True)
    college_course_id = Column(UUID(as_uuid=False), ForeignKey("college_courses.id", ondelete="CASCADE"), nullable=True, index=True)
    course_name = Column(String(150), nullable=False, index=True)
    specialization_name = Column(String(255), nullable=False, index=True)
    specialization_slug = Column(String(255), nullable=True)
    duration = Column(String(100), nullable=True)
    duration_months = Column(Integer, nullable=True)
    total_fee = Column(Numeric(12, 2), nullable=True)
    per_semester_fee = Column(Numeric(12, 2), nullable=True)
    annual_fee = Column(Numeric(12, 2), nullable=True)
    one_time_fee = Column(Numeric(12, 2), nullable=True)
    other_fees_breakdown = Column(Text, nullable=True)
    est_monthly_emi = Column(Numeric(12, 2), nullable=True)
    specialization_url = Column(Text, nullable=True)
    admission_url = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    college = relationship("College", back_populates="specializations")
    college_course = relationship("CollegeCourse", back_populates="specializations")

    __table_args__ = (
        UniqueConstraint("college_id", "course_name", "specialization_name", name="uq_college_course_specialization"),
    )


class CollegeApproval(Base):
    __tablename__ = "college_approvals"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    college_id = Column(UUID(as_uuid=False), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    approvals_list = Column(JSON, nullable=True, server_default=text("'[]'::json"))
    total_approvals = Column(Integer, nullable=True, default=0)
    ugc_deb = Column(String(100), nullable=True)
    aicte = Column(String(100), nullable=True)
    naac = Column(String(50), nullable=True)
    nirf = Column(String(100), nullable=True)
    wes = Column(String(100), nullable=True)
    qs_ranking = Column(String(100), nullable=True)
    other_accreditations = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    college = relationship("College", back_populates="approvals")


class CollegeEmiLoan(Base):
    __tablename__ = "college_emi_loan_plans"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    college_id = Column(UUID(as_uuid=False), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    no_cost_emi_available = Column(String(50), nullable=True)
    loan_sanction_time = Column(String(100), nullable=True)
    lending_partners = Column(JSON, nullable=True, server_default=text("'[]'::json"))
    bank_visit_required = Column(String(50), nullable=True)
    policy_details = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    college = relationship("College", back_populates="emi_loan")


class CollegeAdmissionExam(Base):
    __tablename__ = "college_admission_exams"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    college_id = Column(UUID(as_uuid=False), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    examination_pattern_mode = Column(Text, nullable=True)
    admission_procedure = Column(Text, nullable=True)
    important_dates_cutoffs = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    college = relationship("College", back_populates="admission_exam")


class CollegePlacementPartner(Base):
    __tablename__ = "college_placement_partners"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    college_id = Column(UUID(as_uuid=False), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    hiring_companies = Column(JSON, nullable=True, server_default=text("'[]'::json"))
    total_partners_listed = Column(Integer, nullable=True, default=0)
    placement_assistance_overview = Column(Text, nullable=True)
    highest_package = Column(String(50), nullable=True)
    average_package = Column(String(50), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    college = relationship("College", back_populates="placement")


class CollegeFaculty(Base):
    __tablename__ = "college_faculties"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    college_id = Column(UUID(as_uuid=False), ForeignKey("colleges.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(200), nullable=True)
    designation_title = Column(String(200), nullable=True)
    department_subtitle = Column(String(200), nullable=True)
    profile_bio = Column(Text, nullable=True)
    linkedin_url = Column(Text, nullable=True)
    profile_picture_url = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    college = relationship("College", back_populates="faculty")
