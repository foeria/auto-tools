BOT_NAME = "smart_crawler"
SPIDER_MODULES = ["spiders"]
NEWSPIDER_MODULE = "spiders"
ROBOTSTXT_OBEY = False
CONCURRENT_REQUESTS = 4
DOWNLOAD_DELAY = 1.0
RANDOMIZE_DOWNLOAD_DELAY = True
TELNETCONSOLE_ENABLED = False
OVERRIDE_START_REQUEST_URIS = False
AUTOTHROTTLE_ENABLED = True
AUTOTHROTTLE_START_DELAY = 1.0
AUTOTHROTTLE_MAX_DELAY = 10.0
AUTOTHROTTLE_TARGET_CONCURRENTION_REQUESTS = 1.0
HTTPCACHE_ENABLED = False
LOG_LEVEL = "INFO"
DEFAULT_REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}
FEED_EXPORT_ENCODING = "utf-8"
TWISTED_REACTOR = "twisted.internet.asyncioreactor.AsyncioSelectorReactor"
JOBDIR = "crawls/%(name)s"
CLOSESPIDER_TIMEOUT = 0
CLOSESPIDER_ITEMCOUNT = 0
FEED_URI = "file:///tmp/%(name)s_%(time)s.json"
FEED_FORMAT = "jsonlines"
DOWNLOADER_MIDDLEWARES = {
    "scrapy_playwright.middleware.PlaywrightMiddleware": 1000,
}
PLAYWRIGHT_BROWSER_TYPE = "chromium"
import os

# ============================================
# 浏览器启动与调试配置
# ============================================

# 浏览器可执行文件完整路径（自定义浏览器安装目录）
# 例如：E:\chrome-win64\chrome.exe
PLAYWRIGHT_EXECUTABLE_PATH = os.getenv("PW_EXECUTABLE_PATH", "").strip() or None

# 是否使用系统自带浏览器（Chrome/Edge），否则使用Playwright自带浏览器
PLAYWRIGHT_USE_SYSTEM_BROWSER = os.getenv("PW_USE_SYSTEM_BROWSER", "false").lower() == "true"

# 浏览器渠道：'chrome' 或 'msedge'，仅在使用系统浏览器时生效
PLAYWRIGHT_BROWSER_CHANNEL = os.getenv("PW_BROWSER_CHANNEL", "").strip() or None

# 是否使用持久化上下文（启用后加载历史记录/Cookie等用户数据）
PLAYWRIGHT_USE_PERSISTENT_CONTEXT = os.getenv("PW_USE_PERSISTENT", "false").lower() == "true"

# 用户数据目录（Chrome/Edge的用户数据路径），启用持久化上下文时需要
# 例如：C:\Users\用户名\AppData\Local\Google\Chrome\User Data
PLAYWRIGHT_USER_DATA_DIR = os.getenv("PW_USER_DATA_DIR", "").strip() or None

# 是否无头模式
PLAYWRIGHT_HEADLESS = os.getenv("PW_HEADLESS", "false").lower() == "true"

# ============================================
# 浏览器启动选项
# ============================================
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": PLAYWRIGHT_HEADLESS,
    "timeout": 60000,
    "devtools": False,
}

# 使用自定义浏览器可执行文件路径
if PLAYWRIGHT_EXECUTABLE_PATH:
    PLAYWRIGHT_LAUNCH_OPTIONS["executable_path"] = PLAYWRIGHT_EXECUTABLE_PATH

# 使用系统浏览器渠道
if PLAYWRIGHT_USE_SYSTEM_BROWSER and PLAYWRIGHT_BROWSER_CHANNEL:
    PLAYWRIGHT_LAUNCH_OPTIONS["channel"] = PLAYWRIGHT_BROWSER_CHANNEL

# ============================================
# 上下文配置
# ============================================
PLAYWRIGHT_CONTEXTS = {
    "default": {
        "accept_downloads": True,
        "java_script_enabled": True,
    }
}

# 持久化上下文配置（加载用户历史记录）
PLAYWRIGHT_PERSISTENT_CONTEXTS = {}
if PLAYWRIGHT_USE_PERSISTENT_CONTEXT and PLAYWRIGHT_USER_DATA_DIR:
    PLAYWRIGHT_PERSISTENT_CONTEXTS = {
        "user": {
            "user_data_dir": PLAYWRIGHT_USER_DATA_DIR,
            "accept_downloads": True,
            "java_script_enabled": True,
        }
    }

PLAYWRIGHT_DEFAULT_NAVIGATION_TIMEOUT = 60000
PLAYWRIGHT_PAGE_METHODS_TIMEOUT = 60000
PLAYWRIGHT_MAX_PAGES = 4
PLAYWRIGHT_PROCESS_MAX_CRAWL_COUNT = 4
EXTENSIONS = {}
ITEM_PIPELINES = {
    "scrapy.pipelines.images.ImagesPipeline": 300,
}
IMAGES_STORE = "./screenshots"
IMAGES_EXPIRES = 90
IMAGES_THUMBS = {
    "small": (50, 50),
    "medium": (150, 150),
}
MEDIA_ALLOW_URLS_FOREVER = True
