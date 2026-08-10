"""REST API integration tests."""

from __future__ import annotations

import pytest

httpx = pytest.importorskip("httpx")
from fastapi.testclient import TestClient

from openprompt.config.models import ServerConfig
from openprompt.server.app import create_app


@pytest.fixture
def client() -> TestClient:
    cfg = ServerConfig(api_key="test-secret", rate_limit_per_minute=1000)
    return TestClient(create_app(cfg))


@pytest.fixture
def authed(client: TestClient) -> TestClient:
    client.headers.update({"X-API-Key": "test-secret"})
    return client


def test_health_is_public(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_optimize_requires_api_key(client: TestClient) -> None:
    response = client.post("/optimize", json={"prompt": "Summarize this."})
    assert response.status_code == 401


def test_lint_and_optimize(authed: TestClient) -> None:
    lint_resp = authed.post("/lint", json={"prompt": "Summarize the article."})
    assert lint_resp.status_code == 200
    assert "score" in lint_resp.json()

    opt_resp = authed.post(
        "/optimize",
        json={"prompt": "Summarize the article.", "strategy": "rewrite", "provider": "mock"},
    )
    assert opt_resp.status_code == 200
    body = opt_resp.json()
    assert body["prompt"]
    assert "warnings" in body


def test_evaluate_with_tests(authed: TestClient) -> None:
    response = authed.post(
        "/evaluate",
        json={
            "prompt": "Classify sentiment as positive or negative.",
            "provider": "mock",
            "tests": [
                {
                    "name": "positive",
                    "input": "I love this product!",
                    "expected": "positive",
                    "metric": "exact_match",
                }
            ],
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["pass_rate"] >= 0
    assert len(data["results"]) == 1


def test_rate_limit_headers(client: TestClient) -> None:
    cfg = ServerConfig(api_key=None, rate_limit_per_minute=2)
    limited = TestClient(create_app(cfg))
    assert limited.post("/lint", json={"prompt": "a"}).status_code == 200
    assert limited.post("/lint", json={"prompt": "b"}).status_code == 200
    assert limited.post("/lint", json={"prompt": "c"}).status_code == 429
