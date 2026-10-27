import json
import os
import unittest
from unittest.mock import patch
from urllib.error import URLError

from tools import ufi_ai_orchestrator as orchestrator
from tools import ufi_provider_adapters as adapters

class CouncilFailoverTests(unittest.TestCase):
    class Response:
        def __init__(self,payload): self.payload=payload
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def read(self): return json.dumps(self.payload).encode()

    def test_council_uses_gemini_first(self):
        payload={"candidates":[{"content":{"parts":[{"text":'{"overall_status":"HOLD","summary":"Need evidence"}'}]}}]}
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-key","GEMINI_MODEL":"gemini-2.5-flash","OPENROUTER_API_KEY":"fallback-key"}):
            with patch("tools.ufi_ai_orchestrator.urllib.request.urlopen",return_value=self.Response(payload)) as request:
                result=orchestrator.review_with_failover("Return JSON")
        self.assertEqual(result["provider"],"Gemini")
        self.assertFalse(result["fallbackUsed"])
        self.assertEqual(request.call_count,1)
        self.assertNotIn("test-key",json.dumps(result))

    def test_council_falls_back_to_openrouter(self):
        payload={"choices":[{"message":{"content":'{"overall_status":"HOLD","summary":"Need evidence"}'}}],"model":"test-model"}
        with patch.dict(os.environ,{"GEMINI_API_KEY":"test-key","OPENROUTER_API_KEY":"fallback-key","OPENROUTER_MODEL":"test/model"}):
            with patch("tools.ufi_ai_orchestrator.urllib.request.urlopen",side_effect=[URLError("offline"),self.Response(payload)]):
                result=orchestrator.review_with_failover("Return JSON")
        self.assertEqual(result["provider"],"OpenRouter")
        self.assertTrue(result["fallbackUsed"])
        self.assertFalse(result["verified"])

    def test_council_route_requires_prompt(self):
        with self.assertRaises(adapters.AdapterError):
            adapters.handle_extra_route("/api/ai/council",{})

    def test_firecrawl_failure_uses_gdelt_fallback(self):
        source={"url":"https://example.com/report","timestamp":"2026-10-27T15:00:00Z","retrieved_at":"2026-10-27T15:00:00Z","source_name":"Example","text":"A sourced headline."}
        with patch("tools.ufi_ai_orchestrator.urllib.request.urlopen",side_effect=URLError("firecrawl unavailable")):
            with patch("tools.ufi_gdelt_sources.fetch_gdelt_sources",return_value=[source]):
                result=orchestrator.fetch_firecrawl_sources("Home FC Away FC news")
        self.assertEqual(len(result),1)
        self.assertEqual(result[0]["url"],"https://example.com/report")
        self.assertEqual(result[0]["text"],"A sourced headline.")
if __name__=="__main__":unittest.main()
