"""App settings, read from environment variables.

Reading settings from the environment (instead of hard-coding them) lets the
exact same code run on a laptop, in Docker, and in Kubernetes, with each place
supplying its own values. This is one of the "Twelve-Factor App" principles.
"""

import os
from dataclasses import dataclass

# The satellites we track, keyed by NORAD catalog number: the unique ID that
# US Space Command gives every tracked object in orbit.
SATELLITES: dict[int, str] = {
    25544: "ISS (International Space Station)",
    20580: "Hubble Space Telescope",
    48274: "Tiangong (Chinese Space Station)",
    49260: "Landsat 9",
}


@dataclass(frozen=True)
class Settings:
    observer_name: str
    latitude: float
    longitude: float
    elevation_m: float
    min_elevation_deg: float
    tle_url: str
    tle_cache_seconds: int


def load_settings() -> Settings:
    """Build Settings from environment variables, falling back to defaults (JMU)."""
    return Settings(
        observer_name=os.getenv("OBSERVER_NAME", "JMU, Harrisonburg VA"),
        latitude=float(os.getenv("OBSERVER_LAT", "38.4351")),
        longitude=float(os.getenv("OBSERVER_LON", "-78.8698")),
        elevation_m=float(os.getenv("OBSERVER_ELEVATION_M", "400")),
        min_elevation_deg=float(os.getenv("MIN_ELEVATION_DEG", "10")),
        tle_url=os.getenv("TLE_URL", "https://celestrak.org/NORAD/elements/gp.php"),
        # CelesTrak only updates data every few hours and asks users not to
        # download more often than that, so we cache for 2 hours by default.
        tle_cache_seconds=int(os.getenv("TLE_CACHE_SECONDS", "7200")),
    )
