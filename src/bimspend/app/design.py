"""BIMSpend design system.

Consistent design tokens, colors, typography, and component styles for the
desktop application. All screens should use these tokens to ensure visual
consistency.

Visual direction:
- Dark navy sidebar (#0F2B46)
- Blue and teal accents (#1976A5, #287E72)
- Light content background (#F4F7F9)
- White cards with subtle borders
- Segoe UI typography
- AUD currency formatting
"""

from __future__ import annotations

from decimal import Decimal
from typing import Optional


# ------------------------------------------------------------------
# Color palette
# ------------------------------------------------------------------

# Sidebar / dark surfaces
SIDEBAR_BG = "#0F2B46"
SIDEBAR_BG_HOVER = "#163A5C"
SIDEBAR_TEXT = "#FFFFFF"
SIDEBAR_TEXT_MUTED = "#A9B8C4"
SIDEBAR_ACCENT = "#1976A5"
SIDEBAR_ACTIVE = "#0E2A3A"

# Content surfaces
APP_BG = "#F4F7F9"
CARD_BG = "#FFFFFF"
CARD_BORDER = "#D8E2E8"
HEADER_BG = "#FFFFFF"

# Text
TEXT_PRIMARY = "#172B3A"
TEXT_SECONDARY = "#4A6572"
TEXT_MUTED = "#8A97A5"
TEXT_ON_DARK = "#FFFFFF"

# Accent colors
ACCENT_BLUE = "#1976A5"
ACCENT_TEAL = "#287E72"
ACCENT_AMBER = "#B8860B"
ACCENT_RED = "#9B2C2C"
ACCENT_GREEN = "#2E7D32"

# Status colors
STATUS_APPROVED = "#287E72"
STATUS_REJECTED = "#9B2C2C"
STATUS_PENDING = "#B8860B"
STATUS_SUBMITTED = "#1976A5"
STATUS_BILLED = "#2E7D32"

# Interactive
BUTTON_PRIMARY_BG = "#1976A5"
BUTTON_PRIMARY_HOVER = "#145E82"
BUTTON_SECONDARY_BG = "#E8EEF3"
BUTTON_SECONDARY_HOVER = "#D8E2E8"
BUTTON_DANGER_BG = "#9B2C2C"
BUTTON_DANGER_HOVER = "#7A2222"

INPUT_BG = "#FFFFFF"
INPUT_BORDER = "#C7D2DA"
INPUT_FOCUS = "#1976A5"
INPUT_TEXT = "#172B3A"


# ------------------------------------------------------------------
# Typography
# ------------------------------------------------------------------

FONT_FAMILY = "Segoe UI"
FONT_SIZE_SMALL = 9
FONT_SIZE_NORMAL = 10
FONT_SIZE_MEDIUM = 11
FONT_SIZE_LARGE = 12
FONT_SIZE_TITLE = 20
FONT_SIZE_METRIC = 24

WEIGHT_NORMAL = "normal"
WEIGHT_BOLD = "bold"


# ------------------------------------------------------------------
# Spacing
# ------------------------------------------------------------------

SPACE_XS = 4
SPACE_SM = 8
SPACE_MD = 12
SPACE_LG = 16
SPACE_XL = 24
SPACE_XXL = 32

CARD_PADDING = 16
CARD_RADIUS = 6
BUTTON_PADDING_X = 16
BUTTON_PADDING_Y = 10


# ------------------------------------------------------------------
# Currency formatting (AUD)
# ------------------------------------------------------------------


def format_aud(value: Decimal | float | int | None) -> str:
    """Format a monetary value as AUD currency string.

    Args:
        value: Numeric value or None.

    Returns:
        Formatted string like "AUD 1,234.56" or "AUD 0.00".
    """
    if value is None:
        return "AUD 0.00"
    d = Decimal(str(value))
    return f"AUD {d:,.2f}"


def format_aud_compact(value: Decimal | float | int | None) -> str:
    """Format a monetary value in compact form.

    Returns:
        Formatted string like "A$ 1,234.56".
    """
    if value is None:
        return "A$ 0.00"
    d = Decimal(str(value))
    return f"A$ {d:,.2f}"


# ------------------------------------------------------------------
# Date formatting
# ------------------------------------------------------------------


def format_date_short(iso_timestamp: Optional[str]) -> str:
    """Format an ISO-8601 timestamp as a short date string.

    Returns:
        String like "2026-01-15" or "—" if None/empty.
    """
    if not iso_timestamp:
        return "—"
    return iso_timestamp[:10]


def format_date_time(iso_timestamp: Optional[str]) -> str:
    """Format an ISO-8601 timestamp as date + time.

    Returns:
        String like "2026-01-15 09:30" or "—" if None/empty.
    """
    if not iso_timestamp:
        return "—"
    return iso_timestamp[:16].replace("T", " ")


