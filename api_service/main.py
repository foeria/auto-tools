"""
API服务模块
提供完整的RESTful API，包括任务管理、数据转发、模板管理等
"""
import sys
import os
import json
import logging
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from enum import Enum
from datetime import datetime
import uuid
import httpx
import asyncio
from contextlib import asynccontextmanager

from scrapy_project.utils.scheduler import TaskPriority, TaskStatus, Task
from scrapy_project.utils.storage import storage_manager
from api_service.websocket_manager import ws_manager, WebSocketMessageType
from api_service.execution_engine import execution_engine
from api_service.config import get_config, setup_logging
from api_service.errors import ErrorCode, ErrorHandler, ErrorDetail

# 加载配置
config = get_config()
setup_logging(config)

logger = logging.getLogger(__name__)


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

# 添加CORS中间件 (使用配置)
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.api.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskCreate(BaseModel):
    url: str = Field(..., description="目标URL")
    actions: List[Dict[str, Any]] = Field(..., description="自动化操作列表")
    extractors: List[Dict[str, Any]] = Field(default=[], description="数据提取器配置")
    priority: int = Field(default=1, ge=0, le=3, description="优先级 0-3")
    max_retries: int = Field(default=3, ge=0, le=10, description="最大重试次数")
    metadata: Dict[str, Any] = Field(default={}, description="元数据")
    headless: bool = Field(default=False, description="是否使用无头模式运行浏览器")
    browser_config: Optional[Dict[str, Any]] = Field(default=None, description="浏览器反检测配置")


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


class BatchTaskCreate(BaseModel):
    tasks: List[TaskCreate] = Field(..., min_length=1, max_length=50, description="任务列表，最多为50个")
    max_retries: int = Field(default=3, ge=0, le=10, description="默认最大重试次数")


class BatchTaskDelete(BaseModel):
    task_ids: List[str] = Field(..., min_length=1, max_length=100, description="任务ID列表，最多为100个")


class BatchTaskCancel(BaseModel):
    task_ids: List[str] = Field(..., min_length=1, max_length=100, description="任务ID列表，最多为100个")


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
        metadata=task_data.metadata,
        headless=task_data.headless,
        browser_config=task_data.browser_config
    )

    storage_manager.save_task_with_queue(task.to_dict(), task_data.priority)

    logger.info(f"Task created: {task_id} (headless={task_data.headless})")

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
        error = ErrorHandler.create_task_error(
            task_id=task_id,
            error_code=ErrorCode.ERR_TASK_NOT_FOUND,
            message="任务不存在",
            reason=f"任务ID: {task_id}",
            suggestion="请检查任务ID是否正确"
        )
        raise HTTPException(status_code=404, detail=error)

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
        error = ErrorHandler.create_task_error(
            task_id=task_id,
            error_code=ErrorCode.ERR_TASK_NOT_FOUND,
            message="任务不存在",
            reason=f"任务ID: {task_id}",
            suggestion="请检查任务ID是否正确"
        )
        raise HTTPException(status_code=404, detail=error)

    task = tasks_db[task_id]
    return {
        "task_id": task_id,
        "status": task.status.value,
        "executing": None
    }


@app.delete("/api/tasks/{task_id}", tags=["任务管理"])
async def delete_task(task_id: str):
    # 检查任务是否在待执行队列中
    if task_id in tasks_db:
        task = tasks_db[task_id]
        task.status = TaskStatus.CANCELLED
        del tasks_db[task_id]
        return {"message": "任务已从队列中删除"}

    # 检查任务是否正在执行
    from api_service.execution_engine import execution_engine
    if task_id in execution_engine.executing_tasks:
        # 标记任务为已取消，执行引擎会在下一次检查时停止
        execution_engine.executing_tasks[task_id]["status"] = "cancelled"
        return {"message": "任务正在取消中"}

    # 任务不存在
    error = ErrorHandler.create_task_error(
        task_id=task_id,
        error_code=ErrorCode.ERR_TASK_NOT_FOUND,
        message="任务不存在",
        reason=f"任务ID: {task_id}",
        suggestion="请检查任务ID是否正确"
    )
    raise HTTPException(status_code=404, detail=error)


