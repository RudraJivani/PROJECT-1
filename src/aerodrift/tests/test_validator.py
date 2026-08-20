"""
Tests for configuration and data validation.
"""

from aerodrift.config import AeroDriftConfig
from aerodrift.ingestion import CloudState, Vpc, Instance, SecurityGroup
from aerodrift.validator import CloudStateValidator, ConfigValidator, InputSanitizer


def test_config_validator_accepts_valid_config():
    """Validator should accept valid config."""
    config = AeroDriftConfig()
    errors = ConfigValidator.validate(config)
    assert errors == []
    assert ConfigValidator.is_valid(config)


def test_config_validator_rejects_invalid_region():
    """Validator should reject empty region."""
    config = AeroDriftConfig(aws_region="")
    errors = ConfigValidator.validate(config)
    assert any("region" in e.lower() for e in errors)


def test_config_validator_rejects_invalid_interval():
    """Validator should reject invalid intervals."""
    config = AeroDriftConfig(ingestion_interval=-1)
    errors = ConfigValidator.validate(config)
    assert any("interval" in e.lower() for e in errors)


def test_cloud_state_validator_accepts_valid_state():
    """Validator should accept valid cloud state."""
    state = CloudState(
        vpcs=[Vpc(vpc_id="vpc-123", cidr_block="10.0.0.0/16")],
    )
    errors = CloudStateValidator.validate(state)
    assert errors == []
    assert CloudStateValidator.is_valid(state)


def test_cloud_state_validator_requires_vpc_id():
    """Validator should require VPC ID."""
    state = CloudState(
        vpcs=[Vpc(vpc_id="", cidr_block="10.0.0.0/16")],
    )
    errors = CloudStateValidator.validate(state)
    assert any("vpc_id" in e.lower() for e in errors)


def test_input_sanitizer_sg_id():
    """Sanitizer should validate security group IDs."""
    assert InputSanitizer.sanitize_sg_id("sg-12345") == "sg-12345"
    assert InputSanitizer.sanitize_sg_id("  sg-12345  ") == "sg-12345"
    assert InputSanitizer.sanitize_sg_id("invalid") is None
    assert InputSanitizer.sanitize_sg_id("sg-") is None


def test_input_sanitizer_instance_id():
    """Sanitizer should validate instance IDs."""
    assert InputSanitizer.sanitize_instance_id("i-12345") == "i-12345"
    assert InputSanitizer.sanitize_instance_id("  i-12345  ") == "i-12345"
    assert InputSanitizer.sanitize_instance_id("invalid") is None


def test_input_sanitizer_cidr():
    """Sanitizer should validate CIDR blocks."""
    assert InputSanitizer.sanitize_cidr("10.0.0.0/16") == "10.0.0.0/16"
    assert InputSanitizer.sanitize_cidr("0.0.0.0/0") == "0.0.0.0/0"
    assert InputSanitizer.sanitize_cidr("invalid") is None
    assert InputSanitizer.sanitize_cidr("10.0.0.0") is None