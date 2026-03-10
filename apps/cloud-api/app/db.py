"""Database connection and session management."""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from .config import settings


def validate_database_url(database_url: str) -> str:
    """Reject legacy PostgreSQL URLs that do not match the runtime contract."""
    if database_url.startswith(("postgresql://", "postgres://")):
        raise RuntimeError(
            "DATABASE_URL must use `postgresql+psycopg://` to match the checked-in "
            "SQLAlchemy 2 + psycopg runtime contract. Update your local .env or "
            "docker-compose override before starting apps/cloud-api."
        )
    return database_url


# Create database engine
engine = create_engine(
    validate_database_url(settings.DATABASE_URL),
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
)

# Session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for models
Base = declarative_base()


def get_db():
    """Dependency for getting database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
