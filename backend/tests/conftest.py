import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app as fastapi_app
from app.core.config import settings
from app.db.session import get_db
from app.db.base import Base
import app.models  # Ensure all models are registered on Base.metadata


# Test database engine
test_db_url = settings.TEST_DATABASE_URL or settings.DATABASE_URL
test_engine = create_engine(test_db_url, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="session", autouse=True)
def db_engine():
    """Ensure test tables exist and yield engine for test session."""
    Base.metadata.create_all(bind=test_engine)
    yield test_engine


@pytest.fixture(scope="function")
def db_session():
    """Provide isolated database session per test function."""
    connection = test_engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    if transaction.is_active:
        transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def client(db_session):
    """
    TestClient with overridden get_db dependency to point to the test session.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as test_client:
        yield test_client
    fastapi_app.dependency_overrides.clear()
