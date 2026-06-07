from __future__ import annotations

import logging
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.config import ConfigError, ServerConfig, load_config
from app.services.remote_desktop import RemoteDesktopError, RemoteDesktopLauncher
from app.services.sftp_uploader import SftpUploader, UploadError


LOGGER = logging.getLogger(__name__)
EXCEL_TYPES = (
    ("File Excel", "*.xlsx *.xls *.xlsm"),
    ("Tutti i file", "*.*"),
)
EMPTY_FILE_LABEL = "Nessun file selezionato"


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("NormalizzaLeads / SpostaLeads")
        self.geometry("720x540")
        ctk.set_appearance_mode("system")
        ctk.set_default_color_theme("blue")

        self.instagram_file: Path | None = None
        self.tiktok_file: Path | None = None
        self.config: ServerConfig | None = None

        self._build_layout()
        self._load_config()

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        title = ctk.CTkLabel(
            self,
            text="NormalizzaLeads - caricamento Excel sul server",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        title.grid(row=0, column=0, padx=24, pady=(20, 8), sticky="w")

        self.config_label = ctk.CTkLabel(self, text="Config: non caricata")
        self.config_label.grid(row=1, column=0, padx=24, pady=(0, 8), sticky="w")

        hint = ctk.CTkLabel(
            self,
            text="Puoi caricare solo Instagram, solo TikTok oppure entrambi.",
            text_color="gray",
        )
        hint.grid(row=2, column=0, padx=24, pady=(0, 8), sticky="w")

        files_frame = ctk.CTkFrame(self)
        files_frame.grid(row=3, column=0, padx=24, pady=8, sticky="ew")
        files_frame.grid_columnconfigure(1, weight=1)

        self.instagram_path_label = self._add_file_row(
            files_frame,
            row=0,
            title="File leads Instagram",
            select_command=self._select_instagram_file,
            clear_command=self._clear_instagram_file,
        )
        self.tiktok_path_label = self._add_file_row(
            files_frame,
            row=1,
            title="File leads TikTok",
            select_command=self._select_tiktok_file,
            clear_command=self._clear_tiktok_file,
        )

        buttons = ctk.CTkFrame(self)
        buttons.grid(row=4, column=0, padx=24, pady=12, sticky="ew")
        buttons.grid_columnconfigure((0, 1, 2), weight=1)

        self.upload_button = ctk.CTkButton(
            buttons,
            text="Carica sul server",
            command=self._upload_selected_files,
            state="disabled",
        )
        self.upload_button.grid(row=0, column=0, padx=8, pady=8, sticky="ew")
        self.desktop_button = ctk.CTkButton(
            buttons,
            text="Apri desktop Ubuntu",
            command=self._open_desktop,
            state="disabled",
        )
        self.desktop_button.grid(row=0, column=1, padx=8, pady=8, sticky="ew")
        self.crm_button = ctk.CTkButton(
            buttons,
            text="Apri CRM sul server",
            command=self._open_remote_crm,
            state="disabled",
        )
        self.crm_button.grid(row=0, column=2, padx=8, pady=8, sticky="ew")

        self.status_label = ctk.CTkLabel(self, text="Pronto")
        self.status_label.grid(row=5, column=0, padx=24, pady=(0, 18), sticky="w")

    def _add_file_row(
        self,
        parent: ctk.CTkFrame,
        row: int,
        title: str,
        select_command,
        clear_command,
    ) -> ctk.CTkLabel:
        ctk.CTkLabel(parent, text=title, font=ctk.CTkFont(weight="bold")).grid(
            row=row, column=0, padx=(12, 8), pady=12, sticky="nw"
        )

        path_label = ctk.CTkLabel(
            parent,
            text=EMPTY_FILE_LABEL,
            anchor="w",
            justify="left",
            wraplength=360,
        )
        path_label.grid(row=row, column=1, padx=8, pady=12, sticky="ew")

        actions = ctk.CTkFrame(parent, fg_color="transparent")
        actions.grid(row=row, column=2, padx=(8, 12), pady=12, sticky="e")

        ctk.CTkButton(actions, text="Seleziona", width=90, command=select_command).grid(
            row=0, column=0, padx=(0, 6)
        )
        ctk.CTkButton(
            actions,
            text="Rimuovi",
            width=90,
            fg_color="gray35",
            hover_color="gray25",
            command=clear_command,
        ).grid(row=0, column=1)

        return path_label

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
        self.crm_button.configure(state="normal")
        if self.config.desktop_url:
            self.desktop_button.configure(state="normal")

    def _select_instagram_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Seleziona file leads Instagram",
            filetypes=EXCEL_TYPES,
        )
        if file_path:
            self.instagram_file = Path(file_path)
            self._render_file_label(self.instagram_path_label, self.instagram_file)

    def _select_tiktok_file(self) -> None:
        file_path = filedialog.askopenfilename(
            title="Seleziona file leads TikTok",
            filetypes=EXCEL_TYPES,
        )
        if file_path:
            self.tiktok_file = Path(file_path)
            self._render_file_label(self.tiktok_path_label, self.tiktok_file)

    def _clear_instagram_file(self) -> None:
        self.instagram_file = None
        self._render_file_label(self.instagram_path_label, None)

    def _clear_tiktok_file(self) -> None:
        self.tiktok_file = None
        self._render_file_label(self.tiktok_path_label, None)

    @staticmethod
    def _render_file_label(label: ctk.CTkLabel, file_path: Path | None) -> None:
        label.configure(text=str(file_path) if file_path else EMPTY_FILE_LABEL)

    def _files_to_upload(self) -> list[Path]:
        return [path for path in (self.instagram_file, self.tiktok_file) if path is not None]

    def _upload_selected_files(self) -> None:
        if not self.config:
            messagebox.showerror("Configurazione mancante", "Configura server.local.json.")
            return

        files_to_upload = self._files_to_upload()
        if not files_to_upload:
            messagebox.showwarning(
                "Nessun file",
                "Seleziona almeno un file: Instagram oppure TikTok.\n"
                "L'altro puo' restare vuoto.",
            )
            return

        self.upload_button.configure(state="disabled")
        skipped = []
        if self.instagram_file is None:
            skipped.append("Instagram")
        if self.tiktok_file is None:
            skipped.append("TikTok")

        if skipped:
            self.status_label.configure(
                text=f"Caricamento in corso ({', '.join(skipped)} saltato/i)..."
            )
        else:
            self.status_label.configure(text="Caricamento in corso...")

        thread = threading.Thread(
            target=self._upload_worker,
            args=(files_to_upload,),
            daemon=True,
        )
        thread.start()

    def _upload_worker(self, files_to_upload: list[Path]) -> None:
        assert self.config is not None
        try:
            uploaded = SftpUploader(self.config).upload_files(files_to_upload)
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

    def _open_remote_crm(self) -> None:
        if not self.config:
            messagebox.showerror("Configurazione mancante", "Configura server.local.json.")
            return

        self.crm_button.configure(state="disabled")
        self.status_label.configure(text="Apro il CRM sul desktop Ubuntu remoto...")
        thread = threading.Thread(target=self._open_remote_crm_worker, daemon=True)
        thread.start()

    def _open_remote_crm_worker(self) -> None:
        assert self.config is not None
        try:
            message = RemoteDesktopLauncher(self.config).open_crm_import()
        except RemoteDesktopError as exc:
            LOGGER.exception("Apertura CRM remoto non riuscita")
            self.after(0, self._open_remote_crm_failed, str(exc))
            return
        self.after(0, self._open_remote_crm_completed, message)

    def _open_remote_crm_failed(self, message: str) -> None:
        self.crm_button.configure(state="normal")
        self.status_label.configure(text="Apertura CRM remoto fallita")
        messagebox.showerror("CRM remoto non avviato", message)

    def _open_remote_crm_completed(self, message: str) -> None:
        self.crm_button.configure(state="normal")
        self.status_label.configure(text=message)
        messagebox.showinfo(
            "CRM aperto sul server",
            message
            + "\n\nNel browser del desktop Ubuntu, il selettore file vedra' "
            + "i file del server. Usa la cartella Desktop.",
        )


def run() -> None:
    MainWindow().mainloop()
