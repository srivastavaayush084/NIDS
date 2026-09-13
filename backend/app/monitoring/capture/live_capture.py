import logging
import platform
import time
from typing import Any, Callable, Optional

from backend.app.core.config import settings
from backend.app.monitoring.capture.base import BaseCaptureSource
from backend.app.monitoring.parsing.packet_parser import PacketParser
from backend.app.monitoring.schemas import PacketInfo

logger = logging.getLogger(__name__)

try:
    from scapy.sendrecv import AsyncSniffer
    from scapy.arch import get_if_list
    from scapy.config import conf
    SCAPY_AVAILABLE = True
except ImportError:  # pragma: no cover
    SCAPY_AVAILABLE = False
    AsyncSniffer = None
    conf = None
    get_if_list = lambda: []


class LiveCaptureSource(BaseCaptureSource):
    """
    Live network interface sniffer using Scapy AsyncSniffer.
    Captures raw packets from local network interfaces, validates capture driver
    availability (Npcap/libpcap), and streams parsed PacketInfo objects into the pipeline.
    """

    def __init__(
        self,
        interface: Optional[str] = None,
        filter_bpf: Optional[str] = None,
        max_packets: Optional[int] = None,
    ):
        self.interface = interface or settings.MONITOR_CAPTURE_INTERFACE
        self.filter_bpf = filter_bpf or settings.MONITOR_PACKET_FILTER
        self.max_packets = max_packets
        self._sniffer: Optional[AsyncSniffer] = None
        self._running = False
        self._packet_count = 0

    @classmethod
    def get_available_interfaces(cls) -> list[dict[str, Any]]:
        """
        Enumerate all active/available network adapters with IPs, descriptions, and loopback flags.
        """
        results: list[dict[str, Any]] = []
        if not SCAPY_AVAILABLE:
            return results

        try:
            from scapy.all import ifaces
            for iface in ifaces.values():
                name = getattr(iface, "name", "")
                desc = getattr(iface, "description", "") or name
                ip = getattr(iface, "ip", "") or ""
                guid = getattr(iface, "guid", "")
                if name:
                    is_lb = "loopback" in name.lower() or "127.0.0.1" in str(ip)
                    has_ip = bool(ip and ip != "0.0.0.0" and not ip.startswith("169.254"))
                    results.append({
                        "name": name,
                        "description": desc,
                        "ip": str(ip),
                        "guid": str(guid) if guid else None,
                        "is_loopback": is_lb,
                        "is_default": False,
                        "_has_valid_ip": has_ip,
                    })
        except Exception as e:
            logger.warning(f"Error enumerating scapy ifaces: {e}")

        if not results:
            try:
                for iface_name in get_if_list():
                    results.append({
                        "name": iface_name,
                        "description": iface_name,
                        "ip": "",
                        "guid": None,
                        "is_loopback": "loopback" in iface_name.lower(),
                        "is_default": False,
                        "_has_valid_ip": False,
                    })
            except Exception:
                pass

        # Sort: adapters with valid IPs first (e.g. Wi-Fi), then Loopback, then others
        results.sort(key=lambda x: (
            not x.get("_has_valid_ip", False),
            x.get("is_loopback", False),
            x.get("name", ""),
        ))

        # Mark first valid non-loopback interface (or loopback) as default
        default_found = False
        for item in results:
            if not default_found and (item.get("_has_valid_ip") or item.get("is_loopback")):
                item["is_default"] = True
                default_found = True
            item.pop("_has_valid_ip", None)

        if not default_found and results:
            results[0]["is_default"] = True

        return results

    @classmethod
    def resolve_scapy_interface(cls, interface_name: Optional[str]) -> Optional[Any]:
        """
        Map a user-friendly interface name (e.g. 'Wi-Fi') or GUID to the exact
        Scapy interface object or device identifier.
        """
        if not interface_name or not SCAPY_AVAILABLE:
            return interface_name

        try:
            from scapy.all import conf
            # Check dev_from_name if supported
            if hasattr(conf.ifaces, "dev_from_name"):
                try:
                    dev = conf.ifaces.dev_from_name(interface_name)
                    if dev:
                        return dev
                except Exception:
                    pass

            name_clean = interface_name.lower().strip()
            for key, iface in conf.ifaces.items():
                if name_clean == key.lower().strip():
                    return iface
                if name_clean == getattr(iface, "name", "").lower().strip():
                    return iface
                if name_clean == getattr(iface, "description", "").lower().strip():
                    return iface
                guid = getattr(iface, "guid", "")
                if guid and name_clean in guid.lower():
                    return iface
        except Exception as e:
            logger.warning(f"Could not resolve scapy interface '{interface_name}': {e}")

        return interface_name

    @classmethod
    def get_default_interface(cls) -> Optional[str]:
        """Return the best recommended capture interface name."""
        ifaces_list = cls.get_available_interfaces()
        for iface in ifaces_list:
            if iface.get("is_default"):
                return iface.get("name")
        return ifaces_list[0]["name"] if ifaces_list else None

    @classmethod
    def check_capture_availability(cls) -> tuple[bool, str]:
        """
        Check if live capture is supported on current OS and environment.
        Returns (is_available: bool, message: str)
        """
        if not SCAPY_AVAILABLE:
            return False, "Scapy is not installed. Install scapy inside backend/.venv to enable live capture."

        os_name = platform.system().lower()
        if os_name == "windows":
            try:
                from scapy.config import conf as scapy_conf
                if not getattr(scapy_conf, "use_pcap", False):
                    return (
                        False,
                        "Live packet capture is unavailable. Npcap driver is not installed or not loaded. "
                        "Install Npcap with 'WinPcap API-compatible Mode' enabled from https://npcap.com to enable live capture."
                    )
            except Exception as e:
                return (
                    False,
                    f"Live packet capture driver diagnostic error: {e}. "
                    "Ensure Npcap is installed with Administrator rights."
                )

        return True, "Live capture driver and interfaces are accessible."

    @property
    def is_running(self) -> bool:
        if not self._running or self._sniffer is None:
            return False
        is_sniffer_running = getattr(self._sniffer, "running", False)
        thread = getattr(self._sniffer, "thread", None)
        is_thread_alive = thread.is_alive() if thread else False
        return bool(self._running and is_sniffer_running and is_thread_alive)

    def start(self, packet_callback: Callable[[PacketInfo], None]) -> None:
        """Start live packet sniffer asynchronously."""
        if self._running:
            logger.warning("Live capture is already running.")
            return

        avail, msg = self.check_capture_availability()
        if not avail:
            raise PermissionError(f"Cannot start live capture: {msg}")

        resolved_iface = self.resolve_scapy_interface(self.interface)
        logger.info(
            f"Starting live packet capture on interface='{self.interface or 'default'}' "
            f"(resolved='{getattr(resolved_iface, 'name', resolved_iface)}') "
            f"with filter='{self.filter_bpf}'"
        )

        def _on_packet(raw_pkt):
            self._packet_count += 1
            if self._packet_count == 1 or self._packet_count % 100 == 0:
                logger.debug(f"LiveCaptureSource: captured {self._packet_count} packets on '{self.interface or 'default'}'")
            parsed = PacketParser.parse_packet(raw_pkt)
            if parsed is not None:
                packet_callback(parsed)
            if self.max_packets and self._packet_count >= self.max_packets:
                logger.info(f"Live capture reached max packet count ({self.max_packets}). Stopping.")
                self.stop()

        try:
            self._sniffer = AsyncSniffer(
                iface=resolved_iface,
                filter=self.filter_bpf,
                prn=_on_packet,
                store=False,
            )
            self._sniffer.start()
            # Verify worker thread initialized without immediate failure
            time.sleep(0.1)
            thread = getattr(self._sniffer, "thread", None)
            if thread and not thread.is_alive():
                self._running = False
                err = getattr(self._sniffer, "exception", None)
                err_msg = str(err) if err else "Capture worker thread exited immediately upon starting."
                try:
                    self.stop()
                except Exception:
                    pass
                raise RuntimeError(
                    f"Failed to start live network sniffer on interface '{self.interface}': {err_msg}. "
                    "Ensure appropriate capture driver (Npcap on Windows / libpcap on Linux) is installed and active."
                )
            self._running = True
        except Exception as e:
            self._running = False
            self.stop()
            logger.error(f"Failed to start live sniffer: {e}")
            if isinstance(e, (RuntimeError, PermissionError)):
                raise
            raise RuntimeError(
                f"Failed to start live network sniffer on interface '{self.interface}': {e}. "
                "Ensure appropriate capture driver (Npcap on Windows / libpcap on Linux) is installed."
            ) from e

    def stop(self) -> None:
        """Stop active live sniffer safely with bounded join timeout."""
        if self._sniffer and getattr(self._sniffer, "running", False):
            try:
                self._sniffer.stop(join=False)
                if hasattr(self._sniffer, "thread") and self._sniffer.thread and self._sniffer.thread.is_alive():
                    self._sniffer.thread.join(timeout=0.5)
            except Exception as e:
                logger.warning(f"Error while stopping sniffer: {e}")
        self._running = False
        self._sniffer = None

