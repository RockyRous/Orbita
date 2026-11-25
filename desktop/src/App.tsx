import { Channel, invoke } from "@tauri-apps/api/core";
import { open } from "@tauri-apps/plugin-dialog";
import { useEffect, useState } from "react";
import type { ProjectionEnvelope, RuntimeState } from "./types";
import "./App.css";

type RootTurnResult = { threadId: string; turnId: string; status: string; assistantText?: string };
type ChatEntry = RootTurnResult & { userText: string };
type SupervisorSnapshot = { connection: "connected" | "disconnected"; activeThreadId?: string; activeTurnId?: string };

const initialRuntime: RuntimeState = {
  phase: "not_checked",
  message: "Codex App Server ещё не проверен",
};

function App() {
  const [runtime, setRuntime] = useState<RuntimeState>(initialRuntime);
  const [busy, setBusy] = useState(false);
  const [projectPath, setProjectPath] = useState("");
  const [instruction, setInstruction] = useState("");
  const [sentInstruction, setSentInstruction] = useState("");
  const [turn, setTurn] = useState<RootTurnResult | null>(null);
  const [history, setHistory] = useState<ChatEntry[]>([]);
  const [turnError, setTurnError] = useState<string | null>(null);
  const [interruptRequested, setInterruptRequested] = useState(false);

  useEffect(() => {
    if (runtime.phase !== "connected") return;
    const timer = window.setInterval(() => {
      invoke<SupervisorSnapshot>("get_projection").then((snapshot) => {
        if (snapshot.connection === "disconnected") {
          setRuntime({ phase: "unavailable", message: "Codex App Server завершился. Подключите его заново." });
          setInterruptRequested(false);
        }
      }).catch(() => undefined);
    }, 2000);
    return () => window.clearInterval(timer);
  }, [runtime.phase]);

  async function inspectRuntime() {
    setBusy(true);
    setRuntime({ phase: "checking", message: "Проверяем runtime…" });
    try { setRuntime(await invoke<RuntimeState>("inspect_runtime")); }
    catch { setRuntime({ phase: "unavailable", message: "Не удалось проверить runtime." }); }
    finally { setBusy(false); }
  }

  async function connectRuntime() {
    setBusy(true);
    setRuntime({ phase: "checking", message: "Подключаем Codex App Server…" });
    try { setRuntime(await invoke<RuntimeState>("connect_runtime")); }
    catch (error) { setRuntime({ phase: "unavailable", message: String(error) }); }
    finally { setBusy(false); }
  }

  async function startRootTask() {
    if (runtime.phase !== "connected") return;
    setBusy(true);
    setTurnError(null);
    setInterruptRequested(false);
    setTurn(null);
    setHistory([]);
    setSentInstruction(instruction.trim());
    let lastSequence = 0;
    const updates = new Channel<ProjectionEnvelope>((update) => {
      if (update.sequence <= lastSequence) return;
      lastSequence = update.sequence;
      setTurn((current) => {
        const next = current ?? { threadId: update.rootTaskId, turnId: "", status: "running", assistantText: "" };
        if (update.kind === "assistantDelta") return { ...next, assistantText: `${next.assistantText ?? ""}${update.text ?? ""}` };
        if (update.kind === "assistantMessage") return { ...next, assistantText: update.text ?? next.assistantText };
        if (update.kind === "turnCompleted") return { ...next, status: update.status ?? "unknown" };
        return next;
      });
    });
    try {
      const result = await invoke<RootTurnResult>("start_root_task", { projectPath, instruction, updates });
      setTurn(result);
      setHistory([{ ...result, userText: instruction.trim() }]);
    }
    catch (error) { setTurnError(String(error)); }
    finally { setBusy(false); }
  }

  async function sendFollowUp() {
    const threadId = history[history.length - 1]?.threadId;
    if (!threadId || runtime.phase !== "connected") return;
    setBusy(true);
    setTurnError(null);
    setInterruptRequested(false);
    setTurn(null);
    setSentInstruction(instruction.trim());
    let lastSequence = 0;
    const updates = new Channel<ProjectionEnvelope>((update) => {
      if (update.sequence <= lastSequence) return;
      lastSequence = update.sequence;
      setTurn((current) => {
        const next = current ?? { threadId: update.rootTaskId, turnId: "", status: "running", assistantText: "" };
        if (update.kind === "assistantDelta") return { ...next, assistantText: `${next.assistantText ?? ""}${update.text ?? ""}` };
        if (update.kind === "assistantMessage") return { ...next, assistantText: update.text ?? next.assistantText };
        if (update.kind === "turnCompleted") return { ...next, status: update.status ?? "unknown" };
        return next;
      });
    });
    try {
      const result = await invoke<RootTurnResult>("send_follow_up", { threadId, instruction, updates });
      setTurn(result);
      setHistory((items) => [...items, { ...result, userText: instruction.trim() }]);
    } catch (error) { setTurnError(String(error)); }
    finally { setBusy(false); }
  }

  async function requestInterrupt() {
    if (!busy || interruptRequested) return;
    try {
      await invoke("request_interrupt");
      setInterruptRequested(true);
    } catch (error) {
      setTurnError(String(error));
    }
  }

  async function chooseProject() {
    const selected = await open({ directory: true, multiple: false, title: "Выберите папку проекта" });
    if (typeof selected === "string") setProjectPath(selected);
  }

  const canSend = runtime.phase === "connected" && !busy && projectPath.trim() && instruction.trim();
  const canFollowUp = runtime.phase === "connected" && !busy && history.length > 0 && instruction.trim();

  return (
    <main className="shell">
      <aside className="sidebar" aria-label="Навигация">
        <div className="brand"><span className="brand-mark">O</span><span>Orbita</span></div>
        <button className="new-task" disabled>+ Новая задача</button>
        <section className="nav-section"><h2>РАБОЧАЯ ОБЛАСТЬ</h2><button className="nav-item active">Текущая задача <span>—</span></button><button className="nav-item">История <span>0</span></button></section>
        <section className="sidebar-bottom">
          <div className={`runtime runtime-${runtime.phase}`}><span className="status-dot" /><div><strong>Codex runtime</strong><small>{runtime.message}</small>{runtime.detectedVersion ? <small>Версия: {runtime.detectedVersion}</small> : null}</div></div>
          {runtime.phase === "compatible" ? <button className="link-button" onClick={connectRuntime} disabled={busy}>{busy ? "Подключение…" : "Подключить Codex"}</button> : <button className="link-button" onClick={inspectRuntime} disabled={busy}>{busy ? "Проверка…" : "Проверить runtime"}</button>}
        </section>
      </aside>
      <section className="chat-pane" aria-label="Чат Codex">
        <header className="topbar"><div><p className="eyebrow">ПРОЕКТ НЕ ВЫБРАН</p><h1>Новая задача</h1></div><div className="topbar-actions"><span className="badge">{interruptRequested ? "Запрос на прерывание отправлен" : busy ? "Активный turn" : "Нет активного turn"}</span><button onClick={requestInterrupt} disabled={!busy || interruptRequested}>{interruptRequested ? "Ожидание…" : "Прервать"}</button></div></header>
        {turn || history.length > 0 ? <div className="chat-transcript" aria-live="polite">
          {history.map((entry) => <div key={entry.turnId}>
            <article className="chat-message user-message"><span>Вы</span><p>{entry.userText}</p></article>
            <article className="chat-message assistant-message"><span>Codex • {entry.status}</span><p>{entry.assistantText || "Ответ агента не был доступен."}</p></article>
          </div>)}
          {busy && turn ? <div>
            <article className="chat-message user-message"><span>Вы</span><p>{sentInstruction}</p></article>
            <article className="chat-message assistant-message"><span>Codex {turn.status === "running" ? "печатает…" : `• ${turn.status}`}</span><p>{turn.assistantText || "Ответ готовится…"}</p></article>
          </div> : null}
        </div> : <div className="chat-empty">
          <div className="empty-symbol">✦</div><h2>Начните работу с Codex</h2>
          <p>{runtime.phase === "connected" ? "Codex подключён. Первый turn выполнится безопасно: read-only, без approvals." : "Сначала проверьте и подключите Codex runtime."}</p>
          {turnError ? <p className="honesty">{turnError}</p> : null}
        </div>}
        <form className="composer" onSubmit={(event) => { event.preventDefault(); history.length > 0 ? sendFollowUp() : startRootTask(); }}>
          <div className="project-selector">
            <input className="project-path" value={projectPath} onChange={(event) => setProjectPath(event.currentTarget.value)} disabled={runtime.phase !== "connected" || busy || history.length > 0} aria-label="Папка проекта" placeholder="Выберите папку проекта" />
            <button type="button" onClick={chooseProject} disabled={runtime.phase !== "connected" || busy || history.length > 0}>Выбрать папку</button>
          </div>
          <textarea value={instruction} onChange={(event) => setInstruction(event.currentTarget.value)} disabled={runtime.phase !== "connected" || busy} aria-label="Инструкция для Codex" placeholder="Что поручить Codex?" rows={3} />
          <div className="composer-footer"><span>{history.length > 0 ? "Follow-up в том же root chat" : runtime.phase === "connected" ? "Read-only: первый настоящий запрос к Codex" : "Сначала подключите Codex"}</span><button type="submit" disabled={history.length > 0 ? !canFollowUp : !canSend}>{busy ? "Выполняется…" : "Отправить"}</button></div>
        </form>
      </section>
      <aside className="tracker" aria-label="Трекер работы агентов">
        <header><div><p className="eyebrow">OBSERVABLE WORK</p><h2>Агенты и работа</h2></div><button className="icon-button" disabled aria-label="Настроить отображение">☷</button></header>
        <div className="tracker-table" role="table"><div className="table-head" role="row"><span>Агент / задача</span><span>Статус</span></div><div className="tracker-empty"><div className="empty-symbol small">⌘</div><h3>Пока пусто</h3><p>Строки появятся только для реально наблюдаемых исполнений агентов.</p></div></div>
        <section className="workflow"><h3>Контекст работы</h3><p>Планы, роли и GitHub Issues будут показаны отдельно от исполнений агентов.</p><span className="badge">Нет связанных записей</span></section>
      </aside>
    </main>
  );
}

export default App;
