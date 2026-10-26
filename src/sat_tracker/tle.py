"""Download and cache TLE orbit data from CelesTrak.

A TLE ("Two-Line Element set") is a short text record describing a
satellite's orbit at a moment in time. Orbits slowly change (drag, engine
burns), so TLEs are re-published every few hours.
"""

import logging
import time
from dataclasses import dataclass

import httpx

logger = logging.getLogger("uvicorn.error")


class TLEError(Exception):
    """Raised when orbit data can't be fetched or doesn't look like a TLE."""


@dataclass(frozen=True)
class TLE:
    name: str
    line1: str
    line2: str


@dataclass
class _CacheEntry:
    tle: TLE
    fetched_at: float


class TLESource:
    def __init__(
        self,
        base_url: str,
        cache_seconds: int,
        client: httpx.Client | None = None,
        attempts: int = 3,
        backoff_seconds: float = 1.0,
    ):
        self.base_url = base_url
        self.cache_seconds = cache_seconds
        self.attempts = attempts
        self.backoff_seconds = backoff_seconds
        # Tests pass in a fake client so they never touch the real internet.
        self._client = client or httpx.Client(timeout=10.0)
        self._cache: dict[int, _CacheEntry] = {}

    def get(self, norad_id: int) -> TLE:
        """Return the TLE for a satellite, using the cache when it's fresh enough."""
        now = time.monotonic()
        cached = self._cache.get(norad_id)
        if cached and now - cached.fetched_at < self.cache_seconds:
            return cached.tle

        try:
            tle = self._fetch(norad_id)
        except (httpx.HTTPError, TLEError) as exc:
            # Reliability choice: slightly old orbit data is far better than
            # an error page, so if CelesTrak is down we serve what we have.
            if cached:
                logger.warning("Serving cached TLE for NORAD %s after error: %s", norad_id, exc)
                return cached.tle
            raise

        self._cache[norad_id] = _CacheEntry(tle, now)
        return tle

    def _download(self, norad_id: int) -> httpx.Response:
        """GET the TLE, retrying network hiccups (timeouts, dropped connections).

        We deliberately do NOT retry HTTP error codes like 403: those mean the
        server answered and said no, and hammering it would only make it worse.
        """
        for attempt in range(1, self.attempts + 1):
            try:
                return self._client.get(self.base_url, params={"CATNR": norad_id, "FORMAT": "TLE"})
            except httpx.TransportError as exc:
                if attempt == self.attempts:
                    raise
                # Wait a little longer after each failure ("backoff").
                delay = self.backoff_seconds * attempt
                logger.warning(
                    "CelesTrak request for NORAD %s failed (%s), retry %d/%d in %.0fs",
                    norad_id, exc, attempt, self.attempts - 1, delay,
                )
                time.sleep(delay)
        raise AssertionError("unreachable")

    def _fetch(self, norad_id: int) -> TLE:
        response = self._download(norad_id)
        response.raise_for_status()

        lines = [line.strip() for line in response.text.strip().splitlines()]
        if len(lines) != 3 or not lines[1].startswith("1 ") or not lines[2].startswith("2 "):
            raise TLEError(f"Unexpected response for NORAD {norad_id}: {response.text[:100]!r}")
        return TLE(name=lines[0], line1=lines[1], line2=lines[2])
