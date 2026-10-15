"use client";

import { useState } from "react";
import type { Incident } from "./types";

const SCENARIOS = [
  {
    name: "Scenario A · Critical Medical",
    text: "Emergency at SRM Tech Park! Car crash with 2 passengers unconscious and heavy bleeding!",
  },
  {
    name: "Scenario B · Fire Hazard",
    text: "Electrical short circuit and fire outburst near Java Canteen! Building evacuation required!",
  },
  {
    name: "Scenario C · Non-Urgent",
    text: "Minor water pipe leak near Hostel Block 3. No injuries.",
  },
];

type DemoPanelProps = { apiUrl: string; onIncident: (incident: Incident) => void };

export default function DemoPanel({ apiUrl, onIncident }: DemoPanelProps) {
  const [pending, setPending] = useState("");
  const [error, setError] = useState("");

  async function triggerScenario(name: string, text: string) {
    setPending(name);
    setError("");
    try {
      const response = await fetch(`${apiUrl}/api/triage`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail ?? `Triage request failed (${response.status}).`);
      onIncident(result.incident as Incident);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to submit the demo scenario.");
    } finally {
      setPending("");
    }
  }

  return (
    <section className="demo-panel">
      <div className="section-heading">
        <h2>DEMO SIMULATOR</h2>
        <span>3 PRESETS</span>
      </div>
      <div className="scenario-list">
        {SCENARIOS.map((scenario) => (
          <button key={scenario.name} className="scenario-button" type="button" disabled={Boolean(pending)}
            onClick={() => void triggerScenario(scenario.name, scenario.text)}>
            <strong>{pending === scenario.name ? "Submitting…" : scenario.name}</strong>
            <span>{scenario.text}</span>
          </button>
        ))}
        {error && <div className="error-text" role="alert">{error}</div>}
      </div>
    </section>
  );
}
