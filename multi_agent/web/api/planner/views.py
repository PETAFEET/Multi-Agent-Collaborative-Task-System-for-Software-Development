from fastapi import APIRouter, HTTPException

from multi_agent.agents.base import Message
from multi_agent.agents.openai_planner import OpenAIPlanner
from multi_agent.web.api.planner.schema import PlannerRequest, PlannerResponse

router = APIRouter()


@router.post("/", response_model=PlannerResponse, tags=["planner"])
async def generate_plan(req: PlannerRequest) -> PlannerResponse:
    """Generate a plan using the OpenAI-backed Planner agent.

    The endpoint instantiates an OpenAIPlanner and calls its handle_message
    synchronously (await). It requires OPENAI_API_KEY set in environment.
    """
    planner = OpenAIPlanner(id="openai-planner")

    msg = Message(
        type="plan.request",
        sender="api",
        payload={"prompt": req.prompt, "model": req.model or "gpt-3.5-turbo"},
    )
    try:
        replies = await planner.handle_message(msg)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    if not replies:
        raise HTTPException(status_code=500, detail="planner returned no result")

    # return first reply's payload.plan
    first = replies[0]
    plan_text = first.payload.get("plan", "")
    raw = first.payload.get("raw", {})
    return PlannerResponse(plan=plan_text, raw=raw)
