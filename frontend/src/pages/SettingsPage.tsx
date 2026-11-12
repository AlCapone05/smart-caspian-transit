import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { type AppSettings } from "../api";
import { Layout } from "../components/Layout";
import { fmtMsk, tzShort } from "../format";
import { useSettings } from "../settings";

export function SettingsPage() {
  const { settings: live, save, refresh } = useSettings();
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setSettings(live);
  }, [live]);

  const onSave = async () => {
    if (!settings) return;
    setSaved(false);
    setError(null);
    try {
      const next = await save({
        display_timezone: settings.display_timezone,
        notifications_enabled: settings.notifications_enabled,
        demo_mode: settings.demo_mode,
        default_scenario: settings.default_scenario,
        co2_uncertainty_pct: settings.co2_uncertainty_pct,
        operator_name: settings.operator_name,
        operator_role: settings.operator_role,
        locale: settings.locale,
      });
      setSettings(next);
      setSaved(true);
      await refresh();
    } catch (e) {
      setError((e as Error).message);
    }
  };

  if (!settings) {
    return (
      <Layout title="Настройки">
        <p className="muted">Загрузка…</p>
      </Layout>
    );
  }

  const scenarioLabel =
    settings.default_scenario === "storm"
      ? "Шторм"
      : settings.default_scenario === "port_congestion"
        ? "Перегрузка порта"
        : "Обычные условия";

  return (
    <Layout title="Настройки">
      <h1 className="page-title">Настройки</h1>
      <p className="page-sub">Параметры влияют на диспетчерскую прямо сейчас</p>

      <div className="info-banner">
        <strong>ⓘ Что меняют настройки</strong>
        <p>
          Часовой пояс — все даты в UI. Уведомления — панель в шапке. Сценарий по умолчанию —
          стартовый пресет на карточке груза. Имя/роль — сайдбар. CO₂e % — подпись на карточке.
          Режим разработки — служебная метка в интерфейсе (для презентации выключен).
        </p>
      </div>

      <section className="card settings-effects">
        <h3 style={{ marginTop: 0 }}>Сейчас применено</h3>
        <ul>
          <li>
            Время: <strong>{fmtMsk(new Date().toISOString(), true)}</strong> ({tzShort()})
          </li>
          <li>
            Уведомления:{" "}
            <strong>{settings.notifications_enabled ? "включены" : "выключены"}</strong>
          </li>
          <li>
            Сценарий по умолчанию: <strong>{scenarioLabel}</strong>
          </li>
          <li>
            Оператор:{" "}
            <strong>
              {settings.operator_name} · {settings.operator_role}
            </strong>
          </li>
          <li>
            CO₂e неопределённость: <strong>±{settings.co2_uncertainty_pct}%</strong>
          </li>
          <li>
            Режим разработки: <strong>{settings.demo_mode ? "вкл" : "выкл"}</strong>
          </li>
        </ul>
        <p className="muted">
          Проверьте:{" "}
          <Link to="/">Обзор</Link> · <Link to="/shipments/shp_sct_2048">Карточка SCT-2048</Link>
        </p>
      </section>

      <section className="card settings-grid">
        <label>
          Часовой пояс отображения
          <select
            className="search"
            style={{ width: "100%" }}
            value={settings.display_timezone}
            onChange={(e) => setSettings({ ...settings, display_timezone: e.target.value })}
          >
            <option value="Europe/Moscow">Europe/Moscow (МСК)</option>
            <option value="Asia/Tehran">Asia/Tehran</option>
            <option value="UTC">UTC</option>
          </select>
        </label>

        <label>
          Сценарий по умолчанию
          <select
            className="search"
            style={{ width: "100%" }}
            value={settings.default_scenario}
            onChange={(e) => setSettings({ ...settings, default_scenario: e.target.value })}
          >
            <option value="normal">Обычные условия</option>
            <option value="storm">Шторм</option>
            <option value="port_congestion">Перегрузка порта</option>
          </select>
        </label>

        <label>
          Имя оператора
          <input
            className="search"
            style={{ width: "100%" }}
            value={settings.operator_name}
            onChange={(e) => setSettings({ ...settings, operator_name: e.target.value })}
          />
        </label>

        <label>
          Роль
          <input
            className="search"
            style={{ width: "100%" }}
            value={settings.operator_role}
            onChange={(e) => setSettings({ ...settings, operator_role: e.target.value })}
          />
        </label>

        <label>
          Неопределённость CO₂e, %
          <input
            className="search"
            style={{ width: "100%" }}
            type="number"
            min={0}
            max={50}
            value={settings.co2_uncertainty_pct}
            onChange={(e) =>
              setSettings({ ...settings, co2_uncertainty_pct: Number(e.target.value) })
            }
          />
        </label>

        <label className="check-row">
          <input
            type="checkbox"
            checked={settings.notifications_enabled}
            onChange={(e) =>
              setSettings({ ...settings, notifications_enabled: e.target.checked })
            }
          />
          Уведомления включены
        </label>

        <label className="check-row">
          <input
            type="checkbox"
            checked={settings.demo_mode}
            onChange={(e) => setSettings({ ...settings, demo_mode: e.target.checked })}
          />
          Режим разработки (метка в UI)
        </label>

        <div>
          <p className="kpi-label">API key (подсказка)</p>
          <p className="muted">{settings.api_key_hint}</p>
        </div>
      </section>

      <div className="actions" style={{ display: "flex", gap: 12, alignItems: "center" }}>
        <button type="button" className="btn" onClick={onSave}>
          Сохранить
        </button>
        {saved && <span className="map-selected">Сохранено и применено</span>}
      </div>
      {error && <p className="error">{error}</p>}
      <p className="footer-note">{settings.disclaimer}</p>
    </Layout>
  );
}
