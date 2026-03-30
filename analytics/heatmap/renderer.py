"""Heatmap rendering for MCTS visit-count visualization."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

BOARD_SIZE = 20

# Player colors (RGBA 0-1)
PLAYER_COLORS = {
    0: (0.15, 0.15, 0.18, 1.0),   # empty — dark gray
    1: (0.906, 0.298, 0.235, 1.0),  # RED
    2: (0.204, 0.596, 0.859, 1.0),  # BLUE
    3: (0.945, 0.769, 0.059, 1.0),  # YELLOW
    4: (0.180, 0.800, 0.443, 1.0),  # GREEN
}

PLAYER_NAMES = {1: "Red", 2: "Blue", 3: "Yellow", 4: "Green"}


def load_turn_data(path: Path) -> Dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def build_visit_grid(moves: List[Dict[str, int]], board_size: int = BOARD_SIZE) -> np.ndarray:
    """Build a 2D grid of visit counts from move data."""
    grid = np.zeros((board_size, board_size), dtype=np.float64)
    for m in moves:
        r, c = m["y"], m["x"]
        if 0 <= r < board_size and 0 <= c < board_size:
            grid[r, c] += m["visits"]
    return grid


def generate_heatmap_image(
    turn_data: Dict[str, Any],
    board_size: int = BOARD_SIZE,
    sigma: float = 1.5,
    dpi: int = 100,
    figsize: tuple = (5, 5),
) -> np.ndarray:
    """Render a visit-count heatmap as an RGB numpy array."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.ndimage import gaussian_filter

    grid = build_visit_grid(turn_data.get("moves", []), board_size)

    # Log scaling
    grid = np.log1p(grid)

    # Gaussian blur
    if sigma > 0:
        grid = gaussian_filter(grid, sigma=sigma)

    # Normalize to 0-1
    vmax = grid.max()
    if vmax > 0:
        grid = grid / vmax

    fig, ax = plt.subplots(1, 1, figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    ax.imshow(
        grid,
        cmap="jet",
        interpolation="bilinear",
        vmin=0,
        vmax=1,
        origin="upper",
        extent=[0, board_size, board_size, 0],
    )

    # Grid lines
    for i in range(board_size + 1):
        ax.axhline(i, color="gray", linewidth=0.3, alpha=0.3)
        ax.axvline(i, color="gray", linewidth=0.3, alpha=0.3)

    # Highlight chosen move
    chosen = turn_data.get("chosen_move")
    if chosen:
        cx, cy = chosen["x"] + 0.5, chosen["y"] + 0.5
        ax.plot(cx, cy, marker="x", color="white", markersize=10, markeredgewidth=2)

    ax.set_xlim(0, board_size)
    ax.set_ylim(board_size, 0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("MCTS Visit Heatmap", color="white", fontsize=12, pad=8)

    fig.tight_layout(pad=0.5)
    img = _fig_to_array(fig)
    plt.close(fig)
    return img


def render_board_image(
    board_grid: list,
    board_size: int = BOARD_SIZE,
    dpi: int = 100,
    figsize: tuple = (5, 5),
) -> np.ndarray:
    """Render the board state as an RGB numpy array."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import ListedColormap

    grid = np.array(board_grid, dtype=int)

    # Build RGB image
    img = np.zeros((board_size, board_size, 4), dtype=np.float64)
    for val, color in PLAYER_COLORS.items():
        mask = grid == val
        img[mask] = color

    fig, ax = plt.subplots(1, 1, figsize=figsize, dpi=dpi)
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_facecolor("#1a1a2e")

    ax.imshow(img, origin="upper", extent=[0, board_size, board_size, 0])

    # Grid lines
    for i in range(board_size + 1):
        ax.axhline(i, color="gray", linewidth=0.3, alpha=0.4)
        ax.axvline(i, color="gray", linewidth=0.3, alpha=0.4)

    ax.set_xlim(0, board_size)
    ax.set_ylim(board_size, 0)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Board State", color="white", fontsize=12, pad=8)

    fig.tight_layout(pad=0.5)
    result = _fig_to_array(fig)
    plt.close(fig)
    return result


def compose_frame(
    turn_number: int,
    heatmap_img: np.ndarray,
    board_img: np.ndarray,
    player_id: Optional[int] = None,
    dpi: int = 100,
) -> np.ndarray:
    """Compose heatmap and board into a single frame with title."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.5), dpi=dpi)
    fig.patch.set_facecolor("#1a1a2e")

    player_str = f" | Player: {PLAYER_NAMES.get(player_id, player_id)}" if player_id else ""
    fig.suptitle(
        f"Turn {turn_number}{player_str}",
        color="white",
        fontsize=16,
        fontweight="bold",
        y=0.97,
    )

    for ax, img, title in [
        (axes[0], heatmap_img, "MCTS Visit Heatmap"),
        (axes[1], board_img, "Board State"),
    ]:
        ax.imshow(img)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.set_facecolor("#1a1a2e")
        for spine in ax.spines.values():
            spine.set_visible(False)

    fig.tight_layout(rect=[0, 0, 1, 0.93])
    result = _fig_to_array(fig)
    plt.close(fig)
    return result


def generate_video(
    frames_dir: Path,
    output_path: Path,
    fps: int = 2,
) -> Path:
    """Compile frame PNGs into a video (GIF fallback if mp4 unavailable)."""
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.animation import FuncAnimation
    from PIL import Image

    frame_files = sorted(frames_dir.glob("frame_*.png"))
    if not frame_files:
        raise FileNotFoundError(f"No frames found in {frames_dir}")

    # Load all frames
    images = [np.array(Image.open(f)) for f in frame_files]

    fig, ax = plt.subplots(figsize=(12, 5.5), dpi=100)
    fig.patch.set_facecolor("#1a1a2e")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    fig.subplots_adjust(left=0, right=1, top=1, bottom=0)

    im = ax.imshow(images[0])

    def update(frame_idx):
        im.set_data(images[frame_idx])
        return [im]

    anim = FuncAnimation(fig, update, frames=len(images), interval=1000 // fps, blit=True)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Try mp4 first, fall back to gif
    mp4_path = output_path.with_suffix(".mp4")
    try:
        anim.save(str(mp4_path), writer="ffmpeg", fps=fps)
        plt.close(fig)
        print(f"Video saved: {mp4_path}")
        return mp4_path
    except Exception:
        pass

    gif_path = output_path.with_suffix(".gif")
    try:
        anim.save(str(gif_path), writer="pillow", fps=fps)
        plt.close(fig)
        print(f"GIF saved: {gif_path}")
        return gif_path
    except Exception:
        plt.close(fig)
        # Last resort: save frames as individual PNGs (already done)
        print(f"Could not create video/GIF. Frames available in {frames_dir}")
        return frames_dir


def render_all(
    data_dir: Path,
    output_root: Path,
    player_filter: Optional[int] = None,
    fps: int = 2,
) -> Path:
    """Full pipeline: read turn JSONs, generate heatmaps, boards, frames, video."""
    from PIL import Image

    turn_files = sorted(data_dir.glob("turn_*.json"))
    if not turn_files:
        raise FileNotFoundError(f"No turn data found in {data_dir}")

    game_id = data_dir.name
    heatmaps_dir = output_root / "heatmaps" / game_id
    boards_dir = output_root / "boards" / game_id
    frames_dir = output_root / "frames" / game_id
    videos_dir = output_root / "videos"

    for d in [heatmaps_dir, boards_dir, frames_dir, videos_dir]:
        d.mkdir(parents=True, exist_ok=True)

    frame_idx = 0
    for tf in turn_files:
        turn_data = load_turn_data(tf)

        # Filter by player if requested
        if player_filter is not None and turn_data.get("player") != player_filter:
            continue

        turn_num = turn_data["turn"]
        player_id = turn_data.get("player")

        # Generate heatmap
        heatmap_img = generate_heatmap_image(turn_data)
        heatmap_path = heatmaps_dir / f"turn_{turn_num:03d}.png"
        Image.fromarray(heatmap_img).save(heatmap_path)

        # Generate board image
        board_grid = turn_data.get("board_grid", [[0] * BOARD_SIZE] * BOARD_SIZE)
        board_img = render_board_image(board_grid)
        board_path = boards_dir / f"turn_{turn_num:03d}.png"
        Image.fromarray(board_img).save(board_path)

        # Compose frame
        frame = compose_frame(turn_num, heatmap_img, board_img, player_id=player_id)
        frame_path = frames_dir / f"frame_{frame_idx:03d}.png"
        Image.fromarray(frame).save(frame_path)
        frame_idx += 1

    if frame_idx == 0:
        print("No frames generated (check player filter).")
        return frames_dir

    print(f"Generated {frame_idx} frames in {frames_dir}")

    # Generate video
    video_path = videos_dir / game_id
    result = generate_video(frames_dir, video_path, fps=fps)
    return result


def _fig_to_array(fig) -> np.ndarray:
    """Convert matplotlib figure to RGB numpy array."""
    fig.canvas.draw()
    buf = fig.canvas.buffer_rgba()
    img = np.asarray(buf)
    return img[:, :, :3].copy()  # Drop alpha channel
