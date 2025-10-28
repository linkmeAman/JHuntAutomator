from sqlalchemy import Column, Integer, String, Text, Boolean, Float, DateTime
from sqlalchemy.sql import func
from .database import Base
import hashlib

class Job(Base):
    __tablename__ = "jobs"
    
    id = Column(Integer, primary_key=True, index=True)
    job_hash = Column(String, unique=True, index=True)
    title = Column(String, index=True)
    company = Column(String, index=True)
    location = Column(String)
    description = Column(Text)
    requirements = Column(Text, nullable=True)
    url = Column(String)
    source = Column(String)
    post_date = Column(String, nullable=True)
    relevance_score = Column(Float, default=0.0)
    keywords_matched = Column(String, nullable=True)
    applied = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    @staticmethod
    def generate_hash(title: str, company: str, url: str) -> str:
        content = f"{title}{company}{url}".lower()
        return hashlib.md5(content.encode()).hexdigest()


class Settings(Base):
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True)
    value = Column(Text)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())
