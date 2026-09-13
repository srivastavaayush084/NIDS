import os
from pathlib import Path
from scapy.layers.l2 import Ether
from scapy.layers.inet import ICMP, IP, TCP, UDP
from scapy.utils import wrpcap

def create_sample_pcap():
    out_dir = Path("data/sample")
    out_dir.mkdir(parents=True, exist_ok=True)
    pcap_path = out_dir / "sample_network_traffic.pcap"

    packets = []
    base_time = 1700000000.0

    # 1. Normal HTTP session
    eth_client = "02:00:00:00:00:01"
    eth_server = "02:00:00:00:00:02"

    p1 = Ether(src=eth_client, dst=eth_server) / IP(src="192.168.1.50", dst="192.168.1.100") / TCP(sport=54321, dport=80, flags="S", seq=1000)
    p1.time = base_time
    packets.append(p1)

    p2 = Ether(src=eth_server, dst=eth_client) / IP(src="192.168.1.100", dst="192.168.1.50") / TCP(sport=80, dport=54321, flags="SA", seq=2000, ack=1001)
    p2.time = base_time + 0.01
    packets.append(p2)

    p3 = Ether(src=eth_client, dst=eth_server) / IP(src="192.168.1.50", dst="192.168.1.100") / TCP(sport=54321, dport=80, flags="PA", seq=1001, ack=2001) / b"GET /api/v1/health HTTP/1.1\r\nHost: 192.168.1.100\r\n\r\n"
    p3.time = base_time + 0.02
    packets.append(p3)

    p4 = Ether(src=eth_server, dst=eth_client) / IP(src="192.168.1.100", dst="192.168.1.50") / TCP(sport=80, dport=54321, flags="PA", seq=2001, ack=1055) / b"HTTP/1.1 200 OK\r\nContent-Length: 15\r\n\r\n{\"status\":\"ok\"}"
    p4.time = base_time + 0.05
    packets.append(p4)

    p5 = Ether(src=eth_client, dst=eth_server) / IP(src="192.168.1.50", dst="192.168.1.100") / TCP(sport=54321, dport=80, flags="FA", seq=1055, ack=2050)
    p5.time = base_time + 0.06
    packets.append(p5)

    p6 = Ether(src=eth_server, dst=eth_client) / IP(src="192.168.1.100", dst="192.168.1.50") / TCP(sport=80, dport=54321, flags="FA", seq=2050, ack=1056)
    p6.time = base_time + 0.07
    packets.append(p6)

    # 2. UDP DNS Traffic
    p7 = Ether(src=eth_client, dst=eth_server) / IP(src="192.168.1.50", dst="8.8.8.8") / UDP(sport=61234, dport=53) / b"\x00\x01\x01\x00\x00\x01\x00\x00"
    p7.time = base_time + 0.10
    packets.append(p7)

    # 3. ICMP Ping
    p8 = Ether(src=eth_client, dst=eth_server) / IP(src="192.168.1.50", dst="192.168.1.1") / ICMP(type=8, code=0) / b"benchmark_payload_icmp"
    p8.time = base_time + 0.15
    packets.append(p8)

    # 4. Port scan anomaly simulation
    eth_scanner = "02:00:00:00:00:99"
    for port in [21, 22, 23, 80, 443, 3306, 8080]:
        scan_pkt = Ether(src=eth_scanner, dst=eth_server) / IP(src="10.0.0.99", dst="192.168.1.100") / TCP(sport=40000 + port, dport=port, flags="S")
        scan_pkt.time = base_time + 0.20 + (port * 0.001)
        packets.append(scan_pkt)

    wrpcap(str(pcap_path), packets)
    print(f"Generated sample PCAP at {pcap_path} with {len(packets)} packets.")

if __name__ == "__main__":
    create_sample_pcap()
