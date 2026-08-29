/**
 * Wordnik Word of the Day — Lovelace card.
 *
 * Bundled with the integration and auto-registered as a frontend resource.
 * Dependency-free (vanilla custom element) so no build step is required.
 */

const TIER_META = {
  sprout: { label: "Sprout", color: "#4caf50", icon: "🌱" },
  explorer: { label: "Explorer", color: "#2196f3", icon: "🧭" },
  everyday: { label: "Everyday", color: "#607d8b", icon: "📖" },
  scholar: { label: "Scholar", color: "#9c27b0", icon: "🎓" },
  luminary: { label: "Luminary", color: "#ff9800", icon: "✨" },
};

class WordnikCard extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: "open" });
    this._audio = null;
  }

  setConfig(config) {
    if (!config || !config.entity) {
      throw new Error("Please choose the Wordnik 'Word' sensor as the entity.");
    }
    this._config = {
      title: "Word of the Day",
      show_pronunciation: true,
      show_example: true,
      show_new_word: true,
      audio_mode: "browser",
      ...config,
    };
    this._buildStructure();
  }

  set hass(hass) {
    this._hass = hass;
    this._update();
  }

  getCardSize() {
    return 4;
  }

  static getStubConfig(hass) {
    const entity = Object.keys(hass.states || {}).find(
      (id) => id.startsWith("sensor.") && id.endsWith("_word") && id.includes("wordnik")
    );
    return { entity: entity || "" };
  }

  static getConfigElement() {
    return document.createElement("wordnik-card-editor");
  }

  _relatedEntities() {
    const wordId = this._config.entity;
    const base = wordId.endsWith("_word") ? wordId.slice(0, -5) : wordId;
    return {
      word: wordId,
      definition: `${base}_definition`,
      example: `${base}_example`,
      audio: `${base}_audio`,
      pronunciation: `${base}_pronunciation`,
    };
  }

  _deviceId() {
    if (this._config.device_id) return this._config.device_id;
    const reg = this._hass && this._hass.entities;
    const entry = reg && reg[this._config.entity];
    return entry ? entry.device_id : undefined;
  }

  _buildStructure() {
    this.shadowRoot.innerHTML = `
      <style>
        ha-card {
          padding: 16px;
          display: flex;
          flex-direction: column;
          gap: 10px;
        }
        .header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        .title {
          font-size: 0.85rem;
          letter-spacing: 0.08em;
          text-transform: uppercase;
          color: var(--secondary-text-color);
        }
        .badge {
          font-size: 0.75rem;
          font-weight: 600;
          padding: 2px 10px;
          border-radius: 12px;
          color: #fff;
          white-space: nowrap;
        }
        .word-row {
          display: flex;
          align-items: center;
          gap: 10px;
        }
        .word {
          font-size: 2rem;
          font-weight: 700;
          color: var(--primary-text-color);
          line-height: 1.1;
        }
        .play {
          --mdc-icon-size: 22px;
          border: none;
          background: var(--secondary-background-color);
          color: var(--primary-text-color);
          border-radius: 50%;
          width: 38px;
          height: 38px;
          cursor: pointer;
          display: inline-flex;
          align-items: center;
          justify-content: center;
        }
        .play:disabled { opacity: 0.35; cursor: default; }
        .subline {
          font-size: 0.9rem;
          color: var(--secondary-text-color);
        }
        .pos { font-style: italic; margin-left: 6px; }
        .definition {
          font-size: 1rem;
          color: var(--primary-text-color);
        }
        .example {
          font-style: italic;
          color: var(--secondary-text-color);
          border-left: 3px solid var(--divider-color);
          padding-left: 10px;
        }
        .footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 8px;
          margin-top: 4px;
          font-size: 0.75rem;
          color: var(--secondary-text-color);
        }
        .footer a { color: var(--secondary-text-color); }
        .new-word {
          border: none;
          background: none;
          color: var(--primary-color);
          cursor: pointer;
          font-size: 0.8rem;
          font-weight: 600;
          display: inline-flex;
          align-items: center;
          gap: 4px;
        }
        .unavailable { color: var(--secondary-text-color); }
      </style>
      <ha-card>
        <div class="header">
          <span class="title"></span>
          <span class="badge"></span>
        </div>
        <div class="word-row">
          <span class="word"></span>
          <button class="play" title="Play audio">
            <ha-icon icon="mdi:play"></ha-icon>
          </button>
        </div>
        <div class="subline"></div>
        <div class="definition"></div>
        <div class="example"></div>
        <div class="footer">
          <span class="attribution"></span>
          <button class="new-word">
            <ha-icon icon="mdi:shuffle-variant"></ha-icon>
            <span>New Word</span>
          </button>
        </div>
      </ha-card>
    `;

    this.shadowRoot.querySelector(".play").addEventListener("click", () =>
      this._playAudio()
    );
    this.shadowRoot.querySelector(".new-word").addEventListener("click", () =>
      this._newWord()
    );
  }

  _state(id) {
    return this._hass && id ? this._hass.states[id] : undefined;
  }

  _update() {
    if (!this._hass || !this._config) return;
    const root = this.shadowRoot;
    const ids = this._relatedEntities();
    const wordState = this._state(ids.word);

    root.querySelector(".title").textContent = this._config.title;

    if (!wordState || wordState.state === "unavailable") {
      root.querySelector(".word").textContent = "Unavailable";
      root.querySelector(".word").classList.add("unavailable");
      root.querySelector(".subline").textContent = "";
      root.querySelector(".definition").textContent = "";
      root.querySelector(".example").textContent = "";
      root.querySelector(".play").disabled = true;
      root.querySelector(".badge").style.display = "none";
      return;
    }
    root.querySelector(".word").classList.remove("unavailable");

    const attrs = wordState.attributes || {};
    const tier = attrs.tier || (this._config.entity.split("_")[1] || "everyday");
    const meta = TIER_META[tier] || { label: attrs.tier_name || "", color: "#607d8b", icon: "" };
    const badge = root.querySelector(".badge");
    badge.style.display = meta.label ? "inline-block" : "none";
    badge.style.background = meta.color;
    badge.textContent = `${meta.icon} ${meta.label}`.trim();

    root.querySelector(".word").textContent = wordState.state;

    const pron = this._state(ids.pronunciation);
    const pos = attrs.part_of_speech ? `<span class="pos">${attrs.part_of_speech}</span>` : "";
    const pronText =
      this._config.show_pronunciation && pron && pron.state && pron.state !== "unknown"
        ? `/${pron.state}/`
        : "";
    root.querySelector(".subline").innerHTML = `${pronText}${pos}`;

    const def = this._state(ids.definition);
    root.querySelector(".definition").textContent = def ? def.state : "";

    const example = this._state(ids.example);
    const exampleEl = root.querySelector(".example");
    if (this._config.show_example && example && example.state && example.state !== "unknown") {
      exampleEl.style.display = "block";
      exampleEl.textContent = `“${example.state}”`;
    } else {
      exampleEl.style.display = "none";
    }

    const audio = this._state(ids.audio);
    const audioUrl = audio && audio.state ? audio.state : null;
    this._audioUrl =
      audioUrl && (audioUrl.startsWith("http") || audioUrl.startsWith("/"))
        ? audioUrl
        : null;
    root.querySelector(".play").disabled = !this._audioUrl;

    const attribution = attrs.attribution || (def && def.attributes && def.attributes.attribution) || "Wordnik";
    const url = attrs.word_url || `https://www.wordnik.com/words/${encodeURIComponent(wordState.state)}`;
    root.querySelector(".attribution").innerHTML =
      `${attribution} · <a href="${url}" target="_blank" rel="noopener">Wordnik</a>`;

    root.querySelector(".new-word").style.display = this._config.show_new_word
      ? "inline-flex"
      : "none";
  }

  _playAudio() {
    if (!this._audioUrl) return;
    if (this._config.audio_mode === "media_player" && this._config.media_player) {
      // Casting needs an absolute URL; local cached clips are served relative.
      const mediaUrl = this._audioUrl.startsWith("/")
        ? `${window.location.origin}${this._audioUrl}`
        : this._audioUrl;
      this._hass.callService("media_player", "play_media", {
        entity_id: this._config.media_player,
        media_content_id: mediaUrl,
        media_content_type: "music",
      });
      return;
    }
    if (this._audio) {
      this._audio.pause();
    }
    this._audio = new Audio(this._audioUrl);
    this._audio.play().catch(() => {});
  }

  _newWord() {
    const target = {};
    const deviceId = this._deviceId();
    if (deviceId) {
      target.device_id = deviceId;
    } else {
      target.entity_id = this._config.entity;
    }
    this._hass.callService("wordnik", "new_word", {}, target);
  }
}

