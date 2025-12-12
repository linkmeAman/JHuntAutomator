import json
import os
from pathlib import Path
from typing import List

def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}

class Settings:
    def __init__(self):
        self.DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite:///./jobs.db")
        self.API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
        self.API_PORT: int = int(os.getenv("API_PORT", "8000"))
        
        self.DEFAULT_KEYWORDS: List[str] = [
            "Python", "JavaScript", "React", "Node.js", "FastAPI",
            "Software Engineer", "Full Stack", "Backend", "Frontend",
            "DevOps", "Data Engineer", "Machine Learning", "AI"
        ]
        
        self.DEFAULT_LOCATIONS: List[str] = os.getenv("DEFAULT_LOCATIONS", "Remote,United States").split(",")
        self.DEFAULT_LOCATIONS = [loc.strip() for loc in self.DEFAULT_LOCATIONS if loc.strip()]

        greenhouse_env = os.getenv("GREENHOUSE_BOARDS", "gitlab,zapier,datadog")
        self.GREENHOUSE_BOARDS: List[dict] = self._parse_greenhouse_boards(greenhouse_env)
        
        self.CRAWL_SCHEDULE_HOUR: int = int(os.getenv("CRAWL_SCHEDULE_HOUR", "7"))
        self.CRAWL_SCHEDULE_MINUTE: int = int(os.getenv("CRAWL_SCHEDULE_MINUTE", "0"))
        
        self.MAX_JOBS_PER_SOURCE: int = int(os.getenv("MAX_JOBS_PER_SOURCE", "50"))
        
        self.JOB_SOURCES: dict = {
            "indeed": _as_bool(os.getenv("ENABLE_INDEED"), False),
            "remoteok": _as_bool(os.getenv("ENABLE_REMOTEOK"), True),
            "weworkremotely": _as_bool(os.getenv("ENABLE_WEWORKREMOTELY"), True),
            "greenhouse": _as_bool(os.getenv("ENABLE_GREENHOUSE"), True),
        }

        profile_text = os.getenv("PROFILE_TEXT", "").strip()
        profile_path = os.getenv("PROFILE_TEXT_PATH")
        if not profile_text and profile_path:
            path = Path(profile_path)
            if path.exists():
                profile_text = path.read_text(encoding="utf-8").strip()
        if not profile_text:
            profile_text = "Seasoned software engineer focused on backend APIs, automation, cloud infrastructure, and data engineering."
        self.PROFILE_TEXT_PATH: str | None = profile_path
        self.PROFILE_TEXT: str = profile_text
        self.NLP_MODEL_NAME: str = os.getenv("NLP_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
        self.NLP_WEIGHT: float = float(os.getenv("NLP_WEIGHT", "3.0"))

        self.ENABLE_NOTIFICATIONS: bool = _as_bool(os.getenv("ENABLE_NOTIFICATIONS"))
        self.ENABLE_EMAIL_NOTIFICATIONS: bool = _as_bool(os.getenv("ENABLE_EMAIL_NOTIFICATIONS"))
        self.ENABLE_TELEGRAM_NOTIFICATIONS: bool = _as_bool(os.getenv("ENABLE_TELEGRAM_NOTIFICATIONS"))

        self.SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
        self.SMTP_USERNAME: str | None = os.getenv("SMTP_USERNAME")
        self.SMTP_PASSWORD: str | None = os.getenv("SMTP_PASSWORD")
        self.EMAIL_SENDER: str | None = os.getenv("EMAIL_SENDER")
        self.EMAIL_RECIPIENT: str | None = os.getenv("EMAIL_RECIPIENT")

        self.TELEGRAM_BOT_TOKEN: str | None = os.getenv("TELEGRAM_BOT_TOKEN")
        self.TELEGRAM_CHAT_ID: str | None = os.getenv("TELEGRAM_CHAT_ID")

        self.NOTIFICATION_MIN_SCORE: float = float(os.getenv("NOTIFICATION_MIN_SCORE", "3.0"))
        self.CRAWL_MODE: str = os.getenv("CRAWL_MODE", "workflow").lower()

    def _parse_greenhouse_boards(self, boards_value: str | None) -> List[dict]:
        if not boards_value:
            return [
                {"name": "GitLab", "board_url": "https://boards.greenhouse.io/gitlab"},
                {"name": "Zapier", "board_url": "https://boards.greenhouse.io/zapier"},
                {"name": "Datadog", "board_url": "https://boards.greenhouse.io/datadog"},
            ]

        # JSON list support
        try:
            parsed = json.loads(boards_value)
            if isinstance(parsed, list):
                normalized = []
                for item in parsed:
                    if isinstance(item, dict) and "board_url" in item:
                        name = item.get("name") or item["board_url"].rsplit("/", 1)[-1].replace("-", " ").title()
                        normalized.append({"name": name, "board_url": item["board_url"]})
                    elif isinstance(item, str):
                        normalized.append(
                            {
                                "name": item.replace("-", " ").title(),
                                "board_url": f"https://boards.greenhouse.io/{item}",
                            }
                        )
                if normalized:
                    return normalized
        except Exception:
            pass

        boards: List[dict] = []
        for raw in boards_value.split(","):
            raw = raw.strip()
            if not raw:
                continue
            if "|" in raw:
                name, url = raw.split("|", 1)
                boards.append({"name": name.strip(), "board_url": url.strip()})
                continue

            boards.append(
                {
                    "name": raw.replace("-", " ").title(),
                    "board_url": f"https://boards.greenhouse.io/{raw}",
                }
            )

        return boards or [
            {"name": "GitLab", "board_url": "https://boards.greenhouse.io/gitlab"},
            {"name": "Zapier", "board_url": "https://boards.greenhouse.io/zapier"},
            {"name": "Datadog", "board_url": "https://boards.greenhouse.io/datadog"},
        ]

settings = Settings()
