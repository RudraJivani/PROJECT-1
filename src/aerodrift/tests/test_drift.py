import boto3
import pytest
from moto import mock_aws

from aerodrift.drift import DriftDetector  
from aerodrift.ingestion import CloudIngestor, seed_mock_environment, simulate_drift
from aerodrift.topology import TopologyEngine


@pytest.mark.asyncio
async def test_drift_detector_baseline():
    """First call to compare() should not report any drift."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        seed_mock_environment(ec2)
        state = await CloudIngestor(ec2).ingest()

        engine = TopologyEngine()
        engine.build(state)

        detector = DriftDetector()
        events = detector.compare(engine)

        assert events == []


@pytest.mark.asyncio
async def test_drift_detector_detects_new_exposure():
    """Second call to compare() should report a newly exposed instance."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        ids = seed_mock_environment(ec2)

        # Baseline
        state = await CloudIngestor(ec2).ingest()
        engine = TopologyEngine()
        engine.build(state)
        detector = DriftDetector()
        detector.compare(engine)

        # Simulate drift
        simulate_drift(ec2, ids["db_sg_id"])
        state = await CloudIngestor(ec2).ingest()
        engine.build(state)

        # Detect drift
        events = detector.compare(engine)

        assert len(events) == 1
        assert events[0].node_id == ids["db_instance_id"]
        assert events[0].severity == "CRITICAL"
        assert ids["db_sg_id"] in events[0].offending_security_groups