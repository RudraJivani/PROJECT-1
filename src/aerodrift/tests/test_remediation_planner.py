"""
Tests for the RemediationPlanner.
"""

from aerodrift.drift import DriftEvent
from aerodrift.remediation_planner import (
    RemediationAction,
    RemediationPlanner,
    RemediationStep,
)


def test_remediation_step_creation():
    """Should create remediation steps with proper attributes."""
    step = RemediationStep(
        action=RemediationAction.REVOKE_INGRESS,
        target_id="sg-12345",
        target_type="security_group",
        description="Revoke public ingress",
        risk_level="LOW",
    )

    assert step.action == RemediationAction.REVOKE_INGRESS
    assert step.target_id == "sg-12345"
    assert not step.requires_approval


def test_remediation_planner_creates_plan():
    """Planner should generate a plan for a drift event."""
    event = DriftEvent(
        node_id="i-12345",
        node_label="prod-db",
        node_type="instance",
        exposure_path=["internet:0.0.0.0/0", "sg-abc", "i-12345"],
        offending_security_groups=["sg-abc"],
    )

    planner = RemediationPlanner()
    plan = planner.plan_for_event(event)

    assert plan.drift_event == event
    assert len(plan.steps) > 0
    assert plan.steps[0].action == RemediationAction.REVOKE_INGRESS


def test_remediation_planner_multiple_sgs():
    """Planner should handle multiple offending security groups."""
    event = DriftEvent(
        node_id="i-12345",
        node_label="prod-db",
        node_type="instance",
        exposure_path=["internet:0.0.0.0/0", "sg-abc", "i-12345"],
        offending_security_groups=["sg-abc", "sg-xyz"],
    )

    planner = RemediationPlanner()
    plan = planner.plan_for_event(event)

    assert len(plan.steps) == 2  # One step per SG
    assert len(plan.rollback_steps) == 2


def test_remediation_plan_summary():
    """Plan should generate a readable summary."""
    event = DriftEvent(
        node_id="i-12345",
        node_label="prod-db",
        node_type="instance",
        exposure_path=["internet:0.0.0.0/0", "sg-abc", "i-12345"],
        offending_security_groups=["sg-abc"],
    )

    planner = RemediationPlanner()
    plan = planner.plan_for_event(event)
    summary = plan.summary()

    assert "prod-db" in summary
    assert "1" in summary  # Number of steps


def test_remediation_planner_merges_plans():
    """Planner should merge multiple plans."""
    event1 = DriftEvent(
        node_id="i-111",
        node_label="db-1",
        node_type="instance",
        exposure_path=["internet:0.0.0.0/0", "sg-a", "i-111"],
        offending_security_groups=["sg-a"],
    )
    event2 = DriftEvent(
        node_id="i-222",
        node_label="db-2",
        node_type="instance",
        exposure_path=["internet:0.0.0.0/0", "sg-b", "i-222"],
        offending_security_groups=["sg-b"],
    )

    planner = RemediationPlanner()
    plan1 = planner.plan_for_event(event1)
    plan2 = planner.plan_for_event(event2)

    merged = planner.merge_plans([plan1, plan2])
    assert len(merged.steps) == 2 