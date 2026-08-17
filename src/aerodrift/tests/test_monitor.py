"""
Tests for the RealTimeMonitor continuous polling.
"""

import asyncio

import boto3
import pytest
from moto import mock_aws

from aerodrift.drift import DriftEvent
from aerodrift.ingestion import CloudIngestor, seed_mock_environment, simulate_drift
from aerodrift.monitor import RealTimeMonitor


@pytest.mark.asyncio
async def test_monitor_initializes():
    """Monitor should initialize without error."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        seed_mock_environment(ec2)
        ingestor = CloudIngestor(ec2)

        monitor = RealTimeMonitor(ingestor, poll_interval=0)
        assert monitor.poll_interval == 0
        assert not monitor._running


@pytest.mark.asyncio
async def test_monitor_detects_drift():
    """Monitor should call drift callbacks when drift occurs."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        ids = seed_mock_environment(ec2)
        ingestor = CloudIngestor(ec2)

        monitor = RealTimeMonitor(ingestor, poll_interval=0)
        detected_events: list[DriftEvent] = []

        def capture_drift(events: list[DriftEvent]) -> None:
            detected_events.extend(events)

        monitor.on_drift(capture_drift)

        # Run monitor in background
        task = asyncio.create_task(monitor.start())
        await asyncio.sleep(0.1)

        # Trigger drift
        simulate_drift(ec2, ids["db_sg_id"])
        await asyncio.sleep(0.2)

        monitor.stop()
        try:
            await asyncio.wait_for(task, timeout=2.0)
        except asyncio.TimeoutError:
            pass

        # Should have captured drift events
        assert len(detected_events) > 0


@pytest.mark.asyncio
async def test_monitor_stats():
    """Monitor should track polling and drift statistics."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        seed_mock_environment(ec2)
        ingestor = CloudIngestor(ec2)

        monitor = RealTimeMonitor(ingestor, poll_interval=0)

        task = asyncio.create_task(monitor.start())
        await asyncio.sleep(0.1)
        monitor.stop()

        try:
            await asyncio.wait_for(task, timeout=2.0)
        except asyncio.TimeoutError:
            pass

        stats = monitor.stats()
        assert stats["polls"] > 0
        assert "drifts_detected" in stats