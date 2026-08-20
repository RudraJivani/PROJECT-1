"""
Configuration and Data Validator
Ensures all settings and data are valid before use.
"""

from __future__ import annotations

from typing import Any

from aerodrift.config import AeroDriftConfig
from aerodrift.ingestion import CloudState


class ConfigValidator:
    """Validates AeroDriftConfig."""

    @staticmethod
    def validate(config: AeroDriftConfig) -> list[str]:
        """Validate configuration. Return list of error messages (empty if valid)."""
        errors: list[str] = []

        # AWS settings
        if not config.aws_region:
            errors.append("aws_region cannot be empty")
        if config.ingestion_interval <= 0:
            errors.append("ingestion_interval must be > 0")
        if config.detection_interval <= 0:
            errors.append("detection_interval must be > 0")

        # Logging
        if config.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            errors.append(f"Invalid log_level: {config.log_level}")

        # Remediation
        if config.auto_remediate and not isinstance(config.dry_run, bool):
            errors.append("dry_run must be a boolean")

        return errors

    @staticmethod
    def is_valid(config: AeroDriftConfig) -> bool:
        """Return True if config is valid."""
        return len(ConfigValidator.validate(config)) == 0


class CloudStateValidator:
    """Validates ingested CloudState."""

    @staticmethod
    def validate(state: CloudState) -> list[str]:
        """Validate cloud state. Return list of error messages."""
        errors: list[str] = []

        if not isinstance(state.vpcs, list):
            errors.append("vpcs must be a list")
        if not isinstance(state.subnets, list):
            errors.append("subnets must be a list")
        if not isinstance(state.security_groups, list):
            errors.append("security_groups must be a list")
        if not isinstance(state.instances, list):
            errors.append("instances must be a list")

        # Validate VPCs
        for vpc in state.vpcs:
            if not vpc.vpc_id:
                errors.append("VPC must have vpc_id")
            if not vpc.cidr_block:
                errors.append("VPC must have cidr_block")

        # Validate security groups
        for sg in state.security_groups:
            if not sg.group_id:
                errors.append("SecurityGroup must have group_id")
            if not sg.vpc_id:
                errors.append("SecurityGroup must have vpc_id")

        # Validate instances
        for inst in state.instances:
            if not inst.instance_id:
                errors.append("Instance must have instance_id")
            if not inst.vpc_id:
                errors.append("Instance must have vpc_id")

        return errors

    @staticmethod
    def is_valid(state: CloudState) -> bool:
        """Return True if state is valid."""
        return len(CloudStateValidator.validate(state)) == 0


class InputSanitizer:
    """Sanitizes and validates user input."""

    @staticmethod
    def sanitize_sg_id(sg_id: str) -> str | None:
        """Validate and return a security group ID."""
        if not isinstance(sg_id, str):
            return None
        sg_id = sg_id.strip()
        if not sg_id.startswith("sg-"):
            return None
        if len(sg_id) < 5:
            return None
        return sg_id

    @staticmethod
    def sanitize_instance_id(inst_id: str) -> str | None:
        """Validate and return an instance ID."""
        if not isinstance(inst_id, str):
            return None
        inst_id = inst_id.strip()
        if not inst_id.startswith("i-"):
            return None
        if len(inst_id) < 5:
            return None
        return inst_id

    @staticmethod
    def sanitize_cidr(cidr: str) -> str | None:
        """Validate and return a CIDR block."""
        if not isinstance(cidr, str):
            return None
        cidr = cidr.strip()
        if "/" not in cidr:
            return None
        try:
            parts = cidr.split("/")
            if len(parts) != 2:
                return None
            _ = int(parts[1])  # Validate prefix length
            return cidr
        except (ValueError, IndexError):
            return None