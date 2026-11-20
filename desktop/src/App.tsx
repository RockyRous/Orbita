import { invoke } from "@tauri-apps/api/core";
import { useState } from "react";
import type { RuntimeState } from "./types";
import "./App.css";

const initialRuntime: RuntimeState = {
  phase: "not_checked",
  message: "Codex App Server ещё не проверен",
};

function App() {
  const [runtime, setRuntime] = useState<RuntimeState>(initialRuntime);
  const [checking, setChecking] = useState(false);

  async function inspectRuntime() {
    setChecking(true);
    setRuntime({ phase: "checking", message: "Проверяем runtime…" });
    try {
      setRuntime(await invoke<RuntimeState>("inspect_runtime"));
    } catch {
      setRuntime({
        phase: "unavailable",
        message: "Не удалось вызвать системную проверку runtime.",
      });
    } finally {
      setChecking(false);
    }
  }

  async function connectRuntime() {
    setChecking(true);
    setRuntime({ phase: "checking", message: "Подключаем Codex App Server…" });
    try {
      setRuntime(await invoke<RuntimeState>("connect_runtime"));
    } catch (error) {
      setRuntime({ phase: "unavailable", message: String(error) });
    } finally {
      setChecking(false);
    }
  }

  return (
    <main className="shell">
      <aside className="sidebar" aria-label="Навигация">
        <div className="brand"><span className="brand-mark">O</span><span>Orbita</span></div>
        <button className="new-task" disabled title="Будет доступно после проверки runtime">+ Новая задача</button>
        <section className="nav-section">
          <h2>Рабочая область</h2>
          <button className="nav-item active">Текущая задача <span>—</span></button>
          <button className="nav-item">История <span>0</span></button>
        </section>
        <section className="sidebar-bottom">
          <div className={`runtime runtime-${runtime.phase}`}>
            <span className="status-dot" />
            <div>
              <strong>Codex runtime</strong>
              <small>{runtime.message}</small>
              {runtime.detectedVersion ? <small>Версия: {runtime.detectedVersion}</small> : null}
            </div>
          </div>
          {runtime.phase === "compatible" ? (
            <button className="link-button" onClick={connectRuntime} disabled={checking}>
              {checking ? "Подключение…" : "Подключить Codex"}
            </button>
          ) : (
            <button className="link-button" onClick={inspectRuntime} disabled={checking}>
              {checking ? "Проверка…" : "Проверить runtime"}
            </button>
          )}
        </section>
      </aside>

      <section className="chat-pane" aria-label="Чат Codex">
        <header className="topbar">
          <div><p className="eyebrow">ПРОЕКТ НЕ ВЫБРАН</p><h1>Новая задача</h1></div>
          <div className="topbar-actions"><span className="badge">Нет активного turn</span><button disabled>Прервать</button></div>
        </header>
        <div className="chat-empty">
          <div className="empty-symbol">✦</div>
          <h2>Начните работу с Codex</h2>
          <p>После проверки runtime здесь появится настоящий чат: сообщения, потоковый ответ, команды, планы, вопросы и результаты.</p>
          <p className="honesty">Это только каркас приложения. Задача не создана, Codex не запущен и данные не имитируются.</p>
        </div>
        <form className="composer" onSubmit={(event) => event.preventDefault()}>
          <textarea disabled aria-label="Инструкция для Codex" placeholder="Что поручить Codex?" rows={3} />
          <div className="composer-footer"><span>Сначала проверьте runtime и выберите проект</span><button type="submit" disabled>Отправить</button></div>
        </form>
      </section>

      <aside className="tracker" aria-label="Трекер работы агентов">
        <header><div><p className="eyebrow">OBSERVABLE WORK</p><h2>Агенты и работа</h2></div><button className="icon-button" disabled aria-label="Настроить отображение">☷</button></header>
        <div className="tracker-table" role="table" aria-label="Исполнения агентов">
          <div className="table-head" role="row"><span>Агент / задача</span><span>Статус</span></div>
          <div className="tracker-empty"><div className="empty-symbol small">⌘</div><h3>Пока пусто</h3><p>Строки появятся только для реально наблюдаемых исполнений агентов после запуска задачи.</p></div>
        </div>
        <section className="workflow"><h3>Контекст работы</h3><p>Планы, роли и GitHub Issues будут показаны отдельно от исполнений агентов.</p><span className="badge">Нет связанных записей</span></section>
      </aside>
    </main>
  );
}

export default App;
