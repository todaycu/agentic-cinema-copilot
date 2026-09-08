import { CheckCircle2, Clock3, Search, XCircle } from 'lucide-react';
import { useMissionStore } from '../store/missionStore';
import type { TaskStep } from '../types';

const STANDING_PLAN: TaskStep[] = [
  { id: 'standing-research', title: 'Check known renderer and driver failure signatures', assignedRole: 'researcher', status: 'pending' },
  { id: 'standing-telemetry', title: 'Inspect GPU queue, alert, and job telemetry', assignedRole: 'analyst', status: 'pending' },
  { id: 'standing-verify', title: 'Corroborate research against operational evidence', assignedRole: 'verifier', status: 'pending' },
  { id: 'standing-decision', title: 'Prepare a human-reviewed production decision', assignedRole: 'orchestrator', status: 'pending' },
];

const ROLE_DESCRIPTION: Record<string, string> = {
  researcher: 'Parallel Search intelligence',
  analyst: 'Grafana MCP telemetry',
  verifier: 'Cross-source validation',
  orchestrator: 'Decision and approval routing',
};

export function TaskPlanStepper() {
  const mission = useMissionStore((state) => state.mission);
  if (!mission) return null;

  const waitingForPlan = mission.plan.length === 0;
  const plan = waitingForPlan ? STANDING_PLAN : mission.plan;
  const done = plan.filter((step) => step.status === 'completed').length;

  return (
    <section className="panel plan-panel">
      <div className="panel-header">
        <div>
          <span className="section-eyebrow">Agent orchestration</span>
          <h2 className="panel-title">Investigation plan</h2>
        </div>
        <span className="panel-count">{done}/{plan.length}</span>
      </div>
      <div className="plan-context">
        <Clock3 size={14} /> {waitingForPlan ? 'Waiting for the backend to publish the live plan.' : 'Each step is visible, attributable, and auditable.'}
      </div>
      <ol className="stepper-list">
        {plan.map((step, index) => (
          <li key={step.id} className={`step-row ${step.status}`}>
            <div className="step-rail">
              <StepStatus status={step.status} index={index + 1} />
              {index < plan.length - 1 && <span className="step-line" />}
            </div>
            <div className="step-content">
              <div className="step-header">
                <span className="step-label">{step.title}</span>
                <span className={`step-role ${step.assignedRole}`}>{step.assignedRole}</span>
              </div>
              <p>{ROLE_DESCRIPTION[step.assignedRole] || 'Investigation task'}</p>
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}

function StepStatus({ status, index }: { status: TaskStep['status']; index: number }) {
  if (status === 'completed') return <span className="step-num"><CheckCircle2 size={17} /></span>;
  if (status === 'failed') return <span className="step-num"><XCircle size={17} /></span>;
  if (status === 'active') return <span className="step-num is-running"><Search size={15} /></span>;
  return <span className="step-num"><b>{index}</b></span>;
}
