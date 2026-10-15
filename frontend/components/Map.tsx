"use client";

import L from "leaflet";
import { MapContainer, Marker, Polyline, TileLayer, Tooltip } from "react-leaflet";
import type { Incident, Responder } from "./types";

type MapProps = {
  incidents: Incident[];
  responders: Responder[];
  offlineMode: boolean;
};

const responderIcon = L.divIcon({
  className: "",
  html: '<div class="responder-marker"></div>',
  iconSize: [28, 28],
  iconAnchor: [14, 26],
});

function incidentIcon(urgency: number) {
  const size = urgency >= 5 ? 34 : urgency === 4 ? 30 : 24;
  return L.divIcon({
    className: "",
    html: `<div class="incident-marker urgency-${urgency}"></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
  });
}

function getOfflinePosition(latitude: number, longitude: number) {
  const x = Math.min(95, Math.max(5, 50 + (longitude - 80.0444) * 3200));
  const y = Math.min(95, Math.max(5, 50 - (latitude - 12.8231) * 3200));
  return { left: `${x}%`, top: `${y}%`, x, y };
}

export default function Map({ incidents, responders, offlineMode }: MapProps) {
  if (offlineMode) {
    return (
      <div className="map-container">
        <div className="offline-map">
          <span className="offline-label">SRMIST · LOCAL OFFLINE GRID</span>
          <svg className="offline-route" aria-hidden="true">
            {incidents.map((incident) => {
              const responder = incident.assigned_responder;
              if (!responder) return null;
              const start = getOfflinePosition(incident.latitude, incident.longitude);
              const end = getOfflinePosition(responder.latitude, responder.longitude);
              return (
                <line key={`${incident.id}-route`} x1={start.left} y1={start.top} x2={end.left} y2={end.top}
                  stroke="#e14e4e" strokeWidth="2" strokeDasharray="7 5" />
              );
            })}
          </svg>
          {responders.map((responder) => {
            const position = getOfflinePosition(responder.latitude, responder.longitude);
            return <div key={responder.id} className="offline-marker responder-marker"
              style={{ left: position.left, top: position.top }} title={responder.unit_name} />;
          })}
          {incidents.map((incident) => {
            const position = getOfflinePosition(incident.latitude, incident.longitude);
            return (
              <div key={incident.id} className={`offline-marker incident-marker urgency-${incident.urgency_rating}`}
                style={{ left: position.left, top: position.top }}
                title={`${incident.incident_type}, urgency ${incident.urgency_rating}`} />
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div className="map-container">
      <MapContainer center={[12.8231, 80.0444]} zoom={14} scrollWheelZoom>
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        {responders.map((responder) => (
          <Marker key={responder.id} position={[responder.latitude, responder.longitude]} icon={responderIcon}>
            <Tooltip>{responder.unit_name} · {responder.is_available === false ? "Assigned" : "Available"}</Tooltip>
          </Marker>
        ))}
        {incidents.map((incident) => (
          <Marker key={incident.id} position={[incident.latitude, incident.longitude]} icon={incidentIcon(incident.urgency_rating)}>
            <Tooltip>{incident.incident_type} · urgency {incident.urgency_rating}</Tooltip>
          </Marker>
        ))}
        {incidents.map((incident) => (
          incident.assigned_responder ? (
            <Polyline key={`${incident.id}-route`}
              positions={[
                [incident.latitude, incident.longitude],
                [incident.assigned_responder.latitude, incident.assigned_responder.longitude],
              ]}
              pathOptions={{ color: "#e14e4e", weight: 3, dashArray: "8 8", opacity: 0.85 }}
            />
          ) : null
        ))}
      </MapContainer>
    </div>
  );
}
