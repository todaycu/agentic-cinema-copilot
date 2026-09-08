import { Radio } from 'lucide-react';
import { useMissionStore } from '../store/missionStore';
import { AgentCard } from './AgentCard';
import type { AgentState, AgentRole } from '../types';

const CREW: Array<{ id: string; name: string; role: AgentRole }> = [
  { id: 'standing-orchestrator', name: 'Mission Director', role: 'orchestrator' },
  { id: 'standing-researcher', name: 'Research Agent', role: 'researcher' },
  { id: 'standing-analyst', name: 'Metrics Analyst', role: 'analyst' },
  { id: 'standing-verifier', name: 'Verification Agent', role: 'verifier' },
];

export function CrewDeck() {
  const activeAgents = useMissionStore((state) => state.activeAgents);
  const liveAgents = Object.values(activeAgents);
  const crew: AgentState[] = CREW.map((member) => {
    const liveAgent = liveAgents.find((agent) => agent.role === member.role);
    return liveAgent || {
      ...member,
      status: 'idle',
      thoughtStream: [],
      toolsCalledCount: 0,
    };
  });
  const activeCount = crew.filter((agent) => agent.status === 'thinking' || agent.status === 'calling_tool').length;

  return (
    <section className="panel crew-panel">
      <div className="panel-header">
        <div>
          <span className="section-eyebrow">Specialist crew</span>
          <h2 className="panel-title">Evidence team</h2>
        </div>
        <span className={`crew-presence ${activeCount ? 'is-live' : ''}`}><Radio size={13} /> {activeCount ? `${activeCount} live` : 'Standing by'}</span>
      </div>
      <p className="crew-intro">Live status appears when the backend assigns a task. Roles remain visible so the decision path is always clear.</p>
      <div className="agents-grid">
        {crew.map((agent) => <AgentCard key={agent.id} agent={agent} />)}
      </div>
    </section>
  );
}
