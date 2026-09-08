import { useState } from 'react';
import { Activity, AlertTriangle, ArrowRight, BarChart3, CheckCircle2, Cpu, Flame, Play, Search, ShieldCheck, Sparkles } from 'lucide-react';
import { useMissionStore } from '../store/missionStore';

const PRESETS = [
  { label: 'GPU queue pressure', text: 'Render farm cluster-b GPU utilization spiked to 94% — 847 frames backlogged ahead of the overnight delivery.', icon: Flame },
  { label: 'Arnold render crash', text: 'Arnold 7.3.1 crashes on Scene 42 destruction sim across 6 render nodes after the latest driver rollout.', icon: Cpu },
  { label: 'Nuke pipeline stall', text: 'Nuke compositing pipeline stalled — suspected upstream EXR corruption is blocking the final comp queue.', icon: AlertTriangle },
  { label: 'Houdini regression', text: 'Render throughput dropped 40% after the Houdini 20.5 upgrade. Check for a known compatibility or scheduler issue.', icon: BarChart3 },
];

const FLOW = [
  { label: 'Incident', icon: Activity },
  { label: 'Parallel research', icon: Search },
  { label: 'Grafana telemetry', icon: BarChart3 },
  { label: 'Verification', icon: ShieldCheck },
];

export function MissionComposer() {
  const [objective, setObjective] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const { startMission, updateMission } = useMissionStore();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!objective.trim() || isSubmitting) return;

    const trimmedObjective = objective.trim();
    setSubmitError(null);
    setIsSubmitting(true);

    try {
      const res = await fetch('/api/v1/missions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ objective: trimmedObjective }),
      });

      if (!res.ok) throw new Error('The live incident service did not accept the request.');
      const backendMission = await res.json();
      startMission(trimmedObjective);
      updateMission({ id: backendMission.id, status: 'planning' });
    } catch (error) {
      console.warn('Live incident launch unavailable:', error);
      setSubmitError('We could not reach the live incident service. Check that the backend is running, then try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="mission-launch">
      <section className="launch-hero">
        <div className="launch-hero-copy">
          <div className="eyebrow"><Sparkles size={14} /> VFX operations / incident command</div>
          <h1>Turn a render farm alert into a confident production decision.</h1>
          <p className="launch-lede">
            Give a VFX supervisor one evidence-backed place to investigate GPU queues, renderer failures, and delivery risk — with a human decision before anything changes.
          </p>

          <div className="hero-actions">
            <a className="btn btn-primary hero-primary" href="#incident-dossier">
              <Play size={15} fill="currentColor" /> Open a live incident
            </a>
            <span className="hero-proof"><ShieldCheck size={15} /> Reviewable evidence, then a human decision.</span>
          </div>

          <div className="scenario-strip" aria-label="Scenario brief">
            <div className="scenario-label">Scenario brief</div>
            <div><strong>847</strong><span>frames at risk</span></div>
            <div><strong>94%</strong><span>GPU saturation</span></div>
            <div><strong>$2.4k/hr</strong><span>decision exposure</span></div>
          </div>
          <p className="scenario-note">These figures are a mission starter from the project brief, not live telemetry.</p>
        </div>

        <div className="launch-visual" aria-hidden="true">
          <div className="visual-orbit orbit-one" />
          <div className="visual-orbit orbit-two" />
          <div className="visual-core"><ClapperMark /></div>
          <div className="visual-pip pip-one" /><div className="visual-pip pip-two" /><div className="visual-pip pip-three" />
          <div className="visual-caption">RENDER // DECISION CONTROL</div>
        </div>
      </section>

      <section className="investigation-flow" aria-label="Investigation flow">
        {FLOW.map(({ label, icon: Icon }, index) => (
          <div className="flow-step" key={label}>
            <span className="flow-icon"><Icon size={16} /></span>
            <span>{label}</span>
            {index < FLOW.length - 1 && <ArrowRight className="flow-arrow" size={16} />}
          </div>
        ))}
        <div className="flow-gate"><ShieldCheck size={15} /> Human approval</div>
      </section>

      <div className="launch-grid">
        <section className="incident-composer card-surface" id="incident-dossier">
          <div className="composer-heading-row">
            <div>
              <span className="section-eyebrow">Start a live investigation</span>
              <h2>Open an incident dossier</h2>
            </div>
            <span className="live-contract"><i /> Live execution only</span>
          </div>

          <form onSubmit={handleSubmit}>
            <label className="field-label" htmlFor="incident-objective">What is your render farm telling you?</label>
            <textarea
              id="incident-objective"
              className="composer-input"
              placeholder="Describe the nodes, symptoms, renderer version, and when the incident began…"
              value={objective}
              onChange={(e) => setObjective(e.target.value)}
              disabled={isSubmitting}
              rows={5}
            />

            <div className="preset-heading"><span>Mission starters</span><span>Use a project-brief scenario</span></div>
            <div className="composer-presets">
              {PRESETS.map(({ label, text, icon: Icon }) => (
                <button key={label} type="button" className="preset-card" onClick={() => setObjective(text)} disabled={isSubmitting}>
                  <span className="preset-icon"><Icon size={16} /></span>
                  <span><strong>{label}</strong><small>{text}</small></span>
                </button>
              ))}
            </div>

            {submitError && <p className="form-error" role="alert"><AlertTriangle size={15} /> {submitError}</p>}
            <div className="composer-footer">
              <p><CheckCircle2 size={15} /> No simulated evidence. A failed integration is shown as a failed integration.</p>
              <button type="submit" className="btn btn-primary launch-button" disabled={!objective.trim() || isSubmitting}>
                <Play size={15} fill="currentColor" /> {isSubmitting ? 'Connecting to agents…' : 'Launch investigation'}
              </button>
            </div>
          </form>
        </section>

        <aside className="launch-aside">
          <div className="promise-card card-surface">
            <div className="promise-icon"><ShieldCheck size={21} /></div>
            <span className="section-eyebrow">Why this is safe</span>
            <h2>Evidence before action.</h2>
            <p>Every recommendation must reconcile live research with telemetry. If source evidence is unavailable, scaling is blocked.</p>
            <ul className="promise-list">
              <li><CheckCircle2 size={15} /> Parallel Search for known renderer issues</li>
              <li><CheckCircle2 size={15} /> Grafana MCP for operational telemetry</li>
              <li><CheckCircle2 size={15} /> Recorded human approval at the final gate</li>
            </ul>
          </div>
          <div className="aside-footer"><Activity size={15} /><span>Designed for VFX &amp; animation production operations.</span></div>
        </aside>
      </div>
    </div>
  );
}

function ClapperMark() {
  return (
    <span className="clapper-mark">
      <span /><span /><span /><span />
    </span>
  );
}
