"""
核心框架模块

包含多智能体系统的核心组件
"""

from .coordinator import MultiAgentCoordinator
from .task_manager import TaskManager
from .communication import CommunicationManager
# from .logger import get_logger, setup_logging

__all__ = [
    "MultiAgentCoordinator",
    "TaskManager", 
    "CommunicationManager",
    "get_logger",
    "setup_logging"
]
