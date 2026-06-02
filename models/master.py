from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from database import Base

class MasterState(Base):
    __tablename__ = "master_states"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    code = Column(String(10), unique=True, nullable=True)

class MasterCity(Base):
    __tablename__ = "master_cities"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), index=True, nullable=False)
    state_id = Column(Integer, ForeignKey("master_states.id", ondelete="CASCADE"), nullable=False)
    
    state = relationship("MasterState")

class MasterIndustry(Base):
    __tablename__ = "master_industries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)

class MasterLanguage(Base):
    __tablename__ = "master_languages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)

class MasterRole(Base):
    __tablename__ = "master_roles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    industry_id = Column(Integer, ForeignKey("master_industries.id", ondelete="CASCADE"), nullable=False)
    industry = relationship("MasterIndustry")
