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

Dopo l'installazione la risorsa è registrata da sola. Aggiungi una **scheda manuale**:

```yaml
type: custom:rilevatore-consumi-card
meter: gas        # gas oppure water: la card trova da sola il sensore giusto
title: Gas        # facoltativo
```

La card mostra la lettura, i consumi di oggi / del mese / dell'anno, il grafico a barre degli ultimi 30 giorni, 12 mesi e 5 anni (con media e totale), le ultime letture e i comandi per inserire la lettura a mano o da foto. Il grafico usa le statistiche di Home Assistant, quindi comprende anche lo storico recuperato dal vecchio sensore. In alternativa a `meter` puoi indicare `entity: sensor.…` (il sensore "Lettura contatore").

Se vuoi, aggiungi `image: /local/mia-foto.png` per usare un'altra immagine del contatore, oppure `image: false` per nasconderla: di serie in alto a destra compare l'immagine del gas o dell'acqua.

### Importare letture e storico da file

Nella card, il pulsante **📁 File** carica un file CSV con le letture. Vengono accettati l'esportazione della cronologia di Home Assistant (`entity_id,state,last_changed`) e file semplici con data e lettura (`data;lettura`, con date ISO o `gg/mm/aaaa [hh:mm]`, separatore `,` `;` o tabulazione, decimali ignorati). Prima di scrivere qualsiasi cosa vedi un'**anteprima** (letture trovate, periodo, consumo complessivo, eventuali diminuzioni o righe ignorate) e confermi.

Con l'importazione:
- le letture entrano nell'elenco delle ultime letture e nei consumi di oggi/mese/anno;
- la lettura attuale cambia solo se il file contiene una lettura più recente e non più bassa;
- le statistiche del grafico vengono ricostruite ripartendo il consumo tra una lettura e l'altra (è una stima giorno per giorno; i totali restano esatti). Si riempie il periodo precedente ai dati già presenti, senza toccare quelli esistenti; ripetere l'importazione non duplica nulla.

È il modo più semplice anche per caricare nuove letture in blocco o per portare lo storico dell'acqua e del gas su una nuova installazione.

### Se arrivi dalla v1.x (package YAML)

Lo storico della plancia Energia è legato al **nome** del sensore (`sensor.gas_consumption`, `sensor.water_consumption`). Per non perderlo:
1. Backup e annota la lettura attuale.
2. Rimuovi il package YAML (e le viste) e riavvia, fermando HA in modo pulito. **Non** togliere i tuoi helper utility meter creati dall'interfaccia: continueranno a funzionare perché il sensore tornerà ad avere lo stesso nome.
3. In *Impostazioni → Dispositivi e servizi → Entità* elimina il vecchio sensore "non più fornito". Le statistiche restano nel database.
4. Aggiungi l'integrazione con la lettura annotata e, in **Sensore esistente**, `sensor.gas_consumption` / `sensor.water_consumption`: il nuovo sensore ne prende il nome e lo storico continua senza interruzioni.

**Se hai già aggiunto il contatore senza indicare il sensore** (e il sensore ha un altro nome, per esempio `sensor.gas_meter_reading`), non serve rifarlo:
- Opzione A: nelle *opzioni* dell'integrazione indica il vecchio sensore (dopo aver eliminato quello vecchio come al punto 3); l'integrazione lo rinomina e riprende le statistiche.
- Opzione B: in *Strumenti per sviluppatori → Azioni* esegui `rilevatore_consumi.import_history`, scegli come destinazione il sensore "Lettura contatore" e come `source` il vecchio sensore (es. `sensor.gas_consumption`). Le statistiche vecchie vengono copiate sul nuovo sensore, senza buchi nel totale. Poi nella plancia Energia seleziona il nuovo sensore.

Nella cartella `legacy/` trovi la v1.1 (package YAML) per chi preferisce restare così.

### Risoluzione dei problemi

