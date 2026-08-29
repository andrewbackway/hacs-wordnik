# Wordnik Word of the Day

A custom [Home Assistant](https://www.home-assistant.io/) integration (installable
via [HACS](https://hacs.xyz/)) that surfaces a daily **Word of the Day** from the
[Wordnik API](https://developer.wordnik.com/), with a bundled Lovelace card.

## Features

- Daily word with **definition, example, and audio** (plus pronunciation).
- **Five difficulty tiers** — Sprout, Explorer, Everyday, Scholar, Luminary — each
  added as its own device so you can run several side by side.
- Configurable **daily rollover time** (default midnight).
- **New Word** on demand via the card button or the `wordnik.new_word` service.
- Polished **`wordnik-card`** Lovelace card, auto-registered — no manual resource
  setup, with a visual editor.

## Installation (HACS)

1. Add this repository to HACS as a custom **Integration** repository.
2. Install **Wordnik Word of the Day** and restart Home Assistant.
3. Go to **Settings → Devices & Services → Add Integration → Wordnik**.
4. Enter your [Wordnik API key](https://developer.wordnik.com/), pick one or more
   tiers, and set the rollover time.

Re-run **Add Integration** later to add more tiers (the API key is pre-filled).

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
