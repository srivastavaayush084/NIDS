import hashlib
from datetime import datetime, timezone
from typing import Optional, Union
from backend.app.core.config import settings
from backend.app.core.logging import logger


class AlertDeduplicator:
    """
    Manages deterministic security alert fingerprinting and temporal cooldown deduplication
    to prevent alarm floods and alert fatigue in Security Operations Centers (SOC).
    """

    def __init__(self, window_seconds: Optional[int] = None):
        self.window_seconds = window_seconds if window_seconds is not None else settings.ALERT_DEDUP_WINDOW_SECONDS

    @staticmethod
    def generate_fingerprint(
        source_ip: Optional[str] = None,
        destination_ip: Optional[str] = None,
        source_port: Optional[Union[int, str]] = None,
        destination_port: Optional[Union[int, str]] = None,
        protocol: Optional[str] = "TCP",
        alert_type: str = "network_anomaly",
    ) -> str:
        """
        Generate a deterministic SHA-256 fingerprint identifying a network security incident stream.
        Explicitly excludes instantaneous timestamps to guarantee identical hashes for recurring flows.
        """
        src_ip_clean = str(source_ip or "0.0.0.0").strip().lower()
        dst_ip_clean = str(destination_ip or "0.0.0.0").strip().lower()
        src_port_clean = str(source_port or "0").strip()
        dst_port_clean = str(destination_port or "0").strip()
        proto_clean = str(protocol or "tcp").strip().upper()
        type_clean = str(alert_type or "network_anomaly").strip().lower()

        raw_key = f"{src_ip_clean}:{src_port_clean}->{dst_ip_clean}:{dst_port_clean}|{proto_clean}|{type_clean}"
        fingerprint = hashlib.sha256(raw_key.encode("utf-8")).hexdigest()
        return fingerprint

    def is_within_cooldown(
        self,
        last_seen: datetime,
        current_time: Optional[datetime] = None,
        window_seconds: Optional[int] = None,
    ) -> bool:
        """
        Check if an existing alert is still within its active deduplication cooldown window.
        """
        now = current_time or datetime.now(timezone.utc)
        win = window_seconds if window_seconds is not None else self.window_seconds
        
        # Ensure UTC timezone awareness
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        elapsed = (now - last_seen).total_seconds()
        return 0 <= elapsed <= win
