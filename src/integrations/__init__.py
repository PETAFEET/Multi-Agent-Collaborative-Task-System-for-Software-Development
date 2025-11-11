"""
外部集成模块

包含MCP、浏览器操作等外部系统集成
"""

from .mcp_client import MCPClient
from .browser_use import BrowserUseClient

__all__ = [
    "MCPClient",
    "BrowserUseClient"
]
