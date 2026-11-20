use serde::Serialize;
use std::env;
use std::path::{Path, PathBuf};
use std::process::Command;

const PINNED_CODEX_VERSION: &str = "codex-cli 0.170.0";

#[derive(Serialize)]
#[serde(rename_all = "camelCase")]
struct ShellState {
    phase: String,
    message: String,
    executable_path: Option<String>,
    detected_version: Option<String>,
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

fn version_from(executable: &Path) -> Result<String, String> {
    let output = Command::new(executable)
        .arg("--version")
        .output()
        .map_err(|error| format!("Не удалось запустить Codex: {error}"))?;

    if !output.status.success() {
        return Err(format!(
            "Codex завершился с кодом {:?} при проверке версии.",
            output.status.code()
        ));
    }

    let version = String::from_utf8_lossy(&output.stdout).trim().to_owned();
    if version.is_empty() {
        return Err("Codex не вернул версию runtime.".to_owned());
    }
    Ok(version)
}

#[tauri::command]
fn inspect_runtime() -> ShellState {
    let Some(executable) = find_codex_launcher(env::var_os("PATH").as_deref()) else {
        return ShellState {
            phase: "unavailable".to_owned(),
            message: "Codex не найден в PATH. Установите или обновите Codex CLI.".to_owned(),
            executable_path: None,
            detected_version: None,
        };
    };

    let executable_path = executable.display().to_string();
    match version_from(&executable) {
        Ok(version) if version == PINNED_CODEX_VERSION => ShellState {
            phase: "compatible".to_owned(),
            message: "Проверенный Codex runtime найден.".to_owned(),
            executable_path: Some(executable_path),
            detected_version: Some(version),
        },
        Ok(version) => ShellState {
            phase: "incompatible".to_owned(),
            message: format!(
                "Найдена версия {version}; Orbita пока проверена только с {PINNED_CODEX_VERSION}."
            ),
            executable_path: Some(executable_path),
            detected_version: Some(version),
        },
        Err(message) => ShellState {
            phase: "unavailable".to_owned(),
            message,
            executable_path: Some(executable_path),
            detected_version: None,
        },
    }
}

#[cfg(test)]
mod tests {
    use super::{find_codex_launcher, PINNED_CODEX_VERSION};
    use std::ffi::OsString;

    #[test]
    fn runtime_pin_is_explicit() {
        assert_eq!(PINNED_CODEX_VERSION, "codex-cli 0.170.0");
    }

    #[test]
    fn missing_path_has_no_launcher() {
        assert!(find_codex_launcher(Some(&OsString::from("Z:\\does-not-exist"))).is_none());
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .invoke_handler(tauri::generate_handler![inspect_runtime])
        .run(tauri::generate_context!())
        .expect("error while running Orbita");
}
