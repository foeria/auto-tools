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

| 功能模块             | 按钮/功能         | 实现状态  | 说明                         |
| -------------------- | ----------------- | --------- | ---------------------------- |
| **工作流管理** | 导入 JSON         | ✅ 已完成 | 从本地文件导入工作流         |
|                      | 导出 JSON         | ✅ 已完成 | 导出当前工作流               |
|                      | 保存到本地存储    | ✅ 已完成 | 保存到 localStorage          |
|                      | 从本地存储加载    | ✅ 已完成 | 加载已保存工作流             |
|                      | 清空画布          | ✅ 已完成 | 删除所有节点                 |
| **节点操作**   | 拖拽添加节点      | ✅ 已完成 | 从组件库拖拽到画布           |
|                      | 删除节点          | ✅ 已完成 | 删除节点及连线               |
|                      | 键盘快捷键        | ✅ 已完成 | Delete/Backspace 删除        |
| **任务执行**   | 运行工作流        | ✅ 已完成 | 提交任务到后端               |
|                      | 有头/无头模式切换 | ✅ 已完成 | headlessMode 参数            |
|                      | 取消任务          | ✅ 已完成 | 调用 cancel API              |
|                      | 重试任务          | ✅ 已完成 | 调用 retry API               |
| **执行监控**   | 实时截图预览      | ✅ 已完成 | WebSocket 推送截图           |
|                      | 任务状态显示      | ✅ 已完成 | pending/running/completed 等 |
|                      | 执行进度          | ✅ 已完成 | 进度条 + 数字显示            |
|                      | 日志显示          | ✅ 已完成 | 彩色日志 + 筛选              |
|                      | 日志导出          | ✅ 已完成 | 导出到 TXT                   |

### 2.2 后端 API (api_service)

| 端点                            | 方法      | 功能           | 实现状态  |
| ------------------------------- | --------- | -------------- | --------- |
| `/api/tasks`                  | POST      | 创建并执行任务 | ✅ 已完成 |
| `/api/tasks`                  | GET       | 列出任务列表   | ✅ 已完成 |
| `/api/tasks/{task_id}`        | GET       | 获取任务详情   | ✅ 已完成 |
| `/api/tasks/{task_id}/status` | GET       | 获取任务状态   | ✅ 已完成 |
| `/api/tasks/{task_id}`        | DELETE    | 删除任务       | ✅ 已完成 |
| `/api/tasks/{task_id}/retry`  | POST      | 重试任务       | ✅ 已完成 |
| `/api/tasks/{task_id}/cancel` | POST      | 取消任务       | ✅ 已完成 |
| `/api/templates`              | GET/POST  | 模板管理       | ✅ 已完成 |
| `/api/statistics`             | GET       | 统计信息       | ✅ 已完成 |
| `/api/executing-tasks`        | GET       | 执行中任务列表 | ✅ 已完成 |
| `/api/actions`                | GET       | 可用操作类型   | ✅ 已完成 |
| `/health`                     | GET       | 健康检查       | ✅ 已完成 |
| `/ws/tasks`                   | WebSocket | 通用连接       | ✅ 已完成 |
| `/ws/tasks/{task_id}`         | WebSocket | 任务专用连接   | ✅ 已完成 |

### 2.3 浏览器操作实现状态

| 操作类型             | 真实执行  | 模拟执行 | 说明                   |
| -------------------- | --------- | -------- | ---------------------- |
| `goto`             | ✅        | ✅       | 访问页面               |
| `click`            | ✅        | ✅       | CSS 选择器点击         |
| `click` (by_image) | ✅        | ✅       | 图片识别点击 (OpenCV)  |
| `input`            | ✅        | ✅       | 输入文本               |
| `wait`             | ✅        | ✅       | 等待毫秒               |
| `scroll`           | ✅        | ✅       | 页面滚动               |
| `screenshot`       | ✅        | ✅       | 页面截图               |
| `extract`          | ✅        | ✅       | 数据提取 (多类型/批量) |
| `press`            | ✅        | ✅       | 键盘按键               |
| `hover`            | ✅        | ✅       | 悬停元素               |
| `upload`           | ✅        | ✅       | 文件上传               |
| `evaluate`         | ✅        | ✅       | 执行 JS 脚本           |
| `switch_frame`     | ✅        | ✅       | 切换 iframe            |
| `switch_tab`       | ✅        | ✅       | 切换标签页             |
| `new_tab`          | ⚠️ 部分 | ✅       | 打开新标签页           |
| `close_tab`        | ✅        | ✅       | 关闭标签页             |
| `drag`             | ✅        | ✅       | 拖拽元素               |

### 2.4 WebSocket 消息类型

