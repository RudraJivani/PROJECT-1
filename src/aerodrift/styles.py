"""
Styling and color definitions for the Rich dashboard.
All colors and formatting are centralized here.
"""

from rich.style import Style
from rich.table import Table
from rich.console import Console


class AeroDriftStyles:
    """Central styling for the AeroDrift CLI."""

    # Status styles
    SAFE = Style(color="green", bold=True)
    EXPOSED = Style(color="red", bold=True)
    WARNING = Style(color="yellow", bold=True)
    INFO = Style(color="cyan")

    # Severity styles
    CRITICAL = Style(color="red", bgcolor="black", bold=True)
    HIGH = Style(color="yellow", bold=True)
    MEDIUM = Style(color="orange1", bold=True)
    LOW = Style(color="green")

    # Component styles
    HEADER = Style(color="blue", bold=True)
    SECTION = Style(color="magenta", bold=True)
    LABEL = Style(color="white", dim=True)
    VALUE = Style(color="cyan")

    # Icons
    ICON_INTERNET = "🌐"
    ICON_VPC = "📦"
    ICON_SUBNET = "🔲"
    ICON_INSTANCE_SAFE = "🟢"
    ICON_INSTANCE_EXPOSED = "🔴"
    ICON_SG_SAFE = "🔒"
    ICON_SG_EXPOSED = "🔓"
    ICON_DRIFT = "⚠️"
    ICON_CHECK = "✅"
    ICON_X = "❌"

    @staticmethod
    def severity_to_style(severity: str) -> Style:
        """Map severity string to Rich Style."""
        severity_map = {
            "CRITICAL": AeroDriftStyles.CRITICAL,
            "HIGH": AeroDriftStyles.HIGH,
            "MEDIUM": AeroDriftStyles.MEDIUM,
            "LOW": AeroDriftStyles.LOW,
            "WARNING": AeroDriftStyles.WARNING,
        }
        return severity_map.get(severity, AeroDriftStyles.INFO)

    @staticmethod
    def status_to_style(is_exposed: bool) -> Style:
        """Map exposure status to Rich Style."""
        return AeroDriftStyles.EXPOSED if is_exposed else AeroDriftStyles.SAFE

    @staticmethod
    def status_to_icon(is_exposed: bool) -> str:
        """Map exposure status to icon."""
        return AeroDriftStyles.ICON_INSTANCE_EXPOSED if is_exposed else AeroDriftStyles.ICON_INSTANCE_SAFE

    @staticmethod
    def create_status_table(title: str) -> Table:
        """Factory method for status tables with consistent styling."""
        table = Table(title=title, show_header=True, header_style="bold cyan")
        return table