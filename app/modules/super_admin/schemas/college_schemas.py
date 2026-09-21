from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------
# Sub-entity Schemas
# ---------------------------------------------------------

class CollegeSpecializationBase(BaseModel):
    course_name: str
    specialization_name: str
    specialization_slug: Optional[str] = None
    duration: Optional[str] = None
    duration_months: Optional[int] = None
    total_fee: Optional[float] = None
    per_semester_fee: Optional[float] = None
    annual_fee: Optional[float] = None
    one_time_fee: Optional[float] = None
    other_fees_breakdown: Optional[str] = None
    est_monthly_emi: Optional[float] = None
    specialization_url: Optional[str] = None
    admission_url: Optional[str] = None


class CollegeSpecializationCreate(CollegeSpecializationBase):
    pass


class CollegeSpecializationOut(CollegeSpecializationBase):
    id: str
    college_id: str
    college_course_id: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CollegeCourseBase(BaseModel):
    course_name: str
    display_name: Optional[str] = None
    course_slug: Optional[str] = None
    duration: Optional[str] = None
    duration_months: Optional[int] = None
    base_total_fee: Optional[float] = None
    base_per_semester_fee: Optional[float] = None
    base_annual_fee: Optional[float] = None
    one_time_fee: Optional[float] = None
    other_fees_breakdown: Optional[str] = None
    est_monthly_emi: Optional[float] = None
    specializations_count: Optional[int] = 0
    course_url: Optional[str] = None
    eligibility: Optional[str] = None


class CollegeCourseCreate(CollegeCourseBase):
    specializations: Optional[List[CollegeSpecializationCreate]] = []


class CollegeCourseOut(CollegeCourseBase):
    id: str
    college_id: str
    specializations: List[CollegeSpecializationOut] = []
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CollegeApprovalBase(BaseModel):
    approvals_list: Optional[List[str]] = []
    total_approvals: Optional[int] = 0
    ugc_deb: Optional[str] = None
    aicte: Optional[str] = None
    naac: Optional[str] = None
    nirf: Optional[str] = None
    wes: Optional[str] = None
    qs_ranking: Optional[str] = None
    other_accreditations: Optional[str] = None


class CollegeApprovalCreate(CollegeApprovalBase):
    pass


class CollegeApprovalOut(CollegeApprovalBase):
    id: str
    college_id: str

    class Config:
        from_attributes = True


class CollegeEmiLoanBase(BaseModel):
    no_cost_emi_available: Optional[str] = None
    loan_sanction_time: Optional[str] = None
    lending_partners: Optional[List[str]] = []
    bank_visit_required: Optional[str] = None
    policy_details: Optional[str] = None


class CollegeEmiLoanCreate(CollegeEmiLoanBase):
    pass


class CollegeEmiLoanOut(CollegeEmiLoanBase):
    id: str
    college_id: str

    class Config:
        from_attributes = True


class CollegeAdmissionExamBase(BaseModel):
    examination_pattern_mode: Optional[str] = None
    admission_procedure: Optional[str] = None
    important_dates_cutoffs: Optional[str] = None


class CollegeAdmissionExamCreate(CollegeAdmissionExamBase):
    pass


class CollegeAdmissionExamOut(CollegeAdmissionExamBase):
    id: str
    college_id: str

    class Config:
        from_attributes = True


class CollegePlacementPartnerBase(BaseModel):
    hiring_companies: Optional[List[str]] = []
    total_partners_listed: Optional[int] = 0
    placement_assistance_overview: Optional[str] = None
    highest_package: Optional[str] = None
    average_package: Optional[str] = None


class CollegePlacementPartnerCreate(CollegePlacementPartnerBase):
    pass


class CollegePlacementPartnerOut(CollegePlacementPartnerBase):
    id: str
    college_id: str

    class Config:
        from_attributes = True


class CollegeFacultyBase(BaseModel):
    name: Optional[str] = None
    designation_title: Optional[str] = None
    department_subtitle: Optional[str] = None
    profile_bio: Optional[str] = None
    linkedin_url: Optional[str] = None
    profile_picture_url: Optional[str] = None


class CollegeFacultyCreate(CollegeFacultyBase):
    pass


class CollegeFacultyOut(CollegeFacultyBase):
    id: str
    college_id: str

    class Config:
        from_attributes = True


# ---------------------------------------------------------
# Master College Schemas
# ---------------------------------------------------------

class CollegeBase(BaseModel):
    name: str
    slug: Optional[str] = None
    college_id_code: Optional[str] = None
    type: Optional[str] = "Online / Distance"
    country: Optional[str] = "India"
    city: Optional[str] = None
    state: Optional[str] = None
    full_address: Optional[str] = None
    established_year: Optional[int] = None
    cv_rating: Optional[float] = 0.0
    total_reviews: Optional[int] = 0
    total_courses: Optional[int] = 0
    total_specializations: Optional[int] = 0
    min_fee: Optional[float] = None
    max_fee: Optional[float] = None
    approvals_summary: Optional[str] = None
    whatsapp: Optional[str] = None
    helpline: Optional[str] = None
    official_admission_link: Optional[str] = None
    prospectus_pdf: Optional[str] = None
    college_vidya_url: Optional[str] = None
    about_overview: Optional[str] = None
    banner_image: Optional[str] = None
    logo_image: Optional[str] = None
    is_active: Optional[bool] = True


