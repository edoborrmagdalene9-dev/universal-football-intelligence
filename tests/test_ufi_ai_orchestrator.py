import json
import os
import unittest
from unittest.mock import patch

from tools import ufi_ai_orchestrator as orchestrator
from tools import ufi_provider_adapters as adapters


class OrchestratorTests(unittest.TestCase):
    def test_no_sources_fails_closed(self):
        result=orchestrator.research_with_failover("Check lineup", [])
        self.assertEqual(result["status"],"NEEDS_DATA")
        self.assertEqual(result["claims"],[])

    def test_source_validation_requires_url_and_timestamp(self):
        valid=[{"url":"https://example.com/report","timestamp":"2026-10-27T12:00:00Z","text":"The lineup was announced."}]
        self.assertEqual(len(orchestrator._validate_sources(valid)),1)
        self.assertEqual(orchestrator._validate_sources([{"text":"unsupported"}]),[])

    def test_gemini_primary_success_does_not_call_fallback(self):
        sources=[{"url":"https://example.com/report","timestamp":"2026-10-27T12:00:00Z","text":"A sourced fact."}]
        expected={"status":"RESEARCH_LEADS","claims":[{"text":"A sourced fact.","source_url":sources[0]["url"],"source_timestamp":sources[0]["timestamp"]}],"verified":False}
        with patch("tools.ufi_gemini_research.extract_research_brief",return_value=expected):
            with patch.object(orchestrator,"_openrouter_extract",side_effect=AssertionError("fallback should not run")):
                result=orchestrator.research_with_failover("Extract sourced facts",sources)
        self.assertFalse(result["fallbackUsed"])
        self.assertEqual(result["provider"],"Gemini")

    def test_falls_back_to_openrouter_if_gemini_fails(self):
        sources=[{"url":"https://example.com/report","timestamp":"2026-10-27T12:00:00Z","text":"A sourced fact."}]
        expected={"status":"RESEARCH_LEADS","claims":[{"text":"A sourced fact.","source_url":sources[0]["url"],"source_timestamp":sources[0]["timestamp"]}],"verified":False}
        with patch("tools.ufi_gemini_research.extract_research_brief",side_effect=RuntimeError("provider down")):
            with patch.object(orchestrator,"_openrouter_extract",return_value=expected):
                result=orchestrator.research_with_failover("Extract sourced facts",sources)
        self.assertTrue(result["fallbackUsed"])
        self.assertEqual(result["provider"],"OpenRouter")

    def test_openrouter_claim_must_match_supplied_source(self):
        sources=[{"source_url":"https://example.com/report","source_timestamp":"2026-10-27T12:00:00Z","text":"Fact"}]
        payload={"choices":[{"message":{"content":json.dumps({"claims":[{"text":"unsupported","source_url":"https://evil.example","source_timestamp":"2026-10-27T12:00:00Z"}]})}}]}
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self): return json.dumps(payload).encode()
        with patch.dict(os.environ,{"OPENROUTER_API_KEY":"test-key"}):
            with patch("tools.ufi_ai_orchestrator.urllib.request.urlopen",return_value=Response()):
                result=orchestrator._openrouter_extract("question",sources)
        self.assertEqual(result["status"],"NEEDS_DATA")
        self.assertEqual(result["claims"],[])

    def test_status_does_not_disclose_keys(self):
        with patch.dict(os.environ,{"OPENROUTER_API_KEY":"secret-test","GEMINI_API_KEY":"gemini-test"}):
            result,_=adapters.handle_extra_route("/api/ai/status",{})
        self.assertNotIn("secret-test",json.dumps(result))
        self.assertNotIn("gemini-test",json.dumps(result))


if __name__=="__main__":
    unittest.main()
