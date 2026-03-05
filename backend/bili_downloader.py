from __future__ import annotations

import os
import json
import subprocess
from typing import Optional, Dict, Any


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)


def probe_info(url: str, cookies_from_browser: Optional[str] = None) -> Dict[str, Any]:
    cmd = ["yt-dlp", "-J", "--no-warnings", url]
    if cookies_from_browser:
        cmd.extend(["--cookies-from-browser", cookies_from_browser])
    p = _run(cmd)
    if p.returncode != 0:
        raise RuntimeError(f"yt-dlp probe failed:\n{p.stdout}")
    return json.loads(p.stdout)


def download(url: str, out_dir: str, download_mode: str, parts_mode: str, cookies_from_browser: Optional[str] = None) -> Dict[str, Any]:
    os.makedirs(out_dir, exist_ok=True)

    # Use playlist handling for multi-page; yt-dlp treats multi-page as playlist-like entries.
    # parts_mode=p1 -> download only first item.
    cmd = [
        "yt-dlp",
        "--no-warnings",
        "--newline",
        "--ignore-errors",
        "--restrict-filenames",
        "-o",
        os.path.join(out_dir, "%(playlist_index)s_%(title)s.%(ext)s"),
        url,
    ]
    if cookies_from_browser:
        cmd.extend(["--cookies-from-browser", cookies_from_browser])

    if parts_mode == "p1":
        cmd.extend(["--playlist-items", "1"])

    if download_mode == "audio":
        cmd.extend(["-x", "--audio-format", "m4a"])
    else:
        # download video; keep best
        cmd.extend(["-f", "bv*+ba/best"])

    p = _run(cmd)
    if p.returncode != 0:
        raise RuntimeError(f"yt-dlp download failed:\n{p.stdout}")

    return {"log": p.stdout}
