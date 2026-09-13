from typing import Optional
from pymongo import IndexModel, ASCENDING, DESCENDING
from motor.motor_asyncio import AsyncIOMotorDatabase
from backend.app.core.logging import logger
from backend.app.database.collections import (
    USERS_COLLECTION,
    NETWORK_LOGS_COLLECTION,
    DETECTION_RESULTS_COLLECTION,
    ALERTS_COLLECTION,
    SYSTEM_EVENTS_COLLECTION,
    AUDIT_LOGS_COLLECTION,
)


async def create_database_indexes(db: Optional[AsyncIOMotorDatabase]) -> None:
    """
    Asynchronously create optimized database indexes across all security collections.
    Gracefully handles existing indexes or indexing failures.
    """
    if db is None:
        logger.warning("Skipping index creation: database handle is None.")
        return

    try:
        logger.info("Verifying and creating MongoDB database indexes...")

        # 1. Users Indexes
        user_indexes = [
            IndexModel([("username", ASCENDING)], unique=True, name="idx_users_username_unique"),
            IndexModel([("email", ASCENDING)], unique=True, name="idx_users_email_unique"),
            IndexModel([("role", ASCENDING)], name="idx_users_role"),
            IndexModel([("is_active", ASCENDING)], name="idx_users_is_active"),
            IndexModel([("created_at", DESCENDING)], name="idx_users_created_at"),
        ]
        await db[USERS_COLLECTION].create_indexes(user_indexes)

        # 2. Network Logs Indexes
        network_log_indexes = [
            IndexModel([("timestamp", DESCENDING)], name="idx_netlog_timestamp"),
            IndexModel([("source_ip", ASCENDING)], name="idx_netlog_source_ip"),
            IndexModel([("destination_ip", ASCENDING)], name="idx_netlog_dst_ip"),
            IndexModel([("protocol", ASCENDING)], name="idx_netlog_protocol"),
            IndexModel(
                [("source_ip", ASCENDING), ("destination_ip", ASCENDING), ("timestamp", DESCENDING)],
                name="idx_netlog_flow_compound"
            ),
        ]
        await db[NETWORK_LOGS_COLLECTION].create_indexes(network_log_indexes)

        # 3. Detection Results Indexes
        detection_indexes = [
            IndexModel([("timestamp", DESCENDING)], name="idx_det_timestamp"),
            IndexModel([("model_name", ASCENDING)], name="idx_det_model_name"),
            IndexModel([("severity", ASCENDING)], name="idx_det_severity"),
            IndexModel([("anomaly_score", DESCENDING)], name="idx_det_anomaly_score"),
            IndexModel([("network_log_id", ASCENDING)], name="idx_det_netlog_id"),
        ]
        await db[DETECTION_RESULTS_COLLECTION].create_indexes(detection_indexes)

        # 4. Security Alerts Indexes
        alert_indexes = [
            IndexModel([("alert_id", ASCENDING)], unique=True, name="idx_alert_id_unique"),
            IndexModel([("timestamp", DESCENDING)], name="idx_alert_timestamp"),
            IndexModel([("severity", ASCENDING)], name="idx_alert_severity"),
            IndexModel([("priority", ASCENDING)], name="idx_alert_priority"),
            IndexModel([("status", ASCENDING)], name="idx_alert_status"),
            IndexModel([("risk_score", DESCENDING)], name="idx_alert_risk_score"),
            IndexModel([("deduplication.fingerprint", ASCENDING)], name="idx_alert_dedup_fingerprint"),
            IndexModel([("deduplication.last_seen", DESCENDING)], name="idx_alert_dedup_last_seen"),
            IndexModel([("source.ip", ASCENDING)], name="idx_alert_source_ip"),
            IndexModel([("destination.ip", ASCENDING)], name="idx_alert_dest_ip"),
            IndexModel([("created_at", DESCENDING)], name="idx_alert_created_at"),
        ]
        await db[ALERTS_COLLECTION].create_indexes(alert_indexes)

        # 5. System Events Indexes
        system_event_indexes = [
            IndexModel([("timestamp", DESCENDING)], name="idx_event_timestamp"),
            IndexModel([("event_type", ASCENDING)], name="idx_event_type"),
            IndexModel([("level", ASCENDING)], name="idx_event_level"),
            IndexModel([("component", ASCENDING)], name="idx_event_component"),
        ]
        await db[SYSTEM_EVENTS_COLLECTION].create_indexes(system_event_indexes)

        # 6. Audit Logs Indexes
        audit_indexes = [
            IndexModel([("timestamp", DESCENDING)], name="idx_audit_timestamp"),
            IndexModel([("user_id", ASCENDING)], name="idx_audit_user_id"),
            IndexModel([("action", ASCENDING)], name="idx_audit_action"),
            IndexModel([("resource", ASCENDING)], name="idx_audit_resource"),
        ]
        await db[AUDIT_LOGS_COLLECTION].create_indexes(audit_indexes)

        logger.info("Successfully established indexes for all 6 database collections.")

    except Exception as e:
        logger.warning(f"Database index creation completed with warning: {str(e)}")
