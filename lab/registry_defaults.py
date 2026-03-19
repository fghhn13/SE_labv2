from __future__ import annotations

from typing import Any

from lab.agents import registry as agent_registry
from lab.agents.template_agent import TemplateAgent
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

    def build_template_agent(**kwargs: Any) -> TemplateAgent:
        return TemplateAgent(seed=kwargs.get("seed"))

    agent_registry.register("template", build_template_agent)

