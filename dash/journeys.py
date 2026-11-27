"""'Snabbast till …' – the trips from our stop that arrive first, via Västtrafik's journey planner."""
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from . import config, vasttrafik

log = logging.getLogger(__name__)

_cache = {}  # destination -> (trips, fetched_at)
CACHE_SECONDS = 50


@dataclass
class Trip:
    lines: list = field(default_factory=list)  # e.g. ["6"] or ["1", "25"] when changing
    depart: datetime = None
    arrive: datetime = None


def _t(leg, key):
    v = leg.get(f"estimatedOtherwisePlanned{key}Time") or leg.get(f"planned{key}Time")
    return datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(config.TZ) if v else None


def _trips_to(dest):
    origin = vasttrafik._resolve_stop()
    target = vasttrafik._resolve_stop(dest)
    data = vasttrafik._get("/journeys", {"originGid": origin, "destinationGid": target, "limit": 10})
    now = datetime.now(config.TZ)
    trips = []
    for r in data.get("results") or []:
        legs = r.get("tripLegs") or []
        # Only trips that start at our stop with a vehicle: no walk-only, no walking to another stop.
        if not legs or r.get("departureAccessLink") or r.get("arrivalAccessLink"):
            continue
        if any(leg.get("isCancelled") for leg in legs):
            continue
        trip = Trip(
            lines=[(leg.get("serviceJourney") or {}).get("line", {}).get("shortName") or "?" for leg in legs],
            depart=_t(legs[0], "Departure"),
            arrive=_t(legs[-1], "Arrival"),
        )
        if trip.depart and trip.arrive and trip.depart >= now - timedelta(seconds=30):
            trips.append(trip)
    trips.sort(key=lambda t: (t.arrive, t.depart))
    return trips[: config.FASTEST_COUNT]


def demo():
    now = datetime.now(config.TZ)
    return [
        ("Brunnsparken", [Trip(["6"], now + timedelta(minutes=2), now + timedelta(minutes=9)),
                          Trip(["11"], now + timedelta(minutes=5), now + timedelta(minutes=11))]),
        ("Drottningtorget", [Trip(["1"], now + timedelta(minutes=4), now + timedelta(minutes=11)),
                             Trip(["3"], now + timedelta(minutes=7), now + timedelta(minutes=14))]),
    ]


def fetch():
    """[(destination name, [Trip, ...]), ...] for every destination in FASTEST_TO."""
    if not config.FASTEST_TO:
        return []
    if not vasttrafik.configured():
        return demo() if config.DEMO_WHEN_UNCONFIGURED else []
    out = []
    for dest in config.FASTEST_TO:
        hit = _cache.get(dest)
        if not hit or time.time() - hit[1] > CACHE_SECONDS:
            hit = (_trips_to(dest), time.time())
            _cache[dest] = hit
        out.append((dest, hit[0]))
    return out
