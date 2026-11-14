# v2.4.0

🇬🇧 [English](#english) · 🇮🇹 [Italiano](#italiano)

---

<a id="english"></a>
## 🇬🇧 English

### New

- **"This week" in the card.** A new box between "Today" and "This month" shows the consumption of the current week (Monday to Sunday), for both gas and water.
- **New sensor "Consumption this week"** (`sensor.<meter>_consumption_this_week`), next to the day, month and year ones. It restarts every Monday at midnight and, like the others, is computed from the history, so it is correct from the first start after the update even if the week has already begun. It can be used in dashboards and automations.

### Fixes

- The "Meter reading" sensor now lists the day/week/month/year sensors in its attributes already at its very first state, so the card never shows "—" for them right after an update that adds a sensor.
- Card images in the README renamed (`card-gas-v2.png`, `card-water-v2.png`) and updated with the Weeks tab and the new box, so GitHub does not show cached old ones.

### Updating

From HACS: update to 2.4.0, restart Home Assistant and reload the page (Ctrl+F5) so the browser picks up the new card. The new sensor is created automatically. Existing data and statistics are untouched.

---

<a id="italiano"></a>
## 🇮🇹 Italiano

### Novità

- **«Questa settimana» nella card.** Un nuovo riquadro tra «Oggi» e «Questo mese» mostra il consumo della settimana in corso (da lunedì a domenica), per gas e acqua.
- **Nuovo sensore «Consumo della settimana»** (`sensor.<contatore>_consumption_this_week`), accanto a quelli di giorno, mese e anno. Riparte ogni lunedì a mezzanotte e, come gli altri, viene calcolato dallo storico, quindi è corretto già al primo avvio dopo l'aggiornamento anche se la settimana è già iniziata. Si può usare in plancia e nelle automazioni.

### Correzioni

- Il sensore «Lettura contatore» elenca ora nei suoi attributi i sensori di giorno/settimana/mese/anno già al primissimo stato, così la card non mostra «—» per questi valori subito dopo un aggiornamento che aggiunge un sensore.
- Immagini della card nel README rinominate (`card-gas-v2.png`, `card-water-v2.png`) e aggiornate con la scheda Settimane e il nuovo riquadro, così GitHub non mostra quelle vecchie in cache.

### Aggiornamento

Da HACS: aggiorna alla 2.4.0, riavvia Home Assistant e ricarica la pagina (Ctrl+F5) perché il browser prenda la nuova card. Il nuovo sensore viene creato in automatico. Dati e statistiche esistenti non vengono toccati.
