from __future__ import annotations

import json
from pathlib import Path

from lab.agents.hebbian_agent import HebbianAgent, Neuron, AffordanceStat, RelativeAction
from lab.envs.grid.environment import GridWorldEnvironment
from lab.envs.grid.grid_map import GridMap
from lab.core.types import StepResult


def _make_env() -> GridWorldEnvironment:
    grid = GridMap(width=5, height=5, start=(2, 2), goal=(4, 4), walls=set())
    return GridWorldEnvironment(grid_map=grid)


def test_wta_picks_closest_neuron() -> None:
    env = _make_env()
    agent = HebbianAgent(epsilon=0.0)
    patch0 = agent._extract_egocentric_patch(env, (2, 2), agent._facing)
    n0 = Neuron(prototype=patch0, stats={ra: AffordanceStat() for ra in (RelativeAction.FRONT, RelativeAction.BACK, RelativeAction.LEFT, RelativeAction.RIGHT)})
    patch1 = (
        (0, 0, 0),
        (0, 0, 0),
        (0, 0, 0),
    )
    n1 = Neuron(prototype=patch1, stats={ra: AffordanceStat() for ra in (RelativeAction.FRONT, RelativeAction.BACK, RelativeAction.LEFT, RelativeAction.RIGHT)})
    agent._neurons = {0: n0, 1: n1}
    agent._next_neuron_id = 2

    winner = agent._pick_winner(patch0)
    assert winner == 0


def test_neurogenesis_triggered_by_high_pe() -> None:
    env = _make_env()
    agent = HebbianAgent(epsilon=0.0)
    patch = agent._extract_egocentric_patch(env, (2, 2), agent._facing)
    neuron = Neuron(
        prototype=patch,
        stats={ra: AffordanceStat() for ra in (RelativeAction.FRONT, RelativeAction.BACK, RelativeAction.LEFT, RelativeAction.RIGHT)},
    )
    # Make neuron confident front is passable (3 successes, 0 stuck)
    neuron.stats[RelativeAction.FRONT].move_count = 3
    agent._neurons = {0: neuron}
    agent._next_neuron_id = 1
    agent._last_winner_id = 0
    agent._last_action = RelativeAction.FRONT
    agent._last_patch = patch
    agent._last_state = (2, 2)

    # Now environment says blocked -> actual=0 vs P_move ~1 => PE high -> split
    step = StepResult(next_state=(2, 2), reward=0.0, done=False, info={"blocked": True})
    agent.observe(step)
    assert len(agent._neurons) == 2


def test_hebbian_synapses_update_on_agreement_and_disagreement() -> None:
    env = _make_env()
    agent = HebbianAgent(epsilon=0.0)
    patch = agent._extract_egocentric_patch(env, (2, 2), agent._facing)

    # winner predicts move=1.0, other predicts ~0.0
    n0 = Neuron(
        prototype=patch,
        stats={ra: AffordanceStat() for ra in (RelativeAction.FRONT, RelativeAction.BACK, RelativeAction.LEFT, RelativeAction.RIGHT)},
    )
    n0.stats[RelativeAction.FRONT].move_count = 3

    n1 = Neuron(
        prototype=patch,
        stats={ra: AffordanceStat() for ra in (RelativeAction.FRONT, RelativeAction.BACK, RelativeAction.LEFT, RelativeAction.RIGHT)},
    )
    n1.stats[RelativeAction.FRONT].stuck_count = 3

    agent._neurons = {0: n0, 1: n1}
    agent._next_neuron_id = 2
    agent._last_winner_id = 0
    agent._last_action = RelativeAction.FRONT
    agent._last_patch = patch
    agent._last_state = (2, 2)

    # actual=1.0 -> n0 agrees, n1 disagrees -> synapses[(0,0)] +, [(0,1)] -
    step = StepResult(next_state=(3, 2), reward=0.0, done=False, info={})
    agent.observe(step)

    assert agent._synapses[(0, 0)] > 0.0
    assert agent._synapses[(0, 1)] < 0.0


def test_dump_and_load_preserve_neurons_and_synapses(tmp_path: Path) -> None:
    env = _make_env()
    agent = HebbianAgent(epsilon=0.0)
    # force at least one neuron
    _ = agent.select_action((2, 2), env)
    agent._synapses[(0, 0)] = 0.5

    out = tmp_path / "hebbian_state.json"
    agent.dump_state(out)

    loaded = HebbianAgent(epsilon=0.0)
    loaded.load_state(out)

    assert len(loaded._neurons) == len(agent._neurons)
    assert loaded._synapses.get((0, 0)) == 0.5
    assert loaded._next_neuron_id >= len(loaded._neurons)


def test_energy_boost_and_cap_on_winner() -> None:
    env = _make_env()
    agent = HebbianAgent(epsilon=0.0, energy_decay=0.1, energy_boost=2.0, max_energy=1.0)
    patch = agent._extract_egocentric_patch(env, (2, 2), agent._facing)
    neuron = Neuron(
        prototype=patch,
        stats={ra: AffordanceStat() for ra in (RelativeAction.FRONT, RelativeAction.BACK, RelativeAction.LEFT, RelativeAction.RIGHT)},
        energy=0.9,
    )
    neuron.stats[RelativeAction.FRONT].move_count = 1
    agent._neurons = {0: neuron}
    agent._next_neuron_id = 1
    agent._last_winner_id = 0
    agent._last_action = RelativeAction.FRONT
    agent._last_patch = patch
    agent._last_state = (2, 2)

    step = StepResult(next_state=(3, 2), reward=0.0, done=False, info={})
    agent.observe(step)

    # +2 boost to cap 1.0, then -0.1 decay -> 0.9
    assert 0 in agent._neurons
    assert agent._neurons[0].energy == 0.9


def test_energy_decay_prunes_neurons_and_synapses() -> None:
    env = _make_env()
    agent = HebbianAgent(epsilon=0.0, energy_decay=1.0, energy_boost=0.0, max_energy=100.0)
    patch = agent._extract_egocentric_patch(env, (2, 2), agent._facing)
    n0 = Neuron(
        prototype=patch,
        stats={ra: AffordanceStat() for ra in (RelativeAction.FRONT, RelativeAction.BACK, RelativeAction.LEFT, RelativeAction.RIGHT)},
        energy=0.2,
    )
    n1 = Neuron(
        prototype=patch,
        stats={ra: AffordanceStat() for ra in (RelativeAction.FRONT, RelativeAction.BACK, RelativeAction.LEFT, RelativeAction.RIGHT)},
        energy=0.2,
    )
    n0.stats[RelativeAction.FRONT].move_count = 1
    agent._neurons = {0: n0, 1: n1}
    agent._next_neuron_id = 2
    agent._synapses[(0, 0)] = 0.3
    agent._synapses[(0, 1)] = 0.4
    agent._synapses[(1, 0)] = 0.5
    agent._last_winner_id = 0
    agent._last_action = RelativeAction.FRONT
    agent._last_patch = patch
    agent._last_state = (2, 2)

    step = StepResult(next_state=(3, 2), reward=0.0, done=False, info={})
    agent.observe(step)

    assert len(agent._neurons) == 0
    assert agent._synapses == {}

