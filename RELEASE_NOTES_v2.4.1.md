# v2.4.1

🇬🇧 [English](#english) · 🇮🇹 [Italiano](#italiano)

---

<a id="english"></a>
## 🇬🇧 English

Fixes requested during the HACS default repository review.

### Fixes

- **Entities of other integrations are never removed.** When you set an "existing sensor to replace" and that entity ID is already taken by another integration, the integration no longer deletes that registry entry (not even if it looks orphaned: at startup, entities of integrations that load later have no state yet). It keeps the repair notice instead and you delete the old entity yourself, as described in the README. The entity ID is taken over only when it is free in the registry.
- **Importing a CSV no longer blocks Home Assistant.** Parsing the file, expanding it to hourly rows, merging with existing statistics and repairing the sums now run in the executor, and the hourly expansion walks the readings in a single pass (linear cost) instead of rescanning them for every hour. Importing years of history is fast and the event loop stays responsive.

### Updating

From HACS: update to 2.4.1 and restart Home Assistant. Existing data and statistics are untouched.

---

<a id="italiano"></a>
## 🇮🇹 Italiano

Correzioni richieste durante la revisione per l'inclusione nel repository predefinito di HACS.

### Correzioni

- **Le entità di altre integrazioni non vengono mai rimosse.** Quando indichi un «sensore esistente da sostituire» e quell'`entity_id` è già occupato da un'altra integrazione, l'integrazione non cancella più quella voce del registro (nemmeno se sembra orfana: all'avvio le entità delle integrazioni che si caricano dopo non hanno ancora uno stato). Mantiene invece la segnalazione e sei tu a eliminare il vecchio sensore, come spiegato nel README. Il nome viene preso solo quando è libero nel registro.
- **L'importazione del CSV non blocca più Home Assistant.** Lettura del file, espansione in righe orarie, unione con le statistiche esistenti e riparazione delle somme ora girano in un thread separato, e l'espansione oraria scorre le letture in un'unica passata (costo lineare) invece di rileggerle da capo per ogni ora. Importare anni di storico è veloce e Home Assistant resta reattivo.

### Aggiornamento

Da HACS: aggiorna alla 2.4.1 e riavvia Home Assistant. Dati e statistiche esistenti non cambiano.
