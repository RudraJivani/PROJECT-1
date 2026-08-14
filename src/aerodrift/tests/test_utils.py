"""
Tests for AeroDrift utility functions.
"""

from aerodrift.utils import (
    format_security_group_for_revoke,
    parse_exposure_path,
    severity_to_priority,
)


def test_format_security_group_for_revoke():
    """Should format a revocation rule correctly."""
    result = format_security_group_for_revoke(
        sg_id="sg-12345",
        cidr="0.0.0.0/0",
        port=5432,
    )

    assert result["GroupId"] == "sg-12345"
    assert result["IpPermissions"][0]["FromPort"] == 5432
    assert result["IpPermissions"][0]["ToPort"] == 5432
    assert result["IpPermissions"][0]["IpRanges"][0]["CidrIp"] == "0.0.0.0/0"


def test_parse_exposure_path():
    """Should parse an exposure path into structured data."""
    path = ["internet:0.0.0.0/0", "sg-12345", "i-98765"]
    result = parse_exposure_path(path)

    assert result["source"] == "internet:0.0.0.0/0"
    assert result["first_sg"] == "sg-12345"
    assert result["target"] == "i-98765"


def test_severity_to_priority():
    """Should convert severity strings to numeric priorities."""
    assert severity_to_priority("CRITICAL") < severity_to_priority("HIGH")
    assert severity_to_priority("HIGH") < severity_to_priority("LOW")
    assert severity_to_priority("INFO") == severity_to_priority("LOW")