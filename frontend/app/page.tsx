"use client";

import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { createClient, SupabaseClient } from "@supabase/supabase-js";
import DemoPanel from "@/components/DemoPanel";
import LiveFeed from "@/components/LiveFeed";
import IncidentDetailsModal from "@/components/IncidentDetailsModal";
import type { Incident, Responder } from "@/components/types";

const Map = dynamic(() => import("@/components/Map"), {
  ssr: false,
  loading: () => <div className="map-loading">Loading emergency map…</div>,
});

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

function playAlert() {
  const AudioContextConstructor = window.AudioContext;
  if (!AudioContextConstructor) return;
  const context = new AudioContextConstructor();
  const oscillator = context.createOscillator();
  const gain = context.createGain();
  oscillator.frequency.value = 660;
  gain.gain.setValueAtTime(0.035, context.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, context.currentTime + 0.28);
  oscillator.connect(gain);
  gain.connect(context.destination);
  oscillator.start();
  oscillator.stop(context.currentTime + 0.28);
  oscillator.onended = () => void context.close();
}

export default function Home() {
  const [responders, setResponders] = useState<Responder[]>([]);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [offlineMode, setOfflineMode] = useState(false);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [feedError, setFeedError] = useState("");
  const hasLoadedRef = useRef(false);
  const lastIncidentIdsRef = useRef(new Set<string>());
  const supabase = useMemo<SupabaseClient | null>(() => {
    const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
    const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
    return url && key ? createClient(url, key) : null;
  }, []);

  const refreshDashboard = useCallback(async () => {
    try {
      const [responderResponse, incidentResponse] = await Promise.all([
        fetch(`${API_URL}/api/responders`),
        fetch(`${API_URL}/api/incidents`),
      ]);
      if (!responderResponse.ok || !incidentResponse.ok) {
        throw new Error(`Dashboard API returned ${responderResponse.status}/${incidentResponse.status}.`);
      }
      const [nextResponders, nextIncidents] = await Promise.all([
        responderResponse.json() as Promise<Responder[]>,
        incidentResponse.json() as Promise<Incident[]>,
      ]);
      setResponders(nextResponders);
      if (
        hasLoadedRef.current &&
        nextIncidents.some((incident) => !lastIncidentIdsRef.current.has(incident.id))
      ) {
        playAlert();
      }
      lastIncidentIdsRef.current = new Set(nextIncidents.map((incident) => incident.id));
      setIncidents(nextIncidents);
      hasLoadedRef.current = true;
      setFeedError("");
    } catch (error) {
      setFeedError(error instanceof Error ? error.message : "Unable to load dashboard data.");
    }
  }, []);

  useEffect(() => {
    void refreshDashboard();
    const pollingId = window.setInterval(() => void refreshDashboard(), 5000);
    return () => window.clearInterval(pollingId);
  }, [refreshDashboard]);

  useEffect(() => {
    if (!supabase) return;
    const channel = supabase
      .channel("openrelief-incidents")
      .on("postgres_changes", { event: "INSERT", schema: "public", table: "incidents" }, (payload) => {
        const row = payload.new as Partial<Incident>;
        if (!row.id) return;
        lastIncidentIdsRef.current.add(row.id);
        void refreshDashboard();
        playAlert();
      })
      .subscribe((status) => {
        if (status === "CHANNEL_ERROR" || status === "TIMED_OUT") {
          setFeedError("Supabase realtime connection failed; reload to retry.");
        }
      });
    return () => {
      void supabase.removeChannel(channel);
    };
  }, [refreshDashboard, supabase]);

  const handleNewIncident = useCallback((incident: Incident) => {
    lastIncidentIdsRef.current.add(incident.id);
    setIncidents((current) => [incident, ...current.filter((item) => item.id !== incident.id)]);
    if (incident.assigned_responder_id) {
      setResponders((current) => current.map((responder) =>
        responder.id === incident.assigned_responder_id ? { ...responder, is_available: false } : responder,
      ));
    }
    setSelectedIncident(incident);
  }, []);

  const handleStatusUpdate = useCallback((incidentId: string) => {
    const assignedResponderId = selectedIncident?.assigned_responder_id;
    lastIncidentIdsRef.current.delete(incidentId);
    setIncidents((current) => current.filter((incident) => incident.id !== incidentId));
    setResponders((current) => current.map((responder) =>
      responder.id === assignedResponderId
        ? { ...responder, is_available: true }
        : responder,
    ));
    void refreshDashboard();
    setSelectedIncident(null);
  }, [refreshDashboard, selectedIncident?.assigned_responder_id]);

  return (
    <main className="dashboard-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark">OR</span>
          <div>
            <strong>OpenRelief</strong>
            <span>EMERGENCY COMMAND</span>
          </div>
        </div>
        <div className="command-status"><span className="status-dot" /> COMMAND ACTIVE</div>
        <label className="offline-toggle">
          <span>Local offline mode</span>
          <input
            type="checkbox"
            checked={offlineMode}
            onChange={(event) => setOfflineMode(event.target.checked)}
            aria-label="Toggle local offline mode"
          />
          <span className="toggle-track" />
        </label>
      </header>
      {feedError && <div className="system-notice" role="status">{feedError}</div>}
      {!supabase && <div className="system-notice">Supabase realtime is not configured; live incidents refresh every 5 seconds.</div>}
      <div className="dashboard-grid">
        <aside className="sidebar">
          <DemoPanel apiUrl={API_URL} onIncident={handleNewIncident} />
          <LiveFeed incidents={incidents} onSelect={setSelectedIncident} />
        </aside>
        <section className="map-panel" aria-label="Emergency response map">
          <div className="map-toolbar">
            <div><span className="map-pulse" /> KATTANKULATHUR RESPONSE ZONE</div>
            <span>{offlineMode ? "OFFLINE MAP" : "LIVE MAP"} · SRMIST CAMPUS</span>
          </div>
          <Map incidents={incidents} responders={responders} offlineMode={offlineMode} />
          <div className="map-legend">
            <span><i className="legend-responder" /> Responders</span>
            <span><i className="legend-incident" /> Active incident</span>
            <span><i className="legend-route" /> Dispatch route</span>
          </div>
        </section>
      </div>
      {selectedIncident && (
        <IncidentDetailsModal
          incident={selectedIncident}
          apiUrl={API_URL}
          onClose={() => setSelectedIncident(null)}
          onStatusUpdate={handleStatusUpdate}
        />
      )}
    </main>
  );
}
