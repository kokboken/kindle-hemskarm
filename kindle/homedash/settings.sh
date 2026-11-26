# Under test hemma: datorns adress i ert wifi. Byt till molnadressen (med ?key=...) senare.
# Fyll i adressen till din tjänst, inklusive ?key=...
DASH_URL="http://192.168.68.54:8000/dash.png"

# Sekunder mellan uppdateringar dagtid (06-24) och nattetid (00-06)
DAY_REFRESH=180
NIGHT_REFRESH=1800

# Hur ofta skärmen blinkar svart för att rensa spökbilder (var N:e uppdatering)
FULL_REFRESH_EVERY=10

# 1 = tryck var som helst på skärmen för att växla Jobbresor / Alla avgångar
TAP_TO_TOGGLE=1
# Lämna tomt för att hitta pekskärmen automatiskt, annars t.ex. /dev/input/event1
TOUCH_DEV=""
