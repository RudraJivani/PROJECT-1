"""
Configuration module for AeroDrift.
Handles AWS region, polling intervals, and other settings.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AeroDriftConfig:
    """Central configuration for the AeroDrift daemon."""

    # AWS settings
    aws_region: str = "us-east-1"
    
    # Polling settings (in seconds)
    ingestion_interval: int = 30  # How often to re-ingest cloud state
    detection_interval: int = 10  # How often to check for drift
    
    # Graph settings
    use_mock_aws: bool = True  # Use moto-mocked AWS for development
    
    # Remediation settings
    auto_remediate: bool = False  # Automatically fix drift without approval
    dry_run: bool = True  # If auto_remediate is True, show what would happen without doing it
    
    # Logging
    log_level: str = "INFO"
    log_file: str | None = None  # None = print to console only
    
    # CLI settings
    verbose: bool = False
    color_output: bool = True


# Default config instance
DEFAULT_CONFIG = AeroDriftConfig()