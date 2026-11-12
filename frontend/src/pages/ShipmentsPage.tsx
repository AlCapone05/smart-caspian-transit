import { useEffect, useMemo, useState, type FormEvent, type MouseEvent } from "react";
import { useNavigate } from "react-router-dom";
import { api, type ShipmentSummary, type ShipmentWriteBody } from "../api";
import { Layout } from "../components/Layout";
import { delayLabel, fmtMsk } from "../format";

const PORTS = [
  { id: "port_astrakhan", label: "Астрахань" },
  { id: "port_makhachkala", label: "Махачкала" },
  { id: "port_aktau", label: "Актау" },
  { id: "port_baku", label: "Баку" },
  { id: "port_anzali", label: "Энзели" },
] as const;

const STAGES = [
  "Планирование",
  "Ж/Д к порту",
  "Портовая обработка",
  "Морской переход",
  "Выгрузка",
  "Автодоставка",
  "Завершено",
];

const EQUIPMENT = ["1 × 40′ HC", "1 × 20′ DC", "2 × 40′ HC", "Reefer 40′", "Flat rack"];

function daysFromNowLocal(days: number): string {
  const d = new Date(Date.now() + days * 86400000);
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

function fromLocalInput(value: string): string | undefined {
  if (!value) return undefined;
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return undefined;
  return d.toISOString();
}

function nextReferenceHint(items: ShipmentSummary[]): string {
  const nums = items
    .map((s) => {
      const m = /^SCT-(\d+)$/i.exec(s.reference);
      return m ? Number(m[1]) : 0;
    })
    .filter((n) => n > 0);
  const next = (nums.length ? Math.max(...nums) : 2048) + 1;
  return `SCT-${next}`;
}

type CreateForm = ShipmentWriteBody & {
  origin_port_id: string;
  destination_port_id: string;
  planned_eta_local: string;
  predicted_eta_local: string;
  create_vessel: boolean;
  vessel_name: string;
};

const emptyForm = (hint = "SCT-2050"): CreateForm => ({
  reference: hint,
  cargo_description: "Контейнерный груз",
  cargo_tonnes: 22,
  container_no: "",
  equipment: "1 × 40′ HC",
  route_from: "Астрахань",
  route_to: "Энзели",
  origin_port_id: "port_astrakhan",
  destination_port_id: "port_anzali",
  current_stage: "Планирование",
  current_location: "Астрахань",
  status: "planned",
  risk_level: "low",
  cost_rub: undefined,
  co2e_tonnes: undefined,
  delay_hours: 0,
  planned_eta_local: daysFromNowLocal(5),
  predicted_eta_local: daysFromNowLocal(5),
  create_vessel: true,
  vessel_name: "",
});

const DONE = new Set(["delivered", "completed", "cancelled"]);

export function ShipmentsPage() {
  const [items, setItems] = useState<ShipmentSummary[]>([]);
  const [search, setSearch] = useState("");
  const [picked, setPicked] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [tab, setTab] = useState<"active" | "done">("active");
  const [form, setForm] = useState<CreateForm>(emptyForm());
  const navigate = useNavigate();

  const reload = async () => {
    const d = await api.listShipments();
    setItems(d.items);
  };

  useEffect(() => {
    reload().catch((e: Error) => setError(e.message));
  }, []);

  // Общий backend с мобильным приложением — подтягиваем изменения с телефона
  useEffect(() => {
    if (modalOpen) return;
    const id = window.setInterval(() => {
      reload().catch(() => undefined);
    }, 5000);
    return () => window.clearInterval(id);
  }, [modalOpen]);

  useEffect(() => {
    if (!modalOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !busy) setModalOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [modalOpen, busy]);

  const activeCount = useMemo(
    () => items.filter((s) => !DONE.has(s.status)).length,
    [items]
  );
  const doneCount = useMemo(
    () => items.filter((s) => DONE.has(s.status)).length,
    [items]
  );

  const rows = useMemo(() => {
    const byTab = items.filter((s) =>
      tab === "done" ? DONE.has(s.status) : !DONE.has(s.status)
    );
    const q = search.trim().toLowerCase();
    if (!q) return byTab;
    return byTab.filter((s) => {
      const hay = [
        s.reference,
        s.route_label,
        s.current_stage,
        s.cargo_description || "",
        s.container_no || "",
        s.status,
        s.risk_level,
        s.documents_label,
      ]
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [items, search, tab]);

  const openCreate = () => {
    setFieldError(null);
    setError(null);
    setForm(emptyForm(nextReferenceHint(items)));
    setModalOpen(true);
  };

  const setOrigin = (portId: string) => {
    const p = PORTS.find((x) => x.id === portId);
    setForm((f) => ({
      ...f,
      origin_port_id: portId,
      route_from: p?.label || f.route_from,
      current_location: f.current_location === f.route_from ? p?.label || f.current_location : f.current_location,
    }));
  };

  const setDest = (portId: string) => {
    const p = PORTS.find((x) => x.id === portId);
    setForm((f) => ({
      ...f,
      destination_port_id: portId,
      route_to: p?.label || f.route_to,
    }));
  };

  const toggle = (id: string, e: MouseEvent) => {
    e.stopPropagation();
    setPicked((prev) => (prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id]));
  };

  const validate = (): string | null => {
    if (!form.cargo_description?.trim()) return "Укажите описание груза";
    if (!form.origin_port_id || !form.destination_port_id) return "Выберите порты маршрута";
    if (form.origin_port_id === form.destination_port_id) return "Откуда и куда должны отличаться";
    if (!form.planned_eta_local) return "Укажите плановый ETA";
    if (form.cargo_tonnes == null || form.cargo_tonnes <= 0) return "Укажите тоннаж больше 0";
    const planned = fromLocalInput(form.planned_eta_local);
    const predicted = fromLocalInput(form.predicted_eta_local || form.planned_eta_local);
    if (!planned || !predicted) return "Некорректная дата ETA";
    return null;
  };

  const onCreate = async (e: FormEvent) => {
    e.preventDefault();
    const ve = validate();
    if (ve) {
      setFieldError(ve);
      return;
    }
    setBusy(true);
    setError(null);
    setFieldError(null);
    try {
      const planned = fromLocalInput(form.planned_eta_local)!;
      const predicted = fromLocalInput(form.predicted_eta_local || form.planned_eta_local)!;
      const delayHours = Math.max(
        0,
        (new Date(predicted).getTime() - new Date(planned).getTime()) / 3600000
      );
      const created = await api.createShipment({
        reference: form.reference?.trim() || undefined,
        cargo_description: form.cargo_description?.trim(),
        cargo_tonnes: form.cargo_tonnes,
        container_no: form.container_no?.trim() || undefined,
        equipment: form.equipment,
        route_from: form.route_from,
        route_to: form.route_to,
        origin_port_id: form.origin_port_id,
        destination_port_id: form.destination_port_id,
        current_stage: form.current_stage,
        current_location: form.current_location || form.route_from,
        status: form.status,
        risk_level: form.risk_level,
        planned_eta: planned,
        predicted_eta: predicted,
        delay_hours: form.delay_hours ?? delayHours,
        cost_rub: form.cost_rub,
        co2e_tonnes: form.co2e_tonnes,
        create_vessel: form.create_vessel,
        vessel_name: form.vessel_name?.trim() || undefined,
      } as ShipmentWriteBody);
      setModalOpen(false);
      setForm(emptyForm());
      await reload();
      navigate(`/shipments/${created.id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const onDelete = async (id: string, reference: string, e: MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm(`Удалить перевозку ${reference}?`)) return;
    setBusy(true);
    setError(null);
    try {
      await api.deleteShipment(id);
      setPicked((prev) => prev.filter((x) => x !== id));
      await reload();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const routePreview = `${form.route_from || "—"} → ${form.route_to || "—"}`;

  return (
    <>
      <Layout title="Перевозки" search={search} onSearch={setSearch}>
        <div className="docs-header-row">
          <div>
            <h1 className="page-title">Перевозки</h1>
            <p className="page-sub">
              Активные грузы на карте · после прибытия в пункт Б — во вкладке «Завершённые»
            </p>
          </div>
          <div style={{ display: "flex", gap: 10, flexWrap: "wrap" }}>
            {tab === "active" && (
              <button type="button" className="btn" onClick={openCreate}>
                + Добавить груз
              </button>
            )}
            <button
              type="button"
              className="btn ghost"
              disabled={picked.length < 2}
              onClick={() => navigate(`/compare?ids=${picked.join(",")}`)}
            >
              Сравнить ({picked.length})
            </button>
          </div>
        </div>
        {error && <p className="error">{error}</p>}

        <div className="shipments-tabs" role="tablist" aria-label="Статус перевозок">
          <button
            type="button"
            role="tab"
            aria-selected={tab === "active"}
            className={`shipments-tab ${tab === "active" ? "on" : ""}`}
            onClick={() => {
              setTab("active");
              setPicked([]);
            }}
          >
            Активные · {activeCount}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={tab === "done"}
            className={`shipments-tab ${tab === "done" ? "on" : ""}`}
            onClick={() => {
              setTab("done");
              setPicked([]);
            }}
          >
            Завершённые · {doneCount}
          </button>
        </div>

        <section className="card table-card">
          <table className="shipment-table">
            <thead>
              <tr>
                <th style={{ width: 40 }} />
                <th>Груз</th>
                <th>Маршрут</th>
                <th>Текущий этап</th>
                <th>Прогноз · МСК</th>
                <th>К плану</th>
                <th>Риск</th>
                <th>Документы</th>
                <th style={{ width: 120 }} />
              </tr>
            </thead>
            <tbody>
              {rows.map((s) => (
                <tr key={s.id} onClick={() => navigate(`/shipments/${s.id}`)}>
                  <td onClick={(e) => toggle(s.id, e)}>
                    <input type="checkbox" checked={picked.includes(s.id)} readOnly />
                  </td>
                  <td>{s.reference}</td>
                  <td>{s.route_label}</td>
                  <td>{s.current_stage}</td>
                  <td>{fmtMsk(s.predicted_eta)}</td>
                  <td className={s.delay_hours >= 12 ? "delay-amber" : s.delay_hours > 0 ? "delay-red" : ""}>
                    {delayLabel(s.delay_hours)}
                  </td>
                  <td>{s.risk_level}</td>
                  <td>{s.documents_label}</td>
                  <td onClick={(e) => e.stopPropagation()}>
                    <div style={{ display: "flex", gap: 6 }}>
                      {tab === "active" && (
                        <button
                          type="button"
                          className="btn ghost"
                          style={{ padding: "4px 8px", minHeight: 0 }}
                          onClick={() => navigate(`/shipments/${s.id}?edit=1`)}
                        >
                          Изменить
                        </button>
                      )}
                      <button
                        type="button"
                        className="btn ghost"
                        style={{ padding: "4px 8px", minHeight: 0, color: "#a33" }}
                        disabled={busy}
                        onClick={(e) => onDelete(s.id, s.reference, e)}
                      >
                        Удал.
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
              {rows.length === 0 && (
                <tr>
                  <td colSpan={9} className="muted">
                    {tab === "active"
                      ? "Нет активных перевозок. Создайте груз — он появится на карте."
                      : "Завершённых перевозок пока нет. Груз попадёт сюда после прибытия в пункт Б."}
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </section>

        <p className="footer-note">Каспийский коридор · время МСК (UTC+3)</p>
      </Layout>

      {modalOpen && (
        <div className="modal-backdrop" onClick={() => !busy && setModalOpen(false)}>
          <form
            className="modal-card card shipment-create-modal"
            onClick={(e) => e.stopPropagation()}
            onSubmit={onCreate}
          >
            <h2 style={{ marginTop: 0 }}>Новая перевозка</h2>
            <p className="muted" style={{ marginTop: -4 }}>
              Мультимодальный каркас ж/д → порт → море → авто · маршрут{" "}
              <strong>{routePreview}</strong>
            </p>

            {(fieldError || error) && <p className="error">{fieldError || error}</p>}

            <div className="form-grid">
              <label>
                Референс
                <input
                  value={form.reference || ""}
                  placeholder="SCT-XXXX"
                  onChange={(e) => setForm({ ...form, reference: e.target.value })}
                />
              </label>
              <label>
                Контейнер
                <input
                  value={form.container_no || ""}
                  placeholder="авто, если пусто"
                  onChange={(e) => setForm({ ...form, container_no: e.target.value })}
                />
              </label>

              <label>
                Откуда (порт)
                <select value={form.origin_port_id} onChange={(e) => setOrigin(e.target.value)} required>
                  {PORTS.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Куда (порт)
                <select value={form.destination_port_id} onChange={(e) => setDest(e.target.value)} required>
                  {PORTS.map((p) => (
                    <option key={p.id} value={p.id}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="span-2">
                Описание груза
                <input
                  required
                  value={form.cargo_description || ""}
                  onChange={(e) => setForm({ ...form, cargo_description: e.target.value })}
                />
              </label>

              <label>
                Оборудование
                <select
                  value={form.equipment || EQUIPMENT[0]}
                  onChange={(e) => setForm({ ...form, equipment: e.target.value })}
                >
                  {EQUIPMENT.map((eq) => (
                    <option key={eq} value={eq}>
                      {eq}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Тоннаж
                <input
                  type="number"
                  min={0.1}
                  step={0.1}
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
                Этап
                <select
                  value={form.current_stage || STAGES[0]}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      current_stage: e.target.value,
                      current_location:
                        e.target.value === "Морской переход" || e.target.value === "Выгрузка"
                          ? form.route_to
                          : form.route_from,
                    })
                  }
                >
                  {STAGES.map((s) => (
                    <option key={s} value={s}>
                      {s}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Статус
                <select
                  value={form.status || "planned"}
                  onChange={(e) => setForm({ ...form, status: e.target.value })}
                >
                  <option value="planned">Планируется</option>
                  <option value="in_transit">В пути</option>
                  <option value="delayed">Задержка</option>
                  <option value="completed">Завершена</option>
                </select>
              </label>

              <label>
                План ETA
                <input
                  type="datetime-local"
                  required
                  value={form.planned_eta_local}
                  onChange={(e) => setForm({ ...form, planned_eta_local: e.target.value })}
                />
              </label>
              <label>
                Прогноз ETA
                <input
                  type="datetime-local"
                  value={form.predicted_eta_local}
                  onChange={(e) => setForm({ ...form, predicted_eta_local: e.target.value })}
                />
              </label>

              <label>
                Риск
                <select
                  value={form.risk_level || "low"}
                  onChange={(e) => setForm({ ...form, risk_level: e.target.value })}
                >
                  <option value="low">Низкий</option>
                  <option value="medium">Средний</option>
                  <option value="high">Высокий</option>
                </select>
              </label>
              <label>
                Стоимость, ₽
                <input
                  type="number"
                  min={0}
                  placeholder="авто по дистанции"
                  value={form.cost_rub ?? ""}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      cost_rub: e.target.value === "" ? undefined : Number(e.target.value),
                    })
                  }
                />
              </label>

              <label>
                CO₂e, т
                <input
                  type="number"
                  min={0}
                  step={0.01}
                  placeholder="авто"
                  value={form.co2e_tonnes ?? ""}
                  onChange={(e) =>
                    setForm({
                      ...form,
                      co2e_tonnes: e.target.value === "" ? undefined : Number(e.target.value),
                    })
                  }
                />
              </label>
              <label>
                Локация
                <input
                  value={form.current_location || ""}
                  onChange={(e) => setForm({ ...form, current_location: e.target.value })}
                />
              </label>

              <label className="span-2 check-row" style={{ marginTop: 4 }}>
                <input
                  type="checkbox"
                  checked={form.create_vessel}
                  onChange={(e) => setForm({ ...form, create_vessel: e.target.checked })}
                />
                Поставить судно на карту Каспия (GPS)
              </label>
              {form.create_vessel && (
                <label className="span-2">
                  Имя судна
                  <input
                    value={form.vessel_name}
                    placeholder={`MV ${form.reference || "SCT-XXXX"}`}
                    onChange={(e) => setForm({ ...form, vessel_name: e.target.value })}
                  />
                </label>
              )}
            </div>

            <div className="create-legs-hint">
              <strong>Будет создано автоматически</strong>
              <ul>
                <li>5 плеч: ж/д → порт → море → порт → авто</li>
                <li>Пакет из 5 документов с проверкой комплектности</li>
                <li>Прогноз ETA и событие в таймлайне</li>
                {form.create_vessel && <li>Судно на коридоре {routePreview}</li>}
              </ul>
            </div>

            <div className="modal-actions">
              <button type="button" className="btn ghost" disabled={busy} onClick={() => setModalOpen(false)}>
                Отмена
              </button>
              <button type="submit" className="btn" disabled={busy}>
                {busy ? "Создание…" : "Создать перевозку"}
              </button>
            </div>
          </form>
        </div>
      )}
    </>
  );
}
