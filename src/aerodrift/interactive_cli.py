"""
Interactive CLI
Menu-driven interface for viewing incidents and planning remediation.
"""

from __future__ import annotations

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.table import Table

from aerodrift.dashboard import DriftAwareDashboard
from aerodrift.drift import DriftEvent
from aerodrift.remediation_planner import RemediationPlanner
from aerodrift.report_generator import IncidentReport, ReportGenerator
from aerodrift.styles import AeroDriftStyles
from aerodrift.topology import TopologyEngine


class InteractiveCLI:
    """Menu-driven CLI for incident management."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self.dashboard = DriftAwareDashboard(console)
        self.planner = RemediationPlanner()

    def show_main_menu(self, engine: TopologyEngine) -> None:
        """Display main menu and handle user choices."""
        while True:
            self.console.print("\n" + "=" * 70)
            self.console.print(
                "[bold cyan]AeroDrift — Interactive Incident Management[/bold cyan]"
            )
            self.console.print("=" * 70)
            self.console.print("\nOptions:")
            self.console.print("  [1] View Dashboard")
            self.console.print("  [2] View Drift Events")
            self.console.print("  [3] Plan Remediation")
            self.console.print("  [4] Generate Report")
            self.console.print("  [5] View Audit Trail")
            self.console.print("  [6] Exit")

            choice = Prompt.ask("Select option", choices=["1", "2", "3", "4", "5", "6"])

            if choice == "1":
                self.show_dashboard(engine)
            elif choice == "2":
                self.show_drift_events()
            elif choice == "3":
                self.show_remediation_planning()
            elif choice == "4":
                self.show_report()
            elif choice == "5":
                self.show_audit_trail()
            elif choice == "6":
                self.console.print("[green]✅ Exiting AeroDrift[/green]")
                break

    def show_dashboard(self, engine: TopologyEngine) -> None:
        """Display the full dashboard."""
        self.console.clear()
        self.dashboard.print_full_dashboard(engine)
        _ = Prompt.ask("\nPress Enter to continue")

    def show_drift_events(self) -> None:
        """List all detected drift events."""
        self.console.clear()

        if not self.dashboard.all_drift_events:
            self.console.print("[green]✅ No drift events detected[/green]")
            _ = Prompt.ask("\nPress Enter to continue")
            return

        table = Table(title="🚨 All Drift Events", show_header=True, header_style="bold red")
        table.add_column("#", style="cyan")
        table.add_column("Resource", style="yellow")
        table.add_column("Type", style="white")
        table.add_column("Severity", justify="center")
        table.add_column("Offenders", style="red")

        for i, event in enumerate(self.dashboard.all_drift_events, 1):
            severity_style = AeroDriftStyles.severity_to_style(event.severity)
            severity_text = f"[{severity_style}]{event.severity}[/{severity_style}]"
            offenders = ", ".join(event.offending_security_groups[:2])
            if len(event.offending_security_groups) > 2:
                offenders += "..."

            table.add_row(str(i), event.node_label, event.node_type, severity_text, offenders)

        self.console.print(table)
        _ = Prompt.ask("\nPress Enter to continue")

    def show_remediation_planning(self) -> None:
        """Plan remediation for selected incidents."""
        self.console.clear()

        if not self.dashboard.all_drift_events:
            self.console.print("[yellow]⚠️  No drift events to remediate[/yellow]")
            _ = Prompt.ask("\nPress Enter to continue")
            return

        self.console.print("\n[bold cyan]Remediation Planner[/bold cyan]")
        self.console.print(f"Available incidents: {len(self.dashboard.all_drift_events)}")

        # For demo, plan all events
        self.console.print("\nGenerating remediation plans for all incidents...\n")

        plans = self.planner.plan_for_events(self.dashboard.all_drift_events)

        for i, plan in enumerate(plans, 1):
            self.console.print(f"\n[bold yellow]Plan {i}: {plan.drift_event.node_label}[/bold yellow]")
            self.console.print(f"  Severity: {plan.drift_event.severity}")
            self.console.print(f"  Steps: {len(plan.steps)}")
            self.console.print(f"  Estimated time: {plan.estimated_time_seconds}s")

            for j, step in enumerate(plan.steps, 1):
                self.console.print(f"    Step {j}: {step.description}")

        _ = Prompt.ask("\nPress Enter to continue")

    def show_report(self) -> None:
        """Generate and display an incident report."""
        self.console.clear()

        if not self.dashboard.all_drift_events:
            self.console.print("[yellow]⚠️  No incidents to report[/yellow]")
            _ = Prompt.ask("\nPress Enter to continue")
            return

        summary = ReportGenerator.generate_summary_report(self.dashboard.all_drift_events)
        self.console.print(summary)

        _ = Prompt.ask("\nPress Enter to continue")

    def show_audit_trail(self) -> None:
        """Display the audit trail."""
        self.console.clear()

        if not self.dashboard.all_drift_events:
            self.console.print("[green]✅ No audit events[/green]")
            _ = Prompt.ask("\nPress Enter to continue")
            return

        trail = ReportGenerator.generate_audit_trail(self.dashboard.all_drift_events)
        self.console.print(trail)

        _ = Prompt.ask("\nPress Enter to continue")