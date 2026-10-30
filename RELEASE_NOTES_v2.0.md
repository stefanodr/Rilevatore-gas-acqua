# v2.0

🇮🇹 [Italiano](#italiano) · 🇬🇧 [English](#english)

---

<a id="italiano"></a>
## 🇮🇹 Italiano

Da pacchetto YAML a **integrazione personalizzata** (`rilevatore_consumi`), installabile da HACS e configurabile dall'interfaccia. Un contatore del gas e uno dell'acqua, sempre in **metri cubi interi**.

### Novità

- Integrazione con configurazione guidata: nessun helper, nessuna automazione, nessun YAML.
- Sensore "Lettura contatore" (`total_increasing`) pronto per la plancia Energia, più consumo di oggi, del mese e dell'anno.
- **Lettura da foto**: scatta la foto al contatore dalla card (o con il servizio `rilevatore_consumi.read_from_photo`) e l'AI propone il valore intero. **Non viene mai salvato senza la tua conferma**; la foto resta solo in memoria. Richiede un'entità AI Task (es. Google Gemini oppure Ollama locale).
- Inserimento manuale sempre disponibile (card, entità numerica o servizio `set_reading`).
- Controlli: lettura più bassa rifiutata (a meno di sostituzione contatore), aumento anomalo da confermare.
- Card Lovelace inclusa (`custom:rilevatore-consumi-card`, `meter: gas` o `water`), registrata automaticamente: lettura, consumi di oggi/mese/anno, grafico a barre su 30 giorni, 12 mesi e 5 anni con totale e media, ultime letture, inserimento a mano o da foto.
- **Importa da file**: dalla card, CSV (esportazione cronologia HA o `data;lettura`) con anteprima e conferma; ricostruisce lo storico dei grafici. Immagine del contatore in alto a destra (modificabile con `image:`).
- Consumi di oggi/mese/anno calcolati dallo storico (non dall'installazione) e aggiornati anche se l'istanza era ferma a mezzanotte.
- **Storico**: servizio `import_history` e opzione "sensore di cui prendere il nome" per riprendere le statistiche del vecchio sensore della v1.x.
- Opzione "sensore esistente": il nuovo sensore prende il nome (es. `sensor.gas_consumption`) e quindi lo **storico** del sensore della v1.x.
- Traduzioni italiano e inglese. Tutta la logica è coperta da test automatici.

### Se arrivi dalla v1.x

1. Fai un backup e annota la lettura attuale.
2. Rimuovi il package YAML e riavvia.
3. Elimina il vecchio sensore rimasto "non più fornito".
4. Aggiungi l'integrazione, indica la lettura e, in "sensore esistente", il vecchio sensore.

### Requisiti

Home Assistant 2025.10 o successivo. Per la foto: un'entità AI Task.

---

<a id="english"></a>
## 🇬🇧 English

From YAML package to a **custom integration** (`rilevatore_consumi`), installable via HACS and configured from the UI. One gas meter and one water meter, always in **whole cubic metres**.

### What's new

- Guided setup: no helpers, no automations, no YAML.
- "Meter reading" sensor (`total_increasing`) ready for the Energy dashboard, plus today / this month / this year consumption.
- **Photo reading**: take a picture of the meter from the card (or use the `rilevatore_consumi.read_from_photo` service) and AI proposes the whole-number value. **Nothing is saved without your confirmation**; the photo is kept in memory only. Requires an AI Task entity (e.g. Google Gemini or local Ollama).
- Manual entry always available (card, number entity or `set_reading` service).
- Safety checks: a lower reading is rejected (unless the meter was replaced), an unusual jump must be confirmed.
- Bundled Lovelace card (`custom:rilevatore-consumi-card`, `meter: gas` or `water`), registered automatically: reading, today/month/year consumption, bar chart over 30 days, 12 months and 5 years with total and average, latest readings, manual or photo entry.
- **Import from file**: from the card, CSV (HA history export or `date;reading`) with preview and confirmation; rebuilds the chart history. Meter picture at the top right (configurable with `image:`).
- Today / month / year consumption computed from history (not from installation time) and refreshed even if the instance was down at midnight.
- **History**: `import_history` service and a "sensor whose name to take over" option to pick up the statistics of the old v1.x sensor.
- "Existing sensor" option: the new sensor takes over its name (e.g. `sensor.gas_consumption`) and therefore the **history** of the v1.x sensor.
- Italian and English translations. All logic is covered by automated tests.

### Coming from v1.x

1. Back up and note the current reading.
2. Remove the YAML package and restart.
3. Delete the leftover "no longer provided" sensor.
4. Add the integration, enter the reading and pick the old sensor under "existing sensor".

### Requirements

Home Assistant 2025.10 or later. For photo reading: an AI Task entity.
