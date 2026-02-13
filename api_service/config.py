"""
配置管理模块
从 config.yaml 加载配置，支持环境变量覆盖
"""
import os
import sys
from pathlib import Path
from typing import Any, Dict, Optional
from dataclasses import dataclass, field
import logging
import yaml

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent


@dataclass
class BrowserConfig:
    """浏览器配置"""
    chrome_path: str = "E:\\chrome-win64\\chrome.exe"
    debug_port_min: int = 9222
    debug_port_max: int = 9299
    headless: bool = False
    page_timeout: int = 30000
    action_timeout: int = 5000
    screenshot_quality: int = 70
    start_timeout: int = 10
    # 反检测配置
    enable_stealth: bool = False
    viewport_width: int = 1920
    viewport_height: int = 1080
    user_agent: str = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    locale: str = "zh-CN"
    timezone: str = "Asia/Shanghai"


@dataclass
class TaskConfig:
    """任务配置"""
    max_retries: int = 3
    retry_delay: int = 1000
    cleanup_timeout: int = 5


@dataclass
class WebSocketConfig:
    """WebSocket配置"""
    ping_interval: int = 30000
    pong_timeout: int = 10000
    max_reconnect_attempts: int = 5
    reconnect_delay_base: int = 3000


@dataclass
class StorageConfig:
    """存储配置"""
    db_path: str = "./scrapy_project/data/storage.db"
    data_dir: str = "./scrapy_project/data"
    max_history: int = 1000
    history_retention_days: int = 30


@dataclass
class LoggingConfig:
    """日志配置"""
    level: str = "INFO"
    console: bool = True
    file_path: str = "./logs/app.log"
    max_file_size: int = 10485760
    backup_count: int = 5


@dataclass
class ApiConfig:
    """API配置"""
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list = field(default_factory=lambda: ["*"])
    debug: bool = False


@dataclass
class SimulationConfig:
    """模拟模式配置"""
    enabled: bool = True
    action_delay: float = 0.3
    browser_start_delay: float = 0.5
    browser_close_delay: float = 0.2


@dataclass
class PerformanceConfig:
    """性能优化配置"""
    batch_log_enabled: bool = True
    batch_log_interval: int = 100
    batch_log_size: int = 10
    disable_realtime_screenshot: bool = False
    screenshot_interval: int = 1


