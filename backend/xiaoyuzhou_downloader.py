from __future__ import annotations

import os
import json
import re
import subprocess
from typing import Optional, Dict, Any
import urllib.request
import urllib.parse


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)


def probe_info(url: str, cookies_from_browser: Optional[str] = None) -> Dict[str, Any]:
    """Probe xiaoyuzhou podcast episode info using yt-dlp."""
    cmd = ["yt-dlp", "-J", "--no-warnings", url]
    if cookies_from_browser:
        cmd.extend(["--cookies-from-browser", cookies_from_browser])
    p = _run(cmd)
    if p.returncode != 0:
        raise RuntimeError(f"yt-dlp probe failed:\n{p.stdout}")
    return json.loads(p.stdout)


def download(url: str, out_dir: str, cookies_from_browser: Optional[str] = None) -> Dict[str, Any]:
    """Download xiaoyuzhou podcast audio."""
    os.makedirs(out_dir, exist_ok=True)

    # Use yt-dlp to download audio
    cmd = [
        "yt-dlp",
        "--no-warnings",
        "--newline",
        "--ignore-errors",
        "--restrict-filenames",
        "-x",
        "--audio-format",
        "m4a",
        "-o",
        os.path.join(out_dir, "%(title)s.%(ext)s"),
        url,
    ]
    if cookies_from_browser:
        cmd.extend(["--cookies-from-browser", cookies_from_browser])

    p = _run(cmd)
    if p.returncode != 0:
        raise RuntimeError(f"yt-dlp download failed:\n{p.stdout}")

    return {"log": p.stdout}


def extract_show_notes(url: str) -> Optional[str]:
    """
    Extract show notes from xiaoyuzhou episode page.
    Returns the show notes text if available.
    """
    try:
        # Use yt-dlp to get webpage content and extract description
        cmd = [
            "yt-dlp",
            "--no-warnings",
            "--skip-download",
            "--write-info-json",
            "--output",
            "-",
            url,
        ]
        p = _run(cmd)

        # Try to get description from probe_info
        info = probe_info(url)

        # Extract description/show notes
        description = info.get("description", "")
        if description:
            return description

        # Try to get from webpage
        webpage_url = info.get("webpage_url", url)
        if webpage_url:
            req = urllib.request.Request(
                webpage_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                },
            )
            with urllib.request.urlopen(req, timeout=30) as response:
                html = response.read().decode("utf-8")

                # Try to extract JSON-LD data
                jsonld_match = re.search(r'<script type="application/ld\+json">(.*?)</script>', html, re.DOTALL)
                if jsonld_match:
                    try:
                        jsonld = json.loads(jsonld_match.group(1))
                        if isinstance(jsonld, dict):
                            desc = jsonld.get("description", "")
                            if desc:
                                return desc
                    except json.JSONDecodeError:
                        pass

                # Try to find description in meta tags
                desc_match = re.search(r'<meta name="description" content="([^"]+)"', html)
                if desc_match:
                    return desc_match.group(1)

        return None
    except Exception as e:
        return None
