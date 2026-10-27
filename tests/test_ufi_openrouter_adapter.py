import json
import os
import unittest
from unittest.mock import patch, MagicMock

from tools import ufi_provider_adapters as adapters


class OpenRouterRouteTests(unittest.TestCase):
    def test_status_never_returns_secret(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret"}, clear=False):
            result, _ = adapters.handle_extra_route("/api/openrouter/status", {})
        self.assertTrue(result["configured"])
        self.assertNotIn("test-secret", json.dumps(result))

    def test_chat_fails_closed_without_key(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(adapters.AdapterError):
                adapters.handle_extra_route("/api/openrouter/chat", {"messages": ['[{"role":"user","content":"hi"}]']})

    def test_chat_rejects_invalid_messages(self):
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret"}, clear=False):
            with self.assertRaises(adapters.AdapterError):
                adapters.handle_extra_route("/api/openrouter/chat", {"messages": ["not-json"]})

    def test_chat_returns_message_and_safe_usage(self):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({
            "model": "test/model",
            "choices": [{"message": {"role": "assistant", "content": "evidence needed"}}],
            "usage": {"prompt_tokens": 4, "completion_tokens": 3, "total_tokens": 7}
        }).encode()
        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-secret"}, clear=False):
            with patch("tools.ufi_provider_adapters.urllib.request.urlopen", return_value=response):
                result, cache = adapters.handle_extra_route(
                    "/api/openrouter/chat",
                    {"messages": [json.dumps([{"role": "user", "content": "test"}])]}
                )
        self.assertFalse(cache)
        self.assertEqual(result["message"]["content"], "evidence needed")
        self.assertEqual(result["usage"]["total_tokens"], 7)
        self.assertNotIn("test-secret", json.dumps(result))


if __name__ == "__main__":
    unittest.main()
