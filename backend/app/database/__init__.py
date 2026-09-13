from backend.app.database.collections import (
    USERS_COLLECTION,
    NETWORK_LOGS_COLLECTION,
    DETECTION_RESULTS_COLLECTION,
    ALERTS_COLLECTION,
    SYSTEM_EVENTS_COLLECTION,
    AUDIT_LOGS_COLLECTION,
    ALL_COLLECTIONS,
)
from backend.app.database.client import db_manager, MongoClientManager
from backend.app.database.connection import (
    connect_to_mongo,
    close_mongo_connection,
    get_database,
    check_mongo_health,
)
from backend.app.database.indexes import create_database_indexes
from backend.app.database.repository import (
    BaseRepository,
    NetworkLogRepository,
    DetectionResultRepository,
    AlertRepository,
    SystemEventRepository,
    AuditLogRepository,
    UserRepository,
)

__all__ = [
    "USERS_COLLECTION",
    "NETWORK_LOGS_COLLECTION",
    "DETECTION_RESULTS_COLLECTION",
    "ALERTS_COLLECTION",
    "SYSTEM_EVENTS_COLLECTION",
    "AUDIT_LOGS_COLLECTION",
    "ALL_COLLECTIONS",
    "db_manager",
    "MongoClientManager",
    "connect_to_mongo",
    "close_mongo_connection",
    "get_database",
    "check_mongo_health",
    "create_database_indexes",
    "BaseRepository",
    "NetworkLogRepository",
    "DetectionResultRepository",
    "AlertRepository",
    "SystemEventRepository",
    "AuditLogRepository",
    "UserRepository",
]
