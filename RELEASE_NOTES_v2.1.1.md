# v2.1.1

🇮🇹 [Italiano](#italiano) · 🇬🇧 [English](#english)

---

<a id="italiano"></a>
## 🇮🇹 Italiano

### Correzioni e novità

- **`reset_history` cancella anche la cronologia degli stati.** Prima azzerava letture e statistiche ma i grafici che si aprono toccando le entità (Consumo oggi/mese/anno, Lettura contatore) mostravano ancora i vecchi valori. Ora sono vuoti.
- **Card: pulsante "Azzera dati…"** in fondo alla card, con conferma: cancella letture, consumi e storico del contatore.
- **Card: opzione "Sostituisci i dati esistenti"** nell'anteprima dell'importazione da file: cancella tutto ciò che c'è e riparte dal file (utile se hai importato valori sbagliati).
- **Lettura da foto: il risultato non va più perso.** Dopo la fotocamera l'app Android può ricaricare la pagina mentre la foto viene analizzata: prima non succedeva nulla e nessun errore. Ora la card recupera da sola la proposta di lettura (valida 10 minuti) oppure, se la foto non è arrivata, lo segnala con un messaggio chiaro.
- **Importazione di file molto lunghi** (anni di letture) più affidabile: le statistiche vengono scritte a blocchi.
- Controlli e test aggiunti.

### Aggiornamento

Da HACS: aggiorna alla 2.1.1 e riavvia Home Assistant. Dati e statistiche esistenti non vengono toccati finché non usi "Azzera dati" o "Sostituisci".

---

<a id="english"></a>
## 🇬🇧 English

### Fixes and new features

- **`reset_history` also deletes the state history.** Before, it cleared readings and statistics but the charts opened by tapping the entities (Consumption today/month/year, Meter reading) still showed the old values. They are now empty.
- **Card: "Reset data…" button** at the bottom of the card, with confirmation: deletes the meter's readings, consumption and history.
- **Card: "Replace existing data" option** in the file import preview: deletes everything present and restarts from the file (useful if you imported wrong values).
- **Photo reading: the result is no longer lost.** After the camera the Android app may reload the page while the photo is being analysed: before, nothing happened and no error was shown. Now the card recovers the proposed reading by itself (valid for 10 minutes) or, if the photo did not arrive, says so with a clear message.
- **Very long file imports** (years of readings) are more reliable: statistics are written in chunks.
- Added checks and tests.

### Updating

From HACS: update to 2.1.1 and restart Home Assistant. Existing data and statistics are untouched until you use "Reset data" or "Replace".
