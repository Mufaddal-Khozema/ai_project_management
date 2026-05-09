from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from config import get_settings

def _create_engine():
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        pool_size=10,
        max_overflow=20,
        echo=not settings.is_production,
    )


# Lazily initialised so tests can import app modules without a live DB
_engine = None
_session_factory = None


def get_engine():
    global _engine
    if _engine is None:
        _engine = _create_engine()
    return _engine


def _get_session_factory():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_factory


# Backwards-compatible alias used by app/__init__.py
class _LazySessionLocal:
    def __call__(self):
        return _get_session_factory()()


SessionLocal = _LazySessionLocal()


class Base(DeclarativeBase):
    """Shared declarative base for all ORM models."""
    pass


def get_db():
    """
    Yield a SQLAlchemy session and guarantee cleanup.

    Usage (inside a Falcon resource)::

        db: Session = next(get_db())
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

