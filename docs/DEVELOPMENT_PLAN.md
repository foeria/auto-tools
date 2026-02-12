# 自动化任务系统 - 开发方案

## 一、项目概述

本项目是一个基于 Web 的浏览器自动化任务系统，支持：
- 可视化工作流设计器
- 浏览器自动化执行（Chrome + Playwright）
- WebSocket 实时状态推送
- 任务监控与管理

---

## 二、已完成功能清单

### 2.1 前端功能 (admin-frontend)

| 功能模块 | 按钮/功能 | 实现状态 | 说明 |
|---------|----------|---------|------|
| **工作流管理** | 导入 JSON | ✅ 已完成 | 从本地文件导入工作流 |
| | 导出 JSON | ✅ 已完成 | 导出当前工作流 |
| | 保存到本地存储 | ✅ 已完成 | 保存到 localStorage |
| | 从本地存储加载 | ✅ 已完成 | 加载已保存工作流 |
| | 清空画布 | ✅ 已完成 | 删除所有节点 |
| **节点操作** | 拖拽添加节点 | ✅ 已完成 | 从组件库拖拽到画布 |
| | 删除节点 | ✅ 已完成 | 删除节点及连线 |
| | 键盘快捷键 | ✅ 已完成 | Delete/Backspace 删除 |
| **任务执行** | 运行工作流 | ✅ 已完成 | 提交任务到后端 |
| | 有头/无头模式切换 | ✅ 已完成 | headlessMode 参数 |
| | 取消任务 | ✅ 已完成 | 调用 cancel API |
| | 重试任务 | ✅ 已完成 | 调用 retry API |
| **执行监控** | 实时截图预览 | ✅ 已完成 | WebSocket 推送截图 |
| | 任务状态显示 | ✅ 已完成 | pending/running/completed 等 |
| | 执行进度 | ✅ 已完成 | 进度条 + 数字显示 |
| | 日志显示 | ✅ 已完成 | 彩色日志 + 筛选 |
| | 日志导出 | ✅ 已完成 | 导出到 TXT |

### 2.2 后端 API (api_service)

| 端点 | 方法 | 功能 | 实现状态 |
|------|------|------|---------|
| `/api/tasks` | POST | 创建并执行任务 | ✅ 已完成 |
| `/api/tasks` | GET | 列出任务列表 | ✅ 已完成 |
| `/api/tasks/{task_id}` | GET | 获取任务详情 | ✅ 已完成 |
| `/api/tasks/{task_id}/status` | GET | 获取任务状态 | ✅ 已完成 |
| `/api/tasks/{task_id}` | DELETE | 删除任务 | ✅ 已完成 |
| `/api/tasks/{task_id}/retry` | POST | 重试任务 | ✅ 已完成 |
| `/api/tasks/{task_id}/cancel` | POST | 取消任务 | ✅ 已完成 |
| `/api/templates` | GET/POST | 模板管理 | ✅ 已完成 |
| `/api/statistics` | GET | 统计信息 | ✅ 已完成 |
| `/api/executing-tasks` | GET | 执行中任务列表 | ✅ 已完成 |
| `/api/actions` | GET | 可用操作类型 | ✅ 已完成 |
| `/health` | GET | 健康检查 | ✅ 已完成 |
| `/ws/tasks` | WebSocket | 通用连接 | ✅ 已完成 |
| `/ws/tasks/{task_id}` | WebSocket | 任务专用连接 | ✅ 已完成 |

### 2.3 浏览器操作实现状态

