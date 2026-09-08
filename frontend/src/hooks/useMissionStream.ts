import { useEffect, useRef } from 'react';
import { useMissionStore } from '../store/missionStore';
import type { AgentRole, TaskStep } from '../types';

const ROLE_BY_AGENT: Record<string, AgentRole> = {
  orchestrator: 'orchestrator',
  research_agent: 'researcher',
  data_agent: 'analyst',
  verification_agent: 'verifier',
};

const NAME_BY_AGENT: Record<string, string> = {
  orchestrator: 'Mission Director',
  research_agent: 'Research Agent',
  data_agent: 'Metrics Analyst',
  verification_agent: 'Verification Agent',
};

const roleForAgent = (agentId?: string): AgentRole => ROLE_BY_AGENT[agentId || ''] || 'analyst';
const nameForAgent = (agentId?: string) => NAME_BY_AGENT[agentId || ''] || agentId || 'Agent';

/** Streams only backend events. A connection failure is surfaced, never replaced with fabricated evidence. */
export function useMissionStream() {
  const missionId = useMissionStore((state) => state.mission?.id);
  const connectedMission = useRef<string | null>(null);
  const streamRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!missionId || connectedMission.current === missionId) return;
    connectedMission.current = missionId;

    const { updateMission, updateAgent, addCitation, addMessage, setInterrupt, setConnected } = useMissionStore.getState();
    const es = new EventSource(`/api/v1/missions/${missionId}/stream`);
    streamRef.current = es;
    let receivedEvent = false;
    let closed = false;

    const isCurrentStream = () => !closed && streamRef.current === es;
    const listen = (eventName: string, handler: (event: MessageEvent) => void) => {
      es.addEventListener(eventName, (event) => {
        if (isCurrentStream()) handler(event as MessageEvent);
      });
    };

    es.onopen = () => {
      if (!isCurrentStream()) return;
      setConnected(true);
      addMessage('Connected to live backend SSE stream', 'system', 'info');
    };

    listen('MISSION_INIT', () => {
      receivedEvent = true;
      updateMission({ status: 'planning' });
      addMessage('Copilot is analyzing the incident report.', 'Mission Director', 'info');
    });

    listen('STEP_UPDATE', (event) => {
      receivedEvent = true;
      const data = JSON.parse(event.data);
      const plan: TaskStep[] = (data.steps || []).map((step: any) => ({
        id: step.id,
        title: step.title,
        assignedRole: roleForAgent(step.assigned_agent),
        status: step.status || 'pending',
      }));
      updateMission({ plan, status: 'executing' });
      addMessage('Incident decomposed into an investigation plan.', 'Mission Director', 'success');
    });

    listen('AGENT_STATUS', (event) => {
      receivedEvent = true;
      const data = JSON.parse(event.data);
      const agentId = data.agent_id || 'agent';
      const status = data.data?.status || 'thinking';
      const thought = data.data?.thought || '';
      updateAgent(agentId, {
        id: agentId,
        name: nameForAgent(agentId),
        role: roleForAgent(agentId),
        status: status === 'completed' ? 'completed' : status === 'failed' ? 'failed' : 'thinking',
        thoughtStream: [thought || `Agent status: ${status}`],
      });
      if (thought) addMessage(thought, nameForAgent(agentId), 'info');
    });

    listen('TOOL_START', (event) => {
      receivedEvent = true;
      const data = JSON.parse(event.data);
      const agentId = data.agent_id || 'agent';
      const toolName = data.data?.tool || 'executing_tool';
      updateAgent(agentId, {
        id: agentId,
        name: nameForAgent(agentId),
        role: roleForAgent(agentId),
        status: 'calling_tool',
        currentTool: toolName,
        toolStartTime: Date.now(),
      });
      addMessage(`Executing ${toolName}()`, nameForAgent(agentId), 'info');
    });

    listen('TOOL_END', (event) => {
      receivedEvent = true;
      const data = JSON.parse(event.data);
      const agentId = data.agent_id || 'agent';
      const current = useMissionStore.getState().activeAgents[agentId]?.toolsCalledCount || 0;
      updateAgent(agentId, {
        id: agentId,
        name: nameForAgent(agentId),
        role: roleForAgent(agentId),
        status: 'thinking',
        currentTool: undefined,
        toolDurationMs: Math.round((data.data?.duration || 0) * 1000),
        toolsCalledCount: current + 1,
      });
    });

    listen('EVIDENCE_ADDED', (event) => {
      receivedEvent = true;
      const citations = JSON.parse(event.data).data?.citations || [];
      citations.forEach((citation: any) => addCitation({
        id: citation.id || String(Math.random()),
        title: citation.title || 'Source citation',
        sourceType: citation.source_type || 'web',
        url: citation.url || undefined,
        snippet: citation.snippet || '',
        trustScore: citation.trust_score <= 1 ? Math.round(citation.trust_score * 100) : citation.trust_score,
      }));
      if (citations.length) addMessage(`Surfaced ${citations.length} live evidence source(s).`, 'system', 'success');
    });

    listen('INTERRUPT_TRIGGERED', (event) => {
      receivedEvent = true;
      const data = JSON.parse(event.data);
      updateMission({ status: 'awaiting_approval' });
      setInterrupt({
        id: data.interruptId || 'approval-1',
        proposedAction: data.proposedAction,
        impactLevel: data.impactLevel || 'high',
        payload: data.payload || data,
      });
      addMessage('Human approval required for the proposed infrastructure change.', 'Mission Director', 'warning');
    });

    listen('MISSION_COMPLETE', (event) => {
      receivedEvent = true;
      const data = JSON.parse(event.data);
      const terminalStatus = data.status === 'failed' ? 'failed' : 'completed';
      updateMission({
        status: terminalStatus,
        recommendation: data.recommendation || data.feedback || undefined,
      });
      Object.keys(useMissionStore.getState().activeAgents).forEach((agentId) => {
        updateAgent(agentId, { status: terminalStatus, currentTool: undefined });
      });
      addMessage(data.recommendation || data.feedback || 'Investigation complete.', 'Mission Director', terminalStatus === 'failed' ? 'error' : 'success');
      setConnected(false);
      closed = true;
      if (streamRef.current === es) streamRef.current = null;
      es.close();
    });

    es.onerror = () => {
      if (!isCurrentStream()) return;
      closed = true;
      if (streamRef.current === es) streamRef.current = null;
      es.close();
      setConnected(false);
      if (!receivedEvent) {
        updateMission({ status: 'failed' });
        addMessage('Unable to connect to the live backend. No simulated investigation was run.', 'system', 'error');
      }
    };

    return () => {
      closed = true;
      if (streamRef.current === es) {
        streamRef.current = null;
        if (connectedMission.current === missionId) connectedMission.current = null;
        setConnected(false);
      }
      es.close();
    };
  }, [missionId]);
}
