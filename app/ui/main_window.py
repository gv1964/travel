from __future__ import annotations

import logging
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk

from app.config import DEFAULT_CONFIG_PATH, ConfigError, ServerConfig, load_config
from app.services.remote_desktop import RemoteDesktopError, RemoteDesktopLauncher
from app.services.sftp_uploader import SftpUploader, UploadError


LOGGER = logging.getLogger(__name__)
EXCEL_TYPES = (
    ("File Excel", "*.xlsx *.xls *.xlsm"),
    ("Tutti i file", "*.*"),
)

DEFAULT_HOST = "164.132.43.122"
DEFAULT_USERNAME = "ubuntu"
DEFAULT_REMOTE_DIR = "/home/ubuntu/Desktop/Leads"


class MainWindow(ctk.CTk):
    def __init__(self) -> None:
        super().__init__()
        self.title("SpostaLeads")
        self.geometry("760x560")
        self.minsize(700, 520)
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self._password = ""
        self._crm_url = "http://crm.autovincenti.it:8082"
        self._desktop_url = ""
        self._transferred_count = 0
        self._transfer_total = 0

        self._build_layout()
        self._load_defaults()

    def _build_layout(self) -> None:
        self.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(self, fg_color="#2f6fed", corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="SpostaLeads",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color="white",
        ).grid(row=0, column=0, padx=24, pady=(18, 4), sticky="w")
        ctk.CTkLabel(
            header,
            text="Carica i file Excel Instagram e TikTok sul desktop Ubuntu (cartella Leads)",
            font=ctk.CTkFont(size=13),
            text_color="white",
        ).grid(row=1, column=0, padx=24, pady=(0, 18), sticky="w")

        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=1, column=0, padx=24, pady=20, sticky="ew")
        form.grid_columnconfigure(1, weight=1)

        self.instagram_entry = self._add_path_field(
            form, row=0, label="Leads Instagram", optional=True
        )
        self.tiktok_entry = self._add_path_field(
            form, row=1, label="Leads TikTok", optional=True
        )
        self.host_entry = self._add_text_field(form, row=2, label="Server Linux")
        self.user_entry = self._add_text_field(form, row=3, label="Utente SSH")
        self.password_entry = self._add_password_field(form, row=4, label="Password SSH")
        self.remote_dir_entry = self._add_text_field(form, row=5, label="Cartella remota Linux")

        ctk.CTkLabel(
            form,
            text="* Almeno uno tra Instagram e TikTok; l'altro puo' restare vuoto.",
            text_color="gray",
            font=ctk.CTkFont(size=12),
        ).grid(row=6, column=0, columnspan=3, padx=(0, 8), pady=(8, 0), sticky="w")

        self.progress_bar = ctk.CTkProgressBar(self)
        self.progress_bar.grid(row=2, column=0, padx=24, pady=(0, 6), sticky="ew")
        self.progress_bar.set(0)

        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.grid(row=3, column=0, padx=24, pady=(0, 12), sticky="ew")
        status_frame.grid_columnconfigure(0, weight=1)

        self.transfer_label = ctk.CTkLabel(status_frame, text="File trasferiti: 0/0")
        self.transfer_label.grid(row=0, column=0, sticky="w")
        self.status_label = ctk.CTkLabel(status_frame, text="Pronto")
        self.status_label.grid(row=0, column=1, sticky="e")

        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.grid(row=4, column=0, padx=24, pady=(0, 20), sticky="ew")
        buttons.grid_columnconfigure((0, 1, 2, 3), weight=1)

        ctk.CTkButton(buttons, text="Apri desktop Ubuntu", command=self._open_desktop).grid(
            row=0, column=0, padx=6, pady=6, sticky="ew"
        )
        ctk.CTkButton(
            buttons,
            text="Pulisci",
            fg_color="gray70",
            hover_color="gray55",
            text_color="black",
            command=self._clear_form,
        ).grid(row=0, column=1, padx=6, pady=6, sticky="ew")
        ctk.CTkButton(
            buttons,
            text="Esci",
            fg_color="gray70",
            hover_color="gray55",
            text_color="black",
            command=self.destroy,
        ).grid(row=0, column=2, padx=6, pady=6, sticky="ew")
        self.transfer_button = ctk.CTkButton(
            buttons,
            text="Trasferisci",
            command=self._transfer_files,
        )
        self.transfer_button.grid(row=0, column=3, padx=6, pady=6, sticky="ew")

        self.instagram_entry.bind("<KeyRelease>", self._on_lead_field_changed)
        self.tiktok_entry.bind("<KeyRelease>", self._on_lead_field_changed)

    def _add_path_field(
        self,
        parent: ctk.CTkFrame,
        row: int,
        label: str,
        optional: bool = False,
    ) -> ctk.CTkEntry:
        suffix = "" if optional else " *"
        ctk.CTkLabel(parent, text=f"{label}{suffix}:").grid(
            row=row, column=0, padx=(0, 12), pady=10, sticky="w"
        )
        entry = ctk.CTkEntry(parent)
        entry.grid(row=row, column=1, padx=(0, 8), pady=10, sticky="ew")
        ctk.CTkButton(
            parent,
            text="...",
            width=36,
            command=lambda e=entry, t=label: self._browse_file(e, t),
        ).grid(row=row, column=2, pady=10)
        return entry

    def _add_text_field(self, parent: ctk.CTkFrame, row: int, label: str) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=f"{label} *:").grid(
            row=row, column=0, padx=(0, 12), pady=10, sticky="w"
        )
        entry = ctk.CTkEntry(parent)
        entry.grid(row=row, column=1, columnspan=2, pady=10, sticky="ew")
        return entry

    def _add_password_field(self, parent: ctk.CTkFrame, row: int, label: str) -> ctk.CTkEntry:
        ctk.CTkLabel(parent, text=f"{label} *:").grid(
            row=row, column=0, padx=(0, 12), pady=10, sticky="w"
        )
        entry = ctk.CTkEntry(parent, show="*")
        entry.grid(row=row, column=1, columnspan=2, pady=10, sticky="ew")
        return entry

    def _load_defaults(self) -> None:
        self.host_entry.insert(0, DEFAULT_HOST)
        self.user_entry.insert(0, DEFAULT_USERNAME)
        self.remote_dir_entry.insert(0, DEFAULT_REMOTE_DIR)
        self._update_transfer_counter()

        if not DEFAULT_CONFIG_PATH.exists():
            return

        try:
            config = load_config()
        except ConfigError as exc:
            LOGGER.warning("Config locale non caricata: %s", exc)
            return

        self._password = config.password
        self._crm_url = config.crm_url
        self._desktop_url = config.desktop_url

        self._set_entry(self.host_entry, config.host)
        self._set_entry(self.user_entry, config.username)
        self._set_entry(self.password_entry, config.password)
        self._set_entry(self.remote_dir_entry, config.remote_dir or config.remote_desktop_dir)

    @staticmethod
    def _set_entry(entry: ctk.CTkEntry, value: str) -> None:
        entry.delete(0, "end")
        entry.insert(0, value)

    def _browse_file(self, entry: ctk.CTkEntry, title: str) -> None:
        file_path = filedialog.askopenfilename(title=f"Seleziona {title}", filetypes=EXCEL_TYPES)
        if file_path:
            self._set_entry(entry, file_path)
            self._on_lead_field_changed()

    def _on_lead_field_changed(self, _event=None) -> None:
        self._update_transfer_counter()

    def _lead_files_to_transfer(self) -> list[Path]:
        files: list[Path] = []
        for entry in (self.instagram_entry, self.tiktok_entry):
            path_text = entry.get().strip()
            if path_text:
                files.append(Path(path_text).expanduser())
        return files

    def _update_transfer_counter(self, transferred: int | None = None) -> None:
        if transferred is None:
            transferred = self._transferred_count
        total = len(self._lead_files_to_transfer())
        self._transfer_total = total
        self._transferred_count = transferred
        self.transfer_label.configure(text=f"File trasferiti: {transferred}/{total}")

    def _validate_form(self) -> str | None:
        instagram = self.instagram_entry.get().strip()
        tiktok = self.tiktok_entry.get().strip()
        host = self.host_entry.get().strip()
        username = self.user_entry.get().strip()
        remote_dir = self.remote_dir_entry.get().strip()

        if not instagram and not tiktok:
            return (
                "Seleziona almeno un file: Leads Instagram oppure Leads TikTok.\n"
                "L'altro campo puo' restare vuoto."
            )

        if not host:
            return "Seleziona o compila il campo: Server Linux."
        if not username:
            return "Seleziona o compila il campo: Utente SSH."
        if not remote_dir:
            return "Seleziona o compila il campo: Cartella remota Linux."

        for path_text in (instagram, tiktok):
            if path_text and not Path(path_text).expanduser().is_file():
                return f"File non trovato: {path_text}"

        password = self.password_entry.get().strip() or self._password
        if not password:
            return "Inserisci la password SSH nel campo Password SSH."

        return None

    def _build_config_from_form(self) -> ServerConfig:
        username = self.user_entry.get().strip()
        remote_dir = self.remote_dir_entry.get().strip()
        password = self.password_entry.get().strip() or self._password
        return ServerConfig(
            host=self.host_entry.get().strip(),
            port=22,
            username=username,
            password=password,
            remote_dir=remote_dir,
            remote_desktop_dir=remote_dir,
            crm_url=self._crm_url,
            desktop_url=self._desktop_url,
        )

    def _clear_form(self) -> None:
        for entry in (
            self.instagram_entry,
            self.tiktok_entry,
            self.host_entry,
            self.user_entry,
            self.password_entry,
            self.remote_dir_entry,
        ):
            entry.delete(0, "end")

        self.host_entry.insert(0, DEFAULT_HOST)
        self.user_entry.insert(0, DEFAULT_USERNAME)
        self.remote_dir_entry.insert(0, DEFAULT_REMOTE_DIR)
        if self._password:
            self.password_entry.insert(0, self._password)
        self.progress_bar.set(0)
        self._transferred_count = 0
        self._update_transfer_counter(0)
        self.status_label.configure(text="Pronto")

    def _transfer_files(self) -> None:
        error = self._validate_form()
        if error:
            messagebox.showwarning("Campi mancanti", error)
            return

        files_to_transfer = self._lead_files_to_transfer()
        config = self._build_config_from_form()

        self.transfer_button.configure(state="disabled")
        self._transferred_count = 0
        self._update_transfer_counter(0)
        self.progress_bar.set(0)
        self.status_label.configure(text="Trasferimento in corso...")

        thread = threading.Thread(
            target=self._transfer_worker,
            args=(config, files_to_transfer),
            daemon=True,
        )
        thread.start()

    def _transfer_worker(self, config: ServerConfig, files_to_transfer: list[Path]) -> None:
        uploaded: list[str] = []
        total = len(files_to_transfer)

        try:
            uploader = SftpUploader(config)
            for index, file_path in enumerate(files_to_transfer, start=1):
                uploaded.extend(uploader.upload_files([file_path]))
                progress = index / total
                self.after(0, self._transfer_progress, index, progress)
        except UploadError as exc:
            LOGGER.exception("Trasferimento non riuscito")
            self.after(0, self._transfer_failed, str(exc))
            return

        self.after(0, self._transfer_completed, uploaded)

    def _transfer_progress(self, transferred: int, progress: float) -> None:
        self._transferred_count = transferred
        self._update_transfer_counter(transferred)
        self.progress_bar.set(progress)

    def _transfer_failed(self, message: str) -> None:
        self.transfer_button.configure(state="normal")
        self.status_label.configure(text="Trasferimento fallito")
        messagebox.showerror("Trasferimento fallito", message)

    def _transfer_completed(self, uploaded: list[str]) -> None:
        self.transfer_button.configure(state="normal")
        self.progress_bar.set(1)
        self._update_transfer_counter(len(uploaded))
        self.status_label.configure(text="Trasferimento completato")
        messagebox.showinfo("Trasferimento completato", "\n".join(uploaded))

    def _open_desktop(self) -> None:
        if self._desktop_url:
            webbrowser.open(self._desktop_url)
            return
        messagebox.showinfo(
            "Desktop Ubuntu",
            "Apri il desktop Ubuntu dal link fornito dal reparto IT,\n"
            "oppure aggiungi desktop_url in server.local.json.",
        )


def run() -> None:
    MainWindow().mainloop()
