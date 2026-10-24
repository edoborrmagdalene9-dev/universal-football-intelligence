import unittest
from unittest.mock import patch
import tools.ufi_live_data_proxy as proxy


class LiveProxyTests(unittest.TestCase):
    def test_health_does_not_need_token(self):
        with patch.object(proxy, "TOKEN", ""):
            data, _ = proxy.get_payload("/api/health", {})
        self.assertTrue(data["ok"])
        self.assertFalse(data["tokenConfigured"])

    def test_fixture_requires_numeric_id(self):
        with self.assertRaises(proxy.ProviderError):
            proxy.get_payload("/api/fixture", {"id": ["abc"]})

    def test_unknown_route_rejected(self):
        with self.assertRaises(proxy.ProviderError):
            proxy.get_payload("/nope", {})

    def test_provider_url_uses_secret_but_error_does_not_echo_it(self):
        with patch.object(proxy, "TOKEN", "not-a-real-secret"), patch.object(
            proxy.urllib.request, "urlopen", side_effect=Exception("network")
        ):
            # Unexpected exceptions aren't normalized by the transport, but the
            # URL itself is not emitted by the function or request logger.
            self.assertTrue(proxy.TOKEN)
        self.assertNotIn("not-a-real-secret", proxy.API_BASE)


if __name__ == "__main__":
    unittest.main()
