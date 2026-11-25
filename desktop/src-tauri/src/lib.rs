use serde::Serialize;
use serde_json::{json, Value};
use sha2::{Digest, Sha256};
use std::collections::VecDeque;
use std::env;
use std::fs;
use std::io::{BufRead, BufReader, Read, Write};
use std::path::{Path, PathBuf};
use std::process::{Child, ChildStdin, Command, Stdio};
use std::sync::{mpsc, Arc, Mutex};
use std::thread;
use std::time::Duration;
use tauri::{ipc::Channel, State};

const PINNED_CODEX_VERSION: &str = "codex-cli 0.171.0";
const PINNED_NATIVE_SHA256: &str = "cefea4ffee1fff04983a99c0dda99944d8b380e891e740a28b32f4b815a6e0b7";
const INITIALIZE_TIMEOUT: Duration = Duration::from_secs(10);
const STDERR_LIMIT: usize = 64;

#[derive(Serialize, Clone, Debug)]
#[serde(rename_all = "camelCase")]
struct ShellState {
    phase: String,
    message: String,
    executable_path: Option<String>,
    native_executable_path: Option<String>,
    detected_version: Option<String>,
}

struct RuntimeProcess {
    child: Child,
    stdin: ChildStdin,
    events: mpsc::Receiver<Result<String, String>>,
    _stderr: Arc<Mutex<VecDeque<String>>>,
}

#[derive(Clone)]
struct ActiveTurn {
    thread_id: String,
    turn_id: String,
}

struct ActiveTurnLease<'a> {
    active_turn: &'a Mutex<Option<ActiveTurn>>,
}

impl Drop for ActiveTurnLease<'_> {
    fn drop(&mut self) {
        if let Ok(mut active) = self.active_turn.lock() {
            *active = None;
        }
    }
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct SupervisorSnapshot {
    connection: String,
    active_thread_id: Option<String>,
    active_turn_id: Option<String>,
}

#[derive(Default)]
struct AppState {
    runtime: Arc<Mutex<Option<RuntimeProcess>>>,
    active_turn: Mutex<Option<ActiveTurn>>,
}

#[derive(serde::Deserialize)]
#[serde(rename_all = "camelCase")]
struct StartRootTaskInput {
    project_path: String,
    instruction: String,
}

#[derive(serde::Deserialize)]
#[serde(rename_all = "camelCase")]
struct FollowUpInput {
    thread_id: String,
    instruction: String,
}

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct RootTurnResult {
    thread_id: String,
    turn_id: String,
    status: String,
    assistant_text: Option<String>,
}

/// The only live App Server shape exposed to the webview. Protocol JSON stays
/// in Rust, where it is correlated with the active turn before projection.
#[derive(Serialize, Clone, Debug, PartialEq)]
#[serde(rename_all = "camelCase")]
struct ProjectionEnvelope {
    sequence: u64,
    root_task_id: String,
    kind: String,
    text: Option<String>,
    status: Option<String>,
}

struct RootTurnProjection {
    sequence: u64,
    root_task_id: String,
    thread_id: String,
    turn_id: String,
    assistant_text: String,
}

impl RootTurnProjection {
    fn new(thread_id: String, turn_id: String) -> Self {
        Self { root_task_id: thread_id.clone(), thread_id, turn_id, sequence: 0, assistant_text: String::new() }
    }

    fn emit(&mut self, updates: &Channel<ProjectionEnvelope>, kind: &str, text: Option<String>, status: Option<String>) -> Result<(), String> {
        self.sequence += 1;
        updates.send(ProjectionEnvelope { sequence: self.sequence, root_task_id: self.root_task_id.clone(), kind: kind.to_owned(), text, status })
            .map_err(|error| format!("Could not send chat update: {error}"))
    }

