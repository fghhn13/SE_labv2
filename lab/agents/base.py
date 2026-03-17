from lab.core.interfaces import Agent as AgentInterface


class BaseAgent(AgentInterface):
    """
    Convenience base class with no-op observe/end_episode.
    Concrete agents can subclass this instead of implementing the Protocol directly.
    """

    def reset(self) -> None:
        ...

    def observe(self, step_result):
        ...

    def end_episode(self, result):
        ...

