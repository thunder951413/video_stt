from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any


Platform = Literal["bilibili", "xiaoyuzhou", "douyin"]
DownloadMode = Literal["audio", "video"]
PartsMode = Literal["all", "p1"]
WhisperModel = Literal["tiny", "base", "small", "medium", "large-v3"]
OutputFormat = Literal["A", "B"]  # A: with timestamp, B: without timestamp


class CreateTaskRequest(BaseModel):
    url: str = Field(..., description="Video/Podcast URL")
    platform: Platform = Field("bilibili", description="Source platform")
    download_mode: DownloadMode = Field(
        "audio", description="audio: only audio; video: download full video and also transcribe"
    )
    parts_mode: PartsMode = Field("all", description="all: all pages; p1: only first page")
    cookies_from_browser: Optional[str] = Field(
        "brave", description="yt-dlp --cookies-from-browser value, e.g. brave/chrome"
    )
    whisper_model: WhisperModel = Field("medium", description="whisper.cpp model")
    language: Optional[str] = Field("zh", description="language hint")
    output_format: OutputFormat = Field("A", description="A: with timestamp, B: without timestamp")


class CreateTaskResponse(BaseModel):
    task_id: str


class RenameContextRequest(BaseModel):
    title: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: Literal["queued", "running", "done", "error"]
    step: Optional[str] = None
    progress: Optional[float] = None
    message: Optional[str] = None
    artifacts: Dict[str, Any] = Field(default_factory=dict)
