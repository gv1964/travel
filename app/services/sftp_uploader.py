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
        used_fallback = False
        remote_dir = self.config.remote_dir
        try:
            with self._connect() as ssh:
                remote_dir, used_fallback = self._resolve_writable_remote_dir(ssh)
                if used_fallback:
                    LOGGER.warning(
                        "Cartella configurata non scrivibile, uso %s", remote_dir
                    )

                self._prepare_remote_files(ssh, remote_dir, file_paths)

                try:
                    uploaded = self._upload_via_sftp(ssh, file_paths, remote_dir)
                except SSHException as exc:
                    LOGGER.warning("SFTP non disponibile (%s), uso SCP", exc)
                    uploaded = self._upload_via_scp(ssh, file_paths, remote_dir)
        except SshConnectionError as exc:
            raise UploadError(str(exc)) from exc
        except UploadError:
            raise
        except Exception as exc:
            raise UploadError(self._format_upload_error(exc)) from exc

        if used_fallback:
            uploaded.append(
                f"\nNota: i file sono stati caricati in {remote_dir} "
                f"perche' {self.config.remote_dir} non e' scrivibile."
            )

        return uploaded

    def _connect(self) -> paramiko.SSHClient:
        return connect_ssh(self.config)

    def _candidate_remote_dirs(self) -> list[str]:
        home = f"/home/{self.config.username}"
        candidates = [
            self.config.remote_dir,
            f"{home}/Desktop/Leads",
            f"{home}/Leads",
            f"{home}/Desktop",
        ]
        unique: list[str] = []
        for candidate in candidates:
            normalized = str(PurePosixPath(candidate))
            if normalized not in unique:
                unique.append(normalized)
        return unique

    def _resolve_writable_remote_dir(self, ssh: paramiko.SSHClient) -> tuple[str, bool]:
        configured = str(PurePosixPath(self.config.remote_dir))
        failures: list[str] = []

        for candidate in self._candidate_remote_dirs():
            if self._prepare_remote_directory(ssh, candidate):
                return candidate, candidate != configured
            failures.append(candidate)

        raise UploadError(self._permission_help_message(failures))

    def _prepare_remote_directory(self, ssh: paramiko.SSHClient, remote_dir: str) -> bool:
        quoted_dir = shlex.quote(remote_dir)
        quoted_parent = shlex.quote(str(PurePosixPath(remote_dir).parent))
        quoted_test = shlex.quote(f"{remote_dir}/.spostaleads_write_test")
        username = shlex.quote(self.config.username)

        command = (
            f"mkdir -p {quoted_dir} && "
            f"sudo -n chown -R {username}:{username} {quoted_dir} 2>/dev/null || true; "
            f"chmod u+rwx {quoted_dir} 2>/dev/null || true; "
            f"if [ ! -w {quoted_dir} ] && [ -d {quoted_dir} ] && [ -w {quoted_parent} ]; then "
            f"if [ -z \"$(ls -A {quoted_dir} 2>/dev/null)\" ]; then "
            f"rmdir {quoted_dir} 2>/dev/null || true; "
            f"mkdir -p {quoted_dir}; "
            f"chmod 755 {quoted_dir}; "
            f"fi; "
            f"fi; "
            f"touch {quoted_test} 2>/dev/null && rm -f {quoted_test}"
        )
        exit_code = self._run_ssh_command(ssh, command)
        return exit_code == 0

    def _prepare_remote_files(
        self,
        ssh: paramiko.SSHClient,
        remote_dir: str,
        file_paths: list[Path],
    ) -> None:
        for file_path in file_paths:
            remote_file = str(PurePosixPath(remote_dir) / file_path.name)
            quoted_file = shlex.quote(remote_file)
            command = (
                f"if [ -e {quoted_file} ] && [ ! -w {quoted_file} ]; then "
                f"chmod u+w {quoted_file} 2>/dev/null || rm -f {quoted_file} 2>/dev/null || true; "
                f"fi"
            )
            self._run_ssh_command(ssh, command)

    def _upload_via_sftp(
        self,
        ssh: paramiko.SSHClient,
        file_paths: list[Path],
        remote_dir: str,
    ) -> list[str]:
        uploaded: list[str] = []
        sftp = ssh.open_sftp()
        try:
            self._ensure_remote_dir_sftp(sftp, remote_dir)
            for file_path in file_paths:
                remote_path = str(PurePosixPath(remote_dir) / file_path.name)
                LOGGER.info("Carico via SFTP %s su %s", file_path, remote_path)
                sftp.put(str(file_path), remote_path)
                uploaded.append(remote_path)
        finally:
            sftp.close()
        return uploaded

    def _upload_via_scp(
        self,
        ssh: paramiko.SSHClient,
        file_paths: list[Path],
        remote_dir: str,
    ) -> list[str]:
        uploaded: list[str] = []
        remote_dir_with_slash = str(PurePosixPath(remote_dir)) + "/"

        with SCPClient(ssh.get_transport()) as scp:
            for file_path in file_paths:
                remote_path = str(PurePosixPath(remote_dir) / file_path.name)
                LOGGER.info("Carico via SCP %s su %s", file_path, remote_path)
                scp.put(str(file_path), remote_path=remote_dir_with_slash)
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
                sftp.mkdir(str(current), mode=0o755)

    @staticmethod
    def _run_ssh_command(ssh: paramiko.SSHClient, command: str) -> int:
        _, stdout, stderr = ssh.exec_command(command, timeout=30)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code != 0:
            error = stderr.read().decode("utf-8", errors="replace").strip()
            LOGGER.debug("Comando SSH fallito (%s): %s", exit_code, error or command)
        return exit_code

    def _permission_help_message(self, tried_dirs: list[str]) -> str:
        username = self.config.username
        configured = self.config.remote_dir
        tried = "\n".join(f"- {path}" for path in tried_dirs)
        return (
            "Permesso negato sul server Ubuntu: impossibile scrivere i file.\n\n"
            f"Cartella configurata: {configured}\n"
            f"Cartelle provate:\n{tried}\n\n"
            "Sul server Ubuntu apri un terminale ed esegui:\n"
            f"  mkdir -p {configured}\n"
            f"  sudo chown -R {username}:{username} {configured}\n"
            f"  chmod u+rwx {configured}\n\n"
            "Poi riprova il trasferimento da SpostaLeads."
        )

    @staticmethod
    def _format_upload_error(exc: Exception) -> str:
        message = str(exc).strip() or exc.__class__.__name__
        lowered = message.lower()
        if "permission denied" in lowered:
            return (
                "Permesso negato sul server Ubuntu durante il caricamento.\n\n"
                f"Dettaglio: {message}\n\n"
                "Verifica che la cartella remota sia scrivibile dall'utente ubuntu."
            )
        return f"Upload fallito: {message}"
