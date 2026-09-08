import { useState } from 'react';
import { CheckCircle2, CircleAlert, Clock3, Cpu, DollarSign, Layers, Server, ShieldAlert, XCircle } from 'lucide-react';
import { useMissionStore } from '../store/missionStore';

type Submitting = 'approve' | 'reject' | null;

export function ApprovalGate() {
  const { interrupt, mission, setInterrupt, updateMission, addMessage } = useMissionStore();
  const [rejecting, setRejecting] = useState(false);
  const [feedback, setFeedback] = useState('');
  const [submitting, setSubmitting] = useState<Submitting>(null);
  if (!interrupt) return null;

  const submitDecision = async (approved: boolean) => {
    if (!mission) return;
    const feedbackValue = approved ? '' : feedback;
    setSubmitting(approved ? 'approve' : 'reject');
    try {
      const response = await fetch(
        `/api/v1/missions/${mission.id}/approve?approved=${approved}&feedback=${encodeURIComponent(feedbackValue)}`,
        { method: 'POST' },
      );
      if (!response.ok) throw new Error('The backend did not accept the approval decision.');
      setInterrupt(null);
      updateMission({ status: approved ? 'completed' : 'failed' });
      addMessage(
        approved
          ? 'Recommendation approved and recorded. No infrastructure command was sent by this demo.'
          : `Recommendation rejected: ${feedbackValue || 'No reason given'}`,
        'system',
        approved ? 'success' : 'error',
      );
    } catch (error) {
      addMessage(error instanceof Error ? error.message : 'Unable to record the approval decision.', 'system', 'error');
    } finally {
      setSubmitting(null);
    }
  };

  const payload = interrupt.payload || {};
  const actionContext = [
    { icon: Server, label: 'Target', value: payload.target_cluster },
    { icon: Cpu, label: 'Proposed capacity', value: payload.add_nodes && payload.node_type ? `${payload.add_nodes} × ${payload.node_type}` : payload.node_type },
    { icon: Layers, label: 'Workload impact', value: payload.redistribute_frames && `${payload.redistribute_frames} pending frames` },
    { icon: DollarSign, label: 'Cost context', value: payload.estimated_cost },
    { icon: Clock3, label: 'Estimated recovery', value: payload.estimated_completion },
  ].filter((item) => item.value);

  return (
    <div className="gate-overlay" role="dialog" aria-modal="true" aria-labelledby="approval-heading">
      <section className="gate-card card-surface">
        <div className="gate-banner"><ShieldAlert size={16} /> Human decision required <span>High-impact actions stay gated</span></div>
        <div className="gate-header">
          <div className="gate-icon"><ShieldAlert size={23} /></div>
          <div>
            <span className="section-eyebrow">Authorization checkpoint</span>
            <h2 id="approval-heading">Review the production recommendation</h2>
            <p>The team has stopped at a human gate. Record a decision only after reviewing the evidence above.</p>
          </div>
          <span className={`impact-tag ${interrupt.impactLevel}`}>{interrupt.impactLevel} impact</span>
        </div>

        <div className="gate-recommendation"><span>Proposed action</span><p>{interrupt.proposedAction}</p></div>

        {actionContext.length > 0 && (
          <div className="gate-action-card">
            {actionContext.map(({ icon: Icon, label, value }) => (
              <div className="gate-action-row" key={label}><Icon size={15} /><span>{label}</span><strong>{String(value)}</strong></div>
            ))}
          </div>
        )}

        <div className="approval-disclaimer"><CircleAlert size={16} /><span><strong>What approval does:</strong> records the supervisor's authorization in this demo. It does not send an infrastructure command.</span></div>

        {rejecting && (
          <div className="rejection-field">
            <label htmlFor="approval-feedback">What should the crew re-check?</label>
            <textarea id="approval-feedback" className="gate-input" placeholder="Optional feedback for the investigation…" value={feedback} onChange={(event) => setFeedback(event.target.value)} autoFocus />
          </div>
        )}

        <div className="gate-actions">
          {!rejecting ? (
            <>
              <button className="btn btn-ghost" type="button" disabled={Boolean(submitting)} onClick={() => setRejecting(true)}><XCircle size={16} /> Reject / request changes</button>
              <button className="btn btn-success" type="button" disabled={Boolean(submitting)} onClick={() => submitDecision(true)}><CheckCircle2 size={16} /> {submitting === 'approve' ? 'Recording decision…' : 'Record approval'}</button>
            </>
          ) : (
            <>
              <button className="btn btn-ghost" type="button" disabled={Boolean(submitting)} onClick={() => setRejecting(false)}>Back to review</button>
              <button className="btn btn-danger" type="button" disabled={Boolean(submitting)} onClick={() => submitDecision(false)}><XCircle size={16} /> {submitting === 'reject' ? 'Recording decision…' : 'Record rejection'}</button>
            </>
          )}
        </div>
      </section>
    </div>
  );
}
