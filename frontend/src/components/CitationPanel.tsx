import { BarChart3, ExternalLink, Globe2, Link2, ShieldCheck } from 'lucide-react';
import { useMissionStore } from '../store/missionStore';

export function CitationPanel() {
  const citations = useMissionStore((state) => state.citations);
  const trustPct = (score: number) => Math.max(0, Math.min(100, score <= 1 ? Math.round(score * 100) : Math.round(score)));
  const isMetrics = (sourceType: string) => /grafana|database|metrics|prometheus|loki/i.test(sourceType);

  return (
    <section className="panel evidence-panel">
      <div className="panel-header">
        <div>
          <span className="section-eyebrow">Source of truth</span>
          <h2 className="panel-title">Evidence ledger</h2>
        </div>
        <span className="panel-count">{citations.length}</span>
      </div>
      <p className="evidence-intro"><ShieldCheck size={14} /> Only sources collected by this live mission appear here.</p>
      <div className="evidence-list">
        {citations.length === 0 ? (
          <div className="empty-evidence">
            <span><Link2 size={20} /></span>
            <div><strong>No evidence collected yet</strong><p>Research citations and Grafana context will be added as the agents return them.</p></div>
          </div>
        ) : citations.map((citation) => {
          const metrics = isMetrics(citation.sourceType);
          const trust = trustPct(citation.trustScore);
          return (
            <article key={citation.id} className="citation-item">
              <span className={`citation-icon ${metrics ? 'metrics' : 'research'}`}>{metrics ? <BarChart3 size={16} /> : <Globe2 size={16} />}</span>
              <div className="citation-body">
                <div className="citation-topline"><span>{metrics ? 'Grafana telemetry' : citation.sourceType || 'Parallel research'}</span><span>{trust}% confidence</span></div>
                {citation.url ? (
                  <a className="citation-link" href={citation.url} target="_blank" rel="noreferrer">
                    {citation.title} <ExternalLink size={12} aria-hidden="true" />
                  </a>
                ) : <h3>{citation.title}</h3>}
                {citation.snippet && <p>{citation.snippet}</p>}
                <div className="trust-track"><i style={{ width: `${trust}%` }} /></div>
              </div>
            </article>
          );
        })}
      </div>
    </section>
  );
}
