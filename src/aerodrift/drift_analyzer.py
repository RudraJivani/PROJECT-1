"""
Drift Analyzer
Deep analysis of security group rule changes to classify drift events.
Identifies *which specific rules* changed and *why* it's a problem.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aerodrift.ingestion import SecurityGroup
from aerodrift.topology import TopologyEngine


@dataclass
class RuleChange:
    """A single ingress rule that was added to a security group."""

    security_group_id: str
    security_group_name: str
    protocol: str
    port_range: str
    cidr: str
    is_public: bool
    risk_level: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"

    @property
    def description(self) -> str:
        """Human-readable description of this rule change."""
        public_str = "from anywhere (0.0.0.0/0)" if self.is_public else f"from {self.cidr}"
        return (
            f"Port {self.port_range}/{self.protocol} opened {public_str} "
            f"on {self.security_group_name} ({self.security_group_id})"
        )


class DriftAnalyzer:
    """Analyzes what changed between two snapshots to explain drift."""

    def __init__(self, engine: TopologyEngine) -> None:
        self.engine = engine

    @staticmethod
    def _classify_risk(port: int, protocol: str, is_public: bool) -> str:
        """Classify risk level based on port, protocol, and exposure."""
        if not is_public:
            return "LOW"

        critical_ports = {3306, 5432, 3389, 1433, 27017, 6379, 9042}  # DB ports
        if port in critical_ports:
            return "CRITICAL"

        if protocol == "tcp" and port in {22, 3389, 80, 443}:
            return "HIGH"

        return "MEDIUM"

    def detect_new_public_ingress(
        self, old_sgs: list[SecurityGroup], new_sgs: list[SecurityGroup]
    ) -> list[RuleChange]:
        """
        Compare two snapshots of security groups.
        Return all newly-added public ingress rules.
        """
        old_rules_map = {
            sg.group_id: {(r.from_port, r.cidr) for r in sg.ingress}
            for sg in old_sgs
        }

        changes: list[RuleChange] = []

        for new_sg in new_sgs:
            old_rules = old_rules_map.get(new_sg.group_id, set())
            new_rules = {(r.from_port, r.cidr) for r in new_sg.ingress}

            # Find rules that are new
            for rule in new_sg.ingress:
                if (rule.from_port, rule.cidr) not in old_rules:
                    is_public = rule.cidr in ("0.0.0.0/0", "::/0")
                    risk = self._classify_risk(rule.from_port, rule.protocol, is_public)

                    changes.append(
                        RuleChange(
                            security_group_id=new_sg.group_id,
                            security_group_name=new_sg.group_name or new_sg.group_id,
                            protocol=rule.protocol,
                            port_range=f"{rule.from_port}-{rule.to_port}",
                            cidr=rule.cidr,
                            is_public=is_public,
                            risk_level=risk,
                        )
                    )

        return sorted(changes, key=lambda c: (c.is_public, c.risk_level), reverse=True)

    def explain_exposure(self, target_instance_id: str) -> str:
        """Generate a human-readable explanation of why something is exposed."""
        if not self.engine.path_exists_from_internet(target_instance_id):
            return f"Instance {target_instance_id} is NOT exposed to the internet."

        path = self.engine.exposure_path(target_instance_id)
        if not path:
            return f"Cannot determine path to {target_instance_id}."

        sgs = self.engine.offending_security_groups(target_instance_id)
        explanation = (
            f"Instance {target_instance_id} IS EXPOSED to the internet via:\n"
            f"  Path: {' → '.join(path)}\n"
            f"  Offending SGs: {', '.join(sgs)}\n"
        )
        return explanation 