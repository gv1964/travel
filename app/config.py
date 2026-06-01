from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT_DIR / "server.local.json"
EXAMPLE_CONFIG_PATH = ROOT_DIR / "server.local.json.example"


class ConfigError(RuntimeError):
    """Raised when the local server configuration is missing or invalid."""


@dataclass(frozen=True)
class ServerConfig:
    host: str
    port: int
    username: str
    password: str
    remote_dir: str
    desktop_url: str = ""

    @property
    def is_ready(self) -> bool:
        return bool(self.host and self.username and self.password and self.remote_dir)

    def redacted(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": "***" if self.password else "",
            "remote_dir": self.remote_dir,
            "desktop_url": self.desktop_url,
        }


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> ServerConfig:
    if not path.exists():
        raise ConfigError(
            f"Config mancante: {path}. Copia {EXAMPLE_CONFIG_PATH.name} "
            f"in {path.name} e inserisci le credenziali SSH."
        )

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"JSON non valido in {path}: {exc}") from exc

    return _parse_config(data)


def load_example_config() -> ServerConfig:
    data = json.loads(EXAMPLE_CONFIG_PATH.read_text(encoding="utf-8"))
    return _parse_config(data, require_password=False)


def _parse_config(data: dict[str, Any], require_password: bool = True) -> ServerConfig:
    missing = [name for name in ("host", "username", "remote_dir") if not data.get(name)]
    if require_password and not data.get("password"):
        missing.append("password")
    if missing:
        raise ConfigError("Campi obbligatori mancanti: " + ", ".join(missing))

    try:
        port = int(data.get("port", 22))
    except (TypeError, ValueError) as exc:
        raise ConfigError("Il campo 'port' deve essere un numero intero") from exc

    return ServerConfig(
        host=str(data.get("host", "")),
        port=port,
        username=str(data.get("username", "")),
        password=str(data.get("password", "")),
        remote_dir=str(data.get("remote_dir", "")),
        desktop_url=str(data.get("desktop_url", "")),
    )
