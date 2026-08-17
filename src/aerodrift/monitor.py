"""
Real-Time Monitor
Continuous polling with change detection and alerting.
"""

from __future__ import annotations

import asyncio
import time
from typing import Callable

from aerodrift.drift import DriftDetector, DriftEvent
from aerodrift.drift_analyzer import DriftAnalyzer
from aerodrift.ingestion import CloudIngestor, CloudState
from aerodrift.topology import TopologyEngine


class RealTimeMonitor:
    """Continuously monitors cloud state and triggers callbacks on drift."""

    def __init__(
        self,
        ingestor: CloudIngestor,
        poll_interval: int = 30,
    ) -> None:
        self.ingestor = ingestor
        self.poll_interval = poll_interval
        self.engine = TopologyEngine()
        self.detector = DriftDetector()
        self._running = False
        self._last_state: CloudState | None = None
        self._drift_callbacks: list[Callable[[list[DriftEvent]], None]] = []
        self._poll_count = 0
        self._drift_count = 0

    def on_drift(self, callback: Callable[[list[DriftEvent]], None]) -> None:
        """Register a callback to be called when drift is detected."""
        self._drift_callbacks.append(callback)

    async def start(self) -> None:
        """Start the continuous monitoring loop."""
        self._running = True
        print("[Monitor] Starting real-time monitoring loop")

        try:
            while self._running:
                try:
                    # Poll cloud state
                    t0 = time.perf_counter()
                    state = await self.ingestor.ingest()
                    elapsed = time.perf_counter() - t0

                    self._poll_count += 1
                    print(
                        f"[Monitor] Poll #{self._poll_count}: ingested in {elapsed:.2f}s "
                        f"({len(state.vpcs)} VPCs, {len(state.instances)} instances)"
                    )

                    # Build graph
                    self.engine.build(state)

                    # Detect drift
                    events = self.detector.compare(self.engine)
                    if events:
                        self._drift_count += len(events)
                        print(f"[Monitor] ⚠️  DRIFT DETECTED: {len(events)} new exposure(s)")
                        for callback in self._drift_callbacks:
                            callback(events)

                    self._last_state = state

                except Exception as e:
                    print(f"[Monitor] Error during poll: {e}")

                await asyncio.sleep(self.poll_interval)

        except KeyboardInterrupt:
            print("[Monitor] Stopped by user")
        finally:
            self._running = False

    def stop(self) -> None:
        """Stop the monitoring loop."""
        self._running = False

    def stats(self) -> dict[str, int]:
        """Return monitoring statistics."""
        return {
            "polls": self._poll_count,
            "drifts_detected": self._drift_count,
        }