# v2.1.2

🇬🇧 [English](#english) · 🇮🇹 [Italiano](#italiano)

---

<a id="english"></a>
## 🇬🇧 English

### Fixes and improvements

- **Safer reset.** The "Reset data…" button has been **removed from the card**: resetting a meter is only done through the `rilevatore_consumi.reset_history` service (*Developer tools → Actions*), to avoid accidental deletions. The "Replace existing data" option in the import preview remains, with confirmation.
- **`reset_history` checks the result.** In some cases the statistics of a sensor could remain after the reset and it had to be repeated. The service now verifies that they are really deleted, retries up to three times and, if it cannot, reports an error instead of looking successful. The same applies to "Replace existing data".
- **More reliable file import.**
  - The chart history is now written **from the most recent period backwards**: if the import is interrupted, the most useful months are kept and importing the same file again completes the older part (before, a second import answered "already present" and left the chart incomplete).
  - A second import of the **same meter** while one is running is refused with a clear message. Importing the gas and the water file at the same time is fine: they are independent meters.
  - While importing, the card shows an "import in progress" message, and at the end Home Assistant shows a **notification** with the result, even if the page was reloaded in the meantime.
- README updated.

### Updating

From HACS: update to 2.1.2 and restart Home Assistant. Existing data and statistics are untouched.

---

<a id="italiano"></a>
## 🇮🇹 Italiano

### Correzioni e miglioramenti

- **Azzeramento più sicuro.** Il pulsante "Azzera dati…" è stato **tolto dalla card**: l'azzeramento di un contatore si fa solo dal servizio `rilevatore_consumi.reset_history` (*Strumenti per sviluppatori → Azioni*), per evitare cancellazioni accidentali. Resta l'opzione "Sostituisci i dati esistenti" nell'anteprima dell'importazione, con conferma.
- **`reset_history` controlla il risultato.** In alcuni casi le statistiche di un sensore potevano restare dopo l'azzeramento e serviva ripeterlo. Ora il servizio verifica che siano davvero cancellate, riprova fino a tre volte e, se non ci riesce, lo segnala con un errore invece di sembrare riuscito. Lo stesso vale per "Sostituisci i dati esistenti".
- **Importazione da file più affidabile.**
  - Lo storico dei grafici ora viene scritto **dal periodo più recente verso il più vecchio**: se l'importazione si interrompe restano i mesi più utili e importando di nuovo lo stesso file si completa la parte più vecchia (prima una seconda importazione rispondeva "già presente" e lasciava il grafico incompleto).
  - Una seconda importazione dello **stesso contatore** mentre una è in corso viene rifiutata con un messaggio chiaro. Importare insieme il file del gas e quello dell'acqua non è un problema: sono contatori indipendenti.
  - Durante l'importazione la card mostra "importazione in corso" e alla fine Home Assistant mostra una **notifica** con il risultato, anche se nel frattempo la pagina si è ricaricata.
- README aggiornato.

### Aggiornamento

Da HACS: aggiorna alla 2.1.2 e riavvia Home Assistant. Dati e statistiche esistenti non vengono toccati.
