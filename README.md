# Rilevatore Consumo GAS / ACQUA manuale · Manual GAS / WATER consumption meter (v1.1)

🇬🇧 [English](#english) · 🇮🇹 [Italiano](#italiano)

---

<a id="english"></a>
## 🇬🇧 English

Home Assistant package to enter your **gas and water meter readings by hand** and see them in the **Energy dashboard**, with daily, monthly and yearly consumption. Made for people who cannot (or do not want to) install sensors next to their meters.

Requires Home Assistant **2025.10 or later**.

### What is included

| File | Purpose |
|------|---------|
| `packages/consumo_gas.yaml` | Helpers, sensor, utility meters and automation for gas |
| `packages/consumo_acqua.yaml` | Same for water |
| `cards/vista_consumi_gas.yaml` | Full dashboard view for gas |
| `cards/vista_consumi_acqua.yaml` | Full dashboard view for water |
| `rse.png`, `contatoreH2o.png` | Optional pictures for the view (copy them to `/config/www/foto-pkg/`) |

You can install gas only, water only, or both.

### Installation

1. Enable packages in `configuration.yaml` (if you have not already):

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

2. Copy `consumo_gas.yaml` and/or `consumo_acqua.yaml` to `/config/packages/`.
3. *Developer tools → YAML → Check configuration*, then restart Home Assistant.
4. Type your current meter reading in the **"Valore rilevato"** field (dot or comma, e.g. `1234.567`).
5. Add the view: *Edit dashboard → three dots → Raw configuration editor* and paste `cards/vista_consumi_*.yaml` inside `views:` (or copy single cards). The 24-hour graph needs **mini-graph-card** from HACS (optional: use a `history-graph` card instead).
6. *Settings → Dashboards → Energy*: add **Gas** (`sensor.gas_consumption`) and/or **Water** (`sensor.water_consumption`) as sources.

### How to use

Whenever you read your meter, type the value in **"Valore rilevato"**. Date and time are recorded automatically.

The value must **always increase**: a lower value is read by Home Assistant as a meter replacement (new cycle). If you make a mistake, fix it right away.

### Entities

| Entity | Description |
|--------|-------------|
| `input_text.gas_reading_value` / `input_text.water_reading_value` | Reading entry field |
| `sensor.gas_consumption` / `sensor.water_consumption` | Meter value (used by the Energy dashboard) |
| `sensor.gas_daily`, `sensor.gas_monthly`, `sensor.gas_annual` | Gas consumption per day / month / year |
| `sensor.water_daily`, `sensor.water_monthly`, `sensor.water_annual` | Water consumption per day / month / year |

### Troubleshooting

- **The sensor is "unavailable"**: enter a reading greater than 0.
- **The field rejects my value**: only numbers with dot or comma are accepted, no units.
- **I cannot add the sensor to the Energy dashboard**: check that it is available and has `state_class: total_increasing`, a gas/water `device_class` and unit `m³`.
- **Energy dashboard does not show my reading yet**: it reads hourly statistics, so a reading appears once its hour has been compiled (a few minutes after a restart).

What changed in this version: [RELEASE_NOTES_v1.1.md](RELEASE_NOTES_v1.1.md).

---

<a id="italiano"></a>
## 🇮🇹 Italiano

Package per Home Assistant che permette di inserire **a mano** la lettura del contatore del gas e dell'acqua e di vederla nella **plancia Energia**, con consumi giornalieri, mensili e annuali. Pensato per chi non può o non vuole installare sensori vicino ai contatori.

Richiede Home Assistant **2025.10 o successivo**.

### Contenuto

| File | A cosa serve |
|------|--------------|
| `packages/consumo_gas.yaml` | Helper, sensore, utility meter e automazione per il gas |
| `packages/consumo_acqua.yaml` | Idem per l'acqua |
| `cards/vista_consumi_gas.yaml` | Vista dashboard completa per il gas |
| `cards/vista_consumi_acqua.yaml` | Vista dashboard completa per l'acqua |
| `rse.png`, `contatoreH2o.png` | Immagini facoltative per la vista (da copiare in `/config/www/foto-pkg/`) |

Puoi installare solo il gas, solo l'acqua, oppure entrambi.

### Installazione

1. In `configuration.yaml` abilita i package (se non l'hai già fatto):

   ```yaml
   homeassistant:
     packages: !include_dir_named packages
   ```

2. Copia `consumo_gas.yaml` e/o `consumo_acqua.yaml` in `/config/packages/`.
3. *Strumenti per sviluppatori → YAML → Controlla configurazione*, poi riavvia Home Assistant.
4. Scrivi la lettura attuale del contatore nel campo **"Valore rilevato"** (punto o virgola, es. `1234.567`).
5. Aggiungi la vista: *Modifica dashboard → tre puntini → Editor di configurazione grezzo* e incolla `cards/vista_consumi_*.yaml` dentro `views:` (oppure copia le singole card). Per il grafico a 24 ore serve **mini-graph-card** da HACS (facoltativa: in alternativa usa una card `history-graph`).
6. *Impostazioni → Dashboard → Energia*: aggiungi la fonte **Gas** (`sensor.gas_consumption`) e/o **Acqua** (`sensor.water_consumption`).

### Uso

Quando leggi il contatore, scrivi il valore in **"Valore rilevato"**. Data e ora si aggiornano da sole.

Il valore deve **crescere sempre**: un valore più basso del precedente viene interpretato da Home Assistant come sostituzione del contatore (nuovo ciclo). Se sbagli un inserimento, correggilo subito.

### Entità

| Entità | Descrizione |
|--------|-------------|
| `input_text.gas_reading_value` / `input_text.water_reading_value` | Campo di inserimento della lettura |
| `sensor.gas_consumption` / `sensor.water_consumption` | Valore del contatore (usato dalla plancia Energia) |
| `sensor.gas_daily`, `sensor.gas_monthly`, `sensor.gas_annual` | Consumo gas giornaliero / mensile / annuale |
| `sensor.water_daily`, `sensor.water_monthly`, `sensor.water_annual` | Consumo acqua giornaliero / mensile / annuale |

### Risoluzione problemi

- **Il sensore è "non disponibile"**: inserisci una lettura maggiore di 0.
- **Il campo rifiuta il valore**: sono ammessi solo numeri con punto o virgola, senza unità di misura.
- **Non riesco ad aggiungere il sensore alla plancia Energia**: controlla che sia disponibile e abbia `state_class: total_increasing`, `device_class` gas/water e unità `m³`.
- **La plancia Energia non mostra ancora la lettura**: legge le statistiche orarie, quindi la lettura compare quando quell'ora è stata calcolata (pochi minuti dopo un riavvio).

Cosa cambia in questa versione: [RELEASE_NOTES_v1.1.md](RELEASE_NOTES_v1.1.md).
