"""
Tests for the health check system.
"""

import asyncio

import boto3
import pytest
from moto import mock_aws

from aerodrift.health_check import HealthChecker, HealthStatus
from aerodrift.ingestion import seed_mock_environment


@pytest.mark.asyncio
async def test_health_check_aws_connectivity():
    """Health check should verify AWS connectivity."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        seed_mock_environment(ec2)

        checker = HealthChecker(ec2)
        result = await checker.check_aws_connectivity()

        assert result.status == HealthStatus.HEALTHY
        assert "AWS" in result.message or "Successfully" in result.message


@pytest.mark.asyncio
async def test_health_check_ingestion_pipeline():
    """Health check should verify ingestion pipeline."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        seed_mock_environment(ec2)

        checker = HealthChecker(ec2)
        result = await checker.check_ingestion_pipeline()

        assert result.status == HealthStatus.HEALTHY
        assert result.duration_ms > 0


@pytest.mark.asyncio
async def test_health_check_topology_engine():
    """Health check should verify topology engine."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        seed_mock_environment(ec2)

        checker = HealthChecker(ec2)
        result = await checker.check_topology_engine()

        assert result.status == HealthStatus.HEALTHY
        assert "nodes" in result.message.lower()


@pytest.mark.asyncio
async def test_health_check_all():
    """Should run all checks."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        seed_mock_environment(ec2)

        checker = HealthChecker(ec2)
        results = await checker.check_all()

        assert len(results) >= 3
        assert checker.is_healthy()


@pytest.mark.asyncio
async def test_health_check_summary():
    """Should provide a summary of results."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        seed_mock_environment(ec2)

        checker = HealthChecker(ec2)
        await checker.check_all()
        summary = checker.summary()

        assert "healthy" in summary
        assert "degraded" in summary
        assert "unhealthy" in summary