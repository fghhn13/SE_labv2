from __future__ import annotations

from typing import Any

from lab.agents import registry as agent_registry
from lab.agents.egocentric_stage1_agent import EgocentricStage1Agent
from lab.agents.hebbian_agent import HebbianAgent
from lab.agents.template_agent import TemplateAgent
from lab.envs import registry as env_registry
from lab.envs.grid.environment import GridWorldEnvironment
from lab.envs.grid.maps import get_map, register_builtin_maps
import lab.listeners.stage1_metrics_listener as _stage1_metrics_listener  # noqa: F401
import lab.reporters.stage1_probe_reporter as _stage1_probe_reporter  # noqa: F401
import lab.reporters.stage1_chart_reporter as _stage1_chart_reporter  # noqa: F401
import lab.trainer.stage1_curriculum_trainer as _stage1_curriculum_trainer  # noqa: F401


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

    def build_egocentric_stage1_agent(**kwargs: Any) -> EgocentricStage1Agent:
        return EgocentricStage1Agent(
            env=kwargs.get("env"),
            seed=kwargs.get("seed"),
            epsilon=kwargs.get("epsilon", 0.1),
            max_neurons=kwargs.get("max_neurons", 8),
            distance_threshold=kwargs.get("distance_threshold", 3),
            prototype_lr=kwargs.get("prototype_lr", 0.2),
            init_facing=kwargs.get("init_facing", "N"),
            untried_prior=kwargs.get("untried_prior", 1.0),
            oob_as_wall=kwargs.get("oob_as_wall", True),
            oob_code=kwargs.get("oob_code", -1),
            wall_code=kwargs.get("wall_code", 1),
        )

    agent_registry.register("egocentric_stage1", build_egocentric_stage1_agent)

    def build_hebbian_agent(**kwargs: Any) -> HebbianAgent:
        return HebbianAgent(
            env=kwargs.get("env"),
            seed=kwargs.get("seed"),
            epsilon=kwargs.get("epsilon", 0.1),
            prototype_lr=kwargs.get("prototype_lr", 0.2),
            init_facing=kwargs.get("init_facing", "N"),
            oob_as_wall=kwargs.get("oob_as_wall", True),
            oob_code=kwargs.get("oob_code", -1),
            wall_code=kwargs.get("wall_code", 1),
            energy_decay=kwargs.get("energy_decay", 0.05),
            energy_boost=kwargs.get("energy_boost", 2.0),
            max_energy=kwargs.get("max_energy", 100.0),
        )

    agent_registry.register("hebbian", build_hebbian_agent)