@dataclass
class Config:
    """主配置类"""
    browser: BrowserConfig = field(default_factory=BrowserConfig)
    task: TaskConfig = field(default_factory=TaskConfig)
    websocket: WebSocketConfig = field(default_factory=WebSocketConfig)
    storage: StorageConfig = field(default_factory=StorageConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    api: ApiConfig = field(default_factory=ApiConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)


class ConfigLoader:
    """配置加载器"""

    def __init__(self, config_path: str = None):
        self.config_path = config_path or PROJECT_ROOT / "config.yaml"
        self._config: Optional[Config] = None
        self._raw_config: Dict[str, Any] = {}

    def load(self) -> Config:
        """加载配置"""
        if self._config is not None:
            return self._config

        self._raw_config = self._read_yaml()
        self._config = self._parse_config()
        return self._config

    def _read_yaml(self) -> Dict[str, Any]:
        """读取YAML配置文件"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except FileNotFoundError:
            logging.warning(f"Config file not found: {self.config_path}")
            return {}
        except yaml.YAMLError as e:
            logging.error(f"Failed to parse config file: {e}")
            return {}

    def _parse_config(self) -> Config:
        """解析配置"""
        config = Config()

        # 浏览器配置
        if 'browser' in self._raw_config:
            browser_cfg = self._raw_config['browser']
            config.browser = BrowserConfig(
                chrome_path=self._get_env('BROWSER_CHROME_PATH', browser_cfg.get('chrome_path', config.browser.chrome_path)),
                debug_port_min=browser_cfg.get('debug_port_min', config.browser.debug_port_min),
                debug_port_max=browser_cfg.get('debug_port_max', config.browser.debug_port_max),
                headless=self._get_env_bool('BROWSER_HEADLESS', browser_cfg.get('headless', config.browser.headless)),
                page_timeout=browser_cfg.get('page_timeout', config.browser.page_timeout),
                action_timeout=browser_cfg.get('action_timeout', config.browser.action_timeout),
                screenshot_quality=browser_cfg.get('screenshot_quality', config.browser.screenshot_quality),
                start_timeout=browser_cfg.get('start_timeout', config.browser.start_timeout),
                enable_stealth=browser_cfg.get('enable_stealth', config.browser.enable_stealth),
                viewport_width=browser_cfg.get('viewport_width', config.browser.viewport_width),
                viewport_height=browser_cfg.get('viewport_height', config.browser.viewport_height),
                user_agent=browser_cfg.get('user_agent', config.browser.user_agent),
                locale=browser_cfg.get('locale', config.browser.locale),
                timezone=browser_cfg.get('timezone', config.browser.timezone),
            )

        # 任务配置
        if 'task' in self._raw_config:
            task_cfg = self._raw_config['task']
            config.task = TaskConfig(
                max_retries=task_cfg.get('max_retries', config.task.max_retries),
                retry_delay=task_cfg.get('retry_delay', config.task.retry_delay),
                cleanup_timeout=task_cfg.get('cleanup_timeout', config.task.cleanup_timeout),
            )

        # WebSocket配置
        if 'websocket' in self._raw_config:
            ws_cfg = self._raw_config['websocket']
            config.websocket = WebSocketConfig(
                ping_interval=ws_cfg.get('ping_interval', config.websocket.ping_interval),
                pong_timeout=ws_cfg.get('pong_timeout', config.websocket.pong_timeout),
                max_reconnect_attempts=ws_cfg.get('max_reconnect_attempts', config.websocket.max_reconnect_attempts),
                reconnect_delay_base=ws_cfg.get('reconnect_delay_base', config.websocket.reconnect_delay_base),
            )

        # 存储配置
        if 'storage' in self._raw_config:
            storage_cfg = self._raw_config['storage']
            config.storage = StorageConfig(
                db_path=self._get_env('STORAGE_DB_PATH', storage_cfg.get('db_path', config.storage.db_path)),
                data_dir=self._get_env('STORAGE_DATA_DIR', storage_cfg.get('data_dir', config.storage.data_dir)),
                max_history=storage_cfg.get('max_history', config.storage.max_history),
                history_retention_days=storage_cfg.get('history_retention_days', config.storage.history_retention_days),
            )

        # 日志配置
        if 'logging' in self._raw_config:
            log_cfg = self._raw_config['logging']
            config.logging = LoggingConfig(
                level=self._get_env('LOG_LEVEL', log_cfg.get('level', config.logging.level)),
                console=log_cfg.get('console', config.logging.console),
                file_path=log_cfg.get('file_path', config.logging.file_path),
                max_file_size=log_cfg.get('max_file_size', config.logging.max_file_size),
                backup_count=log_cfg.get('backup_count', config.logging.backup_count),
            )

        # API配置
        if 'api' in self._raw_config:
            api_cfg = self._raw_config['api']
            config.api = ApiConfig(
                host=self._get_env('API_HOST', api_cfg.get('host', config.api.host)),
                port=self._get_env_int('API_PORT', api_cfg.get('port', config.api.port)),
                cors_origins=api_cfg.get('cors_origins', config.api.cors_origins),
                debug=api_cfg.get('debug', config.api.debug),
            )

        # 模拟模式配置
        if 'simulation' in self._raw_config:
            sim_cfg = self._raw_config['simulation']
            config.simulation = SimulationConfig(
                enabled=self._get_env_bool('SIMULATION_ENABLED', sim_cfg.get('enabled', config.simulation.enabled)),
                action_delay=sim_cfg.get('action_delay', config.simulation.action_delay),
                browser_start_delay=sim_cfg.get('browser_start_delay', config.simulation.browser_start_delay),
                browser_close_delay=sim_cfg.get('browser_close_delay', config.simulation.browser_close_delay),
            )

        # 性能优化配置
        if 'performance' in self._raw_config:
            perf_cfg = self._raw_config['performance']
            config.performance = PerformanceConfig(
                batch_log_enabled=perf_cfg.get('batch_log_enabled', config.performance.batch_log_enabled),
                batch_log_interval=perf_cfg.get('batch_log_interval', config.performance.batch_log_interval),
                batch_log_size=perf_cfg.get('batch_log_size', config.performance.batch_log_size),
                disable_realtime_screenshot=perf_cfg.get('disable_realtime_screenshot', config.performance.disable_realtime_screenshot),
                screenshot_interval=perf_cfg.get('screenshot_interval', config.performance.screenshot_interval),
            )

        return config

    def _get_env(self, key: str, default: str) -> str:
        """获取环境变量（字符串）"""
        return os.environ.get(key, default)

    def _get_env_int(self, key: str, default: int) -> int:
        """获取环境变量（整数）"""
        value = os.environ.get(key)
        if value is not None:
            try:
                return int(value)
            except ValueError:
                return default
        return default

    def _get_env_bool(self, key: str, default: bool) -> bool:
        """获取环境变量（布尔值）"""
        value = os.environ.get(key)
        if value is not None:
            return value.lower() in ('true', '1', 'yes')
        return default

    def get_raw(self) -> Dict[str, Any]:
        """获取原始配置"""
        return self._raw_config

    def reload(self) -> Config:
        """重新加载配置"""
        self._config = None
        return self.load()


# 全局配置实例
_config: Optional[Config] = None


def get_config(config_path: str = None) -> Config:
    """获取配置单例"""
    global _config
    if _config is None:
        loader = ConfigLoader(config_path)
        _config = loader.load()
    return _config


def reload_config(config_path: str = None) -> Config:
    """重新加载配置"""
    global _config
    loader = ConfigLoader(config_path)
    _config = loader.load()
    return _config


def setup_logging(config: Config = None):
    """配置日志"""
    if config is None:
        config = get_config()

    log_level = getattr(logging, config.logging.level.upper(), logging.INFO)

    # 创建日志目录
    log_file = Path(config.logging.file_path)
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # 配置日志格式
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 文件日志
    if config.logging.file_path:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            config.logging.file_path,
            maxBytes=config.logging.max_file_size,
            backupCount=config.logging.backup_count,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        file_handler.setLevel(log_level)
        logging.getLogger().addHandler(file_handler)

    # 控制台日志
    if config.logging.console:
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)
        logging.getLogger().addHandler(console_handler)

    # 设置根日志级别
    logging.getLogger().setLevel(log_level)


# 创建logs目录
def ensure_log_dir():
    """确保日志目录存在"""
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)


ensure_log_dir()
