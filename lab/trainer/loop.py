from lab.core.interfaces import Agent, Environment
from lab.core.types import EpisodeResult


class Trainer:
    """
    Barebones trainer:
    - no reward/cost accumulation
    - no callbacks
    - no structure/recording calls

    Purely dispatches env-agent interaction and prints a minimal per-episode summary.
    """

    def __init__(self, env: Environment, agent: Agent, max_steps: int = 100) -> None:
        self.env = env
        self.agent = agent
        self.max_steps = int(max_steps)

    def run(self, num_episodes: int) -> None:
        for ep in range(num_episodes):
            state = self.env.reset()
            self.agent.reset()

            path = [state]
            steps = 0
            success = False

            for _step_idx in range(self.max_steps):
                action = self.agent.select_action(state, self.env)
                step_result = self.env.step(action)
                self.agent.observe(step_result)

                state = step_result.next_state
                path.append(state)
                steps += 1

                if step_result.done:
                    # Success semantics is defined by physical info.
                    success = bool(step_result.info.get("success", False))
                    break

            episode_result = EpisodeResult(
                path=path,
                cost=float(steps),  # cost is irrelevant here; keep a consistent placeholder
                success=success,
                steps=steps,
            )
            self.agent.end_episode(episode_result)

            outcome = (
                "到了终点（success=True）" if success else "死在陷阱里（success=False）"
            )
            print(f"[episode {ep}] 跑了 {steps} 步，{outcome}")

