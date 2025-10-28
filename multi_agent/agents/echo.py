from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import Agent, Message


class EchoAgent(Agent):
    """A trivial agent that echoes back the received payload.

    Useful as an MVP to validate the message path, worker execution and
    basic instrumentation.
    """

    def __init__(
        self,
        id: Optional[str] = None,
        capabilities: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(id=id, capabilities=capabilities)
        self.type = "echo"

    async def handle_message(self, message: Message) -> Optional[List[Message]]:
        """Handle an incoming message and return an echo reply.

        The reply payload contains the original message under the `echo` key.
        """
        # Create a reply message that contains the original payload under `echo` key
        reply = Message(
            type="echo.result",
            sender=self.id,
            target=message.sender,
            payload={"echo": message.payload},
            trace_id=message.trace_id,
        )
        return [reply]
