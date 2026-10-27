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

    def test_monitoring_delivery_failure_does_not_raise(self):
        with patch.dict(os.environ,{"DD_API_KEY":"test","DD_SITE":"datadoghq.com","POSTHOG_API_KEY":""},clear=False):
            with patch("tools.ufi_observability._post",side_effect=RuntimeError("offline")):
                with redirect_stdout(io.StringIO()):
                    emit_request("/api/health","error",5,"TimeoutError")

if __name__=="__main__":unittest.main()
