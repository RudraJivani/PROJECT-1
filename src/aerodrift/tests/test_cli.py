"""
Tests for the Rich CLI dashboard.
"""

import boto3
import pytest
from moto import mock_aws
from io import StringIO

from aerodrift.cli import AeroDriftCLI
from aerodrift.drift import DriftEvent
from aerodrift.ingestion import CloudIngestor, seed_mock_environment, simulate_drift
from aerodrift.topology import TopologyEngine


@pytest.mark.asyncio
async def test_cli_renders_topology_tree():
    """CLI should render the topology tree without crashing."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        seed_mock_environment(ec2)
        state = await CloudIngestor(ec2).ingest()

        engine = TopologyEngine()
        engine.build(state)

        cli = AeroDriftCLI()
        # Just ensure it doesn't crash
        cli.print_topology_tree(engine)


def test_cli_displays_drift_events():
    """CLI should render drift events in a table."""
    cli = AeroDriftCLI()
    
    event = DriftEvent(
        node_id="i-12345",
        node_label="prod-db",
        node_type="instance",
        exposure_path=["internet:0.0.0.0/0", "sg-abc", "i-12345"],
        offending_security_groups=["sg-abc"],
    )
    
    # Just ensure it doesn't crash
    cli.print_drift_events([event])


def test_cli_displays_no_drift():
    """CLI should gracefully handle zero drift events."""
    cli = AeroDriftCLI()
    
    # Just ensure it doesn't crash
    cli.print_drift_events([])


def test_cli_displays_offending_security_groups():
    """CLI should render remediation targets."""
    cli = AeroDriftCLI()
    
    event = DriftEvent(
        node_id="i-12345",
        node_label="prod-db",
        node_type="instance",
        exposure_path=["internet:0.0.0.0/0", "sg-abc", "i-12345"],
        offending_security_groups=["sg-abc", "sg-xyz"],
    )
    
    # Just ensure it doesn't crash
    cli.print_offending_security_groups([event])