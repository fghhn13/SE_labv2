from __future__ import annotations

from typing import Any

from lab.agents import registry as agent_registry
from lab.agents.greedy_agent import GreedyAgent
from lab.agents.random_agent import RandomAgent
from lab.envs import registry as env_registry
from lab.envs.grid.environment import GridWorldEnvironment
from lab.envs.grid.maps import get_map, register_builtin_maps


def register_all_defaults() -> None:
    """
    Register the default set of components used by the CLI scripts.

    This function centralizes what used to live in multiple `_register_defaults()`
    helpers inside CLI entrypoints (env + agents + builtin maps).
    """
    register_builtin_maps()

    def build_grid_env(**kwargs: Any) -> GridWorldEnvironment:
        map_name = kwargs.get("map_name", "open_5x5")
        grid = get_map(map_name)
        return GridWorldEnvironment(grid_map=grid)

    env_registry.register("grid_basic", build_grid_env)

    def build_random_agent(**kwargs: Any) -> RandomAgent:
        return RandomAgent(seed=kwargs.get("seed"))

    agent_registry.register("random", build_random_agent)

    def build_greedy_agent(**kwargs: Any) -> GreedyAgent:
        return GreedyAgent(
            seed=kwargs.get("seed"),
            epsilon=kwargs.get("epsilon", 0.0),
        )

    agent_registry.register("greedy", build_greedy_agent)

