import { BarChart3, Brain, Search, ShieldCheck } from 'lucide-react';
import type { AgentState } from '../types';

const ROLE_ICON = {
  researcher: Search,
  analyst: BarChart3,
  verifier: ShieldCheck,
  orchestrator: Brain,
};

const ROLE_COPY: Record<string, string> = {
  researcher: 'Finds current, attributable failure intelligence through Parallel Search.',
  analyst: 'Reads Grafana MCP telemetry and operational alert context.',
  verifier: 'Blocks unsupported conclusions and validates source agreement.',
  orchestrator: 'Coordinates specialists and routes high-impact decisions.',
};

export function AgentCard({ agent }: { agent: AgentState }) {
  const Icon = ROLE_ICON[agent.role] || Brain;
  const isActive = agent.status === 'thinking' || agent.status === 'calling_tool';
  const latestThought = agent.thoughtStream[agent.thoughtStream.length - 1];
  const statusLabel = agent.status === 'calling_tool' ? 'Running tool' : agent.status === 'thinking' ? 'Reasoning' : agent.status === 'completed' ? 'Complete' : agent.status === 'failed' ? 'Needs attention' : 'Standing by';

  return (
    <article className={`agent-card ${agent.role} ${isActive ? 'is-active' : ''}`}>
      <div className="agent-top">
        <span className={`agent-icon ${agent.role}`}><Icon size={17} /></span>
        <span className={`agent-status ${agent.status}`}><i /> {statusLabel}</span>
      </div>
      <h3>{agent.name}</h3>
      <p className="agent-summary">{ROLE_COPY[agent.role]}</p>

      {agent.status === 'calling_tool' && agent.currentTool ? (
        <div className="agent-tool"><span className="tool-spinner" /> <code>{agent.currentTool}()</code></div>
      ) : (
        <div className="agent-log">{latestThought || 'Waiting for a live assignment.'}</div>
      )}

      <div className="agent-footer">
        <span>Tools <strong>{agent.toolsCalledCount}</strong></span>
        {agent.toolDurationMs != null && <span>Last <strong>{agent.toolDurationMs}ms</strong></span>}
      </div>
    </article>
  );
}
