export type Responder = {
  id: string;
  unit_name: string;
  unit_type: string;
  is_available?: boolean;
  latitude: number;
  longitude: number;
};

export type Incident = {
  id: string;
  transcript: string;
  incident_type: string;
  urgency_rating: number;
  casualty_count: number;
  priority_score: number;
  cap_severity: string;
  status: string;
  created_at?: string;
  latitude: number;
  longitude: number;
  assigned_responder_id?: string | null;
  assigned_responder?: (Responder & { distance_km?: number }) | null;
};
