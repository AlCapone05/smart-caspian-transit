import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, type AppSettings } from "./api";
import { setDisplayTimezone } from "./format";

type SettingsCtx = {
  settings: AppSettings | null;
  loading: boolean;
  refresh: () => Promise<void>;
  save: (patch: Partial<AppSettings>) => Promise<AppSettings>;
};

const Ctx = createContext<SettingsCtx | null>(null);

const FALLBACK: AppSettings = {
  display_timezone: "Europe/Moscow",
  locale: "ru-RU",
  notifications_enabled: true,
  demo_mode: false,
  api_key_hint: "demo-key",
  default_scenario: "storm",
  co2_uncertainty_pct: 20,
  operator_name: "Адам Табиев",
  operator_role: "Логист · Каспий",
  disclaimer: "",
};

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      const s = await api.settings();
      setSettings(s);
      setDisplayTimezone(s.display_timezone);
    } catch {
      setSettings(FALLBACK);
      setDisplayTimezone(FALLBACK.display_timezone);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const save = useCallback(async (patch: Partial<AppSettings>) => {
    const next = await api.updateSettings(patch);
    setSettings(next);
    setDisplayTimezone(next.display_timezone);
    window.dispatchEvent(new CustomEvent("sct:settings", { detail: next }));
    return next;
  }, []);

  const value = useMemo(
    () => ({ settings: settings ?? FALLBACK, loading, refresh, save }),
    [settings, loading, refresh, save]
  );

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useSettings() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useSettings outside provider");
  return ctx;
}