@app.post("/api/tasks/{task_id}/retry", response_model=TaskResponse, tags=["任务管理"])
async def retry_task(task_id: str, background_tasks: BackgroundTasks):
    if task_id not in tasks_db:
        error = ErrorHandler.create_task_error(
            task_id=task_id,
            error_code=ErrorCode.ERR_TASK_NOT_FOUND,
            message="任务不存在",
            reason=f"任务ID: {task_id}",
            suggestion="请检查任务ID是否正确"
        )
        raise HTTPException(status_code=404, detail=error)

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
    """取消正在运行的任务"""
    # 发送取消中状态
    await ws_manager.send_task_status(
        task_id=task_id,
        status="cancelling",
        progress=0,
        current_action="正在取消",
        message="正在取消任务..."
    )

    # 首先关闭浏览器（如果正在运行）
    if task_id in execution_engine.browser_contexts:
        try:
            browser = execution_engine.browser_contexts[task_id]
            # browser_contexts 存储的是 SubprocessBrowser 对象
            if hasattr(browser, 'close'):
                await browser.close()
            logger.info(f"Browser closed for cancelled task: {task_id}")
        except Exception as e:
            logger.error(f"Error closing browser during cancel: {e}")

    # 设置任务状态为已取消
    task_info = execution_engine.get_task_status(task_id)

    if task_info:
        task_info["status"] = "cancelled"

    # 从执行任务中移除（这会触发CancelledError）
    if task_id in execution_engine.executing_tasks:
        del execution_engine.executing_tasks[task_id]

    # 从浏览器上下文中移除
    if task_id in execution_engine.browser_contexts:
        del execution_engine.browser_contexts[task_id]

    if task_id not in tasks_db:
        await ws_manager.send_task_status(
            task_id=task_id,
            status="cancelled",
            progress=0,
            current_action="任务已取消",
            message="任务已取消执行"
        )
        return {"message": "任务已取消"}

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


@app.post("/api/tasks/batch", tags=["任务管理"])
async def create_tasks_batch(request: BatchTaskCreate):
    """批量创建任务"""
    created_tasks = []
    errors = []

    for i, task_data in enumerate(request.tasks):
        try:
            task_id = str(uuid.uuid4())
            task = Task(
                id=task_id,
                url=task_data.url,
                actions=task_data.actions,
                extractors=task_data.extractors or [],
                priority=task_data.priority or 0,
                max_retries=request.max_retries or 3,
                metadata=task_data.metadata or {}
            )
            task_id = storage_manager.save_task_with_queue(task.to_dict(), task.priority.value)
            created_tasks.append({
                "task_id": task_id,
                "url": task.url,
                "status": "pending"
            })
        except Exception as e:
            errors.append({
                "index": i,
                "error": str(e)
            })

    return {
        "created": created_tasks,
        "errors": errors,
        "total_created": len(created_tasks),
        "total_errors": len(errors)
    }


@app.delete("/api/tasks/batch", tags=["任务管理"])
async def delete_tasks_batch(request: BatchTaskDelete):
    """批量删除任务"""
    deleted = []
    errors = []

    for task_id in request.task_ids:
        try:
            if task_id in tasks_db:
                del tasks_db[task_id]
            if task_id in execution_engine.executing_tasks:
                del execution_engine.executing_tasks[task_id]
            if task_id in execution_engine.browser_contexts:
                try:
                    browser = execution_engine.browser_contexts[task_id]
                    if hasattr(browser, 'close'):
                        await browser.close()
                    del execution_engine.browser_contexts[task_id]
                except Exception as e:
                    logger.error(f"Error closing browser during batch delete: {e}")

            deleted.append(task_id)
        except Exception as e:
            errors.append({
                "task_id": task_id,
                "error": str(e)
            })

    return {
        "deleted": deleted,
        "errors": errors,
        "total_deleted": len(deleted),
        "total_errors": len(errors)
    }


@app.post("/api/tasks/batch/cancel", tags=["任务管理"])
async def cancel_tasks_batch(request: BatchTaskCancel):
    """批量取消任务"""
    cancelled = []
    errors = []

    for task_id in request.task_ids:
        try:
            if task_id not in tasks_db:
                errors.append({"task_id": task_id, "error": "任务不存在"})
                continue

            task = tasks_db[task_id]
            if task.status in [TaskStatus.COMPLETED, TaskStatus.CANCELLED]:
                errors.append({"task_id": task_id, "error": f"任务状态为 {task.status.value}，无法取消"})
                continue

            # 发送取消中状态
            await ws_manager.send_task_status(
                task_id=task_id,
                status="cancelling",
                progress=0,
                current_action="正在取消",
                message="正在批量取消任务..."
            )

            # 关闭浏览器
            if task_id in execution_engine.browser_contexts:
                try:
                    browser = execution_engine.browser_contexts[task_id]
                    if hasattr(browser, 'close'):
                        await browser.close()
                    del execution_engine.browser_contexts[task_id]
                except Exception as e:
                    logger.error(f"Error closing browser during batch cancel: {e}")

            task.status = TaskStatus.CANCELLED
            await ws_manager.send_task_status(
                task_id=task_id,
                status="cancelled",
                progress=0,
                current_action="任务已取消",
                message="任务已取消执行"
            )

            cancelled.append(task_id)
        except Exception as e:
            errors.append({"task_id": task_id, "error": str(e)})

    return {
        "cancelled": cancelled,
        "errors": errors,
        "total_cancelled": len(cancelled),
        "total_errors": len(errors)
    }


