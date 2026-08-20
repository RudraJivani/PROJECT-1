"""
Health Check System
Verifies AeroDrift components are working correctly.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

import boto3

from aerodrift.ingestion import CloudIngestor
from aerodrift.topology import TopologyEngine


class HealthStatus(Enum):
    """Health check status levels."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    status: HealthStatus
    message: str
    duration_ms: float


class HealthChecker:
    """Performs system health checks."""

    def __init__(self, ec2_client: object) -> None:
        self.ec2_client = ec2_client
        self.results: list[HealthCheckResult] = []

    async def check_aws_connectivity(self) -> HealthCheckResult:
        """Check if AWS API is reachable."""
        import time

        try:
            t0 = time.perf_counter()
            ingestor = CloudIngestor(self.ec2_client)
            _ = await ingestor._fetch_vpcs()
            elapsed = (time.perf_counter() - t0) * 1000

            return HealthCheckResult(
                name="AWS Connectivity",
                status=HealthStatus.HEALTHY,
                message="Successfully queried AWS APIs",
                duration_ms=elapsed,
            )
        except Exception as e:
            return HealthCheckResult(
                name="AWS Connectivity",
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to reach AWS: {e}",
                duration_ms=0.0,
            )

    async def check_ingestion_pipeline(self) -> HealthCheckResult:
        """Check if cloud ingestion works end-to-end."""
        import time

        try:
            t0 = time.perf_counter()
            ingestor = CloudIngestor(self.ec2_client)
            state = await ingestor.ingest()
            elapsed = (time.perf_counter() - t0) * 1000

            if not state.vpcs:
                return HealthCheckResult(
                    name="Ingestion Pipeline",
                    status=HealthStatus.DEGRADED,
                    message="Ingestion works but returned no data",
                    duration_ms=elapsed,
                )

            return HealthCheckResult(
                name="Ingestion Pipeline",
                status=HealthStatus.HEALTHY,
                message=f"Ingested {len(state.vpcs)} VPCs in {elapsed:.1f}ms",
                duration_ms=elapsed,
            )
        except Exception as e:
            return HealthCheckResult(
                name="Ingestion Pipeline",
                status=HealthStatus.UNHEALTHY,
                message=f"Ingestion failed: {e}",
                duration_ms=0.0,
            )

    async def check_topology_engine(self) -> HealthCheckResult:
        """Check if topology graph building works."""
        import time

        try:
            t0 = time.perf_counter()
            ingestor = CloudIngestor(self.ec2_client)
            state = await ingestor.ingest()
            engine = TopologyEngine()
            engine.build(state)
            elapsed = (time.perf_counter() - t0) * 1000

            return HealthCheckResult(
                name="Topology Engine",
                status=HealthStatus.HEALTHY,
                message=f"Built graph with {engine.graph.number_of_nodes()} nodes in {elapsed:.1f}ms",
                duration_ms=elapsed,
            )
        except Exception as e:
            return HealthCheckResult(
                name="Topology Engine",
                status=HealthStatus.UNHEALTHY,
                message=f"Graph building failed: {e}",
                duration_ms=0.0,
            )

    async def check_all(self) -> list[HealthCheckResult]:
        """Run all health checks."""
        self.results = [
            await self.check_aws_connectivity(),
            await self.check_ingestion_pipeline(),
            await self.check_topology_engine(),
        ]
        return self.results

    def summary(self) -> dict[str, int]:
        """Return a summary of health check results."""
        return {
            "healthy": sum(1 for r in self.results if r.status == HealthStatus.HEALTHY),
            "degraded": sum(1 for r in self.results if r.status == HealthStatus.DEGRADED),
            "unhealthy": sum(1 for r in self.results if r.status == HealthStatus.UNHEALTHY),
        }

    def is_healthy(self) -> bool:
        """Return True if all checks pass."""
        return all(r.status == HealthStatus.HEALTHY for r in self.results)

    def print_report(self, console: object | None = None) -> None:
        """Print a formatted health report."""
        if console is None:
            from rich.console import Console

            console = Console()

        console.print("\n[bold cyan]AeroDrift Health Check Report[/bold cyan]")
        console.print("=" * 60)

        for result in self.results:
            icon = "✅" if result.status == HealthStatus.HEALTHY else "⚠️" if result.status == HealthStatus.DEGRADED else "❌"
            status_color = (
                "green"
                if result.status == HealthStatus.HEALTHY
                else "yellow"
                if result.status == HealthStatus.DEGRADED
                else "red"
            )
            console.print(f"\n{icon} {result.name}")
            console.print(f"   Status: [{status_color}]{result.status.value}[/{status_color}]")
            console.print(f"   Message: {result.message}")
            console.print(f"   Duration: {result.duration_ms:.2f}ms")

        console.print("\n" + "=" * 60)
        summary = self.summary()
        console.print(f"Summary: {summary['healthy']} healthy, {summary['degraded']} degraded, {summary['unhealthy']} unhealthy")
        console.print("=" * 60 + "\n")