    fn project(&mut self, message: &Value, updates: &Channel<ProjectionEnvelope>) -> Result<Option<String>, String> {
        let params = message.get("params");
        let matching = params.and_then(|value| value.get("threadId")).and_then(Value::as_str) == Some(self.thread_id.as_str())
            && (params.and_then(|value| value.get("turnId")).and_then(Value::as_str) == Some(self.turn_id.as_str())
                || params.and_then(|value| value.get("turn")).and_then(|turn| turn.get("id")).and_then(Value::as_str) == Some(self.turn_id.as_str()));
        if !matching { return Ok(None); }
        match message.get("method").and_then(Value::as_str) {
            Some("turn/started") => self.emit(updates, "turnStarted", None, None)?,
            Some("item/agentMessage/delta") => {
                if let Some(delta) = params.and_then(|value| value.get("delta")).and_then(Value::as_str) {
                    self.assistant_text.push_str(delta);
                    self.emit(updates, "assistantDelta", Some(delta.to_owned()), None)?;
                }
            }
            Some("item/completed") => {
                if let Some(item) = params.and_then(|value| value.get("item"))
                    && item.get("type").and_then(Value::as_str) == Some("agentMessage")
                    && let Some(text) = item.get("text").and_then(Value::as_str) {
                        self.assistant_text = text.to_owned();
                        self.emit(updates, "assistantMessage", Some(text.to_owned()), None)?;
                    }
            }
            Some("turn/completed") => {
                let status = params.and_then(|value| value.get("turn")).and_then(|turn| turn.get("status")).and_then(Value::as_str)
                    .ok_or("Codex completed a turn without a status.".to_owned())?.to_owned();
                self.emit(updates, "turnCompleted", None, Some(status.clone()))?;
                return Ok(Some(status));
            }
            _ => {}
        }
        Ok(None)
    }
}

fn find_codex_launcher(path_value: Option<&std::ffi::OsStr>) -> Option<PathBuf> {
    let path_value = path_value?;
    let candidates = ["codex.cmd", "codex.exe"];
    env::split_paths(path_value).find_map(|directory| {
        candidates
            .iter()
            .map(|name| directory.join(name))
            .find(|candidate| candidate.is_file())
    })
}

fn native_executable_from(launcher: &Path) -> Result<PathBuf, String> {
    let Some(launcher_directory) = launcher.parent() else {
        return Err("Не удалось определить каталог Codex launcher.".to_owned());
    };
    let openai_directory = launcher_directory.join("node_modules/@openai/codex/node_modules/@openai");
    let entries = fs::read_dir(&openai_directory)
        .map_err(|_| "Не найден нативный пакет Codex рядом с launcher.".to_owned())?;
    let candidates = entries
        .filter_map(Result::ok)
        .filter(|entry| entry.file_name().to_string_lossy().starts_with("codex-win32-"))
        .filter_map(|entry| fs::read_dir(entry.path().join("vendor")).ok())
        .flat_map(|vendors| vendors.filter_map(Result::ok).collect::<Vec<_>>())
        .map(|vendor| vendor.path().join("bin/codex.exe"))
        .filter(|candidate| candidate.is_file())
        .collect::<Vec<_>>();
    match candidates.as_slice() {
        [candidate] => Ok(candidate.clone()),
        [] => Err("Не найден нативный executable Codex.".to_owned()),
        _ => Err("Найдено несколько нативных executable Codex; runtime заблокирован.".to_owned()),
    }
}

fn sha256_file(path: &Path) -> Result<String, String> {
    let mut source = fs::File::open(path).map_err(|error| format!("Не удалось открыть Codex: {error}"))?;
    let mut digest = Sha256::new();
    let mut buffer = [0_u8; 65_536];
    loop {
        let count = source.read(&mut buffer).map_err(|error| format!("Не удалось прочитать Codex: {error}"))?;
        if count == 0 { break; }
        digest.update(&buffer[..count]);
    }
    Ok(format!("{:x}", digest.finalize()))
}

fn version_from(executable: &Path) -> Result<String, String> {
    let output = Command::new(executable).arg("--version").output()
        .map_err(|error| format!("Не удалось запустить Codex: {error}"))?;
    if !output.status.success() {
        return Err(format!("Codex завершился с кодом {:?} при проверке версии.", output.status.code()));
    }
    let version = String::from_utf8_lossy(&output.stdout).trim().to_owned();
    if version.is_empty() { return Err("Codex не вернул версию runtime.".to_owned()); }
    Ok(version)
}

