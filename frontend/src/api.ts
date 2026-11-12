const API_BASE = import.meta.env.VITE_API_BASE ?? "/api/v1";
const API_KEY = import.meta.env.VITE_API_KEY ?? "demo-key";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) throw new Error((await res.text()) || res.statusText);
  return res.json() as Promise<T>;
}

export type ShipmentSummary = {
  id: string;
  reference: string;
  status: string;
  risk_level: string;
  route_label: string;
  current_stage: string;
  planned_eta: string;
  predicted_eta: string | null;
  delay_hours: number;
  cargo_description?: string;
  container_no?: string;
  documents_label: string;
  attention_title?: string | null;
  attention_detail?: string | null;
  data_quality: string;
};

export type Leg = {
  id: string;
  sequence: number;
  mode: string;
  label: string;
  origin_name?: string;
  destination_name?: string;
  distance_km?: number;
  planned_arrival: string;
  predicted_arrival: string | null;
  actual_arrival: string | null;
  stage_status_label: string;
  status: string;
};

export type ShipmentDetail = {
  id: string;
  reference: string;
  route_from: string;
  route_to: string;
  route_label: string;
  cargo_description: string;
  cargo_tonnes: number;
  container_no: string;
  equipment: string;
  cargo_line: string;
  current_stage: string;
  current_location: string;
  status: string;
  risk_level: string;
  planned_eta: string;
  predicted_eta: string | null;
  delay_hours: number;
  cost_rub: number;
  risk_headline: string | null;
  risk_detail: string | null;
  co2e_tonnes: number;
  documents_ready: number;
  documents_total: number;
  active_scenario: string;
  selected_alternative_id: string | null;
  missed_connection: boolean;
  legs: Leg[];
  timeline: Array<{ id: string; title: string; occurred_at: string }>;
  documents: {
    missing: string[];
    documents: Array<{ id: string; document_type: string; status: string }>;
    disclaimer: string;
  };
  schedule_disclaimer: string;
};

export type ShipmentWriteBody = {
  reference?: string;
  cargo_description?: string;
  cargo_tonnes?: number;
  container_no?: string;
  equipment?: string;
  route_from?: string;
  route_to?: string;
  origin_port_id?: string;
  destination_port_id?: string;
  current_stage?: string;
  current_location?: string;
  status?: string;
  risk_level?: string;
  planned_eta?: string;
  predicted_eta?: string;
  delay_hours?: number;
  cost_rub?: number;
  co2e_tonnes?: number;
  create_vessel?: boolean;
  vessel_name?: string;
  attention_title?: string | null;
  attention_detail?: string | null;
  risk_headline?: string | null;
  risk_detail?: string | null;
  missed_connection?: boolean;
  active_scenario?: string;
  legs?: Array<{
    id?: string;
    sequence?: number;
    mode?: string;
    label?: string;
    origin_name?: string;
    destination_name?: string;
    distance_km?: number;
    planned_departure?: string;
    planned_arrival?: string;
    predicted_departure?: string;
    predicted_arrival?: string;
    status?: string;
    stage_status_label?: string;
  }>;
};

export type ComparePayload = {
  title: string;
  subtitle: string;
  columns: Array<{
    shipment_id: string;
    reference: string;
    route_label: string;
    cargo: string;
    current_stage: string;
    predicted_eta: string | null;
    delay_hours: number;
    delay_label: string;
    risk_level: string;
    cost_rub: number;
    cost_label: string;
    co2e_tonnes: number;
    co2e_label: string;
    documents_label: string;
    documents_issues: number;
    legs_count: number;
    score: number;
    rank: number;
    score_breakdown: {
      time: number;
      risk: number;
      docs: number;
      cost: number;
      co2: number;
    };
  }>;
  metrics: Array<{ key: string; label: string; better: string | null }>;
  ranking: Array<{ shipment_id: string; reference: string; score: number; rank: number }>;
  insights: Array<{ code: string; title: string; detail: string }>;
  winner_id: string | null;
  disclaimer: string;
};

export type Alternative = {
  id: string;
  title: string;
  subtitle: string;
  feasible: boolean;
  is_current: boolean;
  recommended: boolean;
  eta_label: string | null;
  delay_label: string | null;
  duration_label: string | null;
  cost_label: string | null;
  transfers: number | null;
  co2e_label: string | null;
  constraints: string | null;
  availability: string | null;
  action_label: string | null;
  infeasible_reason: string | null;
};

