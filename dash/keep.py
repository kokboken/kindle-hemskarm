"""Shopping list from Google Keep.

Google has no official Keep API for personal accounts, so this uses the
unofficial gkeepapi library with a "master token". Use a separate Google
account made just for the dashboard and share the list with it; then the
token only gives access to that account.
"""
import logging
import threading
import time

from . import config

log = logging.getLogger(__name__)

_lock = threading.Lock()
_state = {"keep": None, "last_sync": 0.0}
SYNC_INTERVAL = 60  # seconds


def configured():
    return bool(config.KEEP_EMAIL and config.KEEP_MASTER_TOKEN)


def _client():
    import gkeepapi

    if _state["keep"] is None:
        keep = gkeepapi.Keep()
        keep.authenticate(config.KEEP_EMAIL, config.KEEP_MASTER_TOKEN)
        _state["keep"] = keep
        _state["last_sync"] = time.time()
    elif time.time() - _state["last_sync"] > SYNC_INTERVAL:
        _state["keep"].sync()
        _state["last_sync"] = time.time()
    return _state["keep"]


def fetch():
    """Return (title, [unchecked item texts])."""
    if not configured():
        if config.DEMO_WHEN_UNCONFIGURED:
            return config.KEEP_NOTE_TITLE, ["Mjölk", "Havregryn", "Bananer", "Kaffe",
                                            "Tvättmedel", "Gul lök", "Pasta", "Parmesan"]
        raise RuntimeError("Google Keep är inte inställt")

    with _lock:
        try:
            keep = _client()
        except Exception:
            _state["keep"] = None  # force a fresh login next time
            raise
        want = config.KEEP_NOTE_TITLE.strip().lower()
        notes = [n for n in keep.all() if not n.trashed and not n.archived
                 and (n.title or "").strip().lower() == want]
        if not notes:
            raise RuntimeError(f"Hittade ingen Keep-anteckning med titeln {config.KEEP_NOTE_TITLE!r}")
        note = notes[0]
        if hasattr(note, "unchecked"):  # checklist
            items = [i.text.strip() for i in note.unchecked if i.text.strip()]
        else:  # plain note: one item per line
            items = [l.strip("-•* ").strip() for l in (note.text or "").splitlines() if l.strip()]
        return note.title or config.KEEP_NOTE_TITLE, items


NOTE_TITLE = "Lapp"


def _note(keep):
    for n in keep.all():
        if not n.trashed and (n.title or "").strip().lower() == NOTE_TITLE.lower():
            return n
    return None


def get_note():
    """Text of the shared note ("Lapp") shown at the top of the screen, or ""."""
    if not configured():
        return ""
    with _lock:
        try:
            keep = _client()
        except Exception:
            _state["keep"] = None
            raise
        n = _note(keep)
        return (n.text or "").strip() if n and not n.archived else ""


def set_note(text):
    """Save (or clear, with empty text) the note. Stored in the dashboard account's Google Keep."""
    if not configured():
        raise RuntimeError("Google Keep är inte inställt")
    text = (text or "").strip()[:300]
    with _lock:
        keep = _client()
        n = _note(keep)
        if n is None and text:
            n = keep.createNote(NOTE_TITLE, text)
        elif n is not None:
            n.text = text
            n.archived = False
        keep.sync()
        _state["last_sync"] = time.time()
