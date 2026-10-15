import type { Incident } from "./types";

type LiveFeedProps = {
  incidents: Incident[];
  onSelect: (incident: Incident) => void;
};

export default function LiveFeed({ incidents, onSelect }: LiveFeedProps) {
  const sorted = [...incidents].sort((left, right) => right.priority_score - left.priority_score);
  return (
    <section className="feed-panel">
      <div className="section-heading">
        <h2>ACTIVE INCIDENTS</h2>
        <span>{sorted.length.toString().padStart(2, "0")} OPEN</span>
      </div>
      <div className="feed-list">
        {sorted.length === 0 ? (
          <div className="empty-feed">No active incidents. The response zone is clear.</div>
        ) : sorted.map((incident) => (
          <button key={incident.id} type="button" className={`incident-row priority-${incident.urgency_rating}`}
            onClick={() => onSelect(incident)}>
            <div className="incident-topline">
              <strong>{incident.incident_type}</strong>
              <span className="urgency-pill">URGENCY {incident.urgency_rating}/5</span>
            </div>
            <p>{incident.transcript}</p>
            <div className="incident-meta">
              <span>{incident.status}</span>
              <span>Priority {incident.priority_score}</span>
            </div>
          </button>
        ))}
      </div>
    </section>
  );
}
