import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, type DocumentsWorkspace } from "../api";
import { Layout } from "../components/Layout";
import { fmtMsk } from "../format";

type RegistryItem = {
  shipment_id: string;
  reference: string;
  route_label: string;
  completeness_label: string;
  issues: number;
  attention: boolean;
};

type HistoryRow = {
  id?: string;
  status: string;
  note: string;
  changed_at?: string;
  changed_label?: string;
  actor: string;
  document_title?: string;
};

export function DocumentsPage() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const [registry, setRegistry] = useState<RegistryItem[]>([]);
  const [shipmentId, setShipmentId] = useState(params.get("shipment") || "");
  const [data, setData] = useState<DocumentsWorkspace | null>(null);
  const [hsCode, setHsCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [historyDoc, setHistoryDoc] = useState<string | null>(null);
  const [historyRows, setHistoryRows] = useState<HistoryRow[]>([]);
  const [preview, setPreview] = useState<DocumentsWorkspace["documents"][0] | null>(null);
  const [activeFixId, setActiveFixId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api
      .documentsRegistry()
      .then((r) => {
        setRegistry(r.items);
        const fromUrl = params.get("shipment");
        const next = fromUrl || r.default_shipment_id;
        setShipmentId(next);
        if (!fromUrl && next) {
          navigate(`/documents?shipment=${next}`, { replace: true });
        }
      })
      .catch((e: Error) => setError(e.message));
  }, []);

  const load = async (id: string) => {
    const d = await api.documentsWorkspace(id);
    setData(d);
  };

  useEffect(() => {
    if (!shipmentId) return;
    setError(null);
    load(shipmentId).catch((e: Error) => setError(e.message));
  }, [shipmentId]);

  const onSelectShipment = (id: string) => {
    setShipmentId(id);
    setMessage(null);
    setHistoryDoc(null);
    setHistoryRows([]);
    setPreview(null);
    setActiveFixId(null);
    navigate(`/documents?shipment=${id}`);
  };

  const onFix = async (documentId: string, field: string, documentType?: string) => {
    setError(null);
    setMessage(null);
    setBusy(true);
    try {
      if (field === "hs_code") {
        if (!/^\d{10}$/.test(hsCode.trim())) {
          throw new Error("Код ТН ВЭД должен состоять из 10 цифр");
        }
        await api.addDocument({
          shipment_id: shipmentId,
          document_id: documentId,
          document_type: documentType,
          hs_code: hsCode.trim(),
        });
        setMessage("Код ТН ВЭД сохранён (тест).");
        setHsCode("");
      } else {
        await api.addDocument({
          shipment_id: shipmentId,
          document_id: documentId,
          document_type: documentType,
          mark_file_added: true,
          file_name: `${documentType || "document"}_demo.pdf`,
        });
        setMessage("Файл добавлен в пакет документов.");
      }
      setActiveFixId(null);
      await load(shipmentId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  const loadHistory = async (docId: string, title: string) => {
    setHistoryDoc(docId);
    setMessage(null);
    try {
      const h = await api.documentHistory(docId);
      setHistoryRows(
        h.history.map((row) => ({
          ...row,
          changed_label: fmtMsk(row.changed_at),
          document_title: title,
        }))
      );
      document.getElementById("docs-history")?.scrollIntoView({ behavior: "smooth" });
    } catch (e) {
      // fallback to workspace history
      const local = data?.history.filter((x) => x.document_id === docId) ?? [];
      setHistoryRows(local);
      setError((e as Error).message);
      document.getElementById("docs-history")?.scrollIntoView({ behavior: "smooth" });
    }
  };

  const onAction = async (doc: DocumentsWorkspace["documents"][0]) => {
    setError(null);
    if (doc.action_label === "История") {
      await loadHistory(doc.id, doc.title);
      return;
    }
    if (doc.action_label === "Исправить") {
      setActiveFixId(doc.id);
      setPreview(null);
      document.getElementById("docs-fixes")?.scrollIntoView({ behavior: "smooth" });
      return;
    }
    if (doc.action_label === "Добавить файл") {
      await onFix(doc.id, "file", doc.document_type);
      return;
    }
    // Открыть
    setPreview(doc);
  };

  const onPrecheck = async () => {
    if (!data) return;
    setBusy(true);
    try {
      const r = await api.precheck(data.shipment_id);
      setMessage(r.message);
      if (r.ok) await load(shipmentId);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  if (!data && !error) {
    return (
      <Layout title="Документы">
        <p className="muted">Загрузка…</p>
      </Layout>
    );
  }

  if (!data) {
    return (
      <Layout title="Документы">
        <p className="error">{error}</p>
      </Layout>
    );
  }

  const visibleHistory =
    historyDoc && historyRows.length
      ? historyRows
      : historyDoc
        ? data.history.filter((h) => h.document_id === historyDoc)
        : data.history;

  return (
    <Layout title="Документы">
      <p className="crumb">
        Документы &nbsp;/&nbsp; <Link to={`/shipments/${data.shipment_id}`}>{data.reference}</Link>
      </p>
      <div className="docs-header-row">
        <div>
          <h1 className="page-title">Документы груза</h1>
          <p className="page-sub">
            {data.reference} · {data.route_label}
          </p>
        </div>
        <label className="docs-picker">
          Перевозка
          <select
            className="search"
            value={shipmentId}
            onChange={(e) => onSelectShipment(e.target.value)}
          >
            {registry.map((r) => (
              <option key={r.shipment_id} value={r.shipment_id}>
                {r.reference} · {r.completeness_label}
                {r.attention ? " · внимание" : ""}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="info-banner">
        <strong>{data.banner.title}</strong>
        <p>{data.banner.text}</p>
      </div>

      <section className="card docs-summary">
        <div>
          <p className="kpi-label">Комплектность пакета</p>
          <p className="kpi-value">{data.completeness_label}</p>
        </div>
        <div>
          <p className="kpi-label">Требует внимания</p>
          <p className="kpi-value">{data.attention_label}</p>
        </div>
        <button
          type="button"
          className={`btn ${data.can_submit_precheck ? "" : "muted"}`}
          disabled={!data.can_submit_precheck || busy}
          onClick={onPrecheck}
          style={{ minWidth: 280 }}
        >
          Отправить на предварительную проверку
        </button>
      </section>

      <section className="card">
        <table className="shipment-table docs-table">
          <thead>
            <tr>
              <th style={{ width: "32%" }}>Документ</th>
              <th style={{ width: "22%" }}>Статус</th>
              <th style={{ width: "24%" }}>Последнее изменение · МСК</th>
              <th style={{ width: "22%" }}>Действие</th>
            </tr>
          </thead>
          <tbody>
            {data.documents.map((d) => (
              <tr key={d.id} className={activeFixId === d.id ? "active" : ""}>
                <td>{d.title}</td>
                <td>
                  <span className={`status-chip ${d.status_tone}`}>{d.status_label}</span>
                </td>
                <td className="muted">{d.updated_label}</td>
                <td>
                  <button
                    type="button"
                    className="btn ghost"
                    disabled={busy}
                    onClick={() => onAction(d)}
                  >
                    {d.action_label}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <div className="docs-bottom">
        <section className="card" id="docs-fixes">
          <h3 style={{ marginTop: 0 }}>Что исправить</h3>
          {data.fixes.length === 0 && <p className="muted">Замечаний нет.</p>}
          {data.fixes.map((f) => (
            <div
              key={`${f.document_id}-${f.field}`}
              className={activeFixId === f.document_id ? "fix-active" : ""}
              style={{ marginBottom: 16 }}
            >
              <p style={{ fontWeight: 500 }}>{f.title}</p>
              {f.field === "hs_code" ? (
                <>
                  <input
                    className="search input-error"
                    style={{ width: "100%", maxWidth: 420, marginTop: 8 }}
                    placeholder={f.placeholder ?? ""}
                    value={activeFixId === f.document_id || !activeFixId ? hsCode : ""}
                    onChange={(e) => {
                      setActiveFixId(f.document_id);
                      setHsCode(e.target.value);
                    }}
                    onFocus={() => setActiveFixId(f.document_id)}
                  />
                  {f.error && <p className="field-error">{f.error}</p>}
                  <button
                    type="button"
                    className="btn"
                    style={{ marginTop: 12 }}
                    disabled={busy}
                    onClick={() => onFix(f.document_id, "hs_code", f.document_type)}
                  >
                    Сохранить код
                  </button>
                </>
              ) : (
                <button
                  type="button"
                  className="btn"
                  style={{ marginTop: 8 }}
                  disabled={busy}
                  onClick={() => onFix(f.document_id, "file", f.document_type)}
                >
                  Добавить PDF
                </button>
              )}
            </div>
          ))}
        </section>

        <section className="card" id="docs-history">
          <div className="docs-header-row" style={{ marginBottom: 8 }}>
            <h3 style={{ margin: 0 }}>История отправки</h3>
            {historyDoc && (
              <button
                type="button"
                className="btn ghost"
                onClick={() => {
                  setHistoryDoc(null);
                  setHistoryRows([]);
                }}
              >
                Показать все
              </button>
            )}
          </div>
          {visibleHistory.length === 0 && <p className="muted">История пуста.</p>}
          {visibleHistory.map((h, idx) => (
            <div key={`${h.document_title || h.status}-${idx}`} style={{ marginBottom: 12 }}>
              <p style={{ margin: 0 }}>
                {(h.changed_label || fmtMsk(h.changed_at)) + " · "}
                {h.note || h.status}
              </p>
              <p className="muted" style={{ margin: "4px 0 0", fontSize: 13 }}>
                {(h.document_title || "Документ") + " · " + h.actor}
              </p>
            </div>
          ))}
          {data.submit_hint && <p className="delay-amber">{data.submit_hint}</p>}
        </section>
      </div>

      {preview && (
        <div className="modal-backdrop" onClick={() => setPreview(null)}>
          <div className="modal-card" onClick={(e) => e.stopPropagation()}>
            <h3 style={{ marginTop: 0 }}>{preview.title}</h3>
            <p className="muted">Статус: {preview.status_label}</p>
            <p className="muted">Обновлён: {preview.updated_label}</p>
            <pre className="payload-view">
              {JSON.stringify(
                {
                  document_type: preview.document_type,
                  status: preview.status,
                  note: "Предпросмотр метаданных документа.",
                },
                null,
                2
              )}
            </pre>
            <div style={{ display: "flex", gap: 8, marginTop: 12 }}>
              <button type="button" className="btn" onClick={() => setPreview(null)}>
                Закрыть
              </button>
              <button
                type="button"
                className="btn ghost"
                onClick={() => {
                  setPreview(null);
                  void loadHistory(preview.id, preview.title);
                }}
              >
                История
              </button>
            </div>
          </div>
        </div>
      )}

      {message && <p className="info-banner">{message}</p>}
      {error && <p className="error">{error}</p>}
      <p className="footer-note">{data.disclaimer}</p>
    </Layout>
  );
}
