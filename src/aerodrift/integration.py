"""
Integration Module
Ties all AeroDrift components together into a unified system.
"""

from __future__ import annotations

import asyncio
from typing import Callable

from aerodrift.config import AeroDriftConfig
from aerodrift.dashboard import DriftAwareDashboard
from aerodrift.drift import DriftDetector, DriftEvent
from aerodrift.drift_analyzer import DriftAnalyzer
from aerodrift.health_check import HealthChecker
from aerodrift.ingestion import CloudIngestor, CloudState
from aerodrift.logger import AuditLogger
from aerodrift.monitor import RealTimeMonitor
from aerodrift.remediation_planner import RemediationPlanner
from aerodrift.topology import TopologyEngine
from aerodrift.validator import CloudStateValidator, ConfigValidator


class AeroDriftSystem:
    """Complete integrated AeroDrift system."""

    def __init__(self, config: AeroDriftConfig | None = None) -> None:
        self.config = config or AeroDriftConfig()

        # Validate config
        errors = ConfigValidator.validate(self.config)
        if errors:
            raise ValueError(f"Invalid config: {', '.join(errors)}")

        # Initialize components
        self.logger = AuditLogger()
        self.engine = TopologyEngine()
        self.detector = DriftDetector()
        self.analyzer = DriftAnalyzer(self.engine)
        self.planner = RemediationPlanner()
        self.dashboard = DriftAwareDashboard()
        self.ingestor: CloudIngestor | None = None
        self.monitor: RealTimeMonitor | None = None
        self.health_checker: HealthChecker | None = None

        self._running = False
        self._last_state: CloudState | None = None
        self._event_callbacks: list[Callable[[list[DriftEvent]], None]] = []

        self.logger.logger.info(f"AeroDriftSystem initialized with config: {self.config}")

    def setup_aws_client(self, ec2_client: object) -> None:
        """Setup AWS client for ingestion."""
        self.ingestor = CloudIngestor(ec2_client)
        self.health_checker = HealthChecker(ec2_client)
        self.monitor = RealTimeMonitor(self.ingestor, self.config.ingestion_interval)
        self.logger.logger.info("AWS client configured")

    async def run_health_checks(self) -> bool:
        """Run all health checks. Return True if healthy."""
        if not self.health_checker:
            self.logger.logger.error("Health checker not configured")
            return False

        results = await self.health_checker.check_all()
        is_healthy = self.health_checker.is_healthy()

        if is_healthy:
            self.logger.logger.info("✅ All health checks passed")
        else:
            self.logger.logger.warning("⚠️  Some health checks failed")

        return is_healthy

    def on_drift(self, callback: Callable[[list[DriftEvent]], None]) -> None:
        """Register a callback for drift events."""
        self._event_callbacks.append(callback)

    async def ingest_and_analyze(self) -> tuple[CloudState | None, list[DriftEvent]]:
        """Ingest cloud state and analyze for drift."""
        if not self.ingestor:
            self.logger.logger.error("Ingestor not configured")
            return None, []

        try:
            # Ingest
            state = await self.ingestor.ingest()

            # Validate
            errors = CloudStateValidator.validate(state)
            if errors:
                self.logger.logger.error(f"Invalid cloud state: {errors}")
                return None, []

            # Build graph
            self.engine.build(state)

            # Log ingestion
            self.logger.log_ingestion(
                len(state.vpcs),
                len(state.security_groups),
                len(state.instances),
            )

            # Detect drift
            events = self.detector.compare(self.engine)

            # Log drift events
            for event in events:
                self.logger.log_drift_detected(event)
                self.dashboard.record_drift([event])

            # Trigger callbacks
            for callback in self._event_callbacks:
                callback(events)

            self._last_state = state
            return state, events

        except Exception as e:
            self.logger.logger.error(f"Ingest and analyze failed: {e}")
            return None, []

    async def start_monitoring(self) -> None:
        """Start continuous real-time monitoring."""
        if not self.monitor:
            self.logger.logger.error("Monitor not configured")
            return

        self._running = True
        self.monitor.on_drift(self._on_drift_callback)

        self.logger.logger.info("Starting continuous monitoring")
        await self.monitor.start()
        self._running = False

    def stop_monitoring(self) -> None:
        """Stop the monitoring loop."""
        if self.monitor:
            self.monitor.stop()
        self._running = False
        self.logger.logger.info("Monitoring stopped")

    def _on_drift_callback(self, events: list[DriftEvent]) -> None:
        """Internal callback when drift is detected."""
        for event in events:
            self.logger.log_drift_detected(event)
            self.dashboard.record_drift([event])

        # Trigger user callbacks
        for callback in self._event_callbacks:
            callback(events)

    def get_remediation_plans(self) -> list:
        """Get remediation plans for all detected drift."""
        if not self.dashboard.all_drift_events:
            return []
        return self.planner.plan_for_events(self.dashboard.all_drift_events)

    def system_status(self) -> dict:
        """Return overall system status."""
        return {
            "running": self._running,
            "configured": self.ingestor is not None,
            "drift_events": len(self.dashboard.all_drift_events),
            "graph_nodes": self.engine.graph.number_of_nodes(),
            "graph_edges": self.engine.graph.number_of_edges(),
        }