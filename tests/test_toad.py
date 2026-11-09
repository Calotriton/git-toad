import unittest
from datetime import date, timedelta

from gittoad.art import FRAMES, H, SKINS, W, Scene
from gittoad.encode import encode_gif, encode_png
from gittoad.life import STAGES, read
from gittoad.pond import SPECIES, assemble, season_for


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


class PondTest(unittest.TestCase):
    def test_species_have_twelve_months_and_valid_frames(self):
        for sp in SPECIES:
            self.assertEqual(len(sp.months), 12, sp.key)
            for frame in sp.frames:
                self.assertEqual(len({len(r) for r in frame}), 1, sp.key)
                self.assertTrue(set("".join(frame)) - {"."} <= set(sp.colors), sp.key)

    def test_only_species_in_season_appear(self):
        for month in range(1, 13):
            for day in range(1, 29, 3):
                d = date(2026, month, day)
                for c in assemble(d, "someone", False, 40, 86, 128):
                    self.assertGreater(c.species.months[month - 1], 0, (c.species.key, month))

    def test_no_odonates_fly_at_night(self):
        for month in range(1, 13):
            critters = assemble(date(2026, month, 1), "someone", True, 40, 86, 128)
            self.assertFalse([c for c in critters if c.species.zone == "air"])

    def test_same_day_same_pond(self):
        a = assemble(date(2026, 5, 3), "x", False, 40, 86, 128)
        b = assemble(date(2026, 5, 3), "x", False, 40, 86, 128)
        self.assertEqual([(c.species.key, c.x0) for c in a], [(c.species.key, c.x0) for c in b])

    def test_lilies_only_in_growing_season(self):
        self.assertFalse(season_for(date(2026, 1, 10)).has("lily_pads"))
        self.assertTrue(season_for(date(2026, 7, 10)).has("lily_flowers"))

    def test_every_month_fits_a_gif_palette(self):
        toad = read(snapshot([12000]))
        for month in range(1, 13):
            for behavior in ("leap", "sleep"):
                toad.behavior = behavior
                toad.day = date(2026, month, 15)
                frames = Scene(toad, skin="violet").frames()
                self.assertLessEqual(len({c for f in frames for c in f}), 256)


if __name__ == "__main__":
    unittest.main()
