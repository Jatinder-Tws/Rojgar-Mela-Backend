import uuid
from datetime import datetime, date
from sqlalchemy import Column, String, DateTime, ForeignKey, Date
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base

class Attendance(Base):
    __tablename__ = "attendance"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    date = Column(Date, default=date.today, nullable=False)
    attendance_status = Column(String, nullable=False, default="Present")
    marked_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User", backref="attendance_records")
