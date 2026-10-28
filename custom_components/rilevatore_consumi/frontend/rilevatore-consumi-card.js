/* Rilevatore consumi - card con lettura (a mano o da foto) e report dei consumi.
 *
 * Uso:
 *   type: custom:rilevatore-consumi-card
 *   meter: gas            # gas | water  (trova da sola il sensore giusto)
 *   title: Gas            # facoltativo
 *   # in alternativa:  entity: sensor.gas_consumption   (il sensore "Lettura contatore")
 */
const TEXTS = {
  it: {
    last: "Ultima lettura",
    today: "Oggi",
    month: "Questo mese",
    year: "Quest'anno",
    days: "Giorni",
    months: "Mesi",
    years: "Anni",
    total: "Totale",
    average: "Media",
    perDay: "al giorno",
    perMonth: "al mese",
    perYear: "all'anno",
    noStats: "Nessun dato storico disponibile",
    readings: "Ultime letture",
    replaced: "contatore sostituito",
    newReading: "Nuova lettura",
    save: "Salva",
    photo: "Foto",
    reading_photo: "Leggo la foto…",
    proposed: "Valore letto dalla foto",
    check: "Controlla il valore",
    confirm: "Conferma",
    cancel: "Annulla",
    saved: "Lettura salvata",
    unreadable: "Non riesco a leggere le cifre. Riprova con più luce o più vicino, oppure inserisci il valore a mano.",
    lower: "Il valore è più basso dell'ultima lettura. Se hai sostituito il contatore, conferma.",
    jump: "L'aumento è molto grande rispetto all'ultima lettura. Controlla il valore prima di confermare.",
    replaceConfirm: "Contatore sostituito: conferma",
    forceConfirm: "Confermo comunque",
    invalid: "Inserisci un numero intero.",
    unavailable: "Nessuna lettura disponibile",
    file: "File",
    importTitle: "Importa letture da file",
    impFound: "Letture trovate",
    impRange: "dal %from% al %to%, da %a% a %b% m³",
    impTotal: "Consumo complessivo",
    impSetsCurrent: "L'ultima lettura del file diventerà la lettura attuale.",
    impKeepsCurrent: "La lettura attuale resta invariata (il file contiene solo dati precedenti).",
    impDecreases: "Letture in diminuzione (contatore sostituito o errori), non vengono sommate:",
    impIgnored: "Righe ignorate:",
    impEstimate: "Il consumo tra una lettura e l'altra viene ripartito sui giorni (stima) per costruire il grafico.",
    import: "Importa",
    imported: "Importate %n% letture",
    importedStats: "storico ricostruito: %h% ore",
    importStatsError: "Letture importate, ma lo storico dei grafici non è stato scritto:",
    errEmpty: "Il file è vuoto.",
    errNoReadings: "Non ho trovato letture valide. Servono almeno una colonna con la data e una con il valore (per esempio data;lettura).",
    errMultiple: "Il file contiene più entità, tienine una sola:",
    errTooLarge: "Il file è troppo grande (massimo 2 MB).",
    notFound: "Entità non trovata:",
    noMeter: "Nessun contatore dell'integrazione trovato per:",
    wrongEntity: "Questa non è la \"Lettura contatore\" dell'integrazione (manca entry_id). Usa il sensore con gli attributi entry_id e meter_type:",
  },
  en: {
    last: "Last reading",
    today: "Today",
    month: "This month",
    year: "This year",
    days: "Days",
    months: "Months",
    years: "Years",
    total: "Total",
    average: "Average",
    perDay: "per day",
    perMonth: "per month",
    perYear: "per year",
    noStats: "No history available",
    readings: "Latest readings",
    replaced: "meter replaced",
    newReading: "New reading",
    save: "Save",
    photo: "Photo",
    reading_photo: "Reading the photo…",
    proposed: "Value read from the photo",
    check: "Check the value",
    confirm: "Confirm",
    cancel: "Cancel",
    saved: "Reading saved",
    unreadable: "I cannot read the digits. Try again with more light or closer, or type the value.",
    lower: "The value is lower than the last reading. If you replaced the meter, confirm.",
    jump: "The increase is very large compared with the last reading. Check the value before confirming.",
    replaceConfirm: "Meter replaced: confirm",
    forceConfirm: "Confirm anyway",
    invalid: "Enter a whole number.",
    unavailable: "No reading available",
    file: "File",
    importTitle: "Import readings from a file",
    impFound: "Readings found",
    impRange: "from %from% to %to%, from %a% to %b% m³",
    impTotal: "Total consumption",
    impSetsCurrent: "The last reading in the file will become the current reading.",
    impKeepsCurrent: "The current reading is unchanged (the file only has older data).",
    impDecreases: "Decreasing readings (meter replaced or errors), not added up:",
    impIgnored: "Rows ignored:",
    impEstimate: "Consumption between readings is spread over the days (estimate) to build the chart.",
    import: "Import",
    imported: "Imported %n% readings",
    importedStats: "history rebuilt: %h% hours",
    importStatsError: "Readings imported, but the chart history was not written:",
    errEmpty: "The file is empty.",
    errNoReadings: "No valid readings found. A date column and a value column are needed (e.g. date;reading).",
    errMultiple: "The file contains several entities, keep just one:",
    errTooLarge: "The file is too large (2 MB maximum).",
    notFound: "Entity not found:",
    noMeter: "No meter of the integration found for:",
    wrongEntity: "This is not the integration's \"Meter reading\" sensor (entry_id missing). Use the sensor that has the entry_id and meter_type attributes:",
  },
};

