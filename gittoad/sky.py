"""Day and night at a real place: sun position and moon phase, no dependencies."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone

# The sun's center 6 degrees below the horizon: the end of civil dusk, when it is properly dark.
CIVIL_ZENITH = 96.0
SYNODIC_MONTH = 29.530588853
NEW_MOON_EPOCH = datetime(2000, 1, 6, 18, 14, tzinfo=timezone.utc)


@dataclass(frozen=True)
class Sky:
    night: bool
    moon: float  # phase: 0 new, 0.25 first quarter, 0.5 full, 0.75 last quarter
    first_light: datetime | None = None
    last_light: datetime | None = None


def light_window(day: date, lat: float, lon: float, zenith: float = CIVIL_ZENITH):
    """UTC times of first light and last light (NOAA solar equations). None during polar day/night."""
    g = 2 * math.pi / 365 * (day.timetuple().tm_yday - 1)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g)
                       - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
            + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    phi = math.radians(lat)
    cos_ha = math.cos(math.radians(zenith)) / (math.cos(phi) * math.cos(decl)) - math.tan(phi) * math.tan(decl)
    if not -1 <= cos_ha <= 1:
        return None
    ha = math.degrees(math.acos(cos_ha))
    midnight = datetime.combine(day, time(0), tzinfo=timezone.utc)
    rise = midnight + timedelta(minutes=720 - 4 * (lon + ha) - eqtime)
    sets = midnight + timedelta(minutes=720 - 4 * (lon - ha) - eqtime)
    return rise, sets


def moon_phase(day: date) -> float:
    noon = datetime.combine(day, time(12), tzinfo=timezone.utc)
    return ((noon - NEW_MOON_EPOCH).total_seconds() / 86400 / SYNODIC_MONTH) % 1


def sky_at(now: datetime, lat: float, lon: float) -> Sky:
    now = now.astimezone(timezone.utc)
    window = light_window(now.date(), lat, lon)
    if window is None:  # polar: dark if the sun never climbs that high in winter
        night = abs(lat) > 60 and (now.month in (11, 12, 1)) == (lat > 0)
        return Sky(night, moon_phase(now.date()))
    first, last = window
    return Sky(not first <= now < last, moon_phase(now.date()), first, last)
