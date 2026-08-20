"""
Tests for the integrated AeroDriftSystem.
"""

import asyncio

import boto3
import pytest
from moto import mock_aws

from aerodrift.config import AeroDriftConfig
from aerodrift.ingestion import seed_mock_environment, simulate_drift
from aerodrift.integration import AeroDriftSystem


def test_system_initializes():
    """System should initialize without errors."""
    config = AeroDriftConfig(use_mock_aws=True)
    system = AeroDriftSystem(config=config)

    assert system.config == config
    assert system.engine is not None
    assert system.detector is not None


def test_system_rejects_invalid_config():
    """System should reject invalid configuration."""
    with pytest.raises(ValueError):
        config = AeroDriftConfig(ingestion_interval=-1)
        AeroDriftSystem(config=config)


@pytest.mark.asyncio
async def test_system_health_checks():
    """System should run health checks."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        seed_mock_environment(ec2)

        system = AeroDriftSystem()
        system.setup_aws_client(ec2)

        is_healthy = await system.run_health_checks()
        assert is_healthy


@pytest.mark.asyncio
async def test_system_ingest_and_analyze():
    """System should ingest and analyze cloud state."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        seed_mock_environment(ec2)

        system = AeroDriftSystem()
        system.setup_aws_client(ec2)

        state, events = await system.ingest_and_analyze()

        assert state is not None
        assert len(state.vpcs) > 0
        assert events == []  # No drift yet


@pytest.mark.asyncio
async def test_system_detects_drift():
    """System should detect drift during analysis."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        ids = seed_mock_environment(ec2)

        system = AeroDriftSystem()
        system.setup_aws_client(ec2)

        # Baseline
        await system.ingest_and_analyze()

        # Drift
        simulate_drift(ec2, ids["db_sg_id"])
        state, events = await system.ingest_and_analyze()

        assert len(events) > 0
        assert any(e.node_id == ids["db_instance_id"] for e in events)


def test_system_status():
    """System should report status."""
    system = AeroDriftSystem()
    status = system.system_status()

    assert "running" in status
    assert "configured" in status
    assert "drift_events" in status


@pytest.mark.asyncio
async def test_system_drift_callbacks():
    """System should call registered drift callbacks."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        ids = seed_mock_environment(ec2)

        system = AeroDriftSystem()
        system.setup_aws_client(ec2)

        callback_called = []

        def on_drift(events):
            callback_called.extend(events)

        system.on_drift(on_drift)

        # Baseline
        await system.ingest_and_analyze()

        # Drift
        simulate_drift(ec2, ids["db_sg_id"])
        await system.ingest_and_analyze()

        assert len(callback_called) > 0 