@app.get("/api/templates", response_model=List[TemplateResponse], tags=["模板管理"])
async def list_templates():
    templates = storage_manager.db.list_templates()

    return [
        TemplateResponse(
            id=t['id'],
            name=t['name'],
            description=t.get('description', ''),
            url_pattern=t.get('url_pattern', ''),
            actions=json.loads(t['actions']) if isinstance(t.get('actions'), str) else t.get('actions', []),
            extractors=json.loads(t['extractors']) if isinstance(t.get('extractors'), str) else t.get('extractors', []),
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

    storage_manager.db.save_template(template)

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
    success = storage_manager.db.delete_template(template_id)

    if not success:
        error = {
            "error_code": ErrorCode.ERR_TASK_NOT_FOUND.value,
            "message": "模板不存在",
            "reason": f"模板ID: {template_id}",
            "suggestion": "请检查模板ID是否正确"
        }
        raise HTTPException(status_code=404, detail=error)

    return {"message": "模板已删除"}


# ============ 工作流API ============

class WorkflowCreate(BaseModel):
    id: Optional[str] = None
    name: str
    description: str = ""
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]] = []
    actions: List[Dict[str, Any]] = []
    url_pattern: str = ""


class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: str
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    actions: List[Dict[str, Any]]
    url_pattern: str
    created_at: str
    updated_at: str


@app.get("/api/workflows", tags=["工作流管理"])
async def list_workflows():
    """列出所有工作流"""
    workflows = storage_manager.db.list_workflows()
    return {
        "success": True,
        "data": workflows,
        "total": len(workflows)
    }


@app.get("/api/workflows/{workflow_id}", tags=["工作流管理"])
async def get_workflow(workflow_id: str):
    """获取工作流详情"""
    workflow = storage_manager.db.get_workflow(workflow_id)

    if not workflow:
        error = {
            "error_code": ErrorCode.ERR_TASK_NOT_FOUND.value,
            "message": "工作流不存在",
            "reason": f"工作流ID: {workflow_id}",
            "suggestion": "请检查工作流ID是否正确"
        }
        raise HTTPException(status_code=404, detail=error)

    return {
        "success": True,
        "data": workflow
    }


@app.post("/api/workflows", response_model=Dict, tags=["工作流管理"])
async def create_workflow(workflow_data: WorkflowCreate):
    """创建或更新工作流"""
    workflow_id = workflow_data.id if workflow_data.id else str(uuid.uuid4())

    workflow = {
        'id': workflow_id,
        'name': workflow_data.name,
        'description': workflow_data.description,
        'nodes': workflow_data.nodes,
        'edges': workflow_data.edges,
        'actions': workflow_data.actions,
        'url_pattern': workflow_data.url_pattern,
        'created_at': datetime.now().isoformat()
    }

    storage_manager.db.save_workflow(workflow)

    logger.info(f"Workflow created/updated: {workflow_id}")

    return {
        "success": True,
        "data": {
            "id": workflow_id,
            "name": workflow_data.name,
            "message": "工作流保存成功"
        }
    }


@app.put("/api/workflows/{workflow_id}", response_model=Dict, tags=["工作流管理"])
async def update_workflow(workflow_id: str, workflow_data: WorkflowCreate):
    """更新工作流"""
    # 检查是否存在
    existing = storage_manager.db.get_workflow(workflow_id)
    if not existing:
        error = {
            "error_code": ErrorCode.ERR_TASK_NOT_FOUND.value,
            "message": "工作流不存在",
            "reason": f"工作流ID: {workflow_id}",
            "suggestion": "请检查工作流ID是否正确"
        }
        raise HTTPException(status_code=404, detail=error)

    workflow = {
        'id': workflow_id,
        'name': workflow_data.name,
        'description': workflow_data.description,
        'nodes': workflow_data.nodes,
        'edges': workflow_data.edges,
        'actions': workflow_data.actions,
        'url_pattern': workflow_data.url_pattern,
        'created_at': existing.get('created_at', datetime.now().isoformat())
    }

    storage_manager.db.save_workflow(workflow)

    return {
        "success": True,
        "data": {
            "id": workflow_id,
            "name": workflow_data.name,
            "message": "工作流更新成功"
        }
    }


