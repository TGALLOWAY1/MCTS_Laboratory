"""Shared matplotlib plotting utilities for Layer 1 baseline analyses.

This module now delegates the visual theme to :mod:`analytics.plot_style` so
all baseline charts match the `/story` page aesthetic (dark charcoal
background, Inter typography, neon accent palette).
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # non-interactive backend for headless environments
import matplotlib.pyplot as plt

from analytics.plot_style import (
    CHARCOAL_900,
    TEXT_SECONDARY,
    apply_lab_style,
    save_figure,
)


def setup_plot_style() -> None:
    """Apply the shared LAB theme to all matplotlib output."""
    apply_lab_style()
    # Baseline charts historically run a little taller; preserve that framing.
    plt.rcParams["figure.figsize"] = (10, 6)


def save_plot(fig: plt.Figure, path: str | Path) -> None:
    """Save figure to *path* with the LAB background baked in."""
    save_figure(fig, path, tight=True)


def annotate_threshold(
    ax: plt.Axes,
    y_value: float,
    label: str,
    color: Optional[str] = None,
    linestyle: str = "--",
) -> None:
    """Draw a horizontal threshold line with a text label."""
    from analytics.plot_style import NEON_RED

    color = color or NEON_RED
    ax.axhline(y=y_value, color=color, linestyle=linestyle, alpha=0.7, linewidth=1)
    ax.text(
        ax.get_xlim()[1],
        y_value,
        f"  {label}",
        va="bottom",
        ha="right",
        color=color,
        fontsize=9,
    )


def annotate_peak(
    ax: plt.Axes,
    x: float,
    y: float,
    label: str,
    color: Optional[str] = None,
) -> None:
    """Annotate a peak point on the plot."""
    from analytics.plot_style import NEON_RED

    color = color or NEON_RED
    ax.annotate(
        label,
        xy=(x, y),
        xytext=(x + 2, y + y * 0.1),
        fontsize=9,
        color=color,
        arrowprops=dict(arrowstyle="->", color=color, lw=1.2),
    )
