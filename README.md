# SpostaLeads / NormalizzaLeads

Questo repository ricostruisce l'ambiente Python indicato nei file TXT caricati
per il pacchetto "Sposta Leads". Il pacchetto originale citava una applicazione
Windows che carica file Excel di lead Instagram/TikTok su un server Ubuntu, dove
poi si usa il Normalizzatore Leads.

## Stato dei file ricevuti

Sono disponibili solo:

- `LEGGIMI.txt`, con istruzioni utente
- `MANIFEST.txt`, con l'elenco dei file del pacchetto originale
- `requirements.txt`, con le dipendenze Python

Il manifest elenca i sorgenti (`app/main.py`, `app/ui/main_window.py`,
`app/services/sftp_uploader.py`, ecc.) ma non contiene il loro codice. Per questo
il repository contiene una implementazione minimale compatibile con la struttura
indicata, sufficiente per creare l'ambiente Python e caricare file via SFTP.

## Installazione su Linux/macOS

Su Ubuntu/Debian servono anche i pacchetti di sistema per creare il venv e usare
Tkinter:

```bash
sudo apt-get update
sudo apt-get install -y python3.12-venv python3-tk
```

```bash
./scripts/start.sh --check
```

Per aprire l'interfaccia:

```bash
./scripts/start.sh
```

## Installazione su Windows

1. Copiare `server.local.json.example` in `server.local.json`.
2. Inserire in `server.local.json` la password SSH fornita dal reparto IT.
3. Fare doppio click su `Avvia SpostaLeads.bat`.

In alternativa, da PowerShell:

```powershell
scripts\start.ps1
```

## Configurazione

`server.local.json` non deve essere condiviso o committato: contiene credenziali.

Campi principali:

- `host`: server Ubuntu, preimpostato a `164.132.43.122`
- `port`: porta SSH, normalmente `22`
- `username`: utente SSH
- `password`: password SSH
- `remote_dir`: cartella remota dove caricare gli Excel
- `desktop_url`: link opzionale per aprire il desktop remoto/Normalizzatore

## Uso CLI senza interfaccia grafica

```bash
.venv/bin/python -m app.main --upload file1.xlsx file2.xlsx
```

## Limite importante

Il Normalizzatore Leads vero e proprio non era incluso nei TXT caricati. Questa
base installa l'ambiente Python e fornisce il caricatore verso il server, ma per
replicare al 100% il pacchetto originale servono i sorgenti originali o un
archivio non limitato ai soli `.txt`.
