from __future__ import annotations

import logging
import shlex
from pathlib import Path, PurePosixPath
from typing import Iterable

import paramiko
from paramiko.ssh_exception import SSHException
from scp import SCPClient

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
                try:
                    uploaded = self._upload_via_sftp(ssh, file_paths)
                except SSHException as exc:
                    LOGGER.warning("SFTP non disponibile (%s), uso SCP", exc)
                    uploaded = self._upload_via_scp(ssh, file_paths)
        except SshConnectionError as exc:
            raise UploadError(str(exc)) from exc
        except Exception as exc:
            raise UploadError(f"Upload fallito: {exc}") from exc

        return uploaded

    def _connect(self) -> paramiko.SSHClient:
        return connect_ssh(self.config)

    def _upload_via_sftp(self, ssh: paramiko.SSHClient, file_paths: list[Path]) -> list[str]:
        uploaded: list[str] = []
        sftp = ssh.open_sftp()
        try:
            self._ensure_remote_dir_sftp(sftp, self.config.remote_dir)
            for file_path in file_paths:
                remote_path = str(PurePosixPath(self.config.remote_dir) / file_path.name)
                LOGGER.info("Carico via SFTP %s su %s", file_path, remote_path)
                sftp.put(str(file_path), remote_path)
                uploaded.append(remote_path)
        finally:
            sftp.close()
        return uploaded

    def _upload_via_scp(self, ssh: paramiko.SSHClient, file_paths: list[Path]) -> list[str]:
        self._ensure_remote_dir_ssh(ssh, self.config.remote_dir)
        uploaded: list[str] = []

        with SCPClient(ssh.get_transport()) as scp:
            for file_path in file_paths:
                remote_path = str(PurePosixPath(self.config.remote_dir) / file_path.name)
                LOGGER.info("Carico via SCP %s su %s", file_path, remote_path)
                scp.put(str(file_path), remote_path=remote_path)
                uploaded.append(remote_path)

        return uploaded

    @staticmethod
    def _ensure_remote_dir_sftp(sftp: paramiko.SFTPClient, remote_dir: str) -> None:
        current = PurePosixPath("/")
        for part in PurePosixPath(remote_dir).parts:
            if part in ("", "/"):
                continue
            current = current / part
            try:
                sftp.stat(str(current))
            except FileNotFoundError:
                sftp.mkdir(str(current))

    @staticmethod
    def _ensure_remote_dir_ssh(ssh: paramiko.SSHClient, remote_dir: str) -> None:
        command = f"mkdir -p {shlex.quote(remote_dir)}"
        _, stdout, stderr = ssh.exec_command(command, timeout=20)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            error = stderr.read().decode("utf-8", errors="replace").strip()
            raise UploadError(error or f"Impossibile creare la cartella remota: {remote_dir}")
