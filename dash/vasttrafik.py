"""Departures from Västtrafik Planera Resa v4."""
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

import requests

from . import config

log = logging.getLogger(__name__)

TOKEN_URL = "https://ext-api.vasttrafik.se/token"
API = "https://ext-api.vasttrafik.se/pr/v4"

_token = {"value": None, "expires": 0.0}
_stop_gids = {config.VT_STOP_NAME.lower(): config.VT_STOP_GID} if config.VT_STOP_GID else {}


@dataclass
class LineDepartures:
    line: str
    direction: str
    mode: str
    times: list = field(default_factory=list)  # list of (datetime, cancelled)
    label: str = ""  # whose work route this is, in "jobb" mode
    via: str = ""  # e.g. "byte Linnéplatsen" when a connection is shown
    via_line: str = ""  # the connecting line, e.g. "25"
    connections: list = field(default_factory=list)  # per time: datetime of the connecting departure or None


def configured():
    return bool(config.VT_CLIENT_ID and config.VT_CLIENT_SECRET)


def _get_token():
    if _token["value"] and time.time() < _token["expires"] - 60:
        return _token["value"]
    r = requests.post(
        TOKEN_URL,
        data={"grant_type": "client_credentials"},
        auth=(config.VT_CLIENT_ID, config.VT_CLIENT_SECRET),
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    _token["value"] = data["access_token"]
    _token["expires"] = time.time() + float(data.get("expires_in", 3600))
    return _token["value"]


def _get(path, params):
    r = requests.get(
        f"{API}{path}",
        params=params,
        headers={"Authorization": f"Bearer {_get_token()}"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _resolve_stop(name=None):
    name = name or config.VT_STOP_NAME
    if name.lower() in _stop_gids:
        return _stop_gids[name.lower()]
    data = _get("/locations/by-text", {"q": name, "types": "stoparea", "limit": 5})
    results = data.get("results") or []
    if not results:
        raise RuntimeError(f"Hittade ingen hållplats som heter {name!r}")
    # Prefer an exact name match ("Järntorget, Göteborg")
    want = name.lower()
    best = next((x for x in results if x.get("name", "").lower().startswith(want)), results[0])
    _stop_gids[name.lower()] = best["gid"]
    log.info("Västtrafik stop %s -> %s", best.get("name"), best["gid"])
    return best["gid"]


def _parse_time(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(config.TZ)


def _departures(gid):
    params = {"timeSpanInMinutes": 120, "limit": 200}
    try:
        return _get(f"/stop-areas/{gid}/departures", params)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 400:
            params["limit"] = 60  # in case the API caps the limit lower
            return _get(f"/stop-areas/{gid}/departures", params)
        raise


def _work_match(name, direction):
    """Return the person's name if this line/direction is one of the work routes, else None."""
    for line, dir_part, person in config.VT_WORK:
        if line.lower() == name.lower() and (not dir_part or dir_part in direction.lower()):
            return person or ""
    return None


def fetch(mode="alla"):
    """Return a list of LineDepartures, grouped by line + direction."""
    if not configured():
        if config.DEMO_WHEN_UNCONFIGURED:
            return demo(mode)
        raise RuntimeError("Västtrafik-nyckel saknas")

    gid = _resolve_stop()
    data = _departures(gid)
    groups = {}
    for d in data.get("results") or []:
        sj = d.get("serviceJourney") or {}
        line = sj.get("line") or {}
        tmode = (line.get("transportMode") or "").lower()
        name = line.get("shortName") or line.get("designation") or line.get("name") or "?"
        direction = (sj.get("direction") or "").split(", Påstigning")[0]
        label = ""
        if mode == "jobb":
            label = _work_match(name, direction)
            if label is None:
                continue
        else:
            if config.VT_MODES and tmode not in config.VT_MODES:
                continue
            if any(h in direction.lower() for h in config.VT_HIDE_DIRECTIONS):
                continue
        t = d.get("estimatedOtherwisePlannedTime") or d.get("estimatedTime") or d.get("plannedTime")
        if not t:
            continue
        g = groups.setdefault((name, direction), LineDepartures(name, direction, tmode, label=label))
        g.times.append((_parse_time(t), bool(d.get("isCancelled"))))
    out = _finish(list(groups.values()), mode)
    if mode == "jobb":
        for g in out:
            conn = config.VT_CONNECTIONS.get(g.line.lower())
            if conn:
                try:
                    _add_connection(g, conn, _connection_times(conn))
                except Exception:
                    log.exception("connection lookup failed")
    return out


def _connection_times(conn):
    """Departure times of the connecting line at the transfer stop."""
    data = _departures(_resolve_stop(conn["stop"]))
    times = []
    for d in data.get("results") or []:
        sj = d.get("serviceJourney") or {}
        line = sj.get("line") or {}
        name = line.get("shortName") or line.get("designation") or line.get("name") or ""
        if name.lower() != conn["line"].lower() or d.get("isCancelled"):
            continue
        if conn["direction"] and conn["direction"] not in (sj.get("direction") or "").lower():
            continue
        t = d.get("estimatedOtherwisePlannedTime") or d.get("estimatedTime") or d.get("plannedTime")
        if t:
            times.append(_parse_time(t))
    return sorted(times)


def _add_connection(g, conn, conn_times):
    """For each departure in g, find the first connecting departure we can catch."""
    stop = conn["stop"].split(",")[0]
    g.via = f"byte {stop}"
    g.via_line = conn["line"]
    need = timedelta(minutes=conn["ride"] + config.VT_CHANGE_MINUTES)
    g.connections = [next((c for c in conn_times if c >= t + need), None) for t, _ in g.times]


def _finish(out, mode):
    n = config.VT_WORK_TIMES if mode == "jobb" else config.VT_TIMES_PER_ROW
    for g in out:
        g.times.sort(key=lambda x: x[0])
        g.times = g.times[:n]
    if mode == "jobb":
        order = [w[0].lower() for w in config.VT_WORK]
        out.sort(key=lambda g: (order.index(g.line.lower()) if g.line.lower() in order else 99, g.direction))
    else:
        out.sort(key=lambda g: g.times[0][0])  # soonest first
    return out


def demo(mode="alla"):
    now = datetime.now(config.TZ)
    rows = [
        ("1", "Östra sjukhuset", [3, 12, 21, 30]),
        ("1", "Tynnered", [6, 16, 26, 36]),
        ("X2", "Billdal", [5, 20, 35, 50]),
        ("X2", "Kungälv", [14, 29, 44, 59]),
        ("3", "Kålltorp", [1, 9, 19, 29]),
        ("3", "Marklandsgatan", [7, 15, 25, 35]),
        ("6", "Kortedala", [4, 14, 24, 34]),
        ("6", "Länsmansgården", [10, 20, 30, 40]),
        ("9", "Angered centrum", [2, 13, 23, 33]),
        ("9", "Kungssten", [8, 18, 28, 38]),
        ("11", "Bergsjön", [11, 17, 29, 41]),
    ]
    out = []
    for l, d, mins in rows:
        label = ""
        if mode == "jobb":
            label = _work_match(l, d)
            if label is None:
                continue
        out.append(LineDepartures(l, d, "bus" if l.startswith("X") else "tram",
                                  [(now + timedelta(minutes=m), m == 18) for m in mins], label=label))
    out = _finish(out, mode)
    if mode == "jobb":
        for g in out:
            conn = config.VT_CONNECTIONS.get(g.line.lower())
            if conn:
                _add_connection(g, conn, [now + timedelta(minutes=m) for m in range(2, 120, 7)])
    return out