| 操作类型 | 真实执行 | 模拟执行 | 说明 |
|---------|---------|---------|------|
| `goto` | ✅ | ✅ | 访问页面 |
| `click` | ✅ | ✅ | CSS 选择器点击 |
| `click` (by_image) | ❌ | ✅ | 图片识别点击 |
| `input` | ✅ | ✅ | 输入文本 |
| `wait` | ✅ | ✅ | 等待毫秒 |
| `scroll` | ✅ | ✅ | 页面滚动 |
| `screenshot` | ✅ | ✅ | 页面截图 |
| `extract` | ⚠️ 部分 | ✅ | 数据提取 |
| `press` | ✅ | ✅ | 键盘按键 |
| `hover` | ✅ | ✅ | 悬停元素 |
| `upload` | ❌ | ✅ | 文件上传 |
| `evaluate` | ✅ | ✅ | 执行 JS 脚本 |
| `switch_frame` | ❌ | ✅ | 切换 iframe |
| `switch_tab` | ❌ | ✅ | 切换标签页 |
| `new_tab` | ⚠️ 部分 | ✅ | 打开新标签页 |
| `close_tab` | ❌ | ✅ | 关闭标签页 |
| `drag` | ❌ | ✅ | 拖拽元素 |

### 2.4 WebSocket 消息类型

| 消息类型 | 功能 | 实现状态 |
|---------|------|---------|
| `task_status` | 任务状态更新 | ✅ 已完成 |
| `task_progress` | 任务进度更新 | ✅ 已完成 |
| `task_log` | 日志推送 | ✅ 已完成 |
| `task_result` | 任务结果 | ✅ 已完成 |
| `task_error` | 任务错误 | ✅ 已完成 |
| `task_screenshot` | 实时截图 | ✅ 已完成 |

---

## 三、待完善功能

### 3.1 高优先级 🔴

#### 3.1.1 真实浏览器启动
**问题**: 当前真实浏览器启动失败，回退到模拟模式

**涉及文件**: `api_service/execution_engine.py`

**调试步骤**:
1. 确认 Chrome 路径正确: `E:\chrome-win64\chrome.exe`
2. 确认端口 9223 未被占用
3. 检查 Chrome 启动参数

**临时解决方案**:
```bash
# 手动启动 Chrome 调试模式
E:\chrome-win64\chrome.exe --remote-debugging-port=9223 --no-sandbox
```

#### 3.1.2 取消任务功能完善
**问题**: 取消任务时浏览器可能未正确关闭

**涉及文件**:
- `api_service/main.py`
- `api_service/execution_engine.py`

**需要实现**:
- 正确关闭 Playwright browser 对象
- 终止 Chrome 进程
- 清理 WebSocket 连接

### 3.2 中优先级 🟡

#### 3.2.1 图片识别点击 (by_image)
**功能**: 根据图片识别点击元素

**方案**:
1. 使用 OpenCV 或其他图像识别库
2. 集成到 `_execute_action_real` 方法

#### 3.2.2 文件上传 (upload)
**功能**: 上传文件到 input 元素

**实现**:
```python
async def _execute_action_real(self, task_id: str, page, action: Dict[str, Any]) -> bool:
    if action_type == "upload":
        file_paths = action.get("file_paths", [])
        selector = action.get("selector", "")
        if selector and file_paths:
            await page.set_input_files(selector, file_paths)
            return True
```

#### 3.2.3 标签页管理 (switch_tab/close_tab)
**功能**: 切换和关闭浏览器标签页

**实现**:
```python
# switch_tab
elif action_type == "switch_tab":
    page_index = action.get("page_index", 0)
    context = browser.contexts[0] if browser.contexts else page.context
    pages = context.pages
    if page_index < len(pages):
        page = pages[page_index]
        return True

# close_tab
elif action_type == "close_tab":
    await page.close()
    return True
```

#### 3.2.4 框架切换 (switch_frame)
**功能**: 切换到指定的 iframe

**实现**:
```python
elif action_type == "switch_frame":
    frame_index = action.get("frame_index", 0)
    frame_selector = action.get("selector", "")
    if frame_selector:
        frame = page.frame_locator(frame_selector)
        # 需要调整后续操作使用 frame
        return True
```

#### 3.2.5 拖拽操作 (drag)
**功能**: 拖拽元素到目标位置

**实现**:
```python
elif action_type == "drag":
    source_selector = action.get("source_selector", "")
    target_selector = action.get("target_selector", "")
    if source_selector and target_selector:
        source = page.locator(source_selector)
        target = page.locator(target_selector)
        await source.drag_to(target)
        return True
```

