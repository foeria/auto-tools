# 智能爬虫系统 (Smart Crawler)

基于Scrapy + Playwright + FastAPI + Vue3的智能爬虫系统，支持拖拽式工作流构建、任务调度、数据提取和转发。

## 项目特点

- 🤖 **自动化爬虫**：支持点击、输入、等待、滚动等自动化操作
- 🎨 **拖拽式工作流**：可视化拖拽构建爬虫流程
- 📊 **多种数据提取**：HTML、JSON、表格、XPath等多种提取方式
- 🖼️ **图像识别点击**：OpenCV模板匹配智能点击
- 📡 **API服务**：FastAPI提供RESTful接口
- 💾 **数据存储**：MongoDB + Redis存储方案
- 🎯 **任务调度**：优先级调度和自动重试
- 📈 **监控统计**：实时任务状态和统计信息

## 快速开始

### Docker启动（推荐）

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps
```

### 本地开发

```bash
# 安装Python依赖
pip install -r requirements.txt

# 安装Playwright浏览器
playwright install chromium

# 启动API服务
cd api_service
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# 启动前端（另开终端）
cd admin-frontend
npm install
npm run dev
```

### 运行测试

```bash
# 安装测试依赖
pip install -r requirements-test.txt

# 运行 tests/test_core.py -v

# 运行集成测试
pytest tests/test单元测试
pytest_integration.py -v

# 运行所有测试
pytest -v
```

## 项目结构

```
smart-crawler/
├── api_service/              # FastAPI服务
│   ├── main.py             # API入口
│   └── Dockerfile
├── scrapy_project/          # Scrapy爬虫
│   ├── spiders/
│   │   └── automation_spider.py
│   ├── utils/
│   │   ├── action_handler.py   # 动作处理器
│   │   ├── data_extractor.py  # 数据提取器
│   │   ├── storage.py         # 存储模块
│   │   └── scheduler.py       # 任务调度
│   └── settings.py
├── admin-frontend/          # Vue3前端
│   ├── src/
│   │   ├── views/          # 页面组件
│   │   ├── components/      # 可复用组件
│   │   ├── services/        # API服务
│   │   ├── stores/          # 状态管理
│   │   └── data/            # 静态数据
│   └── ...
├── tests/                   # 测试文件
│   ├── test_core.py        # 单元测试
│   └── test_integration.py # 集成测试
├── templates/               # 图像识别模板
├── screenshots/            # 截图保存
├── docker-compose.yml
├── requirements.txt
└── README.md
```

## API接口

### 任务管理

- `POST /api/tasks` - 创建任务
- `GET /api/tasks` - 列出任务
- `GET /api/tasks/{task_id}` - 获取任务详情
- `DELETE /api/tasks/{task_id}` - 删除任务
- `POST /api/tasks/{task_id}/retry` - 重试任务

### 模板管理

- `GET /api/templates` - 列出模板
- `POST /api/templates` - 创建模板
- `DELETE /api/templates/{id}` - 删除模板

### 数据转发

- `POST /api/forward` - 转发数据到外部API

### 监控

- `GET /api/statistics` - 获取统计数据
- `GET /api/actions` - 获取可用动作列表
- `GET /health` - 健康检查

## 支持的动作类型

| 动作       | 说明     | 主要参数                            |
| ---------- | -------- | ----------------------------------- |
| goto       | 访问页面 | url, wait_until                     |
| click      | 点击元素 | selector, by_image, timeout         |
| input      | 输入内容 | selector, value, clear, press_enter |
| wait       | 等待     | timeout, selector, state            |
| screenshot | 截图     | selector, full_page, path           |
| extract    | 提取数据 | selectors, extract_type, attribute  |
| evaluate   | 执行脚本 | script, arg                         |
| scroll     | 滚动     | x, y, selector                      |
| press      | 按键     | selector, key                       |
| hover      | 悬停     | selector, timeout                   |
| upload     | 上传文件 | selector, file_paths                |

## 数据提取器

| 提取器     | 说明         |
| ---------- | ------------ |
| html       | HTML元素提取 |
| json       | JSON数据提取 |
| table      | 表格数据提取 |
| xpath      | XPath提取    |
| api        | API响应捕获  |
| screenshot | 页面截图     |
| fullpage   | 完整页面文本 |

## 配置说明

### 环境变量

```bash
# API服务
API_HOST=0.0.0.0
API_PORT=8000

# MongoDB
MONGODB_URI=mongodb://localhost:27017

# Redis
REDIS_HOST=localhost
REDIS_PORT=6379

# 爬虫
CRAWLER_MAX_RETRY=3
CRAWLER_TIMEOUT=60

# 图像识别
TEMPLATE_MATCH_THRESHOLD=0.8
```

### 前端环境

```bash
VITE_API_BASE_URL=http://localhost:8000
```

## 许可证

MIT License
