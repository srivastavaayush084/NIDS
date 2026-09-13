import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from backend.app.database.connection import get_database
from backend.app.database.collections import (
    USERS_COLLECTION,
    NETWORK_LOGS_COLLECTION,
    DETECTION_RESULTS_COLLECTION,
    ALERTS_COLLECTION,
    SYSTEM_EVENTS_COLLECTION,
    AUDIT_LOGS_COLLECTION,
)


def _ensure_utc_datetimes(val: Any) -> Any:
    """Ensure any naive datetime has tzinfo=timezone.utc, recursing through dicts and lists."""
    if isinstance(val, datetime):
        if val.tzinfo is None:
            return val.replace(tzinfo=timezone.utc)
        return val
    elif isinstance(val, dict):
        return {k: _ensure_utc_datetimes(v) for k, v in val.items()}
    elif isinstance(val, list):
        return [_ensure_utc_datetimes(v) for v in val]
    return val


class BaseRepository:
    """Generic async MongoDB repository providing standard CRUD, pagination, and query operations."""
    
    def __init__(self, collection_name: str, db: Optional[AsyncIOMotorDatabase] = None):
        self.collection_name = collection_name
        self._db = db

    @property
    def db(self) -> Optional[AsyncIOMotorDatabase]:
        return self._db or get_database()

    @property
    def collection(self):
        database = self.db
        if database is not None:
            return database[self.collection_name]
        return None

    async def find_one(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Retrieve single document matching filter."""
        if self.collection is None:
            return None
        doc = await self.collection.find_one(query)
        return _ensure_utc_datetimes(doc) if doc else None

    async def find_many(
        self,
        query: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        skip: int = 0,
        sort: Optional[List[Tuple[str, int]]] = None
    ) -> List[Dict[str, Any]]:
        """Retrieve multiple documents with optional pagination and sort."""
        if self.collection is None:
            return []
        filter_query = query or {}
        clamped_limit = max(1, min(limit, 100))
        clamped_skip = max(0, skip)
        cursor = self.collection.find(filter_query).skip(clamped_skip).limit(clamped_limit)
        if sort:
            cursor = cursor.sort(sort)
        docs = await cursor.to_list(length=clamped_limit)
        return [_ensure_utc_datetimes(d) for d in docs]

    async def insert_one(self, document: Dict[str, Any]) -> Optional[str]:
        """Insert single document and return its hex ID string."""
        if self.collection is None:
            return None
        result = await self.collection.insert_one(document)
        return str(result.inserted_id)

    async def insert_many(self, documents: List[Dict[str, Any]]) -> List[str]:
        """Bulk insert multiple documents."""
        if self.collection is None or not documents:
            return []
        result = await self.collection.insert_many(documents)
        return [str(idx) for idx in result.inserted_ids]

    async def update_one(
        self, query: Dict[str, Any], update_data: Dict[str, Any], upsert: bool = False
    ) -> bool:
        """Update a single document."""
        if self.collection is None:
            return False
        result = await self.collection.update_one(query, {"$set": update_data}, upsert=upsert)
        return result.modified_count > 0 or (upsert and result.upserted_id is not None)

    async def delete_one(self, query: Dict[str, Any]) -> bool:
        """Delete single document."""
        if self.collection is None:
            return False
        result = await self.collection.delete_one(query)
        return result.deleted_count > 0

    async def count(self, query: Optional[Dict[str, Any]] = None) -> int:
        """Count total matching documents in collection."""
        if self.collection is None:
            return 0
        return await self.collection.count_documents(query or {})


class NetworkLogRepository(BaseRepository):
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        super().__init__(NETWORK_LOGS_COLLECTION, db)


class DetectionResultRepository(BaseRepository):
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        super().__init__(DETECTION_RESULTS_COLLECTION, db)

    async def find_by_detection_id(self, detection_id: str) -> Optional[Dict[str, Any]]:
        """Find a detection result document by detection_id or _id."""
        doc = await self.find_one({"detection_id": detection_id})
        if not doc:
            doc = await self.find_one({"_id": detection_id})
        return doc

    async def query_detections(
        self,
        query: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        skip: int = 0,
        sort: Optional[List[Tuple[str, int]]] = None,
    ) -> List[Dict[str, Any]]:
        """Query detection history with pagination and sorting."""
        sort_order = sort or [("timestamp", -1)]
        return await self.find_many(query or {}, limit=limit, skip=skip, sort=sort_order)

    async def get_detection_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Aggregate total detections, anomalies, and average risk score."""
        match_stage: Dict[str, Any] = {}
        if start_time or end_time:
            time_filter: Dict[str, Any] = {}
            if start_time:
                time_filter["$gte"] = start_time
            if end_time:
                time_filter["$lte"] = end_time
            match_stage["timestamp"] = time_filter

        if self.collection is None:
            return {"total": 0, "anomalies": 0, "avg_risk_score": 0.0, "last_timestamp": None}

        try:
            pipeline = [
                {"$match": match_stage} if match_stage else {"$match": {}},
                {
                    "$group": {
                        "_id": None,
                        "total": {"$sum": 1},
                        "anomalies": {
                            "$sum": {
                                "$cond": [
                                    {"$or": [{"$eq": ["$is_anomaly", True]}, {"$eq": ["$is_zero_day_suspect", True]}]},
                                    1,
                                    0,
                                ]
                            }
                        },
                        "avg_risk_score": {"$avg": "$risk_score"},
                        "last_timestamp": {"$max": "$timestamp"},
                    }
                },
            ]
            cursor = self.collection.aggregate(pipeline)
            results = await cursor.to_list(length=1)
            if results:
                res = results[0]
                return {
                    "total": res.get("total", 0),
                    "anomalies": res.get("anomalies", 0),
                    "avg_risk_score": round(float(res.get("avg_risk_score", 0.0) or 0.0), 2),
                    "last_timestamp": _ensure_utc_datetimes(res.get("last_timestamp")),
                }
        except Exception:
            pass

        # Fallback to simple count
        total = await self.count(match_stage)
        anomalies = await self.count({**match_stage, "$or": [{"is_anomaly": True}, {"is_zero_day_suspect": True}]})
        return {"total": total, "anomalies": anomalies, "avg_risk_score": 0.0, "last_timestamp": None}


class AlertRepository(BaseRepository):
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        super().__init__(ALERTS_COLLECTION, db)

    async def find_by_alert_id(self, alert_id: str) -> Optional[Dict[str, Any]]:
        """Find an alert document by its unique alert_id (e.g. alt-1234567890ab)."""
        return await self.find_one({"alert_id": alert_id})

    async def find_active_by_fingerprint(self, fingerprint: str) -> Optional[Dict[str, Any]]:
        """
        Find an active (OPEN or ACKNOWLEDGED) alert matching the given deduplication fingerprint.
        """
        query = {
            "deduplication.fingerprint": fingerprint,
            "status": {"$in": ["OPEN", "ACKNOWLEDGED", "new", "acknowledged"]},
        }
        # Sort by last_seen descending to get the most recent active match
        results = await self.find_many(query, limit=1, sort=[("deduplication.last_seen", -1), ("created_at", -1)])
        return results[0] if results else None

    async def increment_occurrence(
        self,
        alert_id: str,
        timestamp: Optional[datetime] = None,
        latest_risk_score: Optional[float] = None,
    ) -> bool:
        """
        Increment the occurrence count of an existing alert and update its last_seen timestamp.
        """
        if self.collection is None:
            return False
        
        now = timestamp or datetime.now(timezone.utc)
        update_doc: Dict[str, Any] = {
            "$inc": {"deduplication.occurrence_count": 1},
            "$set": {
                "deduplication.last_seen": now,
                "updated_at": now,
            }
        }
        if latest_risk_score is not None:
            # If the new event has a higher risk score, optionally elevate the recorded score
            update_doc["$max"] = {"risk_score": latest_risk_score}

        result = await self.collection.update_one({"alert_id": alert_id}, update_doc)
        return result.modified_count > 0

    async def update_status(
        self,
        alert_id: str,
        status: str,
        assigned_to: Optional[str] = None,
        resolution_note: Optional[str] = None,
        dismissal_reason: Optional[str] = None,
    ) -> bool:
        """Update the lifecycle status and triage notes of a security alert."""
        if self.collection is None:
            return False
        
        now = datetime.now(timezone.utc)
        set_fields: Dict[str, Any] = {
            "status": status,
            "updated_at": now,
        }
        if assigned_to is not None:
            set_fields["assigned_to"] = assigned_to
        if resolution_note is not None:
            set_fields["resolution_note"] = resolution_note
        if dismissal_reason is not None:
            set_fields["dismissal_reason"] = dismissal_reason

        result = await self.collection.update_one({"alert_id": alert_id}, {"$set": set_fields})
        return result.modified_count > 0

    async def get_alert_stats(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """Aggregate security alerts by status, severity, and flow endpoints."""
        match_stage: Dict[str, Any] = {}
        if start_time or end_time:
            time_filter: Dict[str, Any] = {}
            if start_time:
                time_filter["$gte"] = start_time
            if end_time:
                time_filter["$lte"] = end_time
            match_stage["created_at"] = time_filter

        base_stats = {
            "total": 0,
            "status_counts": {"OPEN": 0, "ACKNOWLEDGED": 0, "RESOLVED": 0, "DISMISSED": 0},
            "severity_counts": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
            "avg_risk_score": 0.0,
            "top_source_ips": [],
            "top_destination_ips": [],
        }

        if self.collection is None:
            return base_stats

        try:
            # 1. Status and Severity counts
            pipeline = [
                {"$match": match_stage} if match_stage else {"$match": {}},
                {
                    "$facet": {
                        "status_agg": [
                            {"$group": {"_id": "$status", "count": {"$sum": 1}}},
                        ],
                        "severity_agg": [
                            {"$group": {"_id": "$severity", "count": {"$sum": 1}}},
                        ],
                        "general_agg": [
                            {
                                "$group": {
                                    "_id": None,
                                    "total": {"$sum": 1},
                                    "avg_risk_score": {"$avg": "$risk_score"},
                                }
                            }
                        ],
                        "top_sources": [
                            {"$match": {"source.ip": {"$ne": None, "$ne": ""}}},
                            {"$group": {"_id": "$source.ip", "count": {"$sum": 1}}},
                            {"$sort": {"count": -1}},
                            {"$limit": 5},
                        ],
                        "top_destinations": [
                            {"$match": {"destination.ip": {"$ne": None, "$ne": ""}}},
                            {"$group": {"_id": "$destination.ip", "count": {"$sum": 1}}},
                            {"$sort": {"count": -1}},
                            {"$limit": 5},
                        ],
                    }
                },
            ]
            cursor = self.collection.aggregate(pipeline)
            results = await cursor.to_list(length=1)
            if results:
                facet_res = results[0]
                gen = facet_res.get("general_agg", [])
                if gen:
                    base_stats["total"] = gen[0].get("total", 0)
                    base_stats["avg_risk_score"] = round(float(gen[0].get("avg_risk_score", 0.0) or 0.0), 2)

                for s_item in facet_res.get("status_agg", []):
                    st = str(s_item.get("_id", "")).upper()
                    if st in base_stats["status_counts"]:
                        base_stats["status_counts"][st] = s_item.get("count", 0)

                for sev_item in facet_res.get("severity_agg", []):
                    sev = str(sev_item.get("_id", "")).upper()
                    if sev in base_stats["severity_counts"]:
                        base_stats["severity_counts"][sev] = sev_item.get("count", 0)

                base_stats["top_source_ips"] = [
                    {"ip": item["_id"], "count": item["count"]} for item in facet_res.get("top_sources", [])
                ]
                base_stats["top_destination_ips"] = [
                    {"ip": item["_id"], "count": item["count"]} for item in facet_res.get("top_destinations", [])
                ]
                return base_stats
        except Exception:
            pass

        # Fallback count
        base_stats["total"] = await self.count(match_stage)
        return base_stats


class SystemEventRepository(BaseRepository):
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        super().__init__(SYSTEM_EVENTS_COLLECTION, db)


class AuditLogRepository(BaseRepository):
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        super().__init__(AUDIT_LOGS_COLLECTION, db)


class UserRepository(BaseRepository):
    def __init__(self, db: Optional[AsyncIOMotorDatabase] = None):
        super().__init__(USERS_COLLECTION, db)

    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Find a user by _id hex string or user_id field."""
        from bson import ObjectId
        if self.collection is None:
            return None
        or_clauses: List[Dict[str, Any]] = [{"user_id": user_id}, {"_id": user_id}]
        try:
            or_clauses.append({"_id": ObjectId(user_id)})
        except Exception:
            pass
        return await self.find_one({"$or": or_clauses})

    async def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Find a user by case-insensitive username with sanitized regex."""
        safe_username = re.escape(username.strip())
        return await self.find_one({"username": {"$regex": f"^{safe_username}$", "$options": "i"}})

    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """Find a user by case-insensitive email address with sanitized regex."""
        safe_email = re.escape(email.strip())
        return await self.find_one({"email": {"$regex": f"^{safe_email}$", "$options": "i"}})

    async def get_user_by_identifier(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Find user by either username or email."""
        clean_id = identifier.strip()
        user = await self.get_user_by_username(clean_id)
        if not user:
            user = await self.get_user_by_email(clean_id)
        return user

    async def create_user(self, user_data: Dict[str, Any]) -> Optional[str]:
        """Insert a new user document."""
        return await self.insert_one(user_data)

    async def update_user(self, user_id: str, update_fields: Dict[str, Any]) -> bool:
        """Update user fields by ID."""
        from bson import ObjectId
        if self.collection is None:
            return False
        now = datetime.now(timezone.utc)
        update_fields["updated_at"] = now
        
        or_clauses: List[Dict[str, Any]] = [{"user_id": user_id}, {"_id": user_id}]
        try:
            or_clauses.append({"_id": ObjectId(user_id)})
        except Exception:
            pass
        
        result = await self.collection.update_one({"$or": or_clauses}, {"$set": update_fields})
        return result.matched_count > 0 or result.modified_count > 0

    async def update_last_login(self, user_id: str, timestamp: Optional[datetime] = None) -> bool:
        """Record the latest successful login timestamp."""
        now = timestamp or datetime.now(timezone.utc)
        return await self.update_user(user_id, {"last_login_at": now})

    async def deactivate_user(self, user_id: str) -> bool:
        """Set user active status to False."""
        return await self.update_user(user_id, {"is_active": False})

    async def count_active_admins(self) -> int:
        """Count how many active administrator accounts exist."""
        return await self.count({"role": "admin", "is_active": True})

    async def list_users(
        self,
        limit: int = 100,
        skip: int = 0,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve paginated list of users with optional filtering."""
        query: Dict[str, Any] = {}
        if role:
            query["role"] = role.strip().lower()
        if is_active is not None:
            query["is_active"] = is_active
        return await self.find_many(query, limit=limit, skip=skip, sort=[("created_at", -1)])

