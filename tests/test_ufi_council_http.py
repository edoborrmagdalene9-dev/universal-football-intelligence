import json
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from http.client import HTTPConnection

from tools import ufi_live_data_proxy as proxy

class CouncilHttpIntegrationTests(unittest.TestCase):
    def test_post_council_route_dispatches_json_prompt(self):
        server=ThreadingHTTPServer(("127.0.0.1",0),proxy.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with patch.object(proxy,"get_payload",return_value=({"ok":True,"text":"{\"overall_status\":\"HOLD\"}"},False)) as dispatch:
                conn=HTTPConnection("127.0.0.1",server.server_port,timeout=3)
                body=json.dumps({"prompt":"Return JSON only."})
                conn.request("POST","/api/ai/council",body=body,headers={"Content-Type":"application/json"})
                response=conn.getresponse()
                payload=json.loads(response.read().decode())
                conn.close()
            self.assertEqual(response.status,200)
            self.assertTrue(payload["ok"])
            self.assertEqual(dispatch.call_args.args[0],"/api/ai/council")
            self.assertEqual(dispatch.call_args.args[1]["prompt"],["Return JSON only."])
        finally:
            server.shutdown()
            server.server_close()

    def test_post_rejects_other_routes(self):
        server=ThreadingHTTPServer(("127.0.0.1",0),proxy.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            conn=HTTPConnection("127.0.0.1",server.server_port,timeout=3)
            conn.request("POST","/api/fixtures",body="{}",headers={"Content-Type":"application/json"})
            response=conn.getresponse()
            payload=json.loads(response.read().decode())
            conn.close()
            self.assertEqual(response.status,405)
            self.assertIn("only supported",payload["error"])
        finally:
            server.shutdown()
            server.server_close()

if __name__=="__main__":unittest.main()
