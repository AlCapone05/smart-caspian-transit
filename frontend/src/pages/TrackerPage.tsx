import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api";
import { Layout } from "../components/Layout";
import { fmtMsk, tzShort } from "../format";

type Vessel = {
  id: string;
  name: string;
  mmsi: string;
  shipment_id: string | null;
  route_label: string;
  status: string;
  status_label: string;
  lat: number;
  lon: number;
  heading_deg: number;
  speed_knots: number;
  progress_pct: number;
  map: { x: number; y: number };
  updated_label: string;
};

type Alert = {
  id: string;
  kind: string;
  severity: string;
  title: string;
  detail: string;
  wind_ms: number;
  valid_label: string;
  map: { x: number; y: number };
  affected_vessel_ids: string[];
  predicted: boolean;
};

type PortMark = {
  id: string;
  name: string;
  map: { x: number; y: number };
};

type Tracking = {
  title: string;
  subtitle: string;
  refreshed_at: string;
  kpis: { vessels: number; underway: number; alerts: number; storm_alerts: number };
  vessels: Vessel[];
  alerts: Alert[];
  ports: PortMark[];
  disclaimer: string;
};

export function TrackerPage() {
  const [data, setData] = useState<Tracking | null>(null);
  const [selected, setSelected] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [live, setLive] = useState(true);
  const navigate = useNavigate();

  const load = async (tick = false) => {
    const d = tick ? await api.trackingTick() : await api.tracking();
    setData(d);
    if (!selected && d.vessels[0]) setSelected(d.vessels[0].id);
  };

  useEffect(() => {
    load(false).catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    if (!live) return;
    const id = window.setInterval(() => {
      load(true).catch(() => undefined);
    }, 4000);
    return () => window.clearInterval(id);
  }, [live, selected]);

  if (!data && !error) {
    return (
      <Layout title="GPS-трекер">
        <p className="muted">Загрузка позиций…</p>
      </Layout>
    );
  }

  if (!data) {
    return (
      <Layout title="GPS-трекер">
        <p className="error">{error}</p>
      </Layout>
    );
  }

  const active = data.vessels.find((v) => v.id === selected) ?? data.vessels[0];
  const vesselAlerts = data.alerts.filter((a) =>
    active ? a.affected_vessel_ids.includes(active.id) : true
  );

  return (
    <Layout title="GPS-трекер">
      <div className="docs-header-row">
        <div>
          <h1 className="page-title">{data.title}</h1>
          <p className="page-sub">
            {data.subtitle} · обновлено {fmtMsk(data.refreshed_at)} {tzShort()}
          </p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button
            type="button"
            className={`btn ${live ? "selected" : "ghost"}`}
            onClick={() => setLive((v) => !v)}
          >
            {live ? "● Live" : "○ Live выкл"}
          </button>
          <button type="button" className="btn ghost" onClick={() => load(true)}>
            Обновить GPS
          </button>
        </div>
      </div>

      <div className="kpi-row">
        <div>
          <p className="kpi-label">Суда на карте</p>
          <p className="kpi-value">{data.kpis.vessels}</p>
        </div>
        <div>
          <p className="kpi-label">В пути</p>
          <p className="kpi-value">{data.kpis.underway}</p>
        </div>
        <div>
          <p className="kpi-label">Погодные алерты</p>
          <p className="kpi-value">{data.kpis.alerts}</p>
        </div>
        <div>
          <p className="kpi-label">Штормовые</p>
          <p className="kpi-value delay-amber">{data.kpis.storm_alerts}</p>
        </div>
      </div>

      <div className="grid-map tracker-grid">
        <section className="card">
          <div className="map-head">
            <h3>Каспий · live GPS</h3>
            <span className="map-selected">
              {active ? `◉ ${active.name}` : "Нет судна"}
            </span>
          </div>
          <div className="caspian-map tracker-map">
            <svg viewBox="0 0 696 280" role="img" aria-label="GPS карта судов">
              <ellipse cx="330" cy="150" rx="120" ry="95" fill="#c5dbe3" opacity="0.9" />
              <path
                d="M250 40 C 220 90, 230 160, 255 230 C 290 255, 360 250, 400 210 C 430 160, 420 80, 380 45 C 340 25, 280 20, 250 40 Z"
                fill="#b7d0db"
                stroke="#8fb0bf"
                strokeWidth="1"
              />
              {data.ports.map((p) => (
                <g key={p.id}>
                  <circle cx={p.map.x} cy={p.map.y} r="4" fill="#687585" />
                  <text
                    x={p.map.x + 8}
                    y={p.map.y + 4}
                    fill="#687585"
                    fontSize="11"
                    fontFamily="Inter,sans-serif"
                  >
                    {p.name.replace(" (демо)", "")}
                  </text>
                </g>
              ))}
              {data.alerts
                .filter((a) => a.severity === "high")
                .map((a) => (
                  <circle
                    key={`wx-${a.id}`}
                    cx={a.map.x}
                    cy={a.map.y}
                    r="22"
                    fill="#f0b429"
                    opacity="0.22"
                  />
                ))}
              {data.vessels.map((v) => (
                <g
                  key={v.id}
                  style={{ cursor: "pointer" }}
                  onClick={() => setSelected(v.id)}
                >
                  <circle
                    cx={v.map.x}
                    cy={v.map.y}
                    r={v.id === active?.id ? 9 : 6}
                    fill={v.status === "underway" ? "#087f83" : "#687585"}
                    stroke={v.id === active?.id ? "#17212b" : "none"}
                    strokeWidth="2"
                  />
                  <polygon
                    points="0,-10 6,8 -6,8"
                    fill="#245b78"
                    transform={`translate(${v.map.x}, ${v.map.y}) rotate(${v.heading_deg})`}
                    opacity="0.85"
                  />
                  <text
                    x={v.map.x + 12}
                    y={v.map.y - 8}
                    fill="#17212b"
                    fontSize="12"
                    fontFamily="Inter,sans-serif"
                    fontWeight="600"
                  >
                    {v.name}
                  </text>
                </g>
              ))}
            </svg>
          </div>
          <p className="map-note">
            Схема с проекцией lat/lon · не для навигации · желтые зоны — прогноз шторма
          </p>
        </section>

        <section className="card attention-card">
          <h3>Погодные оповещения</h3>
          {data.alerts.length === 0 && <p className="muted">Активных предупреждений нет.</p>}
          {data.alerts.map((a) => (
            <div
              key={a.id}
              className={`attention-item ${a.severity === "high" ? "attention-hot" : ""}`}
              style={{ marginBottom: 10 }}
            >
              <h4>
                {a.severity === "high" ? "△ " : ""}
                {a.title}
              </h4>
              <p>{a.detail}</p>
              <p className="muted" style={{ marginTop: 6, fontSize: 13 }}>
                {a.kind} · {a.wind_ms.toFixed(0)} м/с · {a.valid_label}
                {a.predicted ? " · прогноз" : ""}
              </p>
            </div>
          ))}
        </section>
      </div>

      <div className="detail-grid">
        <section className="card">
          <h3 style={{ marginTop: 0 }}>Суда</h3>
          <table className="shipment-table">
            <thead>
              <tr>
                <th>Судно</th>
                <th>Маршрут</th>
                <th>GPS</th>
                <th>Скорость</th>
                <th>Путь</th>
                <th>Статус</th>
              </tr>
            </thead>
            <tbody>
              {data.vessels.map((v) => (
                <tr
                  key={v.id}
                  className={v.id === active?.id ? "active" : ""}
                  onClick={() => setSelected(v.id)}
                >
                  <td>
                    {v.name}
                    <div className="muted" style={{ fontSize: 12 }}>
                      MMSI {v.mmsi}
                    </div>
                  </td>
                  <td>{v.route_label}</td>
                  <td>
                    {v.lat.toFixed(3)}, {v.lon.toFixed(3)}
                  </td>
                  <td>{v.speed_knots} kn</td>
                  <td>{v.progress_pct}%</td>
                  <td>{v.status_label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section className="card">
          <h3 style={{ marginTop: 0 }}>{active?.name ?? "Судно"}</h3>
          {active && (
            <>
              <p className="muted">{active.route_label}</p>
              <p>
                GPS: <strong>{active.lat.toFixed(4)}°N, {active.lon.toFixed(4)}°E</strong>
              </p>
              <p>
                Курс {active.heading_deg.toFixed(0)}° · {active.speed_knots} kn · путь{" "}
                {active.progress_pct}%
              </p>
              <p className="muted">Обновлено {active.updated_label}</p>
              {active.shipment_id && (
                <button
                  type="button"
                  className="btn"
                  style={{ marginTop: 12 }}
                  onClick={() => navigate(`/shipments/${active.shipment_id}`)}
                >
                  Открыть перевозку
                </button>
              )}
              <h4 style={{ marginTop: 20 }}>Алерты по судну</h4>
              {vesselAlerts.length === 0 && <p className="muted">Нет локальных алертов.</p>}
              {vesselAlerts.map((a) => (
                <p key={a.id} className={a.severity === "high" ? "delay-amber" : "muted"}>
                  {a.title}
                </p>
              ))}
              <p style={{ marginTop: 16 }}>
                <Link to="/shipments/shp_sct_2048">Симулятор шторма на SCT-2048 →</Link>
              </p>
            </>
          )}
        </section>
      </div>

      <p className="footer-note">{data.disclaimer}</p>
    </Layout>
  );
}
