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

2. Install **Wordnik Word of the Day** and **restart Home Assistant**.
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
tier and device (for fast access pay for the service, or wait a week).

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
| **Word blocklist** | — | Comma- or newline-separated words to never pick for this tier. |

## The card

The `wordnik-card` is bundled with the integration and **auto-registered** as a
frontend resource — there's nothing to add to your Lovelace resources manually.

To add it to a dashboard:

1. Edit a dashboard → **Add Card** → search for **Wordnik Word of the Day**.
2. In the visual editor, pick the tier's **`… _word`** sensor as the entity (the
   card discovers the related definition/example/audio/pronunciation entities
   automatically).
3. Adjust the display options, then save.

### Card options

Configurable in the visual editor or in YAML:

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `entity` | string | — | **Required.** The tier's `… _word` sensor. |
| `title` | string | `Word of the Day` | Heading shown above the word. |
| `show_pronunciation` | boolean | `true` | Show the phonetic pronunciation. |
| `show_example` | boolean | `true` | Show the example sentence. |
| `show_new_word` | boolean | `true` | Show the **New Word** button on the card. |
| `audio_mode` | `browser` \| `media_player` | `browser` | Where audio plays: in the browser or cast to a media player. |
| `media_player` | string | — | Target `media_player` entity when `audio_mode` is `media_player`. |

Example YAML:

```yaml
type: custom:wordnik-card
entity: sensor.wordnik_everyday_word
title: Word of the Day
show_pronunciation: true
show_example: true
show_new_word: true
audio_mode: media_player
media_player: media_player.living_room
```

### Multiple word levels

Each difficulty tier is its own device with its own set of entities, so you can run
several **side by side** — for example a **Sprout** card for kids and a **Luminary**
card for yourself. Add each tier during setup (or re-run **Add Integration** to add
more later — the API key is pre-filled), then place one card per tier, each pointing
at that tier's `… _word` sensor:

```yaml
type: vertical-stack
cards:
  - type: custom:wordnik-card
    entity: sensor.wordnik_sprout_word
    title: Kids' Word
  - type: custom:wordnik-card
    entity: sensor.wordnik_luminary_word
    title: Advanced Word
```

Each tier can also be tuned independently via its own **Configure** options
(rollover time, pronunciation, blocklist).

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