def format_minutes(minutes: float | None) -> str:
    """Format duration in minutes as hours and minutes.

    Returns:
        String like "2h 15m" or "0m".
    """
    if minutes is None:
        return "0m"
    total = int(round(minutes))
    hours = total // 60
    mins = total % 60
    if hours > 0:
        return f"{hours}h {mins}m"
    return f"{mins}m"


# ------------------------------------------------------------------
# Style registration
# ------------------------------------------------------------------


def register_styles(style) -> None:
    """Register all ttk styles for the BIMSpend design system.

    Should be called once during application initialization after
    ttk.Style() is created and a theme is selected.
    """
    style.theme_use("clam")

    # --- Frame styles ---
    style.configure("App.TFrame", background=APP_BG)
    style.configure("Sidebar.TFrame", background=SIDEBAR_BG)
    style.configure("Header.TFrame", background=HEADER_BG)
    style.configure("Card.TFrame", background=CARD_BG, relief="solid", borderwidth=1)

    # --- Navigation button ---
    style.configure(
        "Nav.TButton",
        background=SIDEBAR_BG,
        foreground=TEXT_ON_DARK,
        borderwidth=0,
        focuscolor=ACCENT_BLUE,
        anchor="w",
        padding=(BUTTON_PADDING_X, BUTTON_PADDING_Y),
        font=(FONT_FAMILY, FONT_SIZE_MEDIUM),
    )
    style.map(
        "Nav.TButton",
        background=[("active", SIDEBAR_BG_HOVER), ("pressed", SIDEBAR_ACTIVE)],
        foreground=[("active", TEXT_ON_DARK), ("pressed", TEXT_ON_DARK)],
    )

    # --- Primary action button ---
    style.configure(
        "Primary.TButton",
        background=BUTTON_PRIMARY_BG,
        foreground=TEXT_ON_DARK,
        borderwidth=0,
        focuscolor=ACCENT_BLUE,
        anchor="center",
        padding=(BUTTON_PADDING_X, BUTTON_PADDING_Y),
        font=(FONT_FAMILY, FONT_SIZE_NORMAL, WEIGHT_BOLD),
    )
    style.map(
        "Primary.TButton",
        background=[("active", BUTTON_PRIMARY_HOVER), ("pressed", BUTTON_PRIMARY_HOVER)],
        foreground=[("active", TEXT_ON_DARK), ("pressed", TEXT_ON_DARK)],
    )

    # --- Secondary action button ---
    style.configure(
        "Secondary.TButton",
        background=BUTTON_SECONDARY_BG,
        foreground=TEXT_PRIMARY,
        borderwidth=0,
        focuscolor=INPUT_BORDER,
        anchor="center",
        padding=(BUTTON_PADDING_X, BUTTON_PADDING_Y),
        font=(FONT_FAMILY, FONT_SIZE_NORMAL),
    )
    style.map(
        "Secondary.TButton",
        background=[("active", BUTTON_SECONDARY_HOVER), ("pressed", BUTTON_SECONDARY_HOVER)],
        foreground=[("active", TEXT_PRIMARY), ("pressed", TEXT_PRIMARY)],
    )

    # --- Danger button ---
    style.configure(
        "Danger.TButton",
        background=BUTTON_DANGER_BG,
        foreground=TEXT_ON_DARK,
        borderwidth=0,
        focuscolor=ACCENT_RED,
        anchor="center",
        padding=(BUTTON_PADDING_X, BUTTON_PADDING_Y),
        font=(FONT_FAMILY, FONT_SIZE_NORMAL, WEIGHT_BOLD),
    )
    style.map(
        "Danger.TButton",
        background=[("active", BUTTON_DANGER_HOVER), ("pressed", BUTTON_DANGER_HOVER)],
        foreground=[("active", TEXT_ON_DARK), ("pressed", TEXT_ON_DARK)],
    )

    # --- Label styles ---
    style.configure(
        "Title.TLabel",
        background=APP_BG,
        foreground=TEXT_PRIMARY,
        font=(FONT_FAMILY, FONT_SIZE_TITLE, WEIGHT_BOLD),
    )
    style.configure(
        "Subtitle.TLabel",
        background=APP_BG,
        foreground=TEXT_SECONDARY,
        font=(FONT_FAMILY, FONT_SIZE_LARGE),
    )
    style.configure(
        "MetricLabel.TLabel",
        background=CARD_BG,
        foreground=TEXT_SECONDARY,
        font=(FONT_FAMILY, FONT_SIZE_NORMAL),
    )
    style.configure(
        "MetricValue.TLabel",
        background=CARD_BG,
        foreground=TEXT_PRIMARY,
        font=(FONT_FAMILY, FONT_SIZE_METRIC, WEIGHT_BOLD),
    )
    style.configure(
        "Status.TLabel",
        background=CARD_BG,
        foreground=STATUS_APPROVED,
        font=(FONT_FAMILY, FONT_SIZE_NORMAL, WEIGHT_BOLD),
    )
    style.configure(
        "Heading.TLabel",
        background=APP_BG,
        foreground=TEXT_PRIMARY,
        font=(FONT_FAMILY, FONT_SIZE_LARGE, WEIGHT_BOLD),
    )
    style.configure(
        "Caption.TLabel",
        background=APP_BG,
        foreground=TEXT_MUTED,
        font=(FONT_FAMILY, FONT_SIZE_SMALL),
    )

    # --- Entry / input ---
    style.configure(
        "App.TEntry",
        fieldbackground=INPUT_BG,
        bordercolor=INPUT_BORDER,
        focuscolor=INPUT_FOCUS,
        foreground=INPUT_TEXT,
        font=(FONT_FAMILY, FONT_SIZE_NORMAL),
    )

    # --- Combobox ---
    style.configure(
        "App.TCombobox",
        fieldbackground=INPUT_BG,
        bordercolor=INPUT_BORDER,
        focuscolor=INPUT_FOCUS,
        foreground=INPUT_TEXT,
        font=(FONT_FAMILY, FONT_SIZE_NORMAL),
    )

    # --- Treeview (data tables) ---
    style.configure(
        "App.Treeview",
        background=CARD_BG,
        foreground=TEXT_PRIMARY,
        fieldbackground=CARD_BG,
        bordercolor=CARD_BORDER,
        font=(FONT_FAMILY, FONT_SIZE_NORMAL),
        rowheight=28,
    )
    style.configure(
        "App.Treeview.Heading",
        background=APP_BG,
        foreground=TEXT_SECONDARY,
        font=(FONT_FAMILY, FONT_SIZE_NORMAL, WEIGHT_BOLD),
        borderwidth=1,
        relief="solid",
    )
    style.map(
        "App.Treeview",
        background=[("selected", ACCENT_BLUE)],
        foreground=[("selected", TEXT_ON_DARK)],
    )

    # --- Separator ---
    style.configure(
        "App.TSeparator",
        background=CARD_BORDER,
    )


