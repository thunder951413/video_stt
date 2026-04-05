from __future__ import annotations

import os
import json
import subprocess
from typing import Optional, Dict, Any


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)


def probe_info(url: str, cookies_from_browser: Optional[str] = None) -> Dict[str, Any]:
    """
    探测抖音视频信息
    支持链接格式：
    - https://www.douyin.com/video/视频ID
    - https://v.douyin.com/随机字符/ (短链接)
    - https://www.iesdouyin.com/share/video/视频ID/
    - 用户主页链接（自动提取视频ID并转换）

    注意：抖音通常需要登录才能获取视频信息，建议配置 cookies_from_browser 参数
    """
    # 检查URL格式
    if "douyin.com" not in url and "iesdouyin.com" not in url:
        raise ValueError(f"不是有效的抖音链接: {url}")

    # 检查是否是各种非标准视频页面，尝试提取视频ID
    processed_url = url
    print(f"原始URL: {url}")

    # 首先检查是否是标准视频链接
    is_standard_video_url = (
        "/video/" in url or
        "v.douyin.com" in url or
        "iesdouyin.com/share/video/" in url
    )
    print(f"是否是标准视频链接: {is_standard_video_url}")

    # 如果不是标准视频链接，尝试提取modal_id
    if not is_standard_video_url and "modal_id=" in url:
        print("检测到modal_id参数，尝试提取视频ID...")
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        video_id = params.get("modal_id", [None])[0]
        print(f"提取到的video_id: {video_id}")

        if video_id:
            # 转换为标准视频链接
            processed_url = f"https://www.douyin.com/video/{video_id}"
            print(f"检测到非标准抖音链接，已提取modal_id并转换为视频链接: {processed_url}")

            # 记录原始URL类型以便更好的错误提示
            url_type = "未知页面"
            if "/user/" in url or "/self" in url:
                url_type = "用户主页"
            elif "jingxuan" in url:
                url_type = "精选页面"
            elif "showTab=" in url:
                if "showTab=like" in url:
                    url_type = "点赞页面"
                elif "showTab=post" in url:
                    url_type = "发布页面"
                elif "showTab=follow" in url:
                    url_type = "关注页面"

            print(f"原始URL类型: {url_type}, 视频ID: {video_id}")
        else:
            raise ValueError(
                f"检测到非标准抖音URL但无法提取视频ID: {url}\n"
                f"请确保URL包含 modal_id 参数，例如：\n"
                f"https://www.douyin.com/...?modal_id=视频ID"
            )
    else:
        print(f"URL处理: 标准链接或无需转换")

    cmd = ["yt-dlp", "-J", "--no-warnings", processed_url]
    if cookies_from_browser:
        cmd.extend(["--cookies-from-browser", cookies_from_browser])
    else:
        # 如果没有提供Cookie，尝试默认使用brave（与前端默认值一致）
        cmd.extend(["--cookies-from-browser", "brave"])

    p = _run(cmd)
    if p.returncode != 0:
        error_msg = p.stdout.strip()
        # 检查是否是Cookie相关错误
        if "cookies" in error_msg.lower() or "logged in" in error_msg.lower():
            raise RuntimeError(
                f"抖音视频需要登录才能访问。请按以下步骤操作：\n"
                f"1. 在浏览器中打开抖音网站 (https://www.douyin.com) 并登录您的账号\n"
                f"2. 返回此工具，在'Cookies 来源（浏览器）'输入框中选择对应的浏览器类型（如chrome、brave、firefox）\n"
                f"3. 如果仍然失败，请尝试使用抖音App分享的短链接 (https://v.douyin.com/...)\n"
                f"4. 确保视频是公开可见的（非私密视频）\n"
                f"原始错误：{error_msg}"
            )
        elif "Unsupported URL" in error_msg:
            # 提供更详细的错误信息
            if processed_url != url:
                raise ValueError(
                    f"无法处理转换后的链接: {processed_url}\n"
                    f"原始链接: {url}\n"
                    f"转换状态: 已从原始URL提取modal_id并转换\n"
                    f"可能的原因：\n"
                    f"1. 视频ID无效或视频已被删除\n"
                    f"2. 需要登录才能访问此视频（抖音需要Cookie）\n"
                    f"3. 该视频可能设为私密或仅好友可见\n"
                    f"请尝试：\n"
                    f"1. 在抖音App中直接分享视频链接（短链接）\n"
                    f"2. 确保已登录抖音并配置浏览器Cookie\n"
                    f"3. 检查视频是否公开可见"
                )
            else:
                # 检查是否是缺少modal_id的非标准链接
                if "douyin.com" in url and "/video/" not in url and "v.douyin.com" not in url:
                    raise ValueError(
                        f"不支持的抖音URL格式: {url}\n"
                        f"检测到非标准抖音页面，但缺少 modal_id 参数。\n"
                        f"支持的格式：\n"
                        f"1. 标准视频页面: https://www.douyin.com/video/视频ID\n"
                        f"2. 短链接: https://v.douyin.com/随机字符/\n"
                        f"3. 分享链接: https://www.iesdouyin.com/share/video/视频ID/\n"
                        f"4. 任意抖音页面（需包含modal_id）: https://www.douyin.com/任意路径?modal_id=视频ID\n"
                        f"如何获取：\n"
                        f"1. 在抖音App中点击分享→复制链接（推荐）\n"
                        f"2. 或确保URL包含 modal_id=视频ID 参数"
                    )
                else:
                    raise ValueError(
                        f"不支持的URL格式: {url}\n"
                        f"请使用正确的抖音视频链接格式：\n"
                        f"1. 标准视频页面: https://www.douyin.com/video/视频ID\n"
                        f"2. 短链接: https://v.douyin.com/随机字符/\n"
                        f"3. 分享链接: https://www.iesdouyin.com/share/video/视频ID/\n"
                        f"4. 任意抖音页面（需包含modal_id）: https://www.douyin.com/任意路径?modal_id=视频ID\n"
                        f"如何获取：在抖音App中点击分享→复制链接"
                    )
        else:
            raise RuntimeError(f"yt-dlp probe failed:\n{error_msg}")

    info = json.loads(p.stdout)

    # 抖音视频通常没有分P，但可能有合集
    # 提取视频标题和ID
    title = info.get("title", "")
    video_id = info.get("id", "")

    # 尝试提取更多抖音特定信息
    result = {
        "title": title,
        "id": video_id,
        "duration": info.get("duration"),
        "uploader": info.get("uploader", ""),
        "uploader_id": info.get("uploader_id", ""),
        "description": info.get("description", ""),
        "thumbnail": info.get("thumbnail", ""),
        "webpage_url": info.get("webpage_url", ""),
        "extractor": info.get("extractor", ""),
        "extractor_key": info.get("extractor_key", ""),
        "original_url": url,  # 保存原始URL
        "processed_url": processed_url,  # 保存处理后的URL
    }

    return result


