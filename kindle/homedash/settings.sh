# Tjänsten på Render. Nyckeln (DASH_KEY) ligger i nyckel.sh, som inte finns i git.
DASH_BASE="https://home-dash-b3n6.onrender.com"
DASH_KEY=""
[ -f "$(dirname "$0")/nyckel.sh" ] && . "$(dirname "$0")/nyckel.sh"
DASH_KEY="$(printf %s "$DASH_KEY" | tr -d '\r\n ')"  # tål Windows-radbrytningar
DASH_URL="$DASH_BASE/dash.png?key=$DASH_KEY"
# Test mot datorn hemma i stället:
# DASH_URL="http://192.168.68.54:8000/dash.png"

# Natt = från NIGHT_START till NIGHT_END (hela timmar, 0-23)
NIGHT_START=23
NIGHT_END=6

# Sekunder mellan uppdateringar dag och natt. 60 = vid varje minutskifte (klockan stämmer)
DAY_REFRESH=60
NIGHT_REFRESH=60

# Skärmbelysning 0-24 (0 = släckt). Lämna tomt för att inte röra ljuset.
LIGHT_DAY=12
LIGHT_NIGHT=0
# Värme (gult ljus) 0-24 på Paperwhite 5. Lämna tomt för att inte ändra.
WARMTH=""

# Hur ofta skärmen blinkar svart för att rensa spökbilder (var N:e uppdatering)
FULL_REFRESH_EVERY=15

# 1 = tryck var som helst på skärmen för att växla Jobbresor / Alla avgångar
TAP_TO_TOGGLE=1
# Lämna tomt för att hitta pekskärmen automatiskt, annars t.ex. /dev/input/event1
TOUCH_DEV=""