const EDITOR_LABELS = {
  entity: "Word sensor",
  title: "Title",
  show_pronunciation: "Show pronunciation",
  show_example: "Show example",
  show_new_word: 'Show "New Word" button',
  audio_mode: "Audio playback",
  media_player: "Media player",
};

class WordnikCardEditor extends HTMLElement {
  setConfig(config) {
    this._config = { ...config };
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  connectedCallback() {
    this._render();
  }

  _schema(cfg) {
    const schema = [
      {
        name: "entity",
        required: true,
        selector: {
          entity: { filter: [{ integration: "wordnik", domain: "sensor" }] },
        },
      },
      { name: "title", selector: { text: {} } },
      { name: "show_pronunciation", selector: { boolean: {} } },
      { name: "show_example", selector: { boolean: {} } },
      { name: "show_new_word", selector: { boolean: {} } },
      {
        name: "audio_mode",
        selector: {
          select: {
            mode: "dropdown",
            options: [
              { value: "browser", label: "In browser" },
              { value: "media_player", label: "Media player" },
            ],
          },
        },
      },
    ];
    if (cfg.audio_mode === "media_player") {
      schema.push({
        name: "media_player",
        selector: { entity: { domain: "media_player" } },
      });
    }
    return schema;
  }

  _valueChanged(ev) {
    ev.stopPropagation();
    this.dispatchEvent(
      new CustomEvent("config-changed", { detail: { config: ev.detail.value } })
    );
  }

  _render() {
    if (!this._hass || !this._config || !this.isConnected) return;

    if (!this._form) {
      this._form = document.createElement("ha-form");
      this._form.computeLabel = (schema) => EDITOR_LABELS[schema.name] || schema.name;
      this._form.addEventListener("value-changed", (ev) => this._valueChanged(ev));
      this.appendChild(this._form);
    }

    const data = {
      title: "Word of the Day",
      show_pronunciation: true,
      show_example: true,
      show_new_word: true,
      audio_mode: "browser",
      ...this._config,
    };

    this._form.hass = this._hass;
    this._form.data = data;
    this._form.schema = this._schema(data);
  }
}

customElements.define("wordnik-card", WordnikCard);
customElements.define("wordnik-card-editor", WordnikCardEditor);

window.customCards = window.customCards || [];
window.customCards.push({
  type: "wordnik-card",
  name: "Wordnik Word of the Day",
  description: "Shows the daily Wordnik word with definition, example and audio.",
  preview: true,
  documentationURL: "https://github.com/andrewbackway/hacs-wordnik",
});
