"""Draws the dashboard as a grayscale PNG sized for the Kindle screen."""
import io
import logging
import os
from datetime import datetime
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

from . import calendar, config, journeys, keep, vasttrafik, weather

log = logging.getLogger(__name__)

BLACK, DARK, MID, LIGHT, WHITE = 0, 60, 120, 200, 255
M = 64  # page margin
DEP_ROW_H = 84
WEATHER_H = 70 + 62 + 3 * 42 + 18 + 120 + 16  # title + text block + hourly strip + gap
LIST_MIN_H = 70 + 5 * 62  # title + at least 5 rows (10 items in two columns)

WEEKDAYS = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag", "Lördag", "Söndag"]
MONTHS = ["januari", "februari", "mars", "april", "maj", "juni", "juli",
          "augusti", "september", "oktober", "november", "december"]

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_CANDIDATES = {
    False: [os.path.join(HERE, "fonts", "NotoSans-Regular.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:/Windows/Fonts/segoeui.ttf"],
    True: [os.path.join(HERE, "fonts", "NotoSans-Bold.ttf"),
           "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
           "C:/Windows/Fonts/segoeuib.ttf"],
    "italic": [os.path.join(HERE, "fonts", "NotoSans-Italic.ttf"),
               "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
               "C:/Windows/Fonts/segoeuii.ttf"],
}


@lru_cache(maxsize=64)
def font(size, bold=False, italic=False):
    for path in FONT_CANDIDATES["italic" if italic else bold]:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size)


def _w(draw, text, f):
    return draw.textlength(text, font=f)


def _fit(draw, text, f, max_w):
    if _w(draw, text, f) <= max_w:
        return text
    while text and _w(draw, text + "…", f) > max_w:
        text = text[:-1]
    return text.rstrip() + "…"


def _safe(fn):
    try:
        return fn(), None
    except Exception as e:  # show the error on screen instead of crashing
        log.exception("source failed")
        return None, str(e) or e.__class__.__name__


def _section_title(d, y, text, right=None):
    d.text((M, y), text.upper(), font=font(34, True), fill=DARK)
    if right:
        f = font(30)
        d.text((config.WIDTH - M - _w(d, right, f), y + 4), right, font=f, fill=MID)
    y += 52
    d.line([(M, y), (config.WIDTH - M, y)], fill=BLACK, width=3)
    return y + 18


def _error(d, y, msg):
    d.text((M, y), _fit(d, "Fel: " + msg, font(32), config.WIDTH - 2 * M), font=font(32), fill=MID)
    return y + 60


