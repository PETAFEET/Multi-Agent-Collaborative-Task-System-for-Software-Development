"""
日志管理模块

提供统一的日志记录功能
"""

import sys
import logging
from typing import Optional, Dict, Any
from pathlib import Path
from loguru import logger as loguru_logger

# 移除默认处理器
loguru_logger.remove()

# 全局日志配置
_logger_configured = False


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    rotation: str = "1 day",
    retention: str = "30 days",
    format_string: Optional[str] = None
):
    """
    设置日志配置
    
    Args:
        level: 日志级别
        log_file: 日志文件路径
        rotation: 日志轮转周期
        retention: 日志保留时间
        format_string: 日志格式字符串
    """
    global _logger_configured
    
    if _logger_configured:
        return
    
    # 默认格式
    if format_string is None:
        format_string = (
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        )
    
    # 控制台输出
    loguru_logger.add(
        sys.stderr,
        format=format_string,
        level=level,
        colorize=True
    )
    
    # 文件输出
    if log_file:
        log_file_path = Path(log_file)
        log_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        loguru_logger.add(
            log_file,
            format=format_string,
            level=level,
            rotation=rotation,
            retention=retention,
            compression="zip",
            encoding="utf-8"
        )
    
    # 设置标准库日志级别
    logging.basicConfig(level=getattr(logging, level.upper()))
    
    _logger_configured = True


def get_logger(name: str) -> Any:
    """
    获取日志记录器
    
    Args:
        name: 日志记录器名称
        
    Returns:
        日志记录器实例
    """
    if not _logger_configured:
        setup_logging()
    
    return loguru_logger.bind(name=name)


class LoggerMixin:
    """日志混入类"""
    
    @property
    def logger(self):
        """获取日志记录器"""
        return get_logger(self.__class__.__name__)


def log_function_call(func):
    """函数调用日志装饰器"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"调用函数: {func.__name__}")
        try:
            result = func(*args, **kwargs)
            logger.debug(f"函数 {func.__name__} 执行成功")
            return result
        except Exception as e:
            logger.error(f"函数 {func.__name__} 执行失败: {e}")
            raise
    return wrapper


def log_async_function_call(func):
    """异步函数调用日志装饰器"""
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"调用异步函数: {func.__name__}")
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"异步函数 {func.__name__} 执行成功")
            return result
        except Exception as e:
            logger.error(f"异步函数 {func.__name__} 执行失败: {e}")
            raise
    return wrapper


class StructuredLogger:
    """结构化日志记录器"""
    
    def __init__(self, name: str):
        self.logger = get_logger(name)
    
    def info(self, message: str, **kwargs):
        """记录信息日志"""
        self.logger.info(message, **kwargs)
    
    def debug(self, message: str, **kwargs):
        """记录调试日志"""
        self.logger.debug(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """记录警告日志"""
        self.logger.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """记录错误日志"""
        self.logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """记录严重错误日志"""
        self.logger.critical(message, **kwargs)
    
    def log_task_start(self, task_id: str, task_name: str, **kwargs):
        """记录任务开始"""
        self.info(f"任务开始: {task_name}", task_id=task_id, **kwargs)
    
    def log_task_complete(self, task_id: str, task_name: str, duration: float, **kwargs):
        """记录任务完成"""
        self.info(f"任务完成: {task_name}", task_id=task_id, duration=duration, **kwargs)
    
    def log_task_fail(self, task_id: str, task_name: str, error: str, **kwargs):
        """记录任务失败"""
        self.error(f"任务失败: {task_name}", task_id=task_id, error=error, **kwargs)
    
    def log_agent_status(self, agent_id: str, status: str, **kwargs):
        """记录智能体状态"""
        self.info(f"智能体状态更新: {agent_id}", agent_id=agent_id, status=status, **kwargs)
    
    def log_message_sent(self, message_id: str, sender: str, recipient: str, **kwargs):
        """记录消息发送"""
        self.debug(f"消息发送: {message_id}", message_id=message_id, sender=sender, recipient=recipient, **kwargs)
    
    def log_message_received(self, message_id: str, recipient: str, **kwargs):
        """记录消息接收"""
        self.debug(f"消息接收: {message_id}", message_id=message_id, recipient=recipient, **kwargs)
