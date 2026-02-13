"""
任务执行引擎模块
使用子进程方式运行浏览器，避免 asyncio 子进程兼容性问题
"""
import sys
import asyncio
import base64
import subprocess
import json
import signal
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime
import logging
import os
import uuid

from fastapi import BackgroundTasks

sys.path.insert(0, str(Path(__file__).parent.parent))

from scrapy_project.utils.scheduler import TaskStatus, TaskPriority
from scrapy_project.utils.storage import storage_manager
from api_service.websocket_manager import ws_manager, WebSocketMessageType
from api_service.config import get_config
from api_service.errors import ErrorCode, ErrorHandler, ErrorDetail

logger = logging.getLogger(__name__)


def convert_selector(selector: str, selector_type: str = "css") -> str:
    """将不同类型的选择器转换为Playwright可识别的格式"""
    if not selector:
        return selector

    selector_type = selector_type.lower() if selector_type else "css"

    if selector_type == "xpath":
        return selector
    elif selector_type == "id":
        if not selector.startswith("#"):
            return f"#{selector}"
        return selector
    elif selector_type == "class":
        if not selector.startswith("."):
            classes = selector.split()
            return ".".join(classes) if classes else f".{selector}"
        return selector
    elif selector_type == "name":
        return f'[name="{selector}"]'
    else:
        return selector


