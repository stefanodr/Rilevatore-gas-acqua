# v2.0.1

🇮🇹 [Italiano](#italiano) · 🇬🇧 [English](#english)

---

<a id="italiano"></a>
## 🇮🇹 Italiano

Versione di manutenzione: **nessuna modifica al funzionamento**, nessuna azione richiesta per chi ha già la 2.0. Prepara il repository per l'inclusione ufficiale in HACS.

### Novità

- Aggiunta la licenza **MIT**.
- README: immagini delle card gas e acqua, informazioni sull'inserimento da **CSV** e guida per ripristinare i contatori mensile/annuale (CSV con la lettura a inizio periodo) e i totali della plancia Energia (`import_history`, `repair_statistics`, `utility_meter.calibrate`).
- README: nuova sezione **Domande frequenti** (integrazione non visibile dopo il download da HACS, valori CSV errati che ricompaiono dopo la reinstallazione, fotocamera nella Companion app Android).
- Controlli automatici su GitHub (HACS e Hassfest) a ogni modifica.
- Chiavi di `manifest.json` ordinate secondo le regole di Hassfest.

### Aggiornamento

Da HACS: aggiorna alla 2.0.1 e riavvia Home Assistant. I dati e le statistiche esistenti non vengono toccati.

---

<a id="english"></a>
## 🇬🇧 English

Maintenance release: **no change in behaviour**, nothing to do if you already run 2.0. It prepares the repository for inclusion in the official HACS list.

### What's new

- Added the **MIT** license.
- README: gas and water card pictures, information about **CSV** input and a guide to restore monthly/yearly counters (CSV with the period-start reading) and Energy dashboard totals (`import_history`, `repair_statistics`, `utility_meter.calibrate`).
- README: new **FAQ** section (integration not visible after downloading from HACS, wrong CSV values coming back after reinstalling, camera in the Android Companion app).
- Automatic checks on GitHub (HACS and Hassfest) on every change.
- `manifest.json` keys sorted according to Hassfest rules.

### Updating

From HACS: update to 2.0.1 and restart Home Assistant. Existing data and statistics are not touched.
