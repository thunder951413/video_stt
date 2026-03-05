from __future__ import annotations

import os
import json
from typing import Any, AsyncIterator, Dict, Optional

from sse_starlette.sse import EventSourceResponse
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from .config_store import load_config
from .llm_openai_compat import stream_chat_completions
from .contexts import get_context

APP_ROOT = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(APP_ROOT, "data")

router = APIRouter(prefix="/api/llm", tags=["llm"])


class RewriteRequest(BaseModel):
    task_id: str
    source_file: str
    instruction: str = Field("请对下面的文字进行改写，使其更通顺、结构更清晰。", description="rewrite instruction")
    model: Optional[str] = None
    temperature: Optional[float] = None
    top_p: Optional[float] = None


class SaveRewriteRequest(BaseModel):
    task_id: str
    content: str


def _safe_task_file(task_id: str, rel: str) -> str:
    rel = (rel or "").lstrip("/\\")
    task_dir = os.path.abspath(os.path.join(DATA_DIR, task_id))
    data_root = os.path.abspath(DATA_DIR)
    if not task_dir.startswith(data_root + os.sep):
        raise HTTPException(status_code=400, detail="Invalid task_id")
    path = os.path.abspath(os.path.join(task_dir, rel))
    if not path.startswith(task_dir + os.sep):
        raise HTTPException(status_code=400, detail="Invalid file path")
    return path


def _get_llm_cfg(req_model: Optional[str]) -> tuple[str, str, str]:
    cfg = load_config().get("llm") or {}
    base_url = (cfg.get("base_url") or "").strip()
    api_key = (cfg.get("api_key") or "").strip()
    default_model = (cfg.get("default_model") or "").strip()
    model = ((req_model or "") or default_model).strip()
    if not base_url:
        raise HTTPException(status_code=400, detail="LLM base_url not configured")
    if not model:
        raise HTTPException(status_code=400, detail="LLM model not configured")
    return base_url, api_key, model


def _build_messages(instruction: str, source_text: str) -> list[dict[str, str]]:
    return [
        {"role": "system", "content": "你是一个中文写作助手。"},
        {"role": "user", "content": f"改写要求：\n{instruction}\n\n原文：\n{source_text}"},
    ]


async def _sse_from_req(req: RewriteRequest) -> EventSourceResponse:
    base_url, api_key, model = _get_llm_cfg(req.model)

    src_path = _safe_task_file(req.task_id, req.source_file)
    if not os.path.isfile(src_path):
        raise HTTPException(status_code=404, detail="source_file not found")

    try:
        with open(src_path, "r", encoding="utf-8", errors="replace") as f:
            source_text = f.read()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failed to read source_file: {e}")

    messages = _build_messages(req.instruction, source_text)

    async def event_gen() -> AsyncIterator[Dict[str, Any]]:
        yield {"event": "meta", "data": json.dumps({"model": model}, ensure_ascii=False)}
        try:
            async for delta in stream_chat_completions(
                base_url=base_url,
                api_key=api_key,
                model=model,
                messages=messages,
                temperature=req.temperature,
                top_p=req.top_p,
            ):
                yield {"event": "delta", "data": delta}
        except Exception as e:
            yield {"event": "error", "data": str(e)}
            return
        yield {"event": "done", "data": "[DONE]"}

    return EventSourceResponse(event_gen())


@router.post("/rewrite/stream")
async def rewrite_stream(req: RewriteRequest):
    """POST SSE version (useful for fetch-stream clients)."""
    return await _sse_from_req(req)


@router.get("/rewrite/stream_get")
async def rewrite_stream_get(payload: str = Query(..., description="URL-encoded JSON of RewriteRequest")):
    """GET SSE version for EventSource.

    Frontend will pass: ?payload=<encodeURIComponent(JSON.stringify({...}))>
    """
    try:
        obj = json.loads(payload)
        req = RewriteRequest(**obj)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"invalid payload: {e}")

    return await _sse_from_req(req)



def _sanitize_filename(filename: str) -> str:
    # 移除非法字符，替换为空格或下划线
    import re
    # Windows/Linux/Mac 常见的非法字符: \ / : * ? " < > |
    filename = re.sub(r'[\\/:*?"<>|]', '_', filename)
    return filename.strip()

@router.post("/rewrite/save")
def rewrite_save(req: SaveRewriteRequest):
    cfg = load_config()
    custom_output_dir = (cfg.get("rewrite_output_dir") or "").strip()

    if not custom_output_dir:
        # 如果没有指定自定义目录，回退到默认逻辑（任务目录下的 rewrites 子目录）
        task_dir = os.path.abspath(os.path.join(DATA_DIR, req.task_id))
        data_root = os.path.abspath(DATA_DIR)
        if not task_dir.startswith(data_root + os.sep):
            raise HTTPException(status_code=400, detail="Invalid task_id")
        if not os.path.isdir(task_dir):
            raise HTTPException(status_code=404, detail="Task not found")
        task_output_dir = os.path.join(task_dir, "rewrites")
        os.makedirs(task_output_dir, exist_ok=True)
    else:
        # 使用用户指定的存储目录，不创建子目录
        task_output_dir = os.path.abspath(os.path.expanduser(custom_output_dir))
        os.makedirs(task_output_dir, exist_ok=True)

    # 获取视频标题作为文件名
    ctx = get_context(req.task_id)
    title = "rewrite"
    if ctx:
        title = ctx.get("title") or ctx.get("source_title") or "rewrite"
    
    filename = _sanitize_filename(title) + ".md"
    out_path = os.path.join(task_output_dir, filename)

    try:
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(req.content or "")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write file: {e}")

    # 返回相对于存储目录的路径（如果是自定义目录，直接返回文件名）
    return {"file": filename, "path": out_path}
