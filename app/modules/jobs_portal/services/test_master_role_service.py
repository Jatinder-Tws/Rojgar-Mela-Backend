from app.modules.jobs_portal.services.master_role_service import MasterRoleCreate
from app.shared.validators.job_role import job_role_error


def test_create_payload_uses_job_role_rules():
    """Create endpoint rejects junk the same way as profile validation."""
    assert job_role_error("ggfgdg23232323", required=True) is not None
    assert job_role_error("Software Developer", required=True) is None
    body = MasterRoleCreate(name="  Sales Executive  ")
    assert body.name.strip() == "Sales Executive"
