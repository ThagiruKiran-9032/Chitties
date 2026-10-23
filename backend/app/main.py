import time
from fastapi import FastAPI, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import get_db
from app.routes.auth import router as auth_router
from app.routes.organizations import router as organizations_router
from app.routes.branches import router as branches_router
from app.routes.members import router as members_router
from app.routes.chit_schemes import router as schemes_router
from app.routes.chit_groups import router as groups_router
from app.routes.auctions import router as auctions_router
from app.routes.installments import router as installments_router
from app.routes.payouts import router as payouts_router
from app.routes.compliance import router as compliance_router
from app.routes.audit_logs import router as audit_logs_router
from app.dependencies.auth import require_roles
from app.models.user import User, UserRole


from app.middleware.security import SecurityHeadersMiddleware, RateLimitMiddleware

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Chitties - Enterprise Multi-Tenant Chit Fund Management API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enterprise Security Hardening Middlewares
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=200, window_seconds=60)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["General"])
def read_root():
    """Root endpoint verifying API is responsive."""
    return {
        "service": settings.PROJECT_NAME,
        "version": "0.1.0",
        "environment": settings.ENVIRONMENT,
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health", tags=["Health"])
def health_check(db: Session = Depends(get_db)):
    """
    Deep health check verifying backend execution and PostgreSQL connectivity.
    Measures database query roundtrip latency.
    """
    start_time = time.perf_counter()
    try:
        # Execute active probe against PostgreSQL
        db.execute(text("SELECT 1"))
        latency_ms = (time.perf_counter() - start_time) * 1000
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": "0.1.0",
            "database": "connected",
            "database_latency_ms": round(latency_ms, 2),
        }
    except Exception as exc:
        latency_ms = (time.perf_counter() - start_time) * 1000
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "unhealthy",
                "service": settings.PROJECT_NAME,
                "database": "disconnected",
                "error": str(exc),
                "database_latency_ms": round(latency_ms, 2),
            },
        )


# Mount API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(organizations_router, prefix=settings.API_V1_STR)
app.include_router(branches_router, prefix=settings.API_V1_STR)
app.include_router(members_router, prefix=settings.API_V1_STR)
app.include_router(schemes_router, prefix=settings.API_V1_STR)
app.include_router(groups_router, prefix=settings.API_V1_STR)
app.include_router(auctions_router, prefix=settings.API_V1_STR)
app.include_router(installments_router, prefix=settings.API_V1_STR)
app.include_router(payouts_router, prefix=settings.API_V1_STR)
app.include_router(compliance_router, prefix=settings.API_V1_STR)
app.include_router(audit_logs_router, prefix=settings.API_V1_STR)


@app.get(f"{settings.API_V1_STR}/test/admin-only", tags=["Testing"])
def admin_only_test(current_user: User = Depends(require_roles([UserRole.ORG_ADMIN, UserRole.SUPER_ADMIN]))):
    """Protected test route to verify RBAC enforcement."""
    return {"message": "Admin authorization granted", "user_id": str(current_user.id), "role": current_user.role.value}
