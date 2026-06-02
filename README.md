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

## Avvio rapido su Mac

Il file `.bat` e' per Windows e non parte direttamente su Mac. Su macOS usare
invece uno di questi file:

- doppio click su `Avvia NormalizzaLeads.command`
- oppure doppio click su `Avvia SpostaLeads.command`

Se macOS blocca il file per i permessi, aprire il Terminale nella cartella del
programma ed eseguire:

```bash
chmod +x "Avvia NormalizzaLeads.command" "Avvia SpostaLeads.command" scripts/start.sh
./"Avvia NormalizzaLeads.command"
```

## Installazione su Linux/macOS da Terminale

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
- `remote_desktop_dir`: Desktop remoto dove si trovano i CSV normalizzati
- `crm_url`: indirizzo del CRM da aprire sul server Ubuntu
- `desktop_url`: link opzionale per aprire il desktop remoto/Normalizzatore

## Import nel CRM dai file sul server

Il selettore file del browser vede solo i file del computer su cui gira il
browser. Se il CRM e' aperto nel Chrome del PC Windows/Mac, il browser non puo'
mostrare direttamente `/home/ubuntu/Desktop` del server Linux.

Per importare i CSV gia' normalizzati sul server:

1. Aprire l'app SpostaLeads/NormalizzaLeads.
2. Cliccare **Apri CRM sul server**.
3. Usare il browser che si apre dentro ubuntu-desktop.
4. Nel selettore file del CRM scegliere la cartella **Desktop** del server.

Da terminale si puo' fare lo stesso con:

```bash
.venv/bin/python -m app.main --open-remote-crm
```

Questo comando apre anche il file manager del server direttamente sul Desktop e
aggiunge il Desktop ai bookmark GTK, cosi' compare nel selettore file remoto.

## Uso CLI senza interfaccia grafica

```bash
.venv/bin/python -m app.main --upload file1.xlsx file2.xlsx
```

## Errore 504 durante import CRM

Un errore 504 durante l'import indica che il CRM o il proxy stanno andando in
timeout mentre elaborano il CSV. In quel caso dividere il CSV normalizzato in
blocchi piu' piccoli e importarli uno alla volta.

Esempio sul server Ubuntu, per file con delimitatore `;`:

```bash
cd /home/ubuntu/Desktop
python3 -m app.main --split-csv "20260531 13.57 Leads Normalizzati.csv" --rows-per-file 300
```

Il comando crea una cartella accanto al CSV originale con file:

```text
*_part001.csv
*_part002.csv
*_part003.csv
```

Se il CRM va ancora in 504, ridurre il blocco:

```bash
python3 -m app.main --split-csv "20260531 13.57 Leads Normalizzati.csv" --rows-per-file 100
```

## Limite importante

Il Normalizzatore Leads vero e proprio non era incluso nei TXT caricati. Questa
base installa l'ambiente Python e fornisce il caricatore verso il server, ma per
replicare al 100% il pacchetto originale servono i sorgenti originali o un
archivio non limitato ai soli `.txt`.
