import csv, importlib.util, tempfile, unittest
from pathlib import Path
SCRIPT=Path(__file__).resolve().parents[1]/"tools"/"ufi_integrated_pipeline.py"
spec=importlib.util.spec_from_file_location("ufi_integrated_pipeline",SCRIPT)
pipeline=importlib.util.module_from_spec(spec); spec.loader.exec_module(pipeline)
class IntegratedPipelineTests(unittest.TestCase):
 def test_empty_registry_is_not_misrepresented_as_player_data(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/"players.csv"
   path.write_text("player_name,source_name,source_url,preferred_foot,weak_foot_evidence,role,observed_style_tags,efootball_style_tags,confidence_0_to_1,record_type\n",encoding="utf-8")
   result=pipeline.audit_player_registry(path)
   self.assertEqual(result["records"],0); self.assertFalse(result["used_as_prediction_feature"]); self.assertTrue(result["warnings"])
 def test_sourced_player_record_is_counted(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/"players.csv"
   fields=["player_name","source_name","source_url","preferred_foot","weak_foot_evidence","role","observed_style_tags","efootball_style_tags","confidence_0_to_1","record_type"]
   with path.open("w",newline="",encoding="utf-8") as f:
    w=csv.DictWriter(f,fieldnames=fields); w.writeheader()
    w.writerow({"player_name":"Example Player","source_name":"Club profile","source_url":"https://example.com/player","preferred_foot":"left","weak_foot_evidence":"Observed on both feet across full matches","role":"winger","observed_style_tags":"wide carrier","efootball_style_tags":"none","confidence_0_to_1":"0.8","record_type":"source_fact"})
   result=pipeline.audit_player_registry(path)
   self.assertEqual(result["records"],1); self.assertEqual(result["footedness_known_records"],1); self.assertEqual(result["weak_foot_evidence_records"],1); self.assertEqual(result["style_tagged_records"],1); self.assertFalse(result["errors"])
 def test_invalid_foot_is_flagged(self):
  with tempfile.TemporaryDirectory() as tmp:
   path=Path(tmp)/"players.csv"
   path.write_text("player_name,source_name,source_url,preferred_foot,weak_foot_evidence,role,observed_style_tags,efootball_style_tags,confidence_0_to_1,record_type\nExample,source,https://example.com,maybe,,,,,0.5,source_fact\n",encoding="utf-8")
   result=pipeline.audit_player_registry(path)
   self.assertEqual(result["status"],"needs_correction"); self.assertTrue(result["errors"])
if __name__=="__main__": unittest.main()
