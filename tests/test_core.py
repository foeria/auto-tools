"""
测试套件
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from utils.action_handler import (
    ActionDispatcher, ClickHandler, InputHandler, 
    WaitHandler, GotoHandler, ScreenshotHandler
)
from utils.data_extractor import DataExtractor
from utils.scheduler import Task, TaskScheduler, TaskPriority, TaskStatus


class TestActionHandlers:
    """动作处理器测试"""
    
    def setup_method(self):
        self.dispatcher = ActionDispatcher()
    
    def test_click_handler_execute(self):
        handler = ClickHandler()
        assert handler.get_name() == 'click'
    
    def test_input_handler_execute(self):
        handler = InputHandler()
        assert handler.get_name() == 'input'
    
    def test_wait_handler_execute(self):
        handler = WaitHandler()
        assert handler.get_name() == 'wait'
    
    def test_goto_handler_execute(self):
        handler = GotoHandler()
        assert handler.get_name() == 'goto'
    
    def test_screenshot_handler_execute(self):
        handler = ScreenshotHandler()
        assert handler.get_name() == 'screenshot'
    
    def test_dispatcher_has_all_handlers(self):
        handlers = self.dispatcher.get_available_actions()
        assert 'click' in handlers
        assert 'input' in handlers
        assert 'wait' in handlers
        assert 'goto' in handlers
        assert 'screenshot' in handlers
        assert 'extract' in handlers
        assert 'evaluate' in handlers
    
    def test_dispatcher_unknown_action(self):
        page = AsyncMock()
        action = {'type': 'unknown_action'}
        result = asyncio.run(self.dispatcher.execute(page, action))
        assert result['success'] == False
        assert 'Unknown action type' in result['error']


class TestDataExtractor:
    """数据提取器测试"""
    
    def setup_method(self):
        self.extractor = DataExtractor()
    
    def test_extractor_has_all_types(self):
        extractors = self.extractor.get_available_extractors()
        assert 'html' in extractors
        assert 'json' in extractors
        assert 'table' in extractors
        assert 'xpath' in extractors
        assert 'screenshot' in extractors
        assert 'fullpage' in extractors
    
    def test_extractor_unknown_type(self):
        page = AsyncMock()
        result = asyncio.run(self.extractor.extract(page, 'unknown', {}))
        assert 'error' in result


class TestTask:
    """任务测试"""
    
    def test_task_creation(self):
        task = Task(
            task_id='test-001',
            url='https://example.com',
            actions=[{'type': 'goto', 'url': 'https://example.com'}],
            priority=TaskPriority.HIGH
        )
        assert task.id == 'test-001'
        assert task.url == 'https://example.com'
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.PENDING
    
    def test_task_to_dict(self):
        task = Task(
            task_id='test-002',
            url='https://test.com',
            actions=[]
        )
        data = task.to_dict()
        assert data['id'] == 'test-002'
        assert data['url'] == 'https://test.com'
        assert 'priority' in data
        assert 'created_at' in data
    
    def test_task_from_dict(self):
        data = {
            'id': 'test-003',
            'url': 'https://test.com',
            'actions': [{'type': 'click'}],
            'priority': 2,
            'status': 'running'
        }
        task = Task.from_dict(data)
        assert task.id == 'test-003'
        assert task.priority == TaskPriority.HIGH
        assert task.status == TaskStatus.RUNNING
    
    def test_task_priority_ordering(self):
        low = TaskPriority.LOW
        normal = TaskPriority.NORMAL
        high = TaskPriority.HIGH
        urgent = TaskPriority.URGENT
        
        assert low < normal < high < urgent


class TestTaskScheduler:
    """任务调度器测试"""
    
    def setup_method(self):
        self.scheduler = TaskScheduler(max_concurrent=2, max_retries=2)
    
    def teardown_method(self):
        self.scheduler.stop()
    
    def test_add_task(self):
        task = Task(task_id='task-001', url='https://example.com', actions=[])
        self.scheduler.add_task(task)
        assert task.id in self.scheduler.pending_tasks
    
    def test_get_next_task_priority(self):
        low_task = Task(task_id='low', url='a.com', actions=[], priority=TaskPriority.LOW)
        high_task = Task(task_id='high', url='b.com', actions=[], priority=TaskPriority.HIGH)
        
        self.scheduler.add_task(low_task)
        self.scheduler.add_task(high_task)
        
        next_task = self.scheduler.get_next_task()
        assert next_task.id == 'high'
    
    def test_cancel_task(self):
        task = Task(task_id='task-cancel', url='example.com', actions=[])
        self.scheduler.add_task(task)
        
        result = self.scheduler.cancel_task('task-cancel')
        assert result == True
        assert task.id not in self.scheduler.pending_tasks
    
    def test_cancel_nonexistent_task(self):
        result = self.scheduler.cancel_task('nonexistent')
        assert result == False
    
    def test_get_statistics(self):
        task1 = Task(task_id='s1', url='a.com', actions=[])
        task2 = Task(task_id='s2', url='b.com', actions=[])
        
        self.scheduler.add_task(task1)
        self.scheduler.add_task(task2)
        
        stats = self.scheduler.get_statistics()
        assert stats['pending_count'] == 2
        assert stats['max_concurrent'] == 2
    
    def test_list_tasks(self):
        task = Task(task_id='list-test', url='test.com', actions=[])
        self.scheduler.add_task(task)
        
        tasks = self.scheduler.list_tasks()
        assert len(tasks) == 1
        assert tasks[0].id == 'list-test'
    
    def test_list_tasks_by_status(self):
        task = Task(task_id='status-test', url='test.com', actions=[])
        self.scheduler.add_task(task)
        
        pending_tasks = self.scheduler.list_tasks(status=TaskStatus.PENDING)
        assert len(pending_tasks) == 1


class TestImageClicker:
    """图像点击器测试"""
    
    def test_image_clicker_initialization(self):
        from utils.image_clicker import ImageClicker
        clicker = ImageClicker(template_dir='/tmp/test', threshold=0.8)
        assert clicker.threshold == 0.8
        assert clicker.template_dir == '/tmp/test'
    
    def test_load_template_not_found(self):
        from utils.image_clicker import ImageClicker
        clicker = ImageClicker()
        result = clicker.load_template('nonexistent.png')
        assert result == False


class TestStorageManager:
    """存储管理器测试"""
    
    def test_mongodb_storage_mock(self):
        from utils.storage import MongoDBStorage
        storage = MongoDBStorage(uri='mongodb://localhost:27017', db_name='test_db')
        assert storage.db.name == 'test_db'
    
    def test_redis_storage_mock(self):
        from utils.storage import RedisStorage
        storage = RedisStorage(host='localhost', port=6379)
        assert storage.client.ping() == True


@pytest.fixture
def sample_task_data():
    return {
        'url': 'https://example.com',
        'actions': [
            {'type': 'goto', 'url': 'https://example.com'},
            {'type': 'wait', 'timeout': 1000},
            {'type': 'click', 'selector': '#submit'},
            {'type': 'extract', 'selectors': ['.result']}
        ],
        'priority': 1,
        'max_retries': 3
    }


@pytest.fixture
def sample_workflow():
    return {
        'name': '测试工作流',
        'description': '用于测试的示例工作流',
        'actions': [
            {'type': 'goto', 'url': ''},
            {'type': 'input', 'selector': '#search', 'value': 'test'}
        ]
    }


class TestAPIModels:
    """API模型测试"""
    
    def test_task_create_model(self, sample_task_data):
        from pydantic import BaseModel
        from typing import List, Dict, Any
        
        class TaskCreate(BaseModel):
            url: str
            actions: List[Dict[str, Any]]
            priority: int = 1
            max_retries: int = 3
        
        task = TaskCreate(**sample_task_data)
        assert task.url == 'https://example.com'
        assert len(task.actions) == 4
        assert task.priority == 1


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
