"""
自动化爬虫
使用模块化的Action处理器和数据提取器
"""
import scrapy
from scrapy_playwright.page import PageMethod
from typing import Any, Dict, List
from datetime import datetime
import logging

from utils.action_handler import dispatcher
from utils.data_extractor import extractor

logger = logging.getLogger(__name__)


class AutomationSpider(scrapy.Spider):
    name = 'automation'
    
    custom_settings = {
        'DOWNLOAD_DELAY': 1.0,
        'AUTOTHROTTLE_ENABLED': True,
        'AUTOTHROTTLE_START_DELAY': 1.0,
        'AUTOTHROTTLE_MAX_DELAY': 10.0,
        'AUTOTHROTTLE_TARGET_CONCURRENT_REQUESTS': 1.0,
    }
    
    def __init__(self, actions: List[Dict[str, Any]] = None, 
                 extractors: List[Dict[str, Any]] = None,
                 *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.actions = actions or []
        self.extractors = extractors or []
        self.results = {}
    
    def start_requests(self):
        if not self.actions:
            logger.warning("No actions provided")
            return []
        
        first_action = self.actions[0]
        url = first_action.get('url', '')
        
        if not url:
            logger.error("No URL provided in first action")
            return []
        
        page_methods = [
            PageMethod('wait_for_load_state', 'domcontentloaded'),
        ]
        
        if first_action.get('wait_before'):
            page_methods.append(
                PageMethod('wait_for_timeout', first_action['wait_before'])
            )
        
        logger.info(f"Starting crawl for URL: {url}")
        
        context_name = "default"
        try:
            use_persistent = self.settings.getbool("PLAYWRIGHT_USE_PERSISTENT_CONTEXT")
            user_data_dir = self.settings.get("PLAYWRIGHT_USER_DATA_DIR")
            if use_persistent and user_data_dir:
                context_name = "user"
        except Exception:
            context_name = "default"
        
        yield scrapy.Request(
            url=url,
            meta={
                'playwright': True,
                'playwright_page_methods': page_methods,
                'playwright_include_page': True,
                'playwright_default_navigation_timeout': 60000,
                'playwright_context': context_name,
            },
            callback=self.parse,
            errback=self.errback,
        )
    
    async def parse(self, response):
        page = response.meta['playwright_page']
        self.page = page
        
        try:
            logger.info(f"Processing {len(self.actions)} actions")
            
            for i, action in enumerate(self.actions[1:], 1):
                action_type = action.get('type', '')
                logger.info(f"Executing action {i}/{len(self.actions)-1}: {action_type}")
                
                result = await dispatcher.execute(page, action)
                
                if result and result.get('success') != False:
                    action_id = action.get('id', f'action_{i}')
                    self.results[action_id] = result
            
            logger.info("Extracting data using configured extractors")
            
            for i, extractor_config in enumerate(self.extractors):
                extractor_type = extractor_config.get('type', 'html')
                config = {k: v for k, v in extractor_config.items() if k != 'type'}
                
                extract_result = await extractor.extract(page, extractor_type, config)
                
                self.results[f'extractor_{i}'] = {
                    'type': extractor_type,
                    'result': extract_result
                }
            
            final_result = await self.extract_final_data(page)
            self.results['final'] = final_result
            
            success = True
            
        except Exception as e:
            logger.error(f"Error during execution: {e}")
            self.results['error'] = str(e)
            success = False
        
        finally:
            try:
                await page.close()
            except:
                pass
        
        yield {
            'url': response.url,
            'actions_executed': len(self.actions) - 1,
            'extractors_executed': len(self.extractors),
            'results': self.results,
            'success': success,
            'timestamp': self.get_timestamp(),
        }
    
    async def extract_final_data(self, page) -> Dict[str, Any]:
        extracted = {}
        
        try:
            title = await page.title()
            url = page.url
            
            html = await page.content()
            
            text_content = await page.evaluate('''() => {
                return document.body.innerText.trim();
            }''')
            
            extracted = {
                'title': title,
                'url': url,
                'text_length': len(text_content),
                'text_preview': text_content[:500] if text_content else '',
            }
            
        except Exception as e:
            logger.warning(f"Final data extraction warning: {e}")
            extracted = {'error': str(e)}
        
        return extracted
    
    def get_timestamp(self):
        return datetime.now().strftime('%Y%m%d_%H%M%S_%f')
    
    async def errback(self, failure):
        page = failure.request.meta.get('playwright_page')
        if page:
            try:
                await page.close()
            except:
                pass
        
        logger.error(f"Request failed: {failure.value}")
        
        self.results['error'] = str(failure.value)
        
        yield {
            'url': failure.request.url,
            'actions_executed': 0,
            'results': self.results,
            'success': False,
            'error': str(failure.value),
            'timestamp': self.get_timestamp(),
        }
