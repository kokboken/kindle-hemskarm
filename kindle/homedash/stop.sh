#!/bin/sh
for f in /tmp/homedash.pid /tmp/homedash-touch.pid; do
  [ -f "$f" ] && kill "$(cat "$f")" 2>/dev/null
  rm -f "$f"
done
killall dd 2>/dev/null
lipc-set-prop com.lab126.powerd preventScreenSaver 0
start lab126_gui 2>/dev/null || /etc/init.d/framework start 2>/dev/null
