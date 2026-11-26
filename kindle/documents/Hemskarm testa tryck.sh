#!/bin/sh
# Name: Hemskärm – testa tryck
# Author: Victor
# Tar reda på vilken enhet pekskärmen är. Resultat: homedash-diag.txt i Kindlens rot.
OUT=/mnt/us/homedash-diag.txt
{
  echo "== input devices"; cat /proc/bus/input/devices
  echo "== /dev/input"; ls -l /dev/input
  echo "== verktyg"
  for t in dd cat timeout hexdump od setsid evtest; do
    printf "%s: " "$t"; command -v "$t" || echo saknas
  done
  echo "== homedash.log (sista raderna)"; tail -n 20 /mnt/us/homedash.log 2>/dev/null
} > "$OUT" 2>&1

echo "Tryck flera gånger på skärmen de närmaste 10 sekunderna..."
rm -f /tmp/diag_pids
for d in /dev/input/event*; do
  n=$(basename "$d")
  cat "$d" > "/tmp/diag_$n" 2>/dev/null &
  echo $! >> /tmp/diag_pids
done
sleep 10
kill $(cat /tmp/diag_pids) 2>/dev/null
rm -f /tmp/diag_pids

echo "== bytes per enhet under trycken" >> "$OUT"
for f in /tmp/diag_event*; do
  echo "$(basename "$f" | sed 's/diag_//'): $(wc -c < "$f")" >> "$OUT"
  rm -f "$f"
done
tail -n 8 "$OUT"
echo "Klart! Resultatet finns i homedash-diag.txt"