export type Overview = {
  title: string;
  subtitle: string;
  refreshed_at: string;
  kpis: Record<string, number>;
  attention: Array<{
    shipment_id: string;
    reference: string;
    title: string;
    detail: string;
  }>;
  shipments: ShipmentSummary[];
  selected_map_reference: string;
  disclaimer: string;
};

export type DocumentsWorkspace = {
  shipment_id: string;
  reference: string;
  route_label: string;
  completeness_label: string;
  attention_label: string;
  can_submit_precheck: boolean;
  submit_hint: string | null;
  banner: { title: string; text: string };
  documents: Array<{
    id: string;
    document_type: string;
    title: string;
    status: string;
    status_label: string;
    status_tone: string;
    updated_label: string;
    action_label: string;
  }>;
  fixes: Array<{
    document_id: string;
    document_type?: string;
    title: string;
    field: string;
    placeholder: string | null;
    error: string | null;
  }>;
  history: Array<{
    document_id: string;
    document_title: string;
    status: string;
    note: string;
    changed_label: string;
    actor: string;
  }>;
  disclaimer: string;
};

export type AnalyticsDashboard = {
  title: string;
  subtitle: string;
  kpis: {
    shipments: number;
    delayed: number;
    at_risk: number;
    avg_delay_hours: number;
    co2e_tonnes: number;
    cost_rub: number;
  };
  model: {
    mae_hours: Record<string, number | null>;
    note: string;
    split: string;
  };
  shipments: ShipmentSummary[];
  disclaimer: string;
};

export type AppSettings = {
  display_timezone: string;
  locale: string;
  notifications_enabled: boolean;
  demo_mode: boolean;
  api_key_hint: string;
  default_scenario: string;
  co2_uncertainty_pct: number;
  operator_name: string;
  operator_role: string;
  disclaimer: string;
};

export type TrackingDashboard = {
  title: string;
  subtitle: string;
  refreshed_at: string;
  kpis: { vessels: number; underway: number; alerts: number; storm_alerts: number };
  vessels: Array<{
    id: string;
    name: string;
    mmsi: string;
    shipment_id: string | null;
    route_label: string;
    origin_port_id?: string;
    destination_port_id?: string;
    selected_alternative_id?: string | null;
    status: string;
    status_label: string;
    lat: number;
    lon: number;
    heading_deg: number;
    speed_knots: number;
    progress_pct: number;
    route_path?: Array<{ lat: number; lon: number }>;
    waypoints?: Array<{ lat: number; lon: number }>;
    storm_alternatives?: Array<{
      id: string;
      title: string;
      subtitle: string;
      path: Array<{ lat: number; lon: number }>;
      feasible: boolean;
      storm_safe: boolean;
      recommended?: boolean;
      eta_delta_hours: number;
      cost_delta_pct: number;
    }>;
    route_storm_danger?: boolean;
    map: { x: number; y: number };
    updated_label: string;
  }>;
  alerts: Array<{
    id: string;
    kind: string;
    severity: string;
    title: string;
    detail: string;
    wind_ms: number;
    valid_label: string;
    lat: number;
    lon: number;
    map: { x: number; y: number };
    affected_vessel_ids: string[];
    predicted: boolean;
  }>;
  ports: Array<{ id: string; name: string; lat: number; lon: number; map: { x: number; y: number } }>;
  corridors?: Array<{
    id: string;
    path: Array<{ lat: number; lon: number }>;
    waypoints?: Array<{ lat: number; lon: number }>;
  }>;
  storm_affected_vessel_ids?: string[];
  storm_cells?: Array<{
    id: string;
    name: string;
    lat: number;
    lon: number;
    wind_ms: number;
    severity: number;
    radius_km: number;
    kind: string;
    heading_deg: number;
    live: boolean;
  }>;
  disclaimer: string;
};