| 消息类型            | 功能         | 实现状态  |
| ------------------- | ------------ | --------- |
| `task_status`     | 任务状态更新 | ✅ 已完成 |
| `task_progress`   | 任务进度更新 | ✅ 已完成 |
| `task_log`        | 日志推送     | ✅ 已完成 |
| `task_result`     | 任务结果     | ✅ 已完成 |
| `task_error`      | 任务错误     | ✅ 已完成 |
| `task_screenshot` | 实时截图     | ✅ 已完成 |

---

## 三、待完善功能

### 3.1 高优先级 🔴

#### 3.1.1 真实浏览器启动 ✅ 已完成

- **状态**: 已实现 subprocess.Popen + CDP 连接
- **改进**: 使用 CREATE_NO_WINDOW 避免弹出黑窗口
- **随机端口**: 避免端口冲突

#### 3.1.2 取消任务功能完善 ✅ 已完成

- **状态**: 添加 cancelling 状态
- **改进**: 正确关闭页面、浏览器和进程

### 3.2 中优先级 🟡

#### 3.2.1 图片识别点击 (by_image) ✅ 已完成

- **实现**: 使用 OpenCV 进行模板匹配
- **参数**: confidence (置信度), offset_x/y (偏移量)

#### 3.2.2 文件上传 (upload) ✅ 已完成

- **实现**: `page.set_input_files(selector, file_paths)`

#### 3.2.3 标签页管理 (switch_tab/close_tab) ✅ 已完成

- **switch_tab**: 切换到指定标签页
- **close_tab**: 关闭当前标签页

#### 3.2.4 框架切换 (switch_frame) ✅ 已完成

- **实现**: `page.frame_locator(selector)`

#### 3.2.5 拖拽操作 (drag) ✅ 已完成

- **实现**: `source.drag_to(target)`

### 3.3 低优先级 🟢

#### 3.3.1 数据提取功能完善 ✅ 已完成

- **类型**: text, html, attribute, screenshot
- **批量**: 支持 multiple 批量提取

#### 3.3.2 断线重连机制 ✅ 已完成

- **前端**: 指数退避重连 (最多5次)
- **配置**: reconnectInterval, maxReconnectAttempts

#### 3.3.3 心跳保活 (ping/pong) ✅ 已完成

- **间隔**: 30秒发送 ping
- **超时**: 10秒 pong 超时检测

#### 3.3.4 任务历史记录 ✅ 已完成

- **查询**: 按时间范围/状态筛选
- **统计**: 执行时长计算

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

### 4.2 配置管理 ✅ 已实现

配置文件: `config.yaml`
配置模块: `api_service/config.py`

**使用方式**:

```python
from api_service.config import get_config

config = get_config()
print(config.browser.chrome_path)
print(config.websocket.ping_interval)
```

**配置项**:

| 分类                 | 配置项                 | 说明         |
| -------------------- | ---------------------- | ------------ |
| **browser**    | chrome_path            | Chrome路径   |
|                      | debug_port_min/max     | 调试端口范围 |
|                      | headless               | 默认无头模式 |
|                      | page_timeout           | 页面加载超时 |
|                      | action_timeout         | 操作超时     |
|                      | screenshot_quality     | 截图质量     |
| **task**       | max_retries            | 最大重试次数 |
|                      | retry_delay            | 重试间隔     |
|                      | cleanup_timeout        | 清理超时     |
| **websocket**  | ping_interval          | 心跳间隔     |
|                      | pong_timeout           | Pong超时     |
|                      | max_reconnect_attempts | 最大重连次数 |
| **storage**    | db_path                | 数据库路径   |
|                      | max_history            | 最大历史记录 |
|                      | history_retention_days | 历史保留天数 |
| **simulation** | enabled                | 启用模拟模式 |
|                      | action_delay           | 操作延迟     |
|                      | browser_start_delay    | 启动延迟     |

**环境变量覆盖**:

- `BROWSER_CHROME_PATH` - Chrome路径
- `BROWSER_HEADLESS` - 无头模式
- `API_HOST/PORT` - API服务端口
- `LOG_LEVEL` - 日志级别
- 等等...

```

### 4.3 错误处理规范 ✅ 已实现

错误模块: `api_service/errors.py`

**错误码分类**:

| 前缀 | 分类 |
|------|------|
| ERR-BRWSR | 浏览器错误 |
| ERR-PAGE | 页面错误 |
| ERR-ELEM | 元素错误 |
| ERR-ACT | 操作错误 |
| ERR-SCREEN | 截图错误 |
| ERR-EXT | 数据提取错误 |
| ERR-TASK | 任务错误 |
| ERR-SYS | 系统错误 |

**使用方式**:
```python
from api_service.errors import ErrorCode, ErrorHandler, ErrorDetail

# 处理异常
try:
    await page.goto(url)
