# Personalizzazione Lead: bottone "Trasforma in Opportunità"

## Causa dell'errore cache

Il JSON fornito da Copilot usava `recordViews.detail.buttons`, che **non esiste** in EspoCRM.

In `clientDefs`, `recordViews.detail` deve essere una **stringa** (percorso della view), ad esempio:

```json
"recordViews": {
  "detail": "crm:views/lead/record/detail"
}
```

Metterci un oggetto con `buttons` rompe il merge dei metadata e provoca:

`Internal server error → Error while clearing cache`

I bottoni vanno definiti in **`menu.detail.buttons`**, non in `recordViews`.

## Installazione

Copia i file sul server EspoCRM:

```bash
# clientDefs Lead
cp custom/Espo/Custom/Resources/metadata/clientDefs/Lead.json \
   /var/www/espocrm/custom/Espo/Custom/Resources/metadata/clientDefs/Lead.json

# handler JavaScript
cp client/custom/src/create-opportunity-from-lead-handler.js \
   /var/www/espocrm/client/custom/src/create-opportunity-from-lead-handler.js
```

Poi rebuild da terminale:

```bash
cd /var/www/espocrm
php rebuild.php
```

## Verifica JSON

```bash
python3 -m json.tool /var/www/espocrm/custom/Espo/Custom/Resources/metadata/clientDefs/Lead.json
```

Se il comando non restituisce errori, il JSON è valido.

## Comportamento del bottone

1. Visibile solo se il Lead **non** è Converted, Dead o Recycled.
2. Apre un modale con i campi Opportunità (layout `detailConvert`).
3. Alla conferma chiama `Lead/action/convert` creando **solo** l'Opportunità.
4. Reindirizza alla nuova Opportunità creata.
