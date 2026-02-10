"""
集成测试
"""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestIntegrationScenarios:
    """集成测试场景"""
    
    @pytest.fixture
    def mock_page(self):
        page = AsyncMock()
        page.goto = AsyncMock()
        page.click = AsyncMock()
        page.fill = AsyncMock()
        page.wait_for_timeout = AsyncMock()
        page.wait_for_selector = AsyncMock()
        page.screenshot = AsyncMock(return_value=b'fake screenshot')
        page.content = AsyncMock(return_value='<html><body>Test</body></html>')
        page.title = AsyncMock(return_value='Test Page')
        page.url = 'https://example.com'
        return page
    
    @pytest.mark.asyncio
    async def test_full_automation_flow(self, mock_page):
        """测试完整的自动化流程"""
        from utils.action_handler import dispatcher
        
        actions = [
            {'type': 'goto', 'url': 'https://example.com'},
            {'type': 'wait', 'timeout': 1000},
            {'type': 'input', 'selector': '#search', 'value': 'test'},
            {'type': 'click', 'selector': '#submit'},
            {'type': 'wait', 'selector': '.result', 'state': 'visible'}
        ]
        
        for action in actions[1:]:
            result = await dispatcher.execute(mock_page, action)
            assert result is not None
        
        mock_page.goto.assert_called_once()
        mock_page.fill.assert_called()
        mock_page.click.assert_called()
        mock_page.wait_for_timeout.assert_called()
    
    @pytest.mark.asyncio
    async def test_extraction_flow(self, mock_page):
        """测试数据提取流程"""
        from utils.data_extractor import extractor
        
        mock_page.query_selector_all = AsyncMock(return_value=[
            AsyncMock(inner_html=Mock(return_value='<span>Item 1</span>')),
            AsyncMock(inner_html=Mock(return_value='<span>Item 2</span>'))
        ])
        
        config = {
            'selectors': ['.item']
        }
        
        result = await extractor.extract(mock_page, 'html', config)
        
        assert 'extractor' in result
        assert result['extractor'] == 'html'
        assert 'data' in result
    
    def test_scheduler_with_dependencies(self):
        """测试带依赖的任务调度"""
        from utils.scheduler import TaskScheduler, Task, TaskPriority
        
        scheduler = TaskScheduler(max_concurrent=2, max_retries=1)
        
        task1 = Task(
            task_id='task-1',
            url='https://example.com/1',
            actions=[]
        )
        task2 = Task(
            task_id='task-2',
            url='https://example.com/2',
            actions=[],
            priority=TaskPriority.HIGH
        )
        
        scheduler.add_task(task1)
        scheduler.add_task(task2)
        
        scheduler.stop()
        
        assert len(scheduler.pending_tasks) == 2


class TestErrorHandling:
    """错误处理测试"""
    
    @pytest.mark.asyncio
    async def test_action_handler_error(self):
        """测试动作处理器错误处理"""
        from utils.action_handler import dispatcher
        
        page = AsyncMock()
        page.click = AsyncMock(side_effect=Exception('Element not found'))
        
        action = {'type': 'click', 'selector': '#nonexistent'}
        
        result = await dispatcher.execute(page, action)
        
        assert result['success'] == False
        assert 'error' in result
    
    @pytest.mark.asyncio
    async def test_extractor_error_handling(self):
        """测试提取器错误处理"""
        from utils.data_extractor import extractor
        
        page = AsyncMock()
        page.query_selector_all = AsyncMock(side_effect=Exception('Selector error'))
        
        config = {'selectors': ['.invalid']}
        
        result = await extractor.extract(page, 'html', config)
        
        assert 'error' in result['data']['.invalid']


class TestConfigurationScenarios:
    """配置场景测试"""
    
    def test_priority_configuration(self):
        """测试优先级配置"""
        from utils.scheduler import TaskPriority
        
        priorities = [TaskPriority.LOW, TaskPriority.NORMAL, TaskPriority.HIGH, TaskPriority.URGENT]
        
        assert len(priorities) == 4
        
        values = [p.value for p in priorities]
        assert values == sorted(values)
    
    def test_action_config_defaults(self):
        """测试动作默认配置"""
        from utils.action_handler import ClickHandler
        
        handler = ClickHandler()
        
        assert handler.get_name() == 'click'


class TestDataExtractionFormats:
    """数据提取格式测试"""
    
    @pytest.fixture
    def mock_page_for_extract(self):
        page = AsyncMock()
        page.inner_text = AsyncMock(return_value='Test Text')
        page.inner_html = AsyncMock(return_value='<span>HTML</span>')
        page.get_attribute = AsyncMock(return_value='https://link.com')
        return page
    
    @pytest.mark.asyncio
    async def test_extract_text(self, mock_page_for_extract):
        from utils.data_extractor import extractor
        
        config = {
            'selectors': ['.text'],
            'extract_type': 'text'
        }
        
        result = await extractor.extract(mock_page_for_extract, 'html', config)
        
        assert result['data'] is not None
    
    @pytest.mark.asyncio
    async def test_extract_html(self, mock_page_for_extract):
        from utils.data_extractor import extractor
        
        config = {
            'selectors': ['.html'],
            'extract_type': 'html'
        }
        
        result = await extractor.extract(mock_page_for_extract, 'html', config)
        
        assert result['data'] is not None
    
    @pytest.mark.asyncio
    async def test_extract_attribute(self, mock_page_for_extract):
        from utils.data_extractor import extractor
        
        config = {
            'selectors': ['.link'],
            'extract_type': 'attribute',
            'attribute': 'href'
        }
        
        result = await extractor.extract(mock_page_for_extract, 'html', config)
        
        assert result['data'] is not None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