class CollegeCreate(CollegeBase):
    courses: Optional[List[CollegeCourseCreate]] = []
    specializations: Optional[List[CollegeSpecializationCreate]] = []
    approvals: Optional[CollegeApprovalCreate] = None
    emi_loan: Optional[CollegeEmiLoanCreate] = None
    admission_exam: Optional[CollegeAdmissionExamCreate] = None
    placement: Optional[CollegePlacementPartnerCreate] = None
    faculty: Optional[List[CollegeFacultyCreate]] = []


class CollegeUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    college_id_code: Optional[str] = None
    type: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    full_address: Optional[str] = None
    established_year: Optional[int] = None
    cv_rating: Optional[float] = None
    total_reviews: Optional[int] = None
    total_courses: Optional[int] = None
    total_specializations: Optional[int] = None
    min_fee: Optional[float] = None
    max_fee: Optional[float] = None
    approvals_summary: Optional[str] = None
    whatsapp: Optional[str] = None
    helpline: Optional[str] = None
    official_admission_link: Optional[str] = None
    prospectus_pdf: Optional[str] = None
    college_vidya_url: Optional[str] = None
    about_overview: Optional[str] = None
    banner_image: Optional[str] = None
    logo_image: Optional[str] = None
    is_active: Optional[bool] = None

    courses: Optional[List[CollegeCourseCreate]] = None
    approvals: Optional[CollegeApprovalCreate] = None
    emi_loan: Optional[CollegeEmiLoanCreate] = None
    admission_exam: Optional[CollegeAdmissionExamCreate] = None
    placement: Optional[CollegePlacementPartnerCreate] = None
    faculty: Optional[List[CollegeFacultyCreate]] = None


class CollegeListItem(CollegeBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class CollegeDetailOut(CollegeBase):
    id: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    courses: List[CollegeCourseOut] = []
    specializations: List[CollegeSpecializationOut] = []
    approvals: Optional[CollegeApprovalOut] = None
    emi_loan: Optional[CollegeEmiLoanOut] = None
    admission_exam: Optional[CollegeAdmissionExamOut] = None
    placement: Optional[CollegePlacementPartnerOut] = None
    faculty: List[CollegeFacultyOut] = []

    class Config:
        from_attributes = True


class CollegeListResponse(BaseModel):
    items: List[CollegeListItem]
    total: int
    page: int
    limit: int
    total_pages: int


# ---------------------------------------------------------
# Comparison & Import Schemas
# ---------------------------------------------------------

class CollegeCompareItem(BaseModel):
    college_id: str
    college_name: str
    college_slug: str
    logo_image: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    cv_rating: Optional[float] = None
    type: Optional[str] = None
    whatsapp: Optional[str] = None
    helpline: Optional[str] = None
    official_admission_link: Optional[str] = None
    prospectus_pdf: Optional[str] = None

    # Selected course data
    course_name: str
    display_name: Optional[str] = None
    duration: Optional[str] = None
    duration_months: Optional[int] = None
    base_total_fee: Optional[float] = None
    base_per_semester_fee: Optional[float] = None
    base_annual_fee: Optional[float] = None
    one_time_fee: Optional[float] = None
    est_monthly_emi: Optional[float] = None
    specializations_count: Optional[int] = 0
    specializations: List[str] = []

    # Approvals
    approvals_list: List[str] = []
    ugc_deb: Optional[str] = None
    aicte: Optional[str] = None
    naac: Optional[str] = None
    nirf: Optional[str] = None
    wes: Optional[str] = None

    # EMI & Loan
    no_cost_emi_available: Optional[str] = None
    loan_sanction_time: Optional[str] = None
    lending_partners: List[str] = []
    bank_visit_required: Optional[str] = None

    # Admission & Exams
    examination_pattern_mode: Optional[str] = None
    admission_procedure: Optional[str] = None
    important_dates_cutoffs: Optional[str] = None

    # Placements
    hiring_companies: List[str] = []
    placement_assistance_overview: Optional[str] = None
    highest_package: Optional[str] = None
    average_package: Optional[str] = None


class CollegeCompareResponse(BaseModel):
    course_name: str
    items: List[CollegeCompareItem]


class ExcelImportSummary(BaseModel):
    success: bool
    message: str
    colleges_created: int = 0
    colleges_updated: int = 0
    courses_created: int = 0
    courses_updated: int = 0
    specializations_created: int = 0
    specializations_updated: int = 0
    approvals_synced: int = 0
    loans_synced: int = 0
    admissions_synced: int = 0
    placements_synced: int = 0
    faculty_synced: int = 0
    errors: List[str] = []
