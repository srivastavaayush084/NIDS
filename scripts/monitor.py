#!/usr/bin/env python3
"""
CLI Tool for Real-Time Network Monitoring & PCAP Ingestion
AI-Based Zero-Day Attack Detection System
"""

import argparse
import asyncio
import logging
import signal
import sys
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.core.config import settings
from backend.app.monitoring.features.feature_mapper import FeatureMapper
from backend.app.monitoring.manager import monitoring_manager
from backend.app.monitoring.schemas import MonitoringStartRequest, PCAPTestRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("zero.cli.monitor")


async def run_test_pcap(file_path: str, max_packets: int, dataset_name: str, xai: bool):
    """Run synchronous PCAP replay test."""
    print("=" * 70)
    print(f"ZERO-DAY NIDS: PCAP INGESTION & DETECTION BENCHMARK")
    print(f"Target File:   {file_path}")
    print(f"Max Packets:   {max_packets}")
    print(f"Dataset Model: {dataset_name}")
    print("=" * 70)

    req = PCAPTestRequest(
        file=file_path,
        max_packets=max_packets,
        dataset_name=dataset_name,
        generate_xai=xai,
    )

    try:
        report = await monitoring_manager.test_pcap(req)
        print("\n--- Benchmark Results ---")
        print(f"Packets Read:          {report.packets_read}")
        print(f"Packets Parsed:        {report.packets_parsed}")
        print(f"Flows Extracted:       {report.flows_extracted}")
        print(f"Detections Completed:  {report.detections_completed}")
        print(f"Anomalies Flagged:     {report.anomalies_flagged}")
        print(f"Alerts Triggered:      {report.alerts_triggered}")
        print(f"Execution Time:        {report.execution_time_ms:.2f} ms")
        print(f"Packet Throughput:     {report.throughput_pkts_per_sec:.2f} pkts/sec")
        print(f"Flow Throughput:       {report.throughput_flows_per_sec:.2f} flows/sec")

        print("\n--- Model Compatibility ---")
        for model_name, compat in report.model_compatibility.items():
            status_symbol = "[OK]" if compat.compatible else "[FAIL]"
            print(f" {status_symbol} {model_name:20s}: {compat.available_features}/{compat.total_required_features} features. {compat.explanation}")

        if report.sample_flows:
            print("\n--- Sample Extracted Flows ---")
            for sf in report.sample_flows[:5]:
                anom_str = "[ANOMALY]" if sf.get("is_anomaly") else "[NORMAL]"
                print(f" - {sf.get('flow_id')}: {sf.get('src_ip')} -> {sf.get('dst_ip')} | {sf.get('protocol')}/{sf.get('service')} | {anom_str} Risk={sf.get('risk_score'):.1f} ({sf.get('severity')})")

    except Exception as e:
        print(f"\n[ERROR] PCAP replay failed: {e}")
        sys.exit(1)


