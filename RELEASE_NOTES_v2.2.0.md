# v2.2.0

🇬🇧 [English](#english) · 🇮🇹 [Italiano](#italiano)

---

<a id="english"></a>
## 🇬🇧 English

### New

- **Import progress bar.** While a file is being imported the card shows the phase (deleting existing data, rebuilding history, final check) and a progress bar with the percentage. If you reload the page or open the card from another device, it picks the running import up again and shows the progress; when it ends it tells you to check the notification.
- **Downloadable diagnostics** (*Settings → Devices & services → Rilevatore consumi → ⋮ → Download diagnostics*): reading, baselines, last readings and import state, useful when reporting a problem. The meter name is redacted.
- **README split**: `README.md` is in English and `README.it.md` in Italian, with a link between them.

### Improvements

- Better contrast of the success and error messages in the card (readable on light and dark themes).
- New read-only endpoint `GET /api/rilevatore_consumi/import/<entry_id>` with the import state (used by the card).

### Updating

From HACS: update to 2.2.0 and restart Home Assistant. Existing data and statistics are untouched.

---

<a id="italiano"></a>
## 🇮🇹 Italiano

### Novità

- **Barra di avanzamento dell'importazione.** Durante l'importazione di un file la card mostra la fase (cancellazione dei dati esistenti, ricostruzione dello storico, controllo finale) e una barra con la percentuale. Se ricarichi la pagina o apri la card da un altro dispositivo, riprende l'importazione in corso e ne mostra l'avanzamento; alla fine ti indica di controllare la notifica.
- **Diagnostica scaricabile** (*Impostazioni → Dispositivi e servizi → Rilevatore consumi → ⋮ → Scarica diagnostica*): lettura, basi di calcolo, ultime letture e stato dell'importazione, utile per segnalare un problema. Il nome del contatore viene oscurato.
- **README diviso**: `README.md` in inglese e `README.it.md` in italiano, con il collegamento tra i due.

### Miglioramenti

- Migliore contrasto dei messaggi di conferma e di errore nella card (leggibili con tema chiaro e scuro).
- Nuovo endpoint di sola lettura `GET /api/rilevatore_consumi/import/<entry_id>` con lo stato dell'importazione (usato dalla card).

### Aggiornamento

Da HACS: aggiorna alla 2.2.0 e riavvia Home Assistant. Dati e statistiche esistenti non vengono toccati.
