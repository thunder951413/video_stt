from __future__ import annotations

import json
import os
import threading
from typing import Any, Dict

APP_ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(APP_ROOT, "data")
CONFIG_PATH = os.path.join(DATA_DIR, "config.json")

_LOCK = threading.Lock()

_DEFAULT: Dict[str, Any] = {
    "llm": {
        "base_url": "http://127.0.0.1:11434/v1",
        "api_key": "",
        "default_model": "",
    },
    "rewrite_output_dir": "",
}


def load_config() -> Dict[str, Any]:
    with _LOCK:
        if not os.path.exists(CONFIG_PATH):
            return json.loads(json.dumps(_DEFAULT))
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # shallow merge defaults
        out = json.loads(json.dumps(_DEFAULT))
        out.update(data or {})
        if "llm" in data and isinstance(data["llm"], dict):
            out["llm"].update(data["llm"])
        return out


def save_config(cfg: Dict[str, Any]) -> Dict[str, Any]:
    with _LOCK:
        os.makedirs(DATA_DIR, exist_ok=True)
        tmp = CONFIG_PATH + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
        os.replace(tmp, CONFIG_PATH)
        return cfg
