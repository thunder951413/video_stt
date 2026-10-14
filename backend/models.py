from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal, Optional, Dict, Any, List


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


class BatchCreateTaskRequest(BaseModel):
    """批量创建任务请求"""
    urls: List[str] = Field(..., description="视频链接列表")
    platform: Platform = Field("douyin", description="Source platform")
    download_mode: DownloadMode = Field("audio", description="audio: only audio; video: download full video")
    parts_mode: PartsMode = Field("all", description="all: all pages; p1: only first page")
    cookies_from_browser: Optional[str] = Field("brave", description="Browser for cookies")
    whisper_model: WhisperModel = Field("medium", description="whisper.cpp model")
    language: Optional[str] = Field("zh", description="language hint")
    output_format: OutputFormat = Field("A", description="A: with timestamp, B: without timestamp")


class BatchCreateTaskResponse(BaseModel):
    """批量创建任务响应"""
    task_ids: List[str] = Field(..., description="创建的任务ID列表")
    count: int = Field(..., description="创建的任务数量")


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
