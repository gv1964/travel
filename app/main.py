from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from app.config import ConfigError, load_config, load_example_config
from app.services.remote_desktop import RemoteDesktopError, RemoteDesktopLauncher
from app.services.sftp_uploader import SftpUploader, UploadError
from app.utils.logging_config import configure_logging


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SpostaLeads")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verifica dipendenze e configurazione esempio senza aprire la GUI.",
    )
    parser.add_argument(
        "--upload",
        nargs="+",
        metavar="FILE",
        help="Carica uno o piu' file Excel via SFTP senza aprire la GUI.",
    )
    parser.add_argument(
        "--open-remote-crm",
        action="store_true",
        help="Apre il CRM nel browser della sessione grafica Ubuntu remota.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    configure_logging()
    args = build_parser().parse_args(argv)

    if args.check:
        return _check()

    if args.upload:
        return _upload(args.upload)

    if args.open_remote_crm:
        return _open_remote_crm()

    from app.ui.main_window import run

    run()
    return 0


def _check() -> int:
    try:
        import customtkinter  # noqa: F401
        import paramiko  # noqa: F401
    except ImportError as exc:
        print(f"Dipendenza Python mancante: {exc}", file=sys.stderr)
        return 1

    try:
        example = load_example_config()
    except ConfigError as exc:
        print(f"Configurazione esempio non valida: {exc}", file=sys.stderr)
        return 1

    print("Ambiente Python OK")
    print("Dipendenze importate: customtkinter, paramiko")
    print("Configurazione esempio:")
    print(json.dumps(example.redacted(), indent=2))

    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Nota: {exc}")
    else:
        print("Configurazione locale:")
        print(json.dumps(config.redacted(), indent=2))

    return 0


def _upload(files: list[str]) -> int:
    try:
        config = load_config()
        uploaded = SftpUploader(config).upload_files(Path(file) for file in files)
    except (ConfigError, UploadError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print("Upload completato:")
    for remote_path in uploaded:
        print(f"- {remote_path}")
    return 0


def _open_remote_crm() -> int:
    try:
        config = load_config()
        message = RemoteDesktopLauncher(config).open_crm_import()
    except (ConfigError, RemoteDesktopError) as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