class SubprocessBrowser:
    """使用子进程运行浏览器的控制器"""

    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.port: Optional[int] = None
        self.task_id: Optional[str] = None
        self._input_reader = None
        self._output_writer = None
        self._stderr_reader_task = None

    def _find_free_port(self) -> int:
        """查找可用端口"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    async def start(self, task_id: str, url: str, headless: bool = False, config=None,
                    browser_config: dict = None) -> bool:
        """启动浏览器子进程"""
        chrome_path = config.browser.chrome_path
        if not os.path.exists(chrome_path):
            raise FileNotFoundError(f"Chrome not found at: {chrome_path}")

        self.task_id = task_id
        self.port = self._find_free_port()

        logger.info(f"[Browser] 启动 Chrome: {chrome_path}, 端口: {self.port}")

        # 获取当前文件目录，构建浏览器控制器路径
        controller_path = Path(__file__).parent / "browser_controller.py"

        # 启动子进程
        self.process = subprocess.Popen(
            [sys.executable, str(controller_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=0  # 行缓冲
        )

        logger.info(f"[Browser] 子进程已启动, PID: {self.process.pid}")

        # 启动 stderr 读取任务
        self._stderr_reader_task = asyncio.create_task(self._read_stderr())

        # 等待子进程初始化
        await asyncio.sleep(0.5)

        # 获取反检测配置
        if browser_config:
            enable_stealth = browser_config.get("enable_stealth", config.browser.enable_stealth)
            viewport_width = browser_config.get("viewport_width", config.browser.viewport_width)
            viewport_height = browser_config.get("viewport_height", config.browser.viewport_height)
            user_agent = browser_config.get("user_agent", config.browser.user_agent)
            locale = browser_config.get("locale", config.browser.locale)
            timezone = browser_config.get("timezone", config.browser.timezone)
        else:
            enable_stealth = config.browser.enable_stealth
            viewport_width = config.browser.viewport_width
            viewport_height = config.browser.viewport_height
            user_agent = config.browser.user_agent
            locale = config.browser.locale
            timezone = config.browser.timezone

        # 发送启动命令
        start_cmd = {
            "cmd": "start",
            "chrome_path": chrome_path,
            "port": self.port,
            "url": url,
            "enable_stealth": enable_stealth,
            "viewport_width": viewport_width,
            "viewport_height": viewport_height,
            "user_agent": user_agent,
            "locale": locale,
            "timezone": timezone
        }
        logger.info(f"[Browser] 发送启动命令...")
        await self._send_command(start_cmd)

        # 等待响应
        response = await self._read_response()
        logger.info(f"[Browser] 启动响应: {response}")

        if not response.get("success"):
            error = response.get("error", "Unknown error")
            logger.error(f"[Browser] 启动失败: {error}")
            # 启动失败不需要关闭browser，因为browser还没有启动
            raise Exception(f"浏览器启动失败: {error}")

        logger.info(f"[Browser] 浏览器启动成功")
        return True

    async def execute_action(self, action: dict) -> tuple[bool, any]:
        """执行操作"""
        cmd = {
            "cmd": "action",
            "action": action
        }

        logger.debug(f"[Browser] 发送动作命令: {action.get('type')}")
        await self._send_command(cmd)

        response = await self._read_response()
        logger.info(f"[Browser] 动作响应: {response}")

        success = response.get("success", False)
        if success:
            # 返回完整的响应数据（排除success字段），让调用方处理不同类型的结果
            result_data = {k: v for k, v in response.items() if k != "success"}
            return success, result_data
        else:
            return success, response.get("error")

    async def take_screenshot(self) -> Optional[bytes]:
        """截图"""
        cmd = {"cmd": "screenshot"}
        await self._send_command(cmd)

        response = await self._read_response()
        if response.get("success") and response.get("screenshot"):
            return base64.b64decode(response["screenshot"])
        return None

    async def close(self):
        """关闭浏览器"""
        logger.info(f"[Browser] 关闭浏览器...")

        # 取消 stderr 读取任务
        if self._stderr_reader_task and not self._stderr_reader_task.done():
            self._stderr_reader_task.cancel()
            try:
                await self._stderr_reader_task
            except asyncio.CancelledError:
                pass

        if self.process:
            # 发送关闭命令
            try:
                await self._send_command({"cmd": "close"}, timeout=2)
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.debug(f"[Browser] 发送关闭命令失败: {e}")

            # 强制终止进程
            try:
                self.process.stdin.close()
                self.process.stdout.close()
                self.process.stderr.close()
            except Exception:
                pass

            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
            except Exception as e:
                logger.debug(f"[Browser] 终止进程失败: {e}")

            self.process = None
            logger.info(f"[Browser] 浏览器已关闭")

    async def _read_stderr(self):
        """读取子进程的 stderr 输出"""
        try:
            while self.process and self.process.poll() is None:
                try:
                    line = await asyncio.wait_for(
                        asyncio.get_event_loop().run_in_executor(None, self.process.stderr.readline),
                        timeout=1.0
                    )
                    if line:
                        # 将 stderr 日志输出到主日志
                        logger.info(f"[BrowserController] {line.strip()}")
                except asyncio.TimeoutError:
                    continue
                except Exception:
                    break
        except Exception as e:
            logger.debug(f"[Browser] stderr 读取结束: {e}")

    async def _send_command(self, cmd: dict, timeout: float = 10.0):
        """发送命令到子进程"""
        if not self.process or self.process.stdin.closed:
            raise Exception("子进程已关闭")

        line = json.dumps(cmd) + "\n"
        self.process.stdin.write(line)
        self.process.stdin.flush()
        logger.debug(f"[Browser] 已发送命令: {cmd.get('cmd')}")

    async def _read_response(self, timeout: float = 30.0) -> dict:
        """读取子进程响应"""
        if not self.process:
            raise Exception("子进程不存在")

        line = await asyncio.wait_for(
            asyncio.get_event_loop().run_in_executor(None, self.process.stdout.readline),
            timeout=timeout
        )

        if not line:
            raise Exception("子进程无响应")

        line = line.strip()
        if not line:
            return {}

        try:
            return json.loads(line)
        except json.JSONDecodeError as e:
            logger.error(f"[Browser] 解析响应失败: {e}, 内容: {line[:200]}")
            raise


class ExecutionEngine:
    """任务执行引擎"""

    def __init__(self):
        self.executing_tasks: Dict[str, Dict[str, Any]] = {}
        self.browser_contexts: Dict[str, SubprocessBrowser] = {}

    async def execute_task(
        self,
        task_id: str,
        url: str,
        actions: List[Dict[str, Any]],
        priority: int = 1,
        max_retries: int = 3,
        metadata: Dict[str, Any] = None,
        headless: bool = False,
        browser_config: dict = None
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
        logger.info(f"[Task {task_id}] execute_task 开始, URL: {url}, 动作数: {len(actions)}")

        try:
            await ws_manager.send_task_status(
                task_id=task_id,
                status="starting",
                progress=0,
                current_action="初始化任务",
                message="正在准备执行环境"
            )

            await self._run_actions(task_id, url, actions, headless=headless, browser_config=browser_config)

            # 检查任务状态，避免覆盖失败状态
            # _run_actions 内部可能会设置 status = "failed"
            if task_info.get("status") != "failed":
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
            logger.warning(f"[Task {task_id}] 任务被取消 (CancelledError)")

            await ws_manager.send_task_status(
                task_id=task_id,
                status="cancelled",
                progress=task_info.get("current_action", 0) * 100 // max(1, task_info.get("actions_count", 1)),
                current_action="任务已取消",
                message="用户取消了任务执行"
            )

            logger.info(f"Task {task_id} was cancelled")

        except Exception as e:
            logger.error(f"[Task {task_id}] 任务执行异常: {type(e).__name__}: {e}", exc_info=True)
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
            try:
                from api_service.websocket_manager import batch_log_manager
                await batch_log_manager.flush_all()
            except Exception as e:
                logger.debug(f"Failed to flush logs: {e}")

            await self._close_browser(task_id)

            if task_id in self.executing_tasks:
                del self.executing_tasks[task_id]

    async def _run_actions(
        self,
        task_id: str,
        url: str,
        actions: List[Dict[str, Any]],
        headless: bool = False,
        browser_config: dict = None
    ):
        total_actions = len(actions)
        logger.info(f"[Task {task_id}] _run_actions 开始执行, 共 {total_actions} 个动作, URL: {url}")

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

        config = get_config()
        browser = SubprocessBrowser()
        self.browser_contexts[task_id] = browser

        try:
            await browser.start(task_id, url, headless, config, browser_config)
            logger.info(f"[Task {task_id}] 浏览器启动成功")

            await ws_manager.send_task_log(
                task_id=task_id,
                level="info",
                message="浏览器启动成功",
                action_name="browser_start"
            )

            # 发送初始截图
            await self._send_screenshot(task_id, browser, 0)

        except Exception as e:
            logger.error(f"[Task {task_id}] 启动浏览器失败: {e}")
            await ws_manager.send_task_log(
                task_id=task_id,
                level="error",
                message=f"启动浏览器失败: {str(e)}",
                action_name="browser_start"
            )
            await self._simulate_browser_start(task_id, url)
            return

        for index, action in enumerate(actions):
            # 检查任务是否被取消
            task_info = self.executing_tasks.get(task_id)
            if task_info and task_info.get("status") == "cancelled":
                logger.info(f"[Task {task_id}] 任务已取消，停止执行")
                await ws_manager.send_task_log(
                    task_id=task_id,
                    level="warning",
                    message="任务已被用户取消",
                    action_name="cancelled"
                )
                break

            action_type = action.get("type", "unknown")
            action_name = self._get_action_name(action_type)

            logger.info(f"[Task {task_id}] 执行操作 {index+1}/{total_actions}: {action_name}")
            logger.debug(f"[Task {task_id}] 操作详情: {action}")

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
                action_name=action_name
            )

            action_failed = False
            action_error = None

            try:
                success, result = await browser.execute_action(action)
                logger.info(f"[Task {task_id}] 操作执行完成: success={success}, result={result}")

                if success:
                    await ws_manager.send_task_log(
                        task_id=task_id,
                        level="success",
                        message=f"操作 [{index + 1}/{total_actions}] 完成: {action_name}",
                        action_name=action_name
                    )

                    if result and isinstance(result, dict):
                        # 如果是截图操作，单独处理
                        if result.get("screenshot"):
                            await ws_manager.send_task_screenshot(
                                task_id=task_id,
                                screenshot_data=result["screenshot"],
                                action_index=index
                            )
                            if result.get("saved_path"):
                                await ws_manager.send_task_log(
                                    task_id=task_id,
                                    level="info",
                                    message=f"截图已保存到: {result['saved_path']}",
                                    action_name=action_name
                                )
                        else:
                            await ws_manager.send_task_result(task_id, {
                                "extracted_data": result,
                                "action_index": index
                            })
                else:
                    # 操作失败，停止执行
                    logger.warning(f"[Task {task_id}] 操作失败: {result}")
                    await ws_manager.send_task_log(
                        task_id=task_id,
                        level="error",
                        message=f"操作失败: {result}",
                        action_name=action_name
                    )
                    action_failed = True
                    action_error = result

            except Exception as e:
                # 操作异常，停止执行
                logger.error(f"[Task {task_id}] 操作执行异常: {e}", exc_info=True)
                await ws_manager.send_task_log(
                    task_id=task_id,
                    level="error",
                    message=f"操作执行异常: {str(e)}",
                    action_name=action_name
                )
                action_failed = True
                action_error = str(e)

            # 如果操作失败，停止执行整个任务
            if action_failed:
                logger.error(f"[Task {task_id}] 任务执行失败，停止后续操作")
                await ws_manager.send_task_log(
                    task_id=task_id,
                    level="error",
                    message="任务执行中止，已停止后续操作",
                    action_name="task_aborted"
                )
                await self._close_browser(task_id)

                # 更新任务状态为失败
                task_info["status"] = "failed"
                task_info["end_time"] = datetime.now()
                task_info["error"] = f"操作 {action_name} 执行失败: {action_error}"

                await ws_manager.send_task_status(
                    task_id=task_id,
                    status="failed",
                    progress=int(((index + 1) / total_actions) * 100),
                    current_action="任务失败",
                    message=f"操作 {action_name} 执行失败，任务已中止"
                )

                # 清理并返回
                if task_id in self.executing_tasks:
                    del self.executing_tasks[task_id]
                return

            await self._send_screenshot(task_id, browser, index + 1)

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
                browser = self.browser_contexts[task_id]

                await ws_manager.send_task_log(
                    task_id=task_id,
                    level="info",
                    message="正在关闭浏览器...",
                    action_name="browser_close"
                )

                await browser.close()

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

    async def _send_screenshot(self, task_id: str, browser: SubprocessBrowser, action_index: int, force: bool = False):
        """发送页面截图"""
        try:
            config = get_config()
            perf_config = config.performance

            if perf_config.disable_realtime_screenshot and not force:
                return

            if not force and action_index % perf_config.screenshot_interval != 0:
                return

            screenshot_bytes = await browser.take_screenshot()

            if not screenshot_bytes:
                return

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
        """模拟浏览器启动过程"""
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
            message="页面加载完成（模拟模式）",
            action_name="browser_start"
        )

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
