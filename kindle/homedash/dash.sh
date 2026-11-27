#!/bin/sh
# Hämtar dashboard-bilden och visar den på skärmen, varje minut.
# Båda lägena (Jobbresor / Alla avgångar) hämtas, så ett tryck på skärmen
# kan visa det andra läget direkt utan att vänta på nätet.
DIR="$(cd "$(dirname "$0")" && pwd)"
. "$DIR/settings.sh"

CUR=/tmp/hd_cur.png        # det som visas
OTHER=/tmp/hd_other.png    # det andra läget, redo för ett tryck
MODEF=/tmp/hd_mode         # vilket läge som visas
TAPF=/tmp/hd_tap           # när någon senast tryckte (sekunder)
LOCK=/tmp/hd_lock
LOG=/mnt/us/homedash.log
MODE_URL="$(echo "$DASH_URL" | sed 's#/dash\.png#/mode.txt#')"
TOGGLE_URL="$(echo "$DASH_URL" | sed 's#/dash\.png#/toggle.png#')"

log() { echo "$(date '+%F %T') $*" >> "$LOG"; }
lock() { i=0; until mkdir "$LOCK" 2>/dev/null; do i=$((i + 1)); [ $i -gt 10 ] && rm -rf "$LOCK"; sleep 1; done; }
unlock() { rmdir "$LOCK" 2>/dev/null; }
other_of() { if [ "$1" = "jobb" ]; then echo alla; else echo jobb; fi; }

# Batterinivå och laddning till servern, som ritar dem uppe till vänster: "&batt=87&chg=1"
battery_qs() {
  b=$(lipc-get-prop com.lab126.powerd battLevel 2>/dev/null)
  [ -z "$b" ] && b=$(gasgauge-info -c 2>/dev/null | tr -dc '0-9')
  c=$(lipc-get-prop com.lab126.powerd isCharging 2>/dev/null)
  [ -n "$b" ] && echo "&batt=$b&chg=${c:-0}"
}

# Hämtar båda lägena. Visar det aktuella. $1 = "full" för en blinkande helskärmsuppdatering.
refresh() {
  mode=""
  # Har någon nyss tryckt gäller Kindlens eget läge, annars serverns (som mobilen kan ändra).
  last_tap=$(cat "$TAPF" 2>/dev/null || echo 0)
  if [ $(( $(date +%s) - last_tap )) -lt 30 ]; then
    mode=$(cat "$MODEF" 2>/dev/null)
  fi
  bat=$(battery_qs)
  if [ -n "$mode" ]; then url="$DASH_URL&mode=$mode$bat"; else url="$DASH_URL$bat"; fi
  start=$(date +%s)

  if ! curl -fsS -m 90 -D /tmp/hd_headers -o "$CUR.new" "$url"; then
    log "kunde inte hamta ${url%%\?*}"
    eips 2 2 "Ingen kontakt - forsoker igen"
    return 1
  fi
  mode=$(tr -d '\r' < /tmp/hd_headers | awk -F': ' 'tolower($1) == "x-dash-mode" { print $2 }')
  [ -z "$mode" ] && mode=jobb
  lock
  if [ "$(cat "$TAPF" 2>/dev/null || echo 0)" -ge "$start" ]; then
    unlock; rm -f "$CUR.new"; return 0   # någon tryckte under hämtningen – behåll det läget
  fi
  mv "$CUR.new" "$CUR"
  echo "$mode" > "$MODEF"
  if [ "$1" = "full" ]; then eips -f -g "$CUR"; else eips -g "$CUR"; fi
  unlock

  if curl -fsS -m 60 -o "$OTHER.new" "$DASH_URL&mode=$(other_of "$mode")$bat"; then
    lock
    if [ "$(cat "$TAPF" 2>/dev/null || echo 0)" -ge "$start" ]; then rm -f "$OTHER.new"; else mv "$OTHER.new" "$OTHER"; fi
    unlock
  else
    rm -f "$OTHER"
  fi
}