fn qualified_native() -> Result<(PathBuf, ShellState), ShellState> {
    let Some(launcher) = find_codex_launcher(env::var_os("PATH").as_deref()) else {
        return Err(ShellState { phase: "unavailable".to_owned(), message: "Codex не найден в PATH. Установите или обновите Codex CLI.".to_owned(), executable_path: None, native_executable_path: None, detected_version: None });
    };
    let launcher_path = launcher.display().to_string();
    let native = native_executable_from(&launcher).map_err(|message| ShellState { phase: "incompatible".to_owned(), message, executable_path: Some(launcher_path.clone()), native_executable_path: None, detected_version: None })?;
    let native_path = native.display().to_string();
    let digest = sha256_file(&native).map_err(|message| ShellState { phase: "unavailable".to_owned(), message, executable_path: Some(launcher_path.clone()), native_executable_path: Some(native_path.clone()), detected_version: None })?;
    let version = version_from(&native).map_err(|message| ShellState { phase: "unavailable".to_owned(), message, executable_path: Some(launcher_path.clone()), native_executable_path: Some(native_path.clone()), detected_version: None })?;
    let state = if version == PINNED_CODEX_VERSION && digest == PINNED_NATIVE_SHA256 {
        ShellState { phase: "compatible".to_owned(), message: "Проверенный Codex runtime найден.".to_owned(), executable_path: Some(launcher_path), native_executable_path: Some(native_path), detected_version: Some(version) }
    } else {
        ShellState { phase: "incompatible".to_owned(), message: format!("Найден профиль {version}, но он не совпадает с проверенным runtime Orbita."), executable_path: Some(launcher_path), native_executable_path: Some(native_path), detected_version: Some(version) }
    };
    if state.phase == "compatible" { Ok((native, state)) } else { Err(state) }
}

fn spawn_line_reader<R: Read + Send + 'static>(reader: R, sender: mpsc::SyncSender<Result<String, String>>) {
    thread::spawn(move || {
        for line in BufReader::new(reader).lines() {
            // Backpressure is preferable to silently dropping a protocol line or
            // abandoning stdout, which could deadlock the App Server child.
            if sender.send(line.map_err(|error| error.to_string())).is_err() { break; }
        }
    });
}

fn spawn_stderr_reader<R: Read + Send + 'static>(reader: R, buffer: Arc<Mutex<VecDeque<String>>>) {
    thread::spawn(move || {
        for line in BufReader::new(reader).lines().map_while(Result::ok) {
            if let Ok(mut lines) = buffer.lock() {
                if lines.len() == STDERR_LIMIT { lines.pop_front(); }
                lines.push_back(line);
            }
        }
    });
}

fn send_json(stdin: &mut ChildStdin, value: &Value) -> Result<(), String> {
    let encoded = serde_json::to_string(value).map_err(|error| error.to_string())?;
    stdin.write_all(encoded.as_bytes()).map_err(|error| format!("Не удалось отправить сообщение Codex: {error}"))?;
    stdin.write_all(b"\n").map_err(|error| format!("Не удалось завершить сообщение Codex: {error}"))?;
    stdin.flush().map_err(|error| format!("Не удалось передать сообщение Codex: {error}"))
}

fn initialize_process(native: &Path) -> Result<RuntimeProcess, String> {
    let mut child = Command::new(native)
        .args(["app-server", "--listen", "stdio://"])
        .stdin(Stdio::piped()).stdout(Stdio::piped()).stderr(Stdio::piped())
        .spawn().map_err(|error| format!("Не удалось запустить Codex App Server: {error}"))?;
    let mut stdin = child.stdin.take().ok_or("Codex App Server не открыл stdin.")?;
    let stdout = child.stdout.take().ok_or("Codex App Server не открыл stdout.")?;
    let stderr = child.stderr.take().ok_or("Codex App Server не открыл stderr.")?;
    let (sender, events) = mpsc::sync_channel(256);
    let stderr_buffer = Arc::new(Mutex::new(VecDeque::new()));
    spawn_line_reader(stdout, sender);
    spawn_stderr_reader(stderr, Arc::clone(&stderr_buffer));
    let initialize = json!({"id":"orbita-initialize-1","method":"initialize","params":{"capabilities":{"experimentalApi":false},"clientInfo":{"name":"orbita-desktop","title":"Orbita","version":"0.1.0"}}});
    if let Err(error) = send_json(&mut stdin, &initialize) { let _ = child.kill(); return Err(error); }
    let response = events.recv_timeout(INITIALIZE_TIMEOUT).map_err(|_| "Codex App Server не ответил на initialize за 10 секунд.".to_owned())??;
    let message: Value = serde_json::from_str(&response).map_err(|_| "Codex App Server вернул невалидный JSON на initialize.".to_owned())?;
    if message.get("id") != Some(&Value::String("orbita-initialize-1".to_owned())) || message.get("result").is_none() {
        let _ = child.kill();
        return Err("Codex App Server не подтвердил initialize.".to_owned());
    }
    if let Err(error) = send_json(&mut stdin, &json!({"method":"initialized"})) { let _ = child.kill(); return Err(error); }
    Ok(RuntimeProcess { child, stdin, events, _stderr: stderr_buffer })
}

