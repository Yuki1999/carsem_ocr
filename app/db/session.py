from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import AppSettings, get_settings


def create_engine_from_settings(settings: AppSettings | None = None) -> Engine:
    resolved_settings = settings or get_settings()
    return create_engine(resolved_settings.database_url, pool_pre_ping=True)


def create_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    resolved_engine = engine or create_engine_from_settings()
    return sessionmaker(bind=resolved_engine, autoflush=False, expire_on_commit=False)


_ENGINE: Engine | None = None
_SESSION_FACTORY: sessionmaker[Session] | None = None


def get_session_factory() -> sessionmaker[Session]:
    global _ENGINE, _SESSION_FACTORY
    if _SESSION_FACTORY is None:
        _ENGINE = create_engine_from_settings()
        _SESSION_FACTORY = create_session_factory(_ENGINE)
    return _SESSION_FACTORY


def get_db_session():
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def session_scope(session_factory: sessionmaker[Session]) -> Iterator[Session]:
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def set_current_tenant(session: Session, tenant_id: str) -> None:
    session.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )
