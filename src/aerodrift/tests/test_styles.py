"""
Tests for styling and color definitions.
"""

from aerodrift.styles import AeroDriftStyles


def test_styles_has_all_icons():
    """Styles should have all required icons defined."""
    assert AeroDriftStyles.ICON_INTERNET == "🌐"
    assert AeroDriftStyles.ICON_VPC == "📦"
    assert AeroDriftStyles.ICON_INSTANCE_SAFE == "🟢"
    assert AeroDriftStyles.ICON_INSTANCE_EXPOSED == "🔴"


def test_severity_to_style_critical():
    """CRITICAL severity should map to CRITICAL style."""
    style = AeroDriftStyles.severity_to_style("CRITICAL")
    assert style == AeroDriftStyles.CRITICAL


def test_severity_to_style_high():
    """HIGH severity should map to HIGH style."""
    style = AeroDriftStyles.severity_to_style("HIGH")
    assert style == AeroDriftStyles.HIGH


def test_status_to_style_exposed():
    """Exposed status should map to EXPOSED style."""
    style = AeroDriftStyles.status_to_style(True)
    assert style == AeroDriftStyles.EXPOSED


def test_status_to_style_safe():
    """Safe status should map to SAFE style."""
    style = AeroDriftStyles.status_to_style(False)
    assert style == AeroDriftStyles.SAFE


def test_status_to_icon_exposed():
    """Exposed status should use exposed icon."""
    icon = AeroDriftStyles.status_to_icon(True)
    assert icon == AeroDriftStyles.ICON_INSTANCE_EXPOSED


def test_status_to_icon_safe():
    """Safe status should use safe icon."""
    icon = AeroDriftStyles.status_to_icon(False)
    assert icon == AeroDriftStyles.ICON_INSTANCE_SAFE


def test_create_status_table():
    """Should create a properly-styled status table."""
    table = AeroDriftStyles.create_status_table("Test Table")
    assert table is not None
    assert table.title == "Test Table"