"""
Utility functions for AeroDrift.
"""

from __future__ import annotations

from typing import Any


def format_security_group_for_revoke(sg_id: str, cidr: str, port: int) -> dict[str, Any]:
    """
    Format a security group ingress rule for revocation.
    Used by the code generator in Week 3.
    """
    return {
        "GroupId": sg_id,
        "IpPermissions": [
            {
                "IpProtocol": "tcp",
                "FromPort": port,
                "ToPort": port,
                "IpRanges": [{"CidrIp": cidr}],
            }
        ],
    }


def parse_exposure_path(path: list[str]) -> dict[str, str]:
    """
    Parse an exposure path (from internet to a resource) into structured info.
    Example path: ['internet:0.0.0.0/0', 'sg-12345', 'i-98765', ...]
    Returns: {'source': 'internet', 'first_sg': 'sg-12345', 'target': 'i-98765'}
    """
    if len(path) < 2:
        return {}
    
    return {
        "source": path[0],
        "first_sg": path[1] if len(path) > 1 else None,
        "target": path[-1] if len(path) > 0 else None,
    }


def severity_to_priority(severity: str) -> int:
    """Convert severity string to numeric priority for sorting."""
    severity_map = {
        "CRITICAL": 0,
        "HIGH": 1,
        "MEDIUM": 2,
        "LOW": 3,
        "WARNING": 1,
        "INFO": 3,
    }
    return severity_map.get(severity, 999)