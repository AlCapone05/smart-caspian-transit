import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type AnalyticsDashboard } from "../api";
import { Layout } from "../components/Layout";
import { delayLabel, fmtMsk } from "../format";

export function AnalyticsPage() {
  const [data, setData] = useState<AnalyticsDashboard | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api.analytics().then(setData).catch((e: Error) => setError(e.message));
  }, []);

  if (!data && !error) {
    return (
      <Layout title="Аналитика">
        <p className="muted">Загрузка…</p>
      </Layout>
    );
  }

  if (!data) {
    return (
      <Layout title="Аналитика">
        <p className="error">{error}</p>
      </Layout>
    );
  }

  const { kpis, model } = data;

  return (
    <Layout title="Аналитика">
      <h1 className="page-title">{data.title}</h1>
      <p className="page-sub">{data.subtitle}</p>

      <div className="kpi-row">
        <div>
          <p className="kpi-label">Перевозок в выборке</p>
          <p className="kpi-value">{kpis.shipments}</p>
        </div>
        <div>
          <p className="kpi-label">С задержкой</p>
          <p className="kpi-value">{kpis.delayed}</p>
        </div>
        <div>
          <p className="kpi-label">Средняя задержка</p>
          <p className="kpi-value">{kpis.avg_delay_hours} ч</p>
        </div>
        <div>
          <p className="kpi-label">CO₂e суммарно</p>
          <p className="kpi-value">{kpis.co2e_tonnes.toFixed(2).replace(".", ",")} т</p>
        </div>
      </div>

      <div className="grid-map">
        <section className="card">
          <h3 style={{ marginTop: 0 }}>Качество прогноза</h3>
          <p className="muted">{model.note}</p>
          <div className="kpi-row" style={{ marginTop: 16, padding: 0, border: "none" }}>
            <div>
              <p className="kpi-label">MAE median</p>
              <p className="kpi-value">{model.mae_hours.median ?? "—"} ч</p>
            </div>
            <div>
              <p className="kpi-label">MAE catboost</p>
              <p className="kpi-value">{model.mae_hours.catboost ?? "—"} ч</p>
            </div>
            <div>
              <p className="kpi-label">Split</p>
              <p className="kpi-value" style={{ fontSize: 16 }}>
                {model.split}
              </p>
            </div>
            <div>
              <p className="kpi-label">Стоимость выборки</p>
              <p className="kpi-value" style={{ fontSize: 18 }}>
                {Math.round(kpis.cost_rub).toLocaleString("ru-RU")} ₽
              </p>
            </div>
          </div>
        </section>
        <section className="card">
          <h3 style={{ marginTop: 0 }}>Под риском</h3>
          <p className="kpi-value">{kpis.at_risk}</p>
          <p className="muted">high + medium по текущему коридору</p>
        </section>
      </div>

      <section className="card table-card">
        <h3 style={{ marginTop: 0 }}>Перевозки в аналитике</h3>
        <table className="shipment-table">
          <thead>
            <tr>
              <th>Груз</th>
              <th>Маршрут</th>
              <th>Прогноз</th>
              <th>Задержка</th>
              <th>Риск</th>
            </tr>
          </thead>
          <tbody>
            {data.shipments.map((s) => (
              <tr key={s.id} onClick={() => navigate(`/shipments/${s.id}`)}>
                <td>{s.reference}</td>
                <td>{s.route_label}</td>
                <td>{fmtMsk(s.predicted_eta)}</td>
                <td>{delayLabel(s.delay_hours)}</td>
                <td>{s.risk_level}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
      <p className="footer-note">{data.disclaimer}</p>
    </Layout>
  );
}