# ------------------------------------------------------------------
# Status color mapping
# ------------------------------------------------------------------


STATUS_COLORS = {
    "pending_review": STATUS_PENDING,
    "submitted": STATUS_SUBMITTED,
    "approved": STATUS_APPROVED,
    "rejected": STATUS_REJECTED,
    "billed": STATUS_BILLED,
    "merged": TEXT_MUTED,
}


def get_status_color(state: str) -> str:
    """Return the accent color for a given entry/suggestion state."""
    return STATUS_COLORS.get(state, TEXT_MUTED)


# ------------------------------------------------------------------
# Role-based navigation configuration
# ------------------------------------------------------------------


NAV_CONFIG = {
    "overview": {
        "label": "Executive Dashboard",
        "icon": "📊",
        "roles": ["designer", "manager", "administrator"],
    },
    "activity_timeline": {
        "label": "Live Activity",
        "icon": "⌚",
        "roles": ["designer", "manager", "administrator"],
    },
    "timesheet_review": {
        "label": "Timesheets",
        "icon": "📋",
        "roles": ["designer", "manager", "administrator"],
    },
    "designer_review": {
        "label": "Designer Review",
        "icon": "✏️",
        "roles": ["designer", "administrator"],
    },
    "manager_approval": {
        "label": "Manager Approval",
        "icon": "✅",
        "roles": ["manager", "administrator"],
    },
    "projects": {
        "label": "Projects",
        "icon": "🏗️",
        "roles": ["designer", "manager", "administrator"],
    },
    "project_detail": {
        "label": "Project Financial Detail",
        "icon": "💰",
        "roles": ["designer", "manager", "administrator"],
    },
    "project_financial_detail": {
        "label": "Project Financial Detail",
        "icon": "💰",
        "roles": ["designer", "manager", "administrator"],
    },
    "financial_dashboard": {
        "label": "Financial Management",
        "icon": "📈",
        "roles": ["manager", "administrator"],
    },
    "financial_reports": {
        "label": "Reports and Analytics",
        "icon": "📄",
        "roles": ["manager", "administrator"],
    },
    "team": {
        "label": "Employees and Teams",
        "icon": "👥",
        "roles": ["manager", "administrator"],
    },
    "integrations": {
        "label": "Integrations and Capture",
        "icon": "🔌",
        "roles": ["designer", "manager", "administrator"],
    },
    "reports": {
        "label": "Legacy Reports",
        "icon": "📄",
        "roles": ["designer", "manager", "administrator"],
    },
    "estimating": {
        "label": "Historical Estimating",
        "icon": "🔮",
        "roles": ["manager", "administrator"],
    },
}


def get_visible_nav_items(role: str) -> list[dict[str, str]]:
    """Return navigation items visible for the given role.

    Args:
        role: One of "designer", "manager", "administrator".

    Returns:
        List of nav item dicts with keys: id, label, icon.
    """
    visible = []
    for screen_id, config in NAV_CONFIG.items():
        if role in config["roles"]:
            visible.append(
                {
                    "id": screen_id,
                    "label": config["label"],
                    "icon": config["icon"],
                }
            )
    return visible
