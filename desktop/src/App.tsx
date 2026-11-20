import { invoke } from "@tauri-apps/api/core";
import { useState } from "react";
import type { RuntimeState } from "./types";
import "./App.css";

type RootTurnResult = { threadId: string; turnId: string; status: string; assistantText?: string };

const initialRuntime: RuntimeState = {
  phase: "not_checked",
  message: "Codex App Server ещё не проверен",
};

function App() {
  const [runtime, setRuntime] = useState<RuntimeState>(initialRuntime);
  const [busy, setBusy] = useState(false);
  const [projectPath, setProjectPath] = useState("");
  const [instruction, setInstruction] = useState("");
  const [turn, setTurn] = useState<RootTurnResult | null>(null);
  const [turnError, setTurnError] = useState<string | null>(null);

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
    setTurn(null);
    try { setTurn(await invoke<RootTurnResult>("start_root_task", { projectPath, instruction })); }
    catch (error) { setTurnError(String(error)); }
    finally { setBusy(false); }
  }

  const canSend = runtime.phase === "connected" && !busy && projectPath.trim() && instruction.trim();

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
        <header className="topbar"><div><p className="eyebrow">ПРОЕКТ НЕ ВЫБРАН</p><h1>Новая задача</h1></div><div className="topbar-actions"><span className="badge">Нет активного turn</span><button disabled>Прервать</button></div></header>
        <div className="chat-empty">
          <div className="empty-symbol">✦</div><h2>Начните работу с Codex</h2>
          <p>{runtime.phase === "connected" ? "Codex подключён. Первый turn выполнится безопасно: read-only, без approvals." : "Сначала проверьте и подключите Codex runtime."}</p>
          {turn ? <div className="result-card"><strong>Turn: {turn.status}</strong><p>{turn.assistantText ?? "Ответ агента не был доступен в terminal item."}</p></div> : null}
          {turnError ? <p className="honesty">{turnError}</p> : null}
        </div>
        <form className="composer" onSubmit={(event) => { event.preventDefault(); startRootTask(); }}>
          <input className="project-path" value={projectPath} onChange={(event) => setProjectPath(event.currentTarget.value)} disabled={runtime.phase !== "connected" || busy} aria-label="Папка проекта" placeholder="Путь к папке проекта, например D:\\python\\project" />
          <textarea value={instruction} onChange={(event) => setInstruction(event.currentTarget.value)} disabled={runtime.phase !== "connected" || busy} aria-label="Инструкция для Codex" placeholder="Что поручить Codex?" rows={3} />
          <div className="composer-footer"><span>{runtime.phase === "connected" ? "Read-only: первый настоящий запрос к Codex" : "Сначала подключите Codex"}</span><button type="submit" disabled={!canSend}>{busy ? "Выполняется…" : "Отправить"}</button></div>
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
