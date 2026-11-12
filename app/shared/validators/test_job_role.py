import pytest

from app.shared.validators.job_role import job_role_error, validate_job_role_value


@pytest.mark.parametrize(
    "value",
    [
        ".",
        "..",
        "??",
        "1",
        "115",
        "141119",
        "ggfgdg23232323",
        "UI/UX",
        "C++",
        "HR & Admin",
        "Sr. Manager",
        "0-1year",
        "Fresher",
        "2 years",
        "n/a",
        "test",
    ],
)
def test_rejects_junk(value: str):
    assert job_role_error(value) is not None


@pytest.mark.parametrize(
    "value",
    ["Software Developer", "HR Executive", "Accountant", "Sales Manager", "Data Analyst", "Full Stack Developer"],
)
def test_accepts_real_roles(value: str):
    assert job_role_error(value) is None
    assert validate_job_role_value(value) == value


def test_empty_optional_ok():
    assert job_role_error("") is None
    assert validate_job_role_value("  ") is None


def test_empty_required_fails():
    with pytest.raises(ValueError, match="real job role"):
        validate_job_role_value("", required=True)


def test_normalizes_whitespace():
    assert validate_job_role_value("  Sales   Executive  ") == "Sales Executive"
