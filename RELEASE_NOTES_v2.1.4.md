# v2.1.4

🇬🇧 [English](#english) · 🇮🇹 [Italiano](#italiano)

---

<a id="english"></a>
## 🇬🇧 English

### Fixes

- **File import no longer depends on the open page.** Home Assistant cancels a web request when the browser or app disconnects (page closed or reloaded, phone locked, camera app switch). Until now this could stop a long import half-way, leaving the charts partially rebuilt. The import now runs as a background task and always finishes; the final notification reports the result.
- **If something goes wrong, you are told.** A failed import now creates a notification ("import NOT completed") instead of failing silently. Repeating the import completes the missing part.
- Correction to the 2.1.2 / 2.1.3 notes: the notification at the end of an import was only reliable if the page stayed open; from 2.1.4 it is reliable in every case.
- **`reset_history` without `reading`:** the current reading is now taken from the last row of the next imported file (before, the old, possibly wrong reading stayed). A manual reading cancels this.
- New FAQ with the step-by-step procedure to start from scratch after a wrong import.
- The card message now says that a long import (10-15 minutes with many years of history) can be left running.

### Updating

From HACS: update to 2.1.4 and restart Home Assistant. Existing data and statistics are untouched.

---

<a id="italiano"></a>
## 🇮🇹 Italiano

### Correzioni

- **L'importazione da file non dipende più dalla pagina aperta.** Home Assistant annulla una richiesta web quando il browser o l'app si disconnette (pagina chiusa o ricaricata, telefono bloccato, cambio app per la fotocamera). Finora questo poteva fermare a metà un'importazione lunga, lasciando i grafici ricostruiti solo in parte. Ora l'importazione gira come attività in background e arriva sempre in fondo; la notifica finale indica il risultato.
- **Se qualcosa va storto, lo vedi.** Un'importazione fallita crea una notifica ("importazione NON completata") invece di fallire in silenzio. Ripetendo l'importazione si completa la parte mancante.
- Correzione alle note 2.1.2 / 2.1.3: la notifica a fine importazione era affidabile solo se la pagina restava aperta; dalla 2.1.4 lo è sempre.
- **`reset_history` senza `reading`:** la lettura attuale viene ora presa dall'ultima riga del prossimo file importato (prima restava la vecchia lettura, magari errata). Una lettura manuale annulla questo comportamento.
- Nuova FAQ con la procedura passo passo per ripartire da zero dopo un'importazione errata.
- Il messaggio della card ora dice che un'importazione lunga (10-15 minuti con molti anni di storico) si può lasciare in corso.

### Aggiornamento

Da HACS: aggiorna alla 2.1.4 e riavvia Home Assistant. Dati e statistiche esistenti non vengono toccati.
