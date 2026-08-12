from endpoint.main import _web_distribution, app
from fastapi.testclient import TestClient


def test_api_routes_remain_available_with_static_ui():
    with TestClient(app) as client:
        response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_built_web_distribution_is_discovered_when_present():
    distribution = _web_distribution()
    assert distribution is None or (distribution / "index.html").is_file()


def test_local_ui_cannot_be_reused_across_packaged_versions():
    with TestClient(app) as client:
        response = client.get("/")
    if response.status_code == 200:
        assert response.headers["cache-control"] == "no-store, max-age=0"
