"""Phase 4e — Middleware tests (subdomain extraction)."""

import pytest

from multi_tenant_bootstrapper.core.middleware import _extract_subdomain


class TestExtractSubdomain:

    def test_extract_subdomain_from_host(self):
        assert _extract_subdomain("acme.example.com") == "acme"

    def test_extract_subdomain_localhost(self):
        assert _extract_subdomain("localhost:8000") is None

    def test_extract_subdomain_ip_address(self):
        assert _extract_subdomain("127.0.0.1:8000") is None

    def test_extract_subdomain_empty(self):
        assert _extract_subdomain("") is None

    def test_extract_subdomain_two_parts(self):
        """Two parts like 'example.com' returns 'example' as subdomain."""
        result = _extract_subdomain("example.com")
        assert result == "example"

    def test_extract_subdomain_ip_no_port(self):
        assert _extract_subdomain("192.168.1.1") is None

    def test_extract_subdomain_with_port(self):
        assert _extract_subdomain("acme.example.com:8080") == "acme"
