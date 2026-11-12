import { useEffect, useState, type ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { api } from "../api";
import { AssistantChat } from "./AssistantChat";
import { fmtMsk, tzShort } from "../format";
import { useSettings } from "../settings";

const NAV = [
  { to: "/", label: "Обзор", match: (p: string) => p === "/" },
  {
    to: "/shipments",
    label: "Перевозки",
    match: (p: string) => p.startsWith("/shipments"),
  },
  {
    to: "/documents",
    label: "Документы",
    match: (p: string) => p.startsWith("/documents"),
  },
  {
    to: "/compare",
    label: "Сравнение",
    match: (p: string) => p.startsWith("/compare"),
  },
  {
    to: "/analytics",
    label: "Аналитика",
    match: (p: string) => p.startsWith("/analytics"),
  },
];

type Notif = {
  id: string;
  shipment_id: string;
  reference: string;
  title: string;
  detail: string;
  kind: string;
  created_label: string;
};

export function Layout({
  title,
  children,
  search,
  onSearch,
}: {
  title: string;
  children: ReactNode;
  search?: string;
  onSearch?: (v: string) => void;
}) {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { settings } = useSettings();
  const now = fmtMsk(new Date().toISOString());
  const [notifs, setNotifs] = useState<Notif[]>([]);
  const [notifOpen, setNotifOpen] = useState(false);
  const [notifHint, setNotifHint] = useState("");
  const [navOpen, setNavOpen] = useState(false);

  const loadNotifs = () => {
    api
      .notifications()
      .then((r) => {
        setNotifs(r.items);
        setNotifHint(r.enabled ? r.disclaimer : r.disclaimer);
      })
      .catch(() => setNotifs([]));
  };

  useEffect(() => {
    loadNotifs();
    const onSettings = () => loadNotifs();
    window.addEventListener("sct:settings", onSettings);
    return () => window.removeEventListener("sct:settings", onSettings);
  }, []);

  useEffect(() => {
    setNavOpen(false);
    setNotifOpen(false);
  }, [pathname]);

  useEffect(() => {
    if (!navOpen && !notifOpen) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      if (notifOpen) setNotifOpen(false);
      if (navOpen) setNavOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [navOpen, notifOpen]);

  useEffect(() => {
    if (!navOpen && !notifOpen) return;
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, [navOpen, notifOpen]);

  const initials = settings.operator_name
    .split(" ")
    .filter(Boolean)
    .map((p) => p[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

  return (
    <div className={`app ${navOpen ? "nav-open" : ""}`}>
      <button
        type="button"
        className="nav-toggle"
        aria-label={navOpen ? "Закрыть меню" : "Открыть меню"}
        aria-expanded={navOpen}
        onClick={() => setNavOpen((v) => !v)}
      >
        <span className="nav-toggle-bars" aria-hidden>
          <i />
          <i />
          <i />
        </span>
      </button>

      <div
        className={`sidebar-backdrop ${navOpen ? "show" : ""}`}
        onClick={() => setNavOpen(false)}
        aria-hidden
      />

      <aside className={`sidebar ${navOpen ? "is-open" : ""}`}>
        <div className="brand">
          <img
            className="brand-logo"
            src="/moggnit-logo.jpg"
            alt="МОГГНИТ · Smart Caspian Transit"
          />
        </div>
        {settings.demo_mode && (
          <p className="footer-note" style={{ margin: "0 8px 8px" }}>
            Режим разработки
          </p>
        )}
        <nav className="sidebar-nav" aria-label="Основная навигация">
          {NAV.map((item) => (
            <Link
              key={item.label}
              to={item.to}
              className={`nav-item ${item.match(pathname) ? "active" : ""}`}
              onClick={() => setNavOpen(false)}
            >
              {item.label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-spacer" />
        <Link
          to="/settings"
          className={`nav-item ${pathname.startsWith("/settings") ? "active" : ""}`}
          onClick={() => setNavOpen(false)}
        >
          Настройки
        </Link>
        <div className="sidebar-user">
          <strong>
            {initials} &nbsp; {settings.operator_name}
          </strong>
          <span>{settings.operator_role}</span>
        </div>
      </aside>
      <div className="main">
        <header className="topbar">
          <div className="topbar-lead">
            <h2 className="topbar-title">{title}</h2>
          </div>
          <input
            className="search"
            placeholder="Поиск: SCT, контейнер, маршрут…"
            value={search ?? ""}
            onChange={(e) => onSearch?.(e.target.value)}
            disabled={!onSearch}
            title={onSearch ? "Поиск по списку на странице" : "Поиск доступен на Обзоре и Перевозках"}
          />
          <div className="topbar-meta">
            <span className="topbar-clock">
              ↻ &nbsp; {now} {tzShort()}
            </span>
            <div className="notif-wrap">
              <button
                type="button"
                className={`btn ghost notif-btn ${notifOpen ? "selected" : ""}`}
                aria-expanded={notifOpen}
                aria-haspopup="dialog"
                onClick={() => {
                  setNotifOpen((v) => !v);
                  if (!notifOpen) loadNotifs();
                }}
              >
                <span className="notif-btn-full">
                  Уведомления · {settings.notifications_enabled ? notifs.length : 0}
                </span>
                <span className="notif-btn-short">
                  ✉ {settings.notifications_enabled ? notifs.length : 0}
                </span>
              </button>
            </div>
          </div>
        </header>
        <div className="content" key={pathname}>
          {children}
        </div>
      </div>
      {notifOpen && (
        <>
          <div
            className="notif-backdrop"
            onClick={() => setNotifOpen(false)}
            aria-hidden
          />
          <div className="notif-panel" role="dialog" aria-label="Уведомления">
            <div className="notif-panel-head">
              <strong>Уведомления</strong>
              <button type="button" className="btn ghost" onClick={() => setNotifOpen(false)}>
                Закрыть
              </button>
            </div>
            {!settings.notifications_enabled && (
              <p className="muted">
                Выключены в настройках.{" "}
                <Link to="/settings" onClick={() => setNotifOpen(false)}>
                  Включить
                </Link>
              </p>
            )}
            {settings.notifications_enabled && notifs.length === 0 && (
              <p className="muted">Пока нет событий.</p>
            )}
            {notifs.map((n) => (
              <button
                key={n.id}
                type="button"
                className="notif-item"
                onClick={() => {
                  setNotifOpen(false);
                  if (n.kind === "docs") {
                    navigate(`/documents?shipment=${n.shipment_id}`);
                  } else if (n.kind === "weather") {
                    navigate("/");
                  } else {
                    navigate(`/shipments/${n.shipment_id}`);
                  }
                }}
              >
                <span className="notif-time">{n.created_label}</span>
                <strong>{n.title}</strong>
                <span className="muted">{n.detail}</span>
              </button>
            ))}
            {notifHint ? <p className="footer-note">{notifHint}</p> : null}
          </div>
        </>
      )}
      <AssistantChat />
    </div>
  );
}
