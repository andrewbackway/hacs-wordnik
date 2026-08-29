# Wordnik Word of the Day

A custom [Home Assistant](https://www.home-assistant.io/) integration (installable
via [HACS](https://hacs.xyz/)) that surfaces a daily **Word of the Day** from the
[Wordnik API](https://developer.wordnik.com/), with a bundled Lovelace card.

- Daily word with **definition, example, and audio** (plus pronunciation).
- **Five difficulty tiers** — Sprout, Explorer, Everyday, Scholar, Luminary — each
  added as its own device so you can run several side by side.
- Configurable **daily rollover time** (default midnight).
- **New Word** on demand via the card button or the `wordnik.new_word` service.
- Polished **`wordnik-card`** Lovelace card, auto-registered — no manual resource
  setup, with a visual editor.

## Installation

### HACS (recommended)

1. Click the button below to open this repository in HACS, or add it manually
   under **HACS → ⋮ → Custom repositories** as an **Integration**
   (`https://github.com/andrewbackway/hacs-wordnik`).

   [![Open your Home Assistant instance and open this repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=andrewbackway&repository=hacs-wordnik&category=integration)

2. Install **Wordnik Word of the Day** and restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → Wordnik** (or use the
   button below).

   [![Open your Home Assistant instance and start setting up a new integration.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=wordnik)

4. Enter your [Wordnik API key](https://developer.wordnik.com/), pick one or more
   tiers, and set the rollover time.

Re-run **Add Integration** later to add more tiers (the API key is pre-filled).

### Manual

Copy `custom_components/wordnik` into your Home Assistant `config/custom_components`
directory and restart Home Assistant, then follow steps 3–4 above.

## Configuration

You'll need a free **Wordnik API key** from
[developer.wordnik.com](https://developer.wordnik.com/). One key works for every
tier and device.

### Setup options (Add Integration)

Set when you first add the integration (or when adding more tiers later).

| Option | Default | Description |
|--------|---------|-------------|
| **Wordnik API key** | — | Your Wordnik developer key. Validated during setup; a rejected key returns *invalid auth*. |
| **Difficulty tiers** | Everyday | One or more tiers to create. Each becomes its own device/entities. Tiers already configured are skipped. |
| **Daily rollover time** | `00:00:00` | Local time of day when a new word is chosen. |

### Difficulty tiers

Each tier is tuned by word length and Wordnik corpus frequency (how common a word
is). Higher corpus frequency = more common/easier words.

| Tier | Length | Corpus frequency | Intended audience |
|------|--------|------------------|-------------------|
| **Sprout** | 3–6 | ≥ 500,000 | Youngest learners; short, very common words. |
| **Explorer** | 3–9 | ≥ 200,000 | Kids; common everyday words. |
| **Everyday** | 3+ | ≥ 50,000 | General audience; the default tier. |
| **Scholar** | 4+ | 5,000–50,000 | Advanced; less common vocabulary. |
| **Luminary** | 4+ | ≤ 5,000 | Rare and obscure words for word nerds. |

Proper nouns, abbreviations, affixes, and idioms are excluded from every tier.

### Per-device options (Configure)

Open **Settings → Devices & Services → Wordnik → Configure** on any tier's device
to adjust these independently.

| Option | Default | Description |
|--------|---------|-------------|
| **Daily rollover time** | `00:00:00` | When this tier picks a new word each day. |
| **Show pronunciation sensor** | On | Adds/removes the pronunciation sensor entity. |
| **Default audio playback** | In browser | How the card plays word audio: *In browser* or *Media player* (cast). |
| **Media player (for casting)** | — | Target `media_player` used when audio mode is *Media player*. |
| **Word blocklist** | — | Comma- or newline-separated words to never pick for this tier. |

## The card

Add the **Wordnik Word of the Day** card from the card picker and select the tier's
`… _word` sensor. Options: title, show/hide pronunciation and example, show/hide the
New Word button, and audio playback in-browser or cast to a `media_player`.

## Services

| Service | Description |
|---------|-------------|
| `wordnik.refresh` | Silently re-fetch today's word (error recovery). |
| `wordnik.new_word` | Pick a fresh word now, bypassing the daily schedule. |

Both accept a device or entity target.

## Content safety

The kid-oriented tiers (Sprout/Explorer) use best-effort corpus and part-of-speech
filters plus an optional blocklist, but **cannot guarantee** child-appropriate
words from a general dictionary corpus.

## Attribution

Word data is provided by [Wordnik](https://www.wordnik.com/). Definitions and
examples display their required `attributionText`; use of the API is subject to the
[Wordnik Terms of Service](https://developer.wordnik.com/terms). You must supply your
own API key.
