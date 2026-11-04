# v2.1.2

🇮🇹 [Italiano](#italiano) · 🇬🇧 [English](#english)

---

<a id="italiano"></a>
## 🇮🇹 Italiano

### Correzioni

- **Azzeramento più sicuro.** Il pulsante "Azzera dati…" è stato **tolto dalla card**: l'azzeramento di un contatore si fa solo dal servizio `rilevatore_consumi.reset_history` (*Strumenti per sviluppatori → Azioni*), per evitare cancellazioni accidentali. Resta l'opzione "Sostituisci i dati esistenti" nell'anteprima dell'importazione, con conferma.
- **`reset_history` controlla il risultato.** In alcuni casi le statistiche di un sensore potevano restare dopo l'azzeramento e serviva ripeterlo. Ora il servizio verifica che siano davvero cancellate, riprova fino a tre volte e, se non ci riesce, lo segnala con un errore invece di sembrare riuscito. Lo stesso vale per "Sostituisci i dati esistenti".
- README aggiornato.

### Aggiornamento

Da HACS: aggiorna alla 2.1.2 e riavvia Home Assistant. Dati e statistiche esistenti non vengono toccati.

---

<a id="english"></a>
## 🇬🇧 English

### Fixes

- **Safer reset.** The "Reset data…" button has been **removed from the card**: resetting a meter is only done through the `rilevatore_consumi.reset_history` service (*Developer tools → Actions*), to avoid accidental deletions. The "Replace existing data" option in the import preview remains, with confirmation.
- **`reset_history` checks the result.** In some cases the statistics of a sensor could remain after the reset and it had to be repeated. The service now verifies that they are really deleted, retries up to three times and, if it cannot, reports an error instead of looking successful. The same applies to "Replace existing data".
- README updated.

### Updating

From HACS: update to 2.1.2 and restart Home Assistant. Existing data and statistics are untouched.
