"""
基础智能体类

定义所有智能体的通用接口和基础功能
"""

import asyncio
import uuid
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

from langchain_core.language_models.llms import BaseLLM
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from ..utils.logger import get_logger

logger = get_logger(__name__)


class AgentStatus(Enum):
    """智能体状态枚举"""
    IDLE = "idle"           # 空闲
    THINKING = "thinking"   # 思考中
    EXECUTING = "executing" # 执行中
    WAITING = "waiting"     # 等待中
    ERROR = "error"         # 错误
    COMPLETED = "completed" # 完成


@dataclass
class AgentMessage:
    """智能体消息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sender: str = ""
    recipient: str = ""
    message_type: str = "text"
    content: Any = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentCapabilities(BaseModel):
    """智能体能力描述"""
    can_plan: bool = False
    can_execute: bool = False
    can_monitor: bool = False
    can_browse: bool = False
    can_search: bool = False
    can_write_code: bool = False
    can_analyze_data: bool = False
    max_tokens: int = 1000
    supported_formats: List[str] = Field(default_factory=lambda: ["text", "json"])


class BaseAgent(ABC):
    """基础智能体类"""
    
    def __init__(
        self,
        agent_id: str,
        name: str,
        description: str,
        llm: BaseLLM,
        capabilities: AgentCapabilities,
        system_prompt: str = "",
        **kwargs
    ):
        self.agent_id = agent_id
        self.name = name
        self.description = description
        self.llm = llm
        self.capabilities = capabilities
        self.system_prompt = system_prompt
        
        # 状态管理
        self.status = AgentStatus.IDLE
        self.current_task = None
        self.task_history: List[Dict[str, Any]] = []
        
        # 通信
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.subscribers: List[str] = []
        
        # 配置
        self.config = kwargs
        self.logger = get_logger(f"agent.{self.agent_id}")
        
        self.logger.info(f"智能体 {self.name} 初始化完成")
    
    @abstractmethod
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行任务的核心方法
        
        Args:
            task: 任务描述字典
            
        Returns:
            执行结果字典
        """
        pass
    
    async def think(self, prompt: str, context: Dict[str, Any] = None) -> str:
        """
        使用LLM进行思考
        
        Args:
            prompt: 思考提示
            context: 上下文信息
            
        Returns:
            LLM的回复
        """
        try:
            self.status = AgentStatus.THINKING
            
            messages = []
            if self.system_prompt:
                messages.append(SystemMessage(content=self.system_prompt))
            
            if context:
                context_str = "\n".join([f"{k}: {v}" for k, v in context.items()])
                messages.append(HumanMessage(content=f"上下文信息:\n{context_str}\n\n{prompt}"))
            else:
                messages.append(HumanMessage(content=prompt))
            
            response = await self.llm.ainvoke(messages)
            self.logger.info(f"思考完成: {prompt[:50]}...")
            return response.content if hasattr(response, 'content') else str(response)
            
        except Exception as e:
            self.logger.error(f"思考过程出错: {e}")
            self.status = AgentStatus.ERROR
            raise
        finally:
            if self.status == AgentStatus.THINKING:
                self.status = AgentStatus.IDLE
    
    async def send_message(self, recipient: str, content: Any, message_type: str = "text") -> str:
        """
        发送消息给其他智能体
        
        Args:
            recipient: 接收者ID
            content: 消息内容
            message_type: 消息类型
            
        Returns:
            消息ID
        """
        message = AgentMessage(
            sender=self.agent_id,
            recipient=recipient,
            content=content,
            message_type=message_type
        )
        
        # 这里应该通过通信模块发送消息
        self.logger.info(f"发送消息给 {recipient}: {content[:100]}...")
        return message.id
    
    async def receive_message(self) -> Optional[AgentMessage]:
        """
        接收消息
        
        Returns:
            接收到的消息，如果没有消息则返回None
        """
        try:
            message = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
            self.logger.info(f"收到消息: {message.content[:100]}...")
            return message
        except asyncio.TimeoutError:
            return None
    
    def update_status(self, status: AgentStatus, message: str = ""):
        """
        更新智能体状态
        
        Args:
            status: 新状态
            message: 状态更新消息
        """
        old_status = self.status
        self.status = status
        self.logger.info(f"状态更新: {old_status.value} -> {status.value} {message}")
    
    def add_task_to_history(self, task: Dict[str, Any], result: Dict[str, Any]):
        """
        添加任务到历史记录
        
        Args:
            task: 任务描述
            result: 执行结果
        """
        self.task_history.append({
            "task": task,
            "result": result,
            "timestamp": datetime.now(),
            "status": self.status.value
        })
        
        # 保持历史记录在合理范围内
        if len(self.task_history) > 100:
            self.task_history = self.task_history[-100:]
    
    def get_status_info(self) -> Dict[str, Any]:
        """
        获取智能体状态信息
        
        Returns:
            状态信息字典
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "status": self.status.value,
            "current_task": self.current_task,
            "task_count": len(self.task_history),
            "capabilities": self.capabilities.dict(),
            "last_activity": datetime.now().isoformat()
        }
    
    async def health_check(self) -> bool:
        """
        健康检查
        
        Returns:
            是否健康
        """
        try:
            # 简单的健康检查：尝试调用LLM
            test_response = await self.think("健康检查测试")
            return bool(test_response)
        except Exception as e:
            self.logger.error(f"健康检查失败: {e}")
            return False
    
    def __str__(self) -> str:
        return f"{self.name}({self.agent_id}) - {self.status.value}"
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.agent_id}, status={self.status.value})>"
