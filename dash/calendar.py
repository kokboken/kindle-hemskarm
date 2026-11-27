"""Today's events from a shared calendar's public iCal link (e.g. iCloud "Offentlig kalender")."""
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta

import requests

from . import config

_cache = {"events": None, "at": 0.0, "day": None}
CACHE_SECONDS = 300


@dataclass
class Event:
    title: str
    start: datetime = None  # None for all-day events
    end: datetime = None
    all_day: bool = False
    tomorrow: bool = False


def configured():
    return bool(config.ICAL_URL)


def _url():
    u = config.ICAL_URL
    return "https://" + u[len("webcal://"):] if u.startswith("webcal://") else u


def _to_local(v):
    if isinstance(v, datetime):
        return v.astimezone(config.TZ) if v.tzinfo else v.replace(tzinfo=config.TZ)
    return None


def _events_between(cal, start, end, tomorrow=False):
    import recurring_ical_events

    out = []
    for ev in recurring_ical_events.of(cal).between(start, end):
        title = str(ev.get("SUMMARY") or "(utan titel)").strip()
        s = ev.get("DTSTART").dt
        e = ev.get("DTEND").dt if ev.get("DTEND") else None
        if isinstance(s, datetime):
            out.append(Event(title, _to_local(s), _to_local(e), tomorrow=tomorrow))
        else:  # date = all-day
            out.append(Event(title, all_day=True, tomorrow=tomorrow))
    return out


def parse(ics_bytes, now=None):
    """Events left today; after CAL_TOMORROW_FROM o'clock also tomorrow's."""
    from icalendar import Calendar

    now = now or datetime.now(config.TZ)
    cal = Calendar.from_ical(ics_bytes)
    day0 = datetime.combine(now.date(), datetime.min.time(), config.TZ)
    today = [e for e in _events_between(cal, day0, day0 + timedelta(days=1))
             if e.all_day or (e.end or e.start) > now]
    events = sorted(today, key=lambda e: (not e.all_day, e.start or day0))
    if now.hour >= config.CAL_TOMORROW_FROM:
        tm = _events_between(cal, day0 + timedelta(days=1), day0 + timedelta(days=2), tomorrow=True)
        events += sorted(tm, key=lambda e: (not e.all_day, e.start or day0))
    return events


def fetch():
    if not configured():
        return []
    now = datetime.now(config.TZ)
    if _cache["events"] is None or time.time() - _cache["at"] > CACHE_SECONDS or _cache["day"] != now.date():
        r = requests.get(_url(), timeout=20, headers={"User-Agent": "home-dash-kindle/1.0"})
        r.raise_for_status()
        _cache["raw"] = r.content
        _cache["at"] = time.time()
        _cache["day"] = now.date()
        _cache["events"] = True
    return parse(_cache["raw"], now)


def week(now=None):
    """Monday–Sunday of this week: [(date, [Event, ...]), ...]."""
    from icalendar import Calendar

    now = now or datetime.now(config.TZ)
    if not configured():
        return []
    fetch()  # refreshes the cached calendar file
    cal = Calendar.from_ical(_cache["raw"])
    monday = now.date() - timedelta(days=now.weekday())
    days = []
    for i in range(7):
        day = monday + timedelta(days=i)
        start = datetime.combine(day, datetime.min.time(), config.TZ)
        evs = _events_between(cal, start, start + timedelta(days=1))
        evs.sort(key=lambda e: (not e.all_day, e.start or start))
        days.append((day, evs))
    return days
