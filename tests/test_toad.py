import unittest
from datetime import date, timedelta

from gittoad.art import FRAMES, H, SKINS, W, Scene
from gittoad.encode import encode_gif, encode_png
from gittoad.life import STAGES, read


def snapshot(counts):
    start = date(2025, 1, 1)
    days = [((start + timedelta(days=i)).isoformat(), c) for i, c in enumerate(counts)]
    return {"login": "test", "days": days, "languages": [{"name": "Python", "color": "#3572A5", "repos": 2}]}


class LifeTest(unittest.TestCase):
    def test_stages_follow_total(self):
        for stage, (threshold, _) in enumerate(STAGES):
            self.assertEqual(read(snapshot([threshold])).stage, stage)

    def test_long_quiet_spell_sleeps(self):
        self.assertEqual(read(snapshot([5] * 20 + [0] * 14)).behavior, "sleep")

    def test_active_yesterday_hunts(self):
        self.assertEqual(read(snapshot([2] * 300 + [0, 2])).behavior, "hunt")

    def test_quiet_yesterday_idles(self):
        self.assertEqual(read(snapshot([2] * 300 + [0])).behavior, "idle")

    def test_crossing_a_milestone_leaps(self):
        self.assertEqual(read(snapshot([0] * 30 + [95, 0, 10])).behavior, "leap")

    def test_streaks_earn_spots(self):
        self.assertEqual(read(snapshot([1] * 14 + [0])).spots, 2)
        self.assertEqual(read(snapshot([1] * 100)).spots, 3)


class RenderTest(unittest.TestCase):
    def test_every_stage_skin_and_behavior_renders(self):
        for stage in range(len(STAGES)):
            for behavior in ("idle", "hunt", "leap", "sleep"):
                toad = read(snapshot([STAGES[stage][0]]))
                toad.behavior = behavior
                for skin in SKINS:
                    frame = Scene(toad, skin=skin).frame(FRAMES // 2)
                    self.assertEqual(len(frame), W * H)

    def test_encoders_produce_files(self):
        frames = Scene(read(snapshot([3000]))).frames()
        self.assertTrue(encode_gif(frames, W, H, 1, 10).startswith(b"GIF89a"))
        self.assertTrue(encode_png(frames[0], W, H, 1).startswith(b"\x89PNG"))


if __name__ == "__main__":
    unittest.main()
