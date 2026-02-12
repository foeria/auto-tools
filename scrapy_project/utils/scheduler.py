"""
任务调度器模块
负责任务队列管理、优先级调度、任务执行控制
"""
from typing import Any, Dict, List, Optional, Callable
from datetime import datetime
from enum import Enum
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

logger = logging.getLogger(__name__)


class TaskPriority(int, Enum):
    """任务优先级"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class TaskStatus(str, Enum):
    """任务状态"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task:
    """任务类"""

    def __init__(self, task_id: str, url: str, actions: List[Dict[str, Any]],
                 priority: TaskPriority = TaskPriority.NORMAL,
                 max_retries: int = 3,
                 callback: Callable = None,
                 error_callback: Callable = None,
                 metadata: Dict[str, Any] = None):
        self.id = task_id
        self.url = url
        self.actions = actions
        self.priority = priority
        self.max_retries = max_retries
        self.current_retry = 0
        self.status = TaskStatus.PENDING
        self.result = None
        self.error = None
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.callback = callback
        self.error_callback = error_callback
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'url': self.url,
            'actions': self.actions,
            'priority': self.priority.value,
            'status': self.status.value,
            'result': self.result,
            'error': self.error,
            'created_at': self.created_at.isoformat(),
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Task':
        task = cls(
            task_id=data['id'],
            url=data['url'],
            actions=data['actions'],
            priority=TaskPriority(data.get('priority', 1)),
            max_retries=data.get('max_retries', 3)
        )
        task.status = TaskStatus(data.get('status', 'pending'))
        task.result = data.get('result')
        task.error = data.get('error')
        task.metadata = data.get('metadata', {})
        if data.get('created_at'):
            task.created_at = datetime.fromisoformat(data['created_at'])
        return task


class TaskScheduler:
    """任务调度器"""
    
    def __init__(self, max_concurrent: int = 4, max_retries: int = 3):
        self.pending_tasks: Dict[str, Task] = {}
        self.running_tasks: Dict[str, Task] = {}
        self.completed_tasks: Dict[str, Task] = {}
        self.failed_tasks: Dict[str, Task] = {}
        
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        
        self.executor = ThreadPoolExecutor(max_workers=max_concurrent)
        
        self.running = False
        self._loop = None
    
    def add_task(self, task: Task):
        """添加任务到队列"""
        self.pending_tasks[task.id] = task
        logger.info(f"Task {task.id} added to queue with priority {task.priority}")
    
    def add_tasks_batch(self, tasks: List[Task]):
        """批量添加任务"""
        for task in tasks:
            task.max_retries = self.max_retries
            self.add_task(task)
    
    def get_next_task(self) -> Optional[Task]:
        """获取下一个最高优先级的任务"""
        if not self.pending_tasks:
            return None
        
        pending_ids = list(self.pending_tasks.keys())
        
        highest_priority = max(
            self.pending_tasks[tid].priority.value 
            for tid in pending_ids
        )
        
        task_ids = [
            tid for tid in pending_ids 
            if self.pending_tasks[tid].priority.value == highest_priority
        ]
        
        task_id = task_ids[0]
        task = self.pending_tasks.pop(task_id)
        
        return task
    
    def run_task(self, task: Task) -> bool:
        """执行任务"""
        if len(self.running_tasks) >= self.max_concurrent:
            return False
        
        if task.id in self.running_tasks:
            return False
        
        self.running_tasks[task.id] = task
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now()
        
        logger.info(f"Starting task {task.id}")
        
        future = self.executor.submit(self._execute_task, task)
        future.add_done_callback(
            lambda f: self._on_task_complete(task.id, f)
        )
        
        return True
    
    def _execute_task(self, task: Task):
        """任务执行逻辑"""
        try:
            from spiders.automation_spider import AutomationSpider
            from scrapy.crawler import CrawlerRunner
            from twisted.internet import defer
            
            runner = CrawlerRunner()
            
            d = runner.crawl(
                AutomationSpider,
                actions=task.actions
            )
            
            def _callback(results):
                task.result = results
                task.status = TaskStatus.COMPLETED
                task.completed_at = datetime.now()
                if task.callback:
                    task.callback(task)
                return results
            
            def _errback(failure):
                task.error = str(failure.value)
                task.current_retry += 1
                
                if task.current_retry < task.max_retries:
                    task.status = TaskStatus.QUEUED
                    self.pending_tasks[task.id] = task
                    logger.warning(f"Task {task.id} failed, retry {task.current_retry}/{task.max_retries}")
                else:
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now()
                    if task.error_callback:
                        task.error_callback(task)
                    logger.error(f"Task {task.id} failed after {task.max_retries} retries")
                
                return failure
            
            d.addCallback(_callback)
            d.addErrback(_errback)
            
            return d
            
        except Exception as e:
            task.error = str(e)
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.now()
            logger.error(f"Task {task.id} execution error: {e}")
            return None
    
    def _on_task_complete(self, task_id: str, future):
        """任务完成回调"""
        if task_id in self.running_tasks:
            task = self.running_tasks.pop(task_id)
            
            if task.status == TaskStatus.COMPLETED:
                self.completed_tasks[task_id] = task
            elif task.status == TaskStatus.FAILED:
                self.failed_tasks[task_id] = task
            
            logger.info(f"Task {task_id} completed with status {task.status}")
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self.pending_tasks:
            task = self.pending_tasks.pop(task_id)
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            logger.info(f"Task {task_id} cancelled")
            return True
        
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.status = TaskStatus.CANCELLED
            task.completed_at = datetime.now()
            logger.info(f"Task {task_id} cancelled (was running)")
            return True
        
        return False
    
    def retry_task(self, task_id: str) -> bool:
        """重试任务"""
        if task_id in self.failed_tasks:
            task = self.failed_tasks.pop(task_id)
            task.current_retry = 0
            task.status = TaskStatus.PENDING
            task.error = None
            self.pending_tasks[task_id] = task
            logger.info(f"Task {task_id} queued for retry")
            return True
        
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取调度器统计信息"""
        return {
            'pending_count': len(self.pending_tasks),
            'running_count': len(self.running_tasks),
            'completed_count': len(self.completed_tasks),
            'failed_count': len(self.failed_tasks),
            'max_concurrent': self.max_concurrent,
            'utilization': len(self.running_tasks) / self.max_concurrent if self.max_concurrent > 0 else 0
        }
    
    def start(self):
        """启动调度器"""
        self.running = True
        logger.info("Task scheduler started")
    
    def stop(self):
        """停止调度器"""
        self.running = False
        self.executor.shutdown(wait=True)
        logger.info("Task scheduler stopped")
    
    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务"""
        for collection in [self.pending_tasks, self.running_tasks, 
                          self.completed_tasks, self.failed_tasks]:
            if task_id in collection:
                return collection[task_id]
        return None
    
    def list_tasks(self, status: TaskStatus = None, 
                   limit: int = 100) -> List[Task]:
        """列出任务"""
        all_tasks = []
        
        if status is None:
            collections = [
                self.pending_tasks, 
                self.running_tasks, 
                self.completed_tasks, 
                self.failed_tasks
            ]
            for collection in collections:
                all_tasks.extend(collection.values())
        else:
            for collection in [self.pending_tasks, self.running_tasks, 
                              self.completed_tasks, self.failed_tasks]:
                for task in collection.values():
                    if task.status == status:
                        all_tasks.append(task)
        
        all_tasks.sort(key=lambda t: t.created_at, reverse=True)
        return all_tasks[:limit]


scheduler = TaskScheduler(max_concurrent=4, max_retries=3)
