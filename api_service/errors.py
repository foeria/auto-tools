"""
错误处理模块
提供统一的错误码规范和错误处理机制
"""
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime
import logging
import json
import traceback

logger = logging.getLogger(__name__)


class ErrorCode(str, Enum):
    """错误码枚举"""
    # 浏览器错误 (ERR-BRWSR)
    ERR_BRWSR_START_FAILED = "ERR_BRWSR_001"  # 浏览器启动失败
    ERR_BRWSR_NOT_FOUND = "ERR_BRWSR_002"    # 浏览器未找到
    ERR_BRWSR_CONNECTION_LOST = "ERR_BRWSR_003"  # 浏览器连接断开
    ERR_BRWSR_PROCESS_EXITED = "ERR_BRWSR_004"   # 浏览器进程退出

    # 页面错误 (ERR-PAGE)
    ERR_PAGE_LOAD_FAILED = "ERR_PAGE_001"   # 页面加载失败
    ERR_PAGE_LOAD_TIMEOUT = "ERR_PAGE_002"   # 页面加载超时
    ERR_PAGE_NAVIGATION = "ERR_PAGE_003"     # 页面导航错误
    ERR_PAGE_CRASH = "ERR_PAGE_004"         # 页面崩溃

    # 元素错误 (ERR-ELEM)
    ERR_ELEM_NOT_FOUND = "ERR_ELEM_001"     # 元素未找到
    ERR_ELEM_NOT_VISIBLE = "ERR_ELEM_002"    # 元素不可见
    ERR_ELEM_NOT_INTERACTABLE = "ERR_ELEM_003"  # 元素不可交互
    ERR_ELEM_STALE = "ERR_ELEM_004"         # 元素已过期

    # 操作错误 (ERR-ACT)
    ERR_ACT_TIMEOUT = "ERR_ACT_001"         # 操作超时
    ERR_ACT_FAILED = "ERR_ACT_002"          # 操作执行失败
    ERR_ACT_UNSUPPORTED = "ERR_ACT_003"     # 不支持的操作

    # 截图错误 (ERR-SCREEN)
    ERR_SCREEN_FAILED = "ERR_SCREEN_001"    # 截图失败
    ERR_SCREEN_ENCODE = "ERR_SCREEN_002"    # 截图编码失败

    # 数据提取错误 (ERR-EXT)
    ERR_EXT_NOT_FOUND = "ERR_EXT_001"       # 提取数据未找到
    ERR_EXT_FAILED = "ERR_EXT_002"           # 数据提取失败

    # 任务错误 (ERR-TASK)
    ERR_TASK_NOT_FOUND = "ERR_TASK_001"     # 任务不存在
    ERR_TASK_CANCELLED = "ERR_TASK_002"     # 任务已取消
    ERR_TASK_TIMEOUT = "ERR_TASK_003"       # 任务超时
    ERR_TASK_FAILED = "ERR_TASK_004"       # 任务执行失败

    # 系统错误 (ERR-SYS)
    ERR_SYS_CONFIG = "ERR_SYS_001"          # 配置错误
    ERR_SYS_STORAGE = "ERR_SYS_002"         # 存储错误
    ERR_SYS_WEBSOCKET = "ERR_SYS_003"       # WebSocket错误
    ERR_SYS_UNKNOWN = "ERR_SYS_999"         # 未知错误


@dataclass
class ErrorDetail:
    """错误详情"""
    code: str
    message: str
    reason: Optional[str] = None
    suggestion: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    task_id: Optional[str] = None
    action_index: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "error_code": self.code,
            "message": self.message,
            "reason": self.reason,
            "suggestion": self.suggestion,
            "details": self.details,
            "timestamp": self.timestamp,
            "task_id": self.task_id,
            "action_index": self.action_index
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def to_frontend(self) -> Dict[str, Any]:
        """返回前端友好的错误格式"""
        return {
            "error": self.code,
            "message": self.message,
            "reason": self.reason,
            "suggestion": self.suggestion
        }


