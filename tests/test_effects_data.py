import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('effects_data', Path(__file__).resolve().parents[1] / 'effects_data.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def track(mode=1, global_id=0xffffffff):
    return dict(times=[100, 1100], values=[(0,), (10,)], incoming=[(0,), (0,)],
                outgoing=[(0,), (0,)], interpolation=mode, global_id=global_id)


class TrackTests(unittest.TestCase):
    def test_linear(self):
        self.assertEqual(module.sample(track(), 600, (100, 1100), [], -1), 5)

    def test_visibility_is_stepped(self):
        self.assertEqual(module.sample(track(0), 1099, (100, 1100), [], -1), 0)
        self.assertEqual(module.sample(track(0), 1100, (100, 1100), [], -1), 10)

    def test_clip_isolation(self):
        self.assertEqual(module.sample(track(), 2500, (2000, 3000), [], -1), -1)

    def test_global_sequence_repeats(self):
        self.assertEqual(module.sample(track(global_id=0), 9000, (8000, 10000), [1200], -1, 1800), 5)

    def test_bad_global_sequence(self):
        self.assertEqual(module.sample(track(global_id=1), 600, (100, 1100), [0], -1), -1)

    def test_hermite_tangents(self):
        self.assertAlmostEqual(module.sample(track(2), 350, (100, 1100), [], -1), 1.5625)

    def test_bezier_tangents(self):
        self.assertAlmostEqual(module.sample(track(3), 350, (100, 1100), [], -1), 0.15625)

    def test_zero_constant(self):
        data = track()
        data.update(times=[0], values=[(0.25,)])
        self.assertEqual(module.sample(data, 9000, (8000, 10000), [], -1), 0.25)

    def test_vector(self):
        data = track()
        data['values'] = [(0, 1, 0), (1, 0, 1)]
        self.assertEqual(module.sample(data, 600, (100, 1100), [], -1), (0.5, 0.5, 0.5))


if __name__ == '__main__':
    unittest.main()
