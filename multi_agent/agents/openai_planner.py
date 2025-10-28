from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx

from .base import Agent, Message


class OpenAIPlanner(Agent):
    """Planner agent that calls OpenAI Chat Completions to generate a plan.

    Expects incoming message.payload to contain a 'prompt' key with text.
    The agent returns a single Message of type 'plan.result' with payload
    containing 'plan' (str) and 'raw' (the provider response).
    """

    OPENAI_URL = "https://api.openai.com/v1/chat/completions"

    def __init__(
        self,
        id: Optional[str] = None,
        capabilities: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(id=id, capabilities=capabilities)
        self.type = "openai_planner"
        self.api_key = os.getenv("OPENAI_API_KEY")

    async def start(self) -> None:
        """Start the planner agent (no-op)."""

    async def stop(self) -> None:
        """Stop the planner agent (no-op)."""

    async def _call_openai(
        self,
        prompt: str,
        model: str = "gpt-3.5-turbo",
    ) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY not set in environment")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 512,
            "temperature": 0.2,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self.OPENAI_URL, json=payload, headers=headers)
            resp.raise_for_status()
            return resp.json()

    async def handle_message(self, message: Message) -> Optional[List[Message]]:
        """Call the OpenAI API using the prompt in message.payload.

        Returns a list with a single Message containing the `plan` and raw
        provider response under the payload.
        """
        prompt = None
        model = "gpt-3.5-turbo"
        if message.payload and isinstance(message.payload, dict):
            prompt = message.payload.get("prompt")
            model = message.payload.get("model", model)

        if not prompt:
            raise ValueError("Message payload must include 'prompt' string")

        result = await self._call_openai(prompt=prompt, model=model)

        # try to extract the assistant content conservatively
        plan_text = ""
        try:
            choices = result.get("choices") or []
            if choices:
                delta = choices[0].get("message") or {}
                plan_text = delta.get("content", "")
        except Exception:
            plan_text = ""

        reply = Message(
            type="plan.result",
            sender=self.id,
            target=message.sender,
            payload={"plan": plan_text, "raw": result},
            trace_id=message.trace_id,
        )
        return [reply]
