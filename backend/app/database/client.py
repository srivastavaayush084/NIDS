from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


class MongoClientManager:
    """Singleton MongoDB client and database manager."""

    _instance: Optional["MongoClientManager"] = None

    def __new__(cls) -> "MongoClientManager":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.client = None
            cls._instance.db = None
            cls._instance.is_connected = False
        return cls._instance

    @property
    def is_active(self) -> bool:
        return self.client is not None and self.db is not None and self.is_connected


db_manager = MongoClientManager()
