"""Tests for the Wordnik API client."""

import re

import pytest
from aiohttp import ClientSession
from aioresponses import aioresponses

from custom_components.wordnik.api import (
    WordnikApiClient,
    WordnikAuthError,
    WordnikRateLimitError,
)
from custom_components.wordnik.const import TIER_EVERYDAY, TIERS

_ANY = re.compile(r"^https://api\.wordnik\.com/v4/.*")


async def test_validate_key_ok() -> None:
    """A 200 response validates the key."""
    with aioresponses() as mocked:
        mocked.get(_ANY, payload={"id": 1, "word": "test"})
        async with ClientSession() as session:
            client = WordnikApiClient(session, "key")
            await client.async_validate_key()


async def test_validate_key_auth_error() -> None:
    """A 401 raises WordnikAuthError."""
    with aioresponses() as mocked:
        mocked.get(_ANY, status=401)
        async with ClientSession() as session:
            client = WordnikApiClient(session, "bad")
            with pytest.raises(WordnikAuthError):
                await client.async_validate_key()


async def test_rate_limit_error() -> None:
    """A 429 raises WordnikRateLimitError."""
    with aioresponses() as mocked:
        mocked.get(_ANY, status=429)
        async with ClientSession() as session:
            client = WordnikApiClient(session, "key")
            with pytest.raises(WordnikRateLimitError):
                await client.async_random_words(TIERS[TIER_EVERYDAY], 5)


async def test_random_words_parses_words() -> None:
    """Random words returns the word strings."""
    with aioresponses() as mocked:
        mocked.get(_ANY, payload=[{"word": "alpha"}, {"word": "beta"}, {}])
        async with ClientSession() as session:
            client = WordnikApiClient(session, "key")
            words = await client.async_random_words(TIERS[TIER_EVERYDAY], 5)
    assert words == ["alpha", "beta"]


async def test_examples_parses_list() -> None:
    """Examples unwraps the examples list."""
    with aioresponses() as mocked:
        mocked.get(_ANY, payload={"examples": [{"text": "an example"}]})
        async with ClientSession() as session:
            client = WordnikApiClient(session, "key")
            examples = await client.async_examples("word", 5)
    assert examples[0]["text"] == "an example"
