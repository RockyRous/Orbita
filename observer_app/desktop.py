"""Нативное Windows-приложение Orbita: наблюдатель одной корневой задачи."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from observer_app.server import ObserverApplication


COLORS = {
    "bg": "#0b1020", "panel": "#142039", "panel_alt": "#192944",
    "text": "#eef2ff", "muted": "#a7b7d1", "accent": "#78dfce",
    "border": "#31476b", "warning": "#f2ba70", "success": "#75dacb",
}


def russian_timeline(snapshot: dict[str, Any]) -> list[tuple[str, str]]:
    """Map the sanitized projection to Russian observer-only display copy."""
    projection = snapshot["projection"]
    labels = {
        "Root turn completed": "Корневой turn завершён",
        "Follow-up completed": "Уточнение завершено",
        "Interrupt confirmed": "Прерывание подтверждено",
        "No late event observed": "Поздних событий не наблюдалось",
        "Follow-up staged locally": "Уточнение добавлено локально",
        "Interrupt requested in preview": "Прерывание запрошено в демо-режиме",
        "Task marked Finished locally": "Задача отмечена завершённой локально",
    }
    items = [(labels.get(event["title"], event["title"]), event["detail"]) for event in projection["timeline"]]
    items.extend((labels.get(event["title"], event["title"]), event["detail"]) for event in snapshot["preview"]["events"])
    return items


class OrbitaDesktop:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.application = ObserverApplication()
        self.root.title("Orbita — наблюдатель задачи")
        self.root.minsize(960, 640)
        self.root.configure(bg=COLORS["bg"])
        self._configure_style()
        self._build()
        self.refresh()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("TFrame", background=COLORS["bg"])
        style.configure("Panel.TFrame", background=COLORS["panel"])
        style.configure("TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI", 10))
        style.configure("Muted.TLabel", background=COLORS["bg"], foreground=COLORS["muted"], font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=COLORS["bg"], foreground=COLORS["text"], font=("Segoe UI Semibold", 20))
        style.configure("Heading.TLabel", background=COLORS["panel"], foreground=COLORS["text"], font=("Segoe UI Semibold", 12))
        style.configure("Accent.TButton", background=COLORS["accent"], foreground="#071823", font=("Segoe UI Semibold", 10), padding=(11, 7))
        style.map("Accent.TButton", background=[("active", "#9deee1")])
        style.configure("Secondary.TButton", background=COLORS["panel_alt"], foreground=COLORS["text"], font=("Segoe UI", 10), padding=(11, 7))
        style.map("Secondary.TButton", background=[("active", "#284264")])

    def _build(self) -> None:
        outer = ttk.Frame(self.root, padding=22)
        outer.pack(fill="both", expand=True)
        header = ttk.Frame(outer)
        header.pack(fill="x")
        ttk.Label(header, text="Orbita", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="Локальный наблюдатель корневой задачи", style="Muted.TLabel").pack(side="left", padx=14, pady=8)
        self.runtime_label = ttk.Label(header, style="Muted.TLabel")
        self.runtime_label.pack(side="right", pady=8)

        notice = tk.Label(outer, text="Демонстрационный режим: показываются только проверенные данные. Иерархия агентов, подтверждения действий и восстановление недоступны.", anchor="w", justify="left", bg="#173050", fg="#d8e8ff", padx=12, pady=9, font=("Segoe UI", 9))
        notice.pack(fill="x", pady=(18, 14))

        columns = ttk.Frame(outer)
        columns.pack(fill="both", expand=True)
        columns.columnconfigure(0, weight=3)
        columns.columnconfigure(1, weight=2)
        columns.rowconfigure(0, weight=1)

        left = ttk.Frame(columns, style="Panel.TFrame", padding=18)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ttk.Label(left, text="Корневая задача", style="Heading.TLabel").pack(anchor="w")
        self.task_title = ttk.Label(left, text="Проверка границы App Server", style="Heading.TLabel")
        self.task_title.pack(anchor="w", pady=(14, 2))
        self.status_label = tk.Label(left, text="", bg=COLORS["success"], fg="#092d2a", padx=8, pady=3, font=("Segoe UI Semibold", 9))
        self.status_label.pack(anchor="w", pady=(0, 12))
        ttk.Label(left, text="Таймлайн доказательств", style="Heading.TLabel").pack(anchor="w", pady=(4, 7))
        self.timeline = tk.Listbox(left, bg=COLORS["panel"], fg=COLORS["text"], selectbackground="#294b72", selectforeground=COLORS["text"], relief="flat", highlightthickness=0, font=("Segoe UI", 10), activestyle="none")
        self.timeline.pack(fill="both", expand=True)

        action_row = ttk.Frame(left, style="Panel.TFrame")
        action_row.pack(fill="x", pady=(14, 0))
        ttk.Button(action_row, text="Добавить уточнение (демо)", style="Accent.TButton", command=lambda: self.preview_action("follow-up")).pack(side="left")
        ttk.Button(action_row, text="Прервать запуск (демо)", style="Secondary.TButton", command=lambda: self.preview_action("interrupt")).pack(side="left", padx=8)
        ttk.Button(action_row, text="Завершить задачу", style="Secondary.TButton", command=lambda: self.preview_action("finish")).pack(side="right")

        right = ttk.Frame(columns, style="Panel.TFrame", padding=18)
        right.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        ttk.Label(right, text="Источник и ограничения", style="Heading.TLabel").pack(anchor="w")
        self.details = tk.Text(right, height=16, wrap="word", bg=COLORS["panel"], fg=COLORS["text"], insertbackground=COLORS["text"], relief="flat", highlightthickness=0, font=("Segoe UI", 10), padx=0, pady=12)
        self.details.pack(fill="both", expand=True)
        self.details.configure(state="disabled")
        ttk.Button(right, text="Показать provenance", style="Secondary.TButton", command=self.show_provenance).pack(anchor="w", pady=(12, 0))
        self.message = ttk.Label(outer, style="Muted.TLabel")
        self.message.pack(anchor="w", pady=(12, 0))

    def refresh(self) -> None:
        snapshot = self.application.snapshot()
        projection = snapshot["projection"]
        preview = snapshot["preview"]
        self.runtime_label.configure(text=f"{projection['runtime']} · закреплённая версия")
        self.status_label.configure(text="Завершена" if preview["lifecycle"] == "Finished" else "Открыта")
        self.timeline.delete(0, tk.END)
        for title, detail in russian_timeline(snapshot):
            self.timeline.insert(tk.END, f"{title} — {detail}")
        details = (
            f"Проверочный снимок: {projection['fixture']}\n"
            f"Корневой thread: {projection['rootThread']}\n\n"
            "Доступно и доказано:\n"
            "• исход корневого запуска\n• уточнение в том же потоке\n• подтверждённое прерывание\n\n"
            "Недоступно в этом runtime:\n"
            "• визуальная иерархия агентов\n• approval controls\n• восстановление истории\n\n"
            "Локальные кнопки демо-режима не отправляют команд Codex."
        )
        self.details.configure(state="normal")
        self.details.delete("1.0", tk.END)
        self.details.insert("1.0", details)
        self.details.configure(state="disabled")

    def preview_action(self, action: str) -> None:
        snapshot = self.application.action(action)
        if action == "finish":
            self.message.configure(text="Задача завершена только в локальном демо-режиме. Исходный результат не менялся.")
        else:
            self.message.configure(text="Добавлено локальное демо-событие. Команда Codex не отправлялась.")
        self.refresh()

    def show_provenance(self) -> None:
        messagebox.showinfo("Provenance", "Данные получены из санитизированной fixture live-controls-normalized.json, закреплённой за codex-cli 0.170.0.")


def main() -> None:
    root = tk.Tk()
    OrbitaDesktop(root)
    root.mainloop()


if __name__ == "__main__":
    main()
