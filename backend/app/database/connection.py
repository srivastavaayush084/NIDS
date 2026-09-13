import time
from typing import Optional, Dict, Any, Tuple
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.client import db_manager
from backend.app.database.indexes import create_database_indexes


async def connect_to_mongo() -> bool:
    """
    Initialize and connect the asynchronous MongoDB client.
    Reuses centralized connection pool across the entire application lifecycle.
    """
    try:
        masked_uri = settings.MONGODB_URI.split("@")[-1] if "@" in settings.MONGODB_URI else settings.MONGODB_URI
        logger.info(f"Connecting to MongoDB database '{settings.MONGODB_DATABASE}' at [{masked_uri}]...")

        db_manager.client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            tz_aware=True,
            minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
            maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
            serverSelectionTimeoutMS=settings.MONGODB_TIMEOUT_MS,
            connectTimeoutMS=settings.MONGODB_TIMEOUT_MS,
        )
        db_manager.db = db_manager.client[settings.MONGODB_DATABASE]

        # Test connectivity with ping
        start_time = time.perf_counter()
        await db_manager.client.admin.command("ping")
        latency_ms = (time.perf_counter() - start_time) * 1000

        db_manager.is_connected = True
        logger.info(f"MongoDB connection established in {latency_ms:.2f}ms. Database: '{settings.MONGODB_DATABASE}'")

        # Initialize collections indexes
        await create_database_indexes(db_manager.db)
        return True

    except Exception as e:
        db_manager.is_connected = False
        logger.warning(
            f"MongoDB connection could not be established: {str(e)}. "
            "Backend will operate in degraded mode (API endpoints active, DB operations cached or bypassed)."
        )
        return False


async def close_mongo_connection() -> None:
    """Gracefully close active MongoDB client connections on application shutdown."""
    if db_manager.client is not None:
        logger.info("Closing active MongoDB connection pool...")
        db_manager.client.close()
        db_manager.client = None
        db_manager.db = None
        db_manager.is_connected = False
        logger.info("MongoDB connection pool closed successfully.")


def get_database() -> Optional[AsyncIOMotorDatabase]:
    """Dependency / accessor for the active MongoDB database instance."""
    return db_manager.db


async def check_mongo_health() -> Tuple[bool, Optional[float], Dict[str, Any]]:
    """
    Perform an authoritative health probe on the MongoDB connection.
    Executes a real admin ping command to verify live database reachability.
    Returns: (is_healthy, latency_ms, details)
    """
    if db_manager.client is None or db_manager.db is None:
        try:
            db_manager.client = AsyncIOMotorClient(
                settings.MONGODB_URI,
                tz_aware=True,
                minPoolSize=settings.MONGODB_MIN_POOL_SIZE,
                maxPoolSize=settings.MONGODB_MAX_POOL_SIZE,
                serverSelectionTimeoutMS=settings.MONGODB_TIMEOUT_MS,
                connectTimeoutMS=settings.MONGODB_TIMEOUT_MS,
            )
            db_manager.db = db_manager.client[settings.MONGODB_DATABASE]
        except Exception as e:
            return False, None, {
                "status": "disconnected",
                "database": settings.MONGODB_DATABASE,
                "server_type": "unknown",
                "latency_ms": None,
                "connected": False,
                "error": f"Failed to initialize database client: {str(e)}",
            }

    try:
        start_time = time.perf_counter()
        await db_manager.client.admin.command("ping")
        latency_ms = round((time.perf_counter() - start_time) * 1000, 2)

        # Detect server topology / type
        server_type = "standalone"
        try:
            hello_res = await db_manager.client.admin.command("hello")
            if "setName" in hello_res:
                server_type = "replica_set"
            elif hello_res.get("msg") == "isdbgrid":
                server_type = "mongos"
        except Exception:
            pass

        db_manager.is_connected = True
        return True, latency_ms, {
            "status": "connected",
            "database": settings.MONGODB_DATABASE,
            "server_type": server_type,
            "latency_ms": latency_ms,
            "connected": True,
            "error": None,
        }
    except Exception as e:
        db_manager.is_connected = False
        return False, None, {
            "status": "disconnected",
            "database": settings.MONGODB_DATABASE,
            "server_type": "unknown",
            "latency_ms": None,
            "connected": False,
            "error": f"MongoDB is unreachable: {str(e)}",
        }
