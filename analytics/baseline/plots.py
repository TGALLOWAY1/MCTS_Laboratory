"""Shared matplotlib plotting utilities for Layer 1 baseline analyses."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import matplotlib

matplotlib.use("Agg")  # non-interactive backend for headless environments
import matplotlib.pyplot as plt


def setup_plot_style() -> None:
    """Apply a clean, publication-ready plot style."""
    plt.rcParams.update(
        {
            "figure.figsize": (10, 6),
            "figure.dpi": 150,
            "axes.grid": True,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "grid.alpha": 0.3,
            "font.size": 11,
            "axes.titlesize": 13,
            "axes.labelsize": 12,
        }
    )


def save_plot(fig: plt.Figure, path: str | Path) -> None:
    """Save figure to *path*, creating parent directories as needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, bbox_inches="tight")
    plt.close(fig)


def annotate_threshold(
    ax: plt.Axes,
    y_value: float,
    label: str,
    color: str = "red",
    linestyle: str = "--",
) -> None:
    """Draw a horizontal threshold line with a text label."""
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
    color: str = "red",
) -> None:
    """Annotate a peak point on the plot."""
    ax.annotate(
        label,
        xy=(x, y),
        xytext=(x + 2, y + y * 0.1),
        fontsize=9,
        color=color,
        arrowprops=dict(arrowstyle="->", color=color, lw=1.2),
    )
