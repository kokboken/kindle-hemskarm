"""Web server.

  /dash.png?key=...         the image the Kindle shows (current mode)
  /toggle.png?key=...       switch mode and return the new image (Kindle tap)
  /?key=...                 phone page with buttons to switch mode + preview
  /mode/<jobb|alla>?key=... set mode from the phone page
"""
import hmac
import logging
import threading
import time
from urllib.parse import quote

from flask import Flask, Response, abort, redirect, request

from dash import config
from dash.render import render_png

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
app = Flask(__name__)

MODES = {"jobb": "Jobbresor", "alla": "Alla avgångar"}
_state = {"mode": config.DEFAULT_MODE if config.DEFAULT_MODE in MODES else "jobb"}
_cache = {"png": None, "at": 0.0, "mode": None}
_lock = threading.Lock()
CACHE_SECONDS = 45


def _check_key():
    if config.DASH_KEY and not hmac.compare_digest(request.args.get("key", ""), config.DASH_KEY):
        abort(403)


def _key_qs():
    key = request.args.get("key", "")
    return f"?key={quote(key)}" if key else ""


def _set_mode(mode):
    with _lock:
        _state["mode"] = mode
        _cache["png"] = None


def _png_response():
    with _lock:
        mode = _state["mode"]
        if not _cache["png"] or _cache["mode"] != mode or time.time() - _cache["at"] > CACHE_SECONDS:
            _cache["png"] = render_png(mode)
            _cache["at"] = time.time()
            _cache["mode"] = mode
        png = _cache["png"]
    return Response(png, mimetype="image/png", headers={"Cache-Control": "no-store"})


@app.get("/dash.png")
def dash_png():
    _check_key()
    return _png_response()


@app.get("/toggle.png")
def toggle_png():
    _check_key()
    _set_mode("alla" if _state["mode"] == "jobb" else "jobb")
    return _png_response()


@app.get("/mode/<mode>")
def set_mode(mode):
    _check_key()
    if mode not in MODES:
        abort(404)
    _set_mode(mode)
    return redirect("/" + _key_qs())


@app.get("/")
def phone_page():
    _check_key()
    qs = _key_qs()
    current = _state["mode"]
    buttons = "".join(
        f"<a class='btn{' on' if m == current else ''}' href='/mode/{m}{qs}'>{label}</a>"
        for m, label in MODES.items()
    )
    return f"""<!doctype html><html lang=sv><meta charset=utf-8>
<meta name=viewport content='width=device-width,initial-scale=1'>
<title>Hemskärmen</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ margin:0; font:17px system-ui,sans-serif; background:#f2f2f2; color:#111; }}
  main {{ max-width:520px; margin:0 auto; padding:16px; }}
  h1 {{ font-size:20px; margin:4px 0 12px; }}
  .row {{ display:flex; gap:10px; margin-bottom:14px; }}
  .btn {{ flex:1; text-align:center; padding:16px 8px; border-radius:12px; border:2px solid #111;
          color:#111; text-decoration:none; font-weight:600; background:#fff; }}
  .btn.on {{ background:#111; color:#fff; }}
  img {{ width:100%; border-radius:8px; background:#fff; box-shadow:0 1px 4px #0003; }}
  p {{ color:#666; font-size:14px; }}
  @media (prefers-color-scheme: dark) {{
    body {{ background:#1b1b1b; color:#eee; }}
    .btn {{ background:#2a2a2a; color:#eee; border-color:#eee; }}
    .btn.on {{ background:#eee; color:#111; }}
    p {{ color:#aaa; }}
  }}
</style>
<main>
  <h1>Hemskärmen</h1>
  <div class=row>{buttons}</div>
  <img src='/dash.png{qs}' alt='Det som visas på Kindlen'>
  <p>Kindlen visar det nya läget nästa gång den uppdaterar (inom några minuter).</p>
</main></html>"""


@app.get("/health")
def health():
    return "ok"


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)
