"""
Action处理器模块
支持多种自动化操作：点击、输入、等待、截图、数据提取等
"""
from typing import Any, Dict, Optional, List
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class BaseActionHandler(ABC):
    """动作处理器基类"""
    
    @abstractmethod
    async def execute(self, page, action: Dict[str, Any]) -> Any:
        pass
    
    @abstractmethod
    def get_name(self) -> str:
        pass


class ClickHandler(BaseActionHandler):
    """点击处理器"""
    
    def get_name(self) -> str:
        return 'click'
    
    async def execute(self, page, action: Dict[str, Any]) -> Dict[str, Any]:
        selector = action.get('selector', '')
        by_image = action.get('by_image', False)
        timeout = action.get('timeout', 5000)
        
        if by_image:
            return await self._click_by_image(page, action)
        else:
            await page.click(selector, timeout=timeout)
            await page.wait_for_load_state('networkidle')
            return {
                'type': 'click',
                'selector': selector,
                'success': True
            }
    
    async def _click_by_image(self, page, action: Dict[str, Any]) -> Dict[str, Any]:
        from utils.image_clicker import click_by_image
        template_path = action.get('template_path', '')
        
        position = await click_by_image(page, template_path)
        
        if position:
            await page.mouse.click(position[0], position[1])
            return {
                'type': 'image_click',
                'template': template_path,
                'position': position,
                'success': True
            }
        
        return {
            'type': 'image_click',
            'template': template_path,
            'success': False,
            'error': 'Template not found'
        }


class InputHandler(BaseActionHandler):
    """输入处理器"""
    
    def get_name(self) -> str:
        return 'input'
    
    async def execute(self, page, action: Dict[str, Any]) -> Dict[str, Any]:
        selector = action.get('selector', '')
        value = action.get('value', '')
        clear = action.get('clear', True)
        press_enter = action.get('press_enter', False)
        
        if clear:
            await page.fill(selector, '', timeout=5000)
        
        await page.fill(selector, value)
        
        if press_enter:
            await page.press(selector, 'Enter')
        
        return {
            'type': 'input',
            'selector': selector,
            'value': value,
            'clear': clear,
            'press_enter': press_enter,
            'success': True
        }


class WaitHandler(BaseActionHandler):
    """等待处理器"""
    
    def get_name(self) -> str:
        return 'wait'
    
    async def execute(self, page, action: Dict[str, Any]) -> Dict[str, Any]:
        timeout = action.get('timeout', 1000)
        selector = action.get('selector', '')
        state = action.get('state', 'visible')
        
        if selector:
            await page.wait_for_selector(selector, state=state, timeout=timeout)
            return {
                'type': 'wait_for_selector',
                'selector': selector,
                'state': state,
                'success': True
            }
        else:
            await page.wait_for_timeout(timeout)
            return {
                'type': 'wait_for_timeout',
                'timeout': timeout,
                'success': True
            }


class GotoHandler(BaseActionHandler):
    """页面跳转处理器"""
    
    def get_name(self) -> str:
        return 'goto'
    
    async def execute(self, page, action: Dict[str, Any]) -> Dict[str, Any]:
        url = action.get('url', '')
        wait_until = action.get('wait_until', 'networkidle')
        timeout = action.get('timeout', 30000)
        
        response = await page.goto(url, wait_until=wait_until, timeout=timeout)
        
        return {
            'type': 'goto',
            'url': url,
            'status': response.status if response else None,
            'success': True
        }


class ScreenshotHandler(BaseActionHandler):
    """截图处理器"""
    
    def get_name(self) -> str:
        return 'screenshot'
    
    async def execute(self, page, action: Dict[str, Any]) -> Dict[str, Any]:
        path = action.get('path', '')
        selector = action.get('selector', '')
        full_page = action.get('full_page', False)
        
        from datetime import datetime
        import os
        
        if not path:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            os.makedirs('./screenshots', exist_ok=True)
            path = f'./screenshots/screenshot_{timestamp}.png'
        
        if selector:
            element = await page.query_selector(selector)
            if element:
                await element.screenshot(path=path)
            else:
                return {
                    'type': 'screenshot',
                    'success': False,
                    'error': f'Element not found: {selector}'
                }
        else:
            await page.screenshot(path=path, full_page=full_page)
        
        return {
            'type': 'screenshot',
            'path': path,
            'success': True
        }


class EvaluateHandler(BaseActionHandler):
    """JavaScript执行处理器"""
    
    def get_name(self) -> str:
        return 'evaluate'
    
    async def execute(self, page, action: Dict[str, Any]) -> Dict[str, Any]:
        script = action.get('script', '')
        arg = action.get('arg', None)
        
        result = await page.evaluate(script, arg)
        
        return {
            'type': 'evaluate',
            'script': script,
            'result': result,
            'success': True
        }