async def run_live_or_replay_session(args):
    """Run persistent live monitoring or PCAP streaming session with real-time status output."""
    print("=" * 70)
    print(f"ZERO-DAY NIDS: REAL-TIME TRAFFIC MONITORING")
    print(f"Source Mode:    {args.source.upper()}")
    if args.source == "live":
        print(f"Interface:      {args.interface or 'Default / Any'}")
        print(f"BPF Filter:     {args.filter}")
    else:
        print(f"Replay File:    {args.file}")
        print(f"Replay Speed:   {args.replay_speed}x")
    print(f"Target Dataset: {args.dataset}")
    print("=" * 70)

    start_req = MonitoringStartRequest(
        source=args.source,
        interface=args.interface,
        file=args.file,
        filter=args.filter,
        max_packets=args.max_packets,
        replay_speed=args.replay_speed,
        dataset_name=args.dataset,
        generate_xai=not args.no_xai,
    )

    try:
        await monitoring_manager.start(start_req)
        print("\n[+] Monitoring session started. Press Ctrl+C to stop.\n")
    except Exception as e:
        print(f"\n[ERROR] Failed to start monitoring: {e}")
        sys.exit(1)

    stop_requested = False

    def _sig_handler(*_):
        nonlocal stop_requested
        stop_requested = True

    try:
        signal.signal(signal.SIGINT, _sig_handler)
        signal.signal(signal.SIGTERM, _sig_handler)
    except Exception:
        pass

    try:
        while not stop_requested:
            status = monitoring_manager.get_status()
            sys.stdout.write(
                f"\r[STATUS] Uptime: {status.uptime_seconds:.1f}s | "
                f"Pkts: {status.packets_captured} ({status.throughput_pkts_sec:.1f} p/s) | "
                f"Flows: {status.flows_created} ({status.throughput_flows_sec:.1f} f/s) | "
                f"Events: {status.events_processed} | "
                f"Anomalies: {status.anomalies_detected} | "
                f"Alerts: {status.alerts_generated} | "
                f"Buf: {status.buffer_utilization_pct:.1f}%"
            )
            sys.stdout.flush()

            # If PCAP replay source stopped on its own
            if args.source == "pcap" and not status.running:
                break

            await asyncio.sleep(1.0)
    finally:
        print("\n\n[-] Stopping monitoring session and flushing buffers...")
        stop_res = await monitoring_manager.stop()
        print(f"[+] {stop_res.message}")
        print(f"Summary: {stop_res.summary}")


def main():
    parser = argparse.ArgumentParser(
        description="ZERO AI NIDS - Real-Time Network Monitoring & PCAP Ingestion CLI"
    )
    parser.add_argument(
        "--source",
        choices=["live", "pcap"],
        default="pcap",
        help="Capture source: 'live' network interface or 'pcap' file replay (default: pcap)",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Path to PCAP file (required when source=pcap or --test-mode is active)",
    )
    parser.add_argument(
        "--interface",
        type=str,
        default=None,
        help="Network interface for live capture (e.g. eth0, Wi-Fi)",
    )
    parser.add_argument(
        "--filter",
        type=str,
        default="tcp or udp",
        help="BPF filter expression (default: 'tcp or udp')",
    )
    parser.add_argument(
        "--max-packets",
        type=int,
        default=1000,
        help="Maximum packets to process (default: 1000)",
    )
    parser.add_argument(
        "--replay-speed",
        type=float,
        default=0.0,
        help="Replay speed factor (0.0 = max speed, 1.0 = real-time, 2.0 = 2x speed)",
    )
    parser.add_argument(
        "--dataset",
        type=str,
        default="synthetic",
        help="Target dataset model mapping (default: 'synthetic')",
    )
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run synchronous benchmark analysis without starting long-running background monitor",
    )
    parser.add_argument(
        "--no-xai",
        action="store_true",
        help="Disable XAI explanation calculation",
    )
    parser.add_argument(
        "--check-compat",
        action="store_true",
        help="Check and display model feature compatibility matrix",
    )

    args = parser.parse_args()

    if args.check_compat:
        print("=" * 60)
        print(f"MODEL FEATURE COMPATIBILITY MATRIX ({args.dataset})")
        print("=" * 60)
        reports = FeatureMapper.get_all_compatibility(args.dataset)
        for model_name, compat in reports.items():
            sym = "[OK]" if compat.compatible else "[FAIL]"
            print(f" {sym} {model_name:20s}: {compat.available_features}/{compat.total_required_features} features. {compat.explanation}")
        return

    if args.test_mode:
        if not args.file:
            print("[ERROR] --file argument is required when running in --test-mode")
            sys.exit(1)
        asyncio.run(run_test_pcap(args.file, args.max_packets, args.dataset, not args.no_xai))
    else:
        if args.source == "pcap" and not args.file:
            print("[ERROR] --file argument is required when --source=pcap")
            sys.exit(1)
        asyncio.run(run_live_or_replay_session(args))


if __name__ == "__main__":
    main()
