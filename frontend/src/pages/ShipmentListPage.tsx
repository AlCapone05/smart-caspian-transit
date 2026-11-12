import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, type ShipmentSummary } from "../api";

function fmt(iso: string | null) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("ru-RU", { timeZone: "UTC" }) + " UTC";
}

export function ShipmentListPage() {
  const [items, setItems] = useState<ShipmentSummary[]>([]);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    api
      .listShipments()
      .then((r) => setItems(r.items))
      .catch((e: Error) => setError(e.message));
  }, []);

  return (
    <section className="panel">
      <h2>Перевозки</h2>
      <p className="muted">
        Статусы, риски и ETA по текущим перевозкам коридора.
      </p>
      {error && <p className="error">{error}</p>}
      <table className="shipment-table">
        <thead>
          <tr>
            <th>Референс</th>
            <th>Груз</th>
            <th>Статус</th>
            <th>Риск</th>
            <th>План ETA</th>
            <th>Прогноз ETA</th>
            <th>Задержка</th>
          </tr>
        </thead>
        <tbody>
          {items.map((s) => (
            <tr key={s.id} onClick={() => navigate(`/shipments/${s.id}`)}>
              <td>{s.reference}</td>
              <td>{s.cargo_description}</td>
              <td>{s.status}</td>
              <td>
                <span className={`pill ${s.risk_level}`}>{s.risk_level}</span>
              </td>
              <td>{fmt(s.planned_eta)}</td>
              <td>{fmt(s.predicted_eta)}</td>
              <td>{s.delay_hours.toFixed(1)} ч</td>
            </tr>
          ))}
        </tbody>
      </table>
    </section>
  );
}
