"""
Tests for the AeroDrift daemon main loop.
"""

import asyncio

import boto3
import pytest
from moto import mock_aws

from aerodrift.config import AeroDriftConfig
from aerodrift.daemon import AeroDriftDaemon
from aerodrift.ingestion import seed_mock_environment, simulate_drift


@pytest.mark.asyncio
async def test_daemon_initializes_without_error():
    """Daemon should initialize and connect to mock AWS."""
    config = AeroDriftConfig(use_mock_aws=True)
    daemon = AeroDriftDaemon(config=config)
    
    assert daemon.config == config
    assert daemon.detector is not None
    assert daemon.engine is not None


@pytest.mark.asyncio
async def test_daemon_one_ingestion_cycle():
    """Daemon should complete one full ingest + detect cycle."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        seed_mock_environment(ec2)

        config = AeroDriftConfig(
            use_mock_aws=True,
            ingestion_interval=0,  # Don't sleep
            detection_interval=0,
        )
        daemon = AeroDriftDaemon(config=config)

        # Start daemon and let it run for one cycle
        task = asyncio.create_task(daemon.run())
        await asyncio.sleep(0.5)
        daemon.stop()
        
        try:
            await asyncio.wait_for(task, timeout=2.0)
        except asyncio.TimeoutError:
            pass

        # Daemon should have logged at least one ingestion
        assert any(e.get("event_type") == "ingestion" for e in daemon.logger.events)


@pytest.mark.asyncio
async def test_daemon_detects_drift_in_cycle():
    """Daemon should detect drift in a monitoring cycle."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        ids = seed_mock_environment(ec2)

        config = AeroDriftConfig(
            use_mock_aws=True,
            ingestion_interval=0,
            detection_interval=0,
        )
        daemon = AeroDriftDaemon(config=config)

        # Run one cycle to baseline
        task = asyncio.create_task(daemon.run())
        await asyncio.sleep(0.3)

        # Simulate drift
        simulate_drift(ec2, ids["db_sg_id"])
        
        # Let daemon detect it
        await asyncio.sleep(0.3)
        daemon.stop()

        try:
            await asyncio.wait_for(task, timeout=2.0)
        except asyncio.TimeoutError:
            pass

        # Daemon should have logged the drift event
        assert any(e.get("event_type") == "drift_detected" for e in daemon.logger.events)