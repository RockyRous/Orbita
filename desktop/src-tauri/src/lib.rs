use serde::Serialize;

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct ShellState {
    phase: &'static str,
    message: &'static str,
}

/// This is intentionally only a typed shell boundary. Runtime discovery and
/// App Server process ownership are implemented in the next delivery slice.
#[tauri::command]
fn inspect_runtime() -> ShellState {
    ShellState {
        phase: "not_checked",
        message: "Проверка Codex App Server ещё не реализована.",
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![inspect_runtime])
        .run(tauri::generate_context!())
        .expect("error while running Orbita");
}
