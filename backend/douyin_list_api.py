"""
抖音用户视频列表 API
使用 TikTokApi 获取抖音 UP 主发布的所有视频列表
"""
from __future__ import annotations

import re
import urllib.parse
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/api/douyin", tags=["douyin"])


def extract_sec_user_id(url: str) -> Optional[str]:
    """
    从抖音用户主页链接中提取 sec_user_id

    支持的格式：
    - https://www.douyin.com/user/MS4wLjABAAAA...
    - https://v.douyin.com/短链接/ (需要解析重定向)
    """
    # 标准用户主页链接
    match = re.search(r'douyin\.com/user/([^/?]+)', url)
    if match:
        return match.group(1)

    # 可能是短链接或其他格式，尝试提取 modal_id 或 user_id
    # 解析 URL 参数
    parsed = urllib.parse.urlparse(url)
    params = urllib.parse.parse_qs(parsed.query)

    # 尝试从参数中获取
    if 'sec_user_id' in params:
        return params['sec_user_id'][0]
    if 'user_id' in params:
        return params['user_id'][0]

    return None


async def fetch_user_videos(sec_user_id: str, count: int = 30) -> List[Dict[str, Any]]:
    """
    使用 TikTokApi 获取用户发布的视频列表

    注意：TikTokApi 需要先安装 playwright 并下载浏览器
    playwright install
    """
    try:
        from TikTokApi import TikTokApi
    except ImportError:
        raise RuntimeError(
            "TikTokApi 未安装。请运行：pip install TikTokApi playwright && playwright install"
        )

    videos = []

    try:
        async with TikTokApi() as api:
            # 创建会话（模拟移动端）
            await api.create_sessions(num_sessions=1, sleep_after=3, headless=True)

            user = api.user(sec_user_id)
            user_videos = user.videos(count=count)

            async for video in user_videos:
                video_info = {
                    "id": getattr(video, 'id', None) or video.as_dict.get('aweme_id', ''),
                    "title": getattr(video, 'desc', None) or video.as_dict.get('desc', '')[:100],
                    "url": f"https://www.douyin.com/video/{video.as_dict.get('aweme_id', '')}",
                    "create_time": video.as_dict.get('create_time', 0),
                    "author": video.as_dict.get('author', {}).get('nickname', ''),
                    "author_id": video.as_dict.get('author', {}).get('unique_id', ''),
                    "like_count": video.as_dict.get('statistics', {}).get('digg_count', 0),
                    "comment_count": video.as_dict.get('statistics', {}).get('comment_count', 0),
                    "share_count": video.as_dict.get('statistics', {}).get('share_count', 0),
                    "cover": video.as_dict.get('video', {}).get('cover', {}).get('url_list', [''])[0],
                }
                videos.append(video_info)

    except Exception as e:
        # 如果 TikTokApi 失败，提供详细错误信息
        error_msg = str(e)
        if "sign" in error_msg.lower() or "signature" in error_msg.lower():
            raise RuntimeError(
                f"TikTokApi 签名验证失败。抖音可能更新了 API。\n"
                f"建议：\n"
                f"1. 更新 TikTokApi: pip install -U TikTokApi\n"
                f"2. 或使用手动批量输入链接方式\n"
                f"原始错误：{error_msg}"
            )
        raise RuntimeError(f"获取视频列表失败：{error_msg}")

    return videos


@router.get("/user/videos")
async def list_user_videos(
    url: str = Query(..., description="抖音用户主页链接"),
    limit: int = Query(30, ge=1, le=100, description="最大返回数量"),
):
    """
    获取抖音用户发布的视频列表

    参数：
    - url: 抖音用户主页链接，如 https://www.douyin.com/user/MS4wLjABAAAA...
    - limit: 最大返回数量，默认 30，最大 100

    返回：
    - items: 视频列表，包含 id, title, url, create_time 等字段
    - sec_user_id: 提取到的用户 ID
    """
    # 提取用户 ID
    sec_user_id = extract_sec_user_id(url)
    if not sec_user_id:
        raise HTTPException(
            status_code=400,
            detail=f"无法从链接中提取用户ID。请确保链接格式正确。\n"
                   f"支持的格式：\n"
                   f"- https://www.douyin.com/user/用户ID\n"
                   f"当前链接：{url}"
        )

    try:
        videos = await fetch_user_videos(sec_user_id, count=limit)
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取视频列表失败：{str(e)}")

    if not videos:
        return {
            "items": [],
            "sec_user_id": sec_user_id,
            "message": "未找到视频，可能用户没有发布公开视频"
        }

    return {
        "items": videos,
        "sec_user_id": sec_user_id,
        "count": len(videos)
    }
