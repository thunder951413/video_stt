from __future__ import annotations

import json
import os
import glob
import threading
import time
import subprocess
import shutil
from typing import Optional, Dict, Any, List

from .models import CreateTaskRequest, TaskStatusResponse
from . import bili_downloader
from . import xiaoyuzhou_downloader
from .whispercpp import ensure_whispercpp, transcribe
from .text_format import format_segments
from .contexts import upsert_context

APP_ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(APP_ROOT, "data")
MODELS_DIR = os.path.join(APP_ROOT, "models")

_TASK_LOCKS: Dict[str, threading.Lock] = {}


def _task_dir(task_id: str) -> str:
    return os.path.join(DATA_DIR, task_id)


def _status_path(task_id: str) -> str:
    return os.path.join(_task_dir(task_id), "status.json")


def _write_status(task_id: str, **fields: Any) -> None:
    os.makedirs(_task_dir(task_id), exist_ok=True)
    current: Dict[str, Any] = {}
    p = _status_path(task_id)
    if os.path.exists(p):
        try:
            with open(p, "r", encoding="utf-8") as f:
                current = json.load(f)
        except Exception:
            current = {}
    current.update(fields)
    current["task_id"] = task_id
    with open(p, "w", encoding="utf-8") as f:
        json.dump(current, f, ensure_ascii=False, indent=2)


def get_task_status(task_id: str) -> Optional[TaskStatusResponse]:
    p = _status_path(task_id)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)
    return TaskStatusResponse(**data)


def list_task_files(task_id: str) -> Optional[List[str]]:
    d = _task_dir(task_id)
    if not os.path.isdir(d):
        return None
    files: List[str] = []
    for root, _, filenames in os.walk(d):
        for fn in filenames:
            if fn == "status.json":
                continue
            rel = os.path.relpath(os.path.join(root, fn), d)
            files.append(rel)
    return sorted(files)


def get_task_file_path(task_id: str, rel: str) -> Optional[str]:
    d = _task_dir(task_id)
    if not os.path.isdir(d):
        return None
    rel = rel.lstrip("/\\")
    p = os.path.abspath(os.path.join(d, rel))
    if not p.startswith(os.path.abspath(d) + os.sep):
        return None
    return p


def create_task(task_id: str, req: CreateTaskRequest) -> bool:
    os.makedirs(_task_dir(task_id), exist_ok=True)
    _write_status(task_id, status="queued", step="queued", progress=0.0, message=None, artifacts={})

    # create context index entry early
    upsert_context(
        task_id,
        title="新任务",
        url=req.url,
        status="queued",
        created_at=time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    )

    lock = _TASK_LOCKS.setdefault(task_id, threading.Lock())
    t = threading.Thread(target=_run_task, args=(task_id, req, lock), daemon=True)
    t.start()
    return True


def _run_ffmpeg_to_wav(src: str, dst: str) -> None:
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        src,
        "-ac",
        "1",
        "-ar",
        "16000",
        "-f",
        "wav",
        dst,
    ]
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg failed for {src}:\n{p.stdout}")


def _find_media_files(download_dir: str) -> List[str]:
    exts = ["m4a", "mp3", "ogg", "flac", "webm", "mp4", "mkv", "wav"]
    files: List[str] = []
    for ext in exts:
        files.extend(glob.glob(os.path.join(download_dir, f"*.{ext}")))
    return sorted(files)


def _model_path(model_name: str) -> str:
    mapping = {
        "tiny": "ggml-tiny.bin",
        "base": "ggml-base.bin",
        "small": "ggml-small.bin",
        "medium": "ggml-medium.bin",
        "large-v3": "ggml-large-v3.bin",
    }
    fn = mapping.get(model_name)
    if not fn:
        raise ValueError(f"Unknown model: {model_name}")
    return os.path.join(MODELS_DIR, fn)


