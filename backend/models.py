from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict, Union
from enum import Enum
from datetime import datetime

class MissionStatus(str, Enum):
    idle = "idle"
    planning = "planning"
    executing = "executing"
    awaiting_approval = "awaiting_approval"
    completed = "completed"
    failed = "failed"

class Citation(BaseModel):
    id: str
    source_type: str
    title: str
    url: str
    snippet: str
    trust_score: float

class TaskStep(BaseModel):
    id: str
    title: str
    assigned_agent: str
    status: str
    output_summary: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None

class ApprovalRequest(BaseModel):
    id: str
    tool_name: str
    description: str
    impact_level: str
    parameters: Dict[str, Any]

class Mission(BaseModel):
    id: str
    objective: str
    status: MissionStatus = MissionStatus.idle
    steps: List[TaskStep] = []
    created_at: datetime = Field(default_factory=datetime.utcnow)
    recommendation: Optional[str] = None
    citations: List[Citation] = []

class AgentEvent(BaseModel):
    type: str
    agent_id: str
    agent_name: str = ""
    role: str = ""
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SSEEvent(BaseModel):
    event: str
    data: Union[AgentEvent, Mission, Dict[str, Any]]