# Byter läge direkt med den förhämtade bilden och berättar för servern i bakgrunden.
tap_toggle() {
  lock
  if [ -s "$OTHER" ]; then
    eips -g "$OTHER"
    mv "$CUR" "$CUR.swap"; mv "$OTHER" "$CUR"; mv "$CUR.swap" "$OTHER"
    new=$(other_of "$(cat "$MODEF" 2>/dev/null)")
    echo "$new" > "$MODEF"
    date +%s > "$TAPF"
    unlock
    curl -fsS -m 30 -o /dev/null "$MODE_URL&mode=$new" &
  else
    unlock
    # Ingen förhämtad bild än – fråga servern (långsammare)
    curl -fsS -m 90 -o "$CUR.new" "$TOGGLE_URL" && { lock; mv "$CUR.new" "$CUR"; eips -g "$CUR"; unlock; }
  fi
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
    cat "$dev" > /dev/null 2>&1 &                  # släng resten av samma tryck
    drain=$!
    tap_toggle
    sleep 1
    kill "$drain" 2>/dev/null
  done
}

# Svensk timme från servern (Kindlens egen klocka går ofta på UTC), annars Kindlens.
current_hour() {
  h=$(tr -d '
' < /tmp/hd_headers 2>/dev/null | awk -F': ' 'tolower($1) == "x-dash-hour" { print $2 }')
  [ -z "$h" ] && h=$(date +%H)
  h=${h#0}; echo "${h:-0}"
}

is_night() {  # $1 = timme
  if [ "$NIGHT_START" -gt "$NIGHT_END" ]; then
    [ "$1" -ge "$NIGHT_START" ] || [ "$1" -lt "$NIGHT_END" ]
  else
    [ "$1" -ge "$NIGHT_START" ] && [ "$1" -lt "$NIGHT_END" ]
  fi
}

LIGHT_NOW=""
set_light() {  # $1 = 0-24, tomt = rör inte
  [ -z "$1" ] || [ "$1" = "$LIGHT_NOW" ] && return
  if lipc-set-prop com.lab126.powerd flIntensity "$1" 2>/dev/null; then
    LIGHT_NOW="$1"; log "ljus $1"
  else
    log "kunde inte satta ljus $1"; LIGHT_NOW="$1"
  fi
}

WARMTH_NOW=""
set_warmth() {  # $1 = 0-24, tomt = rör inte
  [ -z "$1" ] || [ "$1" = "$WARMTH_NOW" ] && return
  if lipc-set-prop com.lab126.powerd currentAmberLevel "$1" 2>/dev/null; then
    log "varme $1"
  else
    log "kunde inte satta varme $1"
  fi
  WARMTH_NOW="$1"
}

# Sekunder kvar till strax efter nästa minutskifte, så klockan på skärmen stämmer.
until_next_minute() { s=$(date +%S); s=${s#0}; echo $((62 - s)); }

# Hindra skärmsläckaren och stäng av Kindles vanliga gränssnitt så det inte ritar över.
lipc-set-prop com.lab126.powerd preventScreenSaver 1
stop lab126_gui 2>/dev/null || /etc/init.d/framework stop 2>/dev/null
sleep 3
lipc-set-prop com.lab126.cmd wirelessEnable 1
sleep 5
rm -rf "$LOCK" "$TAPF"

if [ "$TAP_TO_TOGGLE" = "1" ]; then
  watch_touch &
  echo $! > /tmp/homedash-touch.pid
fi

n=0
while true; do
  n=$((n + 1))
  if [ $((n % FULL_REFRESH_EVERY)) -eq 1 ]; then refresh full; else refresh; fi
  hour=$(current_hour)
  if is_night "$hour"; then wait=$NIGHT_REFRESH; set_light "$LIGHT_NIGHT"
  else
    wait=$DAY_REFRESH; set_light "$LIGHT_DAY"
    if [ -n "$EVENING_START" ] && [ "$hour" -ge "$EVENING_START" ]; then
      set_warmth "$WARMTH_EVENING"
    else
      set_warmth "$WARMTH_DAY"
    fi
  fi
  if [ "$wait" -le 60 ]; then sleep "$(until_next_minute)"; else sleep "$wait"; fi
done
