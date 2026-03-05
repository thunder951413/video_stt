from __future__ import annotations

import re
from typing import List, Dict, Any


_SENT_SPLIT_RE = re.compile(r"(?<=[。！？!?])")


def ms_to_timestamp(ms: int) -> str:
    if ms < 0:
        ms = 0
    total_sec, milli = divmod(ms, 1000)
    minute, sec = divmod(total_sec, 60)
    hour, minute = divmod(minute, 60)
    if hour > 0:
        return f"{hour:02d}:{minute:02d}:{sec:02d}.{milli:03d}"
    return f"{minute:02d}:{sec:02d}.{milli:03d}"


def punctuate_and_wrap(text: str, max_len: int = 60) -> List[str]:
    """Very simple Chinese-friendly sentence splitting.

    - Split on existing 。！？!? first
    - If still long, insert '，' roughly every max_len chars.
    """
    t = re.sub(r"\s+", "", text).strip()
    if not t:
        return []

    pieces: List[str] = []
    for part in _SENT_SPLIT_RE.split(t):
        part = part.strip()
        if not part:
            continue
        if len(part) <= max_len:
            pieces.append(part)
        else:
            # hard wrap
            i = 0
            while i < len(part):
                chunk = part[i : i + max_len]
                if i + max_len < len(part) and not chunk.endswith(("，", "。", "！", "？")):
                    chunk += "，"
                pieces.append(chunk)
                i += max_len
    return pieces


def format_segments(segments: List[Dict[str, Any]], output_format: str) -> str:
    """output_format:
    - 'A': each line with timestamp prefix
    - 'B': each line without timestamp
    """
    lines: List[str] = []
    for seg in segments:
        start_ms = int(seg.get("start_ms") or 0)
        text = (seg.get("text") or "").strip()
        if not text:
            continue

        # further split long segment into sentences
        sentences = punctuate_and_wrap(text)
        if not sentences:
            continue

        if output_format == "A":
            ts = ms_to_timestamp(start_ms)
            for s in sentences:
                lines.append(f"[{ts}] {s}")
        else:
            for s in sentences:
                lines.append(s)

    return "\n".join(lines).strip() + "\n"
