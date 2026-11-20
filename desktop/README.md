# Orbita desktop

Нативный Windows-клиент Orbita на Tauri 2, React и TypeScript.

## Запуск разработки

```powershell
$env:Path = "$env:USERPROFILE\.cargo\bin;$env:Path"
cd desktop
npm install
npm run tauri dev
```

Tauri требует Rust MSVC toolchain, Microsoft C++ Build Tools и WebView2. См. официальные [предварительные требования Tauri](https://v2.tauri.app/start/prerequisites/).

## Текущее состояние

Это secure-shell slice: русскоязычное desktop-окно, минимальная capability главного окна, CSP и typed command boundary. Он не запускает Codex и не показывает fixture-данные. Live App Server, chat и tracker будут добавляться по тикетам #16–#20.