def _run_task(task_id: str, req: CreateTaskRequest, lock: threading.Lock) -> None:
    with lock:
        title = None
        source_id = None
        platform = req.platform
        show_notes = None

        try:
            _write_status(
                task_id,
                status="running",
                step="probe",
                progress=0.01,
                message=f"正在解析链接：{req.url}",
                artifacts={"url": req.url, "platform": platform},
            )
            upsert_context(task_id, status="running")

            # Platform-specific probe
            if platform == "bilibili":
                info = bili_downloader.probe_info(req.url, cookies_from_browser=req.cookies_from_browser)
                title = info.get("title")
                source_id = info.get("bvid") or info.get("id")
            elif platform == "xiaoyuzhou":
                info = xiaoyuzhou_downloader.probe_info(req.url, cookies_from_browser=req.cookies_from_browser)
                title = info.get("title")
                source_id = info.get("id") or info.get("episode_id")
                # Try to extract show notes for podcasts
                show_notes = xiaoyuzhou_downloader.extract_show_notes(req.url)
            else:
                raise ValueError(f"Unsupported platform: {platform}")

            if title:
                _write_status(
                    task_id,
                    step="probe",
                    progress=0.03,
                    message=f"已识别：{title}",
                    artifacts={"url": req.url, "title": title, "source_id": source_id, "platform": platform},
                )

            # update context title from source title (but keep user edits if they happen later)
            if title:
                upsert_context(task_id, title=title, source_title=title)

            download_dir = os.path.join(_task_dir(task_id), "download")
            _write_status(task_id, step="download", progress=0.05, artifacts={"title": title, "source_id": source_id, "platform": platform})

            # Platform-specific download
            if platform == "bilibili":
                bili_downloader.download(
                    url=req.url,
                    out_dir=download_dir,
                    download_mode=req.download_mode,
                    parts_mode=req.parts_mode,
                    cookies_from_browser=req.cookies_from_browser,
                )
            elif platform == "xiaoyuzhou":
                xiaoyuzhou_downloader.download(
                    url=req.url,
                    out_dir=download_dir,
                    cookies_from_browser=req.cookies_from_browser,
                )

            media_files = _find_media_files(download_dir)
            if not media_files:
                raise RuntimeError("No media files downloaded")

            whisper_bin = ensure_whispercpp(APP_ROOT)
            model_path = _model_path(req.whisper_model)
            if not os.path.exists(model_path):
                raise RuntimeError(f"Whisper model not found: {model_path}. Please download it into ./models")

            parts: List[Dict[str, Any]] = []
            for idx, src in enumerate(media_files, start=1):
                _write_status(task_id, step=f"audio_extract_{idx}", progress=0.2 + 0.2 * (idx - 1) / max(1, len(media_files)))
                wav = os.path.join(_task_dir(task_id), "audio", f"part_{idx}.wav")
                _run_ffmpeg_to_wav(src, wav)

                _write_status(task_id, step=f"transcribe_{idx}", progress=0.3 + 0.6 * (idx - 1) / max(1, len(media_files)))
                tr = transcribe(
                    whisper_bin=whisper_bin,
                    model_path=model_path,
                    audio_wav=wav,
                    out_dir=os.path.join(_task_dir(task_id), "transcripts"),
                    language=req.language,
                )

                readable_name = f"part_{idx}_readable_{req.output_format}.txt"
                readable_rel = os.path.join("transcripts", readable_name)
                readable_abs = os.path.join(_task_dir(task_id), readable_rel)
                os.makedirs(os.path.dirname(readable_abs), exist_ok=True)
                with open(readable_abs, "w", encoding="utf-8") as f:
                    f.write(format_segments(tr["segments"], req.output_format))

                part_obj: Dict[str, Any] = {
                        "p": idx,
                        "source_file": os.path.relpath(src, _task_dir(task_id)),
                        "audio_wav": os.path.relpath(wav, _task_dir(task_id)),
                        "segments": tr["segments"],
                        "full_text": tr["full_text"],
                    "readable_text": readable_rel,
                    }
                if tr.get("srt"):
                    part_obj["srt"] = os.path.join("transcripts", tr["srt"])

                parts.append(part_obj)

            # Build transcript metadata
            source_meta: Dict[str, Any] = {
                "platform": platform,
                "url": req.url,
                "title": title,
                "download_mode": req.download_mode,
                "parts_mode": req.parts_mode,
                "cookies_from_browser": req.cookies_from_browser,
                "whisper_model": req.whisper_model,
                "output_format": req.output_format,
            }
            if source_id:
                source_meta["source_id"] = source_id
            if show_notes:
                source_meta["show_notes"] = show_notes

            transcript = {
                "source": source_meta,
                "parts": parts,
                "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            }

            out_json = os.path.join(_task_dir(task_id), "transcript.json")
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(transcript, f, ensure_ascii=False, indent=2)

            # Save show notes as separate file if available
            if show_notes:
                show_notes_path = os.path.join(_task_dir(task_id), "show_notes.txt")
                with open(show_notes_path, "w", encoding="utf-8") as f:
                    f.write(show_notes)

            _write_status(
                task_id,
                status="done",
                step="done",
                progress=1.0,
                artifacts={"title": title, "source_id": source_id, "platform": platform, "transcript": "transcript.json"},
            )
            upsert_context(task_id, status="done", url=req.url, source_title=title)

        except Exception as e:
            _write_status(task_id, status="error", step="error", progress=1.0, message=str(e))
            upsert_context(task_id, status="error", url=req.url, source_title=title)