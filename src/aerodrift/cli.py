"""
CLI Interface (Rich)
Terminal dashboard that renders the cloud topology as an interactive text tree.
"""

from __future__ import annotations

from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from aerodrift.drift import DriftEvent
from aerodrift.topology import TopologyEngine


class AeroDriftCLI:
    """Terminal-based dashboard using Rich for rendering."""

    def __init__(self) -> None:
        self.console = Console()

    def print_topology_tree(self, engine: TopologyEngine) -> None:
        """Render the cloud graph as a visual text tree."""
        tree = Tree("☁️ Cloud Topology")

        for node_id, attrs in engine.graph.nodes(data=True):
            node_type = attrs.get("type", "unknown")
            label = attrs.get("label", node_id)

            if node_type == "internet":
                internet_branch = tree.add(f"🌐 {label}")
                # Show security groups connected to internet
                for target in engine.graph.successors(node_id):
                    target_attrs = engine.graph.nodes[target]
                    if target_attrs.get("type") == "security_group":
                        sg_label = target_attrs.get("label", target)
                        internet_branch.add(f"🔓 SecurityGroup: {sg_label}")

            elif node_type == "vpc":
                vpc_branch = tree.add(f"📦 VPC: {label}")
                # Show subnets in this VPC
                for subnet_id, subnet_attrs in engine.graph.nodes(data=True):
                    if (subnet_attrs.get("type") == "subnet" and 
                        subnet_attrs.get("label") == label):
                        subnet_branch = vpc_branch.add(f"🔲 Subnet: {subnet_id}")
                        # Show instances in this subnet
                        for inst_id, inst_attrs in engine.graph.nodes(data=True):
                            if (inst_attrs.get("type") == "instance" and
                                inst_attrs.get("label") == label):
                                exposure = "🔴 EXPOSED" if engine.path_exists_from_internet(inst_id) else "🟢 SAFE"
                                subnet_branch.add(f"💻 {inst_attrs.get('label', inst_id)} {exposure}")

        self.console.print(tree)

    def print_drift_events(self, events: list[DriftEvent]) -> None:
        """Display detected drift events in a formatted table."""
        if not events:
            self.console.print("[green]✓ No new drift detected[/green]")
            return

        table = Table(title="🚨 Drift Events Detected", show_header=True, header_style="bold red")
        table.add_column("Severity", style="red")
        table.add_column("Resource", style="yellow")
        table.add_column("Type", style="cyan")
        table.add_column("Exposure Path", style="magenta")

        for event in events:
            path_str = " → ".join(event.exposure_path[:3])  # Show first 3 nodes
            if len(event.exposure_path) > 3:
                path_str += " → ..."
            table.add_row(
                event.severity,
                event.node_label,
                event.node_type,
                path_str,
            )

        self.console.print(table)

    def print_offending_security_groups(self, events: list[DriftEvent]) -> None:
        """Display which security groups need remediation."""
        if not events:
            return

        table = Table(
            title="🔐 Offending Security Groups (Remediation Targets)",
            show_header=True,
            header_style="bold yellow"
        )
        table.add_column("Security Group ID", style="red")
        table.add_column("Affected Resource", style="yellow")

        for event in events:
            for sg_id in event.offending_security_groups:
                table.add_row(sg_id, event.node_label)

        self.console.print(table)