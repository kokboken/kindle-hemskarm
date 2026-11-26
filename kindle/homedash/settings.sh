# Tjänsten på Render. Nyckeln (DASH_KEY) ligger i nyckel.sh, som inte finns i git.
DASH_BASE="https://home-dash-b3n6.onrender.com"
DASH_KEY=""
[ -f "$(dirname "$0")/nyckel.sh" ] && . "$(dirname "$0")/nyckel.sh"
DASH_KEY="$(printf %s "$DASH_KEY" | tr -d '\r\n ')"  # tål Windows-radbrytningar
DASH_URL="$DASH_BASE/dash.png?key=$DASH_KEY"
# Test mot datorn hemma i stället:
# DASH_URL="http://192.168.68.54:8000/dash.png"

# Sekunder mellan uppdateringar dagtid (06-24) och nattetid (00-06)
DAY_REFRESH=180
NIGHT_REFRESH=1800

# Hur ofta skärmen blinkar svart för att rensa spökbilder (var N:e uppdatering)
FULL_REFRESH_EVERY=10

# 1 = tryck var som helst på skärmen för att växla Jobbresor / Alla avgångar
TAP_TO_TOGGLE=1
# Lämna tomt för att hitta pekskärmen automatiskt, annars t.ex. /dev/input/event1
TOUCH_DEV=""
