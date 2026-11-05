# v2.1.3

🇬🇧 [English](#english) · 🇮🇹 [Italiano](#italiano)

---

<a id="english"></a>
## 🇬🇧 English

### Fixes

- **Automatic sums check at the end of every file import.** After rebuilding the chart history, the integration checks that the Energy dashboard sums are continuous with the rows already written by Home Assistant and, if there is a jump (for example negative bars in the current month), it repairs it by itself: no need to run `repair_statistics` by hand any more. The final notification tells how many points were fixed. If nothing needs fixing, nothing changes.
- `repair_statistics` stays available as a manual action for histories created by older versions.

### Updating

From HACS: update to 2.1.3 and restart Home Assistant. Existing data and statistics are untouched.

---

<a id="italiano"></a>
## 🇮🇹 Italiano

### Correzioni

- **Controllo automatico delle somme a fine importazione.** Dopo aver ricostruito lo storico dei grafici, l'integrazione verifica che le somme della plancia Energia siano continue con le righe già scritte da Home Assistant e, se c'è un salto (per esempio barre negative nel mese corrente), lo ripara da sola: non serve più lanciare `repair_statistics` a mano. La notifica finale indica quanti punti sono stati corretti. Se non c'è nulla da correggere, non cambia niente.
- `repair_statistics` resta disponibile come azione manuale per storici creati da versioni precedenti.

### Aggiornamento

Da HACS: aggiorna alla 2.1.3 e riavvia Home Assistant. Dati e statistiche esistenti non vengono toccati.