fn receive_json(runtime: &RuntimeProcess, timeout: Duration) -> Result<Value, String> {
    let line = runtime.events.recv_timeout(timeout)
        .map_err(|_| "Codex App Server не прислал ожидаемое событие вовремя.".to_owned())??;
    serde_json::from_str(&line).map_err(|_| "Codex App Server вернул невалидный JSON.".to_owned())
}

fn poll_json(runtime: &RuntimeProcess, timeout: Duration) -> Result<Option<Value>, String> {
    match runtime.events.recv_timeout(timeout) {
        Ok(Ok(line)) => serde_json::from_str(&line).map(Some).map_err(|_| "Codex App Server returned invalid JSON.".to_owned()),
        Ok(Err(error)) => Err(error),
        Err(mpsc::RecvTimeoutError::Timeout) => Ok(None),
        Err(mpsc::RecvTimeoutError::Disconnected) => Err("Codex App Server closed its event stream.".to_owned()),
    }
}

fn wait_response(runtime: &RuntimeProcess, request_id: &str, timeout: Duration) -> Result<Value, String> {
    let deadline = std::time::Instant::now() + timeout;
    loop {
        let remaining = deadline.checked_duration_since(std::time::Instant::now())
            .ok_or("Codex App Server не ответил вовремя.".to_owned())?;
        let message = receive_json(runtime, remaining)?;
        if message.get("id") == Some(&Value::String(request_id.to_owned())) {
            if message.get("result").is_some() { return Ok(message); }
            return Err("Codex App Server отклонил запрос.".to_owned());
        }
    }
}

fn string_at(value: &Value, path: &[&str]) -> Option<String> {
    let mut current = value;
    for key in path { current = current.get(*key)?; }
    current.as_str().map(ToOwned::to_owned)
}

#[tauri::command]
fn inspect_runtime() -> ShellState {
    match qualified_native() { Ok((_, state)) | Err(state) => state }
}

#[tauri::command]
fn connect_runtime(state: State<'_, AppState>) -> Result<ShellState, String> {
    let (native, mut runtime) = qualified_native().map_err(|state| state.message)?;
    let mut guard = state.runtime.lock().map_err(|_| "Не удалось получить состояние runtime.".to_owned())?;
    if guard.is_some() {
        runtime.phase = "connected".to_owned();
        runtime.message = "Codex App Server уже подключён.".to_owned();
        return Ok(runtime);
    }
    *guard = Some(initialize_process(&native)?);
    runtime.phase = "connected".to_owned();
    runtime.message = "Codex App Server подключён и инициализирован.".to_owned();
    Ok(runtime)
}

#[tauri::command]
fn stop_runtime(state: State<'_, AppState>) -> Result<ShellState, String> {
    let mut guard = state.runtime.lock().map_err(|_| "Не удалось получить состояние runtime.".to_owned())?;
    if let Some(mut runtime) = guard.take() {
        let _ = runtime.stdin.flush();
        runtime.child.kill().map_err(|error| format!("Не удалось остановить Codex App Server: {error}"))?;
        let _ = runtime.child.wait();
    }
    Ok(ShellState { phase: "compatible".to_owned(), message: "Codex App Server остановлен.".to_owned(), executable_path: None, native_executable_path: None, detected_version: Some(PINNED_CODEX_VERSION.to_owned()) })
}

