"""All settings come from environment variables (see .env.example)."""
import os
from zoneinfo import ZoneInfo


def _load_dotenv():
    """Read a local .env file (for running on your own computer). Real env vars win."""
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()


def _env(name, default=""):
    return os.environ.get(name, default).strip()


def _parse_work(spec):
    """'X2:Victor, 1@Östra:Lovisa' -> [(line, direction_contains, name), ...]"""
    out = []
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        part, _, name = part.partition(":")
        line, _, direction = part.partition("@")
        out.append((line.strip(), direction.strip().lower(), name.strip()))
    return out


TZ = ZoneInfo(_env("TZ_NAME", "Europe/Stockholm"))

# Screen: Kindle Paperwhite 5 (11th gen) is 1236 x 1648 px, portrait.
WIDTH = int(_env("SCREEN_WIDTH", "1236"))
HEIGHT = int(_env("SCREEN_HEIGHT", "1648"))

# Secret that must be passed as ?key=... to see the dashboard. Empty = open.
DASH_KEY = _env("DASH_KEY")

# Västtrafik Planera Resa v4 (developer.vasttrafik.se)
VT_CLIENT_ID = _env("VT_CLIENT_ID")
VT_CLIENT_SECRET = _env("VT_CLIENT_SECRET")
VT_STOP_NAME = _env("VT_STOP_NAME", "Järntorget")
VT_STOP_GID = _env("VT_STOP_GID")  # optional, looked up from VT_STOP_NAME if empty

# Two display modes, toggled from the phone page or by tapping the Kindle:
#   "jobb" – only your work routes, with your names on them
#   "alla" – every departure, soonest first
# VT_WORK format: LINE[@direction contains][:Name], comma separated.
#   "X2:Victor,1:Lovisa"  or  "X2@Centrum:Victor,1@Östra:Lovisa"
VT_WORK = _parse_work(_env("VT_WORK", "X2@Billdal:Victor,1@Östra:Lovisa"))
DEFAULT_MODE = _env("DEFAULT_MODE", "jobb")
VT_WORK_TIMES = int(_env("VT_WORK_TIMES", "4"))

# Connections shown under a work route: LINE=TRANSFER STOP:NEXT LINE[@direction contains]:RIDE MINUTES
#   "X2=Linnéplatsen:25:4" -> for each X2, show the first 25 leaving Linnéplatsen
#   after the X2 gets there (ride minutes + VT_CHANGE_MINUTES to walk over).
def _parse_connections(spec):
    out = {}
    for part in spec.split(","):
        if "=" not in part:
            continue
        line, rest = part.split("=", 1)
        bits = [b.strip() for b in rest.split(":")]
        if len(bits) < 2:
            continue
        nxt, _, direction = bits[1].partition("@")
        ride = int(bits[2]) if len(bits) > 2 and bits[2].isdigit() else 4
        out[line.strip().lower()] = {"stop": bits[0], "line": nxt.strip(),
                                     "direction": direction.strip().lower(), "ride": ride}
    return out


VT_CONNECTIONS = _parse_connections(_env("VT_CONNECTIONS", "X2=Linnéplatsen:25@Balltorp:4"))
VT_CHANGE_MINUTES = int(_env("VT_CHANGE_MINUTES", "1"))

# "Snabbast till": destinations shown in the work view (journey planner, arrives first)
FASTEST_TO = [x.strip() for x in _env("FASTEST_TO", "Brunnsparken,Drottningtorget").split(",") if x.strip()]
FASTEST_COUNT = int(_env("FASTEST_COUNT", "2"))

# Shared calendar: public iCal link (iCloud: Kalendrar > (i) > Offentlig kalender). Empty = no calendar.
ICAL_URL = _env("ICAL_URL")
CAL_MAX_EVENTS = int(_env("CAL_MAX_EVENTS", "3"))
CAL_TOMORROW_FROM = int(_env("CAL_TOMORROW_FROM", "18"))  # from this hour, also show tomorrow

# "alla" mode: transport modes to include (tram,bus,ferry,train). Empty = all.
VT_MODES = [m.strip().lower() for m in _env("VT_MODES").split(",") if m.strip()]
# "alla" mode: only these lines (both directions). Empty = every line.
VT_LINES = [x.strip().lower() for x in _env("VT_LINES", "1,3,6,9,11,X2").split(",") if x.strip()]
VT_HIDE_DIRECTIONS = [x.strip().lower() for x in _env("VT_HIDE_DIRECTIONS").split(",") if x.strip()]
VT_TIMES_PER_ROW = int(_env("VT_TIMES_PER_ROW", "3"))

# Weather from MET Norway / Yr (no key needed). Default: Järntorget, Göteborg.
LAT = float(_env("LAT", "57.6997"))
LON = float(_env("LON", "11.9527"))
WEATHER_PLACE = _env("WEATHER_PLACE", "Göteborg")
# Rain warning for the commute: hours "7-9" (from 07:00 to 09:00), weekdays only, from this many mm/h.
COMMUTE_HOURS = _env("COMMUTE_HOURS", "7-9")
COMMUTE_WEEKDAYS_ONLY = _env("COMMUTE_WEEKDAYS_ONLY", "1") == "1"
RAIN_MM = float(_env("RAIN_MM", "0.2"))

# Night view (big clock + tomorrow's weather) between these hours. Same hours as the Kindle's light settings.
NIGHT_START = int(_env("NIGHT_START", "23"))
NIGHT_END = int(_env("NIGHT_END", "6"))


def is_night(hour):
    if NIGHT_START == NIGHT_END:
        return False
    if NIGHT_START > NIGHT_END:
        return hour >= NIGHT_START or hour < NIGHT_END
    return NIGHT_START <= hour < NIGHT_END

# Google Keep (unofficial API via gkeepapi)
KEEP_EMAIL = _env("KEEP_EMAIL")
KEEP_MASTER_TOKEN = _env("KEEP_MASTER_TOKEN")
KEEP_NOTE_TITLE = _env("KEEP_NOTE_TITLE", "Att köpa")

# Use sample data for sources that are not configured.
DEMO_WHEN_UNCONFIGURED = _env("DEMO_WHEN_UNCONFIGURED", "1") == "1"
