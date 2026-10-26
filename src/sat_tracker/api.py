"""The web API: URLs that return satellite data as JSON."""

from datetime import datetime, timezone
from functools import lru_cache

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.responses import RedirectResponse

from sat_tracker import orbits
from sat_tracker.config import SATELLITES, Settings, load_settings
from sat_tracker.tle import TLESource

app = FastAPI(
    title="Satellite Pass Tracker",
    description="Predicts when satellites pass over an observer, using live CelesTrak data.",
    version="0.1.0",
)


# These "dependencies" hand shared objects to each endpoint. Tests can swap
# them for fakes with app.dependency_overrides.
@lru_cache
def get_settings() -> Settings:
    return load_settings()


@lru_cache
def get_tle_source() -> TLESource:
    settings = get_settings()
    return TLESource(settings.tle_url, settings.tle_cache_seconds)


def _load_satellite(norad_id: int, tle_source: TLESource):
    if norad_id not in SATELLITES:
        raise HTTPException(status_code=404, detail=f"Satellite {norad_id} is not tracked")
    try:
        return orbits.make_satellite(tle_source.get(norad_id))
    except Exception as exc:
        # 503 = "Service Unavailable": our upstream data source failed.
        raise HTTPException(status_code=503, detail=f"Orbit data unavailable: {exc}") from exc


def _observer(settings: Settings):
    return orbits.make_observer(settings.latitude, settings.longitude, settings.elevation_m)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Send visitors of the bare URL to the interactive API docs."""
    return RedirectResponse(url="/docs")


@app.get("/healthz")
def healthz() -> dict:
    """Health check: Kubernetes will call this to see if the app is alive."""
    return {"status": "ok"}


@app.get("/api/satellites")
def list_satellites() -> list[dict]:
    return [{"norad_id": nid, "name": name} for nid, name in SATELLITES.items()]


@app.get("/api/satellites/{norad_id}/position")
def satellite_position(
    norad_id: int,
    settings: Settings = Depends(get_settings),
    tle_source: TLESource = Depends(get_tle_source),
) -> dict:
    sat = _load_satellite(norad_id, tle_source)
    now = datetime.now(timezone.utc)
    return {
        "norad_id": norad_id,
        "name": SATELLITES[norad_id],
        "observer": settings.observer_name,
        **orbits.current_position(sat, _observer(settings), now),
    }


@app.get("/api/satellites/{norad_id}/passes")
def satellite_passes(
    norad_id: int,
    hours: int = Query(24, ge=1, le=72, description="How far ahead to look"),
    settings: Settings = Depends(get_settings),
    tle_source: TLESource = Depends(get_tle_source),
) -> dict:
    sat = _load_satellite(norad_id, tle_source)
    now = datetime.now(timezone.utc)
    passes = orbits.upcoming_passes(sat, _observer(settings), now, hours, settings.min_elevation_deg)
    return {
        "norad_id": norad_id,
        "name": SATELLITES[norad_id],
        "observer": settings.observer_name,
        "min_elevation_deg": settings.min_elevation_deg,
        "hours": hours,
        "passes": passes,
    }
