import boto3
import pytest
from moto import mock_aws

from aerodrift.ingestion import CloudIngestor, seed_mock_environment, simulate_drift


@pytest.mark.asyncio
async def test_ingest_returns_seeded_resources():
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        ids = seed_mock_environment(ec2)

        state = await CloudIngestor(ec2).ingest()

        assert any(v.vpc_id == ids["vpc_id"] for v in state.vpcs)
        assert {s.subnet_id for s in state.subnets} >= {
            ids["public_subnet_id"],
            ids["private_subnet_id"],
        }
        assert any(sg.group_id == ids["db_sg_id"] for sg in state.security_groups)
        assert any(i.instance_id == ids["db_instance_id"] for i in state.instances)


@pytest.mark.asyncio
async def test_baseline_security_group_has_no_public_ingress():
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        ids = seed_mock_environment(ec2)

        state = await CloudIngestor(ec2).ingest()
        db_sg = next(sg for sg in state.security_groups if sg.group_id == ids["db_sg_id"])

        assert all(rule.cidr != "0.0.0.0/0" for rule in db_sg.ingress)


@pytest.mark.asyncio
async def test_simulate_drift_opens_public_ingress():
    with mock_aws():
        ec2 = boto3.client("ec2", region_name="us-east-1")
        ids = seed_mock_environment(ec2)
        simulate_drift(ec2, ids["db_sg_id"])

        state = await CloudIngestor(ec2).ingest()
        db_sg = next(sg for sg in state.security_groups if sg.group_id == ids["db_sg_id"])

        assert any(rule.cidr == "0.0.0.0/0" for rule in db_sg.ingress)