import io
import json
import os
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

from tools.ufi_observability import emit_request

class ObservabilityTests(unittest.TestCase):
    def test_telemetry_logs_route_without_query_or_secret(self):
        buffer=io.StringIO()
        with patch.dict(os.environ,{"DD_API_KEY":"","POSTHOG_API_KEY":""},clear=False):
            with redirect_stdout(buffer):
                emit_request("/api/fixtures?token=secret-value","ok",3.5)
        output=buffer.getvalue()
        self.assertIn("/api/fixtures",output)
        self.assertNotIn("secret-value",output)
        record=json.loads(output)
        self.assertEqual(record["telemetry"]["outcome"],"ok")

    def test_posthog_capture_does_not_break_route(self):
        class Response:
            def __enter__(self): return self
            def __exit__(self,*args): return False
            def read(self,n=-1): return b"ok"
        with patch.dict(os.environ,{"DD_API_KEY":"","POSTHOG_API_KEY":"phc-public-test","POSTHOG_HOST":"https://us.i.posthog.com"},clear=False):
            with patch("tools.ufi_observability.urllib.request.urlopen",return_value=Response()) as send:
                with redirect_stdout(io.StringIO()):
                    emit_request("/api/ai/status","ok",2)
        self.assertTrue(send.called)
        self.assertIn("/capture/",send.call_args.args[0].full_url)

    def test_monitoring_delivery_failure_does_not_raise(self):
        with patch.dict(os.environ,{"DD_API_KEY":"test","DD_SITE":"datadoghq.com","POSTHOG_API_KEY":""},clear=False):
            with patch("tools.ufi_observability.urllib.request.urlopen",side_effect=RuntimeError("offline")):
                with redirect_stdout(io.StringIO()):
                    emit_request("/api/health","error",5,"TimeoutError")

if __name__=="__main__":unittest.main()
