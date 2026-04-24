"""Source-of-truth loader for the playable Challenge Champion profile."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Mapping, Optional


CHALLENGE_CHAMPION_PROFILE = "challenge_champion"
DEFAULT_PROFILE_PATH = (
    Path(__file__).resolve().parents[1] / "config" / "challenge_champion_config.json"
)
REQUIRED_TOP_LEVEL_KEYS = {
    "profile",
    "max_budget_ms",
    "warmup_budget_ms",
    "tier_budgets_ms",
    "mcts",
}
REQUIRED_MCTS_KEYS = {
    "rollout_policy",
    "rollout_cutoff_depth",
    "minimax_backup_alpha",
    "rave_enabled",
    "rave_k",
    "progressive_widening_enabled",
    "pw_c",
    "pw_alpha",
    "adaptive_rollout_depth_enabled",
    "state_eval_weights",
}


def load_challenge_champion_profile(
    path: Optional[Path] = None,
) -> Dict[str, Any]:
    profile_path = path or DEFAULT_PROFILE_PATH
    with profile_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise ValueError("Challenge champion profile must be a JSON object.")
    validate_challenge_champion_profile(payload)
    return payload


def validate_challenge_champion_profile(profile: Mapping[str, Any]) -> None:
    missing = sorted(REQUIRED_TOP_LEVEL_KEYS - set(profile.keys()))
    if missing:
        raise ValueError(f"Challenge champion profile missing keys: {missing}")
    if profile["profile"] != CHALLENGE_CHAMPION_PROFILE:
        raise ValueError(
            f"Expected profile '{CHALLENGE_CHAMPION_PROFILE}', got {profile['profile']!r}."
        )
    tier_budgets = profile["tier_budgets_ms"]
    if not isinstance(tier_budgets, Mapping):
        raise ValueError("tier_budgets_ms must be an object.")
    for tier in ("trivial", "normal", "critical"):
        if tier not in tier_budgets:
            raise ValueError(f"tier_budgets_ms missing '{tier}'.")
    mcts = profile["mcts"]
    if not isinstance(mcts, Mapping):
        raise ValueError("mcts must be an object.")
    missing_mcts = sorted(REQUIRED_MCTS_KEYS - set(mcts.keys()))
    if missing_mcts:
        raise ValueError(f"Challenge champion mcts profile missing keys: {missing_mcts}")


def build_mcts_kwargs(
    profile: Optional[Mapping[str, Any]] = None,
    *,
    overrides: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    source = profile or load_challenge_champion_profile()
    validate_challenge_champion_profile(source)
    kwargs = dict(source["mcts"])
    if overrides:
        for key, value in overrides.items():
            if key in kwargs:
                kwargs[key] = value
    return kwargs
