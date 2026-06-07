from __future__ import annotations

import logging
import socket

import paramiko
from paramiko.ssh_exception import AuthenticationException, SSHException

from app.config import ServerConfig


LOGGER = logging.getLogger(__name__)


class SshConnectionError(RuntimeError):
    """Raised when the SSH session cannot be established."""


def connect_ssh(config: ServerConfig) -> paramiko.SSHClient:
    if not config.password:
        raise SshConnectionError(
            "Password SSH mancante. Inseriscila nel campo Password SSH "
            "oppure in server.local.json."
        )

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

    try:
        client.connect(
            hostname=config.host,
            port=config.port,
            username=config.username,
            password=config.password,
            timeout=30,
            banner_timeout=30,
            auth_timeout=30,
            look_for_keys=False,
            allow_agent=False,
        )
        return client
    except (AuthenticationException, SSHException, EOFError) as exc:
        LOGGER.info("Autenticazione standard fallita, provo keyboard-interactive: %s", exc)
        client.close()
    except (socket.timeout, TimeoutError, OSError) as exc:
        raise SshConnectionError(format_ssh_error(exc)) from exc

    try:
        return _connect_keyboard_interactive(config)
    except Exception as exc:
        raise SshConnectionError(format_ssh_error(exc)) from exc


def _connect_keyboard_interactive(config: ServerConfig) -> paramiko.SSHClient:
    password = config.password

    def handler(title, instructions, prompt_list):
        if len(prompt_list) != 1:
            raise SSHException("Il server ha richiesto piu' campi di autenticazione.")
        return [password]

    transport = paramiko.Transport((config.host, config.port))
    try:
        transport.start_client(timeout=30)
        transport.auth_interactive(config.username, handler)
    except Exception:
        transport.close()
        raise

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client._transport = transport
    client._auth_username = config.username
    return client


def format_ssh_error(exc: Exception) -> str:
    message = str(exc) or exc.__class__.__name__
    lowered = message.lower()

    if "authentication" in lowered or "auth" in lowered:
        return (
            "Autenticazione SSH fallita: password errata.\n"
            "Controlla la password nel campo Password SSH."
        )
    if "eof" in lowered:
        return (
            "Connessione SSH interrotta.\n\n"
            "Verifica:\n"
            "- password SSH corretta\n"
            "- server 164.132.43.122 raggiungibile\n"
            "- utente ubuntu corretto\n"
            "- connessione internet attiva"
        )
    if "timed out" in lowered or "timeout" in lowered:
        return "Timeout di connessione al server. Verifica rete e indirizzo server."
    return f"Connessione SSH fallita: {message}"
