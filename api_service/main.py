"""
API服务模块
提供完整的RESTful API，包括任务管理、数据转发、模板管理等
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import uuid
import httpx
import asyncio
from contextlib import asynccontextmanager

from utils.scheduler import TaskPriority, TaskStatus, Task
from utils.storage import storage_manager
from api_service.websocket_manager import ws_manager, WebSocketMessageType
from api_service.execution_engine import execution_engine

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("API服务启动")
    yield
    logger.info("API服务关闭")


app = FastAPI(
    title="智能爬虫API服务",
    description="提供任务管理、数据采集、数据转发等API接口",
    version="1.0.0",
    lifespan=lifespan
)


class TaskCreate(BaseModel):
    url: str = Field(..., description="目标URL")
    actions: List[Dict[str, Any]] = Field(..., description="自动化操作列表")
    extractors: List[Dict[str, Any]] = Field(default=[], description="数据提取器配置")
    priority: int = Field(default=1, ge=0, le=3, description="优先级 0-3")
    max_retries: int = Field(default=3, ge=0, le=10, description="最大重试次数")
    metadata: Dict[str, Any] = Field(default={}, description="元数据")


class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str


class TaskInfo(BaseModel):
    id: str
    url: str
    actions: List[Dict[str, Any]]
    extractors: List[Dict[str, Any]]
    priority: int
    status: str
    result: Optional[Dict[str, Any]]
    error: Optional[str]
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    metadata: Dict[str, Any]


class TaskListResponse(BaseModel):
    total: int
    tasks: List[TaskInfo]


class TaskStatusEnum(str, Enum):
    pending = "pending"
    queued = "queued"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class TemplateCreate(BaseModel):
    name: str
    description: str = ""
    url_pattern: str = ""
    actions: List[Dict[str, Any]]
    extractors: List[Dict[str, Any]] = []


class TemplateResponse(BaseModel):
    id: str
    name: str
    description: str
    url_pattern: str
    actions: List[Dict[str, Any]]
    extractors: List[Dict[str, Any]]
    created_at: datetime


class ForwardRequest(BaseModel):
    data: Dict[str, Any]
    target_url: str
    headers: Dict[str, str] = {}


class ForwardResponse(BaseModel):
    success: bool
    status_code: Optional[int]
    response: Optional[Dict[str, Any]]


class StatisticsResponse(BaseModel):
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    running_tasks: int
    queue_size: int
    total_data_records: int


tasks_db: Dict[str, Task] = {}


@app.websocket("/ws/tasks")
async def websocket_tasks(websocket: WebSocket):
    await ws_manager.connect(websocket)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type")
                
                if msg_type == "subscribe":
                    task_id = message.get("task_id")
                    if task_id:
                        await ws_manager.connect(websocket, task_id)
                
                elif msg_type == "unsubscribe":
                    task_id = message.get("task_id")
                    if task_id:
                        ws_manager.disconnect(websocket, task_id)
                
                elif msg_type == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}))
                
            except json.JSONDecodeError:
                pass
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("WebSocket客户端断开连接")


@app.websocket("/ws/tasks/{task_id}")
async def websocket_task_detail(websocket: WebSocket, task_id: str):
    await ws_manager.connect(websocket, task_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                if message.get("type") == "ping":
                    await websocket.send_text(json.dumps({"type": "pong", "timestamp": datetime.now().isoformat()}))
            except json.JSONDecodeError:
                pass
    
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket, task_id)
        logger.info(f"WebSocket客户端断开连接: task_id={task_id}")


@app.post("/api/tasks", response_model=TaskResponse, tags=["任务管理"])
async def create_task(task_data: TaskCreate, background_tasks: BackgroundTasks):
    task_id = str(uuid.uuid4())
    
    task = Task(
        task_id=task_id,
        url=task_data.url,
        actions=task_data.actions,
        priority=TaskPriority(task_data.priority),
        max_retries=task_data.max_retries,
        metadata=task_data.metadata
    )
    
    tasks_db[task_id] = task
    
    background_tasks.add_task(
        execution_engine.execute_task,
        task_id=task_id,
        url=task_data.url,
        actions=task_data.actions,
        priority=task_data.priority,
        max_retries=task_data.max_retries,
        metadata=task_data.metadata
    )
    
    storage_manager.save_task_with_queue(task.to_dict(), task_data.priority)
    
    logger.info(f"Task created: {task_id}")
    
    return TaskResponse(
        task_id=task_id,
        status="created",
        message="任务已创建，正在执行"
    )


@app.get("/api/tasks", response_model=TaskListResponse, tags=["任务管理"])
async def list_tasks(
    status: Optional[TaskStatusEnum] = None,
    limit: int = 100,
    offset: int = 0
):
    all_tasks = list(tasks_db.values())
    
    if status:
        all_tasks = [t for t in all_tasks if t.status.value == status.value]
    
    total = len(all_tasks)
    tasks_paginated = all_tasks[offset:offset + limit]
    
    return TaskListResponse(
        total=total,
        tasks=[
            TaskInfo(
                id=t.id,
                url=t.url,
                actions=t.actions,
                extractors=[],
                priority=t.priority.value,
                status=t.status.value,
                result=t.result,
                error=t.error,
                created_at=t.created_at,
                started_at=t.started_at,
                completed_at=t.completed_at,
                metadata=t.metadata
            )
            for t in tasks_paginated
        ]
    )


@app.get("/api/tasks/{task_id}", response_model=TaskInfo, tags=["任务管理"])
async def get_task(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks_db[task_id]
    
    return TaskInfo(
        id=task.id,
        url=task.url,
        actions=task.actions,
        extractors=[],
        priority=task.priority.value,
        status=task.status.value,
        result=task.result,
        error=task.error,
        created_at=task.created_at,
        started_at=task.started_at,
        completed_at=task.completed_at,
        metadata=task.metadata
    )


@app.get("/api/tasks/{task_id}/status", tags=["任务管理"])
async def get_task_status(task_id: str):
    task_info = execution_engine.get_task_status(task_id)
    
    if task_info:
        return {
            "task_id": task_id,
            "status": "running",
            "executing": task_info
        }
    
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks_db[task_id]
    return {
        "task_id": task_id,
        "status": task.status.value,
        "executing": None
    }


@app.delete("/api/tasks/{task_id}", tags=["任务管理"])
async def delete_task(task_id: str):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks_db[task_id]
    task.status = TaskStatus.CANCELLED
    
    del tasks_db[task_id]
    
    return {"message": "任务已删除"}


@app.post("/api/tasks/{task_id}/retry", response_model=TaskResponse, tags=["任务管理"])
async def retry_task(task_id: str, background_tasks: BackgroundTasks):
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks_db[task_id]
    
    task.status = TaskStatus.PENDING
    task.error = None
    task.current_retry = 0
    
    background_tasks.add_task(
        execution_engine.execute_task,
        task_id=task_id,
        url=task.url,
        actions=task.actions,
        priority=task.priority.value,
        max_retries=task.max_retries,
        metadata=task.metadata
    )
    
    storage_manager.save_task_with_queue(task.to_dict(), task.priority.value)
    
    return TaskResponse(
        task_id=task_id,
        status="retry",
        message="任务已重新入队执行"
    )


@app.post("/api/tasks/{task_id}/cancel", tags=["任务管理"])
async def cancel_task(task_id: str):
    task_info = execution_engine.get_task_status(task_id)
    
    if task_info:
        task_info["status"] = "cancelled"
        del execution_engine.executing_tasks[task_id]
    
    if task_id not in tasks_db:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    task = tasks_db[task_id]
    task.status = TaskStatus.CANCELLED
    
    await ws_manager.send_task_status(
        task_id=task_id,
        status="cancelled",
        progress=0,
        current_action="任务已取消",
        message="用户取消任务执行"
    )
    
    return {"message": "任务已取消"}


@app.get("/api/templates", response_model=List[TemplateResponse], tags=["模板管理"])
async def list_templates():
    templates = storage_manager.mongo.list_templates()
    
    return [
        TemplateResponse(
            id=t['id'],
            name=t['name'],
            description=t.get('description', ''),
            url_pattern=t.get('url_pattern', ''),
            actions=t['actions'],
            extractors=t.get('extractors', []),
            created_at=datetime.fromisoformat(t['created_at']) if isinstance(t.get('created_at'), str) else t.get('created_at', datetime.now())
        )
        for t in templates
    ]


@app.post("/api/templates", response_model=TemplateResponse, tags=["模板管理"])
async def create_template(template_data: TemplateCreate):
    template_id = str(uuid.uuid4())
    
    template = {
        'id': template_id,
        'name': template_data.name,
        'description': template_data.description,
        'url_pattern': template_data.url_pattern,
        'actions': template_data.actions,
        'extractors': template_data.extractors,
        'created_at': datetime.now()
    }
    
    storage_manager.mongo.save_template(template)
    
    return TemplateResponse(
        id=template_id,
        name=template_data.name,
        description=template_data.description,
        url_pattern=template_data.url_pattern,
        actions=template_data.actions,
        extractors=template_data.extractors,
        created_at=template['created_at']
    )


@app.delete("/api/templates/{template_id}", tags=["模板管理"])
async def delete_template(template_id: str):
    success = storage_manager.mongo.delete_template(template_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="模板不存在")
    
    return {"message": "模板已删除"}


@app.post("/api/forward", response_model=ForwardResponse, tags=["数据转发"])
async def forward_data(forward_request: ForwardRequest):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                forward_request.target_url,
                json=forward_request.data,
                headers=forward_request.headers,
                timeout=30.0
            )
            
            return ForwardResponse(
                success=response.status_code < 400,
                status_code=response.status_code,
                response=response.json() if response.status_code < 400 else None
            )
            
    except httpx.TimeoutException:
        raise HTTPException(status_code=408, detail="转发超时")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"转发失败: {str(e)}")


@app.get("/api/statistics", response_model=StatisticsResponse, tags=["监控"])
async def get_statistics():
    stats = storage_manager.get_statistics()
    
    return StatisticsResponse(
        total_tasks=stats.get('total_tasks', 0),
        completed_tasks=stats.get('completed_tasks', 0),
        failed_tasks=stats.get('failed_tasks', 0),
        running_tasks=stats.get('running_tasks', 0),
        queue_size=stats.get('queue_size', 0),
        total_data_records=stats.get('total_data_records', 0)
    )


@app.get("/api/executing-tasks", tags=["监控"])
async def get_executing_tasks():
    return {
        "count": len(execution_engine.executing_tasks),
        "tasks": execution_engine.get_all_executing_tasks()
    }


@app.get("/api/actions", tags=["系统信息"])
async def get_available_actions():
    return {
        "actions": [
            {"type": "goto", "name": "访问页面", "icon": "Location"},
            {"type": "click", "name": "点击元素", "icon": "Pointer"},
            {"type": "input", "name": "输入内容", "icon": "Edit"},
            {"type": "wait", "name": "等待", "icon": "Clock"},
            {"type": "scroll", "name": "页面滚动", "icon": "Bottom"},
            {"type": "screenshot", "name": "截图", "icon": "Picture"},
            {"type": "extract", "name": "提取数据", "icon": "Document"},
            {"type": "press", "name": "键盘操作", "icon": "Keyboard"},
            {"type": "hover", "name": "悬停", "icon": "Pointer"},
            {"type": "upload", "name": "上传文件", "icon": "Upload"},
            {"type": "evaluate", "name": "执行脚本", "icon": "Code"},
            {"type": "switch_frame", "name": "切换框架", "icon": "Menu"},
            {"type": "switch_tab", "name": "切换标签页", "icon": "CopyDocument"},
            {"type": "new_tab", "name": "打开新标签页", "icon": "DocumentAdd"},
            {"type": "close_tab", "name": "关闭标签页", "icon": "Remove"},
            {"type": "drag", "name": "拖拽", "icon": "Rank"}
        ]
    }


@app.get("/health", tags=["监控"])
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.now(),
        "version": "1.0.0",
        "executing_tasks": len(execution_engine.executing_tasks),
        "total_tasks": len(tasks_db)
    }


import json
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
