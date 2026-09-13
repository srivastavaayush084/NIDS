import logging
import time
from typing import Any, Dict, Optional

from backend.app.monitoring.schemas import PacketInfo

logger = logging.getLogger(__name__)

try:
    from scapy.layers.inet import ICMP, IP, TCP, UDP
    from scapy.layers.inet6 import IPv6
    from scapy.packet import Packet
    SCAPY_AVAILABLE = True
except ImportError:  # pragma: no cover
    SCAPY_AVAILABLE = False
    Packet = Any


class PacketParser:
    """
    Parses raw Scapy packets into standardized, structured PacketInfo objects.
    Extracts Layer 3 (IP/IPv6) and Layer 4 (TCP/UDP/ICMP) metadata safely.
    """

    @staticmethod
    def parse_packet(packet: Any) -> Optional[PacketInfo]:
        """
        Parse a Scapy packet into a PacketInfo object.
        Returns None if packet is not an IPv4/IPv6 packet or cannot be parsed.
        """
        if not SCAPY_AVAILABLE:
            return None

        try:
            timestamp = float(getattr(packet, "time", time.time()))
            length = int(len(packet))

            # Layer 3 - IP or IPv6
            src_ip: Optional[str] = None
            dst_ip: Optional[str] = None
            ttl: Optional[int] = None

            if packet.haslayer(IP):
                ip_layer = packet[IP]
                src_ip = str(ip_layer.src)
                dst_ip = str(ip_layer.dst)
                ttl = int(ip_layer.ttl)
            elif packet.haslayer(IPv6):
                ip6_layer = packet[IPv6]
                src_ip = str(ip6_layer.src)
                dst_ip = str(ip6_layer.dst)
                ttl = int(getattr(ip6_layer, "hlim", 64))
            else:
                # Non-IP packet (e.g. ARP, STP, etc.)
                return None

            # Layer 4 - Protocol & Ports
            protocol = "OTHER"
            src_port: Optional[int] = None
            dst_port: Optional[int] = None
            flags_dict: Dict[str, bool] = {}
            payload_size = 0

            if packet.haslayer(TCP):
                protocol = "TCP"
                tcp_layer = packet[TCP]
                src_port = int(tcp_layer.sport)
                dst_port = int(tcp_layer.dport)

                # TCP flags parsing
                # flags can be an int or a FlagValue / string representation in Scapy
                flag_val = getattr(tcp_layer, "flags", None)
                if flag_val is not None:
                    flag_str = str(flag_val).upper()
                    flags_dict = {
                        "SYN": "S" in flag_str,
                        "ACK": "A" in flag_str,
                        "FIN": "F" in flag_str,
                        "RST": "R" in flag_str,
                        "PSH": "P" in flag_str,
                        "URG": "U" in flag_str,
                    }
                if hasattr(tcp_layer, "payload"):
                    payload_size = len(bytes(tcp_layer.payload))

            elif packet.haslayer(UDP):
                protocol = "UDP"
                udp_layer = packet[UDP]
                src_port = int(udp_layer.sport)
                dst_port = int(udp_layer.dport)
                if hasattr(udp_layer, "payload"):
                    payload_size = len(bytes(udp_layer.payload))

            elif packet.haslayer(ICMP):
                protocol = "ICMP"
                # ICMP doesn't have standard transport ports; type and code can be mapped if needed
                icmp_layer = packet[ICMP]
                src_port = int(getattr(icmp_layer, "type", 0))
                dst_port = int(getattr(icmp_layer, "code", 0))
                if hasattr(icmp_layer, "payload"):
                    payload_size = len(bytes(icmp_layer.payload))

            return PacketInfo(
                timestamp=timestamp,
                src_ip=src_ip,
                dst_ip=dst_ip,
                src_port=src_port,
                dst_port=dst_port,
                protocol=protocol,
                length=length,
                flags=flags_dict,
                ttl=ttl,
                payload_size=payload_size,
            )

        except Exception as e:
            logger.debug(f"Failed to parse packet: {e}")
            return None
