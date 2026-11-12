import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, type ComparePayload, type ShipmentSummary } from "../api";
import { Layout } from "../components/Layout";
import { fmtMsk } from "../format";

export function ComparePage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [all, setAll] = useState<ShipmentSummary[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [data, setData] = useState<ComparePayload | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api
      .listShipments()
      .then((r) => {
        setAll(r.items);
        const fromUrl = (params.get("ids") || "")
          .split(",")
          .map((x) => x.trim())
          .filter(Boolean);
        const initial =
          fromUrl.length >= 2
            ? fromUrl
            : r.items.slice(0, Math.min(3, r.items.length)).map((s) => s.id);
        setSelected(initial);
        if (initial.length) {
          navigate(`/compare?ids=${initial.join(",")}`, { replace: true });
        }
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  useEffect(() => {
    if (selected.length < 2) {
      setData(null);
      return;
    }
    setLoading(true);
    api
      .compareShipments(selected)
      .then(setData)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [selected.join(",")]);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id];
      navigate(`/compare?ids=${next.join(",")}`, { replace: true });
      return next;
    });
  };

  const selectAll = () => {
    const ids = all.map((s) => s.id);
    setSelected(ids);
    navigate(`/compare?ids=${ids.join(",")}`, { replace: true });
  };

  const winner = useMemo(
    () => data?.columns.find((c) => c.shipment_id === data.winner_id) ?? null,
    [data]
  );

  const metricRows = useMemo(
    () => [
      { key: "rank", label: "Место", format: (c: ComparePayload["columns"][0]) => `#${c.rank}` },
      { key: "score", label: "Балл 0–100", format: (c: ComparePayload["columns"][0]) => String(c.score) },
      { key: "route_label", label: "Маршрут", format: (c: ComparePayload["columns"][0]) => c.route_label },
      { key: "cargo", label: "Груз", format: (c: ComparePayload["columns"][0]) => c.cargo },
      { key: "current_stage", label: "Этап", format: (c: ComparePayload["columns"][0]) => c.current_stage },
      {
        key: "predicted_eta",
        label: "Прогноз · МСК",
        format: (c: ComparePayload["columns"][0]) => fmtMsk(c.predicted_eta),
      },
      { key: "delay_label", label: "К плану", format: (c: ComparePayload["columns"][0]) => c.delay_label },
      { key: "risk_level", label: "Риск", format: (c: ComparePayload["columns"][0]) => c.risk_level },
      { key: "cost_label", label: "Стоимость", format: (c: ComparePayload["columns"][0]) => c.cost_label },
      { key: "co2e_label", label: "CO₂e", format: (c: ComparePayload["columns"][0]) => c.co2e_label },
      {
        key: "documents_label",
        label: "Документы",
        format: (c: ComparePayload["columns"][0]) =>
          `${c.documents_label}${c.documents_issues > 0 ? " △" : ""}`,
      },
      {
        key: "legs_count",
        label: "Плечи",
        format: (c: ComparePayload["columns"][0]) => String(c.legs_count),
      },
    ],
    []
  );

  return (
    <Layout title="Сравнение">
      <h1 className="page-title">{data?.title ?? "Сравнение перевозок"}</h1>
      <p className="page-sub">
        {data?.subtitle ??
          "Выберите минимум 2 груза — баллы по времени, риску, документам, цене и CO₂e"}
      </p>

      <div className="kpi-row">
        <div>
          <p className="kpi-label">В выборке</p>
          <p className="kpi-value">{all.length}</p>
        </div>
        <div>
          <p className="kpi-label">Выбрано</p>
          <p className="kpi-value">{selected.length}</p>
        </div>
        <div>
          <p className="kpi-label">Лидер</p>
          <p className="kpi-value" style={{ fontSize: 20 }}>
            {winner?.reference ?? "—"}
          </p>
        </div>
        <div>
          <p className="kpi-label">Балл лидера</p>
          <p className="kpi-value">{winner ? winner.score : "—"}</p>
        </div>
      </div>

      <section className="card table-card" style={{ marginBottom: 16 }}>
        <div className="docs-header-row" style={{ marginBottom: 12 }}>
          <div>
            <h3 style={{ margin: 0 }}>Участники сравнения</h3>
            <p className="muted" style={{ margin: "4px 0 0" }}>
              Отметьте перевозки в таблице — как на остальных вкладках
            </p>
          </div>
          <button type="button" className="btn ghost" onClick={selectAll} disabled={all.length < 2}>
            Выбрать все
          </button>
        </div>
        <table className="shipment-table">
          <thead>
            <tr>
              <th style={{ width: 48 }} />
              <th>Груз</th>
              <th>Маршрут</th>
              <th>Этап</th>
              <th>Риск</th>
              <th>Задержка</th>
            </tr>
          </thead>
          <tbody>
            {all.map((s) => {
              const on = selected.includes(s.id);
              return (
                <tr
                  key={s.id}
                  className={on ? "compare-row-on" : undefined}
                  onClick={() => toggle(s.id)}
                  style={{ cursor: "pointer" }}
                >
                  <td onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={on}
                      onChange={() => toggle(s.id)}
                      aria-label={`Выбрать ${s.reference}`}
                    />
                  </td>
                  <td>
                    <strong>{s.reference}</strong>
                  </td>
                  <td>{s.route_label}</td>
                  <td>{s.current_stage}</td>
                  <td>{s.risk_level}</td>
                  <td>{s.delay_hours ? `+${s.delay_hours} ч` : "по плану"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {selected.length < 2 && (
          <p className="muted" style={{ marginTop: 12, marginBottom: 0 }}>
            Отметьте минимум две перевозки, чтобы построить рейтинг.
          </p>
        )}
      </section>

      {error && <p className="error">{error}</p>}
      {loading && <p className="muted">Считаем сравнение…</p>}

      {data && data.columns.length >= 2 && (
        <>
          <div className="grid-map" style={{ marginBottom: 16 }}>
            <section className="card">
              <h3 style={{ marginTop: 0 }}>Рейтинг</h3>
              <table className="shipment-table">
                <thead>
                  <tr>
                    <th>Место</th>
                    <th>Груз</th>
                    <th>Балл</th>
                  </tr>
                </thead>
                <tbody>
                  {data.ranking.map((r) => (
                    <tr
                      key={r.shipment_id}
                      onClick={() => navigate(`/shipments/${r.shipment_id}`)}
                      className={r.shipment_id === data.winner_id ? "compare-row-on" : undefined}
                    >
                      <td>#{r.rank}</td>
                      <td>
                        <Link to={`/shipments/${r.shipment_id}`} onClick={(e) => e.stopPropagation()}>
                          {r.reference}
                        </Link>
                      </td>
                      <td>{r.score}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </section>
            <section className="card attention-card">
              <h3 style={{ marginTop: 0 }}>Выводы</h3>
              {data.insights.map((i) => (
                <div key={i.code} style={{ marginBottom: 14 }}>
                  <strong>{i.title}</strong>
                  <p className="muted" style={{ margin: "4px 0 0" }}>
                    {i.detail}
                  </p>
                </div>
              ))}
            </section>
          </div>

          <section className="card table-card">
            <h3 style={{ marginTop: 0 }}>Матрица показателей</h3>
            <div className="compare-scroll">
              <table className="shipment-table compare-matrix">
                <thead>
                  <tr>
                    <th>Показатель</th>
                    {data.columns.map((c) => (
                      <th
                        key={c.shipment_id}
                        className={c.shipment_id === data.winner_id ? "compare-col-best" : undefined}
                      >
                        <Link to={`/shipments/${c.shipment_id}`}>{c.reference}</Link>
                        <div className="muted" style={{ fontWeight: 500, fontSize: 12 }}>
                          #{c.rank} · {c.score}/100
                        </div>
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {metricRows.map((row) => (
                    <tr key={row.key}>
                      <td className="compare-metric-label">{row.label}</td>
                      {data.columns.map((c) => (
                        <td
                          key={`${c.shipment_id}-${row.key}`}
                          className={
                            row.key === "score" && c.shipment_id === data.winner_id
                              ? "compare-col-best"
                              : undefined
                          }
                        >
                          {row.format(c)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
          <p className="footer-note">{data.disclaimer}</p>
        </>
      )}
    </Layout>
  );
}
