"""Weather forecast from MET Norway (the data behind Yr). No API key needed."""
from dataclasses import dataclass, field
from datetime import datetime

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

    tomorrow_date = (now.date().toordinal() + 1)
    tm = [s for s in series if s[0].date().toordinal() == tomorrow_date]
    tomorrow = None
    if tm:
        temps = [s[1]["air_temperature"] for s in tm]
        midday = min(tm, key=lambda s: abs(s[0].hour - 12))
        sym = ((midday[2].get("summary") or {}).get("symbol_code", ""))
        tomorrow = (min(temps), max(temps), sym)

    return Weather(
        temp=det0["air_temperature"],
        symbol=(nxt0.get("summary") or {}).get("symbol_code", ""),
        wind=det0.get("wind_speed", 0.0),
        precip_next_hour=(nxt0.get("details") or {}).get("precipitation_amount", 0.0),
        today_min=min(today) if today else det0["air_temperature"],
        today_max=max(today) if today else det0["air_temperature"],
        hours=hours,
        tomorrow=tomorrow,
    )
