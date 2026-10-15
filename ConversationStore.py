"""Small daily conversation archive. Each session is saved as a titled JSON file."""
from datetime import datetime
from pathlib import Path
import json
import re
import uuid

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "Data" / "Conversations"
ACTIVE = BASE / "active_session.json"


def _read(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _slug(text):
    words = re.findall(r"[\w]+", str(text), flags=re.UNICODE)[:8]
    return " ".join(words).strip() or "Conversation"


def _session_path(session_id):
    date_part, unique = session_id.split("_", 1)
    folder = BASE / date_part
    matches = list(folder.glob(f"*__{unique}.json")) if folder.exists() else []
    return matches[0] if matches else None


def _active_id():
    return _read(ACTIVE, {}).get("session_id")


def _write_active(session_id):
    BASE.mkdir(parents=True, exist_ok=True)
    ACTIVE.write_text(json.dumps({"session_id": session_id}, ensure_ascii=False), encoding="utf-8")


def append_message(role, content):
    if role not in {"user", "assistant"} or not str(content).strip():
        return None
    now = datetime.now().astimezone()
    session_id = _active_id()
    path = _session_path(session_id) if session_id else None
    session = _read(path, {}) if path else {}
    if not session:
        session_id = f"{now:%Y-%m-%d}_{uuid.uuid4().hex[:8]}"
        title = _slug(content) if role == "user" else "Welcome"
        folder = BASE / f"{now:%Y-%m-%d}"
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{title}__{session_id.rsplit('_', 1)[1]}.json"
        session = {
            "id": session_id,
            "date": now.date().isoformat(),
            "title": title,
            "created_at": now.isoformat(timespec="seconds"),
            "updated_at": now.isoformat(timespec="seconds"),
            "ended": False,
            "messages": [],
        }
        _write_active(session_id)
    session["messages"].append({"role": role, "content": str(content), "timestamp": now.isoformat(timespec="seconds")})
    session["updated_at"] = now.isoformat(timespec="seconds")
    path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
    return session


def close_session():
    session_id = _active_id()
    path = _session_path(session_id) if session_id else None
    if path:
        session = _read(path, {})
        if session:
            session["ended"] = True
            session["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
            path.write_text(json.dumps(session, ensure_ascii=False, indent=2), encoding="utf-8")
    _write_active(None)


def list_sessions():
    sessions = []
    if not BASE.exists():
        return sessions
    for path in BASE.glob("????-??-??/*.json"):
        session = _read(path, {})
        if session.get("id"):
            session["path"] = str(path)
            sessions.append(session)
    return sorted(sessions, key=lambda item: item.get("updated_at", ""), reverse=True)


def get_session(session_id):
    path = _session_path(session_id)
    return _read(path, {}) if path else {}
