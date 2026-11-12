import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type Overview, type TrackingDashboard } from "../api";
import { LiveCaspianMap } from "../components/LiveCaspianMap";
import { Layout } from "../components/Layout";
import { delayLabel, fmtMsk, tzShort } from "../format";
type StatusFilter = "all" | "at_risk" | "delayed" | "docs" | "ok";

const STATUS_OPTIONS: Array<{ id: StatusFilter; label: string }> = [
  { id: "all", label: "Все статусы" },
  { id: "at_risk", label: "Под риском" },
  { id: "delayed", label: "Задержаны" },
  { id: "docs", label: "Ждут документы" },
  { id: "ok", label: "Без отклонений" },
];

export function OverviewPage() {
  const [data, setData] = useState<Overview | null>(null);
  const [track, setTrack] = useState<TrackingDashboard | null>(null);
  const [selectedVessel, setSelectedVessel] = useState<string | null>(null);
  const [mapNote, setMapNote] = useState<string | null>(null);
  const [previewAlt, setPreviewAlt] = useState<string | null>(null);
  const [routeBusy, setRouteBusy] = useState(false);
  const [search, setSearch] = useState("");
  const [attentionOnly, setAttentionOnly] = useState(false);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  const [statusOpen, setStatusOpen] = useState(false);
  const [live, setLive] = useState(true);
  const [mapOpen, setMapOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    if (!mapOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setMapOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [mapOpen]);

  const loadTrack = async (tick = false) => {
    const d = tick ? await api.trackingTick() : await api.tracking();
    setTrack(d);
    setSelectedVessel((prev) => prev ?? d.vessels[0]?.id ?? null);
  };

  useEffect(() => {
    api.overview().then(setData).catch((e: Error) => setError(e.message));
    loadTrack(false).catch(() => undefined);
  }, []);

  // Синхронизация с мобильным клиентом / ботом (общая API-база)
  useEffect(() => {
    const id = window.setInterval(() => {
      api.overview().then(setData).catch(() => undefined);
    }, 5000);
    return () => window.clearInterval(id);
  }, []);

  useEffect(() => {
    if (!live) return;
    const id = window.setInterval(() => {
      loadTrack(true).catch(() => undefined);
    }, 2500);
    return () => window.clearInterval(id);
  }, [live]);

  const rows = useMemo(() => {
    if (!data) return [];
    // На обзоре — активные; завершённые живут во вкладке «Перевозки → Завершённые»
    const done = new Set(["delivered", "completed", "cancelled"]);
    let list = data.shipments.filter((s) => !done.has(s.status));
    if (search.trim()) {
      const q = search.trim().toLowerCase();
      list = list.filter((s) => {
        const hay = [
          s.reference,
          s.route_label,
          s.current_stage,
          s.cargo_description || "",
          s.container_no || "",
          s.documents_label || "",
          s.risk_level || "",
          s.status || "",
        ]
          .join(" ")
          .toLowerCase();
        return hay.includes(q);
      });
    }
    if (attentionOnly) {
      list = list.filter(
        (s) => s.risk_level !== "low" || s.delay_hours > 0 || s.documents_label.includes("△")
      );
    }
    if (statusFilter === "at_risk") {
      list = list.filter((s) => s.risk_level === "high" || s.risk_level === "medium");
    } else if (statusFilter === "delayed") {
      list = list.filter((s) => s.delay_hours > 0);
    } else if (statusFilter === "docs") {
      list = list.filter((s) => s.documents_label.includes("△"));
    } else if (statusFilter === "ok") {
      list = list.filter(
        (s) => s.risk_level === "low" && s.delay_hours <= 0 && !s.documents_label.includes("△")
      );
    }
    return list;
  }, [data, search, attentionOnly, statusFilter]);

  if (!data && !error) {
    return (
      <Layout title="Обзор">
        <p className="muted">Загрузка…</p>
      </Layout>
    );
  }

  if (!data) {
    return (
      <Layout title="Обзор">
        <p className="error">{error}</p>
      </Layout>
    );
  }

  const primary = data.attention[0];
  const statusLabel = STATUS_OPTIONS.find((o) => o.id === statusFilter)?.label ?? "Все статусы";
  const activeVessel = track?.vessels.find((v) => v.id === selectedVessel) ?? track?.vessels[0];
  const weatherAlerts = track?.alerts.slice(0, 4) ?? [];
  const stormHit = Boolean(
    activeVessel &&
      (track?.storm_affected_vessel_ids?.includes(activeVessel.id) ||
        activeVessel.route_storm_danger ||
        activeVessel.storm_alternatives?.some(
          (a) =>
            (a.id === (activeVessel.selected_alternative_id || "alt_current")) &&
            !a.storm_safe
        ))
  );
  const stormAlts = [...(activeVessel?.storm_alternatives ?? [])].sort((a, b) => {
    if (a.recommended !== b.recommended) return a.recommended ? -1 : 1;
    if (a.storm_safe !== b.storm_safe) return a.storm_safe ? -1 : 1;
    return (a.eta_delta_hours ?? 0) - (b.eta_delta_hours ?? 0);
  });
  const recommendedAlt = stormAlts.find(
    (a) =>
      a.recommended &&
      a.feasible &&
      a.id !== (activeVessel?.selected_alternative_id || "alt_current")
  );
  const previewPath =
    activeVessel?.storm_alternatives?.find((a) => a.id === previewAlt)?.path ?? null;

  const applyStormRoute = async (alternativeId: string) => {
    if (!activeVessel) return;
    setRouteBusy(true);
    setError(null);
    try {
      const d = await api.selectVesselRoute(activeVessel.id, alternativeId);
      setTrack(d);
      setPreviewAlt(null);
      const title =
        activeVessel.storm_alternatives?.find((a) => a.id === alternativeId)?.title ??
        alternativeId;
      setMapNote(`Маршрут сменён на «${title}» · ${activeVessel.name}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRouteBusy(false);
    }
  };

  return (
    <>
    <Layout title="Обзор" search={search} onSearch={setSearch}>
      <h1 className="page-title">{data.title}</h1>
      <p className="page-sub">
        {data.subtitle}
        {track
          ? ` · GPS live · ${track.kpis.underway} судов в пути · штормы ~2–3 мин`
          : " · оперативный контроль коридора"}
      </p>

      <div className="kpi-row">
        <div>
          <p className="kpi-label">Активные перевозки</p>
          <p className="kpi-value">{data.kpis.active}</p>
        </div>
        <div>
          <p className="kpi-label">△ Под риском</p>
          <p className="kpi-value">{data.kpis.at_risk}</p>
        </div>
        <div>
          <p className="kpi-label">! Задержаны</p>
          <p className="kpi-value">{data.kpis.delayed}</p>
        </div>
        <div>
          <p className="kpi-label">Ожидают документов</p>
          <p className="kpi-value">{data.kpis.awaiting_docs}</p>
        </div>
      </div>

      <div className="grid-map">
        <section className="card map-card-compact">
          <div className="map-head">
            <h3>Каспийский коридор · GPS</h3>
            <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
              <button
                type="button"
                className={`btn ghost ${live ? "selected" : ""}`}
                onClick={() => setLive((v) => !v)}
                style={{ padding: "6px 10px", minHeight: 0 }}
              >
                {live ? "● Live" : "○ Live"}
              </button>
              <button
                type="button"
                className="btn"
                style={{ padding: "6px 12px", minHeight: 0 }}
                onClick={() => setMapOpen(true)}
              >
                Открыть карту
              </button>
            </div>
          </div>
          <LiveCaspianMap
            variant="compact"
            showLegend={false}
            vessels={track?.vessels ?? []}
            alerts={track?.alerts ?? []}
            stormCells={track?.storm_cells ?? []}
            ports={track?.ports ?? []}
            corridors={track?.corridors ?? []}
            selectedId={selectedVessel}
            previewPath={previewPath}
            onSelect={(id) => {
              setSelectedVessel(id);
              setPreviewAlt(null);
              const v = track?.vessels.find((x) => x.id === id);
              setMapNote(v ? `Судно: ${v.name} · ${v.route_label}` : null);
            }}
            onPortSelect={(_id, name) => setMapNote(`Город: ${name}`)}
            onAlertSelect={(id) => {
              const a = track?.alerts.find((x) => x.id === id);
              setMapNote(a ? `Шторм: ${a.title}` : null);
            }}
          />
          {mapNote && (
            <p className="map-selected" style={{ marginTop: 8 }}>
              {mapNote}
            </p>
          )}
          {activeVessel && (
            <div className="vessel-chip">
              <strong>{activeVessel.name}</strong>
              <span>
                {activeVessel.lat.toFixed(2)}°N {activeVessel.lon.toFixed(2)}°E ·{" "}
                {activeVessel.speed_knots} kn · {activeVessel.progress_pct}%
              </span>
              {activeVessel.shipment_id && (
                <button
                  type="button"
                  className="btn ghost"
                  style={{ padding: "4px 10px", minHeight: 0 }}
                  onClick={() => navigate(`/shipments/${activeVessel.shipment_id}`)}
                >
                  Груз →
                </button>
              )}
            </div>
          )}

          {activeVessel && (stormHit || stormAlts.length > 1) && (
            <div className={`storm-route-panel ${stormHit ? "hot" : ""}`}>
              <div className="storm-route-head">
                <h4 style={{ margin: 0 }}>
                  {stormHit
                    ? "△ Опасность на маршруте — смените путь"
                    : "Альтернативные морские пути"}
                </h4>
                <p className="muted" style={{ margin: "4px 0 0", fontSize: 13 }}>
                  {activeVessel.name} · {activeVessel.route_label}
                </p>
                {stormHit && recommendedAlt && (
                  <button
                    type="button"
                    className="btn"
                    style={{ marginTop: 10, padding: "8px 14px", minHeight: 0 }}
                    disabled={routeBusy}
                    onClick={() => applyStormRoute(recommendedAlt.id)}
                  >
                    Перейти на безопасный: {recommendedAlt.title}
                  </button>
                )}
              </div>
              <div className="storm-route-list">
                {stormAlts.map((alt) => {
                  const selected =
                    (activeVessel.selected_alternative_id || "alt_current") === alt.id;
                  const canSelect = !selected && alt.feasible !== false;
                  return (
                    <div
                      key={alt.id}
                      className={`storm-route-item ${selected ? "on" : ""} ${
                        previewAlt === alt.id ? "preview" : ""
                      } ${alt.recommended && stormHit ? "recommended" : ""}`}
                    >
                      <div>
                        <strong>
                          {alt.title}
                          {alt.recommended ? " · рекомендуем" : ""}
                        </strong>
                        <p>
                          {alt.subtitle}
                          {alt.storm_safe ? " · безопаснее" : " · опасность"}
                          {alt.eta_delta_hours
                            ? ` · ETA ${alt.eta_delta_hours > 0 ? "+" : ""}${alt.eta_delta_hours} ч`
                            : ""}
                          {alt.cost_delta_pct ? ` · +${alt.cost_delta_pct}% ₽` : ""}
                        </p>
                      </div>
                      <div className="storm-route-actions">
                        <button
                          type="button"
                          className="btn ghost"
                          style={{ padding: "4px 10px", minHeight: 0 }}
                          onClick={() => {
                            setPreviewAlt(alt.id);
                            setMapOpen(true);
                          }}
                        >
                          На карте
                        </button>
                        <button
                          type="button"
                          className={`btn ${alt.recommended && canSelect ? "" : "ghost"}`}
                          style={{ padding: "4px 10px", minHeight: 0 }}
                          disabled={routeBusy || !canSelect}
                          onClick={() => applyStormRoute(alt.id)}
                        >
                          {selected ? "Активен" : "Выбрать"}
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </section>

        <section className="card attention-card">
          <h3>Требуют внимания</h3>
          {primary && (
            <div className="attention-hot">
              <h4>{primary.title}</h4>
              <p>{primary.detail}</p>
              <button
                type="button"
                className="btn ghost"
                style={{ marginTop: 12, width: "100%" }}
                onClick={() => navigate(`/shipments/${primary.shipment_id}`)}
              >
                Разобрать риск →
              </button>
            </div>
          )}
          {data.attention.slice(1).map((a) => (
            <div
              className="attention-item"
              key={a.shipment_id}
              onClick={() => navigate(`/shipments/${a.shipment_id}`)}
              style={{ cursor: "pointer" }}
            >
              <h4>{a.title}</h4>
              <p>{a.detail}</p>
            </div>
          ))}

          {weatherAlerts.length > 0 && (
            <>
              <h3 style={{ marginTop: 20 }}>Погода · live</h3>
              {(track?.storm_cells ?? []).slice(0, 4).map((c) => (
                <div
                  key={c.id}
                  className={`attention-item ${c.severity >= 0.72 ? "attention-hot" : ""}`}
                >
                  <h4>
                    {c.severity >= 0.72 ? "△ " : ""}
                    {c.name}
                  </h4>
                  <p>
                    Ветер {c.wind_ms.toFixed(0)} м/с · радиус ~{c.radius_km.toFixed(0)} км · дрейф{" "}
                    {c.heading_deg.toFixed(0)}°
                  </p>
                  <p className="muted" style={{ fontSize: 12, marginTop: 4 }}>
                    {c.lat.toFixed(2)}°N {c.lon.toFixed(2)}°E · обновляется с Live
                  </p>
                </div>
              ))}
              {(!track?.storm_cells || track.storm_cells.length === 0) &&
                weatherAlerts.map((a) => (
                  <div
                    key={a.id}
                    className={`attention-item ${a.severity === "high" ? "attention-hot" : ""}`}
                  >
                    <h4>
                      {a.severity === "high" ? "△ " : ""}
                      {a.title}
                    </h4>
                    <p>{a.detail}</p>
                  </div>
                ))}
            </>
          )}
        </section>
      </div>

      <section className="card table-card">
        <div className="table-toolbar">
          <h3 style={{ margin: 0, flex: 1 }}>Перевозки</h3>
          <input
            className="search"
            style={{ width: 310 }}
            placeholder="SCT, контейнер, маршрут, груз…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
          <div className="status-filter-wrap">
            <button
              type="button"
              className={`btn ghost ${statusOpen ? "selected" : ""}`}
              onClick={() => setStatusOpen((v) => !v)}
            >
              {statusLabel} ⌄
            </button>
            {statusOpen && (
              <div className="status-menu">
                {STATUS_OPTIONS.map((o) => (
                  <button
                    key={o.id}
                    type="button"
                    className={o.id === statusFilter ? "active" : ""}
                    onClick={() => {
                      setStatusFilter(o.id);
                      setStatusOpen(false);
                      if (o.id !== "all") setAttentionOnly(false);
                    }}
                  >
                    {o.label}
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            type="button"
            className={`btn ${attentionOnly ? "selected" : "ghost"}`}
            onClick={() => {
              setAttentionOnly((v) => !v);
              setStatusFilter("all");
            }}
          >
            Требуют внимания
          </button>
        </div>
        <table className="shipment-table">
          <thead>
            <tr>
              <th style={{ width: 120 }}>Груз</th>
              <th style={{ width: 235 }}>Маршрут</th>
              <th style={{ width: 210 }}>Текущий этап</th>
              <th style={{ width: 200 }}>Прогноз · {tzShort()}</th>
              <th style={{ width: 120 }}>К плану</th>
              <th style={{ width: 170 }}>Документы</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((s) => (
              <tr
                key={s.id}
                className={s.reference === data.selected_map_reference ? "active" : ""}
                onClick={() => navigate(`/shipments/${s.id}`)}
              >
                <td>{s.reference}</td>
                <td>{s.route_label}</td>
                <td>{s.current_stage}</td>
                <td>{fmtMsk(s.predicted_eta)}</td>
                <td className={s.delay_hours >= 12 ? "delay-amber" : s.delay_hours > 0 ? "delay-red" : ""}>
                  {delayLabel(s.delay_hours)}
                </td>
                <td>{s.documents_label}</td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr>
                <td colSpan={6} className="muted">
                  Нет перевозок по выбранному фильтру
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </section>

      <p className="footer-note">{data.disclaimer}</p>
      {track && <p className="footer-note">{track.disclaimer}</p>}

    </Layout>
      {mapOpen && (
        <div
          className="modal-backdrop map-modal-backdrop"
          onClick={() => setMapOpen(false)}
        >
          <div
            className="map-modal-card"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="map-head" style={{ marginBottom: 12 }}>
              <div>
                <h3 style={{ margin: 0 }}>Каспийский коридор · карта</h3>
                <p className="muted" style={{ margin: "4px 0 0", fontSize: 13 }}>
                  ◉ {activeVessel?.name ?? data.selected_map_reference}
                  {live ? " · Live" : ""}
                </p>
              </div>
              <div style={{ display: "flex", gap: 8 }}>
                <button
                  type="button"
                  className={`btn ghost ${live ? "selected" : ""}`}
                  onClick={() => setLive((v) => !v)}
                  style={{ padding: "6px 10px", minHeight: 0 }}
                >
                  {live ? "● Live" : "○ Live"}
                </button>
                <button
                  type="button"
                  className="btn ghost"
                  style={{ padding: "6px 10px", minHeight: 0 }}
                  onClick={() => setMapOpen(false)}
                >
                  Закрыть
                </button>
              </div>
            </div>
            <LiveCaspianMap
              variant="expanded"
              vessels={track?.vessels ?? []}
              alerts={track?.alerts ?? []}
              stormCells={track?.storm_cells ?? []}
              ports={track?.ports ?? []}
              corridors={track?.corridors ?? []}
              selectedId={selectedVessel}
              previewPath={previewPath}
              onSelect={(id) => {
                setSelectedVessel(id);
                setPreviewAlt(null);
                const v = track?.vessels.find((x) => x.id === id);
                setMapNote(v ? `Судно: ${v.name} · ${v.route_label}` : null);
              }}
              onPortSelect={(_id, name) => setMapNote(`Город: ${name}`)}
              onAlertSelect={(id) => {
                const a = track?.alerts.find((x) => x.id === id);
                setMapNote(a ? `Шторм: ${a.title}` : null);
              }}
            />
          </div>
        </div>
      )}
    </>
  );
}
