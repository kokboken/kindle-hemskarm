#!/bin/sh
# Hämtar dashboard-bilden och visar den på skärmen, om och om igen.
# Ett tryck på skärmen växlar mellan "Jobbresor" och "Alla avgångar".
# OBS: ej testad på riktig Kindle än – första versionen.
DIR="$(cd "$(dirname "$0")" && pwd)"
. "$DIR/settings.sh"

IMG=/tmp/homedash.png
LOG=/mnt/us/homedash.log
TOGGLE_URL="$(echo "$DASH_URL" | sed 's#/dash\.png#/toggle.png#')"

log() { echo "$(date '+%F %T') $*" >> "$LOG"; }

show() {  # $1 = url, $2 = "full" for a flashing full refresh
  if curl -fsS -m 90 -o "$IMG.new" "$1"; then
    mv "$IMG.new" "$IMG"
    if [ "$2" = "full" ]; then eips -f -g "$IMG"; else eips -g "$IMG"; fi
    return 0
  fi
  log "kunde inte hamta $1"
  eips 2 2 "Ingen kontakt - forsoker igen"
  return 1
}

# Hitta pekskärmen om den inte är angiven i settings.sh
find_touch() {
  [ -n "$TOUCH_DEV" ] && { echo "$TOUCH_DEV"; return; }
  # Pekskärmen är den enhet som rapporterar positioner (B: ABS=), t.ex. "goodix-ts" på Paperwhite 5.
  awk '
    function pick() { if (!found && ev != "" && (named || abs)) { print "/dev/input/" ev; found = 1 } }
    /^I:/           { ev = ""; named = 0; abs = 0 }
    /^N: Name=/     { named = ($0 ~ /[Tt]ouch|goodix|cyttsp|pt_mt|zforce|elan|[Ww]acom|_ts"/) }
    /^H: Handlers=/ { if (match($0, /event[0-9]+/)) ev = substr($0, RSTART, RLENGTH) }
    /^B: ABS=/      { abs = 1 }
    /^$/            { pick() }
    END             { pick() }' /proc/bus/input/devices | head -n 1
}

watch_touch() {
  dev="$(find_touch)"
  if [ -z "$dev" ]; then
    log "hittade ingen pekskarm bland: $(grep '^N: Name=' /proc/bus/input/devices | tr '\n' ' ')"
    return
  fi
  log "lyssnar pa $dev"
  while true; do
    dd if="$dev" bs=16 count=1 > /dev/null 2>&1   # väntar tills någon rör skärmen
    # Släng resten av händelserna från samma tryck
    cat "$dev" > /dev/null 2>&1 &
    drain=$!
    log "tryck - vaxlar lage"
    show "$TOGGLE_URL" full
    sleep 2
    kill "$drain" 2>/dev/null
  done
}

# Hindra skärmsläckaren och stäng av Kindles vanliga gränssnitt så det inte ritar över.
lipc-set-prop com.lab126.powerd preventScreenSaver 1
stop lab126_gui 2>/dev/null || /etc/init.d/framework stop 2>/dev/null
sleep 3
lipc-set-prop com.lab126.cmd wirelessEnable 1
sleep 5

if [ "$TAP_TO_TOGGLE" = "1" ]; then
  watch_touch &
  echo $! > /tmp/homedash-touch.pid
fi

n=0
while true; do
  hour=$(date +%H)
  if [ "$hour" -lt 6 ]; then wait=$NIGHT_REFRESH; else wait=$DAY_REFRESH; fi
  n=$((n + 1))
  if [ $((n % FULL_REFRESH_EVERY)) -eq 1 ]; then show "$DASH_URL" full; else show "$DASH_URL"; fi
  sleep "$wait"
done