### 3.3 低优先级 🟢

#### 3.3.1 数据提取功能完善
**功能**: 提取页面数据并结构化返回

**实现**:
```python
elif action_type == "extract":
    selectors = action.get("selectors", {})
    extract_type = action.get("extract_type", "text")
    result = {}
    for key, selector in selectors.items():
        if extract_type == "text":
            result[key] = page.locator(selector).inner_text()
        elif extract_type == "html":
            result[key] = page.locator(selector).inner_html()
        elif extract_type == "attribute":
            attr = action.get("attribute", "href")
            result[key] = page.locator(selector).get_attribute(attr)
    # 发送提取结果
    await ws_manager.send_task_result(task_id, {"extracted_data": result})
    return True
```

#### 3.3.2 断线重连机制
**功能**: WebSocket 断线后自动重连

**实现**:
```javascript
// 前端 WebSocket 服务
class WebSocketService {
  reconnect() {
    let attempts = 0
    const maxAttempts = 5
    const reconnect = () => {
      attempts++
      if (attempts <= maxAttempts) {
        setTimeout(() => {
          this.connect()
        }, Math.min(1000 * attempts, 10000))
      }
    }
  }
}
```

#### 3.3.3 心跳保活 (ping/pong)
**功能**: 定期发送心跳检测连接状态

**实现**:
- 前端定时发送 `ping` 消息
- 后端返回 `pong` 消息
- 超时未响应则断开重连

#### 3.3.4 任务历史记录
**功能**: 查看历史任务执行记录

**实现**:
- 添加 `started_at`, `completed_at` 字段
- 支持按时间范围筛选
- 显示任务执行耗时统计

---

## 四、架构优化建议

### 4.1 执行引擎改进

```
execution_engine.py
├── 浏览器生命周期管理
│   ├── _start_browser()     # 启动浏览器
│   ├── _close_browser()     # 关闭浏览器
│   └── _ensure_browser()    # 确保浏览器运行
├── 操作执行层
│   ├── _execute_action_real()   # 真实执行
│   ├── _execute_action()        # 模拟执行
│   └── _execute_fallback()      # 失败回退
├── 错误处理
│   ├── _handle_timeout()       # 超时处理
│   ├── _handle_not_found()     # 元素未找到
│   └── _handle_navigation()    # 导航错误
└── 截图管理
    ├── _take_screenshot()      # 截图
    └── _compress_image()       # 压缩图片
```

### 4.2 配置管理

建议添加配置文件 `config.yaml`:

```yaml
browser:
  chrome_path: "E:\\chrome-win64\\chrome.exe"
  debug_port: 9223
  headless: false
  timeout: 30000
  screenshot_quality: 70

task:
  max_retries: 3
  retry_delay: 1000
  cleanup_timeout: 5000

websocket:
  ping_interval: 30000
  pong_timeout: 5000
  reconnect_delay: 1000

storage:
  data_dir: "./data"
  max_history: 100
```

### 4.3 错误处理规范

```
错误类型:
- ERR001: 浏览器启动失败
- ERR002: 页面加载超时
- ERR003: 元素未找到
- ERR004: 操作超时
- ERR005: 截图失败

错误响应格式:
{
  "error_code": "ERR001",
  "message": "Chrome 浏览器启动失败",
  "details": {
    "reason": "端口 9223 已被占用",
    "suggestion": "请检查是否有其他 Chrome 实例正在运行"
  }
}
```

---

## 五、测试方案

### 5.1 单元测试

```python
# tests/test_execution_engine.py
class TestExecutionEngine:
    async def test_goto_action(self):
        """测试访问页面操作"""
        pass

    async def test_click_action(self):
        """测试点击操作"""
        pass

    async def test_input_action(self):
        """测试输入操作"""
        pass

    async def test_scroll_action(self):
        """测试滚动操作"""
        pass
```

