# AGENTS.md

## Cursor Cloud specific instructions

### Repository layout

`main` contains only a placeholder README. Runnable application code lives on feature branches:

| Branch | Contents |
|--------|----------|
| `cursor/setup-normalizza-leads-3bc4` | **SpostaLeads** Python desktop app (GUI + CLI) |
| `cursor/fix-espo-lead-button-df28` | EspoCRM customizations (PHP/JS metadata for remote deploy) |

For local development and testing, check out `cursor/setup-normalizza-leads-3bc4`:

```bash
git checkout cursor/setup-normalizza-leads-3bc4
```

### System dependencies (one-time per VM)

Tkinter and venv support are required and are **not** installed by the update script:

```bash
sudo apt-get update
sudo apt-get install -y python3.12-venv python3-tk
```

### SpostaLeads (Python app)

See `README.md` on branch `cursor/setup-normalizza-leads-3bc4` for full usage.

| Task | Command |
|------|---------|
| Install deps + verify | `./scripts/start.sh --check` |
| Launch GUI | `./scripts/start.sh` |
| Split CSV (no infra) | `./scripts/start.sh --split-csv FILE.csv --rows-per-file 300` |
| SFTP upload | Copy `server.local.json.example` → `server.local.json`, add SSH password, then `./scripts/start.sh --upload file.xlsx` |

**Config:** `server.local.json` is gitignored and holds SSH credentials. Without it, `--check` and `--split-csv` still work; `--upload` and `--open-remote-crm` require it.

**Remote services:** SFTP upload and “Apri CRM sul server” need the Ubuntu server (`164.132.43.122`) and EspoCRM at `http://crm.autovincenti.it:8082`. These are not runnable inside the cloud VM without credentials and network access.

**GUI:** Requires a display (`DISPLAY` is set in Cursor Cloud). Use tmux for long-running GUI sessions.

### EspoCRM customizations

Branch `cursor/fix-espo-lead-button-df28` contains files under `espocrm-custom/` meant to be deployed to `/var/www/espocrm/` on the server, followed by `php rebuild.php`. There is no local EspoCRM instance in this repo.

### Lint / tests

No linter or automated test suite is configured. `.gitignore` references `ruff`/`mypy` caches but no config files exist. Use `./scripts/start.sh --check` as the smoke test.
