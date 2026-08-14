"""
Audit logging for AeroDrift.
Records all ingestions, detections, and remediation actions.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from aerodrift.drift import DriftEvent


class AuditLogger:
    """Structured logging of all AeroDrift events for auditing."""

    def __init__(self, log_file: Path | None = None) -> None:
        self.log_file = log_file
        self.events: list[dict] = []
        
        # Set up Python's built-in logging
        self.logger = logging.getLogger("aerodrift")
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def log_ingestion(self, num_vpcs: int, num_sgs: int, num_instances: int) -> None:
        """Log a successful cloud ingestion."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "ingestion",
            "vpcs": num_vpcs,
            "security_groups": num_sgs,
            "instances": num_instances,
        }
        self.events.append(event)
        self.logger.info(
            f"Ingested cloud state: {num_vpcs} VPCs, {num_sgs} SGs, {num_instances} instances"
        )

    def log_drift_detected(self, event: DriftEvent) -> None:
        """Log a single drift event."""
        log_event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "drift_detected",
            "severity": event.severity,
            "node_id": event.node_id,
            "node_label": event.node_label,
            "node_type": event.node_type,
            "exposure_path": event.exposure_path,
            "offending_sgs": event.offending_security_groups,
        }
        self.events.append(log_event)
        self.logger.warning(
            f"[{event.severity}] Drift detected on {event.node_type} '{event.node_label}'"
        )

    def log_remediation_executed(self, sg_id: str, action: str) -> None:
        """Log a remediation action."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "event_type": "remediation_executed",
            "security_group_id": sg_id,
            "action": action,
        }
        self.events.append(event)
        self.logger.info(f"Remediation executed on {sg_id}: {action}")

    def export_audit_trail(self) -> str:
        """Export full audit trail as JSON."""
        return json.dumps(self.events, indent=2)