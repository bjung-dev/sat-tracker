import pytest
from fastapi.testclient import TestClient

from sat_tracker.api import app, get_tle_source
from sat_tracker.tle import TLEError


class FakeTLESource:
    def __init__(self, tle=None):
        self.tle = tle

    def get(self, norad_id):
        if self.tle is None:
            raise TLEError("upstream down")
        return self.tle


@pytest.fixture
def client(iss_tle):
    app.dependency_overrides[get_tle_source] = lambda: FakeTLESource(iss_tle)
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_root_redirects_to_docs(client):
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"] == "/docs"


def test_healthz(client):
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_satellites(client):
    ids = [s["norad_id"] for s in client.get("/api/satellites").json()]
    assert 25544 in ids


def test_position(client):
    body = client.get("/api/satellites/25544/position").json()
    assert body["name"].startswith("ISS")
    assert {"latitude", "longitude", "altitude_km", "above_horizon"} <= body.keys()


def test_passes(client):
    body = client.get("/api/satellites/25544/passes?hours=48").json()
    assert body["hours"] == 48
    assert isinstance(body["passes"], list)


def test_unknown_satellite_is_404(client):
    assert client.get("/api/satellites/1/position").status_code == 404


def test_hours_out_of_range_is_422(client):
    assert client.get("/api/satellites/25544/passes?hours=500").status_code == 422


def test_upstream_failure_is_503():
    app.dependency_overrides[get_tle_source] = lambda: FakeTLESource(None)
    try:
        response = TestClient(app).get("/api/satellites/25544/position")
        assert response.status_code == 503
    finally:
        app.dependency_overrides.clear()
