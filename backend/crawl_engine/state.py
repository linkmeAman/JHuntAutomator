import json
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import declarative_base, Session
from datetime import datetime, timedelta

StateBase = declarative_base()


class SourceState(StateBase):
    __tablename__ = "source_state"
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String, unique=True, index=True)
    cursor_json = Column(Text, nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    consecutive_failures = Column(Integer, default=0)
    cooldown_until = Column(DateTime(timezone=True), nullable=True)


def ensure_state_table(engine):
    StateBase.metadata.create_all(bind=engine)


def load_state(db: Session, source_id: str) -> SourceState:
    state = db.query(SourceState).filter(SourceState.source_id == source_id).first()
    if not state:
        state = SourceState(source_id=source_id, cursor_json=None, consecutive_failures=0)
        db.add(state)
        db.commit()
        db.refresh(state)
    # Safety: if cooldown is unrealistically far in the future, reset it
    now = datetime.utcnow()
    if state.cooldown_until and state.cooldown_until > now + timedelta(hours=6):
        state.cooldown_until = None
        state.consecutive_failures = 0
        db.add(state)
        db.commit()
    return state


def update_state_success(db: Session, state: SourceState, cursor: dict | None):
    state.last_success_at = datetime.utcnow()
    state.consecutive_failures = 0
    state.cooldown_until = None
    state.cursor_json = json.dumps(cursor) if cursor else state.cursor_json
    db.add(state)
    db.commit()


def update_state_failure(db: Session, state: SourceState, cooldown_minutes: int = 15):
    state.consecutive_failures = (state.consecutive_failures or 0) + 1
    state.cooldown_until = datetime.utcnow() + timedelta(minutes=cooldown_minutes)
    db.add(state)
    db.commit()


def get_cursor(state: SourceState) -> dict:
    try:
        return json.loads(state.cursor_json) if state.cursor_json else {}
    except Exception:
        return {}


def set_cursor(state: SourceState, cursor: dict):
    state.cursor_json = json.dumps(cursor)
