"""
Tests for incident report generation.
"""

from aerodrift.drift import DriftEvent
from aerodrift.remediation_planner import RemediationPlanner
from aerodrift.report_generator import IncidentReport, ReportGenerator


def test_incident_report_creation():
    """Should create an incident report."""
    event = DriftEvent(
        node_id="i-12345",
        node_label="prod-db",
        node_type="instance",
        exposure_path=["internet:0.0.0.0/0", "sg-abc", "i-12345"],
        offending_security_groups=["sg-abc"],
    )

    report = IncidentReport(event)
    assert report.event == event
    assert report.report_id is not None


def test_incident_report_markdown():
    """Should export report as Markdown."""
    event = DriftEvent(
        node_id="i-12345",
        node_label="prod-db",
        node_type="instance",
        exposure_path=["internet:0.0.0.0/0", "sg-abc", "i-12345"],
        offending_security_groups=["sg-abc"],
    )

    report = IncidentReport(event)
    markdown = report.to_markdown()

    assert "Incident Report" in markdown
    assert "prod-db" in markdown
    assert "CRITICAL" in markdown


def test_incident_report_text():
    """Should export report as plain text."""
    event = DriftEvent(
        node_id="i-12345",
        node_label="prod-db",
        node_type="instance",
        exposure_path=["internet:0.0.0.0/0", "sg-abc", "i-12345"],
        offending_security_groups=["sg-abc"],
    )

    report = IncidentReport(event)
    text = report.to_text()

    assert "INCIDENT REPORT" in text
    assert "prod-db" in text


def test_report_generator_summary():
    """Should generate summary report for multiple events."""
    events = [
        DriftEvent(
            node_id="i-111",
            node_label="db-1",
            node_type="instance",
            exposure_path=["internet:0.0.0.0/0", "sg-a", "i-111"],
            offending_security_groups=["sg-a"],
        ),
        DriftEvent(
            node_id="i-222",
            node_label="db-2",
            node_type="instance",
            exposure_path=["internet:0.0.0.0/0", "sg-b", "i-222"],
            offending_security_groups=["sg-b"],
        ),
    ]

    summary = ReportGenerator.generate_summary_report(events)

    assert "SUMMARY" in summary
    assert "2" in summary  # Total incidents
    assert "db-1" in summary
    assert "db-2" in summary


def test_report_generator_audit_trail():
    """Should generate audit trail."""
    event = DriftEvent(
        node_id="i-12345",
        node_label="prod-db",
        node_type="instance",
        exposure_path=["internet:0.0.0.0/0", "sg-abc", "i-12345"],
        offending_security_groups=["sg-abc"],
    )

    trail = ReportGenerator.generate_audit_trail([event])

    assert "AUDIT TRAIL" in trail
    assert "prod-db" in trail