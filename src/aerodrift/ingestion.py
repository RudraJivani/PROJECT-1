"""
Cloud Ingestion (boto3 & asyncio)
Highly concurrent polling of AWS APIs to ingest current state data.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

import boto3

try:
    from moto import mock_aws
except ImportError:
    mock_aws = None


@dataclass
class SecurityGroupRule:
    protocol: str
    from_port: int
    to_port: int
    cidr: str


@dataclass
class SecurityGroup:
    group_id: str
    group_name: str
    vpc_id: str
    ingress: list[SecurityGroupRule] = field(default_factory=list)


@dataclass
class Instance:
    instance_id: str
    vpc_id: str
    subnet_id: str
    security_group_ids: list[str]
    tags: dict[str, str] = field(default_factory=dict)


@dataclass
class Subnet:
    subnet_id: str
    vpc_id: str
    cidr_block: str


@dataclass
class Vpc:
    vpc_id: str
    cidr_block: str


@dataclass
class CloudState:
    """A single point-in-time snapshot of the ingested cloud environment."""

    vpcs: list[Vpc] = field(default_factory=list)
    subnets: list[Subnet] = field(default_factory=list)
    security_groups: list[SecurityGroup] = field(default_factory=list)
    instances: list[Instance] = field(default_factory=list)


def seed_mock_environment(ec2_client: Any) -> dict[str, str]:
    """Build a small sandbox environment inside a moto-mocked AWS account."""
    vpc = ec2_client.create_vpc(CidrBlock="10.0.0.0/16")
    vpc_id = vpc["Vpc"]["VpcId"]

    public_subnet = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock="10.0.1.0/24")
    private_subnet = ec2_client.create_subnet(VpcId=vpc_id, CidrBlock="10.0.2.0/24")

    db_sg = ec2_client.create_security_group(
        GroupName="db-sg", Description="Database security group", VpcId=vpc_id
    )
    db_sg_id = db_sg["GroupId"]

    ec2_client.authorize_security_group_ingress(
        GroupId=db_sg_id,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 5432,
                "ToPort": 5432,
                "IpRanges": [{"CidrIp": "10.0.0.0/16"}],
            }
        ],
    )

    db_instance = ec2_client.run_instances(
        ImageId="ami-12345678",
        MinCount=1,
        MaxCount=1,
        SubnetId=private_subnet["Subnet"]["SubnetId"],
        SecurityGroupIds=[db_sg_id],
        TagSpecifications=[
            {"ResourceType": "instance", "Tags": [{"Key": "Name", "Value": "prod-db"}]}
        ],
    )
    db_instance_id = db_instance["Instances"][0]["InstanceId"]

    return {
        "vpc_id": vpc_id,
        "public_subnet_id": public_subnet["Subnet"]["SubnetId"],
        "private_subnet_id": private_subnet["Subnet"]["SubnetId"],
        "db_sg_id": db_sg_id,
        "db_instance_id": db_instance_id,
    }


def simulate_drift(ec2_client: Any, sg_id: str) -> None:
    """Simulate an engineer accidentally opening the DB to the internet."""
    ec2_client.authorize_security_group_ingress(
        GroupId=sg_id,
        IpPermissions=[
            {
                "IpProtocol": "tcp",
                "FromPort": 5432,
                "ToPort": 5432,
                "IpRanges": [{"CidrIp": "0.0.0.0/0"}],
            }
        ],
    )


class CloudIngestor:
    """Concurrently pulls VPC/Subnet/SecurityGroup/Instance state via boto3."""

    def __init__(self, ec2_client: Any):
        self._ec2 = ec2_client

    async def _fetch_vpcs(self) -> list[Vpc]:
        resp = await asyncio.to_thread(self._ec2.describe_vpcs)
        return [Vpc(vpc_id=v["VpcId"], cidr_block=v["CidrBlock"]) for v in resp["Vpcs"]]

    async def _fetch_subnets(self) -> list[Subnet]:
        resp = await asyncio.to_thread(self._ec2.describe_subnets)
        return [
            Subnet(subnet_id=s["SubnetId"], vpc_id=s["VpcId"], cidr_block=s["CidrBlock"])
            for s in resp["Subnets"]
        ]

    async def _fetch_security_groups(self) -> list[SecurityGroup]:
        resp = await asyncio.to_thread(self._ec2.describe_security_groups)
        groups = []
        for g in resp["SecurityGroups"]:
            rules = [
                SecurityGroupRule(
                    protocol=p.get("IpProtocol", "-1"),
                    from_port=p.get("FromPort", -1),
                    to_port=p.get("ToPort", -1),
                    cidr=ip_range["CidrIp"],
                )
                for p in g.get("IpPermissions", [])
                for ip_range in p.get("IpRanges", [])
            ]
            groups.append(
                SecurityGroup(
                    group_id=g["GroupId"],
                    group_name=g.get("GroupName", ""),
                    vpc_id=g.get("VpcId", ""),
                    ingress=rules,
                )
            )
        return groups

    async def _fetch_instances(self) -> list[Instance]:
        resp = await asyncio.to_thread(self._ec2.describe_instances)
        instances = []
        for reservation in resp["Reservations"]:
            for inst in reservation["Instances"]:
                tags = {t["Key"]: t["Value"] for t in inst.get("Tags", [])}
                sg_ids = [sg["GroupId"] for sg in inst.get("SecurityGroups", [])]
                instances.append(
                    Instance(
                        instance_id=inst["InstanceId"],
                        vpc_id=inst.get("VpcId", ""),
                        subnet_id=inst.get("SubnetId", ""),
                        security_group_ids=sg_ids,
                        tags=tags,
                    )
                )
        return instances

    async def ingest(self) -> CloudState:
        """Poll all resource types concurrently and assemble a snapshot."""
        vpcs, subnets, sgs, instances = await asyncio.gather(
            self._fetch_vpcs(),
            self._fetch_subnets(),
            self._fetch_security_groups(),
            self._fetch_instances(),
        )
        return CloudState(vpcs=vpcs, subnets=subnets, security_groups=sgs, instances=instances)