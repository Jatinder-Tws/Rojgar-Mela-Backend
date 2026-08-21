import uuid
from sqlalchemy import Column, String, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base


def _uuid():
    return str(uuid.uuid4())


class MasterState(Base):
    __tablename__ = "master_states"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(100), nullable=False, unique=True)


class MasterCity(Base):
    __tablename__ = "master_cities"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(100), nullable=False)
    state_id = Column(UUID(as_uuid=False), ForeignKey("master_states.id", ondelete="CASCADE"), nullable=True)


class MasterIndustry(Base):
    __tablename__ = "master_industries"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(100), nullable=False, unique=True)


class MasterLanguage(Base):
    __tablename__ = "master_languages"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(100), nullable=False, unique=True)


class MasterRole(Base):
    __tablename__ = "master_roles"

    id = Column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    name = Column(String(100), nullable=False, unique=True)
