import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

TOOLS_DIR = str(Path(__file__).resolve().parents[1] / "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import ufi_multi_provider_server as server

class MultiProviderServerTests(unittest.TestCase):
    def test_server_keeps_health_and_existing_routes(self):
        payload, hit = server.legacy.get_payload("/api/providers/status", {})
        self.assertFalse(hit)
        self.assertTrue(payload["ok"])
        self.assertIn("openMeteo", payload["providers"])

    def test_new_ev_route_is_wired_through_server(self):
        payload, hit = server.legacy.get_payload("/api/ev", {"probability":["0.2"],"odds":["5"]})
        self.assertFalse(hit)
        self.assertEqual(payload["expectedReturnPerUnit"], 0.0)

    def test_provider_status_never_echoes_secret(self):
        secret = "test-secret-not-for-output"
        with patch.dict(os.environ, {"SHARPAPI_KEY": secret}, clear=False):
            payload, _ = server.legacy.get_payload("/api/providers/status", {})
        self.assertNotIn(secret, str(payload))

if __name__ == "__main__":
    unittest.main()
