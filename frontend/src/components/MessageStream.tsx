import { useEffect, useRef } from 'react';
import { Activity } from 'lucide-react';
import { useMissionStore } from '../store/missionStore';

export function MessageStream() {
  const messages = useMissionStore((state) => state.messages);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const list = listRef.current;
    if (list) list.scrollTo({ top: list.scrollHeight, behavior: 'smooth' });
  }, [messages.length]);

  const fmt = (timestamp: number) => new Date(timestamp).toLocaleTimeString('en-US', {
    hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit',
  });

  return (
    <section className="panel trace-panel">
      <div className="panel-header">
        <div>
          <span className="section-eyebrow">Auditable trace</span>
          <h2 className="panel-title">Mission activity</h2>
        </div>
        <span className="panel-count">{messages.length}</span>
      </div>
      <div className="trace-legend"><Activity size={14} /> Events are contained here so the dashboard never steals your scroll position.</div>
      <div className="log-list" ref={listRef} aria-live="polite">
        {messages.length === 0 ? (
          <div className="empty-log">Waiting for the live mission stream…</div>
        ) : messages.map((message) => (
          <div key={message.id} className={`log-entry ${message.type || 'info'}`}>
            <time>{fmt(message.timestamp)}</time>
            <div><span className="log-role">{message.role || 'system'}</span><p>{message.text}</p></div>
          </div>
        ))}
      </div>
    </section>
  );
}
