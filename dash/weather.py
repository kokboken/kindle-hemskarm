"""Weather forecast from MET Norway (the data behind Yr). No API key needed."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import requests

from . import config

URL = "https://api.met.no/weatherapi/locationforecast/2.0/compact"
# MET Norway requires an identifying User-Agent.
HEADERS = {"User-Agent": "home-dash-kindle/1.0 (personal e-ink dashboard)"}

_cache = {"data": None, "expires": None, "last_modified": None}

SYMBOLS = {
    "clearsky": "Klart",
    "fair": "Mest klart",
    "partlycloudy": "Halvklart",
    "cloudy": "Mulet",
    "fog": "Dimma",
    "rain": "Regn",
    "lightrain": "Lätt regn",
    "heavyrain": "Kraftigt regn",
    "rainshowers": "Regnskurar",
    "lightrainshowers": "Lätta regnskurar",
    "heavyrainshowers": "Kraftiga regnskurar",
    "sleet": "Snöblandat regn",
    "lightsleet": "Lätt snöblandat regn",
    "heavysleet": "Kraftigt snöblandat regn",
    "sleetshowers": "Byar av snöblandat regn",
    "lightsleetshowers": "Lätta byar av snöblandat regn",
    "heavysleetshowers": "Kraftiga byar av snöblandat regn",
    "snow": "Snö",
    "lightsnow": "Lätt snöfall",
    "heavysnow": "Kraftigt snöfall",
    "snowshowers": "Snöbyar",
    "lightsnowshowers": "Lätta snöbyar",
    "heavysnowshowers": "Kraftiga snöbyar",
}


def describe(symbol_code):
    base = (symbol_code or "").split("_")[0]
    if "thunder" in base:
        return SYMBOLS.get(base.replace("andthunder", ""), "Nederbörd") + " och åska"
    return SYMBOLS.get(base, base or "–")


@dataclass
class Hour:
    time: datetime
    temp: float
    symbol: str
    precip: float


@dataclass
class Weather:
    temp: float
    symbol: str
    wind: float
    precip_next_hour: float
    today_min: float
    today_max: float
    hours: list = field(default_factory=list)  # upcoming, every 3 h
    tomorrow: tuple = None  # (min, max, symbol)
    today: tuple = None  # (min, max, symbol) for the rest of today – used by the night view after midnight
    commute_warning: str = ""  # e.g. "Ta paraply imorgon: regn 07–09 (1,4 mm)"


def commute_warning(hourly, now):
    """Warn if the next commute window (today if not over, else the next weekday) gets rain or snow.

    hourly: [(start datetime, precipitation mm, symbol_code)] for 1-hour steps."""
    try:
        a, b = (int(x) for x in config.COMMUTE_HOURS.split("-"))
    except ValueError:
        return ""
    day = now.date()
    for _ in range(2):  # today or the next day only
        weekday_ok = not config.COMMUTE_WEEKDAYS_ONLY or day.weekday() < 5
        end = datetime.combine(day, datetime.min.time(), config.TZ).replace(hour=b)
        if weekday_ok and end > now:
            break
        day = day.fromordinal(day.toordinal() + 1)
    else:
        return ""
    if config.COMMUTE_WEEKDAYS_ONLY and day.weekday() >= 5:
        return ""
    window = [(t, mm, sym) for t, mm, sym in hourly
              if t.date() == day and a <= t.hour < b and t + timedelta(hours=1) > now]
    wet = [(t, mm, sym) for t, mm, sym in window if mm >= config.RAIN_MM]
    if not wet:
        return ""
    total = sum(mm for _, mm, _ in wet)
    snow = any("snow" in sym for _, _, sym in wet)
    sleet = any("sleet" in sym for _, _, sym in wet)
    kind = "snö" if snow and not sleet else "snöblandat regn" if sleet else "regn"
    when = "idag" if day == now.date() else "imorgon"
    first, last = wet[0][0], wet[-1][0] + timedelta(hours=1)
    gear = "Klä dig varmt" if kind == "snö" else "Ta paraply"
    return f"{gear} {when}: {kind} {first:%H}–{last:%H} ({total:.1f} mm)".replace(".", ",")


def _fetch_raw():
    now = datetime.now(config.TZ)
    if _cache["data"] and _cache["expires"] and now < _cache["expires"]:
        return _cache["data"]
    headers = dict(HEADERS)
    if _cache["last_modified"]:
        headers["If-Modified-Since"] = _cache["last_modified"]
    r = requests.get(URL, params={"lat": round(config.LAT, 4), "lon": round(config.LON, 4)},
                     headers=headers, timeout=15)
    if r.status_code == 304 and _cache["data"]:
        data = _cache["data"]
    else:
        r.raise_for_status()
        data = r.json()
        _cache["data"] = data
        _cache["last_modified"] = r.headers.get("Last-Modified")
    exp = r.headers.get("Expires")
    if exp:
        from email.utils import parsedate_to_datetime
        _cache["expires"] = parsedate_to_datetime(exp).astimezone(config.TZ)
    return data


def fetch():
    data = _fetch_raw()
    now = datetime.now(config.TZ)
    series = []
    for e in data["properties"]["timeseries"]:
        t = datetime.fromisoformat(e["time"].replace("Z", "+00:00")).astimezone(config.TZ)
        d = e["data"]
        nxt = d.get("next_1_hours") or d.get("next_6_hours") or {}
        series.append((t, d["instant"]["details"], nxt))

    # Current = latest entry not in the future (or the first one).
    current = series[0]
    for s in series:
        if s[0] <= now:
            current = s
    t0, det0, nxt0 = current

    today = [s[1]["air_temperature"] for s in series if s[0].date() == now.date() and s[0] >= t0]
    hours = []
    for t, det, nxt in series:
        if t > now and t.hour % 3 == 0 and len(hours) < 6:
            hours.append(Hour(t, det["air_temperature"], (nxt.get("summary") or {}).get("symbol_code", ""),
                              (nxt.get("details") or {}).get("precipitation_amount", 0.0)))

    def day_summary(ordinal, not_before=None):
        day = [s for s in series if s[0].date().toordinal() == ordinal and (not_before is None or s[0] >= not_before)]
        if not day:
            return None
        temps = [s[1]["air_temperature"] for s in day]
        midday = min(day, key=lambda s: abs(s[0].hour - 12))
        return (min(temps), max(temps), (midday[2].get("summary") or {}).get("symbol_code", ""))

    tomorrow = day_summary(now.date().toordinal() + 1)
    today_sum = day_summary(now.date().toordinal(), not_before=t0)

    # Hour-by-hour precipitation (only entries that have a 1-hour forecast)
    hourly = []
    for e in data["properties"]["timeseries"]:
        one = e["data"].get("next_1_hours")
        if one:
            t = datetime.fromisoformat(e["time"].replace("Z", "+00:00")).astimezone(config.TZ)
            hourly.append((t, (one.get("details") or {}).get("precipitation_amount", 0.0),
                           (one.get("summary") or {}).get("symbol_code", "")))

    return Weather(
        commute_warning=commute_warning(hourly, now),
        temp=det0["air_temperature"],
        symbol=(nxt0.get("summary") or {}).get("symbol_code", ""),
        wind=det0.get("wind_speed", 0.0),
        precip_next_hour=(nxt0.get("details") or {}).get("precipitation_amount", 0.0),
        today_min=min(today) if today else det0["air_temperature"],
        today_max=max(today) if today else det0["air_temperature"],
        hours=hours,
        tomorrow=tomorrow,
        today=today_sum,
    )
