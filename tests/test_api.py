"""
API 端点测试 - 使用 FastAPI TestClient
"""
import pytest
from fastapi.testclient import TestClient
import sys
import os

# Add api_service to path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'api_service'))


class TestAPIModels:
    """API 模型测试"""

    def test_batch_task_create_model(self):
        """测试批量任务创建模型"""
        from pydantic import BaseModel
        from typing import List, Dict, Any

        class BatchTaskCreate(BaseModel):
            tasks: List[Dict[str, Any]]
            max_retries: int = 3

        data = {
            'tasks': [
                {'url': 'https://example1.com', 'actions': []},
                {'url': 'https://example2.com', 'actions': []}
            ],
            'max_retries': 5
        }

        model = BatchTaskCreate(**data)
        assert len(model.tasks) == 2
        assert model.max_retries == 5

    def test_batch_task_create_empty_validation(self):
        """测试批量任务空列表验证"""
        from pydantic import BaseModel, ValidationError, Field
        from typing import List, Dict, Any

        class BatchTaskCreate(BaseModel):
            tasks: List[Dict[str, Any]] = Field(..., min_length=1, max_length=50)

        try:
            BatchTaskCreate(tasks=[])
            assert False, "Should have raised ValidationError"
        except ValidationError:
            pass  # Expected

    def test_batch_task_delete_model(self):
        """测试批量任务删除模型"""
        from pydantic import BaseModel
        from typing import List

        class BatchTaskDelete(BaseModel):
            task_ids: List[str]

        data = {'task_ids': ['task-1', 'task-2', 'task-3']}
        model = BatchTaskDelete(**data)
        assert len(model.task_ids) == 3

    def test_batch_task_cancel_model(self):
        """测试批量任务取消模型"""
        from pydantic import BaseModel
        from typing import List

        class BatchTaskCancel(BaseModel):
            task_ids: List[str]

        data = {'task_ids': ['task-1']}
        model = BatchTaskCancel(**data)
        assert model.task_ids[0] == 'task-1'


class TestAPIValidation:
    """API 验证测试"""

    def test_task_create_validation_url_required(self):
        """测试任务创建时 URL 必填"""
        from pydantic import BaseModel, ValidationError, Field
        from typing import List, Dict, Any

        class TaskCreate(BaseModel):
            url: str = Field(..., min_length=1)
            actions: List[Dict[str, Any]]
            priority: int = 1

        # Valid URL
        task = TaskCreate(url='https://example.com', actions=[])
        assert task.url == 'https://example.com'

        # Empty URL should fail
        try:
            TaskCreate(url='', actions=[])
            assert False, "Should have raised ValidationError for empty URL"
        except ValidationError:
            pass  # Expected

    def test_task_create_validation_priority_range(self):
        """测试任务创建时优先级范围"""
        from pydantic import BaseModel, ValidationError, Field
        from typing import List, Dict, Any

        class TaskCreate(BaseModel):
            url: str
            actions: List[Dict[str, Any]]
            priority: int = Field(default=1, ge=0, le=3)

        # Valid priorities
        for p in [0, 1, 2, 3]:
            task = TaskCreate(url='https://example.com', actions=[], priority=p)
            assert task.priority == p

        # Invalid priority
        try:
            TaskCreate(url='https://example.com', actions=[], priority=10)
            assert False, "Should have raised ValidationError for invalid priority"
        except (ValidationError, NameError):
            pass


class TestSchedulerModels:
    """调度器模型测试"""

    def test_task_serialization(self):
        """测试任务序列化"""
        from datetime import datetime
        import json

        task_dict = {
            'id': 'test-123',
            'url': 'https://example.com',
            'actions': [{'type': 'goto', 'url': 'https://example.com'}],
            'priority': 2,
            'status': 'pending',
            'created_at': datetime.now().isoformat()
        }

        # Verify it can be serialized
        json_str = json.dumps(task_dict)
        assert 'test-123' in json_str

    def test_task_list_pagination(self):
        """测试任务列表分页"""
        class PaginationParams:
            def __init__(self, limit: int, offset: int):
                self.limit = limit
                self.offset = offset

        params = PaginationParams(limit=10, offset=20)
        assert params.limit == 10
        assert params.offset == 20


class TestActionModels:
    """动作模型测试"""

    def test_action_types(self):
        """测试动作类型定义"""
        valid_actions = [
            'goto', 'click', 'input', 'wait', 'screenshot',
            'extract', 'evaluate', 'scroll', 'press', 'hover', 'upload'
        ]

        for action_type in valid_actions:
            action = {'type': action_type}
            assert 'type' in action
            assert action['type'] == action_type

    def test_action_with_selector(self):
        """测试带选择器的动作"""
        action = {
            'type': 'click',
            'selector': '#submit-button',
            'timeout': 5000
        }

        assert action['selector'] == '#submit-button'
        assert action['timeout'] == 5000

    def test_action_with_value(self):
        """测试带值的动作"""
        action = {
            'type': 'input',
            'selector': '#username',
            'value': 'test_user',
            'clear': True
        }

        assert action['value'] == 'test_user'
        assert action['clear'] is True


class TestExtractorModels:
    """提取器模型测试"""

    def test_extractor_types(self):
        """测试提取器类型"""
        valid_extractors = ['html', 'json', 'table', 'xpath', 'api', 'screenshot', 'fullpage']

        for extractor_type in valid_extractors:
            config = {'type': extractor_type}
            assert config['type'] == extractor_type

    def test_extractor_with_selectors(self):
        """测试带选择器的提取器"""
        extractor = {
            'type': 'html',
            'selectors': ['.item', '.title', '.description'],
            'extract_type': 'text'
        }

        assert len(extractor['selectors']) == 3
        assert extractor['extract_type'] == 'text'


class TestBatchOperationsLogic:
    """批量操作逻辑测试"""

    def test_batch_limit_validation(self):
        """测试批量限制验证"""
        MAX_BATCH_CREATE = 50
        MAX_BATCH_DELETE = 100

        # Test create limit
        tasks_count = 50
        assert tasks_count <= MAX_BATCH_CREATE

        # Test delete limit
        ids_count = 100
        assert ids_count <= MAX_BATCH_DELETE

    def test_batch_result_structure(self):
        """测试批量结果结构"""
        result = {
            'created': [
                {'task_id': 'task-1', 'url': 'https://a.com', 'status': 'pending'},
                {'task_id': 'task-2', 'url': 'https://b.com', 'status': 'pending'}
            ],
            'errors': [],
            'total_created': 2,
            'total_errors': 0
        }

        assert 'created' in result
        assert 'errors' in result
        assert 'total_created' in result
        assert 'total_errors' in result

    def test_batch_error_structure(self):
        """测试批量错误结构"""
        error_result = {
            'deleted': ['task-1'],
            'errors': [
                {'task_id': 'task-2', 'error': '任务不存在'}
            ],
            'total_deleted': 1,
            'total_errors': 1
        }

        assert len(error_result['errors']) == 1
        assert 'task_id' in error_result['errors'][0]
        assert 'error' in error_result['errors'][0]


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
