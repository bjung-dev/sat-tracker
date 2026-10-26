from datetime import datetime, timezone

import pytest

from sat_tracker import orbits

JMU = orbits.make_observer(38.4351, -78.8698, 400)
# Shortly after the test TLE's timestamp, so predictions are accurate.
START = datetime(2026, 10, 26, 12, 0, tzinfo=timezone.utc)


def test_iss_position_is_physically_sensible(iss_tle):
    sat = orbits.make_satellite(iss_tle)
    pos = orbits.current_position(sat, JMU, START)

    # The ISS orbits roughly 400 km up...
    assert 370 < pos["altitude_km"] < 460
    # ...and its 51.6 degree orbit tilt means it never goes further north or south.
    assert -52 < pos["latitude"] < 52
    assert -180 <= pos["longitude"] <= 180


def test_iss_has_passes_over_jmu_in_a_day(iss_tle):
    sat = orbits.make_satellite(iss_tle)
    passes = orbits.upcoming_passes(sat, JMU, START, hours=24, min_elevation_deg=10)

    assert len(passes) >= 1
    for p in passes:
        assert p["rise_time"] < p["peak_time"] < p["set_time"]
        assert p["max_elevation_deg"] >= 10
        # A low-orbit pass is visible for minutes, not hours.
        assert 0 < p["duration_minutes"] < 15


@pytest.mark.parametrize(
    ("azimuth", "expected"),
    [(0, "N"), (44, "NE"), (90, "E"), (180, "S"), (270, "W"), (350, "N")],
)
def test_compass_direction(azimuth, expected):
    assert orbits.compass_direction(azimuth) == expected
