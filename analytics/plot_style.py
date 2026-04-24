"""Shared matplotlib theme for MCTS Laboratory charts.

All matplotlib output should route through this module so the plots match the
visual language of the `/story` page (Inter typography, charcoal background,
neon accent palette). Keeping the tokens in one place mirrors the Tailwind
config in ``frontend/tailwind.config.js``.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, Optional

import matplotlib

matplotlib.use("Agg")  # safe default for headless chart generation
import matplotlib.pyplot as plt
from matplotlib import font_manager

# ---------------------------------------------------------------------------
# Design tokens (mirror frontend/tailwind.config.js and frontend/src/index.css)
# ---------------------------------------------------------------------------

CHARCOAL_900 = "#1E1E1E"
CHARCOAL_800 = "#252526"
CHARCOAL_700 = "#333333"
CHARCOAL_600 = "#3E3E42"

NEON_BLUE = "#00F0FF"
NEON_CYAN = "#22D3EE"
NEON_VIOLET = "#8B5CF6"
NEON_GREEN = "#00FF9D"
NEON_RED = "#FF4D4D"
NEON_YELLOW = "#FFE600"

TEXT_PRIMARY = "#F3F4F6"   # gray-100
TEXT_SECONDARY = "#CBD5E1"  # slate-300
TEXT_MUTED = "#94A3B8"     # slate-400

# Default data-series palette — ordered for good contrast when many series are
# present in a single chart.
DATA_PALETTE: tuple[str, ...] = (
    NEON_CYAN,
    NEON_VIOLET,
    NEON_GREEN,
    NEON_YELLOW,
    NEON_BLUE,
    NEON_RED,
)

# Player colors used for Blokus-specific charts (matches the in-app board).
PLAYER_COLORS: Dict[str, str] = {
    "RED": NEON_RED,
    "BLUE": NEON_BLUE,
    "YELLOW": NEON_YELLOW,
    "GREEN": NEON_GREEN,
}

# Background / axis tokens consumed by legacy code paths that imported raw
# constants directly.
BG_COLOR = CHARCOAL_900
PANEL_COLOR = CHARCOAL_800
GRID_COLOR = CHARCOAL_700
SPINE_COLOR = CHARCOAL_600


# ---------------------------------------------------------------------------
# Font stack
# ---------------------------------------------------------------------------

_FONT_STACK: tuple[str, ...] = (
    "Inter",
    "Inter Variable",
    "Helvetica Neue",
    "Helvetica",
    "Arial",
    "DejaVu Sans",
)


def _resolve_font_family() -> list[str]:
    """Return a font stack with Inter first if installed, else graceful fallbacks."""
    available = {f.name for f in font_manager.fontManager.ttflist}
    return [name for name in _FONT_STACK if name in available] or ["DejaVu Sans"]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def apply_lab_style() -> None:
    """Apply the LAB theme globally via ``rcParams``.

    Safe to call multiple times. Call this once near the top of any script that
    produces matplotlib output.
    """
    family = _resolve_font_family()
    plt.rcParams.update(
        {
            # Typography
            "font.family": family,
            "font.size": 11,
            "axes.titlesize": 14,
            "axes.titleweight": "600",
            "axes.labelsize": 12,
            "axes.labelweight": "500",
            "legend.fontsize": 10,
            "xtick.labelsize": 10,
            "ytick.labelsize": 10,
            # Surfaces
            "figure.facecolor": CHARCOAL_900,
            "axes.facecolor": CHARCOAL_900,
            "savefig.facecolor": CHARCOAL_900,
            "savefig.edgecolor": CHARCOAL_900,
            # Text colors
            "text.color": TEXT_PRIMARY,
            "axes.labelcolor": TEXT_PRIMARY,
            "axes.titlecolor": TEXT_PRIMARY,
            "xtick.color": TEXT_SECONDARY,
            "ytick.color": TEXT_SECONDARY,
            # Spines / grid
            "axes.edgecolor": SPINE_COLOR,
            "axes.linewidth": 1.0,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "axes.grid": True,
            "grid.color": GRID_COLOR,
            "grid.alpha": 0.45,
            "grid.linewidth": 0.8,
            # Legend
            "legend.facecolor": CHARCOAL_800,
            "legend.edgecolor": SPINE_COLOR,
            "legend.labelcolor": TEXT_PRIMARY,
            "legend.frameon": True,
            # Line defaults
            "lines.linewidth": 2.0,
            "lines.solid_capstyle": "round",
            # Figure
            "figure.dpi": 120,
            "savefig.dpi": 150,
            "figure.autolayout": False,
        }
    )
    # Cycle data series through the neon palette.
    plt.rcParams["axes.prop_cycle"] = plt.cycler(color=list(DATA_PALETTE))


def style_axes(ax: plt.Axes) -> plt.Axes:
    """Re-apply LAB styling to an already-created axes (useful for subplots)."""
    ax.set_facecolor(CHARCOAL_900)
    ax.tick_params(colors=TEXT_SECONDARY)
    ax.grid(True, color=GRID_COLOR, alpha=0.45, linewidth=0.8)
    for name, spine in ax.spines.items():
        if name in ("top", "right"):
            spine.set_visible(False)
        else:
            spine.set_color(SPINE_COLOR)
    return ax


def style_legend(legend) -> None:
    """Force-tint an existing legend to LAB colors."""
    if legend is None:
        return
    frame = legend.get_frame()
    frame.set_facecolor(CHARCOAL_800)
    frame.set_edgecolor(SPINE_COLOR)
    for text in legend.get_texts():
        text.set_color(TEXT_PRIMARY)


def save_figure(fig: plt.Figure, path: str | Path, *, tight: bool = True) -> Path:
    """Save *fig* to *path* with LAB background, creating parents as needed."""
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    if tight:
        fig.tight_layout()
    fig.savefig(
        out,
        facecolor=fig.get_facecolor() or CHARCOAL_900,
        edgecolor=CHARCOAL_900,
        bbox_inches="tight" if tight else None,
    )
    plt.close(fig)
    return out


def palette(n: Optional[int] = None) -> tuple[str, ...]:
    """Return the neon data palette, optionally sliced to *n* entries."""
    if n is None:
        return DATA_PALETTE
    if n <= len(DATA_PALETTE):
        return DATA_PALETTE[:n]
    # Repeat the palette if we need more colors than we defined.
    repeats = (n + len(DATA_PALETTE) - 1) // len(DATA_PALETTE)
    return (DATA_PALETTE * repeats)[:n]


def player_colors(names: Iterable[str]) -> list[str]:
    """Look up player-specific colors, falling back to the neon palette."""
    fallback = iter(DATA_PALETTE)
    resolved: list[str] = []
    for name in names:
        resolved.append(PLAYER_COLORS.get(name.upper(), next(fallback, NEON_CYAN)))
    return resolved


__all__ = [
    "CHARCOAL_900",
    "CHARCOAL_800",
    "CHARCOAL_700",
    "CHARCOAL_600",
    "NEON_BLUE",
    "NEON_CYAN",
    "NEON_VIOLET",
    "NEON_GREEN",
    "NEON_RED",
    "NEON_YELLOW",
    "TEXT_PRIMARY",
    "TEXT_SECONDARY",
    "TEXT_MUTED",
    "DATA_PALETTE",
    "PLAYER_COLORS",
    "BG_COLOR",
    "PANEL_COLOR",
    "GRID_COLOR",
    "SPINE_COLOR",
    "apply_lab_style",
    "style_axes",
    "style_legend",
    "save_figure",
    "palette",
    "player_colors",
]
