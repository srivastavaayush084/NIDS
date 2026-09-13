import ipaddress
from typing import Optional


def is_valid_ipv4(ip_str: Optional[str]) -> bool:
    """Validate if given string is a valid IPv4 address."""
    if not ip_str:
        return False
    try:
        ipaddress.IPv4Address(ip_str)
        return True
    except ValueError:
        return False


def is_private_ip(ip_str: Optional[str]) -> bool:
    """Check if given IP address is in a private subnet range."""
    if not ip_str:
        return False
    try:
        return ipaddress.ip_address(ip_str).is_private
    except ValueError:
        return False
