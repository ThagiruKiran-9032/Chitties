from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,      # Tests connection liveness before checking out from pool
    pool_size=10,            # Maintained active pool connections
    max_overflow=20,         # Maximum burst overflow connections under peak load
    echo=settings.DEBUG,     # Echo SQL queries in development
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that yields a database session per request
    and guarantees safe closure upon request completion.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
