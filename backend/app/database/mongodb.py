"""
Backward-compatibility wrapper for MongoDB connection and database utilities.
Delegates to modular backend.app.database components.
"""
from backend.app.database.client import db_manager as mongodb
from backend.app.database.connection import (
    connect_to_mongo,
    close_mongo_connection,
    get_database,
    check_mongo_health,
)

__all__ = [
    "mongodb",
    "connect_to_mongo",
    "close_mongo_connection",
    "get_database",
    "check_mongo_health",
]
