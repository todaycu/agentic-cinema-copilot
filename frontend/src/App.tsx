import { Clapperboard, RotateCcw, ShieldCheck, Sparkles } from 'lucide-react';
import { useMissionStore } from './store/missionStore';
import { useMissionStream } from './hooks/useMissionStream';
import { MissionComposer } from './components/MissionComposer';
import { MissionControl } from './components/MissionControl';
import { DecisionPanel } from './components/DecisionPanel';
import { TaskPlanStepper } from './components/TaskPlanStepper';
import { CrewDeck } from './components/CrewDeck';
import { ApprovalGate } from './components/ApprovalGate';
import { CitationPanel } from './components/CitationPanel';
import { MessageStream } from './components/MessageStream';

function StatusPill({ status }: { status: string }) {
  const active = status === 'executing' || status === 'planning';
  const label = status === 'awaiting_approval' ? 'approval required' : status.replace('_', ' ');

  return (
    <span className={`status-pill ${status}`}>
      <span className={`status-indicator ${active ? 'pulse' : ''}`} />
      {label}
    </span>
  );
}

export default function App() {
  const { mission, interrupt, resetMission } = useMissionStore();
  useMissionStream();

  return (
    <div className="app-shell">
      <div className="ambient-grid" aria-hidden="true" />

      <header className="topbar">
        <div className="topbar-inner">
          <div className="topbar-brand">
            <div className="brand-mark"><Clapperboard size={18} /></div>
            <div>
              <span className="brand-kicker">Agentic Cinema / Production Ops</span>
              <span className="brand-name">Render Farm <strong>Incident Copilot</strong></span>
            </div>
          </div>

          <div className="topbar-meta">
            <span className="system-chip"><Sparkles size={13} /> Gemini Flash</span>
            <span className="system-chip"><ShieldCheck size={13} /> Evidence-first</span>
            {mission && <StatusPill status={mission.status} />}
            {mission && (
              <button className="new-incident-btn" type="button" onClick={resetMission}>
                <RotateCcw size={14} /> New incident
              </button>
            )}
          </div>
        </div>
      </header>

      <main className={`app-main ${mission ? 'has-mission' : 'is-launch'}`}>
        {mission ? (
          <>
            <MissionControl />
            <DecisionPanel />
            <div className="workspace">
              <div className="workspace-left">
                <TaskPlanStepper />
                <MessageStream />
              </div>
              <div className="workspace-right">
                <CrewDeck />
                <CitationPanel />
              </div>
            </div>
          </>
        ) : (
          <MissionComposer />
        )}
      </main>

      {interrupt && <ApprovalGate />}
    </div>
  );
}