#[tauri::command]
fn request_interrupt(state: State<'_, AppState>) -> Result<(), String> {
    let active = state.active_turn.lock().map_err(|_| "Не удалось получить активный turn.".to_owned())?
        .clone().ok_or("Нет активного turn для прерывания.".to_owned())?;
    let mut runtime = state.runtime.lock().map_err(|_| "Не удалось получить состояние runtime.".to_owned())?;
    let process = runtime.as_mut().ok_or("Codex App Server не подключён.".to_owned())?;
    if process.child.try_wait().map_err(|error| error.to_string())?.is_some() {
        *runtime = None;
        return Err("Codex App Server завершился; подключите его заново.".to_owned());
    }
    send_json(&mut process.stdin, &json!({
        "id":"orbita-turn-interrupt-1", "method":"turn/interrupt",
        "params":{"threadId":active.thread_id, "turnId":active.turn_id}
    }))
}

#[tauri::command]
fn get_projection(state: State<'_, AppState>) -> Result<SupervisorSnapshot, String> {
    let connection = {
        let mut runtime = state.runtime.lock().map_err(|_| "Не удалось получить состояние runtime.".to_owned())?;
        let disconnected = match runtime.as_mut() {
            None => true,
            Some(process) => process.child.try_wait().map_err(|error| error.to_string())?.is_some(),
        };
        if disconnected {
            *runtime = None;
            "disconnected".to_owned()
        } else {
            "connected".to_owned()
        }
    };
    if connection == "disconnected" {
        *state.active_turn.lock().map_err(|_| "Не удалось очистить активный turn.".to_owned())? = None;
        return Ok(SupervisorSnapshot { connection, active_thread_id: None, active_turn_id: None });
    }
    let active = state.active_turn.lock().map_err(|_| "Не удалось получить активный turn.".to_owned())?.clone();
    Ok(SupervisorSnapshot {
        connection,
        active_thread_id: active.as_ref().map(|turn| turn.thread_id.clone()),
        active_turn_id: active.map(|turn| turn.turn_id),
    })
}

#[tauri::command]
fn start_root_task(input: StartRootTaskInput, updates: Channel<ProjectionEnvelope>, state: State<'_, AppState>) -> Result<RootTurnResult, String> {
    let instruction = input.instruction.trim();
    if instruction.is_empty() { return Err("Введите инструкцию для Codex.".to_owned()); }
    let project = fs::canonicalize(input.project_path.trim())
        .map_err(|_| "Папка проекта не найдена.".to_owned())?;
    if !project.is_dir() { return Err("Укажите папку проекта, а не файл.".to_owned()); }
    let runtime_state = Arc::clone(&state.runtime);
    let (thread_id, turn_id) = {
    let mut guard = runtime_state.lock().map_err(|_| "Не удалось получить состояние runtime.".to_owned())?;
    let runtime = guard.as_mut().ok_or("Сначала подключите Codex App Server.".to_owned())?;
    if runtime.child.try_wait().map_err(|error| error.to_string())?.is_some() {
        *guard = None;
        return Err("Codex App Server завершился; подключите его заново.".to_owned());
    }

    send_json(&mut runtime.stdin, &json!({
        "id":"orbita-thread-start-1", "method":"thread/start",
        "params":{"approvalPolicy":"never", "cwd":project, "ephemeral":true, "sandbox":"read-only"}
    }))?;
    let thread_response = wait_response(runtime, "orbita-thread-start-1", INITIALIZE_TIMEOUT)?;
    let thread_id = string_at(&thread_response, &["result", "thread", "id"])
        .ok_or("Codex не вернул identity новой задачи.".to_owned())?;
    send_json(&mut runtime.stdin, &json!({
        "id":"orbita-turn-start-1", "method":"turn/start",
        "params":{"threadId":thread_id, "input":[{"type":"text", "text":instruction, "text_elements":[]}]}
    }))?;
    let turn_response = wait_response(runtime, "orbita-turn-start-1", INITIALIZE_TIMEOUT)?;
    let turn_id = string_at(&turn_response, &["result", "turn", "id"])
        .ok_or("Codex не вернул identity turn.".to_owned())?;
    (thread_id, turn_id)
    };
    *state.active_turn.lock().map_err(|_| "Не удалось записать активный turn.".to_owned())? = Some(ActiveTurn { thread_id: thread_id.clone(), turn_id: turn_id.clone() });
    let _active_turn_lease = ActiveTurnLease { active_turn: &state.active_turn };
    let mut projection = RootTurnProjection::new(thread_id.clone(), turn_id.clone());
    projection.emit(&updates, "turnAccepted", None, None)?;
    let deadline = std::time::Instant::now() + Duration::from_secs(120);
    let mut assistant_text = None;
    loop {
        let remaining = deadline.checked_duration_since(std::time::Instant::now())
            .ok_or("Turn не завершился за 120 секунд; Orbita не считает его успешным.".to_owned())?;
        let message = {
            let guard = runtime_state.lock().map_err(|_| "Не удалось получить состояние runtime.".to_owned())?;
            let runtime = guard.as_ref().ok_or("Codex App Server не подключён.".to_owned())?;
            poll_json(runtime, remaining.min(Duration::from_millis(250)))?
        };
        let Some(message) = message else { continue; };
        // Projection is deliberately independent from the legacy result adapter:
        // the channel receives live updates while the invoke result stays a
        // terminal summary for callers that need it.
        let _ = projection.project(&message, &updates)?;
        let params = message.get("params");
        let matching = params.and_then(|params| params.get("threadId")).and_then(Value::as_str) == Some(thread_id.as_str())
            && (params.and_then(|params| params.get("turnId")).and_then(Value::as_str) == Some(turn_id.as_str())
                || params.and_then(|params| params.get("turn")).and_then(|turn| turn.get("id")).and_then(Value::as_str) == Some(turn_id.as_str()));
        if !matching { continue; }
        if message.get("method").and_then(Value::as_str) == Some("item/completed") {
            if let Some(item) = params.and_then(|params| params.get("item")) {
                if item.get("type").and_then(Value::as_str) == Some("agentMessage") {
                    assistant_text = item.get("text").and_then(Value::as_str).map(ToOwned::to_owned);
                }
            }
        }
        if message.get("method").and_then(Value::as_str) == Some("turn/completed") {
            let status = params.and_then(|params| params.get("turn")).and_then(|turn| turn.get("status")).and_then(Value::as_str)
                .ok_or("Codex завершил turn без статуса.".to_owned())?.to_owned();
            *state.active_turn.lock().map_err(|_| "Не удалось очистить активный turn.".to_owned())? = None;
            return Ok(RootTurnResult { thread_id, turn_id, status, assistant_text });
        }
    }
}

