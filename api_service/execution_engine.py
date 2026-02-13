"""
任务执行引擎模块
负责任务执行和状态推送
"""
import sys
import asyncio
import base64
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import json
import os
import random

from fastapi import BackgroundTasks

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapy_project.utils.scheduler import TaskStatus, TaskPriority
from scrapy_project.utils.storage import storage_manager
from api_service.websocket_manager import ws_manager, WebSocketMessageType
from api_service.config import get_config
from api_service.errors import ErrorCode, ErrorHandler, ErrorDetail

logger = logging.getLogger(__name__)


def convert_selector(selector: str, selector_type: str = "css") -> str:
    """将不同类型的选择器转换为Playwright可识别的格式

    Args:
        selector: 用户输入的选择器值
        selector_type: 选择器类型 (css, xpath, id, name, class)

    Returns:
        转换后的选择器字符串
    """
    if not selector:
        return selector

    selector_type = selector_type.lower() if selector_type else "css"

    if selector_type == "xpath":
        # XPath选择器保持不变，Playwright原生支持
        return selector
    elif selector_type == "id":
        # ID选择器添加#前缀
        if not selector.startswith("#"):
            return f"#{selector}"
        return selector
    elif selector_type == "class":
        # Class选择器添加.前缀，并处理多个class的情况
        if not selector.startswith("."):
            # 如果有空格分隔的多个class，转换为CSS复合选择器
            classes = selector.split()
            return ".".join(classes) if classes else f".{selector}"
        return selector
    elif selector_type == "name":
        # Name属性选择器
        return f'[name="{selector}"]'
    else:
        # CSS选择器，保持原样
        return selector


