from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, field_serializer


class AuditLogItem(BaseModel):
    id: str
    actor_id: Optional[str] = None
    actor_name: str
    actor_email: Optional[str] = None
    actor_role: str
    action: str
    entity_type: str
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    description: str
    changes: Optional[Dict[str, Any]] = None
    request_path: Optional[str] = None
    request_method: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    @field_serializer("created_at")
    def serialize_created_at(self, dt: datetime, _info) -> str:
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()

    model_config = ConfigDict(from_attributes=True)


class AuditLogListResponse(BaseModel):
    items: List[AuditLogItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class AuditLogStatsResponse(BaseModel):
    total_today: int
    total_all_time: int
    role_counts: Dict[str, int]
    action_counts: Dict[str, int]
    top_actors: List[Dict[str, Any]]
    recent_trend: List[Dict[str, Any]]
