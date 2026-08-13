import boto3
import pytest
from moto import mock_aws

from aerodrift.ingestion import CloudIngestor, seed_mock_environment, simulate_drift
from aerodrift.topology import TopologyEngine


@pytest.mark.asyncio
async def test_no_path_from_internet_before_drift():
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        ids = seed_mock_environment(ec2)
        state = await CloudIngestor(ec2).ingest()

        engine = TopologyEngine()
        engine.build(state)

        assert engine.find_exposed_instances(name_filter="db") == []
        assert not engine.path_exists_from_internet(ids["db_instance_id"])


@pytest.mark.asyncio
async def test_path_from_internet_appears_after_drift():
    """Mid-Project Review acceptance test: manually alter a security group
    and prove the graph detects the new network path."""
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        ids = seed_mock_environment(ec2)
        simulate_drift(ec2, ids["db_sg_id"])
        state = await CloudIngestor(ec2).ingest()

        engine = TopologyEngine()
        engine.build(state)

        assert engine.path_exists_from_internet(ids["db_instance_id"])
        exposed = engine.find_exposed_instances(name_filter="db")
        assert ids["db_instance_id"] in exposed

        path = engine.exposure_path(ids["db_instance_id"])
        assert path[0] == "internet:0.0.0.0/0"
        assert path[-1] == ids["db_instance_id"]

        offenders = engine.offending_security_groups(ids["db_instance_id"])
        assert ids["db_sg_id"] in offenders