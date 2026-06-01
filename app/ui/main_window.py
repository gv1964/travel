from __future__ import annotations

import logging
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.config import ConfigError, ServerConfig, load_config
from app.services.sftp_uploader import SftpUploader, UploadError


LOGGER = logging.getLogger(__name__)
EXCEL_TYPES = (
    ("File Excel", "*.xlsx *.xls *.xlsm"),
    ("Tutti i file", "*.*"),
)


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SpostaLeads")
        self.geometry("720x480")
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.selected_files: list[Path] = []
        self.config: ServerConfig | None = None

        self._build_layout()
        self._load_config()

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        title = ctk.CTkLabel(
            self,
            text="SpostaLeads - caricamento Excel sul server",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, padx=24, pady=(20, 8), sticky="w")

        self.config_label = ctk.CTkLabel(self, text="Config: non caricata")
        self.config_label.grid(row=1, column=0, padx=24, pady=(0, 8), sticky="w")

        self.files_text = ctk.CTkTextbox(self, height=190)
        self.files_text.grid(row=2, column=0, padx=24, pady=8, sticky="nsew")
        self.files_text.insert("1.0", "Nessun file selezionato.\n")
        self.files_text.configure(state="disabled")

        buttons = ctk.CTkFrame(self)
        buttons.grid(row=3, column=0, padx=24, pady=12, sticky="ew")
        buttons.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(buttons, text="Seleziona file Excel", command=self._select_files).grid(
            row=0, column=0, padx=8, pady=8, sticky="ew"
        )
        self.upload_button = ctk.CTkButton(
            buttons,
            text="Carica sul server",
            command=self._upload_selected_files,
            state="disabled",
        )
        self.upload_button.grid(row=0, column=1, padx=8, pady=8, sticky="ew")
        self.desktop_button = ctk.CTkButton(
            buttons,
            text="Apri desktop Ubuntu",
            command=self._open_desktop,
            state="disabled",
        )
        self.desktop_button.grid(row=0, column=2, padx=8, pady=8, sticky="ew")

        self.status_label = ctk.CTkLabel(self, text="Pronto")
        self.status_label.grid(row=4, column=0, padx=24, pady=(0, 18), sticky="w")

    def _load_config(self) -> None:
        try:
            self.config = load_config()
        except ConfigError as exc:
            self.status_label.configure(text=str(exc))
            self.config_label.configure(text="Config: server.local.json mancante o incompleto")
            return

        self.config_label.configure(
            text=f"Config: {self.config.username}@{self.config.host}:{self.config.port}"
        )
        self.upload_button.configure(state="normal")
        if self.config.desktop_url:
            self.desktop_button.configure(state="normal")

    def _select_files(self) -> None:
        files = filedialog.askopenfilenames(title="Seleziona file Excel", filetypes=EXCEL_TYPES)
        self.selected_files = [Path(path) for path in files]
        self._render_selected_files()

    def _render_selected_files(self) -> None:
        self.files_text.configure(state="normal")
        self.files_text.delete("1.0", "end")
        if not self.selected_files:
            self.files_text.insert("1.0", "Nessun file selezionato.\n")
        else:
            for path in self.selected_files:
                self.files_text.insert("end", f"- {path}\n")
        self.files_text.configure(state="disabled")

    def _upload_selected_files(self) -> None:
        if not self.config:
            messagebox.showerror("Configurazione mancante", "Configura server.local.json.")
            return
        if not self.selected_files:
            messagebox.showwarning("Nessun file", "Seleziona almeno un file Excel.")
            return

        self.upload_button.configure(state="disabled")
        self.status_label.configure(text="Caricamento in corso...")
        thread = threading.Thread(target=self._upload_worker, daemon=True)
        thread.start()

    def _upload_worker(self) -> None:
        assert self.config is not None
        try:
            uploaded = SftpUploader(self.config).upload_files(self.selected_files)
        except UploadError as exc:
            LOGGER.exception("Upload non riuscito")
            self.after(0, self._upload_failed, str(exc))
            return
        self.after(0, self._upload_completed, uploaded)

    def _upload_failed(self, message: str) -> None:
        self.upload_button.configure(state="normal")
        self.status_label.configure(text="Upload fallito")
        messagebox.showerror("Upload fallito", message)

    def _upload_completed(self, uploaded: list[str]) -> None:
        self.upload_button.configure(state="normal")
        self.status_label.configure(text=f"Upload completato: {len(uploaded)} file")
        messagebox.showinfo("Upload completato", "\n".join(uploaded))

    def _open_desktop(self) -> None:
        if self.config and self.config.desktop_url:
            webbrowser.open(self.config.desktop_url)


def run() -> None:
    MainWindow().mainloop()
