import { useEffect, useState, type ReactNode } from 'react';
import { Activity, CheckCircle2, Clock3, Search, ShieldCheck } from 'lucide-react';
import { useMissionStore } from '../store/missionStore';

export function MissionControl() {
  const { mission, citations, isConnected } = useMissionStore();
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    if (!mission) return;
    const updateElapsed = () => setElapsed(Math.max(0, Math.floor((Date.now() - mission.startTime) / 1000)));
    updateElapsed();
    if (mission.status === 'completed' || mission.status === 'failed') return;
    const timer = window.setInterval(updateElapsed, 1000);
    return () => window.clearInterval(timer);
  }, [mission?.status, mission?.startTime]);

  if (!mission) return null;

  const total = mission.plan.length || 1;
  const done = mission.plan.filter((step) => step.status === 'completed').length;
  const pct = Math.round((done / total) * 100);
  const fmt = (seconds: number) => `${Math.floor(seconds / 60)}:${(seconds % 60).toString().padStart(2, '0')}`;
  const agentSignal = mission.status === 'awaiting_approval' ? 'Decision ready' : isConnected ? 'Collecting live evidence' : mission.status === 'completed' ? 'Mission closed' : 'Awaiting stream';

  return (
    <section className="mission-control card-surface" aria-label="Live incident dossier">
      <div className="mission-title-block">
        <span className="section-eyebrow">Live incident dossier</span>
        <h1>{mission.objective}</h1>
        <div className="mission-identifiers">
          <span><Clock3 size={13} /> Elapsed {fmt(elapsed)}</span>
          <span><Activity size={13} /> Trace {mission.id.slice(0, 8)}</span>
          <span className={isConnected ? 'connection-live' : 'connection-idle'}><i /> {agentSignal}</span>
        </div>
      </div>

      <div className="mission-progress-card">
        <div className="progress-summary"><span>Investigation progress</span><strong>{done}/{total} steps</strong></div>
        <div className="progress-track"><div className="progress-fill" style={{ width: `${pct}%` }} /></div>
        <span className="progress-note">The copilot will not recommend an infrastructure change without corroborated live evidence.</span>
      </div>

      <div className="signal-stack" aria-label="Integration status">
        <Signal icon={<Search size={14} />} label="Parallel Search" value={citations.length ? `${citations.length} sources` : 'Research queue'} active={isConnected} />
        <Signal icon={<Activity size={14} />} label="Grafana MCP" value={isConnected ? 'Telemetry check' : 'Integration required'} active={isConnected} />
        <Signal icon={<ShieldCheck size={14} />} label="Human gate" value={mission.status === 'awaiting_approval' ? 'Decision needed' : 'Protected'} active={mission.status === 'awaiting_approval'} />
      </div>
    </section>
  );
}

function Signal({ icon, label, value, active }: { icon: ReactNode; label: string; value: string; active: boolean }) {
  return (
    <div className={`signal-item ${active ? 'is-active' : ''}`}>
      <span className="signal-icon">{icon}</span>
      <span><strong>{label}</strong><small>{value}</small></span>
      {active ? <span className="signal-pulse" /> : <CheckCircle2 size={14} className="signal-check" />}
    </div>
  );
}
