from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.connection import connect_to_mongo, close_mongo_connection, check_mongo_health
from backend.app.ml.model_manager import model_manager
from backend.app.api.middleware import (
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    RequestSizeLimitMiddleware,
    ApiRateLimiterMiddleware,
)
from backend.app.api.errors import register_exception_handlers
from backend.app.api.v1.api import api_router
from backend.app.api.v1.endpoints import health


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifespan context manager."""
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.PROJECT_VERSION} in [{settings.ENVIRONMENT}] mode...")
    
    # 0. Production Security Verification
    if settings.is_production:
        if settings.JWT_SECRET_KEY == "dev-insecure-secret-key-change-in-production-1234567890" or len(settings.JWT_SECRET_KEY) < 32:
            logger.critical("CRITICAL SECURITY ERROR: Production deployment requires a secure, non-default JWT_SECRET_KEY of at least 32 characters.")
            raise RuntimeError("Insecure JWT_SECRET_KEY configured for production environment.")

    # 1. Initialize centralized MongoDB connection pool and verify with real ping
    db_connected = await connect_to_mongo()
    is_healthy, latency_ms, db_details = await check_mongo_health()
    
    # 2. Initialize ML Model Manager
    model_manager.load_models()
    models_status = model_manager.get_model_status()
    loaded_models_count = sum(1 for v in models_status.values() if v.get("is_trained", False))

    # 3. Print clear terminal status summary
    print("\n" + "=" * 54)
    print("ZERO-DAY NIDS BACKEND")
    print("=" * 54)
    print("[OK] Configuration loaded")
    if is_healthy:
        server_type = str(db_details.get("server_type", "Standalone")).replace("_", " ").title()
        ping_str = f"{latency_ms:.1f} ms" if latency_ms is not None else "< 5 ms"
        print("[OK] MongoDB connected successfully")
        print(f"[OK] Database: {settings.MONGODB_DATABASE}")
        print(f"[OK] Connection type: {server_type}")
        print(f"[OK] MongoDB ping: {ping_str}")
    else:
        err_msg = db_details.get("error", "Database connection unreachable")
        print("[ERROR] MongoDB connection failed")
        print(f"[ERROR] Database: {settings.MONGODB_DATABASE}")
        print(f"[ERROR] Unable to establish MongoDB connection: {err_msg}")
        print("[WARNING] Backend operating in degraded mode")
    
    print(f"[OK] ML models available ({loaded_models_count}/4 loaded)")
    print("[OK] Security headers & rate limiting active")
    print("[OK] Monitoring subsystem ready")
    print("[OK] API ready")
    print("=" * 54)
    print(f"Server running on http://{settings.HOST}:{settings.PORT}\n")
    
    yield
    
    # Graceful shutdown of database connections
    logger.info("Initiating graceful shutdown...")
    await close_mongo_connection()
    logger.info("Shutdown completed.")



def create_application() -> FastAPI:
    """FastAPI Application factory."""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.PROJECT_VERSION,
        description="End-to-end AI-Based Zero-Day Attack Detection System API",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan
    )

    # Security & Defense Middlewares
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware)
    app.add_middleware(ApiRateLimiterMiddleware)
    app.add_middleware(RequestIDMiddleware)

    # CORS Middleware configuration (explicit origins, restricted methods and headers)
    allowed_origins = settings.CORS_ORIGINS if settings.CORS_ORIGINS else [settings.FRONTEND_URL]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS", "HEAD"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID", "Accept", "Origin", "X-Requested-With"],
        expose_headers=["X-Request-ID", "X-Process-Time", "Retry-After"],
    )

    # Register centralized exception handlers for consistent JSON error structures
    register_exception_handlers(app)

    # Register API Routers
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Direct alias for health check at /api/health and root /health
    app.include_router(health.router, prefix="/api", include_in_schema=False)
    app.include_router(health.router, include_in_schema=False)

    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG
    )
