/* Rilevatore consumi - card per inserire la lettura (a mano o da foto).
 * Uso:  type: custom:rilevatore-consumi-card
 *       entity: sensor.gas_consumption   # il sensore "Lettura contatore"
 *       title: Gas                       # facoltativo
 */
const TEXTS = {
  it: {
    reading: "Lettura attuale",
    last: "Ultima lettura",
    newReading: "Nuova lettura (m³)",
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
  },
  en: {
    reading: "Current reading",
    last: "Last reading",
    newReading: "New reading (m³)",
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
  },
};

const MAX_SIDE = 1600;

class RilevatoreConsumiCard extends HTMLElement {
  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("entity is required");
    }
    this._config = config;
    this._pending = null; // {value, warning, photoUrl}
    this._message = "";
    this._busy = false;
    this._built = false;
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  getCardSize() {
    return 4;
  }

  static getStubConfig() {
    return { entity: "sensor.gas_meter_reading" };
  }

  get _t() {
    const lang = (this._hass && this._hass.language) || "en";
    return TEXTS[lang.startsWith("it") ? "it" : "en"];
  }

  _render() {
    if (this._built) return;
    this._built = true;
    this.attachShadow({ mode: "open" });
    this.shadowRoot.innerHTML = `
      <style>
        ha-card { padding: 16px; }
        .title { font-size: 1.2em; font-weight: 500; margin-bottom: 8px; }
        .big { font-size: 2em; font-weight: 500; line-height: 1.1; }
        .sub { color: var(--secondary-text-color); font-size: 0.9em; margin-bottom: 12px; }
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
        .hidden { display: none; }
      </style>
      <ha-card>
        <div class="title"></div>
        <div class="big"></div>
        <div class="sub"></div>
        <div class="row">
          <input id="value" type="number" inputmode="numeric" step="1" min="0">
          <button id="save"></button>
          <button id="photo" class="secondary"></button>
          <input id="file" type="file" accept="image/*" capture="environment" class="hidden">
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
        <div class="msg"></div>
      </ha-card>`;
    const $ = (s) => this.shadowRoot.querySelector(s);
    $("#save").addEventListener("click", () => this._onSave());
    $("#photo").addEventListener("click", () => $("#file").click());
    $("#file").addEventListener("change", (ev) => this._onFile(ev));
    $("#confirm").addEventListener("click", () => this._onConfirm());
    $("#cancel").addEventListener("click", () => this._cancel());
  }

  _update() {
    if (!this._built || !this._hass) return;
    const $ = (s) => this.shadowRoot.querySelector(s);
    const t = this._t;
    const state = this._hass.states[this._config.entity];
    const title =
      this._config.title || (state && state.attributes.friendly_name) || this._config.entity;
    $(".title").textContent = title;
    const available = state && state.state !== "unavailable" && state.state !== "unknown";
    $(".big").textContent = available ? `${state.state} m³` : t.unavailable;
    const last = state && state.attributes.last_reading_time;
    $(".sub").textContent = last ? `${t.last}: ${new Date(last).toLocaleString(this._hass.language)}` : t.reading;
    $("#save").textContent = t.save;
    $("#photo").textContent = `📷 ${t.photo}`;
    $("#confirm").textContent = t.confirm;
    $("#cancel").textContent = t.cancel;
    $("#value").placeholder = t.newReading;
    $("#save").disabled = this._busy;
    $("#photo").disabled = this._busy;
    const msg = $(".msg");
    msg.textContent = this._message;
    msg.className = "msg " + (this._messageKind || "");
    this._renderPending();
  }

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
    $("#pendingText").textContent = `${this._pending.photoUrl ? t.proposed : t.check}${warn === "lower" ? ` — ${t.lower}` : warn === "jump" ? ` — ${t.jump}` : ""}`;
    const input = $("#pendingValue");
    if (document.activeElement !== input && this._pending.fresh) {
      input.value = this._pending.value;
      this._pending.fresh = false;
    }
    $("#confirm").textContent =
      warn === "lower" ? t.replaceConfirm : warn === "jump" ? t.forceConfirm : t.confirm;
  }

  _setMessage(text, kind) {
    this._message = text;
    this._messageKind = kind || "";
    this._update();
  }

  _currentReading() {
    const state = this._hass.states[this._config.entity];
    const n = state ? parseInt(state.state, 10) : NaN;
    return Number.isNaN(n) ? null : n;
  }

  _warningFor(value) {
    const state = this._hass.states[this._config.entity];
    const current = this._currentReading();
    const maxJump = (state && state.attributes.max_jump) || Infinity;
    if (current === null) return null;
    if (value < current) return "lower";
    if (value - current > maxJump) return "jump";
    return null;
  }

  _onSave() {
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
    this._busy = true;
    this._update();
    try {
      await this._hass.callService(
        "rilevatore_consumi",
        "set_reading",
        { reading: value, force, replace_meter: replace },
        { entity_id: this._config.entity }
      );
      this.shadowRoot.querySelector("#value").value = "";
      this._cancel();
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
    const state = this._hass.states[this._config.entity];
    const entryId = state && state.attributes.entry_id;
    if (!entryId) {
      this._setMessage("entry_id not found", "error");
      return;
    }
    this._busy = true;
    this._setMessage(this._t.reading_photo, "");
    try {
      const blob = await this._downscale(file);
      const resp = await this._hass.fetchWithAuth(`/api/rilevatore_consumi/photo/${entryId}`, {
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
  description: "Inserisci la lettura del contatore a mano o da foto.",
});