export const api = {
  overview: () => request<Overview>("/overview"),
  listShipments: () =>
    request<{ items: ShipmentSummary[]; data_quality: string }>("/shipments"),
  getShipment: (id: string) => request<ShipmentDetail>(`/shipments/${id}`),
  createShipment: (body: ShipmentWriteBody) =>
    request<ShipmentDetail>("/shipments", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  updateShipment: (id: string, body: ShipmentWriteBody) =>
    request<ShipmentDetail>(`/shipments/${id}`, {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  deleteShipment: (id: string) =>
    request<{ ok: boolean; deleted_id: string; reference: string }>(`/shipments/${id}`, {
      method: "DELETE",
    }),
  compareShipments: (ids: string[]) =>
    request<ComparePayload>(
      `/shipments/compare?ids=${ids.map(encodeURIComponent).join(",")}`
    ),
  simulate: (id: string, scenario: string) =>
    request<{ delay_hours: number; active_scenario: string; missed_connection: boolean }>(
      `/shipments/${id}/simulate`,
      { method: "POST", body: JSON.stringify({ scenario }) }
    ),
  alternatives: (id: string) =>
    request<{
      reference: string;
      route_label: string;
      insight: { title: string; detail: string };
      alternatives: Alternative[];
      footnote: string;
    }>(`/shipments/${id}/alternatives`),
  selectAlternative: (id: string, alternative_id: string) =>
    request(`/shipments/${id}/select-alternative`, {
      method: "POST",
      body: JSON.stringify({ alternative_id }),
    }),
  scenarios: () =>
    request<{ items: Record<string, { label: string }> }>("/scenarios"),
  predeclare: (shipment_id: string, document_type: string) =>
    request("/documents/predeclare", {
      method: "POST",
      body: JSON.stringify({ shipment_id, document_type, payload: { demo: true } }),
    }),
  addDocument: (body: {
    shipment_id: string;
    document_id?: string;
    document_type?: string;
    file_name?: string;
    hs_code?: string;
    mark_file_added?: boolean;
    mark_complete?: boolean;
  }) =>
    request<{ document_id: string; status: string }>("/documents/add", {
      method: "POST",
      body: JSON.stringify(body),
    }),
  documentsRegistry: () =>
    request<{
      items: Array<{
        shipment_id: string;
        reference: string;
        route_label: string;
        completeness_label: string;
        issues: number;
        attention: boolean;
      }>;
      default_shipment_id: string;
      disclaimer: string;
    }>("/documents/registry"),
  documentsWorkspace: (shipmentId: string) =>
    request<DocumentsWorkspace>(`/documents/workspace?shipment_id=${encodeURIComponent(shipmentId)}`),
  fixDocument: (
    documentId: string,
    body: { hs_code?: string; mark_file_added?: boolean; file_name?: string }
  ) =>
    request(`/documents/${documentId}/fix`, {
      method: "POST",
      body: JSON.stringify(body),
    }),
  precheck: (shipment_id: string) =>
    request<{ ok: boolean; message: string }>(`/documents/precheck`, {
      method: "POST",
      body: JSON.stringify({ shipment_id }),
    }),
  analytics: () => request<AnalyticsDashboard>("/analytics"),
  settings: () => request<AppSettings>("/settings"),
  updateSettings: (body: Partial<AppSettings>) =>
    request<AppSettings>("/settings", {
      method: "PATCH",
      body: JSON.stringify(body),
    }),
  notifications: () =>
    request<{
      items: Array<{
        id: string;
        shipment_id: string;
        reference: string;
        title: string;
        detail: string;
        kind: string;
        created_label: string;
      }>;
      unread: number;
      enabled: boolean;
      disclaimer: string;
    }>("/notifications"),
  documentHistory: (documentId: string) =>
    request<{
      document_id: string;
      history: Array<{
        id: string;
        status: string;
        note: string;
        changed_at: string;
        actor: string;
      }>;
      disclaimer: string;
    }>(`/documents/${documentId}/history`),
  tracking: () => request<TrackingDashboard>("/tracking"),
  trackingTick: () =>
    request<TrackingDashboard>("/tracking/tick", { method: "POST", body: "{}" }),
  selectVesselRoute: (vesselId: string, alternative_id: string) =>
    request<TrackingDashboard>(`/tracking/vessels/${encodeURIComponent(vesselId)}/select-route`, {
      method: "POST",
      body: JSON.stringify({ alternative_id }),
    }),
  assistantChat: (message: string, history?: Array<{ role: string; content: string }>) =>
    request<{
      ok: boolean;
      refused: boolean;
      reply: string;
      mode: string;
      as_of?: string;
      data_quality?: string;
    }>("/assistant/chat", {
      method: "POST",
      body: JSON.stringify({ message, history: history ?? [] }),
    }),
};
