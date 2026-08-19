"""
Remediation Planner
Plans the exact steps needed to fix each drift event.
Does NOT execute — just plans what should happen.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from aerodrift.drift import DriftEvent


class RemediationAction(Enum):
    """Types of remediation actions."""

    REVOKE_INGRESS = "revoke_security_group_ingress"
    MODIFY_NACL = "modify_network_acl"
    ISOLATE_INSTANCE = "isolate_instance"
    ALERT_ONLY = "alert_only"


@dataclass
class RemediationStep:
    """A single remediation action to take."""

    action: RemediationAction
    target_id: str
    target_type: str
    description: str
    parameters: dict = field(default_factory=dict)
    risk_level: str = "LOW"  # LOW, MEDIUM, HIGH, CRITICAL
    requires_approval: bool = False

    def __str__(self) -> str:
        return f"[{self.action.value}] {self.description}"


@dataclass
class RemediationPlan:
    """Complete plan for remediating a drift event."""

    drift_event: DriftEvent
    steps: list[RemediationStep] = field(default_factory=list)
    estimated_time_seconds: int = 0
    rollback_steps: list[RemediationStep] = field(default_factory=list)
    approval_required: bool = False

    def add_step(self, step: RemediationStep) -> None:
        """Add a remediation step to the plan."""
        self.steps.append(step)
        if step.requires_approval:
            self.approval_required = True
        self.estimated_time_seconds += 5  # Estimate 5 seconds per step

    def summary(self) -> str:
        """Human-readable summary of the plan."""
        lines = [
            f"Remediation Plan for {self.drift_event.node_label}",
            f"  Severity: {self.drift_event.severity}",
            f"  Steps: {len(self.steps)}",
            f"  Estimated time: {self.estimated_time_seconds}s",
            f"  Requires approval: {self.approval_required}",
        ]
        return "\n".join(lines)


class RemediationPlanner:
    """Creates remediation plans for drift events."""

    def plan_for_event(self, event: DriftEvent) -> RemediationPlan:
        """Generate a remediation plan for a single drift event."""
        plan = RemediationPlan(drift_event=event)

        # For each offending security group, plan a revocation
        for sg_id in event.offending_security_groups:
            step = RemediationStep(
                action=RemediationAction.REVOKE_INGRESS,
                target_id=sg_id,
                target_type="security_group",
                description=f"Revoke public ingress rule(s) on {sg_id}",
                parameters={
                    "group_id": sg_id,
                    "cidr": "0.0.0.0/0",  # Assume public exposure
                    "protocol": "tcp",
                },
                risk_level="LOW",
                requires_approval=False,
            )
            plan.add_step(step)

            # Add rollback step
            rollback = RemediationStep(
                action=RemediationAction.REVOKE_INGRESS,
                target_id=sg_id,
                target_type="security_group",
                description=f"[ROLLBACK] Re-authorize ingress on {sg_id}",
                parameters={
                    "group_id": sg_id,
                    "cidr": "0.0.0.0/0",
                    "protocol": "tcp",
                },
                risk_level="LOW",
            )
            plan.rollback_steps.append(rollback)

        return plan

    def plan_for_events(self, events: list[DriftEvent]) -> list[RemediationPlan]:
        """Generate plans for multiple drift events."""
        return [self.plan_for_event(event) for event in events]

    def merge_plans(self, plans: list[RemediationPlan]) -> RemediationPlan:
        """Merge multiple plans into one batch operation."""
        if not plans:
            raise ValueError("Cannot merge empty plan list")

        first = plans[0]
        merged = RemediationPlan(drift_event=first.drift_event)

        for plan in plans:
            for step in plan.steps:
                merged.add_step(step)
            merged.approval_required = merged.approval_required or plan.approval_required

        return merged 