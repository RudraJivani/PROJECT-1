"""
AeroDrift Daemon
Main loop that continuously monitors cloud topology for drift.
"""

from __future__ import annotations

import asyncio
from typing import Any

import boto3

from aerodrift.config import AeroDriftConfig
from aerodrift.drift import DriftDetector
from aerodrift.ingestion import CloudIngestor
from aerodrift.logger import AuditLogger
from aerodrift.topology import TopologyEngine

try:
    from moto import mock_aws
except ImportError:
    mock_aws = None


class AeroDriftDaemon:
    """Long-running daemon that monitors cloud topology for drift."""

    def __init__(self, config: AeroDriftConfig | None = None) -> None:
        self.config = config or AeroDriftConfig()
        self.logger = AuditLogger()
        self.detector = DriftDetector()
        self.engine = TopologyEngine()
        self.ingestor: CloudIngestor | None = None
        self._running = False

    def _setup_aws_client(self) -> Any:
        """Create a boto3 EC2 client, either real or mocked."""
        if self.config.use_mock_aws:
            if mock_aws is None:
                raise RuntimeError("Install moto (`pip install moto`) to use mock AWS.")
            self._mock_context = mock_aws()
            self._mock_context.__enter__()
            return boto3.client("ec2", region_name=self.config.aws_region)
        else:
            # Real AWS (requires credentials to be configured)
            return boto3.client("ec2", region_name=self.config.aws_region)

    async def run(self) -> None:
        """Start the daemon's main monitoring loop."""
        self._running = True
        ec2_client = self._setup_aws_client()
        self.ingestor = CloudIngestor(ec2_client)

        self.logger.logger.info("AeroDrift daemon started")

        try:
            while self._running:
                # Ingest
                try:
                    state = await self.ingestor.ingest()
                    self.engine.build(state)
                    self.logger.log_ingestion(
                        len(state.vpcs),
                        len(state.security_groups),
                        len(state.instances),
                    )
                except Exception as e:
                    self.logger.logger.error(f"Ingestion failed: {e}")
                    await asyncio.sleep(self.config.ingestion_interval)
                    continue

                # Detect drift
                try:
                    events = self.detector.compare(self.engine)
                    for event in events:
                        self.logger.log_drift_detected(event)
                except Exception as e:
                    self.logger.logger.error(f"Drift detection failed: {e}")

                await asyncio.sleep(self.config.detection_interval)

        except KeyboardInterrupt:
            self.logger.logger.info("Daemon stopped by user")
        finally:
            self._running = False
            if self.config.use_mock_aws:
                self._mock_context.__exit__(None, None, None)

    def stop(self) -> None:
        """Stop the daemon gracefully."""
        self._running = False
        self.logger.logger.info("Stopping AeroDrift daemon")