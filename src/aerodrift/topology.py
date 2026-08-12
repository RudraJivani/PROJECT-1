"""
Topology Engine (NetworkX)
Models cloud architecture as a directed graph.
"""

from __future__ import annotations

import ipaddress

import networkx as nx

from aerodrift.ingestion import CloudState

INTERNET_NODE = "internet:0.0.0.0/0"


def _is_public_cidr(cidr: str) -> bool:
    """Check if a CIDR is public (not private RFC1918 range)."""
    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except ValueError:
        return False
    return not network.is_private


class TopologyEngine:
    """Builds and queries a directed graph model of a CloudState snapshot."""

    def __init__(self) -> None:
        self.graph: nx.DiGraph = nx.DiGraph()

    def build(self, state: CloudState) -> nx.DiGraph:
        self.graph = nx.DiGraph()
        self.graph.add_node(INTERNET_NODE, type="internet", label="Internet")

        for vpc in state.vpcs:
            self.graph.add_node(vpc.vpc_id, type="vpc", label=vpc.vpc_id, cidr=vpc.cidr_block)

        for subnet in state.subnets:
            self.graph.add_node(
                subnet.subnet_id, type="subnet", label=subnet.subnet_id, cidr=subnet.cidr_block
            )
            if subnet.vpc_id in self.graph:
                self.graph.add_edge(subnet.subnet_id, subnet.vpc_id, relation="belongs_to")

        for sg in state.security_groups:
            self.graph.add_node(sg.group_id, type="security_group", label=sg.group_name)
            for rule in sg.ingress:
                if _is_public_cidr(rule.cidr):
                    self.graph.add_edge(
                        INTERNET_NODE,
                        sg.group_id,
                        relation="ingress",
                        port=f"{rule.from_port}-{rule.to_port}",
                        cidr=rule.cidr,
                    )

        for inst in state.instances:
            name = inst.tags.get("Name", inst.instance_id)
            self.graph.add_node(inst.instance_id, type="instance", label=name, tags=inst.tags)
            if inst.subnet_id in self.graph:
                self.graph.add_edge(inst.instance_id, inst.subnet_id, relation="runs_in")
            for sg_id in inst.security_group_ids:
                if sg_id in self.graph:
                    self.graph.add_edge(sg_id, inst.instance_id, relation="protects")

        return self.graph

    def path_exists_from_internet(self, target_node: str) -> bool:
        """Can the internet reach this node?"""
        if target_node not in self.graph:
            return False
        return nx.has_path(self.graph, INTERNET_NODE, target_node)

    def exposure_path(self, target_node: str) -> list[str] | None:
        """Return the actual path from the internet to a target, or None."""
        if not self.path_exists_from_internet(target_node):
            return None
        return nx.shortest_path(self.graph, INTERNET_NODE, target_node)

    def find_exposed_instances(self, name_filter: str | None = None) -> list[str]:
        """Return every instance reachable from the internet."""
        exposed = []
        for node, attrs in self.graph.nodes(data=True):
            if attrs.get("type") != "instance":
                continue
            if name_filter and name_filter.lower() not in str(attrs.get("label", "")).lower():
                continue
            if self.path_exists_from_internet(node):
                exposed.append(node)
        return exposed

    def offending_security_groups(self, target_node: str) -> list[str]:
        """Which security groups are blocking the exposure path?"""
        path = self.exposure_path(target_node)
        if not path:
            return []
        return [n for n in path[1:] if self.graph.nodes[n].get("type") == "security_group"]