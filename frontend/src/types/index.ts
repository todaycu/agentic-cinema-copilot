export type AgentRole = 'orchestrator' | 'researcher' | 'analyst' | 'verifier';
export type AgentStatus = 'idle' | 'thinking' | 'calling_tool' | 'completed' | 'failed';

export interface TaskStep {
  id: string;
  title: string;
  assignedRole: AgentRole;
  status: 'pending' | 'active' | 'completed' | 'failed';
}

export interface AgentState {
  id: string;
  name: string;
  role: AgentRole;
  status: AgentStatus;
  currentTool?: string;
  toolDurationMs?: number;
  toolStartTime?: number;
  thoughtStream: string[];
  toolsCalledCount: number;
}

export interface Citation {
  id: string;
  title: string;
  sourceType: string;
  url?: string;
  snippet: string;
  trustScore: number;
}

export interface ApprovalRequest {
  id: string;
  proposedAction: string;
  impactLevel: 'low' | 'medium' | 'high';
  payload: any;
}

export interface Mission {
  id: string;
  objective: string;
  status: 'planning' | 'executing' | 'awaiting_approval' | 'completed' | 'failed';
  plan: TaskStep[];
  startTime: number;
  /** The backend's evidence-backed conclusion, retained for the decision brief. */
  recommendation?: string;
}

export type SSEEventType =
  | 'MISSION_INIT'
  | 'AGENT_STATUS'
  | 'TOOL_START'
  | 'TOOL_END'
  | 'EVIDENCE_ADDED'
  | 'INTERRUPT_TRIGGERED'
  | 'TOKEN_STREAM'
  | 'STEP_UPDATE'
  | 'MISSION_COMPLETE';