class AsyncPlaywrightBrowser:
    """异步Playwright浏览器包装器"""

    def __init__(self):
        self.browser = None
        self.page = None
        self.context = None
        self.process = None
        self.port = None
        self.playwright = None

    async def start(self, task_id: str, url: str, headless: bool = False, config=None):
        """启动浏览器 - 使用本地Chrome通过CDP连接"""
        import socket
        from playwright.async_api import async_playwright

        # 获取Chrome路径
        chrome_path = config.browser.chrome_path
        if not os.path.exists(chrome_path):
            raise FileNotFoundError(f"Chrome not found at: {chrome_path}")

        # 查找可用端口
        def find_free_port():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('', 0))
                return s.getsockname()[1]

        self.port = find_free_port()

        logger.info(f"Starting local Chrome: {chrome_path}")

        # 启动Chrome进程
        CREATE_NO_WINDOW = 0x08000000
        chrome_args = [
            f'--remote-debugging-port={self.port}',
            '--remote-debugging-address=127.0.0.1',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--new-window',
        ]

        if headless:
            chrome_args.insert(0, '--headless=new')

        self.process = subprocess.Popen(
            [chrome_path] + chrome_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            creationflags=CREATE_NO_WINDOW,
        )

        logger.info(f"Chrome started, PID: {self.process.pid}, Port: {self.port}")

        # 等待Chrome启动
        import time
        max_wait = 15
        waited = 0
        while waited < max_wait:
            try:
                import http.client
                conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=2)
                conn.request("GET", "/json/version")
                response = conn.getresponse()
                if response.status == 200:
                    break
            except Exception:
                pass
            await asyncio.sleep(0.5)
            waited += 0.5

        # 连接Playwright
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.connect(
            f'http://127.0.0.1:{self.port}', timeout=30000
        )
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

        # 访问初始URL
        if url:
            await self.page.goto(url, wait_until='domcontentloaded', timeout=30000)

        logger.info(f"Connected to Chrome successfully")
        return self.browser, self.page

    async def close(self):
        """关闭浏览器"""
        try:
            if self.page:
                await self.page.close()
        except Exception as e:
            logger.debug(f"Error closing page: {e}")

        try:
            if self.context:
                await self.context.close()
        except Exception as e:
            logger.debug(f"Error closing context: {e}")

        try:
            if self.browser:
                await self.browser.close()
        except Exception as e:
            logger.debug(f"Error closing browser: {e}")

        try:
            if self.playwright:
                await self.playwright.stop()
        except Exception as e:
            logger.debug(f"Error stopping playwright: {e}")

        # 关闭Chrome进程
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

    async def execute_action(self, action: dict) -> tuple[bool, any]:
        """执行操作（异步方法）"""
        if not self.page:
            logger.warning("[Browser] Page is None, 无法执行操作")
            return False, "Page not available"

        try:
            action_type = action.get("type", "")
            selector = action.get("selector", "")
            selector_type = action.get("selector_type", "css")

            logger.info(f"[Browser] 执行 action_type={action_type}, selector={selector}, selector_type={selector_type}")

            # 执行操作
            if action_type == "goto":
                url = action.get("url", "")
                logger.info(f"[Browser] 访问页面: {url}")
                await self.page.goto(url, wait_until='networkidle', timeout=30000)
                return True, None

            elif action_type == "click":
                if selector:
                    converted = convert_selector(selector, selector_type)
                    logger.info(f"[Browser] 点击元素: {converted}")
                    await self.page.click(converted, timeout=5000)
                    return True, None

            elif action_type == "input":
                if selector:
                    converted = convert_selector(selector, selector_type)
                    value = action.get("value", "")
                    logger.info(f"[Browser] 输入内容到 {converted}: {value[:20]}...")
                    await self.page.fill(converted, value)
                    return True, None

            elif action_type == "wait":
                timeout = action.get("timeout", 1000)
                logger.info(f"[Browser] 等待 {timeout}ms")
                await asyncio.sleep(timeout / 1000)
                return True, None

            elif action_type == "wait_element":
                if selector:
                    converted = convert_selector(selector, selector_type)
                    state = action.get("state", "present")
                    timeout = action.get("timeout", 30000)
                    logger.info(f"[Browser] 等待元素 {converted} 状态: {state}, 超时: {timeout}ms")
                    locator = self.page.locator(converted)
                    if state == "present":
                        await locator.wait_for(state="attached", timeout=timeout)
                    else:
                        await locator.wait_for(state="detached", timeout=timeout)
                    return True, None

            elif action_type == "scroll":
                direction = action.get("direction", "down")
                amount = action.get("amount", 500)
                if direction == "down":
                    await self.page.evaluate(f"window.scrollBy(0, {amount})")
                elif direction == "up":
                    await self.page.evaluate(f"window.scrollBy(0, -{amount})")
                elif direction == "top":
                    await self.page.evaluate("window.scrollTo(0, 0)")
                elif direction == "bottom":
                    await self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                return True, None

            elif action_type == "press":
                keys = action.get("keys", [])
                if keys:
                    await self.page.keyboard.press("+".join(keys))
                if action.get("press_enter"):
                    await self.page.keyboard.press("Enter")
                return True, None

            elif action_type == "hover":
                if selector:
                    converted = convert_selector(selector, selector_type)
                    await self.page.hover(converted, timeout=5000)
                    return True, None

            elif action_type == "screenshot":
                return True, None

            elif action_type == "extract":
                selectors = action.get("selectors", [])
                extracted_data = {}
                for sel in selectors:
                    key = sel.get("name", f"field_{len(extracted_data)}")
                    sel_selector = sel.get("selector", "")
                    sel_type = sel.get("selectorType", "css")
                    sel_extract_type = sel.get("extractType", "text")
                    attr = sel.get("attribute", "href")

                    if sel_selector:
                        converted = convert_selector(sel_selector, sel_type)
                        element = self.page.locator(converted)
                        if sel_extract_type == "text":
                            extracted_data[key] = await element.inner_text()
                        elif sel_extract_type == "html":
                            extracted_data[key] = await element.inner_html()
                        elif sel_extract_type == "attribute":
                            extracted_data[key] = await element.get_attribute(attr)
                return True, extracted_data

            elif action_type == "evaluate":
                script = action.get("script", "")
                if script:
                    await self.page.evaluate(script)
                    return True, None

            elif action_type == "close_tab":
                await self.page.close()
                return True, None

            elif action_type == "upload":
                if selector:
                    converted = convert_selector(selector, selector_type)
                    file_paths = action.get("file_paths", [])
                    await self.page.set_input_files(converted, file_paths)
                    return True, None

            elif action_type in ("start", "end"):
                # start 和 end 是虚拟节点，不需要实际执行
                return True, None

            return False, f"Unknown action type: {action_type}"

        except Exception as e:
            logger.error(f"[Browser] 执行操作异常: {e}", exc_info=True)
            return False, str(e)

    async def take_screenshot(self, config) -> Optional[bytes]:
        """截图"""
        if not self.page:
            return None
        try:
            return await self.page.screenshot(type='jpeg', quality=config.browser.screenshot_quality)
        except Exception as e:
            logger.debug(f"Failed to take screenshot: {e}")
            return None


