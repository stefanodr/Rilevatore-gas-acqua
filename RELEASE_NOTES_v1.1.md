# v1.1

🇬🇧 [English](#english) · 🇮🇹 [Italiano](#italiano)

---

<a id="english"></a>
## 🇬🇧 English

### Changes

- Sensors rewritten with the modern `template:` syntax (`platform: template` is no longer supported by Home Assistant).
- `state_class: total_increasing` is now set directly in the sensor: `add_state_class.py`, `Automazione.yaml`, the `python_scripts` folder and the 30-second delay are **no longer needed**.
- The sensor stays unavailable until a valid reading (> 0) exists, to avoid fake consumption after a restart or on first setup.
- The "Valore rilevato" field only accepts numbers, with dot or comma.
- Automations updated to the current syntax (`triggers`/`actions`) and given an `id`.
- New complete dashboard views (`cards/vista_consumi_*.yaml`): entry form, daily/monthly/yearly consumption, 24-hour graph, monthly and weekly statistics, reading log and Energy graph. **button-card is no longer required** (date and time update by themselves); mini-graph-card is optional.
- Removed the `energy:` block from the packages: it is not part of the Energy integration's YAML configuration. Sources are added from the UI.
- Fixed a typo in the monthly gas meter `unique_id` (`gas_monthly`).
- New `ultima_lettura` attribute on the sensors.
- README in English and Italian.

### Requirements

Home Assistant 2025.10 or later.

---

<a id="italiano"></a>
## 🇮🇹 Italiano

### Cambiamenti

- Sensori in sintassi `template:` moderna (`platform: template` non è più supportato da Home Assistant).
- `state_class: total_increasing` direttamente nel sensore: **non servono più** `add_state_class.py`, `Automazione.yaml`, la cartella `python_scripts` e il ritardo di 30 secondi.
- Il sensore resta non disponibile finché non c'è una lettura valida (> 0), per evitare falsi consumi dopo un riavvio o alla prima configurazione.
- Il campo "Valore rilevato" accetta solo numeri, con punto o virgola.
- Automazioni aggiornate alla sintassi attuale (`triggers`/`actions`) e con `id`.
- Nuove viste dashboard complete (`cards/vista_consumi_*.yaml`): registrazione, consumi giornalieri/mensili/annuali, grafico a 24 ore, statistiche mensili e settimanali, storico rilevamenti e grafico Energia. **button-card non è più necessaria** (data e ora si aggiornano da sole); mini-graph-card è facoltativa.
- Rimosso il blocco `energy:` dai package, che non fa parte della configurazione YAML dell'integrazione Energy: le fonti si aggiungono dall'interfaccia.
- Corretto il refuso nell'`unique_id` del contatore mensile del gas (`gas_monthly`).
- Nuovo attributo `ultima_lettura` sui sensori.
- README in italiano e in inglese.

### Requisiti

Home Assistant 2025.10 o successivo.
