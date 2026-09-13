from abc import ABC, abstractmethod
from typing import Callable, Optional
from backend.app.monitoring.schemas import PacketInfo


class BaseCaptureSource(ABC):
    """Abstract interface for all network traffic capture sources (Live & PCAP)."""

    @abstractmethod
    def start(self, packet_callback: Callable[[PacketInfo], None]) -> None:
        """Start capturing packets and emitting them to packet_callback."""
        pass

    @abstractmethod
    def stop(self) -> None:
        """Gracefully stop packet capture."""
        pass

    @property
    @abstractmethod
    def is_running(self) -> bool:
        """Check if capture source is currently active."""
        pass
