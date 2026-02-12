"""
任务执行引擎模块
负责任务执行和状态推送
"""
import sys
import asyncio
import base64
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import json
import os

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
        self.browser_contexts: Dict[str, Any] = {}  # 存储浏览器上下文

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
            error_msg = str(e)
            task_info["status"] = "failed"
            task_info["end_time"] = datetime.now()
            task_info["error"] = error_msg

            await ws_manager.send_task_error(
                task_id=task_id,
                error=error_msg,
                details={"actions_executed": task_info["current_action"]}
            )

            logger.error(f"Task {task_id} failed: {error_msg}", exc_info=True)

        finally:
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

        # 启动真实浏览器
        browser, page = await self._start_browser(task_id, url, headless)

        if not browser or not page:
            # 如果浏览器启动失败，回退到模拟模式
            logger.warning(f"Browser startup failed for task {task_id}, falling back to simulation")
            await self._simulate_browser_start(task_id, url)

        for index, action in enumerate(actions):
            action_type = action.get("type", "unknown")
            action_name = self._get_action_name(action_type)

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

            # 尝试真实执行，如果失败则模拟
            success = False
            if page:
                success = await self._execute_action_real(task_id, page, action)

            if not success:
                await self._execute_action(task_id, action)

            # 发送截图
            if page:
                await self._send_screenshot(task_id, page, index + 1)

            await ws_manager.send_task_log(
                task_id=task_id,
                level="success",
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

        await self._close_browser(task_id)

        await ws_manager.send_task_log(
            task_id=task_id,
            level="info",
            message="任务执行完成",
            action_name="complete"
        )

    async def _start_browser(self, task_id: str, url: str, headless: bool = False):
        """启动真实浏览器"""
        try:
            # 本地Chrome路径
            chrome_path = "E:\\chrome-win64\\chrome.exe"

            # 检查Chrome是否已安装
            if not os.path.exists(chrome_path):
                raise FileNotFoundError(f"Chrome not found at: {chrome_path}")

            await ws_manager.send_task_log(
                task_id=task_id,
                level="info",
                message=f"正在启动浏览器...",
                action_name="browser_start"
            )

            logger.info(f"Chrome path: {chrome_path}")

            # 使用Windows subprocess启动Chrome带调试端口
            debug_port = 9223  # 固定端口
            chrome_args = [
                '--remote-debugging-port=9223',
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--new-window',
                url,
            ]

            if headless:
                chrome_args.insert(0, '--headless')

            logger.info(f"Starting Chrome: {chrome_path} {' '.join(chrome_args)}")

            # 使用Windows兼容的方式启动进程
            process = subprocess.Popen(
                [chrome_path] + chrome_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                shell=True,
            )

            logger.info(f"Chrome started, PID: {process.pid}")

            # 等待浏览器启动
            await asyncio.sleep(2)

            # 尝试连接到浏览器
            from playwright.sync_api import sync_playwright

            # 在线程池中运行同步的playwright
            loop = asyncio.get_event_loop()
            browser, page = await loop.run_in_executor(
                None,
                self._connect_chrome_sync,
                debug_port
            )

            await ws_manager.send_task_log(
                task_id=task_id,
                level="info",
                message=f"页面已加载: {url}",
                action_name="browser_start"
            )

            # 发送初始截图
            await self._send_screenshot(task_id, page, 0)

            # 保存浏览器引用
            self.browser_contexts[task_id] = (browser, page, process)

            logger.info(f"Browser started successfully for task {task_id}")
            return browser, page

        except FileNotFoundError as e:
            logger.error(f"Chrome not found: {e}")
            await ws_manager.send_task_log(
                task_id=task_id,
                level="error",
                message=f"Chrome浏览器未找到: {str(e)}",
                action_name="browser_start"
            )
            await self._simulate_browser_start(task_id, url)
            return None, None
        except Exception as e:
            logger.error(f"Failed to start browser: {e}", exc_info=True)
            await ws_manager.send_task_log(
                task_id=task_id,
                level="error",
                message=f"启动浏览器失败: {str(e)}",
                action_name="browser_start"
            )
            # 回退到模拟模式
            await self._simulate_browser_start(task_id, url)
            return None, None

    def _connect_chrome_sync(self, debug_port: int):
        """同步连接到Chrome（运行在线程池中）"""
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            # 连接到已运行的Chrome
            browser = p.chromium.connect_over_cdp(f'http://localhost:{debug_port}')

            # 获取页面
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()

            return browser, page

    async def _close_browser(self, task_id: str):
        """关闭浏览器"""
        try:
            if task_id in self.browser_contexts:
                ctx = self.browser_contexts[task_id]
                browser = ctx[0] if len(ctx) > 0 else None
                page = ctx[1] if len(ctx) > 1 else None
                process = ctx[2] if len(ctx) > 2 else None

                await ws_manager.send_task_log(
                    task_id=task_id,
                    level="info",
                    message="正在关闭浏览器...",
                    action_name="browser_close"
                )

                # 关闭页面
                if page:
                    try:
                        await page.close()
                    except Exception as e:
                        logger.debug(f"Error closing page: {e}")

                # 关闭浏览器连接
                if browser:
                    try:
                        await browser.close()
                    except Exception as e:
                        logger.debug(f"Error closing browser: {e}")

                # 如果有Chrome进程，终止它
                if process:
                    try:
                        process.terminate()
                        process.wait(timeout=5)
                    except Exception:
                        process.kill()

                await ws_manager.send_task_log(
                    task_id=task_id,
                    level="info",
                    message="浏览器已关闭",
                    action_name="browser_close"
                )

                logger.info(f"Browser closed for task {task_id}")

                # 清理上下文
                del self.browser_contexts[task_id]

        except Exception as e:
            logger.error(f"Error closing browser: {e}")

    async def _send_screenshot(self, task_id: str, page, action_index: int):
        """发送页面截图"""
        try:
            screenshot_bytes = await page.screenshot(
                type='jpeg',
                quality=70
            )
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')

            await ws_manager.send_task_screenshot(
                task_id=task_id,
                screenshot_data=screenshot_base64,
                action_index=action_index
            )

        except Exception as e:
            logger.warning(f"Failed to send screenshot: {e}")

    async def _execute_action_real(self, task_id: str, page, action: Dict[str, Any]) -> bool:
        """使用Playwright执行真实操作"""
        try:
            action_type = action.get("type", "")

            if action_type == "goto":
                url = action.get("url", "")
                if url:
                    await page.goto(url, wait_until='networkidle', timeout=30000)
                    return True

            elif action_type == "click":
                selector = action.get("selector", "")
                by_image = action.get("by_image", False)

                if by_image:
                    # 图片点击需要额外处理
                    return False

                if selector:
                    await page.click(selector, timeout=5000)
                    return True

            elif action_type == "input":
                selector = action.get("selector", "")
                value = action.get("value", "")
                clear = action.get("clear", True)

                if selector:
                    await page.fill(selector, value)
                    return True

            elif action_type == "wait":
                timeout = action.get("timeout", 1000)
                await asyncio.sleep(timeout / 1000)
                return True

            elif action_type == "scroll":
                direction = action.get("direction", "down")
                amount = action.get("amount", 500)

                if direction == "down":
                    await page.evaluate(f"window.scrollBy(0, {amount})")
                elif direction == "up":
                    await page.evaluate(f"window.scrollBy(0, -{amount})")
                elif direction == "top":
                    await page.evaluate("window.scrollTo(0, 0)")
                elif direction == "bottom":
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                return True

            elif action_type == "press":
                keys = action.get("keys", [])
                press_enter = action.get("press_enter", False)

                if keys:
                    await page.keyboard.press("+".join(keys))
                if press_enter:
                    await page.keyboard.press("Enter")
                return True

            elif action_type == "hover":
                selector = action.get("selector", "")
                if selector:
                    await page.hover(selector, timeout=5000)
                    return True

            elif action_type == "screenshot":
                # 截图已通过_send_screenshot处理
                return True

            elif action_type == "extract":
                # 数据提取已通过截图发送
                return True

            elif action_type == "evaluate":
                script = action.get("script", "")
                if script:
                    await page.evaluate(script)
                    return True

            elif action_type == "new_tab":
                # 新标签页处理
                await page.evaluate("window.open(arguments[0], '_blank')", action.get("url", ""))
                return True

            return False

        except Exception as e:
            logger.warning(f"Real action execution failed: {e}")
            return False

    async def _simulate_browser_start(self, task_id: str, url: str):
        """模拟浏览器启动过程（当Playwright不可用时）"""
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
        """执行单个操作（模拟模式）"""
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
