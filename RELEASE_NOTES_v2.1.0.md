# v2.1.0

🇮🇹 [Italiano](#italiano) · 🇬🇧 [English](#english)

---

<a id="italiano"></a>
## 🇮🇹 Italiano

### Novità

- **Nuovo servizio `rilevatore_consumi.reset_history`**: cancella in un solo passaggio l'elenco delle letture, i consumi di mese e anno e tutte le statistiche (grafici e plancia Energia) di un contatore. Utile se hai importato valori sbagliati e vuoi ripartire pulito, senza dover eliminare e reinstallare l'integrazione né cancellare le statistiche a mano.
  - Si esegue da *Strumenti per sviluppatori → Azioni* sul sensore "Lettura contatore" del contatore interessato.
  - `confirm` deve essere attivo (senza conferma non viene cancellato nulla); `reading` è facoltativa e indica la nuova lettura di ripartenza, altrimenti resta quella attuale.
  - **Non si può annullare.** Dopo, importa il CSV corretto dalla card o inserisci la lettura.
- README: il servizio è descritto nell'elenco dei servizi e nelle FAQ.

### Aggiornamento

Da HACS: aggiorna alla 2.1.0 e riavvia Home Assistant. Dati e statistiche esistenti non vengono toccati finché non esegui il nuovo servizio.

---

<a id="english"></a>
## 🇬🇧 English

### What's new

- **New service `rilevatore_consumi.reset_history`**: deletes in one go the list of readings, month and year consumption and all statistics (charts and Energy dashboard) of a meter. Handy when you imported wrong values and want a clean start, without deleting and reinstalling the integration or removing statistics by hand.
  - Run it from *Developer tools → Actions* on the "Meter reading" sensor of the meter concerned.
  - `confirm` must be on (nothing is deleted without it); `reading` is optional and sets the restart reading, otherwise the current one is kept.
  - **It cannot be undone.** Afterwards import the correct CSV from the card or enter the reading.
- README: the service is described in the services list and in the FAQ.

### Updating

From HACS: update to 2.1.0 and restart Home Assistant. Existing data and statistics are untouched until you run the new service.
