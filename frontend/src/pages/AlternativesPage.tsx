import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, type Alternative } from "../api";
import { Layout } from "../components/Layout";

const ROWS: Array<{ key: keyof Alternative | "params"; label: string }> = [
  { key: "eta_label", label: "Прогноз прибытия" },
  { key: "delay_label", label: "Отклонение от плана" },
  { key: "duration_label", label: "Продолжительность¹" },
  { key: "cost_label", label: "Стоимость" },
  { key: "transfers", label: "Перегрузки" },
  { key: "co2e_label", label: "Оценка CO₂e" },
  { key: "constraints", label: "Ограничения" },
  { key: "availability", label: "Доступность" },
];

export function AlternativesPage() {
  const { id = "" } = useParams();
  const navigate = useNavigate();
  const [alts, setAlts] = useState<Alternative[]>([]);
  const [meta, setMeta] = useState<{
    reference: string;
    route_label: string;
    insight: { title: string; detail: string };
    footnote: string;
  } | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .alternatives(id)
      .then((r) => {
        setAlts(r.alternatives);
        setMeta({
          reference: r.reference,
          route_label: r.route_label,
          insight: r.insight,
          footnote: r.footnote,
        });
      })
      .catch((e: Error) => setError(e.message));
  }, [id]);

  const onSelect = async (alt: Alternative) => {
    if (!alt.feasible || alt.is_current) return;
    setBusy(true);
    try {
      await api.selectAlternative(id, alt.id);
      navigate(`/shipments/${id}`);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (!meta && !error) {
    return (
      <Layout title="Перевозки">
        <p className="muted">Загрузка…</p>
      </Layout>
    );
  }

  return (
    <Layout title="Перевозки">
      <p className="crumb">
        <Link to="/">Перевозки</Link>
        {"  /  "}
        <Link to={`/shipments/${id}`}>{meta?.reference ?? "…"}</Link>
        {"  /  Альтернативы"}
      </p>
      <h1 className="page-title">Сравнение маршрутов</h1>
      <p className="page-sub">
        {meta?.route_label} · доставка до склада получателя · МСК (UTC+3)
      </p>

      {meta?.insight && (
        <div className="insight">
          <h3>{meta.insight.title}</h3>
          <p>{meta.insight.detail}</p>
        </div>
      )}

      <div className="compare">
        <div className="compare-col">
          <div className="compare-cell head">
            <h3>Параметры</h3>
            <p>Расчёт по текущему сценарию</p>
          </div>
          {ROWS.map((r) => (
            <div className="compare-cell label" key={r.label}>
              {r.label}
            </div>
          ))}
          <div className="compare-cell">
            <span className="footer-note">Расчёт 12 ноя, 10:42</span>
          </div>
        </div>

        {alts.map((alt) => (
          <div
            className={`compare-col ${alt.recommended ? "recommended" : ""}`}
            key={alt.id}
          >
            <div className="compare-cell head">
              <h3>{alt.title}</h3>
              <p>{alt.subtitle}</p>
            </div>
            {ROWS.map((r) => (
              <div className="compare-cell" key={`${alt.id}-${r.label}`}>
                {r.key === "transfers" ? alt.transfers : (alt[r.key] as string)}
              </div>
            ))}
            <div className="compare-cell">
              <button
                type="button"
                className={`btn ${
                  alt.recommended ? "" : alt.feasible && !alt.is_current ? "ghost" : "muted"
                }`}
                style={{ width: "100%" }}
                disabled={busy || !alt.feasible || alt.is_current}
                onClick={() => onSelect(alt)}
              >
                {alt.action_label}
              </button>
            </div>
          </div>
        ))}
      </div>

      {error && <p className="error">{error}</p>}
      <p className="footer-note">{meta?.footnote}</p>
      <p className="footer-note">
        Альтернативы коридора · время МСК (UTC+3)
      </p>
    </Layout>
  );
}
