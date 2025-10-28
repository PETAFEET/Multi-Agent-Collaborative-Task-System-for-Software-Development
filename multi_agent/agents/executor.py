from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Agent, Message


class ExecutorAgent(Agent):
    """Skeleton for an Executor agent.

    Receives a concrete subtask and performs the action, returning a result
    message.
    """

    def __init__(
        self,
        id: Optional[str] = None,
        capabilities: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(id=id, capabilities=capabilities)
        self.type = "executor"

    async def handle_message(self, message: Message) -> Optional[List[Message]]:
        """Execute a subtask message and return a result message.

        This minimal implementation simply echoes the payload as a 'result'.
        """
        # Minimal example: pretend we executed and return a result message
        result = Message(
            type="task.result",
            sender=self.id,
            target=message.sender,
            payload={"result": message.payload},
            trace_id=message.trace_id,
        )
        return [result]
