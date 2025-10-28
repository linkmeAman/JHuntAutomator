import os
from typing import List

class Settings:
    DATABASE_URL: str = "sqlite:///./jobs.db"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    DEFAULT_KEYWORDS: List[str] = [
        "Python", "JavaScript", "React", "Node.js", "FastAPI",
        "Software Engineer", "Full Stack", "Backend", "Frontend",
        "DevOps", "Data Engineer", "Machine Learning", "AI"
    ]
    
    DEFAULT_LOCATIONS: List[str] = ["Remote", "United States"]
    
    CRAWL_SCHEDULE_HOUR: int = 7
    CRAWL_SCHEDULE_MINUTE: int = 0
    
    MAX_JOBS_PER_SOURCE: int = 50
    
    JOB_SOURCES: dict = {
        "indeed": True,
        "remoteok": True,
        "weworkremotely": True
    }

settings = Settings()
