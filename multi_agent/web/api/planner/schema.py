from typing import Any, Dict, Optional

from pydantic import BaseModel


class PlannerRequest(BaseModel):
    """Request body for planner endpoint.

    Contains the prompt to send to the planner and optional model/metadata.
    """

    prompt: str
    model: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class PlannerResponse(BaseModel):
    """Response returned by planner endpoint.

    `plan` is the generated plan text; `raw` contains the provider response.
    """

    plan: str
    raw: Dict[str, Any]
