# v2.2.1

🇬🇧 [English](#english) · 🇮🇹 [Italiano](#italiano)

---

<a id="english"></a>
## 🇬🇧 English

### Fixes

- **The entity is renamed only once.** When you set an "existing sensor to replace", the integration takes over its entity ID (so the Energy dashboard history continues). Until now it re-checked at every start and could move the entity back to that name after you had renamed it yourself. Now the takeover happens once; later renames are kept. The configuration entry is migrated automatically (version 2) and installations that already took over the name are marked as done.

### Changes

- README: installation by searching **Rilevatore consumi** in HACS now comes first, with the custom repository as an alternative.

### Updating

From HACS: update to 2.2.1 and restart Home Assistant. Existing data and statistics are untouched.

---

<a id="italiano"></a>
## 🇮🇹 Italiano

### Correzioni

- **L'entità viene rinominata una sola volta.** Quando indichi un «sensore esistente da sostituire», l'integrazione prende il suo `entity_id` (così lo storico della plancia Energia continua). Finora lo ricontrollava a ogni avvio e poteva riportare l'entità a quel nome dopo che l'avevi rinominata tu. Ora la sostituzione avviene una volta sola e le rinomine successive restano. La voce di configurazione viene migrata automaticamente (versione 2) e le installazioni che hanno già preso il nome vengono segnate come completate.

### Modifiche

- README: l'installazione cercando **Rilevatore consumi** in HACS è ora la prima, con il repository personalizzato come alternativa.

### Aggiornamento

Da HACS: aggiorna alla 2.2.1 e riavvia Home Assistant. Dati e statistiche esistenti non vengono toccati.
