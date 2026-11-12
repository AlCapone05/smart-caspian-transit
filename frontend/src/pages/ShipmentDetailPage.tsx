import { useEffect, useMemo, useState, type FormEvent } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api, type ShipmentDetail, type ShipmentWriteBody } from "../api";
import { Layout } from "../components/Layout";
import { fmtMsk, fmtTimeMsk, tzShort } from "../format";
import { useSettings } from "../settings";

const SCENARIOS = [
  { id: "normal", label: "Обычные условия" },
  { id: "storm", label: "Шторм" },
  { id: "port_congestion", label: "Перегрузка порта" },
];

type LegDraft = {
  id?: string;
  sequence: number;
  mode: string;
  label: string;
  origin_name: string;
  destination_name: string;
  distance_km: number;
  planned_arrival: string;
  predicted_arrival: string;
  status: string;
  stage_status_label: string;
};

function toLocalInput(iso: string | null | undefined): string {
  if (!iso) return "";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromLocalInput(value: string): string | undefined {
  if (!value) return undefined;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return undefined;
  return d.toISOString();
}

export function ShipmentDetailPage() {
  const { id = "" } = useParams();
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { settings } = useSettings();
  const co2Pct = settings?.co2_uncertainty_pct ?? 15;
  const defaultScenario = settings?.default_scenario ?? "normal";
  const [detail, setDetail] = useState<ShipmentDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [editing, setEditing] = useState(params.get("edit") === "1");
  const [form, setForm] = useState<ShipmentWriteBody>({});
  const [legs, setLegs] = useState<LegDraft[]>([]);

  const load = async () => {
    const d = await api.getShipment(id);
    setDetail(d);
    const portByName: Record<string, string> = {
      Астрахань: "port_astrakhan",
      Махачкала: "port_makhachkala",
      Актау: "port_aktau",
      Баку: "port_baku",
      Энзели: "port_anzali",
    };
    setForm({
      reference: d.reference,
      cargo_description: d.cargo_description,
      cargo_tonnes: d.cargo_tonnes,
      container_no: d.container_no,
      equipment: d.equipment,
      route_from: d.route_from,
      route_to: d.route_to,
      origin_port_id: portByName[d.route_from] || d.route_from,
      destination_port_id: portByName[d.route_to] || d.route_to,
      current_stage: d.current_stage,
      current_location: d.current_location,
      status: d.status,
      risk_level: d.risk_level,
      planned_eta: d.planned_eta,
      predicted_eta: d.predicted_eta ?? undefined,
      delay_hours: d.delay_hours,
      cost_rub: d.cost_rub,
      co2e_tonnes: d.co2e_tonnes,
      risk_headline: d.risk_headline,
      risk_detail: d.risk_detail,
      missed_connection: d.missed_connection,
      active_scenario: d.active_scenario,
    });
    setLegs(
      d.legs.map((l) => ({
        id: l.id,
        sequence: l.sequence,
        mode: l.mode,
        label: l.label,
        origin_name: (l as { origin_name?: string }).origin_name || "",
        destination_name: (l as { destination_name?: string }).destination_name || "",
        distance_km: (l as { distance_km?: number }).distance_km || 0,
        planned_arrival: l.planned_arrival,
        predicted_arrival: l.predicted_arrival || l.planned_arrival,
        status: l.status,
        stage_status_label: l.stage_status_label,
      }))
    );
  };

  useEffect(() => {
    load().catch((e: Error) => setError(e.message));
  }, [id]);

  useEffect(() => {
    if (params.get("edit") === "1") setEditing(true);
  }, [params]);

  const onScenario = async (scenario: string) => {
    setBusy(true);
    setError(null);
    try {
      await api.simulate(id, scenario);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const onSave = async (e: FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api.updateShipment(id, {
        ...form,
        planned_eta: fromLocalInput(toLocalInput(form.planned_eta)) || form.planned_eta,
        predicted_eta: fromLocalInput(toLocalInput(form.predicted_eta)) || form.predicted_eta,
        legs: legs.map((l, i) => ({
          id: l.id,
          sequence: i + 1,
          mode: l.mode,
          label: l.label,
          origin_name: l.origin_name,
          destination_name: l.destination_name,
          distance_km: l.distance_km,
          planned_arrival: fromLocalInput(toLocalInput(l.planned_arrival)) || l.planned_arrival,
          predicted_arrival: fromLocalInput(toLocalInput(l.predicted_arrival)) || l.predicted_arrival,
          status: l.status,
          stage_status_label: l.stage_status_label,
        })),
      });
      await load();
      setEditing(false);
      navigate(`/shipments/${id}`, { replace: true });
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const onDelete = async () => {
    if (!detail) return;
    if (!window.confirm(`Удалить перевозку ${detail.reference}?`)) return;
    setBusy(true);
    try {
      await api.deleteShipment(id);
      navigate("/shipments");
    } catch (err) {
      setError((err as Error).message);
      setBusy(false);
    }
  };

  const addLeg = () => {
    setLegs((prev) => [
      ...prev,
      {
        sequence: prev.length + 1,
        mode: "road",
        label: "Новое плечо",
        origin_name: form.route_to || "",
        destination_name: "",
        distance_km: 50,
        planned_arrival: form.planned_eta || new Date().toISOString(),
        predicted_arrival: form.predicted_eta || form.planned_eta || new Date().toISOString(),
        status: "planned",
        stage_status_label: "○ Далее",
      },
    ]);
  };

  const title = useMemo(() => detail?.reference ?? "Перевозка", [detail]);

  if (!detail && !error) {
    return (
      <Layout title="Перевозки">
        <p className="muted">Загрузка…</p>
      </Layout>
    );
  }

  if (!detail) {
    return (
      <Layout title="Перевозки">
        <p className="error">{error}</p>
      </Layout>
    );
  }

  return (
    <Layout title="Перевозки">
      <p className="crumb">
        <Link to="/shipments">Перевозки</Link>
        {"  /  "}
        {title}
      </p>

      <div className="detail-head">
        <div>
          <h1 className="page-title">{detail.reference}</h1>
          <p className="page-sub">{detail.route_label}</p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
          <span className="status-pill">◷ {detail.current_stage}</span>
          {!editing ? (
            <>
              <button type="button" className="btn" onClick={() => setEditing(true)}>
                Редактировать
              </button>
              <button type="button" className="btn ghost" disabled={busy} onClick={onDelete}>
                Удалить
              </button>
            </>
          ) : (
            <button type="button" className="btn ghost" onClick={() => setEditing(false)} disabled={busy}>
              Отмена
            </button>
          )}
        </div>
      </div>
      <p className="muted">{detail.cargo_line}</p>

      {editing ? (
        <form className="card" onSubmit={onSave} style={{ marginBottom: 20 }}>
          <h3 style={{ marginTop: 0 }}>Полное редактирование</h3>
          <div className="form-grid">
            <label>
              Референс
              <input
                value={form.reference || ""}
                onChange={(e) => setForm({ ...form, reference: e.target.value })}
              />
            </label>
            <label>
              Контейнер
              <input
                value={form.container_no || ""}
                onChange={(e) => setForm({ ...form, container_no: e.target.value })}
              />
            </label>
            <label>
              Откуда
              <select
                value={form.origin_port_id || form.route_from || ""}
                onChange={(e) => {
                  const map: Record<string, string> = {
                    port_astrakhan: "Астрахань",
                    port_makhachkala: "Махачкала",
                    port_aktau: "Актау",
                    port_baku: "Баку",
                    port_anzali: "Энзели",
                  };
                  const id = e.target.value;
                  setForm({
                    ...form,
                    origin_port_id: id,
                    route_from: map[id] || id,
                  });
                }}
              >
                <option value="port_astrakhan">Астрахань</option>
                <option value="port_makhachkala">Махачкала</option>
                <option value="port_aktau">Актау</option>
                <option value="port_baku">Баку</option>
                <option value="port_anzali">Энзели</option>
              </select>
            </label>
            <label>
              Куда
              <select
                value={form.destination_port_id || form.route_to || ""}
                onChange={(e) => {
                  const map: Record<string, string> = {
                    port_astrakhan: "Астрахань",
                    port_makhachkala: "Махачкала",
                    port_aktau: "Актау",
                    port_baku: "Баку",
                    port_anzali: "Энзели",
                  };
                  const id = e.target.value;
                  setForm({
                    ...form,
                    destination_port_id: id,
                    route_to: map[id] || id,
                  });
                }}
              >
                <option value="port_astrakhan">Астрахань</option>
                <option value="port_makhachkala">Махачкала</option>
                <option value="port_aktau">Актау</option>
                <option value="port_baku">Баку</option>
                <option value="port_anzali">Энзели</option>
              </select>
            </label>
            <label className="span-2">
              Описание груза
              <input
                value={form.cargo_description || ""}
                onChange={(e) => setForm({ ...form, cargo_description: e.target.value })}
              />
            </label>
            <label>
              Оборудование
              <input
                value={form.equipment || ""}
                onChange={(e) => setForm({ ...form, equipment: e.target.value })}
              />
            </label>
            <label>
              Тоннаж
              <input
                type="number"
                step={0.1}
                min={0.1}
                inputMode="decimal"
                value={form.cargo_tonnes === undefined || form.cargo_tonnes === null ? "" : form.cargo_tonnes}
                onChange={(e) => {
                  const raw = e.target.value;
                  if (raw === "") {
                    setForm({ ...form, cargo_tonnes: undefined });
                    return;
                  }
                  const n = Number(raw);
                  if (!Number.isNaN(n)) setForm({ ...form, cargo_tonnes: n });
                }}
              />
            </label>
            <label>
              Текущий этап
              <input
                value={form.current_stage || ""}
                onChange={(e) => setForm({ ...form, current_stage: e.target.value })}
              />
            </label>
            <label>
              Локация
              <input
                value={form.current_location || ""}
                onChange={(e) => setForm({ ...form, current_location: e.target.value })}
              />
            </label>
            <label>
              Статус
              <select
                value={form.status || "in_transit"}
                onChange={(e) => setForm({ ...form, status: e.target.value })}
              >
                <option value="planned">planned</option>
                <option value="in_transit">in_transit</option>
                <option value="delayed">delayed</option>
                <option value="completed">completed</option>
              </select>
            </label>
            <label>
              Риск
              <select
                value={form.risk_level || "low"}
                onChange={(e) => setForm({ ...form, risk_level: e.target.value })}
              >
                <option value="low">low</option>
                <option value="medium">medium</option>
                <option value="high">high</option>
              </select>
            </label>
            <label>
              План ETA
              <input
                type="datetime-local"
                value={toLocalInput(form.planned_eta)}
                onChange={(e) =>
                  setForm({ ...form, planned_eta: fromLocalInput(e.target.value) || form.planned_eta })
                }
              />
            </label>
            <label>
              Прогноз ETA
              <input
                type="datetime-local"
                value={toLocalInput(form.predicted_eta)}
                onChange={(e) =>
                  setForm({
                    ...form,
                    predicted_eta: fromLocalInput(e.target.value) || form.predicted_eta,
                  })
                }
              />
            </label>
            <label>
              Задержка, ч
              <input
                type="number"
                value={form.delay_hours ?? 0}
                onChange={(e) => setForm({ ...form, delay_hours: Number(e.target.value) })}
              />
            </label>
            <label>
              Стоимость, ₽
              <input
                type="number"
                value={form.cost_rub ?? 0}
                onChange={(e) => setForm({ ...form, cost_rub: Number(e.target.value) })}
              />
            </label>
            <label>
              CO₂e, т
              <input
                type="number"
                step={0.01}
                value={form.co2e_tonnes ?? 0}
                onChange={(e) => setForm({ ...form, co2e_tonnes: Number(e.target.value) })}
              />
            </label>
            <label className="span-2">
              Заголовок риска
              <input
                value={form.risk_headline || ""}
                onChange={(e) => setForm({ ...form, risk_headline: e.target.value })}
              />
            </label>
            <label className="span-2">
              Детали риска
              <textarea
                rows={2}
                value={form.risk_detail || ""}
                onChange={(e) => setForm({ ...form, risk_detail: e.target.value })}
              />
            </label>
          </div>

          <div className="legs-edit">
            <div className="docs-header-row" style={{ marginBottom: 8 }}>
              <h4 style={{ margin: 0 }}>Плечи маршрута</h4>
              <button type="button" className="btn ghost" onClick={addLeg}>
                + Плечо
              </button>
            </div>
            {legs.map((leg, idx) => (
              <div key={leg.id || idx} className="leg-edit-row">
                <input
                  placeholder="Метка"
                  value={leg.label}
                  onChange={(e) => {
                    const next = [...legs];
                    next[idx] = { ...leg, label: e.target.value };
                    setLegs(next);
                  }}
                />
                <select
                  value={leg.mode}
                  onChange={(e) => {
                    const next = [...legs];
                    next[idx] = { ...leg, mode: e.target.value };
                    setLegs(next);
                  }}
                >
                  <option value="rail">rail</option>
                  <option value="port_handling">port_handling</option>
                  <option value="sea">sea</option>
                  <option value="road">road</option>
                </select>
                <input
                  placeholder="Откуда"
                  value={leg.origin_name}
                  onChange={(e) => {
                    const next = [...legs];
                    next[idx] = { ...leg, origin_name: e.target.value };
                    setLegs(next);
                  }}
                />
                <input
                  placeholder="Куда"
                  value={leg.destination_name}
                  onChange={(e) => {
                    const next = [...legs];
                    next[idx] = { ...leg, destination_name: e.target.value };
                    setLegs(next);
                  }}
                />
                <input
                  type="number"
                  placeholder="км"
                  value={leg.distance_km}
                  onChange={(e) => {
                    const next = [...legs];
                    next[idx] = { ...leg, distance_km: Number(e.target.value) };
                    setLegs(next);
                  }}
                />
                <select
                  value={leg.status}
                  onChange={(e) => {
                    const next = [...legs];
                    next[idx] = { ...leg, status: e.target.value };
                    setLegs(next);
                  }}
                >
                  <option value="planned">planned</option>
                  <option value="in_progress">in_progress</option>
                  <option value="completed">completed</option>
                </select>
                <button
                  type="button"
                  className="btn ghost"
                  onClick={() => setLegs(legs.filter((_, i) => i !== idx))}
                >
                  ×
                </button>
              </div>
            ))}
          </div>

          <div className="modal-actions" style={{ marginTop: 16 }}>
            <button type="submit" className="btn" disabled={busy}>
              {busy ? "Сохранение…" : "Сохранить изменения"}
            </button>
          </div>
        </form>
      ) : (
        <>
          <section className="card metrics-3">
            <div>
              <p className="kpi-label">Плановое прибытие · {tzShort()}</p>
              <p className="kpi-value">{fmtMsk(detail.planned_eta)}</p>
            </div>
            <div>
              <p className="kpi-label">Прогноз прибытия · {tzShort()}</p>
              <p className="kpi-value">{fmtMsk(detail.predicted_eta)}</p>
            </div>
            <div>
              <p className="kpi-label">Отклонение от плана</p>
              <p className={`kpi-value ${detail.delay_hours > 0 ? "delay-amber" : ""}`}>
                {detail.delay_hours > 0
                  ? `+${Math.round(detail.delay_hours)} часов`
                  : "По плану"}
              </p>
            </div>
          </section>
          {detail.selected_alternative_id && (
            <p className="map-selected">
              Выбранный маршрут: {detail.selected_alternative_id.replace("alt_", "").replace(/_/g, " ")}
            </p>
          )}

          <div className="detail-grid">
            <section className="card">
              <h3 style={{ fontSize: 22, marginTop: 0 }}>Путь груза</h3>
              <p style={{ color: "var(--color-blue)", fontWeight: 500, marginTop: 0 }}>
                Сейчас · {detail.current_location}
              </p>
              <div className="stages">
                {detail.legs.map((leg) => {
                  const done = leg.status === "completed" || Boolean(leg.actual_arrival);
                  const active = leg.status === "in_progress";
                  return (
                    <div className="stage" key={leg.id}>
                      <div className={`stage-line ${done || active ? "done" : ""}`} />
                      <strong>
                        {String(leg.sequence).padStart(2, "0")} &nbsp; {leg.label}
                      </strong>
                      <span className={`label ${active ? "active" : ""}`}>{leg.stage_status_label}</span>
                      <span className="meta">План {fmtMsk(leg.planned_arrival)}</span>
                      {leg.actual_arrival ? (
                        <span className="meta">Факт {fmtMsk(leg.actual_arrival)}</span>
                      ) : (
                        <span className="meta pred">Прогноз {fmtMsk(leg.predicted_arrival)}</span>
                      )}
                    </div>
                  );
                })}
              </div>
              <hr style={{ border: 0, borderTop: "1px solid var(--color-border)", margin: "16px 0" }} />
              <p className="footer-note">
                Все даты — ноябрь 2026, МСК (UTC+3).
                <br />
                Сплошная линия — факт · последующие этапы — прогноз.
              </p>
            </section>

            <aside className="risk-card">
              <h3>{detail.risk_headline ?? "Риск не выявлен"}</h3>
              <p>{detail.risk_detail ?? "Сценарий без критического отклонения."}</p>
              <button
                type="button"
                className="btn"
                onClick={() => navigate(`/shipments/${detail.id}/alternatives`)}
              >
                Сравнить альтернативы
              </button>
              <p className="footer-note">
                Модель SCT · прогноз задержки
                <br />
                Обновлено {fmtMsk(new Date().toISOString())} МСК
              </p>
            </aside>
          </div>

          <div className="detail-grid">
            <section className="card">
              <h3 style={{ marginTop: 0 }}>История событий</h3>
              {detail.timeline.map((e) => (
                <div className="timeline-row" key={e.id}>
                  <time>{fmtTimeMsk(e.occurred_at)}</time>
                  <span>{e.title}</span>
                </div>
              ))}
            </section>
            <section className="card" id="docs">
              <button
                type="button"
                className="btn ghost"
                style={{ width: "100%" }}
                onClick={() => navigate(`/documents?shipment=${detail.id}`)}
              >
                Документы · {detail.documents_ready} из {detail.documents_total}
              </button>
              <h3 style={{ margin: "16px 0 8px" }}>
                CO₂e · оценка {detail.co2e_tonnes.toFixed(2).replace(".", ",")} т
              </h3>
              <p className="footer-note">
                Расчёт по этапам, ±{co2Pct}% (из настроек).
                <br />
                Не является верифицированным отчётом.
              </p>
              <p className="footer-note" style={{ marginTop: 12 }}>
                {detail.documents.disclaimer}
              </p>
            </section>
          </div>

          <div className="scenario-bar">
            <span className="tag">СЦЕНАРИЙ · ПРОТОТИП</span>
            {SCENARIOS.map((s) => (
              <button
                key={s.id}
                type="button"
                className={`btn ${detail.active_scenario === s.id ? "selected" : "ghost"}`}
                disabled={busy}
                onClick={() => onScenario(s.id)}
              >
                {s.label}
                {s.id === defaultScenario ? " · default" : ""}
              </button>
            ))}
            <button
              type="button"
              className="btn"
              disabled={busy}
              onClick={() => onScenario(defaultScenario)}
            >
              Применить сценарий из настроек
            </button>
          </div>
        </>
      )}

      {error && <p className="error">{error}</p>}
      <p className="footer-note">{detail.schedule_disclaimer}</p>
    </Layout>
  );
}
