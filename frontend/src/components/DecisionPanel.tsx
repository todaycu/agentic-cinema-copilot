import { AlertTriangle, CheckCircle2, CircleDot, ShieldCheck } from 'lucide-react';
import { useMissionStore } from '../store/missionStore';

export function DecisionPanel() {
  const { mission, citations, isConnected } = useMissionStore();
  if (!mission) return null;

  const completed = mission.status === 'completed';
  const failed = mission.status === 'failed';
  const heldForEvidence = /incomplete|could not be corroborated|unavailable/i.test(mission.recommendation || '');
  const title = failed
    ? 'Investigation needs attention'
    : heldForEvidence
      ? 'Decision held until evidence is complete'
      : completed
        ? 'Investigation outcome'
        : 'Evidence is being assembled';
  const detail = mission.recommendation || (failed
    ? 'The live investigation ended before a verified recommendation could be recorded.'
    : completed
      ? 'The mission has closed and the evidence trail remains available for review.'
      : mission.status === 'awaiting_approval'
        ? 'A recommendation has reached the human authorization checkpoint.'
        : 'The copilot is collecting live research and telemetry before it can propose an action.');

  return (
    <section className={`decision-panel ${failed ? 'is-failed' : heldForEvidence ? 'is-held' : completed ? 'is-complete' : ''}`} aria-label="Decision brief">
      <div className="decision-icon">
        {failed || heldForEvidence ? <AlertTriangle size={19} /> : completed ? <CheckCircle2 size={19} /> : <CircleDot size={19} />}
      </div>
      <div className="decision-copy">
        <span className="section-eyebrow">Decision brief</span>
        <h2>{title}</h2>
        <p>{detail}</p>
      </div>
      <div className="decision-meta">
        <span><ShieldCheck size={14} /> {citations.length} live source{citations.length === 1 ? '' : 's'} collected</span>
        <span className={isConnected ? 'connection-live' : 'connection-idle'}>
          <i /> {isConnected ? 'Live mission stream connected' : 'No active stream'}
        </span>
      </div>
    </section>
  );
}
