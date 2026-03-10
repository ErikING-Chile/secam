"""Secam Cloud API - Main FastAPI Application."""
from contextlib import asynccontextmanager
from datetime import datetime

from .runtime import validate_runtime

validate_runtime()

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import redis

from .config import settings
from .db import engine, Base, get_db
from .models import Tenant, User  # Import models to register them
from .routers import auth, cameras, events, persons, edge, admin, streaming, webrtc

# Import models for Alembic auto-detection
from . import models


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    print(f"🚀 Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    print(f"📦 Environment: {settings.ENVIRONMENT}")
    
    # Create database tables
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")
    
    # Check Redis connection
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        print("✅ Redis connected")
    except Exception as e:
        print(f"⚠️  Redis connection failed: {e}")
    
    yield
    
    # Shutdown
    print("👋 Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Secam - Smart Security Camera SaaS API",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle uncaught exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": "Internal server error",
            "path": str(request.url.path)
        }
    )


# Include routers
app.include_router(auth.router, prefix="/api/v1")
app.include_router(cameras.router, prefix="/api/v1")
app.include_router(streaming.router, prefix="/api/v1")
app.include_router(webrtc.router, prefix="/api/v1")
app.include_router(events.router, prefix="/api/v1")
app.include_router(persons.router, prefix="/api/v1")
app.include_router(edge.router, prefix="/api/v1")
app.include_router(admin.router, prefix="/api/v1")


# Health check endpoint
@app.get("/healthz", tags=["Health"])
async def health_check():
    """
    Health check endpoint for monitoring and load balancers.
    """
    health_status = {
        "status": "healthy",
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "database": "unknown",
        "redis": "unknown",
        "timestamp": datetime.utcnow()
    }
    
    # Check database
    try:
        db = next(get_db())
        db.execute("SELECT 1")
        health_status["database"] = "connected"
    except Exception as e:
        health_status["database"] = f"error: {str(e)}"
        health_status["status"] = "unhealthy"
    
    # Check Redis
    try:
        r = redis.from_url(settings.REDIS_URL)
        r.ping()
        health_status["redis"] = "connected"
    except Exception as e:
        health_status["redis"] = f"error: {str(e)}"
        health_status["status"] = "degraded"
    
    status_code = (
        status.HTTP_200_OK if health_status["status"] == "healthy"
        else status.HTTP_503_SERVICE_UNAVAILABLE
    )
    
    return JSONResponse(
        status_code=status_code,
        content=health_status
    )


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/healthz"
    }


# Placeholder endpoints for future phases
@app.get("/api/v1/cameras", tags=["Cameras"], status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def list_cameras():
    """List cameras (Phase 2)."""
    return {"detail": "Not implemented yet - Phase 2"}


@app.get("/api/v1/persons", tags=["Persons"], status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def list_persons():
    """List registered persons (Phase 4)."""
    return {"detail": "Not implemented yet - Phase 4"}


@app.get("/api/v1/events", tags=["Events"], status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def list_events():
    """List events (Phase 3)."""
    return {"detail": "Not implemented yet - Phase 3"}