def download(url: str, out_dir: str, download_mode: str, parts_mode: str, cookies_from_browser: Optional[str] = None) -> Dict[str, Any]:
    """
    下载抖音视频
    参数：
    - url: 抖音视频链接（支持多种格式）
    - out_dir: 输出目录
    - download_mode: "audio" 或 "video"
    - parts_mode: "all" 或 "p1" (抖音通常只有单个视频，但支持合集)
    - cookies_from_browser: 浏览器Cookie来源，如 "chrome", "firefox" 等

    注意：抖音通常需要登录才能下载高清视频，建议配置 cookies_from_browser 参数
    """
    os.makedirs(out_dir, exist_ok=True)

    # 处理URL，如果是非标准链接则转换为视频链接
    processed_url = url

    # 首先检查是否是标准视频链接
    is_standard_video_url = (
        "/video/" in url or
        "v.douyin.com" in url or
        "iesdouyin.com/share/video/" in url
    )

    # 如果不是标准视频链接，尝试提取modal_id
    if not is_standard_video_url and "modal_id=" in url:
        import urllib.parse
        parsed = urllib.parse.urlparse(url)
        params = urllib.parse.parse_qs(parsed.query)
        video_id = params.get("modal_id", [None])[0]

        if video_id:
            # 转换为标准视频链接
            processed_url = f"https://www.douyin.com/video/{video_id}"
            print(f"下载：检测到非标准抖音链接，已提取modal_id并转换为视频链接: {processed_url}")

    # 抖音视频下载命令
    cmd = [
        "yt-dlp",
        "--no-warnings",
        "--newline",
        "--ignore-errors",
        "--restrict-filenames",
        "-o",
        os.path.join(out_dir, "%(title)s.%(ext)s"),  # 抖音通常没有分P，使用简单文件名
        processed_url,
    ]

    if cookies_from_browser:
        cmd.extend(["--cookies-from-browser", cookies_from_browser])
    else:
        # 如果没有提供Cookie，尝试默认使用brave（与前端默认值一致）
        cmd.extend(["--cookies-from-browser", "brave"])

    # 抖音通常没有分P，但如果是合集，parts_mode控制是否只下载第一个
    if parts_mode == "p1":
        cmd.extend(["--playlist-items", "1"])

    if download_mode == "audio":
        cmd.extend(["-x", "--audio-format", "m4a"])
    else:
        # 下载视频，选择最佳质量
        cmd.extend(["-f", "bv*+ba/best"])

    p = _run(cmd)
    if p.returncode != 0:
        error_msg = p.stdout.strip()
        # 检查是否是Cookie相关错误
        if "cookies" in error_msg.lower() or "logged in" in error_msg.lower():
            raise RuntimeError(
                f"抖音视频需要登录才能下载。请按以下步骤操作：\n"
                f"1. 在浏览器中打开抖音网站 (https://www.douyin.com) 并登录您的账号\n"
                f"2. 返回此工具，在'Cookies 来源（浏览器）'输入框中选择对应的浏览器类型（如chrome、brave、firefox）\n"
                f"3. 如果仍然失败，请尝试使用抖音App分享的短链接 (https://v.douyin.com/...)\n"
                f"4. 确保视频是公开可见的（非私密视频）\n"
                f"原始错误：{error_msg}"
            )
        else:
            # 提供更详细的错误信息
            if processed_url != url:
                raise RuntimeError(
                    f"下载失败（转换后链接: {processed_url}）:\n"
                    f"原始链接: {url}\n"
                    f"错误信息: {error_msg}\n"
                    f"可能的原因：\n"
                    f"1. 视频ID无效或视频已被删除\n"
                    f"2. 需要登录才能访问此视频\n"
                    f"3. 链接格式不受支持"
                )
            else:
                raise RuntimeError(f"yt-dlp download failed:\n{error_msg}")

    return {"log": p.stdout, "original_url": url, "processed_url": processed_url}


def extract_video_info(url: str, cookies_from_browser: Optional[str] = None) -> Dict[str, Any]:
    """
    提取抖音视频详细信息
    返回包含视频元数据的字典
    """
    info = probe_info(url, cookies_from_browser)

    # 添加抖音特定的信息提取
    result = {
        "title": info.get("title", "抖音视频"),
        "video_id": info.get("id", ""),
        "author": info.get("uploader", ""),
        "author_id": info.get("uploader_id", ""),
        "description": info.get("description", ""),
        "duration": info.get("duration", 0),
        "thumbnail_url": info.get("thumbnail", ""),
        "original_url": info.get("webpage_url", url),
        "platform": "douyin",
    }

    return result