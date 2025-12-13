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


def ensure_columns(engine_to_use=None):
    """Add newly introduced columns in a backwards-compatible way."""
    eng = engine_to_use or engine
    with eng.connect() as conn:
        result = conn.execute(text("PRAGMA table_info(jobs)"))
        columns = {row[1] for row in result}
        if "source_detail" not in columns:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN source_detail VARCHAR"))
        if "remote" not in columns:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN remote BOOLEAN DEFAULT 0"))
        if "source_meta" not in columns:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN source_meta TEXT"))
        if "job_key" not in columns:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN job_key VARCHAR"))
        if "job_fingerprint" not in columns:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN job_fingerprint VARCHAR"))
        if "last_seen_at" not in columns:
            conn.execute(text("ALTER TABLE jobs ADD COLUMN last_seen_at DATETIME"))
        result_runs = conn.execute(text("PRAGMA table_info(crawl_runs)"))
        run_cols = {row[1] for row in result_runs}
        if "source_metrics" not in run_cols:
            conn.execute(text("ALTER TABLE crawl_runs ADD COLUMN source_metrics TEXT"))


def ensure_indexes(engine_to_use=None):
    """Create helpful indexes if they do not already exist."""
    eng = engine_to_use or engine
    with eng.connect() as conn:
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_job_hash ON jobs(job_hash);"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_job_key ON jobs(job_key);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_jobs_relevance_score ON jobs(relevance_score);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_jobs_created_at ON jobs(created_at);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_jobs_applied ON jobs(applied);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_jobs_source ON jobs(source);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_crawl_runs_started_at ON crawl_runs(started_at);"))


def ensure_schema(engine_to_use=None):
    ensure_columns(engine_to_use)
    ensure_indexes(engine_to_use)
    from backend.crawl_engine.state import ensure_state_table
    ensure_state_table(engine_to_use or engine)
