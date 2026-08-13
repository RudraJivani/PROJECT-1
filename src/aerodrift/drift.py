"""
Drift Detection
Compares two TopologyEngine graph snapshots and reports any node that has
newly become reachable from the internet.
"""

from __future__ import annotations

from dataclasses import dataclass

import networkx as nx

from aerodrift.topology import INTERNET_NODE, TopologyEngine


@dataclass
class DriftEvent:
    node_id: str
    node_label: str
    node_type: str
    exposure_path: list[str]
    offending_security_groups: list[str]

    @property
    def severity(self) -> str:
        """An exposed instance is more severe than an exposed security group."""
        return "CRITICAL" if self.node_type == "instance" else "WARNING"


class DriftDetector:
    """Stateful: remembers the last-known-good set of internet-reachable
    nodes and reports new arrivals on each comparison."""

    def __init__(self) -> None:
        self._previously_exposed: set[str] = set()
        self._baselined = False

    def reset_baseline(self, engine: TopologyEngine) -> None:
        """Record the current exposure set as 'expected' without raising
        any drift events for it."""
        self._previously_exposed = self._currently_exposed(engine.graph)
        self._baselined = True

    @staticmethod
    def _currently_exposed(graph: nx.DiGraph) -> set[str]:
        if INTERNET_NODE not in graph:
            return set()
        reachable = nx.descendants(graph, INTERNET_NODE)
        return {n for n in reachable if graph.nodes[n].get("type") in ("instance", "security_group")}

    def compare(self, engine: TopologyEngine) -> list[DriftEvent]:
        """Compare the engine's current graph against the last baseline.
        Returns one DriftEvent per node that is newly internet-reachable
        since the last call."""
        graph = engine.graph
        currently_exposed = self._currently_exposed(graph)

        if not self._baselined:
            self.reset_baseline(engine)
            return []

        new_nodes = currently_exposed - self._previously_exposed
        self._previously_exposed = currently_exposed

        events = []
        for node_id in new_nodes:
            attrs = graph.nodes[node_id]
            path = engine.exposure_path(node_id) or []
            offenders = engine.offending_security_groups(node_id)
            events.append(
                DriftEvent(
                    node_id=node_id,
                    node_label=str(attrs.get("label", node_id)),
                    node_type=str(attrs.get("type", "unknown")),
                    exposure_path=path,
                    offending_security_groups=offenders,
                )
            )
        return events