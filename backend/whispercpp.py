from __future__ import annotations

import os
import re
import json
import subprocess
from typing import Optional, List, Dict, Any


def _run(cmd: list[str], cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    # Use binary capture to avoid decoding issues during execution
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=False, cwd=cwd)


def ensure_whispercpp(root_dir: str) -> str:
    """Return path to whisper-cli."""
    candidates = [
        os.path.join(root_dir, "bin", "whisper-cli"),
        "whisper-cli",
    ]
    for c in candidates:
        if os.path.isabs(c):
            if os.path.isfile(c) and os.access(c, os.X_OK):
                return c
        else:
            try:
                subprocess.run([c, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                return c
            except FileNotFoundError:
                continue
    return "whisper-cli"


_SRT_TIME_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2}),(\d{3})\s+-->\s+(\d{2}):(\d{2}):(\d{2}),(\d{3})$")


def _to_ms(hh: int, mm: int, ss: int, ms: int) -> int:
    return ((hh * 3600 + mm * 60 + ss) * 1000) + ms


def parse_srt(srt_text: str) -> List[Dict[str, Any]]:
    """Parse .srt into segments with ms timestamps."""
    segments: List[Dict[str, Any]] = []
    lines = [ln.rstrip("\n") for ln in srt_text.splitlines()]
    i = 0
    while i < len(lines):
        # block format:
        # 1
        # 00:00:01,000 --> 00:00:03,000
        # text...
        if not lines[i].strip():
            i += 1
            continue

        # skip index line if numeric
        if lines[i].strip().isdigit():
            i += 1
            if i >= len(lines):
                break

        m = _SRT_TIME_RE.match(lines[i].strip())
        if not m:
            i += 1
            continue

        sh, sm, ss, sms, eh, em, es, ems = map(int, m.groups())
        start_ms = _to_ms(sh, sm, ss, sms)
        end_ms = _to_ms(eh, em, es, ems)
        i += 1

        texts: List[str] = []
        while i < len(lines) and lines[i].strip() != "":
            texts.append(lines[i].strip())
            i += 1

        text = " ".join([t for t in texts if t]).strip()
        if text:
            segments.append({"start_ms": start_ms, "end_ms": end_ms, "text": text})

        # skip blank
        while i < len(lines) and lines[i].strip() == "":
            i += 1

    return segments


def transcribe(
    whisper_bin: str,
    model_path: str,
    audio_wav: str,
    out_dir: str,
    language: Optional[str] = "zh",
) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)

    output_base = os.path.join(out_dir, os.path.basename(audio_wav))

    # Ask whisper-cli to write SRT (timestamps) and TXT; JSON can be added later if needed
    cmd = [
        whisper_bin,
        "-m",
        model_path,
        "-f",
        audio_wav,
        "--output-srt",
        "--output-txt",
        "-of",
        output_base,
        "--print-progress",
        "--print-colors",
        "0",
        "--no-timestamps",
        "0",
    ]
    if language:
        cmd.extend(["-l", language])

    p = _run(cmd)
    stdout_decoded = p.stdout.decode("utf-8", errors="replace")
    if p.returncode != 0:
        raise RuntimeError(f"whisper.cpp failed:\n{stdout_decoded}")

    # Prefer SRT for timestamps
    srt_file = output_base + ".srt"
    segments: List[Dict[str, Any]] = []
    if os.path.exists(srt_file):
        with open(srt_file, "r", encoding="utf-8", errors="replace") as f:
            segments = parse_srt(f.read())

    # Fallback: if no SRT segments, read txt as plain text and make one segment
    txt_file = output_base + ".txt"
    plain_text = ""
    if os.path.exists(txt_file):
        with open(txt_file, "r", encoding="utf-8", errors="replace") as f:
            plain_text = f.read().strip()

    if not segments:
        if not plain_text:
            plain_text = stdout_decoded.strip()
        if plain_text:
            segments = [{"start_ms": 0, "end_ms": 0, "text": plain_text}]

    full_text = "\n".join([s["text"] for s in segments]).strip()
    return {"segments": segments, "full_text": full_text, "raw_log": stdout_decoded, "srt": os.path.basename(srt_file) if os.path.exists(srt_file) else None}
