#!/bin/sh
# Name: Hemskärm – starta
# Author: Victor
# DontUseFBInk
# Startar hemskärmen. Avsluta genom att starta om Kindlen (håll in strömknappen).
D=/mnt/us/homedash
[ -f /tmp/homedash.pid ] && kill "$(cat /tmp/homedash.pid)" 2>/dev/null
if command -v setsid > /dev/null 2>&1; then
  setsid nohup sh "$D/dash.sh" > /dev/null 2>&1 &
else
  nohup sh "$D/dash.sh" > /dev/null 2>&1 &
fi
echo $! > /tmp/homedash.pid
