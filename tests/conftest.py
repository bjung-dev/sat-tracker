"""Shared test fixtures. pytest loads this file automatically."""

import pytest

from sat_tracker.tle import TLE

# A real ISS TLE downloaded from CelesTrak on 2026-10-26. Freezing it here
# means the tests give the same answer every time, with no internet needed.
ISS_TLE = TLE(
    name="ISS (ZARYA)",
    line1="1 25544U 98067A   26299.20906838  .00006121  00000+0  11890-3 0  9995",
    line2="2 25544  51.6337  11.7282 0006920 310.9581  49.0809 15.49059765592065",
)
ISS_TLE_TEXT = f"{ISS_TLE.name}\n{ISS_TLE.line1}\n{ISS_TLE.line2}\n"


@pytest.fixture
def iss_tle() -> TLE:
    return ISS_TLE