except Exception as e:
    error = ErrorHandler.handle_exception(
        exception=e,
        error_code=ErrorCode.ERR_PAGE_LOAD_TIMEOUT,
        task_id="xxx"
    )
    # 发送到前端
    await ws_manager.send_task_error(task_id, error.message, error.to_dict())

# 创建任务错误
error = ErrorHandler.create_task_error(
    task_id="xxx",
    error_code=ErrorCode.ERR_ELEM_NOT_FOUND,
    message="元素未找到",
    reason="选择器: #submit-btn",
    suggestion="请检查元素是否存在"
)
```

**错误响应格式**:

```json
{
  "error_code": "ERR-ELEM-001",
  "message": "元素未找到",
  "reason": "无法找到选择器: #submit-btn",
  "suggestion": "1. 检查选择器是否正确 2. 确认元素是否在iframe中 3. 添加等待时间",
  "details": {
    "selector": "#submit-btn",
    "action": "click"
  },
  "timestamp": "2026-02-12T10:30:00.000Z",
  "task_id": "xxx",
  "action_index": 3
}
```

### 4.4 性能优化 ✅ 已实现

**性能优化配置** (config.yaml > performance):

| 配置项                      | 默认值 | 说明                 |
| --------------------------- | ------ | -------------------- |
| batch_log_enabled           | true   | 启用日志批量发送     |
| batch_log_interval          | 100    | 日志批量发送间隔(ms) |
| batch_log_size              | 10     | 日志批量大小         |
| disable_realtime_screenshot | false  | 禁用实时截图         |
| screenshot_interval         | 1      | 截图间隔(操作数)     |

**截图优化**:

- 使用PIL压缩图片
- 最大宽度限制 (screenshot_max_width)
- JPEG质量可配置 (screenshot_quality)

**日志优化**:

- info级别日志批量发送
- error/warning级别日志立即发送
- 批量大小达到或超时时自动发送

**配置示例**:

```yaml
performance:
  batch_log_enabled: true
  batch_log_interval: 100
  batch_log_size: 10
  disable_realtime_screenshot: false
  screenshot_interval: 1

browser:
  screenshot_quality: 70
  screenshot_max_width: 1920
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

### Phase 1: 核心功能完善 ✅ 已完成

| 任务               | 状态      |
| ------------------ | --------- |
| 修复真实浏览器启动 | ✅ 已完成 |
| 完善取消任务功能   | ✅ 已完成 |
| 实现文件上传操作   | ✅ 已完成 |
| 实现标签页切换     | ✅ 已完成 |
| 实现框架切换       | ✅ 已完成 |
| 实现拖拽操作       | ✅ 已完成 |

### Phase 2: 高级功能 ✅ 已完成

| 任务         | 状态      |
| ------------ | --------- |
| 图片识别点击 | ✅ 已完成 |
| 数据提取完善 | ✅ 已完成 |
| 断线重连机制 | ✅ 已完成 |
| 心跳保活     | ✅ 已完成 |
| 任务历史记录 | ✅ 已完成 |

### Phase 3: 优化与扩展 ⚪ 待实现

| 任务                   | 优先级 | 状态      |
| ---------------------- | ------ | --------- |
| 配置管理 (config.yaml) | P2     | ✅ 已完成 |
| 错误处理规范化         | P2     | ✅ 已完成 |
| 性能优化               | P2     | ✅ 已完成 |
| 插件系统设计           | P3     | ⚪ 待实现 |
| 前端任务历史页面       | P2     | ✅ 已完成 |
| 批量操作支持           | P2     | ⚪ 待实现 |
| 单元测试覆盖           | P2     | ⚪ 待实现 |

---

## 七、快速开始

### 启动后端服务

```bash
cd api_service
# 安装依赖
pip install fastapi uvicorn websockets playwright pyyaml
playwright install chromium

# 启动服务 (会自动加载 config.yaml)
python main.py
```

### 配置文件

主配置文件: `config.yaml`

```yaml
# 修改配置后需重启服务
browser:
  chrome_path: "E:\\chrome-win64\\chrome.exe"  # Chrome路径
  headless: false                               # 无头模式
  screenshot_quality: 70                        # 截图质量

websocket:
  ping_interval: 30000   # 心跳间隔(ms)
  pong_timeout: 10000    # Pong超时(ms)

api:
  host: "0.0.0.0"
  port: 8000
```

### 启动前端开发服务器

```bash
cd admin-frontend
npm install
npm run dev
```

### 测试真实浏览器

```bash
# 1. 确保 Chrome 已安装 (路径在 config.yaml 中配置)
# 默认路径: E:\chrome-win64\chrome.exe

# 2. 手动测试 Chrome 调试模式
E:\chrome-win64\chrome.exe --remote-debugging-port=9223 --no-sandbox
```

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