class ErrorMessages:
    """错误消息模板"""

    @staticmethod
    def browser_start_failed(reason: str = None) -> ErrorDetail:
        return ErrorDetail(
            code=ErrorCode.ERR_BRWSR_START_FAILED,
            message="浏览器启动失败",
            reason=reason or "未知原因",
            suggestion="请检查Chrome路径配置是否正确，或尝试手动启动Chrome调试模式",
            details={"chrome_path": "检查 config.yaml 中的 browser.chrome_path"}
        )

    @staticmethod
    def browser_not_found(path: str) -> ErrorDetail:
        return ErrorDetail(
            code=ErrorCode.ERR_BRWSR_NOT_FOUND,
            message="Chrome浏览器未找到",
            reason=f"文件不存在: {path}",
            suggestion="请确认Chrome已安装，或在config.yaml中配置正确的路径"
        )

    @staticmethod
    def page_load_timeout(url: str, timeout: int) -> ErrorDetail:
        return ErrorDetail(
            code=ErrorCode.ERR_PAGE_LOAD_TIMEOUT,
            message="页面加载超时",
            reason=f"页面 {url} 在 {timeout}ms 内未加载完成",
            suggestion="1. 检查网络连接 2. 增加超时时间 3. 使用wait_until='domcontentloaded'",
            details={"url": url, "timeout": timeout}
        )

    @staticmethod
    def element_not_found(selector: str, action: str = None) -> ErrorDetail:
        return ErrorDetail(
            code=ErrorCode.ERR_ELEM_NOT_FOUND,
            message="元素未找到",
            reason=f"无法找到选择器: {selector}",
            suggestion="1. 检查选择器是否正确 2. 确认元素是否在iframe中 3. 添加等待时间",
            details={"selector": selector, "action": action}
        )

    @staticmethod
    def element_not_visible(selector: str) -> ErrorDetail:
        return ErrorDetail(
            code=ErrorCode.ERR_ELEM_NOT_VISIBLE,
            message="元素不可见",
            reason=f"元素 {selector} 存在但不可见",
            suggestion="1. 滚动到元素可见 2. 检查元素是否被遮挡 3. 等待元素加载完成",
            details={"selector": selector}
        )

    @staticmethod
    def action_timeout(action: str, timeout: int) -> ErrorDetail:
        return ErrorDetail(
            code=ErrorCode.ERR_ACT_TIMEOUT,
            message="操作超时",
            reason=f"{action} 操作在 {timeout}ms 内未完成",
            suggestion="1. 增加超时时间 2. 检查页面状态 3. 简化操作步骤",
            details={"action": action, "timeout": timeout}
        )

    @staticmethod
    def screenshot_failed(reason: str) -> ErrorDetail:
        return ErrorDetail(
            code=ErrorCode.ERR_SCREEN_FAILED,
            message="截图失败",
            reason=reason,
            suggestion="1. 检查页面是否加载完成 2. 确认元素是否存在 3. 尝试减少截图区域",
            details={"reason": reason}
        )

    @staticmethod
    def task_not_found(task_id: str) -> ErrorDetail:
        return ErrorDetail(
            code=ErrorCode.ERR_TASK_NOT_FOUND,
            message="任务不存在",
            reason=f"任务ID: {task_id}",
            suggestion="请检查任务ID是否正确，或重新创建任务"
        )

    @staticmethod
    def unsupported_action(action_type: str) -> ErrorDetail:
        return ErrorDetail(
            code=ErrorCode.ERR_ACT_UNSUPPORTED,
            message="不支持的操作",
            reason=f"操作类型: {action_type}",
            suggestion="请检查操作类型是否正确，或联系开发者添加支持"
        )


