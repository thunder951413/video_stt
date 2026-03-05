from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

from . import bili_downloader

router = APIRouter(prefix="/api/bili", tags=["bilibili"])


def _entry_to_item(e: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    if not isinstance(e, dict):
        return None

    url = e.get("webpage_url") or e.get("url")
    title = e.get("title")
    duration = e.get("duration")
    bvid = e.get("bvid") or e.get("id")

    if not url:
        return None

    # normalize bilibili video url if bvid exists
    if bvid and isinstance(bvid, str) and bvid.startswith("BV"):
        url = f"https://www.bilibili.com/video/{bvid}"

    return {
        "title": title,
        "url": url,
        "bvid": bvid,
        "duration": duration,
    }


@router.get("/list")
def list_videos(
    url: str = Query(..., description="Bilibili UP space video page or playlist URL"),
    cookies_from_browser: Optional[str] = Query("brave"),
    limit: int = Query(50, ge=1, le=200),
):
    try:
        info = bili_downloader.probe_info(url, cookies_from_browser=cookies_from_browser)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    items: List[Dict[str, Any]] = []

    entries = info.get("entries")
    if isinstance(entries, list):
        for e in entries:
            it = _entry_to_item(e)
            if it:
                items.append(it)
            if len(items) >= limit:
                break

    # Some pages might not return entries; fallback to single item
    if not items:
        it = _entry_to_item(info)
        if it:
            items.append(it)

    # remove duplicates by url
    seen = set()
    dedup: List[Dict[str, Any]] = []
    for it in items:
        u = it.get("url")
        if not u or u in seen:
            continue
        seen.add(u)
        dedup.append(it)

    return {"items": dedup}
