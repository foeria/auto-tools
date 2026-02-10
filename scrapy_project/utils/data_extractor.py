"""
数据提取器模块
提供多种数据提取策略：HTML解析、JSON提取、表格提取等
"""
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
import json
import re
from lxml import etree
import logging

logger = logging.getLogger(__name__)


class BaseExtractor(ABC):
    """数据提取器基类"""
    
    @abstractmethod
    async def extract(self, page, config: Dict[str, Any]) -> Dict[str, Any]:
        pass


class HTMLExtractor(BaseExtractor):
    """HTML元素提取器"""
    
    def get_name(self) -> str:
        return 'html'
    
    async def extract(self, page, config: Dict[str, Any]) -> Dict[str, Any]:
        selectors = config.get('selectors', [])
        extract_type = config.get('extract_type', 'html')
        
        results = {}
        
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                
                if extract_type == 'text':
                    results[selector] = [await el.inner_text() for el in elements]
                elif extract_type == 'html':
                    results[selector] = [await el.inner_html() for el in elements]
                elif extract_type == 'attribute':
                    attr = config.get('attribute', 'href')
                    results[selector] = [await el.get_attribute(attr) for el in elements]
                else:
                    results[selector] = [await el.inner_html() for el in elements]
                    
            except Exception as e:
                results[selector] = {'error': str(e)}
        
        return {
            'extractor': 'html',
            'selectors': selectors,
            'data': results
        }


class JSONExtractor(BaseExtractor):
    """JSON数据提取器"""
    
    def get_name(self) -> str:
        return 'json'
    
    async def extract(self, page, config: Dict[str, Any]) -> Dict[str, Any]:
        script_tag = config.get('script_tag', 'window.__INITIAL_STATE__')
        attribute = config.get('attribute', None)
        
        try:
            if attribute:
                json_data = await page.evaluate(f'document.querySelector("{attribute}").getAttribute("data-json")')
            else:
                json_data = await page.evaluate(f'document.querySelector("script:{script_tag}").textContent')
            
            if json_data:
                data = json.loads(json_data)
                return {
                    'extractor': 'json',
                    'data': data
                }
            
            return {
                'extractor': 'json',
                'data': None,
                'error': 'No JSON data found'
            }
            
        except Exception as e:
            return {
                'extractor': 'json',
                'error': str(e)
            }


class TableExtractor(BaseExtractor):
    """表格数据提取器"""
    
    def get_name(self) -> str:
        return 'table'
    
    async def extract(self, page, config: Dict[str, Any]) -> Dict[str, Any]:
        selector = config.get('selector', 'table')
        has_header = config.get('has_header', True)
        
        try:
            table_html = await page.evaluate(f'''(selector) => {{
                const table = document.querySelector(selector);
                if (!table) return null;
                
                const rows = Array.from(table.querySelectorAll('tr'));
                return rows.map(row => {{
                    const cells = Array.from(row.querySelectorAll('th, td'));
                    return cells.map(cell => cell.textContent.trim());
                }});
            }}''', selector)
            
            if not table_html:
                return {
                    'extractor': 'table',
                    'error': 'Table not found'
                }
            
            if has_header and table_html:
                headers = table_html[0]
                data = table_html[1:]
                
                result = []
                for row in data:
                    result.append(dict(zip(headers, row)))
                
                return {
                    'extractor': 'table',
                    'headers': headers,
                    'data': result
                }
            
            return {
                'extractor': 'table',
                'data': table_html
            }
            
        except Exception as e:
            return {
                'extractor': 'table',
                'error': str(e)
            }


class XPathExtractor(BaseExtractor):
    """XPath提取器"""
    
    def get_name(self) -> str:
        return 'xpath'
    
    async def extract(self, page, config: Dict[str, Any]) -> Dict[str, Any]:
        xpaths = config.get('xpaths', [])
        result_type = config.get('result_type', 'text')
        
        results = {}
        
        for name, xpath in xpaths.items():
            try:
                elements = await page.xpath(xpath)
                
                if result_type == 'text':
                    results[name] = [await el.inner_text() for el in elements]
                elif result_type == 'html':
                    results[name] = [await el.inner_html() for el in elements]
                else:
                    results[name] = [await el.get_attribute(result_type) for el in elements]
                    
            except Exception as e:
                results[name] = {'error': str(e)}
        
        return {
            'extractor': 'xpath',
            'data': results
        }


