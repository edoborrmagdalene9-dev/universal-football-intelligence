import json
import os
import unittest
from unittest.mock import patch
from tools import ufi_provider_adapters as adapters

class PostHogConfigTests(unittest.TestCase):
    def test_public_project_token_is_only_returned_by_analytics_config(self):
        with patch.dict(os.environ,{"POSTHOG_API_KEY":"phc-test-public","POSTHOG_HOST":"https://us.i.posthog.com"}):
            config,_=adapters.handle_extra_route("/api/analytics/config",{})
            status,_=adapters.handle_extra_route("/api/ai/status",{})
        self.assertTrue(config["configured"])
        self.assertEqual(config["projectToken"],"phc-test-public")
        self.assertFalse(config["autocapture"])
        self.assertFalse(config["sessionRecording"])
        self.assertNotIn("phc-test-public",json.dumps(status))

    def test_invalid_posthog_host_falls_back_to_safe_https_host(self):
        with patch.dict(os.environ,{"POSTHOG_API_KEY":"phc-test-public","POSTHOG_HOST":"http://unsafe.example"}):
            config,_=adapters.handle_extra_route("/api/analytics/config",{})
        self.assertEqual(config["apiHost"],"https://us.i.posthog.com")

if __name__=="__main__":unittest.main()
