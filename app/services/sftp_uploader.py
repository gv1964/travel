from __future__ import annotations

import logging
from pathlib import Path, PurePosixPath
from typing import Iterable

import paramiko

from app.config import ServerConfig
from app.services.ssh_client import SshConnectionError, connect_ssh


LOGGER = logging.getLogger(__name__)


class UploadError(RuntimeError):
    """Raised when a lead file cannot be uploaded."""


class SftpUploader:
    def __init__(self, config: ServerConfig) -> None:
        self.config = config

    def upload_files(self, files: Iterable[Path]) -> list[str]:
        file_paths = [Path(path).expanduser().resolve() for path in files]
        missing = [str(path) for path in file_paths if not path.is_file()]
        if missing:
            raise UploadError("File non trovati: " + ", ".join(missing))

        if not file_paths:
            raise UploadError("Nessun file selezionato")

        uploaded: list[str] = []
        try:
            with self._connect() as ssh:
                sftp = ssh.open_sftp()
                try:
                    self._ensure_remote_dir(sftp, self.config.remote_dir)
                    for file_path in file_paths:
                        remote_path = str(PurePosixPath(self.config.remote_dir) / file_path.name)
                        LOGGER.info("Carico %s su %s", file_path, remote_path)
                        sftp.put(str(file_path), remote_path)
                        uploaded.append(remote_path)
                finally:
                    sftp.close()
        except SshConnectionError as exc:
            raise UploadError(str(exc)) from exc
        except Exception as exc:  # paramiko raises several transport/auth exceptions.
            raise UploadError(f"Upload fallito: {exc}") from exc

        return uploaded

    def _connect(self) -> paramiko.SSHClient:
        return connect_ssh(self.config)

    @staticmethod
    def _ensure_remote_dir(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
        current = PurePosixPath("/")
        for part in PurePosixPath(remote_dir).parts:
            if part in ("", "/"):
                continue
            current = current / part
            try:
                sftp.stat(str(current))
            except FileNotFoundError:
                sftp.mkdir(str(current))
