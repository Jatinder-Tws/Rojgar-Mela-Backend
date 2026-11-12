"""Regression: dashboard must load the newest assessment when a user has many rows."""

from app.modules.jobs_portal.services.assessment_result_queries import latest_assessment_for_user_query


def test_latest_assessment_query_limits_and_orders():
    query = latest_assessment_for_user_query("user-123")
    sql = str(query.compile(compile_kwargs={"literal_binds": True})).lower()
    assert "assessment_results" in sql
    assert "user_id" in sql
    assert "created_at" in sql
    assert "desc" in sql
    assert "limit" in sql