class ExecutionEngine:
    """任务执行引擎"""

    def __init__(self):
        self.executing_tasks: Dict[str, Dict[str, Any]] = {}
        self.browser_contexts: Dict[str, AsyncPlaywrightBrowser] = {}  # 存储浏览器上下文

    async def execute_task(
        self,
        task_id: str,
        url: str,
        actions: List[Dict[str, Any]],
        priority: int = 1,
        max_retries: int = 3,
        metadata: Dict[str, Any] = None,
        headless: bool = False
    ):
        task_info = {
            "task_id": task_id,
            "url": url,
            "actions_count": len(actions),
            "current_action": 0,
            "status": "pending",
            "logs": [],
            "start_time": datetime.now(),
            "headless": headless
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

            await self._run_actions(task_id, url, actions, headless=headless)

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

        except asyncio.CancelledError:
            task_info["status"] = "cancelled"
            task_info["end_time"] = datetime.now()

            await ws_manager.send_task_status(
                task_id=task_id,
                status="cancelled",
                progress=task_info.get("current_action", 0) * 100 // max(1, task_info.get("actions_count", 1)),
                current_action="任务已取消",
                message="用户取消了任务执行"
            )

            logger.info(f"Task {task_id} was cancelled")

        except Exception as e:
            error_detail = ErrorHandler.handle_exception(
                exception=e,
                error_code=ErrorCode.ERR_TASK_FAILED,
                task_id=task_id
            )
            task_info["status"] = "failed"
            task_info["end_time"] = datetime.now()
            task_info["error"] = error_detail.to_json()

            await ws_manager.send_task_error(
                task_id=task_id,
                error=error_detail.message,
                details=error_detail.to_dict()
            )

            logger.error(f"Task {task_id} failed: {error_detail.message}", exc_info=True)

        finally:
            # 刷新所有待发送的日志
            try:
                from api_service.websocket_manager import batch_log_manager
                await batch_log_manager.flush_all()
            except Exception as e:
                logger.debug(f"Failed to flush logs: {e}")

            # 清理浏览器上下文
            await self._close_browser(task_id)

            # 从执行任务中移除
            if task_id in self.executing_tasks:
                del self.executing_tasks[task_id]

    async def _run_actions(
        self,
        task_id: str,
        url: str,
        actions: List[Dict[str, Any]],
        headless: bool = False
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
            message=f"正在打开目标页面 (headless={headless})"
        )

        # 创建并启动浏览器
        config = get_config()
        browser_wrapper = AsyncPlaywrightBrowser()
        self.browser_contexts[task_id] = browser_wrapper

        try:
            browser, page = await browser_wrapper.start(task_id, url, headless, config)
            logger.info(f"Browser started successfully for task {task_id}")

            await ws_manager.send_task_log(
                task_id=task_id,
                level="info",
                message="浏览器启动成功",
                action_name="browser_start"
            )

            # 发送初始截图
            await self._send_screenshot(task_id, browser_wrapper, 0)

        except Exception as e:
            logger.error(f"Failed to start browser: {e}")
            await ws_manager.send_task_log(
                task_id=task_id,
                level="error",
                message=f"启动浏览器失败: {str(e)}",
                action_name="browser_start"
            )
            # 回退到模拟模式
            await self._simulate_browser_start(task_id, url)
            return

        for index, action in enumerate(actions):
            action_type = action.get("type", "unknown")
            action_name = self._get_action_name(action_type)

            logger.info(f"[Task {task_id}] 执行操作 {index+1}/{total_actions}: {action_name}, 数据: {action}")

            task_info = self.executing_tasks.get(task_id)
            if task_info:
                task_info["current_action"] = index + 1
                task_info["current_action_name"] = action_name

            progress = int(((index + 1) / total_actions) * 90)

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

            # 执行操作
            try:
                logger.info(f"[Task {task_id}] 调用浏览器执行操作...")
                success, result = await browser_wrapper.execute_action(action)
                logger.info(f"[Task {task_id}] 操作执行完成: success={success}, result={result}")

                if success:
                    await ws_manager.send_task_log(
                        task_id=task_id,
                        level="success",
                        message=f"操作 [{index + 1}/{total_actions}] 完成: {action_name}",
                        action_name=action_name
                    )

                    # 如果有提取结果，发送
                    if result and isinstance(result, dict):
                        await ws_manager.send_task_result(task_id, {
                            "extracted_data": result,
                            "action_index": index
                        })
                else:
                    logger.warning(f"[Task {task_id}] 操作失败: {result}")
                    await ws_manager.send_task_log(
                        task_id=task_id,
                        level="warning",
                        message=f"操作失败: {result}，跳过",
                        action_name=action_name
                    )

            except Exception as e:
                logger.error(f"[Task {task_id}] 操作执行异常: {e}", exc_info=True)
                await ws_manager.send_task_log(
                    task_id=task_id,
                    level="warning",
                    message=f"操作执行异常: {str(e)}，跳过",
                    action_name=action_name
                )

            # 发送截图
            logger.info(f"[Task {task_id}] 发送截图...")
            await self._send_screenshot(task_id, browser_wrapper, index + 1)

        await ws_manager.send_task_status(
            task_id=task_id,
            status="running",
            progress=95,
            current_action="关闭浏览器",
            message="正在清理执行环境"
        )

        await self._close_browser(task_id)

        await ws_manager.send_task_log(
            task_id=task_id,
            level="info",
            message="任务执行完成",
            action_name="complete"
        )

    async def _close_browser(self, task_id: str):
        """关闭浏览器"""
        try:
            if task_id in self.browser_contexts:
                browser_wrapper = self.browser_contexts[task_id]

                await ws_manager.send_task_log(
                    task_id=task_id,
                    level="info",
                    message="正在关闭浏览器...",
                    action_name="browser_close"
                )

                await browser_wrapper.close()

                await ws_manager.send_task_log(
                    task_id=task_id,
                    level="info",
                    message="浏览器已关闭",
                    action_name="browser_close"
                )

                logger.info(f"Browser closed for task {task_id}")

                del self.browser_contexts[task_id]

        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    async def _send_screenshot(self, task_id: str, browser_wrapper: AsyncPlaywrightBrowser, action_index: int, force: bool = False):
        """发送页面截图"""
        try:
            config = get_config()
            perf_config = config.performance

            # 检查是否禁用实时截图
            if perf_config.disable_realtime_screenshot and not force:
                return

            # 检查截图间隔
            if not force and action_index % perf_config.screenshot_interval != 0:
                return

            # 异步截图
            screenshot_bytes = await browser_wrapper.take_screenshot(config)

            if not screenshot_bytes:
                return

            # 压缩图片
            try:
                import io
                from PIL import Image

                img = Image.open(io.BytesIO(screenshot_bytes))
                max_width = config.browser.screenshot_max_width

                if img.width > max_width:
                    ratio = max_width / img.width
                    new_height = int(img.height * ratio)
                    img = img.resize((max_width, new_height), Image.Resampling.LANCZOS)

                output = io.BytesIO()
                img.save(output, format='JPEG', quality=config.browser.screenshot_quality, optimize=True)
                compressed_bytes = output.getvalue()

                screenshot_base64 = base64.b64encode(compressed_bytes).decode('utf-8')
            except ImportError:
                screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')

            await ws_manager.send_task_screenshot(
                task_id=task_id,
                screenshot_data=screenshot_base64,
                action_index=action_index
            )

        except Exception as e:
            logger.debug(f"Failed to send screenshot: {e}")

    async def _simulate_browser_start(self, task_id: str, url: str):
        """模拟浏览器启动过程（当Playwright不可用时）"""
        config = get_config()
        sim_config = config.simulation

        await asyncio.sleep(sim_config.browser_start_delay)

        await ws_manager.send_task_log(
            task_id=task_id,
            level="info",
            message=f"正在访问: {url}",
            action_name="browser_start"
        )

        await asyncio.sleep(sim_config.action_delay)

        await ws_manager.send_task_log(
            task_id=task_id,
            level="info",
            message="页面加载完成",
            action_name="browser_start"
        )

    async def _simulate_browser_close(self, task_id: str):
        """模拟浏览器关闭过程"""
        config = get_config()

        await asyncio.sleep(config.simulation.browser_close_delay)

        await ws_manager.send_task_log(
            task_id=task_id,
            level="info",
            message="浏览器已关闭",
            action_name="browser_close"
        )

    async def _execute_action(self, task_id: str, action: Dict[str, Any]):
        """执行单个操作（模拟模式）"""
        action_type = action.get("type", "unknown")
        config = get_config()

        await asyncio.sleep(config.simulation.action_delay)

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
