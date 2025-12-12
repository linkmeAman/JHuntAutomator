from sqlalchemy import create_engine, text, event
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from .config import settings

engine = create_engine(
    settings.DATABASE_URL, connect_args={"check_same_thread": False}
)

if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):  # pragma: no cover - side effect
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    import backend.models
    Base.metadata.create_all(bind=engine)
    ensure_schema()


def ensure_columns():
    """Add newly introduced columns in a backwards-compatible way."""
    with engine.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(jobs)"))
        columns = {row[1] for row in result}
        if "source_detail" not in columns:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN source_detail VARCHAR"))


def ensure_indexes():
    """Create helpful indexes if they do not already exist."""
    with engine.connect() as conn:
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_job_hash ON jobs(job_hash);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_jobs_relevance_score ON jobs(relevance_score);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_jobs_applied ON jobs(applied);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_crawl_runs_started_at ON crawl_runs(started_at);"))


def ensure_schema():
    ensure_columns()
    ensure_indexes()
