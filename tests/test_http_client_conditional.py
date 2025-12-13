import responses

from backend.http_client import get


@responses.activate
def test_conditional_get_uses_cached_etag_and_handles_304():
    cache = {"etag": "abc"}
    url = "https://example.com/feed"
    responses.add(
        responses.GET,
        url,
        status=304,
        headers={"ETag": "abc"},
    )
    resp = get(url, cache=cache)
    assert resp.status_code == 304
    # cache should retain etag
    assert cache["etag"] == "abc"