#[tauri::command]
fn send_follow_up(input: FollowUpInput, updates: Channel<ProjectionEnvelope>, state: State<'_, AppState>) -> Result<RootTurnResult, String> {
    let instruction = input.instruction.trim();
    let thread_id = input.thread_id.trim().to_owned();
    if instruction.is_empty() { return Err("Введите сообщение для Codex.".to_owned()); }
    if thread_id.is_empty() { return Err("Не указан root chat для follow-up.".to_owned()); }
    if state.active_turn.lock().map_err(|_| "Не удалось получить активный turn.".to_owned())?.is_some() {
        return Err("Сначала дождитесь завершения активного turn.".to_owned());
    }
    let runtime_state = Arc::clone(&state.runtime);
    let turn_id = {
        let mut guard = runtime_state.lock().map_err(|_| "Не удалось получить состояние runtime.".to_owned())?;
        let runtime = guard.as_mut().ok_or("Сначала подключите Codex App Server.".to_owned())?;
        if runtime.child.try_wait().map_err(|error| error.to_string())?.is_some() {
            *guard = None;
            return Err("Codex App Server завершился; подключите его заново.".to_owned());
        }
        send_json(&mut runtime.stdin, &json!({
            "id":"orbita-follow-up-1", "method":"turn/start",
            "params":{"threadId":thread_id, "input":[{"type":"text", "text":instruction, "text_elements":[]}]}
        }))?;
        let response = wait_response(runtime, "orbita-follow-up-1", INITIALIZE_TIMEOUT)?;
        string_at(&response, &["result", "turn", "id"])
            .ok_or("Codex не вернул identity follow-up turn.".to_owned())?
    };
    *state.active_turn.lock().map_err(|_| "Не удалось записать активный turn.".to_owned())? = Some(ActiveTurn { thread_id: thread_id.clone(), turn_id: turn_id.clone() });
    let _active_turn_lease = ActiveTurnLease { active_turn: &state.active_turn };
    let mut projection = RootTurnProjection::new(thread_id.clone(), turn_id.clone());
    projection.emit(&updates, "turnAccepted", None, None)?;
    let deadline = std::time::Instant::now() + Duration::from_secs(120);
    let mut assistant_text = None;
    loop {
        let remaining = deadline.checked_duration_since(std::time::Instant::now())
            .ok_or("Follow-up turn did not finish within 120 seconds.".to_owned())?;
        let message = {
            let guard = runtime_state.lock().map_err(|_| "Не удалось получить состояние runtime.".to_owned())?;
            let runtime = guard.as_ref().ok_or("Codex App Server не подключён.".to_owned())?;
            poll_json(runtime, remaining.min(Duration::from_millis(250)))?
        };
        let Some(message) = message else { continue; };
        let _ = projection.project(&message, &updates)?;
        let params = message.get("params");
        let matching = params.and_then(|value| value.get("threadId")).and_then(Value::as_str) == Some(thread_id.as_str())
            && (params.and_then(|value| value.get("turnId")).and_then(Value::as_str) == Some(turn_id.as_str())
                || params.and_then(|value| value.get("turn")).and_then(|turn| turn.get("id")).and_then(Value::as_str) == Some(turn_id.as_str()));
        if !matching { continue; }
        if message.get("method").and_then(Value::as_str) == Some("item/completed") {
            if let Some(item) = params.and_then(|value| value.get("item")) {
                if item.get("type").and_then(Value::as_str) == Some("agentMessage") {
                    assistant_text = item.get("text").and_then(Value::as_str).map(ToOwned::to_owned);
                }
            }
        }
        if message.get("method").and_then(Value::as_str) == Some("turn/completed") {
            let status = params.and_then(|value| value.get("turn")).and_then(|turn| turn.get("status")).and_then(Value::as_str)
                .ok_or("Codex completed a follow-up without a status.".to_owned())?.to_owned();
            *state.active_turn.lock().map_err(|_| "Не удалось очистить активный turn.".to_owned())? = None;
            return Ok(RootTurnResult { thread_id, turn_id, status, assistant_text });
        }
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .manage(AppState::default())
        .invoke_handler(tauri::generate_handler![inspect_runtime, connect_runtime, stop_runtime, get_projection, request_interrupt, start_root_task, send_follow_up])
        .run(tauri::generate_context!())
        .expect("error while running Orbita");
}

#[cfg(test)]
mod tests {
    use super::{find_codex_launcher, initialize_process, qualified_native, ActiveTurn, ActiveTurnLease, ProjectionEnvelope, PINNED_CODEX_VERSION, PINNED_NATIVE_SHA256};
    use std::sync::Mutex;
    use std::ffi::OsString;

    #[test]
    fn runtime_pin_is_explicit() {
        assert_eq!(PINNED_CODEX_VERSION, "codex-cli 0.171.0");
        assert_eq!(PINNED_NATIVE_SHA256.len(), 64);
    }

    #[test]
    fn missing_path_has_no_launcher() {
        assert!(find_codex_launcher(Some(&OsString::from("Z:\\does-not-exist"))).is_none());
    }

    #[test]
    fn projection_envelope_serializes_the_public_contract() {
        let event = ProjectionEnvelope {
            sequence: 7,
            root_task_id: "thread-1".to_owned(),
            kind: "assistantDelta".to_owned(),
            text: Some("hello".to_owned()),
            status: None,
        };
        let value = serde_json::to_value(event).expect("projection serializes");
        assert_eq!(value["sequence"], 7);
        assert_eq!(value["rootTaskId"], "thread-1");
        assert_eq!(value["kind"], "assistantDelta");
        assert_eq!(value["text"], "hello");
    }

    #[test]
    fn active_turn_lease_clears_the_claim_on_scope_exit() {
        let active = Mutex::new(Some(ActiveTurn { thread_id: "thread-1".to_owned(), turn_id: "turn-1".to_owned() }));
        { let _lease = ActiveTurnLease { active_turn: &active }; }
        assert!(active.lock().expect("test mutex").is_none());
    }

    #[test]
    fn live_initialize_requires_explicit_opt_in() {
        if std::env::var("ORBITA_LIVE_RUNTIME_TEST").as_deref() != Ok("1") {
            return;
        }
        let (native, _) = qualified_native().expect("the exact qualified runtime must be installed");
        let mut runtime = initialize_process(&native).expect("initialize must succeed for the qualified runtime");
        runtime.child.kill().expect("the test child must stop");
        runtime.child.wait().expect("the test child must exit");
    }
}
