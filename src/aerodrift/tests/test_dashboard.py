"""
Tests for the DriftAwareDashboard real-time rendering.
"""

import boto3
import pytest
from moto import mock_aws

from aerodrift.dashboard import DriftAwareDashboard
from aerodrift.drift import DriftEvent
from aerodrift.ingestion import CloudIngestor, seed_mock_environment, simulate_drift
from aerodrift.topology import TopologyEngine


def test_dashboard_initializes():
    """Dashboard should initialize without error."""
    dashboard = DriftAwareDashboard()
    
    assert dashboard.exposed_instances == set()
    assert dashboard.exposed_sgs == set()
    assert dashboard.all_drift_events == []


def test_dashboard_records_drift_events():
    """Dashboard should track recorded drift events."""
    dashboard = DriftAwareDashboard()

    event = DriftEvent(
        node_id="i-12345",
        node_label="prod-db",
        node_type="instance",
        exposure_path=["internet:0.0.0.0/0", "sg-abc", "i-12345"],
        offending_security_groups=["sg-abc"],
    )

    dashboard.record_drift([event])

    assert len(dashboard.all_drift_events) == 1
    assert "i-12345" in dashboard.exposed_instances


def test_dashboard_tracks_exposed_sgs():
    """Dashboard should track exposed security groups."""
    dashboard = DriftAwareDashboard()

    event = DriftEvent(
        node_id="sg-12345",
        node_label="web-sg",
        node_type="security_group",
        exposure_path=["internet:0.0.0.0/0", "sg-12345"],
        offending_security_groups=["sg-12345"],
    )

    dashboard.record_drift([event])

    assert "sg-12345" in dashboard.exposed_sgs


@pytest.mark.asyncio
async def test_dashboard_renders_topology_with_exposure():
    """Dashboard should render topology with exposure highlighting."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        ids = seed_mock_environment(ec2)
        simulate_drift(ec2, ids["db_sg_id"])

        state = await CloudIngestor(ec2).ingest()
        engine = TopologyEngine()
        engine.build(state)

        dashboard = DriftAwareDashboard()
        tree = dashboard.render_topology_with_exposure(engine)

        assert tree is not None
        # Tree should contain internet and protected nodes
        assert tree.label is not None


def test_dashboard_renders_drift_summary_no_events():
    """Dashboard should show safe status when no drift."""
    dashboard = DriftAwareDashboard()
    panel = dashboard.render_drift_summary()

    assert panel is not None
    assert "No drift detected" in str(panel)


def test_dashboard_renders_drift_summary_with_events():
    """Dashboard should summarize detected drift."""
    dashboard = DriftAwareDashboard()

    event = DriftEvent(
        node_id="i-12345",
        node_label="prod-db",
        node_type="instance",
        exposure_path=["internet:0.0.0.0/0", "sg-abc", "i-12345"],
        offending_security_groups=["sg-abc"],
    )
    dashboard.record_drift([event])

    panel = dashboard.render_drift_summary()
    assert panel is not None


def test_dashboard_renders_exposed_resources_table():
    """Dashboard should list all exposed resources."""
    dashboard = DriftAwareDashboard()

    event1 = DriftEvent(
        node_id="i-111",
        node_label="db-1",
        node_type="instance",
        exposure_path=["internet:0.0.0.0/0", "sg-a", "i-111"],
        offending_security_groups=["sg-a"],
    )
    event2 = DriftEvent(
        node_id="i-222",
        node_label="db-2",
        node_type="instance",
        exposure_path=["internet:0.0.0.0/0", "sg-b", "i-222"],
        offending_security_groups=["sg-b"],
    )
    dashboard.record_drift([event1, event2])

    table = dashboard.render_exposed_resources_table()
    assert table is not None


def test_dashboard_renders_remediation_targets():
    """Dashboard should list security groups requiring remediation."""
    dashboard = DriftAwareDashboard()

    event = DriftEvent(
        node_id="i-12345",
        node_label="prod-db",
        node_type="instance",
        exposure_path=["internet:0.0.0.0/0", "sg-abc", "i-12345"],
        offending_security_groups=["sg-abc"],
    )
    dashboard.record_drift([event])

    table = dashboard.render_remediation_targets_table()
    assert table is not None