### 5.2 集成测试

```bash
# 启动测试
pytest tests/ -v --tb=short

# 测试覆盖率
pytest --cov=api_service --cov-report=html
```

### 5.3 E2E 测试

```typescript
// tests/e2e/workflow.spec.ts
test('complete workflow execution', async ({ page }) => {
  // 1. 打开工作流设计器
  // 2. 添加节点
  // 3. 点击运行
  // 4. 验证执行监控
  // 5. 检查结果
})
```

---

## 六、后续开发计划

### Phase 1: 核心功能完善 (1-2 周)

| 任务 | 预估时间 | 优先级 |
|-----|---------|-------|
| 修复真实浏览器启动 | 2 天 | 🔴 P0 |
| 完善取消任务功能 | 1 天 | 🔴 P0 |
| 实现文件上传操作 | 1 天 | 🟡 P1 |
| 实现标签页切换 | 1 天 | 🟡 P1 |
| 实现框架切换 | 1 天 | 🟡 P1 |
| 实现拖拽操作 | 1 天 | 🟡 P1 |

### Phase 2: 高级功能 (2-3 周)

| 任务 | 预估时间 | 优先级 |
|-----|---------|-------|
| 图片识别点击 | 3 天 | 🟡 P1 |
| 数据提取完善 | 2 天 | 🟡 P1 |
| 断线重连机制 | 1 天 | 🟢 P2 |
| 心跳保活 | 1 天 | 🟢 P2 |
| 任务历史记录 | 2 天 | 🟢 P2 |

### Phase 3: 优化与扩展 (持续)

| 任务 | 预估时间 | 优先级 |
|-----|---------|-------|
| 配置管理 | 1 天 | 🟢 P2 |
| 错误处理规范化 | 1 天 | 🟢 P2 |
| 性能优化 | 2 天 | 🟢 P2 |
| 插件系统设计 | 1 周 | ⚪ P3 |

---

## 七、快速开始

### 启动后端服务

```bash
cd api_service
# 安装依赖
pip install fastapi uvicorn websockets playwright
playwright install chromium

# 启动服务
python main.py
```

### 启动前端开发服务器

```bash
cd admin-frontend
npm install
npm run dev
```

### 测试真实浏览器

```bash
# 1. 确保 Chrome 已安装
# 路径: E:\chrome-win64\chrome.exe

# 2. 手动测试 Chrome 调试模式
E:\chrome-win64\chrome.exe --remote-debugging-port=9223 --no-sandbox

# 3. 访问 Playwright 检查
# 打开浏览器访问 http://localhost:9223
```

---

## 八、常见问题

### Q1: 浏览器启动失败，提示端口被占用

**解决方案**:
```bash
# Windows 查看占用端口的进程
netstat -ano | findstr :9223

# 结束进程
taskkill /PID <PID> /F
```

### Q2: 任务卡住无响应

**原因**: 页面加载超时或元素未找到

**解决方案**:
1. 检查 `wait_until='networkidle'` 设置
2. 增加超时时间
3. 添加显式等待条件

### Q3: 截图不清晰

**解决方案**:
```python
# 提高截图质量
await page.screenshot(type='jpeg', quality=85)
```

### Q4: WebSocket 频繁断开

**原因**: 心跳超时或网络不稳定

**解决方案**:
1. 实现心跳保活机制
2. 添加断线重连逻辑
3. 检查服务器资源使用情况

---

## 九、参考资源

### 技术栈

- **前端**: Vue 3 + Element Plus + Vue Flow
- **后端**: FastAPI + Python 3.13
- **浏览器自动化**: Playwright + Chrome DevTools Protocol
- **实时通信**: WebSocket

### 相关文档

- [Playwright Python API](https://playwright.dev/python/docs/api/class-page)
- [FastAPI WebSocket](https://fastapi.tiangolo.com/advanced/websockets/)
- [Vue Flow 文档](https://vueflow.dev/)

---

*文档版本: 1.0*
*最后更新: 2026-02-12*
