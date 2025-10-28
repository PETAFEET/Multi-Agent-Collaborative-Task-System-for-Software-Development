from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Agent, Message


class PlannerAgent(Agent):
    """Skeleton for a Planner agent.

    Receives a high-level task and emits one or more subtasks.
    """

    def __init__(
        self,
        id: Optional[str] = None,
        capabilities: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(id=id, capabilities=capabilities)
        self.type = "planner"

    async def handle_message(self, message: Message) -> Optional[List[Message]]:
        """Handle a high-level task and emit subtask messages.

        This minimal example creates a single subtask that wraps the original
        payload.
        """
        # Minimal example: wrap payload into a single subtask message.
        subtask = Message(
            type="task.sub",
            sender=self.id,
            target=message.metadata.get("target_agent") if message.metadata else None,
            payload={"original": message.payload},
            trace_id=message.trace_id,
        )
        return [subtask]
