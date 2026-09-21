"""Add colleges, courses, specializations, approvals, loans, exams, placements and faculty tables.

Revision ID: 3531b13e7900
Revises: f7a8b9c0d1e2
Create Date: 2026-09-21 14:30:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '3531b13e7900'
down_revision: Union[str, None] = 'f7a8b9c0d1e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Colleges
    op.create_table(
        'colleges',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('college_id_code', sa.String(length=100), nullable=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=100), nullable=True, server_default='Online / Distance'),
        sa.Column('country', sa.String(length=100), nullable=True, server_default='India'),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state', sa.String(length=100), nullable=True),
        sa.Column('full_address', sa.Text(), nullable=True),
        sa.Column('established_year', sa.Integer(), nullable=True),
        sa.Column('cv_rating', sa.Float(), nullable=True, server_default='0.0'),
        sa.Column('total_reviews', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_courses', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('total_specializations', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('min_fee', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('max_fee', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('approvals_summary', sa.Text(), nullable=True),
        sa.Column('whatsapp', sa.String(length=50), nullable=True),
        sa.Column('helpline', sa.String(length=50), nullable=True),
        sa.Column('official_admission_link', sa.Text(), nullable=True),
        sa.Column('prospectus_pdf', sa.Text(), nullable=True),
        sa.Column('college_vidya_url', sa.Text(), nullable=True),
        sa.Column('about_overview', sa.Text(), nullable=True),
        sa.Column('banner_image', sa.String(length=500), nullable=True),
        sa.Column('logo_image', sa.String(length=500), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('name', name='uq_colleges_name'),
        sa.UniqueConstraint('slug', name='uq_colleges_slug')
    )
    op.create_index('ix_colleges_slug', 'colleges', ['slug'])
    op.create_index('ix_colleges_name', 'colleges', ['name'])
    op.create_index('ix_colleges_college_id_code', 'colleges', ['college_id_code'])
    op.create_index('ix_colleges_country', 'colleges', ['country'])
    op.create_index('ix_colleges_city', 'colleges', ['city'])
    op.create_index('ix_colleges_state', 'colleges', ['state'])

    # 2. College Courses
    op.create_table(
        'college_courses',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('college_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=False),
        sa.Column('course_name', sa.String(length=150), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=True),
        sa.Column('course_slug', sa.String(length=200), nullable=True),
        sa.Column('duration', sa.String(length=100), nullable=True),
        sa.Column('duration_months', sa.Integer(), nullable=True),
        sa.Column('base_total_fee', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('base_per_semester_fee', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('base_annual_fee', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('one_time_fee', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('other_fees_breakdown', sa.Text(), nullable=True),
        sa.Column('est_monthly_emi', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('specializations_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('course_url', sa.Text(), nullable=True),
        sa.Column('eligibility', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('college_id', 'course_name', name='uq_college_course_name')
    )
    op.create_index('ix_college_courses_college_id', 'college_courses', ['college_id'])
    op.create_index('ix_college_courses_course_name', 'college_courses', ['course_name'])

    # 3. College Specializations
    op.create_table(
        'college_specializations',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('college_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=False),
        sa.Column('college_course_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('college_courses.id', ondelete='CASCADE'), nullable=True),
        sa.Column('course_name', sa.String(length=150), nullable=False),
        sa.Column('specialization_name', sa.String(length=255), nullable=False),
        sa.Column('specialization_slug', sa.String(length=255), nullable=True),
        sa.Column('duration', sa.String(length=100), nullable=True),
        sa.Column('duration_months', sa.Integer(), nullable=True),
        sa.Column('total_fee', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('per_semester_fee', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('annual_fee', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('one_time_fee', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('other_fees_breakdown', sa.Text(), nullable=True),
        sa.Column('est_monthly_emi', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('specialization_url', sa.Text(), nullable=True),
        sa.Column('admission_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('college_id', 'course_name', 'specialization_name', name='uq_college_course_specialization')
    )
    op.create_index('ix_college_specializations_college_id', 'college_specializations', ['college_id'])
    op.create_index('ix_college_specializations_course_name', 'college_specializations', ['course_name'])
    op.create_index('ix_college_specializations_specialization_name', 'college_specializations', ['specialization_name'])

    # 4. Approvals
    op.create_table(
        'college_approvals',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('college_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=False),
        sa.Column('approvals_list', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('total_approvals', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('ugc_deb', sa.String(length=100), nullable=True),
        sa.Column('aicte', sa.String(length=100), nullable=True),
        sa.Column('naac', sa.String(length=50), nullable=True),
        sa.Column('nirf', sa.String(length=100), nullable=True),
        sa.Column('wes', sa.String(length=100), nullable=True),
        sa.Column('qs_ranking', sa.String(length=100), nullable=True),
        sa.Column('other_accreditations', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('college_id', name='uq_college_approvals_college_id')
    )
    op.create_index('ix_college_approvals_college_id', 'college_approvals', ['college_id'])

    # 5. EMI & Loan Plans
    op.create_table(
        'college_emi_loan_plans',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('college_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=False),
        sa.Column('no_cost_emi_available', sa.String(length=50), nullable=True),
        sa.Column('loan_sanction_time', sa.String(length=100), nullable=True),
        sa.Column('lending_partners', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('bank_visit_required', sa.String(length=50), nullable=True),
        sa.Column('policy_details', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('college_id', name='uq_college_emi_loan_plans_college_id')
    )
    op.create_index('ix_college_emi_loan_plans_college_id', 'college_emi_loan_plans', ['college_id'])

    # 6. Admission Exams
    op.create_table(
        'college_admission_exams',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('college_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=False),
        sa.Column('examination_pattern_mode', sa.Text(), nullable=True),
        sa.Column('admission_procedure', sa.Text(), nullable=True),
        sa.Column('important_dates_cutoffs', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('college_id', name='uq_college_admission_exams_college_id')
    )
    op.create_index('ix_college_admission_exams_college_id', 'college_admission_exams', ['college_id'])

    # 7. Placement Partners
    op.create_table(
        'college_placement_partners',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('college_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=False),
        sa.Column('hiring_companies', postgresql.JSON(astext_type=sa.Text()), nullable=True, server_default='[]'),
        sa.Column('total_partners_listed', sa.Integer(), nullable=True, server_default='0'),
        sa.Column('placement_assistance_overview', sa.Text(), nullable=True),
        sa.Column('highest_package', sa.String(length=50), nullable=True),
        sa.Column('average_package', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.UniqueConstraint('college_id', name='uq_college_placement_partners_college_id')
    )
    op.create_index('ix_college_placement_partners_college_id', 'college_placement_partners', ['college_id'])

    # 8. Faculty
    op.create_table(
        'college_faculties',
        sa.Column('id', postgresql.UUID(as_uuid=False), primary_key=True),
        sa.Column('college_id', postgresql.UUID(as_uuid=False), sa.ForeignKey('colleges.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=True),
        sa.Column('designation_title', sa.String(length=200), nullable=True),
        sa.Column('department_subtitle', sa.String(length=200), nullable=True),
        sa.Column('profile_bio', sa.Text(), nullable=True),
        sa.Column('linkedin_url', sa.Text(), nullable=True),
        sa.Column('profile_picture_url', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False)
    )
    op.create_index('ix_college_faculties_college_id', 'college_faculties', ['college_id'])


def downgrade() -> None:
    op.drop_table('college_faculties')
    op.drop_table('college_placement_partners')
    op.drop_table('college_admission_exams')
    op.drop_table('college_emi_loan_plans')
    op.drop_table('college_approvals')
    op.drop_table('college_specializations')
    op.drop_table('college_courses')
    op.drop_table('colleges')
