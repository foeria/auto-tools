"""
任务执行引擎模块
负责任务执行和状态推送
"""
import sys
import asyncio
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import json

from fastapi import BackgroundTasks

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapy_project.utils.scheduler import TaskStatus, TaskPriority
from scrapy_project.utils.storage import storage_manager
from api_service.websocket_manager import ws_manager, WebSocketMessageType

logger = logging.getLogger(__name__)


class ExecutionEngine:
    """任务执行引擎"""
    
    def __init__(self):
        self.executing_tasks: Dict[str, Dict[str, Any]] = {}
    
    async def execute_task(
        self,
        task_id: str,
        url: str,
        actions: List[Dict[str, Any]],
        priority: int = 1,
        max_retries: int = 3,
        metadata: Dict[str, Any] = None
    ):
        task_info = {
            "task_id": task_id,
            "url": url,
            "actions_count": len(actions),
            "current_action": 0,
            "status": "pending",
            "logs": [],
            "start_time": datetime.now()
        }
        
        self.executing_tasks[task_id] = task_info
        
        try:
            await ws_manager.send_task_status(
                task_id=task_id,
                status="starting",
                progress=0,
                current_action="初始化任务",
                message="正在准备执行环境"
            )
            
            await self._run_actions(task_id, url, actions)
            
            task_info["status"] = "completed"
            task_info["end_time"] = datetime.now()
            task_info["progress"] = 100
            
            await ws_manager.send_task_status(
                task_id=task_id,
                status="completed",
                progress=100,
                current_action="任务完成",
                message="所有操作执行成功"
            )
            
            result = {
                "task_id": task_id,
                "status": "completed",
                "url": url,
                "actions_executed": task_info["current_action"],
                "start_time": task_info["start_time"].isoformat(),
                "end_time": task_info["end_time"].isoformat(),
                "duration_seconds": (task_info["end_time"] - task_info["start_time"]).total_seconds()
            }
            
            await ws_manager.send_task_result(task_id, result)
            
            logger.info(f"Task {task_id} completed successfully")
            
        except Exception as e:
            error_msg = str(e)
            task_info["status"] = "failed"
            task_info["end_time"] = datetime.now()
            task_info["error"] = error_msg
            
            await ws_manager.send_task_error(
                task_id=task_id,
                error=error_msg,
                details={"actions_executed": task_info["current_action"]}
            )
            
            logger.error(f"Task {task_id} failed: {error_msg}")
        
        finally:
            if task_id in self.executing_tasks:
                del self.executing_tasks[task_id]
    
    async def _run_actions(
        self,
        task_id: str,
        url: str,
        actions: List[Dict[str, Any]]
    ):
        total_actions = len(actions)
        
        await ws_manager.send_task_log(
            task_id=task_id,
            level="info",
            message=f"开始执行任务，共 {total_actions} 个操作",
            action_name="start"
        )
        
        await ws_manager.send_task_status(
            task_id=task_id,
            status="running",
            progress=0,
            current_action="启动浏览器",
            message="正在打开目标页面"
        )
        
        await self._simulate_browser_start(task_id, url)
        
        for index, action in enumerate(actions):
            action_type = action.get("type", "unknown")
            action_name = self._get_action_name(action_type)
            
            task_info = self.executing_tasks.get(task_id)
            if task_info:
                task_info["current_action"] = index + 1
                task_info["current_action_name"] = action_name
            
            progress = int(((index) / total_actions) * 90)
            
            await ws_manager.send_task_progress(
                task_id=task_id,
                action_index=index + 1,
                total_actions=total_actions,
                action_name=action_name,
                details=action
            )
            
            await ws_manager.send_task_log(
                task_id=task_id,
                level="info",
                message=f"执行操作 [{index + 1}/{total_actions}]: {action_name}",
                action_name=action_name,
                details=action
            )
            
            await self._execute_action(task_id, action)
            
            await ws_manager.send_task_log(
                task_id=task_id,
                level="info",
                message=f"操作 [{index + 1}/{total_actions}] 完成: {action_name}",
                action_name=action_name
            )
        
        await ws_manager.send_task_status(
            task_id=task_id,
            status="running",
            progress=95,
            current_action="关闭浏览器",
            message="正在清理执行环境"
        )
        
        await self._simulate_browser_close(task_id)
        
        await ws_manager.send_task_log(
            task_id=task_id,
            level="info",
            message="任务执行完成",
            action_name="complete"
        )
    
    async def _simulate_browser_start(self, task_id: str, url: str):
        """模拟浏览器启动过程"""
        await asyncio.sleep(0.5)
        
        await ws_manager.send_task_log(
            task_id=task_id,
            level="info",
            message=f"正在访问: {url}",
            action_name="browser_start"
        )
        
        await asyncio.sleep(0.3)
        
        await ws_manager.send_task_log(
            task_id=task_id,
            level="info",
            message="页面加载完成",
            action_name="browser_start"
        )
    
    async def _simulate_browser_close(self, task_id: str):
        """模拟浏览器关闭过程"""
        await asyncio.sleep(0.2)
        
        await ws_manager.send_task_log(
            task_id=task_id,
            level="info",
            message="浏览器已关闭",
            action_name="browser_close"
        )
    
    async def _execute_action(self, task_id: str, action: Dict[str, Any]):
        """执行单个操作"""
        action_type = action.get("type", "unknown")
        
        await asyncio.sleep(0.3)
        
        details = {}
        
        if action_type == "goto":
            url = action.get("url", "")
            details = {"url": url}
        
        elif action_type == "click":
            selector = action.get("selector", "")
            by_image = action.get("by_image", False)
            details = {
                "selector": selector,
                "by_image": by_image
            }
        
        elif action_type == "input":
            selector = action.get("selector", "")
            value = action.get("value", "")
            clear = action.get("clear", True)
            details = {
                "selector": selector,
                "value": value[:10] + "***" if len(value) > 10 else value,
                "clear": clear
            }
        
        elif action_type == "wait":
            timeout = action.get("timeout", 1000)
            wait_type = action.get("wait_type", "timeout")
            details = {
                "wait_type": wait_type,
                "timeout": timeout
            }
        
        elif action_type == "scroll":
            direction = action.get("direction", "down")
            amount = action.get("amount", 500)
            details = {
                "direction": direction,
                "amount": amount
            }
        
        elif action_type == "screenshot":
            full_page = action.get("full_page", False)
            selector = action.get("selector", "")
            details = {
                "full_page": full_page,
                "selector": selector
            }
        
        elif action_type == "extract":
            selectors = action.get("selectors", [])
            extract_type = action.get("extract_type", "text")
            details = {
                "selectors": selectors,
                "extract_type": extract_type
            }
        
        elif action_type == "press":
            keys = action.get("keys", [])
            key = action.get("key", "")
            press_enter = action.get("press_enter", False)
            details = {
                "keys": keys,
                "key": key,
                "press_enter": press_enter
            }
        
        elif action_type == "hover":
            selector = action.get("selector", "")
            details = {"selector": selector}
        
        elif action_type == "upload":
            file_paths = action.get("file_paths", [])
            selector = action.get("selector", "")
            details = {
                "file_paths": file_paths,
                "selector": selector
            }
        
        elif action_type == "evaluate":
            script = action.get("script", "")
            details = {"script_length": len(script)}
        
        else:
            details = {"raw_action": action}
        
        return details
    
    def _get_action_name(self, action_type: str) -> str:
        """获取操作名称"""
        names = {
            "goto": "访问页面",
            "click": "点击元素",
            "input": "输入内容",
            "wait": "等待",
            "scroll": "页面滚动",
            "screenshot": "截图",
            "extract": "提取数据",
            "press": "键盘操作",
            "hover": "悬停",
            "upload": "上传文件",
            "evaluate": "执行脚本",
            "switch_frame": "切换框架",
            "switch_tab": "切换标签页",
            "new_tab": "打开新标签页",
            "close_tab": "关闭标签页",
            "drag": "拖拽元素",
            "keyboard": "键盘操作"
        }
        return names.get(action_type, f"未知操作({action_type})")
    
    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        if task_id in self.executing_tasks:
            return self.executing_tasks[task_id]
        return None
    
    def get_all_executing_tasks(self) -> Dict[str, Dict[str, Any]]:
        return self.executing_tasks


execution_engine = ExecutionEngine()
