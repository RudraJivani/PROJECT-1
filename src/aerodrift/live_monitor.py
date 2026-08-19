"""
Live Monitoring Script
Combines the RealTimeMonitor with the DriftAwareDashboard for a live view.

Run with:  python -m aerodrift.live_monitor
"""

from __future__ import annotations

import asyncio

import boto3

from aerodrift.config import AeroDriftConfig
from aerodrift.dashboard import DriftAwareDashboard
from aerodrift.drift import DriftEvent
from aerodrift.ingestion import CloudIngestor, seed_mock_environment
from aerodrift.monitor import RealTimeMonitor
from aerodrift.topology import TopologyEngine

try:
    from moto import mock_aws
except ImportError as exc:
    raise SystemExit("Install moto (`pip install moto`) to run this monitor.") from exc


async def main() -> None:
    """Run the live monitor with dashboard."""
    with mock_aws():
        # Setup
        ec2 = boto3.client("ec2", region_name="us-east-1")
        seed_mock_environment(ec2)

        ingestor = CloudIngestor(ec2)
        engine = TopologyEngine()
        dashboard = DriftAwareDashboard()
        monitor = RealTimeMonitor(ingestor, poll_interval=5)

        # Register dashboard as drift callback
        def on_drift(events: list[DriftEvent]) -> None:
            dashboard.record_drift(events)
            print(f"\n[ALERT] {len(events)} drift event(s) detected!")
            for event in events:
                print(f"  - {event.node_label} ({event.severity})")

        monitor.on_drift(on_drift)

        print("=" * 70)
        print("AERODRIFT LIVE MONITOR")
        print("=" * 70)
        print("\nStarting real-time monitoring...")
        print("Press Ctrl+C to stop.\n")

        try:
            # Run monitor in background
            monitor_task = asyncio.create_task(monitor.start())

            # Display dashboard updates every 10 seconds
            update_count = 0
            while True:
                await asyncio.sleep(10)
                update_count += 1

                # Re-ingest for latest state
                state = await ingestor.ingest()
                engine.build(state)

                # Display dashboard
                print("\n" + "=" * 70)
                print(f"DASHBOARD UPDATE #{update_count}")
                print("=" * 70 + "\n")
                dashboard.print_full_dashboard(engine)

                stats = monitor.stats()
                print(f"\n[Stats] Polls: {stats['polls']} | Drifts: {stats['drifts_detected']}")

        except KeyboardInterrupt:
            print("\n\n[Monitor] Shutting down...")
            monitor.stop()
            try:
                await asyncio.wait_for(monitor_task, timeout=2.0)
            except asyncio.TimeoutError:
                pass

        print("[Monitor] Live monitoring stopped.")


if __name__ == "__main__":
    asyncio.run(main())