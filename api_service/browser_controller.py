#!/usr/bin/env python3
"""
独立浏览器控制器
通过 stdin/stdout 与主进程通信，避免 asyncio 子进程兼容性问题
"""
import sys
import json
import asyncio
import logging
import signal
import os
import subprocess

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stderr
)
logger = logging.getLogger(__name__)


class BrowserController:
    def __init__(self):
        self.browser = None
        self.page = None
        self.context = None
        self.playwright = None
        self.running = True
        self.process = None  # Chrome 进程

    def convert_selector(self, selector: str, selector_type: str = "css") -> str:
        """转换选择器"""
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

    def start_browser(self, chrome_path: str, port: int, url: str = None,
                       enable_stealth: bool = True, viewport_width: int = 1920,
                       viewport_height: int = 1080, user_agent: str = None,
                       locale: str = "zh-CN", timezone: str = "Asia/Shanghai") -> dict:
        """启动 Chrome - 同步版本"""
        logger.info(f"[BrowserController] 启动 Chrome: {chrome_path}, 端口: {port}, stealth: {enable_stealth}")

        if enable_stealth:
            # 使用 undetected-playwright 自动应用所有反检测措施
            return self._start_browser_stealth(
                chrome_path, port, url, viewport_width, viewport_height,
                user_agent, locale, timezone
            )
        else:
            # 使用原来的方式启动
            return self._start_browser_normal(
                chrome_path, port, url, viewport_width, viewport_height,
                user_agent, locale, timezone
            )

    def _start_browser_stealth(self, chrome_path: str, port: int, url: str = None,
                                 viewport_width: int = 1920, viewport_height: int = 1080,
                                 user_agent: str = None, locale: str = "zh-CN",
                                 timezone: str = "Asia/Shanghai") -> dict:
        """使用 undetected-playwright 启动浏览器"""
        try:
            import undetected_playwright as uc
        except ImportError:
            logger.warning("undetected-playwright 未安装，回退到普通模式")
            return self._start_browser_normal(
                chrome_path, port, url, viewport_width, viewport_height,
                user_agent, locale, timezone
            )

        try:
            logger.info("[BrowserController] 使用 undetected-playwright 启动浏览器")
            self.playwright = uc.sync_playwright().start()
            # launch_persistent_context 会保留 cookie 和 session
            self.browser = self.playwright.chromium.launch(
                headless=False,
                executable_path=chrome_path,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',
                ]
            )

            # 创建上下文
            context_options = {
                'viewport': {'width': viewport_width, 'height': viewport_height},
                'locale': locale,
                'timezone_id': timezone,
                'geolocation': {'latitude': 31.2304, 'longitude': 121.4737},
                'permissions': ['geolocation'],
                'ignore_https_errors': True,
            }
            if user_agent:
                context_options['user_agent'] = user_agent

            self.context = self.browser.new_context(**context_options)
            self.page = self.context.new_page()

            # 注入额外的反检测脚本
            self.context.add_init_script(self._get_stealth_script())

            if url:
                self.page.goto(url, wait_until='networkidle', timeout=30000)
                # 等待页面渲染完成
                self.page.wait_for_timeout(500)
                logger.info(f"[BrowserController] 已访问页面: {url}")

            logger.info("[BrowserController] undetected-playwright 浏览器启动成功")
            return {"success": True, "stealth_mode": True}

        except Exception as e:
            logger.error(f"[BrowserController] undetected-playwright 启动失败: {e}, 回退到普通模式")
            # 回退到普通模式，保留原来的端口
            return self._start_browser_normal(
                chrome_path, port, url, viewport_width, viewport_height,
                user_agent, locale, timezone
            )

    def _start_browser_normal(self, chrome_path: str, port: int, url: str = None,
                               viewport_width: int = 1920, viewport_height: int = 1080,
                               user_agent: str = None, locale: str = "zh-CN",
                               timezone: str = "Asia/Shanghai",
                               enable_stealth: bool = False) -> dict:
        """普通模式启动 Chrome"""
        from playwright.sync_api import sync_playwright

        # 启动 Chrome 进程
        CREATE_NO_WINDOW = 0x08000000
        chrome_args = [
            f'--remote-debugging-port={port}',
            '--remote-debugging-address=127.0.0.1',
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-gpu',
            '--new-window',
            '--disable-blink-features=AutomationControlled',
            '--disable-infobars',
            '--window-size=1920,1080',
        ]

        self.process = subprocess.Popen(
            [chrome_path] + chrome_args,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            shell=False,
            creationflags=CREATE_NO_WINDOW,
        )
        logger.info(f"[BrowserController] Chrome 已启动, PID: {self.process.pid}")

        # 等待 Chrome 启动并获取 WebSocket URL
        import http.client
        import time
        max_wait = 15
        waited = 0
        ws_url = None

        while waited < max_wait:
            try:
                conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
                conn.request("GET", "/json/version")
                response = conn.getresponse()
                if response.status == 200:
                    data = json.loads(response.read().decode())
                    if data.get("webSocketDebuggerUrl"):
                        ws_url = data["webSocketDebuggerUrl"]
                        logger.info(f"[BrowserController] 获取到 WebSocket URL: {ws_url}")
                        break
            except Exception as e:
                logger.debug(f"[BrowserController] 等待 Chrome... {e}")

            time.sleep(0.5)
            waited += 0.5
            logger.debug(f"[BrowserController] 等待 Chrome 启动... {waited}s")

        if not ws_url:
            return {"success": False, "error": "无法获取 Chrome WebSocket URL"}

        # 连接 Playwright (使用 WebSocket URL)
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.connect_over_cdp(ws_url)

        # 创建上下文时应用反检测配置
        context_options = {}
        if enable_stealth:
            context_options = {
                'viewport': {'width': viewport_width, 'height': viewport_height},
                'locale': locale,
                'timezone_id': timezone,
                'geolocation': {'latitude': 31.2304, 'longitude': 121.4737},  # 上海
                'permissions': ['geolocation'],
            }
            if user_agent:
                context_options['user_agent'] = user_agent

        self.context = self.browser.new_context(**context_options) if context_options else self.browser.new_context()

        # 注入反检测 JavaScript
        if enable_stealth:
            self.context.add_init_script(self._get_stealth_script())

        self.page = self.context.pages[0] if self.context.pages else self.context.new_page()

        if url:
            self.page.goto(url, wait_until='networkidle', timeout=30000)
            # 等待页面渲染完成
            self.page.wait_for_timeout(500)
            logger.info(f"[BrowserController] 已访问页面: {url}")

        logger.info("[BrowserController] 浏览器准备就绪")
        return {"success": True}

    def _get_stealth_script(self) -> str:
        """获取反检测 JavaScript 脚本"""
        return """
        // 隐藏 webdriver 标志
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });

        // 覆盖 chrome.runtime
        if (window.chrome) {
            window.chrome.runtime = {
                connect: function() {},
                sendMessage: function() {}
            };
        }

        // 修改 permissions
        const originalQuery = window.navigator.permissions.query;
        window.navigator.permissions.query = (parameters) => (
            parameters.name === 'notifications' ?
                Promise.resolve({ state: Notification.permission }) :
                originalQuery(parameters)
        );

        // 修改 plugins
        Object.defineProperty(navigator, 'plugins', {
            get: () => [1, 2, 3, 4, 5],
            configurable: true
        });

        // 修改 languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['zh-CN', 'zh', 'en-US', 'en'],
            configurable: true
        });

        // 添加 chrome 属性
        window.chrome = {
            loadTimes: function() {
                return {
                    commit_finished_warmup_time: 0.1,
                    first_paint_after_load_time: 0.1,
                    first_meaningful_paint: 0.1,
                    first_meaningful_paint_candidate: 0.1,
                    first_text_paint: 0.1,
                    load_event_start_time: 0.1,
                    navigation_start: Date.now() - 100
                };
            },
            csi: function() {
                return {
                    onloadT: Date.now() - 100,
                    pageT: Date.now() - 100,
                    tran: 15
                };
            }
        };

        // 覆盖 automation 检测
        window.navigator.__defineGetter__('webdriver', function() {
            return undefined;
        });

        // 修改 getComputedStyle
        const originalGetComputedStyle = window.getComputedStyle;
        window.getComputedStyle = function(element, pseudoElt) {
            const style = originalGetComputedStyle(element, pseudoElt);
            style.display = '';  // 确保 display 不被修改
            return style;
        };

        // 模拟真实的 chrome.automation 对象
        if (!window.chrome.automation) {
            Object.defineProperty(window.chrome, 'automation', {
                get: () => ({
                    isAutomation: false,
                    getAutomationId: () => null
                }),
                configurable: true
            });
        }
        """

    def execute_action(self, action: dict) -> dict:
        """执行操作 - 同步版本"""
        if not self.page:
            return {"success": False, "error": "Page not available"}

        try:
            action_type = action.get("type", "")
            selector = action.get("selector", "")
            selector_type = action.get("selector_type", "css")

            logger.info(f"[BrowserController] 执行动作: {action_type}, selector={selector}, type={selector_type}")

            if action_type == "goto":
                url = action.get("url", "")
                self.page.goto(url, wait_until='networkidle', timeout=30000)
                return {"success": True}

            elif action_type == "click":
                if selector:
                    converted = self.convert_selector(selector, selector_type)
                    try:
                        self.page.click(converted, timeout=5000)
                        return {"success": True}
                    except Exception as e:
                        logger.error(f"[BrowserController] 点击失败: {e}")
                        return {"success": False, "error": str(e)}
                return {"success": False, "error": "未提供选择器"}

            elif action_type == "input":
                if selector:
                    converted = self.convert_selector(selector, selector_type)
                    value = action.get("value", "")
                    clear = action.get("clear", True)

                    if clear:
                        self.page.fill(converted, value)
                    else:
                        # 不清空，直接追加
                        current = self.page.locator(converted).input_value()
                        self.page.fill(converted, current + value)

                    # 检查是否需要按回车
                    if action.get("press_enter"):
                        self.page.press(converted, "Enter")

                    return {"success": True}

            elif action_type == "wait":
                import time
                timeout = action.get("timeout", 1000)
                time.sleep(timeout / 1000)
                return {"success": True}

            elif action_type == "wait_element":
                if selector:
                    try:
                        converted = self.convert_selector(selector, selector_type)
                        state = action.get("state", "present")
                        timeout = action.get("timeout", 30000)
                        locator = self.page.locator(converted)
                        if state == "present":
                            locator.wait_for(state="attached", timeout=timeout)
                        else:
                            locator.wait_for(state="detached", timeout=timeout)
                        return {"success": True}
                    except Exception as e:
                        logger.error(f"[BrowserController] 等待元素失败: {e}")
                        return {"success": False, "error": str(e)}
                return {"success": False, "error": "未提供选择器"}

            elif action_type == "scroll":
                try:
                    direction = action.get("direction", "down")
                    amount = action.get("amount", 500)
                    if direction == "down":
                        self.page.evaluate(f"window.scrollBy(0, {amount})")
                    elif direction == "up":
                        self.page.evaluate(f"window.scrollBy(0, -{amount})")
                    elif direction == "top":
                        self.page.evaluate("window.scrollTo(0, 0)")
                    elif direction == "bottom":
                        self.page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    return {"success": True}
                except Exception as e:
                    logger.error(f"[BrowserController] 滚动失败: {e}")
                    return {"success": False, "error": str(e)}

            elif action_type == "press":
                keys = action.get("keys", [])
                if keys:
                    self.page.keyboard.press("+".join(keys))
                if action.get("press_enter"):
                    self.page.keyboard.press("Enter")
                return {"success": True}

            elif action_type == "hover":
                if selector:
                    try:
                        converted = self.convert_selector(selector, selector_type)
                        self.page.hover(converted, timeout=5000)
                        return {"success": True}
                    except Exception as e:
                        logger.error(f"[BrowserController] 悬停失败: {e}")
                        return {"success": False, "error": str(e)}
                return {"success": False, "error": "未提供选择器"}

            elif action_type == "screenshot":
                if not self.page:
                    logger.error("[BrowserController] 截图失败: Page not available")
                    return {"success": False, "error": "Page not available"}

                try:
                    # 确保页面加载完成
                    try:
                        self.page.wait_for_load_state("domcontentloaded", timeout=5000)
                    except Exception:
                        pass  # 忽略加载状态超时

                    screenshot_type = action.get("screenshotType", "viewport")
                    selector = action.get("selector", "")
                    selector_type = action.get("selector_type", "css")
                    full_page = action.get("fullPage", False)
                    save_path = action.get("savePath", "")

                    logger.info(f"[BrowserController] 截图: action_type={action_type}, screenshotType={screenshot_type}, fullPage={full_page}, selector={selector}, savePath={save_path}")

                    if screenshot_type == "selector" and selector:
                        # 元素截图
                        converted = self.convert_selector(selector, selector_type)
                        element = self.page.locator(converted)
                        screenshot_bytes = element.screenshot(type='jpeg', quality=80)
                    elif full_page or screenshot_type == "fullpage":
                        # 整页截图
                        screenshot_bytes = self.page.screenshot(type='jpeg', quality=80, full_page=True)
                    else:
                        # 可视区域截图
                        screenshot_bytes = self.page.screenshot(type='jpeg', quality=80, full_page=False)

                    # 保存到文件
                    saved_path = ""
                    if save_path:
                        try:
                            import os
                            from pathlib import Path
                            # 如果是相对路径，转换为绝对路径（基于项目根目录）
                            if not os.path.isabs(save_path):
                                # 获取项目根目录
                                project_root = Path(__file__).parent.parent.resolve()
                                save_path = str(project_root / save_path)
                            # 确保目录存在
                            save_dir = os.path.dirname(save_path)
                            if save_dir:
                                os.makedirs(save_dir, exist_ok=True)
                            # 保存文件
                            with open(save_path, 'wb') as f:
                                f.write(screenshot_bytes)
                            saved_path = save_path
                            logger.info(f"[BrowserController] 截图已保存到: {save_path}")
                        except Exception as save_err:
                            logger.warning(f"[BrowserController] 保存截图失败: {save_err}")

                    import base64
                    screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
                    result = {"success": True, "screenshot": screenshot_b64}
                    if saved_path:
                        result["saved_path"] = saved_path
                    logger.info(f"[BrowserController] 截图完成: screenshot_size={len(screenshot_b64)}, saved_path={saved_path}")
                    return result
                except Exception as e:
                    logger.error(f"[BrowserController] 截图失败: {e}", exc_info=True)
                    return {"success": False, "error": str(e)}

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
                        converted = self.convert_selector(sel_selector, sel_type)
                        element = self.page.locator(converted)
                        if sel_extract_type == "text":
                            extracted_data[key] = element.inner_text()
                        elif sel_extract_type == "html":
                            extracted_data[key] = element.inner_html()
                        elif sel_extract_type == "attribute":
                            extracted_data[key] = element.get_attribute(attr)
                return {"success": True, "data": extracted_data}

            elif action_type == "evaluate":
                script = action.get("script", "")
                if script:
                    self.page.evaluate(script)
                    return {"success": True}

            elif action_type == "close_tab":
                self.page.close()
                return {"success": True}

            elif action_type == "upload":
                if selector:
                    converted = self.convert_selector(selector, selector_type)
                    file_paths = action.get("file_paths", [])
                    self.page.set_input_files(converted, file_paths)
                    return {"success": True}

            elif action_type in ("start", "end"):
                return {"success": True}

            return {"success": False, "error": f"Unknown action type: {action_type}"}

        except Exception as e:
            logger.error(f"[BrowserController] 执行动作失败: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def take_screenshot(self) -> dict:
        """截图 - 同步版本（用于实时截图）"""
        if not self.page:
            logger.warning("[BrowserController] take_screenshot: page not available")
            return {"success": False, "error": "Page not available"}

        try:
            # 确保页面加载完成
            try:
                self.page.wait_for_load_state("domcontentloaded", timeout=3000)
            except Exception:
                pass  # 忽略加载状态超时

            screenshot_bytes = self.page.screenshot(type='jpeg', quality=70, full_page=False)
            import base64
            result = {"success": True, "screenshot": base64.b64encode(screenshot_bytes).decode()}
            logger.debug(f"[BrowserController] 截图成功, 大小: {len(screenshot_bytes)} bytes")
            return result
        except Exception as e:
            logger.error(f"[BrowserController] 截图失败: {e}")
            return {"success": False, "error": str(e)}

    def close(self):
        """关闭浏览器"""
        logger.info("[BrowserController] 关闭浏览器...")
        try:
            if self.page:
                self.page.close()
        except Exception as e:
            logger.debug(f"[BrowserController] 关闭 page 失败: {e}")

        try:
            if self.context:
                self.context.close()
        except Exception as e:
            logger.debug(f"[BrowserController] 关闭 context 失败: {e}")

        try:
            if self.browser:
                self.browser.close()
        except Exception as e:
            logger.debug(f"[BrowserController] 关闭 browser 失败: {e}")

        try:
            if self.playwright:
                self.playwright.stop()
        except Exception as e:
            logger.debug(f"[BrowserController] 停止 playwright 失败: {e}")

        # 关闭 Chrome 进程
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass

        logger.info("[BrowserController] 浏览器已关闭")

    def run(self):
        """主循环：通过 stdin/stdout 通信"""
        logger.info("[BrowserController] 启动主循环...")

        while self.running:
            try:
                # 读取命令
                line = sys.stdin.readline()
                if not line:
                    break

                line = line.strip()
                if not line:
                    continue

                logger.debug(f"[BrowserController] 收到命令: {line[:100]}...")

                try:
                    msg = json.loads(line)
                    cmd = msg.get("cmd")

                    if cmd == "start":
                        chrome_path = msg.get("chrome_path")
                        port = msg.get("port")
                        url = msg.get("url")
                        # 反检测配置
                        enable_stealth = msg.get("enable_stealth", True)
                        viewport_width = msg.get("viewport_width", 1920)
                        viewport_height = msg.get("viewport_height", 1080)
                        user_agent = msg.get("user_agent")
                        locale = msg.get("locale", "zh-CN")
                        timezone = msg.get("timezone", "Asia/Shanghai")
                        # 调用同步版本
                        result = self.start_browser(
                            chrome_path, port, url,
                            enable_stealth=enable_stealth,
                            viewport_width=viewport_width,
                            viewport_height=viewport_height,
                            user_agent=user_agent,
                            locale=locale,
                            timezone=timezone
                        )
                        print(json.dumps(result), flush=True)

                    elif cmd == "action":
                        action = msg.get("action")
                        result = self.execute_action(action)
                        print(json.dumps(result), flush=True)

                    elif cmd == "screenshot":
                        result = self.take_screenshot()
                        print(json.dumps(result), flush=True)

                    elif cmd == "close":
                        self.close()
                        print(json.dumps({"success": True}), flush=True)
                        break

                    elif cmd == "ping":
                        print(json.dumps({"success": True, "running": True}), flush=True)

                    else:
                        print(json.dumps({"success": False, "error": f"Unknown cmd: {cmd}"}), flush=True)

                except json.JSONDecodeError as e:
                    logger.error(f"[BrowserController] JSON 解析失败: {e}")
                    print(json.dumps({"success": False, "error": "Invalid JSON"}), flush=True)

                except Exception as e:
                    logger.error(f"[BrowserController] 处理命令失败: {e}", exc_info=True)
                    print(json.dumps({"success": False, "error": str(e)}), flush=True)

            except Exception as e:
                logger.error(f"[BrowserController] 主循环异常: {e}", exc_info=True)
                break

        logger.info("[BrowserController] 退出主循环")


if __name__ == "__main__":
    controller = BrowserController()

    # 注册信号处理
    def signal_handler(sig, frame):
        logger.info(f"[BrowserController] 收到信号: {sig}")
        controller.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    controller.run()
