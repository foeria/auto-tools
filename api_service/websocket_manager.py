"""
WebSocket服务模块
提供任务状态实时推送功能
"""
from typing import Dict, Set, Any
from datetime import datetime
import json
import logging
from enum import Enum

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class WebSocketMessageType(str, Enum):
    """WebSocket消息类型"""
    TASK_STATUS = "task_status"
    TASK_PROGRESS = "task_progress"
    TASK_LOG = "task_log"
    TASK_RESULT = "task_result"
    TASK_ERROR = "task_error"
    TASK_SCREENSHOT = "task_screenshot"  # 实时截图
    CONNECT = "connect"
    DISCONNECT = "disconnect"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"
    PONG = "pong"


class WebSocketMessage:
    """WebSocket消息"""
    
    def __init__(self, type: WebSocketMessageType, payload: Dict[str, Any], task_id: str = None):
        self.type = type.value if isinstance(type, WebSocketMessageType) else type
        self.payload = payload
        self.task_id = task_id
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.type,
            "payload": self.payload,
            "task_id": self.task_id,
            "timestamp": self.timestamp
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)


class ConnectionManager:
    """WebSocket连接管理器"""
    
    def __init__(self):
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self.global_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket, task_id: str = None):
        try:
            await websocket.accept()
        except RuntimeError as e:
            logger.warning(f"WebSocket already connected or closed: {e}")
            return

        if task_id:
            if task_id not in self.active_connections:
                self.active_connections[task_id] = set()
            self.active_connections[task_id].add(websocket)
            logger.info(f"Client connected to task: {task_id}")
        else:
            self.global_connections.add(websocket)
            logger.info("Client connected to global channel")
    
    def disconnect(self, websocket: WebSocket, task_id: str = None):
        if task_id and task_id in self.active_connections:
            self.active_connections[task_id].discard(websocket)
            if not self.active_connections[task_id]:
                del self.active_connections[task_id]
        else:
            self.global_connections.discard(websocket)
    
    async def send_message(self, websocket: WebSocket, message: WebSocketMessage):
        try:
            # 检查连接是否仍然有效
            if websocket.client.state != 2:  # WebSocketState.CONNECTED
                return
            await websocket.send_text(message.to_json())
        except Exception as e:
            logger.debug(f"Failed to send message (connection may be closed): {e}")
    
    async def broadcast(self, message: WebSocketMessage, task_id: str = None):
        connections = set()
        
        if task_id and task_id in self.active_connections:
            connections = self.active_connections[task_id]
        
        connections.update(self.global_connections)
        
        for connection in connections:
            await self.send_message(connection, message)
    
    async def send_task_status(
        self,
        task_id: str,
        status: str,
        progress: int = 0,
        current_action: str = None,
        message: str = None
    ):
        payload = {
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "current_action": current_action,
            "message": message
        }
        
        await self.broadcast(
            WebSocketMessage(
                type=WebSocketMessageType.TASK_STATUS,
                payload=payload,
                task_id=task_id
            ),
            task_id
        )
    
    async def send_task_progress(
        self,
        task_id: str,
        action_index: int,
        total_actions: int,
        action_name: str,
        details: Dict[str, Any] = None
    ):
        progress = int((action_index / total_actions) * 100) if total_actions > 0 else 0
        
        payload = {
            "task_id": task_id,
            "action_index": action_index,
            "total_actions": total_actions,
            "progress": progress,
            "action_name": action_name,
            "details": details or {}
        }
        
        await self.broadcast(
            WebSocketMessage(
                type=WebSocketMessageType.TASK_PROGRESS,
                payload=payload,
                task_id=task_id
            ),
            task_id
        )
    
    async def send_task_log(
        self,
        task_id: str,
        level: str,
        message: str,
        action_name: str = None,
        details: Dict[str, Any] = None
    ):
        payload = {
            "task_id": task_id,
            "level": level,
            "message": message,
            "action_name": action_name,
            "details": details or {}
        }
        
        await self.broadcast(
            WebSocketMessage(
                type=WebSocketMessageType.TASK_LOG,
                payload=payload,
                task_id=task_id
            ),
            task_id
        )
    
    async def send_task_result(self, task_id: str, result: Dict[str, Any]):
        payload = {
            "task_id": task_id,
            "result": result
        }
        
        await self.broadcast(
            WebSocketMessage(
                type=WebSocketMessageType.TASK_RESULT,
                payload=payload,
                task_id=task_id
            ),
            task_id
        )
    
    async def send_task_error(self, task_id: str, error: str, details: Dict[str, Any] = None):
        payload = {
            "task_id": task_id,
            "error": error,
            "details": details or {}
        }
        
        await self.broadcast(
            WebSocketMessage(
                type=WebSocketMessageType.TASK_ERROR,
                payload=payload,
                task_id=task_id
            ),
            task_id
        )
    
    async def send_task_screenshot(self, task_id: str, screenshot_data: str, action_index: int = 0):
        """发送实时截图"""
        payload = {
            "task_id": task_id,
            "screenshot": screenshot_data,  # base64编码的图片数据
            "action_index": action_index,
            "timestamp": datetime.now().isoformat()
        }

        await self.broadcast(
            WebSocketMessage(
                type=WebSocketMessageType.TASK_SCREENSHOT,
                payload=payload,
                task_id=task_id
            ),
            task_id
        )

    def get_connection_count(self, task_id: str = None) -> int:
        if task_id and task_id in self.active_connections:
            return len(self.active_connections[task_id])
        return len(self.global_connections)


ws_manager = ConnectionManager()
