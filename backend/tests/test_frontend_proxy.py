from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import SecretStr
from starlette.requests import Request

from app.config import settings
from app.graphql.context import client_ip_from_request
from app.main import app


def make_request(headers: dict[str, str], client_host: str = "10.0.0.5") -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [(key.lower().encode(), value.encode()) for key, value in headers.items()],
            "client": (client_host, 1234),
        }
    )


class FrontendProxyTests(unittest.TestCase):
    def setUp(self) -> None:
        patcher = patch.object(settings, "proxy_shared_secret", SecretStr("s3cret"))
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_requests_without_secret_are_rejected(self) -> None:
        response = TestClient(app).get("/auth/config")
        self.assertEqual(response.status_code, 404)

    def test_requests_with_wrong_secret_are_rejected(self) -> None:
        response = TestClient(app).get("/auth/config", headers={"x-tf-proxy-secret": "nope"})
        self.assertEqual(response.status_code, 404)

    def test_requests_with_secret_are_allowed(self) -> None:
        response = TestClient(app).get("/auth/config", headers={"x-tf-proxy-secret": "s3cret"})
        self.assertEqual(response.status_code, 200)

    def test_health_check_needs_no_secret(self) -> None:
        response = TestClient(app).get("/health")
        self.assertEqual(response.status_code, 200)

    def test_forwarded_ip_is_used_only_with_valid_secret(self) -> None:
        trusted = make_request({"x-tf-proxy-secret": "s3cret", "x-tf-client-ip": "203.0.113.9"})
        spoofed = make_request({"x-tf-proxy-secret": "bad", "x-tf-client-ip": "203.0.113.9"})

        self.assertEqual(client_ip_from_request(trusted), "203.0.113.9")
        self.assertEqual(client_ip_from_request(spoofed), "10.0.0.5")


class WithoutProxySecretTests(unittest.TestCase):
    def test_forwarded_ip_is_ignored_when_no_secret_is_configured(self) -> None:
        with patch.object(settings, "proxy_shared_secret", None):
            request = make_request({"x-tf-client-ip": "203.0.113.9"})
            self.assertEqual(client_ip_from_request(request), "10.0.0.5")
            response = TestClient(app).get("/auth/config")
        self.assertEqual(response.status_code, 200)


if __name__ == "__main__":
    unittest.main()
