import json
import unittest
from unittest.mock import patch
from urllib.error import URLError

from tools import ufi_gdelt_sources as gdelt
from tools import ufi_ai_orchestrator as orchestrator

class GdeltFallbackTests(unittest.TestCase):
    class Response:
        def __init__(self,body): self.body=body
        def __enter__(self): return self
        def __exit__(self,*args): return False
        def read(self,n=-1): return self.body[:n] if n>0 else self.body

    def test_gdelt_discovers_url_and_extracts_page_metadata(self):
        index={"articles":[{"url":"https://news.example/story","title":"Original title","domain":"news.example","seendate":"20261027T140000Z"}]}
        page=b'<html><head><title>Better title</title><meta name="description" content="A sourced match report."><meta property="article:published_time" content="2026-10-27T13:00:00Z"></head><body>story</body></html>'
        with patch("tools.ufi_gdelt_sources.urllib.request.urlopen",side_effect=[self.Response(json.dumps(index).encode()),self.Response(page)]):
            sources=gdelt.fetch_gdelt_sources("Home FC Away FC",limit=1)
        self.assertEqual(len(sources),1)
        self.assertEqual(sources[0]["url"],"https://news.example/story")
        self.assertIn("A sourced match report.",sources[0]["text"])
        self.assertEqual(sources[0]["published_at"],"2026-10-27T13:00:00Z")
        self.assertTrue(sources[0]["retrieved_at"])

    def test_firecrawl_error_uses_gdelt_fallback(self):
        source={"url":"https://news.example/story","timestamp":"2026-10-27T14:00:00Z","text":"Headline","source_name":"news.example"}
        with patch("tools.ufi_ai_orchestrator.urllib.request.urlopen",side_effect=URLError("firecrawl unavailable")):
            with patch("tools.ufi_gdelt_sources.fetch_gdelt_sources",return_value=[source]):
                result=orchestrator.fetch_firecrawl_sources("Home FC Away FC")
        self.assertEqual(result[0]["url"],source["url"])
        self.assertEqual(result[0]["text"],"Headline")

if __name__=="__main__":unittest.main()
