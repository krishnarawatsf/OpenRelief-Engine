"use client";

import { useState } from "react";
import type { Incident } from "./types";

type IncidentDetailsModalProps = {
  incident: Incident;
  apiUrl: string;
  onClose: () => void;
};

export default function IncidentDetailsModal({ incident, apiUrl, onClose }: IncidentDetailsModalProps) {
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  async function exportCap() {
    setExporting(true);
    setError("");
    try {
      const response = await fetch(`${apiUrl}/api/incidents/${encodeURIComponent(incident.id)}/cap.xml`);
      if (!response.ok) throw new Error(`CAP export failed (${response.status}).`);
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = "alert_CAP_v1.2.xml";
      anchor.click();
      URL.revokeObjectURL(url);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to export the CAP alert.");
    } finally {
      setExporting(false);
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => {
      if (event.target === event.currentTarget) onClose();
    }}>
      <section className="incident-modal" role="dialog" aria-modal="true" aria-labelledby="incident-title">
        <div className="modal-heading">
          <div>
            <h2 id="incident-title">{incident.incident_type} incident</h2>
            <p>{incident.status} · CAP severity {incident.cap_severity}</p>
          </div>
          <button className="close-button" type="button" aria-label="Close incident details" onClick={onClose}>×</button>
        </div>
        <div className="modal-content">
          <div className="modal-stats">
            <div className="modal-stat"><span>Urgency</span><strong>{incident.urgency_rating}/5</strong></div>
            <div className="modal-stat"><span>Casualties</span><strong>{incident.casualty_count}</strong></div>
            <div className="modal-stat"><span>Priority</span><strong>{incident.priority_score}</strong></div>
          </div>
          <p>{incident.transcript}</p>
          <p>Assigned unit: {incident.assigned_responder?.unit_name ?? "Awaiting available responder"}</p>
          <button type="button" className="export-button" disabled={exporting} onClick={() => void exportCap()}>
            {exporting ? "Preparing XML…" : "Export CAP v1.2 Alert"}
          </button>
          {error && <div className="error-text" role="alert">{error}</div>}
        </div>
      </section>
    </div>
  );
}