@app.delete("/api/workflows/{workflow_id}", tags=["工作流管理"])
async def delete_workflow(workflow_id: str):
    """删除工作流"""
    success = storage_manager.db.delete_workflow(workflow_id)

    if not success:
        error = {
            "error_code": ErrorCode.ERR_TASK_NOT_FOUND.value,
            "message": "工作流不存在",
            "reason": f"工作流ID: {workflow_id}",
            "suggestion": "请检查工作流ID是否正确"
        }
        raise HTTPException(status_code=404, detail=error)

    return {"success": True, "message": "工作流已删除"}


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
        error = {
            "error_code": ErrorCode.ERR_SYS_WEBSOCKET.value,
            "message": "数据转发超时",
            "reason": "目标服务器响应超时",
            "suggestion": "请检查目标服务器是否可访问，或增加超时时间"
        }
        raise HTTPException(status_code=408, detail=error)
    except Exception as e:
        error = {
            "error_code": ErrorCode.ERR_SYS_WEBSOCKET.value,
            "message": "数据转发失败",
            "reason": str(e),
            "suggestion": "请检查目标URL和网络连接"
        }
        raise HTTPException(status_code=500, detail=error)


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


@app.get("/api/task-history", tags=["任务历史"])
async def get_task_history(
    start_date: str = None,
    end_date: str = None,
    status: str = None,
    limit: int = 100,
    offset: int = 0
):
    """获取任务执行历史记录"""
    try:
        # 从数据库获取历史记录
        history = storage_manager.db.list_task_history(
            start_date=start_date,
            end_date=end_date,
            status=status,
            limit=limit,
            offset=offset
        )

        # 增强历史数据（添加计算字段）
        enhanced_history = []
        for task in history:
            # 计算执行时长
            duration = None
            if task.get('started_at') and task.get('completed_at'):
                try:
                    start = datetime.fromisoformat(task['started_at'])
                    end = datetime.fromisoformat(task['completed_at'])
                    duration = (end - start).total_seconds()
                except Exception:
                    duration = None

            enhanced_history.append({
                **task,
                'duration': duration,
                'success_count': len([a for a in task.get('actions', []) if a.get('status') == 'success']),
                'failed_count': len([a for a in task.get('actions', []) if a.get('status') == 'failed']),
                'avg_step_duration': duration / len(task.get('actions', [])) if duration and task.get('actions') else None
            })

        return {
            "success": True,
            "data": enhanced_history,
            "total": len(history),
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"获取任务历史失败: {e}")
        return {
            "success": False,
            "data": [],
            "error": str(e)
        }


@app.get("/api/task-history/statistics", tags=["任务历史"])
async def get_history_statistics(
    start_date: str = None,
    end_date: str = None
):
    """获取任务历史统计数据"""
    try:
        history = storage_manager.db.list_task_history(
            start_date=start_date,
            end_date=end_date,
            limit=10000  # 获取全部用于统计
        )

        completed = [t for t in history if t.get('status') == 'completed']
        failed = [t for t in history if t.get('status') == 'failed']
        cancelled = [t for t in history if t.get('status') == 'cancelled']

        # 计算平均执行时长
        durations = []
        for task in completed:
            if task.get('started_at') and task.get('completed_at'):
                try:
                    start = datetime.fromisoparse(task['started_at'])
                    end = datetime.fromisoformat(task['completed_at'])
                    durations.append((end - start).total_seconds())
                except Exception:
                    pass

        avg_duration = sum(durations) / len(durations) if durations else 0

        return {
            "success": True,
            "data": {
                "total_tasks": len(history),
                "completed_tasks": len(completed),
                "failed_tasks": len(failed),
                "cancelled_tasks": len(cancelled),
                "success_rate": len(completed) / len(history) * 100 if history else 0,
                "avg_duration": avg_duration
            }
        }
    except Exception as e:
        logger.error(f"获取历史统计失败: {e}")
        return {
            "success": False,
            "data": {
                "total_tasks": 0,
                "completed_tasks": 0,
                "failed_tasks": 0,
                "cancelled_tasks": 0,
                "success_rate": 0,
                "avg_duration": 0
            },
            "error": str(e)
        }


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
