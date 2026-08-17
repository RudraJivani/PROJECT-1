"""
Tests for the DriftAnalyzer rule-level analysis.
"""

import boto3
import pytest
from moto import mock_aws

from aerodrift.drift_analyzer import DriftAnalyzer, RuleChange
from aerodrift.ingestion import CloudIngestor, seed_mock_environment, simulate_drift
from aerodrift.topology import TopologyEngine


@pytest.mark.asyncio
async def test_analyzer_detects_new_public_ingress():
    """Analyzer should identify newly-added public ingress rules."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        ids = seed_mock_environment(ec2)

        # Get baseline state
        ingestor = CloudIngestor(ec2)
        old_state = await ingestor.ingest()

        # Simulate drift
        simulate_drift(ec2, ids["db_sg_id"])

        # Get new state
        new_state = await ingestor.ingest()

        # Analyze
        analyzer = DriftAnalyzer(TopologyEngine())
        changes = analyzer.detect_new_public_ingress(
            old_state.security_groups, new_state.security_groups
        )

        assert len(changes) > 0
        assert any(
            c.security_group_id == ids["db_sg_id"] and c.is_public for c in changes
        )


def test_analyzer_classifies_critical_port():
    """Analyzer should classify DB port exposure as CRITICAL."""
    analyzer = DriftAnalyzer(TopologyEngine())
    
    risk = analyzer._classify_risk(port=5432, protocol="tcp", is_public=True)
    assert risk == "CRITICAL"


def test_analyzer_classifies_ssh_as_high():
    """Analyzer should classify SSH exposure as HIGH."""
    analyzer = DriftAnalyzer(TopologyEngine())
    
    risk = analyzer._classify_risk(port=22, protocol="tcp", is_public=True)
    assert risk == "HIGH"


def test_analyzer_classifies_private_as_low():
    """Analyzer should classify private exposures as LOW."""
    analyzer = DriftAnalyzer(TopologyEngine())
    
    risk = analyzer._classify_risk(port=5432, protocol="tcp", is_public=False)
    assert risk == "LOW"


def test_rule_change_description():
    """RuleChange should format a readable description."""
    change = RuleChange(
        security_group_id="sg-12345",
        security_group_name="prod-db",
        protocol="tcp",
        port_range="5432-5432",
        cidr="0.0.0.0/0",
        is_public=True,
        risk_level="CRITICAL",
    )

    desc = change.description
    assert "5432" in desc
    assert "prod-db" in desc
    assert "0.0.0.0/0" in desc