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

# Hämtar båda lägena. Visar det aktuella. $1 = "full" för en blinkande helskärmsuppdatering.
refresh() {
  mode=""
  # Har någon nyss tryckt gäller Kindlens eget läge, annars serverns (som mobilen kan ändra).
  last_tap=$(cat "$TAPF" 2>/dev/null || echo 0)
  if [ $(( $(date +%s) - last_tap )) -lt 30 ]; then
    mode=$(cat "$MODEF" 2>/dev/null)
  fi
  if [ -n "$mode" ]; then url="$DASH_URL&mode=$mode"; else url="$DASH_URL"; fi
  start=$(date +%s)

  if ! curl -fsS -m 90 -D /tmp/hd_headers -o "$CUR.new" "$url"; then
    log "kunde inte hamta $url"
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

  if curl -fsS -m 60 -o "$OTHER.new" "$DASH_URL&mode=$(other_of "$mode")"; then
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
  hour=$(date +%H); hour=${hour#0}
  if [ "${hour:-0}" -lt 6 ]; then wait=$NIGHT_REFRESH; else wait=$DAY_REFRESH; fi
  n=$((n + 1))
  if [ $((n % FULL_REFRESH_EVERY)) -eq 1 ]; then refresh full; else refresh; fi
  if [ "$wait" -le 60 ]; then sleep "$(until_next_minute)"; else sleep "$wait"; fi
done
