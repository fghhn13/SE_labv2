import argparse
from pathlib import Path
from typing import Optional

from lab.agents import registry as agent_registry
from lab.envs import registry as env_registry
from lab.listeners.async_jsonl_listener import AsyncJsonlListener
from lab.trainer.standard_trainer import StandardTrainer
from lab.registry_defaults import register_all_defaults


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Run StandardTrainer with async jsonl listener.")
    parser.add_argument("--episodes", type=int, default=5)
    parser.add_argument("--max-steps", type=int, default=50)
    parser.add_argument("--map-name", type=str, default="open_5x5")
    parser.add_argument("--env-name", type=str, default="grid_basic")
    parser.add_argument("--agent-name", type=str, default="template")
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--epsilon", type=float, default=0.0)
    parser.add_argument("--output-jsonl", type=str, default="lab_v2_results/standard/events.jsonl")
    args = parser.parse_args(argv)

    register_all_defaults()

    env = env_registry.create(args.env_name, map_name=args.map_name)
    agent = agent_registry.create(args.agent_name, seed=args.seed, epsilon=args.epsilon)

    output_file = Path(args.output_jsonl)
    listener = AsyncJsonlListener(output_file=output_file)

    trainer = StandardTrainer(
        env=env,
        agent=agent,
        listeners=[listener],
        max_steps=args.max_steps,
        record_path=False,
    )
    trainer.run(args.episodes)

    print(f"[done] wrote events to: {output_file}")


if __name__ == "__main__":
    main()