class ErrorHandler:
    """错误处理器"""

    @staticmethod
    def handle_exception(
        exception: Exception,
        error_code: ErrorCode = ErrorCode.ERR_SYS_UNKNOWN,
        task_id: str = None,
        action_index: int = None
    ) -> ErrorDetail:
        """处理异常并生成错误详情"""

        # 根据异常类型映射错误码
        error_code = ErrorHandler._map_exception_to_code(exception, error_code)

        # 提取错误信息
        reason = str(exception)

        # 生成建议
        suggestion = ErrorHandler._get_suggestion(error_code, exception)

        # 提取详细信息
        details = ErrorHandler._extract_details(exception)

        error_detail = ErrorDetail(
            code=error_code.value if isinstance(error_code, ErrorCode) else error_code,
            message=ErrorHandler._get_message(error_code),
            reason=reason,
            suggestion=suggestion,
            details=details,
            task_id=task_id,
            action_index=action_index
        )

        # 记录错误日志
        logger.error(
            f"[{error_detail.code}] {error_detail.message}",
            extra={"task_id": task_id, "action_index": action_index},
            exc_info=True
        )

        return error_detail

    @staticmethod
    def _map_exception_to_code(
        exception: Exception,
        default_code: ErrorCode
    ) -> ErrorCode:
        """根据异常类型映射错误码"""

        exception_type = type(exception).__name__

        mappings = {
            "FileNotFoundError": ErrorCode.ERR_BRWSR_NOT_FOUND,
            "TimeoutError": ErrorCode.ERR_ACT_TIMEOUT,
            "ValueError": ErrorCode.ERR_ELEM_NOT_FOUND,
            "IndexError": ErrorCode.ERR_ELEM_NOT_FOUND,
            "AttributeError": ErrorCode.ERR_SYS_UNKNOWN,
            "ConnectionError": ErrorCode.ERR_BRWSR_CONNECTION_LOST,
            "ProcessLookupError": ErrorCode.ERR_BRWSR_PROCESS_EXITED,
        }

        return mappings.get(exception_type, default_code)

    @staticmethod
    def _get_message(error_code: ErrorCode) -> str:
        """获取错误码对应的消息"""
        messages = {
            ErrorCode.ERR_BRWSR_START_FAILED: "浏览器启动失败",
            ErrorCode.ERR_BRWSR_NOT_FOUND: "Chrome浏览器未找到",
            ErrorCode.ERR_BRWSR_CONNECTION_LOST: "浏览器连接断开",
            ErrorCode.ERR_PAGE_LOAD_FAILED: "页面加载失败",
            ErrorCode.ERR_PAGE_LOAD_TIMEOUT: "页面加载超时",
            ErrorCode.ERR_ELEM_NOT_FOUND: "元素未找到",
            ErrorCode.ERR_ELEM_NOT_VISIBLE: "元素不可见",
            ErrorCode.ERR_ELEM_NOT_INTERACTABLE: "元素不可交互",
            ErrorCode.ERR_ACT_TIMEOUT: "操作超时",
            ErrorCode.ERR_ACT_FAILED: "操作执行失败",
            ErrorCode.ERR_ACT_UNSUPPORTED: "不支持的操作",
            ErrorCode.ERR_SCREEN_FAILED: "截图失败",
            ErrorCode.ERR_TASK_NOT_FOUND: "任务不存在",
            ErrorCode.ERR_TASK_CANCELLED: "任务已取消",
            ErrorCode.ERR_TASK_TIMEOUT: "任务执行超时",
            ErrorCode.ERR_TASK_FAILED: "任务执行失败",
            ErrorCode.ERR_SYS_CONFIG: "系统配置错误",
            ErrorCode.ERR_SYS_STORAGE: "存储错误",
            ErrorCode.ERR_SYS_WEBSOCKET: "WebSocket错误",
            ErrorCode.ERR_SYS_UNKNOWN: "未知错误",
        }
        return messages.get(error_code, "发生错误")

    @staticmethod
    def _get_suggestion(error_code: ErrorCode, exception: Exception = None) -> str:
        """获取错误处理建议"""
        suggestions = {
            ErrorCode.ERR_BRWSR_START_FAILED: "请检查Chrome路径配置，或手动启动Chrome调试模式测试",
            ErrorCode.ERR_BRWSR_NOT_FOUND: "请在config.yaml中配置正确的Chrome路径",
            ErrorCode.ERR_PAGE_LOAD_TIMEOUT: "建议增加超时时间或使用wait_until='domcontentloaded'",
            ErrorCode.ERR_ELEM_NOT_FOUND: "请检查选择器是否正确，确认元素是否在iframe中",
            ErrorCode.ERR_ACT_TIMEOUT: "请增加超时时间或简化操作步骤",
            ErrorCode.ERR_SCREEN_FAILED: "请确认页面已加载完成，元素存在",
        }
        return suggestions.get(error_code, "请检查输入参数和网络连接")

    @staticmethod
    def _extract_details(exception: Exception) -> Dict[str, Any]:
        """从异常中提取详细信息"""
        details = {}

        if hasattr(exception, 'args'):
            details['args'] = list(exception.args)

        if hasattr(exception, 'selector'):
            details['selector'] = exception.selector

        if hasattr(exception, 'timeout'):
            details['timeout'] = exception.timeout

        return details

    @staticmethod
    def create_task_error(
        task_id: str,
        error_code: ErrorCode,
        message: str,
        reason: str = None,
        suggestion: str = None
    ) -> Dict[str, Any]:
        """创建任务错误响应"""
        return {
            "error_code": error_code.value if isinstance(error_code, ErrorCode) else error_code,
            "message": message,
            "task_id": task_id,
            "reason": reason,
            "suggestion": suggestion,
            "timestamp": datetime.now().isoformat()
        }


# 便捷函数
def handle_error(
    exception: Exception,
    task_id: str = None,
    action_index: int = None,
    default_code: ErrorCode = ErrorCode.ERR_SYS_UNKNOWN
) -> ErrorDetail:
    """处理异常的便捷函数"""
    return ErrorHandler.handle_exception(
        exception=exception,
        error_code=default_code,
        task_id=task_id,
        action_index=action_index
    )


def create_error_response(error_detail: ErrorDetail) -> Dict[str, Any]:
    """创建API错误响应"""
    return {
        "success": False,
        "error": error_detail.to_frontend(),
        "timestamp": error_detail.timestamp
    }