**Barre negative nella plancia Energia** (per esempio −440 m³ nell'ultimo mese, dopo aver importato storico o file con una versione precedente): esegui in *Strumenti per sviluppatori → Azioni* `rilevatore_consumi.repair_statistics` sul sensore "Lettura contatore" di ogni contatore. Il servizio ricalcola le somme dalle letture memorizzate partendo dall'ora più recente e aggiunge in testa una riga di riferimento, necessaria perché la plancia calcoli bene il primo mese dell'anno; si può ripetere senza danni. Dopo l'aggiornamento le importazioni non creano più il problema.

**Le card non si aprono nella Companion app** ("Errore di configurazione" / "Custom element doesn't exist") mentre dal browser funzionano: è un difetto noto dell'app (home-assistant/frontend #55272), che tiene in cache la pagina iniziale e non riceve i moduli aggiunti dalle integrazioni. Registra la card anche come risorsa della dashboard: *Impostazioni → Dashboard → ⋮ → Risorse → Aggiungi risorsa*, URL `/rilevatore_consumi_static/rilevatore-consumi-card.js`, tipo *Modulo JavaScript*. In alternativa svuota la cache dell'app.

### Servizi

- `rilevatore_consumi.set_reading` — `reading`, `force`, `replace_meter`
- `rilevatore_consumi.read_from_photo` — `media` (restituisce la proposta, non salva)
- `rilevatore_consumi.import_history` — `source` (copia le statistiche di un vecchio sensore)
- `rilevatore_consumi.repair_statistics` — toglie i salti nelle somme dello storico

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

The resource is registered automatically. Add a **manual card**:

```yaml
type: custom:rilevatore-consumi-card
meter: gas        # gas or water: the card finds the right sensor by itself
title: Gas        # optional
```

The card shows the reading, consumption today / this month / this year, a bar chart of the last 30 days, 12 months and 5 years (with total and average), the latest readings and the controls to enter a reading by hand or from a photo. The chart uses Home Assistant statistics, so it includes history recovered from the old sensor. Instead of `meter` you can use `entity: sensor.…` (the "Meter reading" sensor).

Add `image: /local/my-photo.png` to use another picture of the meter, or `image: false` to hide it: by default a gas or water meter picture appears at the top right.

### Importing readings and history from a file

In the card, the **📁 File** button uploads a CSV file of readings. Accepted: the Home Assistant history export (`entity_id,state,last_changed`) and simple files with a date and a reading (`date;reading`, ISO dates or `dd/mm/yyyy [hh:mm]`, separator `,` `;` or tab, decimals ignored). Before anything is written you see a **preview** (readings found, period, total consumption, any decreases or ignored rows) and you confirm.

On import:
- readings go into the latest-readings list and into today / month / year consumption;
- the current reading changes only if the file holds a newer, not lower reading;
- chart statistics are rebuilt by spreading consumption between readings (a day-by-day estimate; totals stay exact). It fills the period before the data already present, without touching existing data; importing twice does not duplicate anything.

It is also the easiest way to load new readings in bulk or to bring gas and water history into a fresh installation.

### Coming from v1.x (YAML package)

Energy dashboard history is tied to the sensor **name** (`sensor.gas_consumption`, `sensor.water_consumption`). To keep it:
1. Back up and note the current reading.
2. Remove the YAML package (and views) and restart, shutting HA down cleanly. Do **not** remove your utility meter helpers created from the UI: they keep working because the sensor gets the same name again.
3. In *Settings → Devices & services → Entities* delete the old "no longer provided" sensor. Its statistics stay in the database.
4. Add the integration with the noted reading and, under **Existing sensor**, `sensor.gas_consumption` / `sensor.water_consumption`: the new sensor takes that name and the history continues without a gap.

**If you already added the meter without the existing sensor** (so it has another name, e.g. `sensor.gas_meter_reading`) there is no need to redo it:
- Option A: in the integration *options* enter the old sensor (after deleting the old one as in step 3); the integration renames itself and picks up the statistics.
- Option B: in *Developer tools → Actions* run `rilevatore_consumi.import_history`, target the "Meter reading" sensor and set `source` to the old sensor (e.g. `sensor.gas_consumption`). The old statistics are copied to the new sensor with no gap in the total. Then select the new sensor in the Energy dashboard.

The `legacy/` folder holds v1.1 (YAML package) for those who prefer it.

### Troubleshooting

**Negative bars in the Energy dashboard** (for example −440 m³ in the last month, after importing history or a file with an earlier version): in *Developer tools → Actions* run `rilevatore_consumi.repair_statistics` on the "Meter reading" sensor of each meter. The service recomputes the sums from the stored readings starting from the most recent hour and adds a reference row at the start, needed for the dashboard to compute the first month of the year correctly; safe to repeat. After the update, imports no longer cause the problem.

**Cards do not open in the Companion app** ("Configuration error" / "Custom element doesn't exist") while they work in the browser: this is a known app issue (home-assistant/frontend #55272): the app caches the start page and does not receive modules added by integrations. Also register the card as a dashboard resource: *Settings → Dashboards → ⋮ → Resources → Add resource*, URL `/rilevatore_consumi_static/rilevatore-consumi-card.js`, type *JavaScript module*. Alternatively clear the app cache.

### Services

- `rilevatore_consumi.set_reading` — `reading`, `force`, `replace_meter`
- `rilevatore_consumi.read_from_photo` — `media` (returns the proposal, saves nothing)
- `rilevatore_consumi.import_history` — `source` (copies the statistics of an old sensor)
- `rilevatore_consumi.repair_statistics` — removes jumps in the history sums
