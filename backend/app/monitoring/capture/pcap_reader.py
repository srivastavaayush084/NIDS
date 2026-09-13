import logging
from pathlib import Path
import tempfile
import threading
import time
from typing import Callable, Optional

from backend.app.core.config import settings
from backend.app.monitoring.capture.base import BaseCaptureSource
from backend.app.monitoring.parsing.packet_parser import PacketParser
from backend.app.monitoring.schemas import PacketInfo

logger = logging.getLogger(__name__)

try:
    import scapy.layers.l2  # noqa: F401 - registers Ethernet DLT
    import scapy.layers.inet  # noqa: F401 - registers IP/TCP/UDP
    from scapy.utils import PcapReader
    SCAPY_AVAILABLE = True
except ImportError:  # pragma: no cover
    SCAPY_AVAILABLE = False
    PcapReader = None


def resolve_and_validate_pcap_path(path_str: str) -> Path:
    """
    Validate that PCAP file exists, has a valid extension, is within allowed directories,
    and does not exceed maximum allowable file size.
    Prevents path traversal attacks (../, absolute escape).
    """
    clean_str = (path_str or "").strip()
    if not clean_str:
        raise ValueError("PCAP file path cannot be empty.")
    if "\x00" in clean_str:
        raise ValueError("Invalid file path: Null bytes are not permitted.")

    ext = "." + clean_str.rsplit(".", 1)[-1].lower() if "." in clean_str else ""
    if ext not in settings.ALLOWED_PCAP_EXTENSIONS:
        raise ValueError(f"Invalid file extension '{ext}'. Allowed extensions: {settings.ALLOWED_PCAP_EXTENSIONS}")

    p = Path(clean_str).resolve()
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"PCAP file not found: {path_str}")

    # Check file size limit
    file_size = p.stat().st_size
    if file_size > settings.MAX_PCAP_FILE_BYTES:
        raise ValueError(f"PCAP file size ({file_size} bytes) exceeds maximum permitted limit of {settings.MAX_PCAP_FILE_BYTES} bytes.")

    # Check against allowed directory if configured
    allowed_dir = Path(settings.MONITOR_PCAP_ALLOWED_DIRECTORY).resolve()
    try:
        p.relative_to(allowed_dir)
        return p
    except ValueError:
        pass

    # Check against project root data directory
    project_data = Path("data").resolve()
    try:
        p.relative_to(project_data)
        return p
    except ValueError:
        pass

    # Check against workspace root
    workspace_root = Path(".").resolve()
    try:
        p.relative_to(workspace_root)
        return p
    except ValueError:
        pass

    # Check against system temp directory (for test fixtures and uploads)
    sys_temp = Path(tempfile.gettempdir()).resolve()
    try:
        p.relative_to(sys_temp)
        return p
    except ValueError:
        raise PermissionError(f"Access to PCAP path '{path_str}' outside allowed directories is restricted.")


class PCAPCaptureSource(BaseCaptureSource):
    """
    Streaming PCAP/PCAPNG file replay source.
    Reads packets chunk-by-chunk using PcapReader to support large captures without memory exhaustion,
    with configurable replay speed pacing and packet limits.
    """

    def __init__(
        self,
        file_path: str,
        max_packets: Optional[int] = None,
        replay_speed: float = 0.0,
    ):
        self.file_path = resolve_and_validate_pcap_path(file_path)
        self.max_packets = max_packets or settings.MONITOR_MAX_PACKETS_PER_PCAP
        self.replay_speed = replay_speed
        self._running = False
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self, packet_callback: Callable[[PacketInfo], None]) -> None:
        """Start reading PCAP in a background daemon thread."""
        if self._running:
            logger.warning("PCAP capture source is already running.")
            return

        self._running = True
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_reader,
            args=(packet_callback,),
            daemon=True,
            name="pcap-reader-thread",
        )
        self._thread.start()

    def _run_reader(self, packet_callback: Callable[[PacketInfo], None]) -> None:
        """Internal streaming reader loop."""
        if not SCAPY_AVAILABLE:
            logger.error("Scapy is not installed; cannot read PCAP files.")
            self._running = False
            return

        logger.info(f"Starting PCAP replay from '{self.file_path}' (max_packets={self.max_packets}, speed={self.replay_speed})")
        packet_count = 0
        last_pkt_time: Optional[float] = None

        try:
            with PcapReader(str(self.file_path)) as reader:
                for raw_pkt in reader:
                    if self._stop_event.is_set():
                        break

                    parsed = PacketParser.parse_packet(raw_pkt)
                    if parsed is not None:
                        # Pacing control if replay_speed > 0
                        if self.replay_speed > 0 and last_pkt_time is not None:
                            delta_sim = max(0.0, parsed.timestamp - last_pkt_time)
                            delay = delta_sim / self.replay_speed
                            if delay > 0 and delay < 5.0:  # Cap max sleep at 5s
                                time.sleep(delay)

                        last_pkt_time = parsed.timestamp
                        packet_callback(parsed)
                        packet_count += 1

                        if self.max_packets and packet_count >= self.max_packets:
                            logger.info(f"Reached maximum packet count limit ({self.max_packets}). Stopping replay.")
                            break

        except Exception as e:
            logger.error(f"Error during PCAP replay: {e}", exc_info=True)
        finally:
            self._running = False
            logger.info(f"PCAP replay finished. Total packets processed: {packet_count}")

    def stop(self) -> None:
        """Signal reader to terminate."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2.0)
        self._running = False
