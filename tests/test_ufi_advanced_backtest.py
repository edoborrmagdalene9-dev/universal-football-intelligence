import importlib.util, math, tempfile, unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "tools" / "ufi_advanced_backtest.py"
spec = importlib.util.spec_from_file_location("ufi_advanced_backtest", SCRIPT)
model = importlib.util.module_from_spec(spec); spec.loader.exec_module(model)

class AdvancedModelTests(unittest.TestCase):
    def test_elo_probabilities_sum_to_one(self):
        p = model.probs_from_ratings(1500, 1500)
        self.assertAlmostEqual(sum(p), 1.0, places=10)
        self.assertTrue(all(0 <= x <= 1 for x in p))
    def test_poisson_probabilities_sum_to_one(self):
        self.assertAlmostEqual(sum(model.poisson_probs(1.7)), 1.0, places=10)
    def test_poisson_1x2_sum_to_one(self):
        self.assertAlmostEqual(sum(model.poisson_1x2(1.4, 1.1)), 1.0, places=10)
    def test_scoring_finite(self):
        b, ll = model.score((0.5,0.25,0.25), "H")
        self.assertTrue(math.isfinite(b) and math.isfinite(ll))
        self.assertGreaterEqual(b, 0); self.assertGreaterEqual(ll, 0)

if __name__ == "__main__": unittest.main()