def _draw_departures(d, y, deps, err, now, max_y, mode):
    work = mode == "jobb"
    title = ("Jobbresor" if work else "Alla avgångar") + ("" if vasttrafik.configured() else " (EXEMPEL)")
    hint = "Tryck: alla avgångar" if work else "Tryck: jobbresor"
    y = _section_title(d, y, f"{title} · {config.VT_STOP_NAME}", right=hint)
    if err:
        return _error(d, y, err)
    if not deps:
        d.text((M, y), "Inga avgångar de närmaste två timmarna", font=font(40), fill=MID)
        return y + 70

    n_times = config.VT_WORK_TIMES if work else config.VT_TIMES_PER_ROW
    slot_w = 140 if n_times > 3 else 150
    times_w = slot_w * n_times
    badge_w, badge_h = 96, 54
    f_badge, f_dir = font(40, True), font(40)
    for g in deps:
        if g.connections:
            row_h = 136
        elif work:
            row_h = 108
        else:
            row_h = DEP_ROW_H
        if y + row_h > max_y:
            break
        cy = y + row_h // 2
        # Line number badge
        d.rounded_rectangle([M, cy - badge_h // 2, M + badge_w, cy + badge_h // 2], radius=12, fill=BLACK)
        tw = _w(d, g.line, f_badge)
        d.text((M + (badge_w - tw) / 2, cy), g.line, font=f_badge, fill=WHITE, anchor="lm")
        # Direction
        dir_x = M + badge_w + 28
        dir_max = config.WIDTH - M - times_w - dir_x - 16
        if g.label:
            d.text((dir_x, cy - 18), _fit(d, g.direction, f_dir, dir_max), font=f_dir, fill=BLACK, anchor="lm")
            sub = " · ".join(x for x in (g.label, g.via) if x)
            d.text((dir_x, cy + 26), _fit(d, sub, font(30), dir_max), font=font(30), fill=MID, anchor="lm")
        else:
            d.text((dir_x, cy), _fit(d, g.direction, f_dir, dir_max), font=f_dir, fill=BLACK, anchor="lm")
        # Times, right aligned in fixed slots: "5 min" / "22:34" / ("25 22:45")
        for i, (t, cancelled) in enumerate(g.times):
            mins = int((t - now).total_seconds() // 60)
            if mins <= 0:
                label = "Nu"
            elif mins < 60:
                label = f"{mins} min"
            else:
                label = t.strftime("%H:%M")
            right = config.WIDTH - M - (n_times - 1 - i) * slot_w
            big = font(42 if work else 38, True) if i == 0 else font(38 if work else 34)
            lines = []
            if g.connections:  # connecting line on top, in italics: "25 23:19"
                wait = g.waits[i] if i < len(g.waits) else None
                cf = font(25, italic=True)
                c_txt = f"vänta {wait} min" if wait is not None else f"ingen {g.via_line}"
                for alt in (font(23, italic=True), font(21, italic=True)):  # shrink to fit its column
                    if _w(d, c_txt, cf) <= slot_w - 12:
                        break
                    cf = alt
                if _w(d, c_txt, cf) > slot_w - 12:
                    c_txt = f"vänta {wait}" if wait is not None else "–"
                lines.append((c_txt, cf, MID, 30))
            main_idx = len(lines)
            lines.append((label, big, BLACK if i == 0 else DARK, 44 if work else 40))
            if mins < 60:
                lines.append((t.strftime("%H:%M"), font(28 if work else 26), MID, 32 if work else 30))
            ly = cy - sum(h for *_, h in lines) / 2
            for n, (txt, f, fill, h) in enumerate(lines):
                tcy = ly + h / 2
                lw = _w(d, txt, f)
                d.text((right - lw, tcy), txt, font=f, fill=fill, anchor="lm")
                if cancelled and n == main_idx:
                    d.line([(right - lw - 4, tcy), (right + 4, tcy)], fill=BLACK, width=4)
                ly += h
        y += row_h
        d.line([(M, y), (config.WIDTH - M, y)], fill=LIGHT, width=1)
    return y + 10


def _deg(v):
    return f"{round(v):d}°".replace("-", "−")


def _draw_weather(d, y, w, err, compact=False):
    y = _section_title(d, y, f"Väder · {config.WEATHER_PLACE}")
    if err:
        return _error(d, y, err)

    big = font(140, True)
    temp = _deg(w.temp)
    d.text((M - 6, y - 22), temp, font=big, fill=BLACK)
    x = M + _w(d, temp, big) + 40
    max_w = config.WIDTH - M - x
    d.text((x, y), _fit(d, weather.describe(w.symbol), font(46, True), max_w), font=font(46, True), fill=BLACK)
    info = f"Vind {round(w.wind)} m/s"
    if round(w.today_min) != round(w.today_max):
        info = f"Idag {_deg(w.today_min)} till {_deg(w.today_max)}  ·  " + info
    lines = [info]
    if w.commute_warning:
        lines.append(("!", w.commute_warning))
    elif w.precip_next_hour >= 0.1:
        lines.append(f"{w.precip_next_hour:.1f} mm nederbörd närmaste timmen".replace(".", ","))
    else:
        lines.append("Uppehåll närmaste timmen")
    if w.tomorrow:
        lo, hi, sym = w.tomorrow
        lines.append(f"Imorgon: {weather.describe(sym)}, {_deg(lo)} till {_deg(hi)}")
    for i, line in enumerate(lines):
        f, fill = font(32), DARK
        if isinstance(line, tuple):  # warning: bold black
            line, f, fill = line[1], font(32, True), BLACK
        d.text((x, y + 62 + i * 42), _fit(d, line, f, max_w), font=f, fill=fill)
    y += 62 + len(lines) * 42 + 18

    # Hourly strip (dropped when the screen is full)
    if w.hours and not compact:
        col_w = (config.WIDTH - 2 * M) / len(w.hours)
        for i, h in enumerate(w.hours):
            cx = M + col_w * i + col_w / 2
            d.text((cx, y), h.time.strftime("%H"), font=font(28), fill=MID, anchor="mt")
            d.text((cx, y + 34), _deg(h.temp), font=font(42, True), fill=BLACK, anchor="mt")
            p = f"{h.precip:.1f} mm".replace(".", ",") if h.precip >= 0.1 else "–"
            d.text((cx, y + 84), p, font=font(26), fill=MID, anchor="mt")
        y += 120
    return y


def _draw_list(d, y, data, err, max_y):
    title, items = data if data else (config.KEEP_NOTE_TITLE, [])
    if not keep.configured():
        title += " (EXEMPEL)"
    y = _section_title(d, y, title, right=f"{len(items)} saker" if items else None)
    if err:
        return _error(d, y, err)
    if not items:
        d.text((M, y), "Listan är tom", font=font(40), fill=MID)
        return y + 70

    f = font(40)
    row_h = 62
    col_w = (config.WIDTH - 2 * M) // 2
    rows = max(1, (max_y - y) // row_h)
    capacity = rows * 2
    shown = items if len(items) <= capacity else items[: capacity - 1]
    for i, text in enumerate(shown):
        col, row = divmod(i, rows)
        x = M + col * col_w
        yy = y + row * row_h
        d.rectangle([x, yy + 12, x + 34, yy + 46], outline=BLACK, width=3)
        d.text((x + 54, yy + 29), _fit(d, text, f, col_w - 70), font=f, fill=BLACK, anchor="lm")
    if len(shown) < len(items):
        col, row = divmod(len(shown), rows)
        d.text((M + col * col_w + 54, y + row * row_h + 29), f"+ {len(items) - len(shown)} till",
               font=f, fill=MID, anchor="lm")
    return y + min(rows, len(shown)) * row_h


FASTEST_ROW_H = 84


def _fastest_height(fast):
    return 70 + FASTEST_ROW_H * len(fast) + 10 if fast else 0


def _badge(d, x, cy, text, h=42, fsize=28):
    f = font(fsize, True)
    w = max(h + 12, int(_w(d, text, f)) + 20)
    d.rounded_rectangle([x, cy - h // 2, x + w, cy + h // 2], radius=9, fill=BLACK)
    d.text((x + w / 2, cy), text, font=f, fill=WHITE, anchor="mm")
    return x + w


def _draw_fastest(d, y, fast, err, now):
    y = _section_title(d, y, "Snabbast till")
    if err:
        return _error(d, y, err)
    name_w = 330
    col_w = (config.WIDTH - 2 * M - name_w) / max(1, config.FASTEST_COUNT)
    for dest, trips in fast:
        cy = y + FASTEST_ROW_H // 2
        d.text((M, cy), _fit(d, dest, font(36, True), name_w - 20), font=font(36, True), fill=BLACK, anchor="lm")
        if not trips:
            d.text((M + name_w, cy), "Ingen resa hittad", font=font(30), fill=MID, anchor="lm")
        for i, t in enumerate(trips):
            x = M + name_w + i * col_w
            for n, line in enumerate(t.lines):
                x = _badge(d, x, cy, line) + 6
            x += 8
            mins = int((t.depart - now).total_seconds() // 60)
            when = "går nu" if mins <= 0 else f"går {t.depart:%H:%M} · om {mins} min"
            d.text((x, cy - 15), f"framme {t.arrive:%H:%M}", font=font(34, True), fill=BLACK, anchor="lm")
            d.text((x, cy + 22), when, font=font(24), fill=MID, anchor="lm")
        y += FASTEST_ROW_H
        d.line([(M, y), (config.WIDTH - M, y)], fill=LIGHT, width=1)
    return y + 10


def _note_lines(d, note):
    """Wrap the note into at most 3 lines that fit inside the box."""
    f = font(38, True)
    max_w = config.WIDTH - 2 * M - 48
    lines = []
    for para in note.splitlines() or [note]:
        words, cur = para.split(), ""
        for w in words:
            test = f"{cur} {w}".strip()
            if _w(d, test, f) <= max_w:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w
        if cur:
            lines.append(cur)
    if len(lines) > 3:
        lines = lines[:3]
        lines[2] = _fit(d, lines[2] + " …", f, max_w)
    return lines


def _draw_note(d, y, lines):
    h = 28 + 50 * len(lines)
    d.rounded_rectangle([M, y, config.WIDTH - M, y + h], radius=14, outline=BLACK, width=4)
    for i, line in enumerate(lines):
        d.text((M + 24, y + 14 + i * 50), line, font=font(38, True), fill=BLACK)
    return y + h


CAL_ROW_H = 54


def _cal_height(events, err):
    if err:
        return 130
    return 70 + CAL_ROW_H * min(len(events), config.CAL_MAX_EVENTS) + 10 if events else 0


def _draw_calendar(d, y, events, err):
    y = _section_title(d, y, "Kalender")
    if err:
        return _error(d, y, err)
    for e in events[: config.CAL_MAX_EVENTS]:
        cy = y + CAL_ROW_H // 2
        when = "Heldag" if e.all_day else f"{e.start:%H:%M}"
        x = M
        if e.tomorrow:
            d.text((x, cy), "Imorgon", font=font(30), fill=MID, anchor="lm")
            x += 140
        d.text((x, cy), when, font=font(34, True), fill=BLACK, anchor="lm")
        tx = x + (130 if not e.all_day else 130)
        d.text((tx, cy), _fit(d, e.title, font(34), config.WIDTH - M - tx), font=font(34), fill=BLACK, anchor="lm")
        y += CAL_ROW_H
    return y + 10


def _render_night(now):
    """Calm night screen: big clock, date, tomorrow's weather, commute warning and the note."""
    wx, wx_err = _safe(weather.fetch)
    note, _ = _safe(keep.get_note)
    img = Image.new("L", (config.WIDTH, config.HEIGHT), WHITE)
    d = ImageDraw.Draw(img)
    cx = config.WIDTH / 2
    d.text((cx, 470), f"{now:%H:%M}", font=font(300, True), fill=BLACK, anchor="mm")
    date = f"{WEEKDAYS[now.weekday()]} {now.day} {MONTHS[now.month - 1]}"
    d.text((cx, 690), date, font=font(60), fill=DARK, anchor="mm")
    y = 840
    # Before midnight: tomorrow's weather. After midnight the new day has started: today's.
    day = (wx.tomorrow, "Imorgon") if wx and now.hour >= 12 else ((wx.today or wx.tomorrow), "Idag") if wx else (None, "")
    if day[0]:
        (lo, hi, sym), label = day
        d.text((cx, y), f"{label}: {weather.describe(sym)}", font=font(56, True), fill=BLACK, anchor="mm")
        d.text((cx, y + 80), f"{_deg(lo)} till {_deg(hi)}", font=font(56), fill=BLACK, anchor="mm")
        y += 190
    elif wx_err:
        d.text((cx, y), "Väder saknas", font=font(40), fill=MID, anchor="mm")
        y += 100
    if wx and wx.commute_warning:
        d.text((cx, y), _fit(d, wx.commute_warning, font(40, True), config.WIDTH - 2 * M),
               font=font(40, True), fill=BLACK, anchor="mm")
        y += 100
    if note:
        y = _draw_note(d, y + 20, _note_lines(d, note))
    d.text((cx, config.HEIGHT - 60), f"Nattläge till {config.NIGHT_END:02d}:00 · uppdaterad {now:%H:%M}",
           font=font(26), fill=MID, anchor="mm")
    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def render_png(mode="alla", now=None):
    now = now or datetime.now(config.TZ)
    if config.is_night(now.hour):
        return _render_night(now)
    deps, deps_err = _safe(lambda: vasttrafik.fetch(mode))
    wx, wx_err = _safe(weather.fetch)
    lst, lst_err = _safe(keep.fetch)
    fast, fast_err = _safe(journeys.fetch) if mode == "jobb" else ([], None)
    note, _ = _safe(keep.get_note)
    cal, cal_err = _safe(calendar.fetch)
    cal = cal or []

    img = Image.new("L", (config.WIDTH, config.HEIGHT), WHITE)
    d = ImageDraw.Draw(img)

    # Header: date left, big clock right with "updated" under it
    date = f"{WEEKDAYS[now.weekday()]} {now.day} {MONTHS[now.month - 1]}"
    d.text((M, 50), date, font=font(66, True), fill=BLACK)
    clock = f"{now:%H:%M}"
    fc = font(104, True)
    d.text((config.WIDTH - M - _w(d, clock, fc), 8), clock, font=fc, fill=BLACK)
    upd = f"Uppdaterad {now:%H:%M:%S}"
    d.text((config.WIDTH - M - _w(d, upd, font(26)), 140), upd, font=font(26), fill=MID)
    y = 190
    note_h = 0
    if note:
        note_lines = _note_lines(d, note)
        y = _draw_note(d, y, note_lines) + 20
        note_h = y - 190

    # Space budget. Everything below the departures needs room; when the work view is too full,
    # first drop the hourly weather strip, then show fewer calendar events.
    n_items = len(lst[1]) if lst else 0
    list_rows = min(5, max(1, (n_items + 1) // 2))  # two columns, at most 5 rows reserved
    list_h = 70 + list_rows * 62
    fast_h = (_fastest_height(fast) + 16 if fast else 0) if not fast_err else 146
    weather_h = WEATHER_H
    compact = False
    if mode == "jobb" and deps:
        dep_h = 70 + sum(136 if g.connections else 108 for g in deps) + 26
        def need():
            return y + dep_h + fast_h + (_cal_height(cal, cal_err) + 16 if (cal or cal_err) else 0) + weather_h + list_h + 30
        if need() > config.HEIGHT:
            compact, weather_h = True, WEATHER_H - 120
        while need() > config.HEIGHT and len(cal) > 1:
            cal = cal[: min(len(cal), config.CAL_MAX_EVENTS) - 1]
        while need() > config.HEIGHT and list_rows > 2:  # the list shows "+N till" for the rest
            list_rows -= 1
            list_h = 70 + list_rows * 62
    cal_h = _cal_height(cal, cal_err) + 16 if (cal or cal_err) else 0
    dep_max_y = config.HEIGHT - 30 - weather_h - list_h - fast_h - cal_h
    y = _draw_departures(d, y, deps, deps_err, now, max_y=dep_max_y, mode=mode) + 16
    if fast or fast_err:
        y = _draw_fastest(d, y, fast, fast_err, now) + 16
    if cal or cal_err:
        y = _draw_calendar(d, y, cal, cal_err) + 16
    y = _draw_weather(d, y, wx, wx_err, compact=compact) + 16
    _draw_list(d, y, lst, lst_err, max_y=config.HEIGHT - 30)

    buf = io.BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()
