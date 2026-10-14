import os
import uuid
import shutil
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .models import CreateTaskRequest, CreateTaskResponse, TaskStatusResponse, RenameContextRequest, BatchCreateTaskRequest, BatchCreateTaskResponse
from .tasks import create_task, get_task_status, get_task_file_path, list_task_files, create_batch_tasks
from .contexts import list_contexts, rename_context, delete_context, DATA_DIR
from .config_store import load_config, save_config
from .llm_api import router as llm_router
from .bili_list_api import router as bili_list_router
from .douyin_list_api import router as douyin_list_router

APP_ROOT = os.path.dirname(os.path.dirname(__file__))
FRONTEND_DIR = os.path.join(APP_ROOT, "frontend")

app = FastAPI(title="Bilibili Video Transcriber")

# Routers
app.include_router(llm_router)
app.include_router(bili_list_router)
app.include_router(douyin_list_router)


@app.post("/api/tasks", response_model=CreateTaskResponse)
def api_create_task(req: CreateTaskRequest):
    task_id = str(uuid.uuid4())
    ok = create_task(task_id=task_id, req=req)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to create task")
    return CreateTaskResponse(task_id=task_id)


@app.post("/api/tasks/batch", response_model=BatchCreateTaskResponse)
def api_create_batch_tasks(req: BatchCreateTaskRequest):
    """批量创建任务"""
    if not req.urls:
        raise HTTPException(status_code=400, detail="urls 列表不能为空")

    task_ids = create_batch_tasks(req)
    if not task_ids:
        raise HTTPException(status_code=500, detail="创建任务失败")

    return BatchCreateTaskResponse(task_ids=task_ids, count=len(task_ids))


@app.get("/api/tasks/{task_id}", response_model=TaskStatusResponse)
def api_get_task(task_id: str):
    status = get_task_status(task_id)
    if status is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return status


@app.get("/api/tasks/{task_id}/files")
def api_list_files(task_id: str):
    files = list_task_files(task_id)
    if files is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"files": files}


@app.get("/api/tasks/{task_id}/download")
def api_download(task_id: str, file: str):
    path = get_task_file_path(task_id, file)
    if path is None or not os.path.isfile(path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(path, filename=os.path.basename(path))


@app.get("/api/contexts")
def api_list_contexts():
    return {"items": list_contexts()}


@app.patch("/api/contexts/{task_id}")
def api_rename_context(task_id: str, body: RenameContextRequest):
    try:
        ctx = rename_context(task_id, body.title)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"item": ctx}


@app.delete("/api/contexts/{task_id}")
def api_delete_context(task_id: str):
    delete_context(task_id)

    target_dir = os.path.abspath(os.path.join(DATA_DIR, task_id))
    data_root = os.path.abspath(DATA_DIR)
    if not target_dir.startswith(data_root + os.sep):
        raise HTTPException(status_code=400, detail="Invalid task_id")
    if os.path.isdir(target_dir):
        shutil.rmtree(target_dir)

    return {"ok": True}


@app.post("/api/contexts/{task_id}/open")
def api_open_context_dir(task_id: str):
    target_dir = os.path.abspath(os.path.join(DATA_DIR, task_id))
    data_root = os.path.abspath(DATA_DIR)
    if not target_dir.startswith(data_root + os.sep):
        raise HTTPException(status_code=400, detail="Invalid task_id")
    if not os.path.isdir(target_dir):
        raise HTTPException(status_code=404, detail="Context directory not found")

    import subprocess

    p = subprocess.run(["open", target_dir], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    if p.returncode != 0:
        raise HTTPException(status_code=500, detail=p.stdout)

    return {"ok": True}


@app.get("/api/config")
def api_get_config() -> Dict[str, Any]:
    return load_config()


class UpdateConfigRequest(BaseModel):
    llm: Dict[str, Any] = {}
    rewrite_output_dir: str = ""


@app.put("/api/config")
def api_put_config(body: UpdateConfigRequest) -> Dict[str, Any]:
    cfg = load_config()
    if body.llm and isinstance(body.llm, dict):
        cfg.setdefault("llm", {})
        cfg["llm"].update(body.llm)
    cfg["rewrite_output_dir"] = body.rewrite_output_dir
    return save_config(cfg)


# Serve frontend (mount AFTER API routes; otherwise StaticFiles will swallow /api/* and can return 405)
if os.path.isdir(FRONTEND_DIR):
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
