import httpx
import pytest

from conftest import ISS_TLE_TEXT
from sat_tracker.tle import TLEError, TLESource


def make_source(handler, cache_seconds=7200):
    """A TLESource whose 'internet' is the handler function we supply."""
    client = httpx.Client(transport=httpx.MockTransport(handler))
    # backoff_seconds=0 so retry tests don't actually wait.
    return TLESource("https://example.test/gp.php", cache_seconds, client=client, backoff_seconds=0)


def test_parses_tle(iss_tle):
    source = make_source(lambda request: httpx.Response(200, text=ISS_TLE_TEXT))
    assert source.get(25544) == iss_tle


def test_cache_avoids_repeat_downloads():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(200, text=ISS_TLE_TEXT)

    source = make_source(handler)
    source.get(25544)
    source.get(25544)
    assert len(calls) == 1


def test_serves_stale_data_when_upstream_fails(iss_tle):
    responses = iter([httpx.Response(200, text=ISS_TLE_TEXT), httpx.Response(500)])
    # cache_seconds=0 forces a re-download on every call.
    source = make_source(lambda request: next(responses), cache_seconds=0)

    source.get(25544)
    assert source.get(25544) == iss_tle


def test_retries_after_timeout(iss_tle):
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            raise httpx.ReadTimeout("simulated slow server", request=request)
        return httpx.Response(200, text=ISS_TLE_TEXT)

    assert make_source(handler).get(25544) == iss_tle
    assert len(calls) == 2


def test_gives_up_after_max_attempts():
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("always slow", request=request)

    with pytest.raises(httpx.ReadTimeout):
        make_source(handler).get(25544)
    assert len(calls) == 3


def test_does_not_retry_http_errors():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(403)

    with pytest.raises(httpx.HTTPStatusError):
        make_source(handler).get(25544)
    assert len(calls) == 1


def test_rejects_garbage():
    source = make_source(lambda request: httpx.Response(200, text="No GP data found"))
    with pytest.raises(TLEError):
        source.get(99999)
