from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse
from backend.models import Mission, MissionStatus
from backend.agents.orchestrator import Orchestrator, missions_db
from backend.services.event_bus import event_bus
from typing import List
import uuid
import json

router = APIRouter(prefix="/api/v1/missions", tags=["missions"])

class CreateMissionRequest(BaseModel):
    objective: str

@router.post("", response_model=Mission)
async def create_mission(req: CreateMissionRequest, background_tasks: BackgroundTasks):
    try:
        mission_id = str(uuid.uuid4())
        mission = Mission(id=mission_id, objective=req.objective)
        missions_db[mission_id] = mission
        orchestrator = Orchestrator(mission)
        background_tasks.add_task(orchestrator.run)
        return mission
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{mission_id}/stream")
async def stream_mission(mission_id: str):
    if mission_id not in missions_db:
        raise HTTPException(status_code=404, detail="Mission not found")

    async def event_generator():
        async for event in event_bus.subscribe(mission_id):
            # Serialize data correctly — send just the data payload, not the entire SSEEvent wrapper
            data = event.data
            if hasattr(data, "model_dump"):
                payload = data.model_dump()
            elif isinstance(data, dict):
                payload = data
            else:
                payload = str(data)

            yield {
                "event": event.event,
                "data": json.dumps(payload, default=str)
            }

    return EventSourceResponse(event_generator())

@router.get("", response_model=List[Mission])
async def list_missions():
    return list(missions_db.values())

@router.get("/{mission_id}", response_model=Mission)
async def get_mission(mission_id: str):
    if mission_id not in missions_db:
        raise HTTPException(status_code=404, detail="Mission not found")
    return missions_db[mission_id]

@router.post("/{mission_id}/approve")
async def approve_mission(mission_id: str, approved: bool, feedback: str = ""):
    if mission_id not in missions_db:
        raise HTTPException(status_code=404, detail="Mission not found")
    mission = missions_db[mission_id]
    if approved:
        mission.status = MissionStatus.completed
        await event_bus.publish(mission_id, __import__('backend.models', fromlist=['SSEEvent']).SSEEvent(
            event="MISSION_COMPLETE",
            data={"mission_id": mission_id, "status": "completed", "feedback": feedback}
        ))
    else:
        mission.status = MissionStatus.failed
        await event_bus.publish(mission_id, __import__('backend.models', fromlist=['SSEEvent']).SSEEvent(
            event="MISSION_COMPLETE",
            data={"mission_id": mission_id, "status": "failed", "feedback": feedback}
        ))
    return mission
