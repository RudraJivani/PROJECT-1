"""
Enhanced Dashboard with Real-Time Updates
Renders cloud topology with live drift highlighting.
"""

from __future__ import annotations

from datetime import datetime

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.tree import Tree

from aerodrift.drift import DriftEvent
from aerodrift.styles import AeroDriftStyles
from aerodrift.topology import TopologyEngine


class DriftAwareDashboard:
    """Real-time dashboard that highlights exposed resources in red."""

    def __init__(self, console: Console | None = None) -> None:
        self.console = console or Console()
        self.exposed_instances: set[str] = set()
        self.exposed_sgs: set[str] = set()
        self.all_drift_events: list[DriftEvent] = []
        self.last_update = datetime.now()

    def record_drift(self, events: list[DriftEvent]) -> None:
        """Record drift events to be shown on dashboard."""
        for event in events:
            self.all_drift_events.append(event)
            if event.node_type == "instance":
                self.exposed_instances.add(event.node_id)
            elif event.node_type == "security_group":
                self.exposed_sgs.add(event.node_id)
        self.last_update = datetime.now()

    def render_topology_with_exposure(self, engine: TopologyEngine) -> Tree:
        """Render topology tree with exposed resources highlighted in red."""
        tree = Tree("☁️ Cloud Topology (Red = Exposed to Internet)")

        # Add internet node
        internet = tree.add(f"{AeroDriftStyles.ICON_INTERNET} Internet")

        # Group SGs by exposure
        for node_id, attrs in engine.graph.nodes(data=True):
            node_type = attrs.get("type", "unknown")
            label = attrs.get("label", node_id)

            if node_type == "security_group":
                is_exposed = engine.path_exists_from_internet(node_id)
                if is_exposed:
                    sg_icon = AeroDriftStyles.ICON_SG_EXPOSED
                    sg_text = Text(f"{sg_icon} {label} ({node_id})", style=AeroDriftStyles.EXPOSED)
                    sg_branch = internet.add(sg_text)

                    # Show attached instances
                    for inst_id, inst_attrs in engine.graph.nodes(data=True):
                        if inst_attrs.get("type") == "instance":
                            # Check if this instance is protected by this SG
                            if any(
                                engine.graph.has_edge(node_id, inst_id)
                                for _ in [None]
                            ):
                                inst_exposed = engine.path_exists_from_internet(inst_id)
                                inst_icon = AeroDriftStyles.status_to_icon(inst_exposed)
                                inst_style = AeroDriftStyles.status_to_style(inst_exposed)
                                inst_label = inst_attrs.get("label", inst_id)
                                inst_text = Text(
                                    f"{inst_icon} {inst_label}",
                                    style=inst_style,
                                )
                                sg_branch.add(inst_text)

        # Add internal resources (not exposed)
        internal = tree.add("🔒 Protected Resources")
        for node_id, attrs in engine.graph.nodes(data=True):
            if attrs.get("type") == "instance":
                if not engine.path_exists_from_internet(node_id):
                    label = attrs.get("label", node_id)
                    text = Text(
                        f"{AeroDriftStyles.ICON_INSTANCE_SAFE} {label}",
                        style=AeroDriftStyles.SAFE,
                    )
                    internal.add(text)

        return tree

    def render_drift_summary(self) -> Panel:
        """Render a summary of detected drift events."""
        if not self.all_drift_events:
            summary_text = Text("✅ No drift detected", style=AeroDriftStyles.SAFE)
            return Panel(summary_text, title="Drift Summary", border_style="green")

        lines = []
        lines.append(f"Total Drift Events: {len(self.all_drift_events)}")
        lines.append("")

        critical_count = sum(
            1 for e in self.all_drift_events if e.severity == "CRITICAL"
        )
        high_count = sum(1 for e in self.all_drift_events if e.severity == "HIGH")

        if critical_count > 0:
            text = Text(f"🔴 CRITICAL: {critical_count}", style=AeroDriftStyles.CRITICAL)
            lines.append(text)
        if high_count > 0:
            text = Text(f"🟠 HIGH: {high_count}", style=AeroDriftStyles.HIGH)
            lines.append(text)

        lines.append(f"Last Update: {self.last_update.strftime('%H:%M:%S')}")

        content = Text()
        for i, line in enumerate(lines):
            if isinstance(line, Text):
                content.append(line)
            else:
                content.append(str(line))
            if i < len(lines) - 1:
                content.append("\n")

        return Panel(
            content,
            title="🚨 Drift Summary",
            border_style="red" if self.all_drift_events else "green",
        )

    def render_exposed_resources_table(self) -> Table:
        """Render a table of all exposed resources."""
        table = AeroDriftStyles.create_status_table("🔴 Exposed Resources")
        table.add_column("Type", style="cyan")
        table.add_column("Resource ID", style="yellow")
        table.add_column("Severity", justify="center")

        for event in self.all_drift_events:
            severity_style = AeroDriftStyles.severity_to_style(event.severity)
            severity_text = Text(event.severity, style=severity_style)
            table.add_row(
                event.node_type,
                event.node_label,
                severity_text,
            )

        return table

    def render_remediation_targets_table(self) -> Table:
        """Render a table of security groups requiring remediation."""
        table = AeroDriftStyles.create_status_table("🔐 Remediation Targets")
        table.add_column("Security Group ID", style="red")
        table.add_column("Affected Resources", style="yellow")
        table.add_column("Action", style="cyan")

        # Deduplicate
        sg_to_resources: dict[str, set[str]] = {}
        for event in self.all_drift_events:
            for sg_id in event.offending_security_groups:
                if sg_id not in sg_to_resources:
                    sg_to_resources[sg_id] = set()
                sg_to_resources[sg_id].add(event.node_label)

        for sg_id, resources in sg_to_resources.items():
            resource_list = ", ".join(sorted(resources))
            action = Text("REVOKE public ingress", style="bold red")
            table.add_row(sg_id, resource_list, action)

        return table

    def print_full_dashboard(self, engine: TopologyEngine) -> None:
        """Print a complete dashboard view."""
        layout = Layout()
        layout.split_column(
            Layout(name="header", size=3),
            Layout(name="main"),
            Layout(name="footer", size=3),
        )

        # Header
        header_text = Text("AeroDrift — Cloud Security Monitoring", justify="center")
        header_text.stylize(AeroDriftStyles.HEADER)
        layout["header"].update(Panel(header_text, border_style="blue"))

        # Main content
        layout["main"].split_row(
            Layout(name="topology"),
            Layout(name="alerts"),
        )

        topology_tree = self.render_topology_with_exposure(engine)
        layout["topology"].update(Panel(topology_tree, title="Topology", border_style="cyan"))

        drift_summary = self.render_drift_summary()
        layout["alerts"].update(drift_summary)

        # Footer
        status = f"Monitoring active | {len(self.all_drift_events)} drift events | Last: {self.last_update.strftime('%H:%M:%S')}"
        footer_text = Text(status, justify="center", style=AeroDriftStyles.LABEL)
        layout["footer"].update(Panel(footer_text, border_style="dim"))

        self.console.print(layout)

        # Print detailed tables below
        if self.all_drift_events:
            self.console.print("\n")
            self.console.print(self.render_exposed_resources_table())
            self.console.print("\n")
            self.console.print(self.render_remediation_targets_table())