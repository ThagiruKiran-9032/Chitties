from unittest.mock import MagicMock
from fastapi import status
from sqlalchemy import text
from app.db.session import get_db
from app.main import app


def test_read_root(client):
    """Test root endpoint returns API information."""
    response = client.get("/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["service"] == "Chitties"
    assert data["status"] == "online"
    assert "version" in data
    assert response.headers.get("x-content-type-options") == "nosniff"
    assert response.headers.get("x-frame-options") == "DENY"


def test_health_check_success(client):
    """Test /health endpoint verifies database connectivity and latency."""
    response = client.get("/health")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "database_latency_ms" in data
    assert isinstance(data["database_latency_ms"], (int, float))
    assert data["database_latency_ms"] >= 0


def test_db_direct_connectivity(db_session):
    """Test direct database connectivity using isolated test session."""
    result = db_session.execute(text("SELECT 1 AS probe")).scalar()
    assert result == 1


def test_health_check_db_failure(client):
    """Test /health handles database failures gracefully with HTTP 503."""
    mock_db = MagicMock()
    mock_db.execute.side_effect = Exception("Simulated DB connection timeout")

    def override_broken_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_broken_db
    try:
        response = client.get("/health")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
        assert "Simulated DB connection timeout" in data["error"]
    finally:
        app.dependency_overrides.clear()
