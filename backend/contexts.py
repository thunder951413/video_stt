from __future__ import annotations

import json
import os
import threading
import time
from typing import Any, Dict, List, Optional

APP_ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(APP_ROOT, "data")
CONTEXTS_PATH = os.path.join(DATA_DIR, "contexts.json")

_LOCK = threading.Lock()


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S%z")


def _load() -> Dict[str, Any]:
    if not os.path.exists(CONTEXTS_PATH):
        return {"items": []}
    with open(CONTEXTS_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _save(data: Dict[str, Any]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = CONTEXTS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, CONTEXTS_PATH)


def list_contexts() -> List[Dict[str, Any]]:
    with _LOCK:
        data = _load()
        items = data.get("items") or []
        # sort by created_at desc
        def key(it: Dict[str, Any]) -> str:
            return str(it.get("created_at") or "")
        return sorted(items, key=key, reverse=True)


def get_context(task_id: str) -> Optional[Dict[str, Any]]:
    with _LOCK:
        data = _load()
        for it in data.get("items") or []:
            if it.get("id") == task_id:
                return it
        return None


def upsert_context(task_id: str, **fields: Any) -> Dict[str, Any]:
    """Create or update a context entry. 'title' is user-editable display title.
    If 'title' is not provided on update, keep existing title.
    """
    with _LOCK:
        data = _load()
        items: List[Dict[str, Any]] = data.get("items") or []
        existing: Optional[Dict[str, Any]] = None
        for it in items:
            if it.get("id") == task_id:
                existing = it
                break

        if existing is None:
            existing = {
                "id": task_id,
                "title": fields.get("title") or "新任务",
                "source_title": fields.get("source_title"),
                "url": fields.get("url"),
                "created_at": fields.get("created_at") or _now(),
                "status": fields.get("status") or "queued",
            }
            items.append(existing)
        else:
            # preserve user title unless explicitly set
            if "title" in fields and fields["title"]:
                existing["title"] = fields["title"]
            for k, v in fields.items():
                if k == "title":
                    continue
                if v is not None:
                    existing[k] = v

        data["items"] = items
        _save(data)
        return existing


def rename_context(task_id: str, title: str) -> Dict[str, Any]:
    title = (title or "").strip()
    if not title:
        raise ValueError("title cannot be empty")
    return upsert_context(task_id, title=title)


def delete_context(task_id: str) -> None:
    with _LOCK:
        data = _load()
        items: List[Dict[str, Any]] = data.get("items") or []
        data["items"] = [it for it in items if it.get("id") != task_id]
        _save(data)
