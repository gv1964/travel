from __future__ import annotations

import logging
import shlex

import paramiko

from app.config import ServerConfig


LOGGER = logging.getLogger(__name__)


class RemoteDesktopError(RuntimeError):
    """Raised when a command cannot be started on the remote desktop."""


class RemoteDesktopLauncher:
    def __init__(self, config: ServerConfig) -> None:
        self.config = config

    def open_crm_import(self) -> str:
        script = _build_open_crm_script(
            crm_url=self.config.crm_url,
            desktop_dir=self.config.remote_desktop_dir,
        )
        try:
            with self._connect() as ssh:
                stdin, stdout, stderr = ssh.exec_command(script, timeout=20)
                stdin.close()
                exit_code = stdout.channel.recv_exit_status()
                output = stdout.read().decode("utf-8", errors="replace").strip()
                error = stderr.read().decode("utf-8", errors="replace").strip()
        except Exception as exc:
            raise RemoteDesktopError(f"Comando remoto fallito: {exc}") from exc

        if exit_code != 0:
            raise RemoteDesktopError(error or output or f"Comando remoto uscito con {exit_code}")

        LOGGER.info("CRM remoto avviato: %s", output)
        return output or "CRM aperto sul desktop Ubuntu remoto"

    def _connect(self) -> paramiko.SSHClient:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=self.config.host,
            port=self.config.port,
            username=self.config.username,
            password=self.config.password,
            timeout=20,
            banner_timeout=20,
            auth_timeout=20,
        )
        return client


def _build_open_crm_script(crm_url: str, desktop_dir: str) -> str:
    quoted_url = shlex.quote(crm_url)
    quoted_desktop_dir = shlex.quote(desktop_dir)
    return f"""bash -lc {shlex.quote(f'''
set -e
CRM_URL={quoted_url}
DESKTOP_DIR={quoted_desktop_dir}

if [ -z "${{DISPLAY:-}}" ]; then
  for candidate in :1 :0 :2 :10; do
    socket="/tmp/.X11-unix/X${{candidate#:}}"
    if [ -S "$socket" ]; then
      export DISPLAY="$candidate"
      break
    fi
  done
fi

if [ -z "${{DISPLAY:-}}" ]; then
  echo "Nessuna sessione grafica Ubuntu trovata: apri prima ubuntu-desktop." >&2
  exit 1
fi

session_pid="$(pgrep -u "$USER" -n xfce4-session 2>/dev/null || true)"
if [ -z "$session_pid" ]; then
  session_pid="$(pgrep -u "$USER" -n gnome-session 2>/dev/null || true)"
fi
if [ -n "$session_pid" ] && [ -r "/proc/$session_pid/environ" ]; then
  dbus="$(tr "\\0" "\\n" < "/proc/$session_pid/environ" | awk -F= '$1=="DBUS_SESSION_BUS_ADDRESS" {{print $2; exit}}')"
  if [ -n "$dbus" ]; then
    export DBUS_SESSION_BUS_ADDRESS="$dbus"
  fi
fi

if [ -f "$HOME/.Xauthority" ]; then
  export XAUTHORITY="$HOME/.Xauthority"
fi

mkdir -p "$DESKTOP_DIR" "$HOME/.config/gtk-3.0"
bookmark="file://$DESKTOP_DIR Desktop"
grep -qxF "$bookmark" "$HOME/.config/gtk-3.0/bookmarks" 2>/dev/null || \\
  printf "%s\\n" "$bookmark" >> "$HOME/.config/gtk-3.0/bookmarks"

(xdg-open "$DESKTOP_DIR" >/tmp/normalizzaleads-filemanager.log 2>&1 || true) &
sleep 1
cd "$DESKTOP_DIR"

if command -v google-chrome >/dev/null 2>&1; then
  nohup google-chrome "$CRM_URL" >/tmp/normalizzaleads-crm.log 2>&1 &
elif command -v google-chrome-stable >/dev/null 2>&1; then
  nohup google-chrome-stable "$CRM_URL" >/tmp/normalizzaleads-crm.log 2>&1 &
elif command -v chromium >/dev/null 2>&1; then
  nohup chromium "$CRM_URL" >/tmp/normalizzaleads-crm.log 2>&1 &
elif command -v chromium-browser >/dev/null 2>&1; then
  nohup chromium-browser "$CRM_URL" >/tmp/normalizzaleads-crm.log 2>&1 &
elif command -v firefox >/dev/null 2>&1; then
  nohup firefox "$CRM_URL" >/tmp/normalizzaleads-crm.log 2>&1 &
else
  nohup xdg-open "$CRM_URL" >/tmp/normalizzaleads-crm.log 2>&1 &
fi

echo "CRM aperto su $DISPLAY; Desktop remoto: $DESKTOP_DIR"
''')}"""
