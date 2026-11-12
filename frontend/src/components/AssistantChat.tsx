import { useEffect, useRef, useState, type FormEvent, type KeyboardEvent } from "react";
import { api } from "../api";

type Msg = {
  id: string;
  role: "user" | "assistant";
  text: string;
  refused?: boolean;
  streaming?: boolean;
};

const SUGGESTIONS = [
  "Что с SCT-2048?",
  "Где сейчас штормы?",
  "Как выбрать обход маршрута?",
  "Какие суда на карте?",
  "Что с документами?",
  "Как сравнить грузы?",
];

const WELCOME: Msg = {
  id: "welcome",
  role: "assistant",
  text:
    "Поддержка МОГГНИТ (DeepSeek). Отвечаю только по Smart Caspian Transit. Выберите вопрос ниже или напишите свой.",
};

function TypingDots() {
  return (
    <div className="sct-typing" aria-label="Печатает">
      <span />
      <span />
      <span />
    </div>
  );
}

export function AssistantChat() {
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [typing, setTyping] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([WELCOME]);
  const listRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const typeTimer = useRef<number | null>(null);

  const showSuggestions = messages.length <= 1 && !busy && !typing;

  useEffect(() => {
    if (!open) return;
    const t = window.setTimeout(() => inputRef.current?.focus(), 50);
    return () => window.clearTimeout(t);
  }, [open]);

  useEffect(() => {
    if (!listRef.current) return;
    listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [messages, open, busy, typing]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open]);

  useEffect(() => {
    return () => {
      if (typeTimer.current) window.clearInterval(typeTimer.current);
    };
  }, []);

  const typeOut = (full: string, refused?: boolean) =>
    new Promise<void>((resolve) => {
      const id = `a_${Date.now()}`;
      setTyping(false);
      setMessages((prev) => [...prev, { id, role: "assistant", text: "", refused, streaming: true }]);
      let i = 0;
      const step = Math.max(1, Math.ceil(full.length / 90));
      if (typeTimer.current) window.clearInterval(typeTimer.current);
      typeTimer.current = window.setInterval(() => {
        i = Math.min(full.length, i + step);
        const slice = full.slice(0, i);
        setMessages((prev) =>
          prev.map((m) => (m.id === id ? { ...m, text: slice, streaming: i < full.length } : m))
        );
        if (i >= full.length) {
          if (typeTimer.current) window.clearInterval(typeTimer.current);
          typeTimer.current = null;
          setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, streaming: false } : m)));
          resolve();
        }
      }, 22);
    });

  const ask = async (raw: string) => {
    const text = raw.trim();
    if (!text || busy) return;
    const userMsg: Msg = { id: `u_${Date.now()}`, role: "user", text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setBusy(true);
    setTyping(true);
    try {
      const history = [...messages, userMsg]
        .filter((m) => m.id !== "welcome")
        .slice(-8)
        .map((m) => ({ role: m.role, content: m.text }));
      const res = await api.assistantChat(text, history);
      await typeOut(res.reply, res.refused);
    } catch (err) {
      setTyping(false);
      await typeOut(`Не удалось связаться с ассистентом: ${(err as Error).message}`, true);
    } finally {
      setBusy(false);
      setTyping(false);
    }
  };

  const send = async (e?: FormEvent) => {
    e?.preventDefault();
    await ask(input);
  };

  const onKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      void ask(input);
    }
  };

  return (
    <div className="sct-assistant">
      {open && (
        <div className="sct-assistant-panel" role="dialog" aria-label="Чат поддержки МОГГНИТ">
          <div className="sct-assistant-head">
            <div>
              <strong>Поддержка МОГГНИТ</strong>
              <p>DeepSeek · только вопросы по проекту</p>
            </div>
            <button type="button" className="btn ghost" onClick={() => setOpen(false)}>
              ✕
            </button>
          </div>
          <div className="sct-assistant-list" ref={listRef}>
            {messages.map((m) => (
              <div
                key={m.id}
                className={`sct-assistant-msg ${m.role}${m.refused ? " refused" : ""}${m.streaming ? " streaming" : ""}`}
              >
                {m.text}
                {m.streaming ? <span className="sct-caret">▍</span> : null}
              </div>
            ))}
            {showSuggestions && (
              <div className="sct-assistant-suggestions">
                <p className="sct-assistant-suggestions-label">Предложенные вопросы</p>
                <div className="sct-assistant-chips">
                  {SUGGESTIONS.map((q) => (
                    <button
                      key={q}
                      type="button"
                      className="sct-assistant-chip"
                      disabled={busy}
                      onClick={() => void ask(q)}
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            )}
            {typing && (
              <div className="sct-assistant-msg assistant typing-bubble">
                <TypingDots />
              </div>
            )}
          </div>
          <form className="sct-assistant-form" onSubmit={send}>
            <textarea
              ref={inputRef}
              rows={3}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="Вопрос по перевозкам, штормам, документам…"
              disabled={busy}
            />
            <button type="submit" className="btn" disabled={busy || !input.trim()}>
              Отправить
            </button>
          </form>
        </div>
      )}
      <button
        type="button"
        className={`sct-assistant-fab ${open ? "open" : ""}`}
        aria-label={open ? "Закрыть чат поддержки" : "Открыть чат поддержки"}
        title="Поддержка МОГГНИТ"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? (
          <span className="sct-fab-x" aria-hidden>
            ✕
          </span>
        ) : (
          <svg
            className="sct-fab-support"
            viewBox="0 0 24 24"
            width="26"
            height="26"
            aria-hidden
          >
            <path
              fill="currentColor"
              d="M12 2a8 8 0 0 0-8 8v2.5A2.5 2.5 0 0 0 6.5 15H7v-3a5 5 0 0 1 10 0v3h.5a2.5 2.5 0 0 0 2.5-2.5V10a8 8 0 0 0-8-8zm-3 11v3a3 3 0 0 0 3 3h1v2h-1a5 5 0 0 1-5-5v-3h2zm8 0h2v3a5 5 0 0 1-5 5h-1v-2h1a3 3 0 0 0 3-3v-3z"
            />
          </svg>
        )}
      </button>
    </div>
  );
}