const MAX_SIDE = 1600;
const STATIC = "/rilevatore_consumi_static";
const TABS = ["days", "months", "years"];
const STATS_TTL_MS = 10 * 60 * 1000;

class RilevatoreConsumiCard extends HTMLElement {
  setConfig(config) {
    if (!config || (!config.entity && !config.meter)) {
      throw new Error("meter (gas | water) or entity is required");
    }
    this._config = config;
    this._pending = null; // {value, warning, photoUrl}
    this._imp = null; // {text, summary}
    this._message = "";
    this._busy = false;
    this._tab = "months";
    this._stats = {}; // tab -> {at, key, buckets}
    this._built = false;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  getCardSize() {
    return 8;
  }

  static getStubConfig() {
    return { meter: "gas" };
  }

  get _t() {
    const lang = (this._hass && this._hass.language) || "en";
    return TEXTS[lang.startsWith("it") ? "it" : "en"];
  }

  get _lang() {
    return (this._hass && this._hass.language) || "en";
  }

  // ---------------------------------------------------------------- entità
  _entityId() {
    if (this._config.entity) return this._config.entity;
    const states = (this._hass && this._hass.states) || {};
    const wanted = String(this._config.meter || "").toLowerCase();
    const found = Object.keys(states)
      .filter((id) => id.startsWith("sensor."))
      .filter((id) => {
        const a = states[id].attributes || {};
        return a.entry_id && a.meter_type === wanted;
      })
      .sort();
    return found.length ? found[0] : null;
  }

  _state() {
    const id = this._entityId();
    return id && this._hass ? this._hass.states[id] : undefined;
  }

  // ---------------------------------------------------------------- struttura
  _render() {
    if (this._built) return;
    this._built = true;
    this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `
      <style>
        ha-card { padding: 16px; }
        .title { font-size: 1.2em; font-weight: 500; margin-bottom: 4px; }
        .big { font-size: 2.2em; font-weight: 500; line-height: 1.1; }
        .sub { color: var(--secondary-text-color); font-size: 0.9em; margin-bottom: 12px; }
        .tiles { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; margin: 8px 0 16px; }
        .tile { background: var(--secondary-background-color); border-radius: 10px; padding: 10px 8px; text-align: center; }
        .tile .v { font-size: 1.4em; font-weight: 500; }
        .tile .l { font-size: 0.8em; color: var(--secondary-text-color); }
        .tabs { display: flex; gap: 6px; margin-bottom: 6px; }
        .tabs button { flex: 1; padding: 6px 4px; font-size: 0.9em; background: var(--secondary-background-color);
          color: var(--primary-text-color); }
        .tabs button.active { background: var(--primary-color); color: var(--text-primary-color, #fff); }
        .chart svg { width: 100%; height: auto; display: block; }
        .bar { fill: var(--primary-color); opacity: 0.55; }
        .bar.now { opacity: 1; }
        .axis { fill: var(--secondary-text-color); font-size: 9px; }
        .val { fill: var(--primary-text-color); font-size: 9px; }
        .base { stroke: var(--divider-color); stroke-width: 1; }
        .summary { display: flex; justify-content: space-between; color: var(--secondary-text-color);
          font-size: 0.9em; margin: 4px 0 12px; }
        .empty { color: var(--secondary-text-color); text-align: center; padding: 16px 0; }
        h3 { font-size: 1em; font-weight: 500; margin: 12px 0 4px; }
        .list { font-size: 0.92em; }
        .list .r { display: flex; justify-content: space-between; padding: 4px 0;
          border-bottom: 1px solid var(--divider-color); gap: 8px; }
        .list .r span:first-child { color: var(--secondary-text-color); }
        .row { display: flex; gap: 8px; align-items: center; margin: 8px 0; flex-wrap: wrap; }
        input[type=number] { flex: 1 1 120px; min-width: 0; font-size: 1.1em; padding: 10px;
          border-radius: 8px; border: 1px solid var(--divider-color);
          background: var(--card-background-color); color: var(--primary-text-color); }
        button { font-size: 1em; padding: 10px 14px; border-radius: 8px; border: none; cursor: pointer;
          background: var(--primary-color); color: var(--text-primary-color, #fff); }
        button.secondary { background: var(--secondary-background-color); color: var(--primary-text-color); }
        button:disabled { opacity: 0.5; cursor: default; }
        .msg { margin-top: 8px; font-size: 0.95em; }
        .msg.error { color: var(--error-color); }
        .msg.ok { color: var(--success-color, green); }
        .pending { margin-top: 12px; padding: 12px; border-radius: 8px;
          background: var(--secondary-background-color); }
        .pending img { max-width: 100%; max-height: 160px; border-radius: 8px; display: block; margin-bottom: 8px; }
        .head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
        .headtxt { min-width: 0; }
        .meterimg { width: 96px; max-height: 96px; object-fit: contain; border-radius: 8px; flex: none; }
        .import { margin-top: 12px; padding: 12px; border-radius: 8px; background: var(--secondary-background-color); }
        .import p { margin: 4px 0; font-size: 0.92em; }
        .import .warn { color: var(--warning-color, #ffa600); }
        .hidden { display: none; }
      </style>
      <ha-card>
        <div class="head">
          <div class="headtxt">
            <div class="title"></div>
            <div class="big"></div>
            <div class="sub"></div>
          </div>
          <img class="meterimg hidden" alt="">
        </div>
        <div class="tiles">
          <div class="tile"><div class="v" id="vDay"></div><div class="l" id="lDay"></div></div>
          <div class="tile"><div class="v" id="vMonth"></div><div class="l" id="lMonth"></div></div>
          <div class="tile"><div class="v" id="vYear"></div><div class="l" id="lYear"></div></div>
        </div>
        <div class="tabs"></div>
        <div class="chart"></div>
        <div class="summary"></div>
        <h3 id="hReadings"></h3>
        <div class="list"></div>
        <div class="row">
          <input id="value" type="number" inputmode="numeric" step="1" min="0">
          <button id="save"></button>
          <button id="photo" class="secondary"></button>
          <button id="csv" class="secondary"></button>
          <input id="file" type="file" accept="image/*" capture="environment" class="hidden">
          <input id="csvfile" type="file" accept=".csv,.txt,text/csv,text/plain" class="hidden">
        </div>
        <div class="pending hidden">
          <img id="preview" class="hidden" alt="">
          <div id="pendingText"></div>
          <div class="row">
            <input id="pendingValue" type="number" inputmode="numeric" step="1" min="0">
            <button id="confirm"></button>
            <button id="cancel" class="secondary"></button>
          </div>
        </div>
        <div class="import hidden">
          <div id="impTitle"><b></b></div>
          <div id="impBody"></div>
          <div class="row">
            <button id="impGo"></button>
            <button id="impCancel" class="secondary"></button>
          </div>
        </div>
        <div class="msg"></div>
      </ha-card>`;
    const $ = (s) => this.shadowRoot.querySelector(s);
    $("#save").addEventListener("click", () => this._onSave());
    $("#photo").addEventListener("click", () => $("#file").click());
    $("#file").addEventListener("change", (ev) => this._onFile(ev));
    $("#confirm").addEventListener("click", () => this._onConfirm());
    $("#cancel").addEventListener("click", () => this._cancel());
    $("#csv").addEventListener("click", () => $("#csvfile").click());
    $("#csvfile").addEventListener("change", (ev) => this._onCsv(ev));
    $("#impGo").addEventListener("click", () => this._importFile(true));
    $("#impCancel").addEventListener("click", () => this._cancelImport());
    $(".meterimg").addEventListener("error", (ev) => ev.target.classList.add("hidden"));
    $(".tabs").addEventListener("click", (ev) => {
      const tab = ev.target && ev.target.dataset && ev.target.dataset.tab;
      if (tab) this._selectTab(tab);
    });
  }

  // ---------------------------------------------------------------- aggiornamento
  _update() {
    if (!this._built || !this._hass) return;
    const $ = (s) => this.shadowRoot.querySelector(s);
    const t = this._t;
    const id = this._entityId();
    const state = this._state();
    const attrs = (state && state.attributes) || {};
    const title = this._config.title || attrs.friendly_name || id || this._config.meter;
    $(".title").textContent = title;
    const available = state && state.state !== "unavailable" && state.state !== "unknown";
    $(".big").textContent = available ? `${this._fmt(Number(state.state))} m³` : t.unavailable;
    const last = attrs.last_reading_time;
    $(".sub").textContent = last ? `${t.last}: ${new Date(last).toLocaleString(this._lang)}` : "";

    const sib = (key) => {
      const s = attrs[key] ? this._hass.states[attrs[key]] : undefined;
      const n = s ? Number(s.state) : NaN;
      return Number.isNaN(n) ? null : n;
    };
    this._cur = { days: sib("day_entity"), months: sib("month_entity"), years: sib("year_entity") };
    const tile = (v) => (v === null ? "—" : `${this._fmt(v)} m³`);
    $("#vDay").textContent = tile(this._cur.days);
    $("#vMonth").textContent = tile(this._cur.months);
    $("#vYear").textContent = tile(this._cur.years);
    $("#lDay").textContent = t.today;
    $("#lMonth").textContent = t.month;
    $("#lYear").textContent = t.year;
    $("#hReadings").textContent = t.readings;

    this._renderImage(attrs);
    $("#save").textContent = t.save;
    $("#photo").textContent = `📷 ${t.photo}`;
    $("#csv").textContent = `📁 ${t.file}`;
    $("#confirm").textContent = t.confirm;
    $("#cancel").textContent = t.cancel;
    $("#value").placeholder = t.newReading;
    $("#save").disabled = this._busy;
    $("#photo").disabled = this._busy;
    $("#csv").disabled = this._busy;

    const msg = $(".msg");
    msg.textContent = this._message;
    msg.className = "msg " + (this._messageKind || "");

    this._renderTabs();
    this._renderReadings(attrs.recent_readings || []);
    this._renderPending();
    this._renderImport();

    // Grafico: si ricarica se cambia entità, scheda o lettura (o dopo un po')
    const key = `${id}|${attrs.last_reading_time || ""}|${this._cur.days}|${this._cur.months}|${this._cur.years}`;
    const cached = this._stats[this._tab];
    if (id && attrs.entry_id && (!cached || cached.key !== key || Date.now() - cached.at > STATS_TTL_MS)) {
      this._loadStats(this._tab, id, key);
    } else if (cached) {
      this._renderChart(cached.buckets);
    } else {
      this._renderChart(null);
    }
  }

  _fmt(n) {
    return new Intl.NumberFormat(this._lang, { maximumFractionDigits: 1 }).format(n);
  }

  _renderTabs() {
    const t = this._t;
    const tabs = this.shadowRoot.querySelector(".tabs");
    const html = TABS.map(
      (k) => `<button class="${k === this._tab ? "active" : ""}" data-tab="${k}">${t[k]}</button>`
    ).join("");
    if (tabs.innerHTML !== html) tabs.innerHTML = html;
  }

  _selectTab(tab) {
    this._tab = tab;
    const cached = this._stats[tab];
    this._renderTabs();
    this._renderChart(cached ? cached.buckets : null);
    this._update();
  }

  // ---------------------------------------------------------------- statistiche
  _range(tab) {
    const now = new Date();
    const y = now.getFullYear();
    const m = now.getMonth();
    if (tab === "days") {
      const start = new Date(y, m, now.getDate() - 29);
      return { period: "day", start };
    }
    if (tab === "months") {
      return { period: "month", start: new Date(y, m - 11, 1) };
    }
    return { period: "month", start: new Date(y - 4, 0, 1) };
  }

  _bucketsFor(tab, rows) {
    const now = new Date();
    const y = now.getFullYear();
    const m = now.getMonth();
    const d = now.getDate();
    const lang = this._lang;
    const byKey = {};
    for (const r of rows || []) {
      const dt = new Date(r.start);
      const key =
        tab === "days"
          ? `${dt.getFullYear()}-${dt.getMonth()}-${dt.getDate()}`
          : tab === "months"
          ? `${dt.getFullYear()}-${dt.getMonth()}`
          : `${dt.getFullYear()}`;
      byKey[key] = (byKey[key] || 0) + (Number(r.change) || 0);
    }
    const out = [];
    if (tab === "days") {
      for (let i = 29; i >= 0; i--) {
        const dt = new Date(y, m, d - i);
        out.push({
          key: `${dt.getFullYear()}-${dt.getMonth()}-${dt.getDate()}`,
          label: dt.getDate() === 1 || i === 29 || i === 0 ? String(dt.getDate()) : String(dt.getDate()),
          title: dt.toLocaleDateString(lang, { day: "numeric", month: "short" }),
          now: i === 0,
        });
      }
    } else if (tab === "months") {
      for (let i = 11; i >= 0; i--) {
        const dt = new Date(y, m - i, 1);
        out.push({
          key: `${dt.getFullYear()}-${dt.getMonth()}`,
          label: dt.toLocaleDateString(lang, { month: "short" }),
          title: dt.toLocaleDateString(lang, { month: "long", year: "numeric" }),
          now: i === 0,
        });
      }
    } else {
      for (let i = 4; i >= 0; i--) {
        out.push({ key: `${y - i}`, label: String(y - i), title: String(y - i), now: i === 0 });
      }
    }
    for (const b of out) {
      b.value = Math.max(0, Math.round((byKey[b.key] || 0) * 10) / 10);
      if (b.now && this._cur && this._cur[tab] !== null && this._cur[tab] !== undefined) {
        b.value = this._cur[tab]; // il periodo in corso si prende dal sensore (esatto)
      }
    }
    return out;
  }

  async _loadStats(tab, id, key) {
    if (this._loading === `${tab}|${key}`) return;
    this._loading = `${tab}|${key}`;
    const { period, start } = this._range(tab);
    let rows = [];
    try {
      const res = await this._hass.callWS({
        type: "recorder/statistics_during_period",
        start_time: start.toISOString(),
        end_time: new Date(Date.now() + 3600 * 1000).toISOString(),
        statistic_ids: [id],
        period,
        types: ["change"],
      });
      rows = (res && res[id]) || [];
    } catch (err) {
      rows = []; // recorder non disponibile: restano i dati dei sensori
    }
    this._stats[tab] = { at: Date.now(), key, buckets: this._bucketsFor(tab, rows) };
    this._loading = null;
    if (tab === this._tab) this._renderChart(this._stats[tab].buckets);
  }

  _renderChart(buckets) {
    const t = this._t;
    const chart = this.shadowRoot.querySelector(".chart");
    const summary = this.shadowRoot.querySelector(".summary");
    if (!buckets || !buckets.some((b) => b.value > 0)) {
      chart.innerHTML = `<div class="empty">${t.noStats}</div>`;
      summary.textContent = "";
      return;
    }
    const W = 300;
    const H = 130;
    const top = 14;
    const bottom = 18;
    const n = buckets.length;
    const step = W / n;
    const bw = Math.max(2, step * 0.7);
    const max = Math.max(...buckets.map((b) => b.value)) || 1;
    const labelEvery = n > 12 ? 5 : 1;
    let bars = "";
    buckets.forEach((b, i) => {
      const h = Math.max(b.value > 0 ? 1.5 : 0, ((H - top - bottom) * b.value) / max);
      const x = i * step + (step - bw) / 2;
      const y = H - bottom - h;
      bars += `<rect class="bar${b.now ? " now" : ""}" x="${x.toFixed(1)}" y="${y.toFixed(1)}"
        width="${bw.toFixed(1)}" height="${h.toFixed(1)}" rx="1.5"><title>${b.title}: ${this._fmt(b.value)} m³</title></rect>`;
      if (n <= 12 && b.value > 0) {
        bars += `<text class="val" x="${(x + bw / 2).toFixed(1)}" y="${(y - 2).toFixed(1)}" text-anchor="middle">${this._fmt(b.value)}</text>`;
      }
      if ((n - 1 - i) % labelEvery === 0 || i === 0) {
        bars += `<text class="axis" x="${(x + bw / 2).toFixed(1)}" y="${H - 5}" text-anchor="middle">${b.label}</text>`;
      }
    });
    chart.innerHTML = `<svg viewBox="0 0 ${W} ${H}" role="img">
      <line class="base" x1="0" y1="${H - bottom}" x2="${W}" y2="${H - bottom}"></line>${bars}</svg>`;
    const total = buckets.reduce((s, b) => s + b.value, 0);
    // la media considera solo i periodi già conclusi o in corso con dati
    const first = buckets.findIndex((b) => b.value > 0);
    const used = buckets.slice(first);
    const avg = total / used.length;
    const unit = { days: t.perDay, months: t.perMonth, years: t.perYear }[this._tab];
    summary.innerHTML = `<span>${t.total}: <b>${this._fmt(total)} m³</b></span><span>${t.average}: <b>${this._fmt(avg)} m³</b> ${unit}</span>`;
  }

  // ---------------------------------------------------------------- ultime letture
  _renderReadings(rows) {
    const t = this._t;
    const list = this.shadowRoot.querySelector(".list");
    const items = rows.slice(-6).reverse();
    const all = rows.slice(-7);
    const html = items
      .map((r, i) => {
        const prev = all[all.length - 2 - i];
        const delta = prev && !r.replaced ? r.v - prev.v : null;
        const d = delta !== null && delta >= 0 ? ` <small>(+${this._fmt(delta)})</small>` : "";
        const note = r.replaced ? ` <small>· ${t.replaced}</small>` : "";
        return `<div class="r"><span>${new Date(r.t).toLocaleString(this._lang, {
          day: "numeric",
          month: "short",
          year: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        })}</span><span><b>${this._fmt(r.v)}</b> m³${d}${note}</span></div>`;
      })
      .join("");
    if (list.innerHTML !== html) list.innerHTML = html;
  }

  // ---------------------------------------------------------------- conferma
  _renderPending() {
    const $ = (s) => this.shadowRoot.querySelector(s);
    const box = $(".pending");
    if (!this._pending) {
      box.classList.add("hidden");
      return;
    }
    const t = this._t;
    box.classList.remove("hidden");
    const img = $("#preview");
    if (this._pending.photoUrl) {
      img.src = this._pending.photoUrl;
      img.classList.remove("hidden");
    } else {
      img.classList.add("hidden");
    }
    const warn = this._pending.warning;
    $("#pendingText").textContent = `${this._pending.photoUrl ? t.proposed : t.check}${
      warn === "lower" ? ` — ${t.lower}` : warn === "jump" ? ` — ${t.jump}` : ""
    }`;
    const input = $("#pendingValue");
    if (this.shadowRoot.activeElement !== input && this._pending.fresh) {
      input.value = this._pending.value;
      this._pending.fresh = false;
    }
    $("#confirm").textContent =
      warn === "lower" ? t.replaceConfirm : warn === "jump" ? t.forceConfirm : t.confirm;
  }

  _renderImage(attrs) {
    const img = this.shadowRoot.querySelector(".meterimg");
    const cfg = this._config.image;
    let src = null;
    if (cfg === false || cfg === "none") {
      src = null;
    } else if (typeof cfg === "string" && cfg) {
      src = cfg;
    } else {
      const type = attrs.meter_type || String(this._config.meter || "").toLowerCase();
      if (type) src = `${STATIC}/meter-${type === "water" ? "water" : "gas"}.png`;
    }
    if (!src) {
      img.classList.add("hidden");
      return;
    }
    if (img.getAttribute("src") !== src) {
      img.classList.remove("hidden");
      img.src = src;
    }
  }

  // ---------------------------------------------------------------- importazione da file
  async _onCsv(ev) {
    const file = ev.target.files && ev.target.files[0];
    ev.target.value = "";
    if (!file) return;
    if (!this._target()) return;
    let text;
    try {
      text = await file.text();
    } catch (err) {
      this._setMessage((err && err.message) || String(err), "error");
      return;
    }
    this._imp = { text, summary: null };
    await this._importFile(false);
  }

  _importError(data) {
    const t = this._t;
    const map = { empty: t.errEmpty, no_readings: t.errNoReadings, too_large: t.errTooLarge };
    if (data && data.code === "multiple_entities") {
      return `${t.errMultiple} ${(data.entities || []).join(", ")}`;
    }
    return (data && map[data.code]) || (data && data.message) || "Error";
  }

  async _importFile(commit) {
    const target = this._target();
    if (!target || !this._imp) return;
    this._busy = true;
    this._setMessage("", "");
    try {
      const resp = await this._hass.fetchWithAuth(
        `/api/rilevatore_consumi/import/${target.entryId}?commit=${commit ? 1 : 0}`,
        { method: "POST", headers: { "Content-Type": "text/csv" }, body: this._imp.text }
      );
      const data = await resp.json();
      if (!resp.ok) {
        this._imp = null;
        this._setMessage(this._importError(data), "error");
        return;
      }
      if (!commit) {
        this._imp.summary = data;
        this._message = "";
        return;
      }
      const t = this._t;
      this._imp = null;
      this._stats = {};
      let text = t.imported.replace("%n%", data.added);
      const st = data.statistics;
      if (st && st.error) {
        this._setMessage(`${t.importStatsError} ${st.error}`, "error");
      } else {
        if (st && st.imported_hours !== undefined) {
          text += ` · ${t.importedStats.replace("%h%", st.imported_hours + (st.adjusted_hours || 0))}`;
        }
        this._setMessage(text, "ok");
      }
    } catch (err) {
      this._setMessage((err && err.message) || String(err), "error");
    } finally {
      this._busy = false;
      this._update();
    }
  }

  _cancelImport() {
    this._imp = null;
    this._update();
  }

  _renderImport() {
    const box = this.shadowRoot.querySelector(".import");
    const imp = this._imp && this._imp.summary;
    if (!imp) {
      box.classList.add("hidden");
      return;
    }
    const t = this._t;
    const d = (iso) => new Date(iso).toLocaleDateString(this._lang);
    const range = t.impRange
      .replace("%from%", d(imp.from))
      .replace("%to%", d(imp.to))
      .replace("%a%", this._fmt(imp.first_value))
      .replace("%b%", this._fmt(imp.last_value));
    let html = `<p><b>${t.impFound}: ${imp.count}</b> — ${range}</p>
      <p>${t.impTotal}: <b>${this._fmt(imp.total)} m³</b></p>
      <p>${imp.sets_current ? t.impSetsCurrent : t.impKeepsCurrent}</p>
      <p>${t.impEstimate}</p>`;
    if (imp.decreases) html += `<p class="warn">${t.impDecreases} ${imp.decreases}</p>`;
    if (imp.ignored_rows) html += `<p class="warn">${t.impIgnored} ${imp.ignored_rows}</p>`;
    box.querySelector("#impTitle b").textContent = t.importTitle;
    box.querySelector("#impBody").innerHTML = html;
    box.querySelector("#impGo").textContent = t.import;
    box.querySelector("#impGo").disabled = this._busy;
    box.querySelector("#impCancel").textContent = t.cancel;
    box.classList.remove("hidden");
  }

  _setMessage(text, kind) {
    this._message = text;
    this._messageKind = kind || "";
    this._update();
  }

  _currentReading() {
    const state = this._state();
    const n = state ? parseInt(state.state, 10) : NaN;
    return Number.isNaN(n) ? null : n;
  }

  _warningFor(value) {
    const state = this._state();
    const current = this._currentReading();
    const maxJump = (state && state.attributes.max_jump) || Infinity;
    if (current === null) return null;
    if (value < current) return "lower";
    if (value - current > maxJump) return "jump";
    return null;
  }

  _target() {
    // Controlla che l'entità sia davvero quella dell'integrazione
    const t = this._t;
    const id = this._entityId();
    const state = this._state();
    if (!state) {
      this._setMessage(
        this._config.entity ? `${t.notFound} ${this._config.entity}` : `${t.noMeter} ${this._config.meter}`,
        "error"
      );
      return null;
    }
    if (!state.attributes.entry_id) {
      this._setMessage(`${t.wrongEntity} ${id}`, "error");
      return null;
    }
    return { id, entryId: state.attributes.entry_id };
  }

  _onSave() {
    if (!this._target()) return;
    const raw = this.shadowRoot.querySelector("#value").value;
    const value = parseInt(raw, 10);
    if (raw === "" || Number.isNaN(value) || value < 0) {
      this._setMessage(this._t.invalid, "error");
      return;
    }
    const warning = this._warningFor(value);
    if (warning) {
      this._pending = { value, warning, photoUrl: null, fresh: true };
      this._setMessage("", "");
      return;
    }
    this._save(value, false, false);
  }

  _onConfirm() {
    const raw = this.shadowRoot.querySelector("#pendingValue").value;
    const value = parseInt(raw, 10);
    if (raw === "" || Number.isNaN(value) || value < 0) {
      this._setMessage(this._t.invalid, "error");
      return;
    }
    // Rivaluta l'avviso sul valore eventualmente corretto a mano
    const warning = this._warningFor(value);
    this._save(value, warning === "jump", warning === "lower");
  }

  _cancel() {
    if (this._pending && this._pending.photoUrl) URL.revokeObjectURL(this._pending.photoUrl);
    this._pending = null;
    this._update();
  }

  async _save(value, force, replace) {
    const target = this._target();
    if (!target) return;
    this._busy = true;
    this._update();
    try {
      await this._hass.callService(
        "rilevatore_consumi",
        "set_reading",
        { reading: value, force, replace_meter: replace },
        { entity_id: target.id }
      );
      this.shadowRoot.querySelector("#value").value = "";
      this._cancel();
      this._stats = {};
      this._setMessage(this._t.saved, "ok");
    } catch (err) {
      this._setMessage((err && err.message) || String(err), "error");
    } finally {
      this._busy = false;
      this._update();
    }
  }

  async _onFile(ev) {
    const file = ev.target.files && ev.target.files[0];
    ev.target.value = "";
    if (!file) return;
    const target = this._target();
    if (!target) return;
    this._busy = true;
    this._setMessage(this._t.reading_photo, "");
    try {
      const blob = await this._downscale(file);
      const resp = await this._hass.fetchWithAuth(`/api/rilevatore_consumi/photo/${target.entryId}`, {
        method: "POST",
        headers: { "Content-Type": blob.type || "image/jpeg" },
        body: blob,
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.message || data.error || resp.statusText);
      if (!data.readable || data.reading === null || data.reading === undefined) {
        this._setMessage(this._t.unreadable, "error");
        return;
      }
      this._pending = {
        value: data.reading,
        warning: data.warning,
        photoUrl: URL.createObjectURL(blob),
        fresh: true,
      };
      this._setMessage("", "");
    } catch (err) {
      this._setMessage((err && err.message) || String(err), "error");
    } finally {
      this._busy = false;
      this._update();
    }
  }

  // Riduce la foto (lato lungo max 1600 px, JPEG) per un invio più rapido
  _downscale(file) {
    return new Promise((resolve) => {
      const url = URL.createObjectURL(file);
      const img = new Image();
      img.onload = () => {
        const scale = Math.min(1, MAX_SIDE / Math.max(img.width, img.height));
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
        URL.revokeObjectURL(url);
        canvas.toBlob((b) => resolve(b || file), "image/jpeg", 0.85);
      };
      img.onerror = () => {
        URL.revokeObjectURL(url);
        resolve(file);
      };
      img.src = url;
    });
  }
}

if (!customElements.get("rilevatore-consumi-card")) {
  customElements.define("rilevatore-consumi-card", RilevatoreConsumiCard);
}
window.customCards = window.customCards || [];
window.customCards.push({
  type: "rilevatore-consumi-card",
  name: "Rilevatore consumi",
  description: "Lettura del contatore (a mano o da foto) e report dei consumi.",
});
