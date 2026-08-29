"""Constants for the Wordnik Word of the Day integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "wordnik"
VERSION: Final = "0.1.2"
PLATFORMS: Final = ["sensor"]

# Config / options keys
CONF_API_KEY: Final = "api_key"
CONF_TIER: Final = "tier"
CONF_TIERS: Final = "tiers"
CONF_ROLLOVER: Final = "rollover_time"
CONF_SHOW_PRONUNCIATION: Final = "show_pronunciation"
CONF_BLOCKLIST: Final = "blocklist"

# Defaults
DEFAULT_ROLLOVER: Final = "00:00:00"
DEFAULT_SHOW_PRONUNCIATION: Final = True

# Wordnik API
API_BASE: Final = "https://api.wordnik.com/v4"
WORD_URL: Final = "https://www.wordnik.com/words/{word}"

# Local audio cache. Wordnik audio fileUrls are signed and expire, so we
# download the clip locally on each word update and serve it ourselves.
AUDIO_CACHE_DIRNAME: Final = f"{DOMAIN}_audio"
AUDIO_URL_BASE: Final = f"/{DOMAIN}/audio"

# Services
SERVICE_REFRESH: Final = "refresh"
SERVICE_NEW_WORD: Final = "new_word"

# Storage
STORAGE_VERSION: Final = 1

# Word-selection tuning
CANDIDATE_LIMIT: Final = 20
MAX_ASSEMBLE_ATTEMPTS: Final = 10
DEFINITIONS_LIMIT: Final = 10
EXAMPLES_LIMIT: Final = 5

# Parts of speech excluded from every tier (proper nouns, abbreviations, etc.)
EXCLUDE_POS: Final = (
    "proper-noun,proper-noun-plural,proper-noun-posessive,"
    "suffix,family-name,idiom,affix,abbreviation"
)

# Tier slugs
TIER_SPROUT: Final = "sprout"
TIER_EXPLORER: Final = "explorer"
TIER_EVERYDAY: Final = "everyday"
TIER_SCHOLAR: Final = "scholar"
TIER_LUMINARY: Final = "luminary"

# Tier profiles. Corpus/length thresholds are deliberately tunable; the
# boundaries between difficulty tiers are inherently fuzzy.
TIERS: Final[dict[str, dict]] = {
    TIER_SPROUT: {
        "name": "Sprout",
        "min_length": 3,
        "max_length": 6,
        "min_corpus": 500000,
        "max_corpus": None,
        "icon": "mdi:sprout",
        "color": "#4caf50",
    },
    TIER_EXPLORER: {
        "name": "Explorer",
        "min_length": 3,
        "max_length": 9,
        "min_corpus": 200000,
        "max_corpus": None,
        "icon": "mdi:compass",
        "color": "#2196f3",
    },
    TIER_EVERYDAY: {
        "name": "Everyday",
        "min_length": 3,
        "max_length": None,
        "min_corpus": 50000,
        "max_corpus": None,
        "icon": "mdi:book-open-variant",
        "color": "#607d8b",
    },
    TIER_SCHOLAR: {
        "name": "Scholar",
        "min_length": 4,
        "max_length": None,
        "min_corpus": 5000,
        "max_corpus": 50000,
        "icon": "mdi:school",
        "color": "#9c27b0",
    },
    TIER_LUMINARY: {
        "name": "Luminary",
        "min_length": 4,
        "max_length": None,
        "min_corpus": None,
        "max_corpus": 5000,
        "icon": "mdi:star-four-points",
        "color": "#ff9800",
    },
}
