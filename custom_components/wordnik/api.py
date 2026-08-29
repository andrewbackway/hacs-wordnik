"""Async client for the Wordnik API."""

from __future__ import annotations

import asyncio
import logging
from urllib.parse import quote

from aiohttp import ClientError, ClientSession

from .const import API_BASE, EXCLUDE_POS

_LOGGER = logging.getLogger(__name__)


class WordnikError(Exception):
    """Base error for Wordnik API problems."""


class WordnikAuthError(WordnikError):
    """Raised when the API key is rejected."""


class WordnikRateLimitError(WordnikError):
    """Raised when the account hits its rate limit."""


class WordnikApiClient:
    """Thin async wrapper around the Wordnik v4 API."""

    def __init__(self, session: ClientSession, api_key: str) -> None:
        """Initialise the client."""
        self._session = session
        self._api_key = api_key

    async def _get(self, path: str, params: dict | None = None):
        """Perform a GET request and return decoded JSON (or None on 404)."""
        query = dict(params or {})
        query["api_key"] = self._api_key
        url = f"{API_BASE}{path}"
        try:
            async with self._session.get(url, params=query) as resp:
                if resp.status in (401, 403):
                    raise WordnikAuthError("Wordnik rejected the API key")
                if resp.status == 429:
                    raise WordnikRateLimitError("Wordnik rate limit reached")
                if resp.status == 404:
                    return None
                resp.raise_for_status()
                return await resp.json()
        except (ClientError, asyncio.TimeoutError) as err:
            raise WordnikError(f"Error talking to Wordnik: {err}") from err

    async def async_validate_key(self) -> None:
        """Make a lightweight call to confirm the API key works."""
        await self._get("/words.json/randomWord", {"hasDictionaryDef": "true"})

    async def async_random_words(self, profile: dict, limit: int) -> list[str]:
        """Return candidate words for a tier profile."""
        params: dict[str, str] = {
            "hasDictionaryDef": "true",
            "limit": str(limit),
            "minLength": str(profile["min_length"]),
            "excludePartOfSpeech": EXCLUDE_POS,
        }
        if profile.get("max_length"):
            params["maxLength"] = str(profile["max_length"])
        if profile.get("min_corpus"):
            params["minCorpusCount"] = str(profile["min_corpus"])
        if profile.get("max_corpus"):
            params["maxCorpusCount"] = str(profile["max_corpus"])
        data = await self._get("/words.json/randomWords", params)
        return [item["word"] for item in (data or []) if item.get("word")]

    async def async_definitions(self, word: str, limit: int) -> list[dict]:
        """Return definitions for a word."""
        data = await self._get(
            f"/word.json/{quote(word)}/definitions", {"limit": str(limit)}
        )
        return data or []

    async def async_examples(self, word: str, limit: int) -> list[dict]:
        """Return example sentences for a word."""
        data = await self._get(
            f"/word.json/{quote(word)}/examples", {"limit": str(limit)}
        )
        return (data or {}).get("examples", [])

    async def async_audio(self, word: str) -> list[dict]:
        """Return audio clips for a word."""
        data = await self._get(f"/word.json/{quote(word)}/audio", {"limit": "5"})
        return data or []

    async def async_pronunciations(self, word: str) -> list[dict]:
        """Return pronunciations for a word."""
        data = await self._get(
            f"/word.json/{quote(word)}/pronunciations", {"limit": "5"}
        )
        return data or []
