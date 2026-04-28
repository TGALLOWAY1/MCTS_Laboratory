"""TrueSkill-style rating system for multiplayer Blokus tournaments.

Uses the openskill library's Plackett-Luce model which provides
Gaussian skill distributions (mu, sigma) equivalent to TrueSkill's
factor graph approach, designed for multiplayer (>2 player) games.

Key concepts:
    mu (μ): Estimated skill mean. Higher = stronger player.
    sigma (σ): Uncertainty in the skill estimate. Lower = more confident.
    conservative estimate: μ - 3σ. The leaderboard metric — rewards agents
        that are both strong and consistently strong.
"""

from typing import Any, Dict, List, Optional, Tuple

from openskill.models import PlackettLuce


# Default TrueSkill-compatible parameters
DEFAULT_MU = 25.0
DEFAULT_SIGMA = DEFAULT_MU / 3.0  # ~8.333


class TrueSkillTracker:
    """Track agent skill ratings using a TrueSkill-style Plackett-Luce model.

    Parameters match the TrueSkill paper (Herbrich et al., 2006):
        mu_0 = 25, sigma_0 = 25/3, beta = 25/2, tau = 25/100
    """

    def __init__(
        self,
        mu: float = DEFAULT_MU,
        sigma: float = DEFAULT_SIGMA,
        beta: float = DEFAULT_MU / 2.0,
        tau: float = DEFAULT_MU / 100.0,
    ):
        self._mu = mu
        self._sigma = sigma
        self._model = PlackettLuce(mu=mu, sigma=sigma, beta=beta, tau=tau)
        self._ratings: Dict[str, Any] = {}  # agent_id -> openskill Rating object
        self._games_played: Dict[str, int] = {}

    def _ensure_agent(self, agent_id: str) -> None:
        """Create a default rating for a new agent if not yet tracked."""
        if agent_id not in self._ratings:
            self._ratings[agent_id] = self._model.rating()
            self._games_played[agent_id] = 0

    def update_game(self, agent_scores: Dict[str, int]) -> None:
        """Update ratings from a single multiplayer game result.

        Converts scores to a full ranking (1st through Nth) and updates
        all players' skill distributions via approximate message passing.

        Args:
            agent_scores: Dict mapping agent_id to their game score.
                Higher score = better placement.
        """
        if len(agent_scores) < 2:
            return

        for agent_id in agent_scores:
            self._ensure_agent(agent_id)

        # Sort agents by score descending (highest score = rank 1)
        sorted_agents = sorted(agent_scores.items(), key=lambda x: x[1], reverse=True)

        # Build teams (each agent is a 1-player team) in rank order
        teams = [[self._ratings[agent_id]] for agent_id, _ in sorted_agents]
        agent_order = [agent_id for agent_id, _ in sorted_agents]

        # Rate using Plackett-Luce model
        updated = self._model.rate(teams)

        # Update stored ratings
        for i, agent_id in enumerate(agent_order):
            self._ratings[agent_id] = updated[i][0]
            self._games_played[agent_id] = self._games_played.get(agent_id, 0) + 1

    def get_rating(self, agent_id: str) -> Dict[str, float]:
        """Get rating details for a single agent.

        Returns:
            Dict with 'mu', 'sigma', 'conservative' (mu - 3*sigma),
            and 'games_played'.
        """
        self._ensure_agent(agent_id)
        r = self._ratings[agent_id]
        return {
            "mu": float(r.mu),
            "sigma": float(r.sigma),
            "conservative": float(r.mu - 3 * r.sigma),
            "games_played": self._games_played.get(agent_id, 0),
        }

    def get_ratings(self) -> Dict[str, Dict[str, float]]:
        """Get ratings for all tracked agents."""
        return {agent_id: self.get_rating(agent_id) for agent_id in self._ratings}

    def get_leaderboard(self) -> List[Dict[str, Any]]:
        """Get agents sorted by conservative estimate (mu - 3*sigma).

        Returns:
            List of dicts with 'agent_id', 'mu', 'sigma', 'conservative',
            'games_played', 'rank'.
        """
        entries = []
        for agent_id in self._ratings:
            info = self.get_rating(agent_id)
            info["agent_id"] = agent_id
            entries.append(info)
        entries.sort(key=lambda x: x["conservative"], reverse=True)
        for i, entry in enumerate(entries):
            entry["rank"] = i + 1
        return entries

    def is_converged(self, sigma_threshold: float = 6.5) -> bool:
        """Check if all agents' uncertainty is below the threshold.

        When sigma drops below the threshold for all agents, ratings
        have stabilized and the tournament can be stopped.

        Note: The Plackett-Luce model in openskill typically converges
        sigma to ~5-7 range after 100+ games. The default threshold
        of 6.5 is appropriate for stable relative rankings.

        Args:
            sigma_threshold: Maximum acceptable sigma for convergence.

        Returns:
            True if all agents have sigma < sigma_threshold.
        """
        if not self._ratings:
            return False
        return all(
            self._ratings[agent_id].sigma < sigma_threshold
            for agent_id in self._ratings
        )

    def reset_agent(self, agent_id: str, increase_sigma: bool = True) -> None:
        """Reset or increase uncertainty for an agent.

        Use when an agent has been modified between tournaments.
        Increases tau^2 (dynamics variance) to signal the old rating
        is less trustworthy.

        Args:
            agent_id: The agent to reset.
            increase_sigma: If True, increase sigma to initial value
                while keeping mu. If False, fully reset to defaults.
        """
        if agent_id not in self._ratings:
            self._ensure_agent(agent_id)
            return

        if increase_sigma:
            # Keep current mu but reset sigma to initial uncertainty
            current_mu = self._ratings[agent_id].mu
            self._ratings[agent_id] = self._model.rating(mu=current_mu, sigma=self._sigma)
        else:
            self._ratings[agent_id] = self._model.rating()
            self._games_played[agent_id] = 0

    def load_ratings(self, saved: Dict[str, Dict[str, float]]) -> None:
        """Seed the tracker with previously saved ratings.

        Call this before the first ``update_game`` when continuing an
        ongoing rating series across multiple arena sessions.

        Args:
            saved: Dict mapping agent_id to a dict with keys 'mu', 'sigma',
                and optionally 'games_played', as produced by ``get_ratings()``.
        """
        for agent_id, r in saved.items():
            mu = float(r.get("mu", self._mu))
            sigma = float(r.get("sigma", self._sigma))
            self._ratings[agent_id] = self._model.rating(mu=mu, sigma=sigma)
            self._games_played[agent_id] = int(r.get("games_played", 0))

    @property
    def agent_ids(self) -> List[str]:
        """List of all tracked agent IDs."""
        return list(self._ratings.keys())
