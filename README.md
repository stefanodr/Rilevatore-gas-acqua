# Rilevatore consumi gas / acqua · Gas / water meter reader (v2.0)

🇮🇹 [Italiano](#italiano) · 🇬🇧 [English](#english)

---

<a id="italiano"></a>
## 🇮🇹 Italiano

Integrazione per Home Assistant per registrare la lettura del **contatore del gas** e dell'**acqua** (m³ interi), vederla nella **plancia Energia** e calcolare i consumi di oggi, del mese e dell'anno. Pensata per chi non può installare sensori vicino ai contatori: la lettura si inserisce **a mano** oppure **da foto**.

Richiede Home Assistant **2025.10 o successivo**.

### Installazione

**HACS**: Integrazioni → menu ⋮ → *Repository personalizzati* → `https://github.com/stefanodr/Rilevatore-gas-acqua` (categoria *Integrazione*) → installa → riavvia.
**Manuale**: copia `custom_components/rilevatore_consumi` nella cartella `custom_components` di HA e riavvia.

### Configurazione

*Impostazioni → Dispositivi e servizi → Aggiungi integrazione → Rilevatore consumi.* Aggiungi un contatore per il gas e uno per l'acqua, indicando nome, tipo e lettura attuale (solo la parte intera).

Per ogni contatore ottieni:
- **Lettura contatore** (da usare nella plancia Energia come fonte gas/acqua);
- **Consumo oggi / mese / anno**;
- **Nuova lettura** (campo numerico) e **Ultima foto** (solo in memoria, mai salvata su disco).

### Inserire la lettura

- **A mano**: card, entità *Nuova lettura* o servizio `rilevatore_consumi.set_reading`.
- **Da foto**: con la card tocca 📷, scatta, controlla il valore proposto e conferma. Richiede un'entità **AI Task** (es. Google Gemini, oppure Ollama in locale se non vuoi inviare foto a servizi esterni). Nelle opzioni dell'integrazione puoi scegliere quale usare. Il valore è sempre solo un suggerimento: **non viene salvato senza la tua conferma**.

Controlli: una lettura più bassa viene rifiutata (se hai sostituito il contatore, conferma "contatore sostituito"); un aumento oltre la soglia (300 m³ gas, 100 m³ acqua, modificabile) va confermato.

### Card

Dopo l'installazione la risorsa è registrata da sola. Aggiungi una scheda manuale:

```yaml
type: custom:rilevatore-consumi-card
entity: sensor.gas_meter_reading   # il sensore "Lettura contatore"
title: Gas
```

### Se arrivi dalla v1.x (package YAML)

Per non perdere letture e storico:
1. Backup e annota la lettura attuale.
2. Rimuovi il package YAML (e le viste) e riavvia, fermando HA in modo pulito.
3. In *Impostazioni → Dispositivi e servizi → Entità* elimina il vecchio sensore "non più fornito".
4. Aggiungi l'integrazione con la lettura annotata e, in **Sensore esistente**, `sensor.gas_consumption` / `sensor.water_consumption`: il nuovo sensore ne prende il nome e quindi lo storico.

Nella cartella `legacy/` trovi la v1.1 (package YAML) per chi preferisce restare così.

### Servizi

- `rilevatore_consumi.set_reading` — `reading`, `force`, `replace_meter`
- `rilevatore_consumi.read_from_photo` — `media` (restituisce la proposta, non salva)

---

<a id="english"></a>
## 🇬🇧 English

Home Assistant integration to record the **gas** and **water meter** reading (whole m³), show it in the **Energy dashboard** and compute today / month / year consumption. Built for meters where no sensor can be installed: enter the reading **by hand** or **from a photo**.

Requires Home Assistant **2025.10 or later**.

### Installation

**HACS**: Integrations → ⋮ → *Custom repositories* → `https://github.com/stefanodr/Rilevatore-gas-acqua` (type *Integration*) → install → restart.
**Manual**: copy `custom_components/rilevatore_consumi` into HA's `custom_components` folder and restart.

### Setup

*Settings → Devices & services → Add integration → Rilevatore consumi.* Add one gas and one water meter with name, type and current reading (integer part only).

Each meter provides:
- **Meter reading** (use it as gas/water source in the Energy dashboard);
- **Consumption today / month / year**;
- **New reading** (number field) and **Last photo** (kept in memory only, never written to disk).

### Entering a reading

- **By hand**: the card, the *New reading* entity or the `rilevatore_consumi.set_reading` service.
- **From a photo**: in the card tap 📷, take the picture, check the proposed value and confirm. Needs an **AI Task** entity (e.g. Google Gemini, or local Ollama if you don't want photos sent to external services). You can choose which one in the integration options. The value is only a suggestion: **nothing is saved without your confirmation**.

Checks: a lower reading is rejected (if you replaced the meter, confirm "meter replaced"); an increase above the threshold (300 m³ gas, 100 m³ water, configurable) must be confirmed.

### Card

The resource is registered automatically. Add a manual card:

```yaml
type: custom:rilevatore-consumi-card
entity: sensor.gas_meter_reading   # the "Meter reading" sensor
title: Gas
```

### Coming from v1.x (YAML package)

To keep readings and history:
1. Back up and note the current reading.
2. Remove the YAML package (and views) and restart, shutting HA down cleanly.
3. In *Settings → Devices & services → Entities* delete the old "no longer provided" sensor.
4. Add the integration with the noted reading and, under **Existing sensor**, `sensor.gas_consumption` / `sensor.water_consumption`: the new sensor takes that name and therefore its history.

The `legacy/` folder holds v1.1 (YAML package) for those who prefer it.

### Services

- `rilevatore_consumi.set_reading` — `reading`, `force`, `replace_meter`
- `rilevatore_consumi.read_from_photo` — `media` (returns the proposal, saves nothing)
