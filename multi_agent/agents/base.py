from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class Message(BaseModel):
    """Basic message schema used by agents.

    Keep this small and serializable. It can be replaced by a central
    messaging.schemas.Message later when the project grows.
    """

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    sender: Optional[str] = None
    target: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    trace_id: Optional[str] = None


class Agent(ABC):
    """Abstract agent interface.

    Implementations should be lightweight and side-effect free where
    possible. Long-running or blocking work should be delegated to
    TaskIQ sub-tasks.
    """

    id: str
    type: str
    capabilities: Dict[str, Any]

    def __init__(
        self,
        id: Optional[str] = None,
        capabilities: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.id = id or str(uuid.uuid4())
        self.type = self.__class__.__name__.lower()
        self.capabilities = capabilities or {}

    @abstractmethod
    async def handle_message(self, message: Message) -> Optional[List[Message]]:
        """Handle an incoming message.

        Return a list of outbound Message objects, or None if there's no reply.
        """

    @abstractmethod
    async def start(self) -> None:
        """Optional lifecycle hook called when an agent is started.

        Implementations may perform initialization here. Must be overridden
        by implementations that need startup behavior.
        """

    @abstractmethod
    async def stop(self) -> None:
        """Optional lifecycle hook called when an agent is stopped.

        Implementations may perform cleanup here. Must be overridden by
        implementations that need shutdown behavior.
        """

    def as_dict(self) -> Dict[str, Any]:
        """Return a serializable representation of the agent.

        This is intentionally simple; callers may extend or filter fields.
        """
        return {"id": self.id, "type": self.type, "capabilities": self.capabilities}