class ScrollHandler(BaseActionHandler):
    """滚动处理器"""
    
    def get_name(self) -> str:
        return 'scroll'
    
    async def execute(self, page, action: Dict[str, Any]) -> Dict[str, Any]:
        x = action.get('x', 0)
        y = action.get('y', 0)
        selector = action.get('selector', '')
        
        if selector:
            element = await page.query_selector(selector)
            if element:
                await element.scroll_into_view_if_needed()
        else:
            await page.mouse.wheel(x, y)
        
        return {
            'type': 'scroll',
            'x': x,
            'y': y,
            'selector': selector,
            'success': True
        }


class PressHandler(BaseActionHandler):
    """键盘按键处理器"""
    
    def get_name(self) -> str:
        return 'press'
    
    async def execute(self, page, action: Dict[str, Any]) -> Dict[str, Any]:
        selector = action.get('selector', '')
        key = action.get('key', '')
        
        await page.press(selector, key)
        
        return {
            'type': 'press',
            'selector': selector,
            'key': key,
            'success': True
        }


class ExtractHandler(BaseActionHandler):
    """数据提取处理器"""
    
    def get_name(self) -> str:
        return 'extract'
    
    async def execute(self, page, action: Dict[str, Any]) -> Dict[str, Any]:
        selectors = action.get('selectors', [])
        extract_type = action.get('extract_type', 'html')
        
        extracted = {}
        
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                
                if extract_type == 'text':
                    extracted[selector] = [await el.inner_text() for el in elements]
                elif extract_type == 'html':
                    extracted[selector] = [await el.inner_html() for el in elements]
                elif extract_type == 'attribute':
                    attr = action.get('attribute', 'href')
                    extracted[selector] = [await el.get_attribute(attr) for el in elements]
                else:
                    extracted[selector] = [await el.inner_html() for el in elements]
                    
            except Exception as e:
                extracted[selector] = {'error': str(e)}
        
        return {
            'type': 'extract',
            'selectors': selectors,
            'extract_type': extract_type,
            'data': extracted,
            'success': True
        }


class UploadHandler(BaseActionHandler):
    """文件上传处理器"""
    
    def get_name(self) -> str:
        return 'upload'
    
    async def execute(self, page, action: Dict[str, Any]) -> Dict[str, Any]:
        selector = action.get('selector', '')
        file_paths = action.get('file_paths', [])
        
        await page.set_input_files(selector, file_paths)
        
        return {
            'type': 'upload',
            'selector': selector,
            'file_paths': file_paths,
            'success': True
        }


class HoverHandler(BaseActionHandler):
    """悬停处理器"""
    
    def get_name(self) -> str:
        return 'hover'
    
    async def execute(self, page, action: Dict[str, Any]) -> Dict[str, Any]:
        selector = action.get('selector', '')
        timeout = action.get('timeout', 5000)
        
        await page.hover(selector, timeout=timeout)
        
        return {
            'type': 'hover',
            'selector': selector,
            'success': True
        }


class ActionDispatcher:
    """动作分发器 - 根据动作类型分发到对应的处理器"""
    
    def __init__(self):
        self.handlers: Dict[str, BaseActionHandler] = {}
        self._register_default_handlers()
    
    def _register_default_handlers(self):
        handlers = [
            ClickHandler(),
            InputHandler(),
            WaitHandler(),
            GotoHandler(),
            ScreenshotHandler(),
            EvaluateHandler(),
            ScrollHandler(),
            PressHandler(),
            ExtractHandler(),
            UploadHandler(),
            HoverHandler(),
        ]
        
        for handler in handlers:
            self.register_handler(handler)
    
    def register_handler(self, handler: BaseActionHandler):
        self.handlers[handler.get_name()] = handler
    
    def get_handler(self, action_type: str) -> Optional[BaseActionHandler]:
        return self.handlers.get(action_type)
    
    def get_available_actions(self) -> List[str]:
        return list(self.handlers.keys())
    
    async def execute(self, page, action: Dict[str, Any]) -> Dict[str, Any]:
        action_type = action.get('type', '')
        
        handler = self.get_handler(action_type)
        
        if not handler:
            return {
                'type': action_type,
                'success': False,
                'error': f'Unknown action type: {action_type}'
            }
        
        try:
            result = await handler.execute(page, action)
            return result
        except Exception as e:
            logger.error(f"Action {action_type} failed: {e}")
            return {
                'type': action_type,
                'success': False,
                'error': str(e)
            }


dispatcher = ActionDispatcher()