class APIExtractor(BaseExtractor):
    """API响应提取器 - 从页面加载的API请求中提取数据"""
    
    def get_name(self) -> str:
        return 'api'
    
    async def extract(self, page, config: Dict[str, Any]) -> Dict[str, Any]:
        url_pattern = config.get('url_pattern', '')
        timeout = config.get('timeout', 5000)
        
        try:
            responses = await page.evaluate(f'''async (pattern, timeout) => {{
                const responses = [];
                const startTime = Date.now();
                
                for (const request of page.getRequestInterception()) {{
                    if (request.url().includes(pattern)) {{
                        responses.push({{
                            url: request.url(),
                            postData: request.postData()
                        }});
                    }}
                }}
                
                return responses;
            }}''', url_pattern, timeout)
            
            return {
                'extractor': 'api',
                'pattern': url_pattern,
                'responses': responses
            }
            
        except Exception as e:
            return {
                'extractor': 'api',
                'error': str(e)
            }


class ScreenshotExtractor(BaseExtractor):
    """页面状态提取器 - 截图并检测页面状态"""
    
    def get_name(self) -> str:
        return 'screenshot'
    
    async def extract(self, page, config: Dict[str, Any]) -> Dict[str, Any]:
        save_path = config.get('save_path', '')
        element_selector = config.get('selector', '')
        
        try:
            from datetime import datetime
            import os
            
            if not save_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                os.makedirs('./screenshots', exist_ok=True)
                save_path = f'./screenshots/extraction_{timestamp}.png'
            
            if element_selector:
                element = await page.query_selector(element_selector)
                if element:
                    await element.screenshot(path=save_path)
                else:
                    return {
                        'extractor': 'screenshot',
                        'success': False,
                        'error': f'Element not found: {element_selector}'
                    }
            else:
                await page.screenshot(path=save_path, full_page=True)
            
            return {
                'extractor': 'screenshot',
                'path': save_path,
                'success': True
            }
            
        except Exception as e:
            return {
                'extractor': 'screenshot',
                'error': str(e)
            }


class FullPageExtractor(BaseExtractor):
    """完整页面提取器 - 提取页面的所有可见文本"""
    
    def get_name(self) -> str:
        return 'fullpage'
    
    async def extract(self, page, config: Dict[str, Any]) -> Dict[str, Any]:
        try:
            html = await page.content()
            
            tree = etree.HTML(html)
            
            text = ' '.join(tree.xpath('//body//text()')).strip()
            
            text = re.sub(r'\s+', ' ', text)
            
            title = await page.title()
            
            url = page.url
            
            return {
                'extractor': 'fullpage',
                'url': url,
                'title': title,
                'text': text[:10000] if len(text) > 10000 else text,
                'text_length': len(text)
            }
            
        except Exception as e:
            return {
                'extractor': 'fullpage',
                'error': str(e)
            }


class DataExtractor:
    """数据提取器管理器"""
    
    def __init__(self):
        self.extractors: Dict[str, BaseExtractor] = {}
        self._register_default_extractors()
    
    def _register_default_extractors(self):
        extractors = [
            HTMLExtractor(),
            JSONExtractor(),
            TableExtractor(),
            XPathExtractor(),
            APIExtractor(),
            ScreenshotExtractor(),
            FullPageExtractor(),
        ]
        
        for extractor in extractors:
            self.register_extractor(extractor)
    
    def register_extractor(self, extractor: BaseExtractor):
        self.extractors[extractor.get_name()] = extractor
    
    def get_extractor(self, extractor_type: str) -> Optional[BaseExtractor]:
        return self.extractors.get(extractor_type)
    
    def get_available_extractors(self) -> List[str]:
        return list(self.extractors.keys())
    
    async def extract(self, page, extractor_type: str, config: Dict[str, Any]) -> Dict[str, Any]:
        extractor = self.get_extractor(extractor_type)
        
        if not extractor:
            return {
                'extractor': extractor_type,
                'error': f'Unknown extractor type: {extractor_type}'
            }
        
        try:
            result = await extractor.extract(page, config)
            return result
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            return {
                'extractor': extractor_type,
                'error': str(e)
            }


extractor = DataExtractor()
