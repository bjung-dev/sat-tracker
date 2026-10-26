"""Orbit math: where a satellite is now, and when it will pass overhead.

The heavy lifting is done by Skyfield, which implements SGP4, the standard
model for predicting a satellite's position from its TLE.
"""

from datetime import datetime, timedelta

from skyfield.api import EarthSatellite, load, wgs84
from skyfield.toposlib import GeographicPosition

from sat_tracker.tle import TLE

# A "timescale" converts ordinary dates into the precise time systems
# astronomers use. Skyfield ships the data it needs, so this works offline.
_ts = load.timescale()

_COMPASS = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]


def make_observer(latitude: float, longitude: float, elevation_m: float) -> GeographicPosition:
    return wgs84.latlon(latitude, longitude, elevation_m=elevation_m)


def make_satellite(tle: TLE) -> EarthSatellite:
    return EarthSatellite(tle.line1, tle.line2, tle.name, _ts)


def compass_direction(azimuth_deg: float) -> str:
    """Turn an azimuth (0 = north, 90 = east) into a label like 'NE'."""
    return _COMPASS[round(azimuth_deg / 45) % 8]


def current_position(sat: EarthSatellite, observer: GeographicPosition, when: datetime) -> dict:
    t = _ts.from_datetime(when)
    geocentric = sat.at(t)
    lat, lon = wgs84.latlon_of(geocentric)
    height = wgs84.height_of(geocentric)
    # Subtracting positions gives the view from the observer to the satellite.
    elevation, azimuth, distance = (sat - observer).at(t).altaz()

    return {
        "time": when.isoformat(),
        "latitude": round(lat.degrees, 4),
        "longitude": round(lon.degrees, 4),
        "altitude_km": round(height.km, 1),
        "elevation_deg": round(elevation.degrees, 2),
        "azimuth_deg": round(azimuth.degrees, 2),
        "range_km": round(distance.km, 1),
        "above_horizon": bool(elevation.degrees > 0),
    }


def upcoming_passes(
    sat: EarthSatellite,
    observer: GeographicPosition,
    start: datetime,
    hours: int,
    min_elevation_deg: float,
) -> list[dict]:
    """List passes where the satellite climbs above min_elevation_deg."""
    t0 = _ts.from_datetime(start)
    t1 = _ts.from_datetime(start + timedelta(hours=hours))
    # events: 0 = rises above the threshold, 1 = highest point, 2 = sets below it
    times, events = sat.find_events(observer, t0, t1, altitude_degrees=min_elevation_deg)

    passes = []
    current = None
    for t, event in zip(times, events):
        if event == 0:
            elevation, azimuth, _ = (sat - observer).at(t).altaz()
            current = {"rise": t, "rise_az": azimuth.degrees, "peak": None, "max_el": -90.0}
        elif event == 1 and current is not None:
            elevation, _, _ = (sat - observer).at(t).altaz()
            if elevation.degrees > current["max_el"]:
                current["peak"], current["max_el"] = t, elevation.degrees
        elif event == 2 and current is not None:
            _, azimuth, _ = (sat - observer).at(t).altaz()
            rise_dt = current["rise"].utc_datetime()
            set_dt = t.utc_datetime()
            passes.append(
                {
                    "rise_time": rise_dt.isoformat(),
                    "peak_time": current["peak"].utc_datetime().isoformat(),
                    "set_time": set_dt.isoformat(),
                    "duration_minutes": round((set_dt - rise_dt).total_seconds() / 60, 1),
                    "max_elevation_deg": round(current["max_el"], 1),
                    "rise_direction": compass_direction(current["rise_az"]),
                    "set_direction": compass_direction(azimuth.degrees),
                }
            )
            current = None
        # A pass already in progress at `start` has no rise event; we skip it.

    return passes
