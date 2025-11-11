"""
通信管理器

负责智能体之间的消息传递和通信协调
"""

import asyncio
import json
import uuid
from typing import Dict, List, Any, Optional, Callable, Union
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum

from ..utils.logger import get_logger

logger = get_logger(__name__)


class MessageType(Enum):
    """消息类型枚举"""
    TASK_ASSIGNMENT = "task_assignment"      # 任务分配
    TASK_RESULT = "task_result"              # 任务结果
    STATUS_UPDATE = "status_update"          # 状态更新
    COORDINATION = "coordination"            # 协调请求
    NOTIFICATION = "notification"            # 通知
    ERROR = "error"                          # 错误
    HEARTBEAT = "heartbeat"                  # 心跳


class MessagePriority(Enum):
    """消息优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class Message:
    """消息数据结构"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType = MessageType.NOTIFICATION
    priority: MessagePriority = MessagePriority.NORMAL
    sender: str = ""
    recipient: str = ""
    content: Any = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3


class CommunicationManager:
    """通信管理器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # 消息存储
        self.message_queues: Dict[str, asyncio.Queue] = {}
        self.message_history: List[Message] = []
        
        # 消息处理器
        self.message_handlers: Dict[MessageType, List[Callable]] = {}
        
        # 订阅者
        self.subscribers: Dict[str, List[str]] = {}  # topic -> [agent_ids]
        
        # 广播通道
        self.broadcast_channels: Dict[str, asyncio.Queue] = {}
        
        # 运行状态
        self.running = False
        
        # 统计信息
        self.stats = {
            "messages_sent": 0,
            "messages_received": 0,
            "messages_failed": 0,
            "active_agents": 0
        }
    
    async def start(self):
        """启动通信管理器"""
        if self.running:
            return
        
        self.running = True
        self.logger.info("通信管理器启动")
        
        # 启动消息处理循环
        asyncio.create_task(self._message_processing_loop())
        
        # 启动清理循环
        asyncio.create_task(self._cleanup_loop())
    
    async def stop(self):
        """停止通信管理器"""
        self.running = False
        self.logger.info("通信管理器停止")
    
    def register_agent(self, agent_id: str) -> asyncio.Queue:
        """
        注册智能体
        
        Args:
            agent_id: 智能体ID
            
        Returns:
            智能体的消息队列
        """
        if agent_id not in self.message_queues:
            self.message_queues[agent_id] = asyncio.Queue()
            self.stats["active_agents"] += 1
            self.logger.info(f"智能体 {agent_id} 已注册")
        
        return self.message_queues[agent_id]
    
    def unregister_agent(self, agent_id: str):
        """
        注销智能体
        
        Args:
            agent_id: 智能体ID
        """
        if agent_id in self.message_queues:
            del self.message_queues[agent_id]
            self.stats["active_agents"] -= 1
            self.logger.info(f"智能体 {agent_id} 已注销")
    
    def register_message_handler(self, message_type: MessageType, handler: Callable):
        """
        注册消息处理器
        
        Args:
            message_type: 消息类型
            handler: 处理函数
        """
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []
        
        self.message_handlers[message_type].append(handler)
        self.logger.info(f"注册消息处理器: {message_type.value}")
    
    def subscribe_to_topic(self, agent_id: str, topic: str):
        """
        订阅主题
        
        Args:
            agent_id: 智能体ID
            topic: 主题名称
        """
        if topic not in self.subscribers:
            self.subscribers[topic] = []
        
        if agent_id not in self.subscribers[topic]:
            self.subscribers[topic].append(agent_id)
            self.logger.info(f"智能体 {agent_id} 订阅主题: {topic}")
    
    def unsubscribe_from_topic(self, agent_id: str, topic: str):
        """
        取消订阅主题
        
        Args:
            agent_id: 智能体ID
            topic: 主题名称
        """
        if topic in self.subscribers and agent_id in self.subscribers[topic]:
            self.subscribers[topic].remove(agent_id)
            self.logger.info(f"智能体 {agent_id} 取消订阅主题: {topic}")
    
    async def send_message(
        self,
        recipient: str,
        message_type: MessageType,
        content: Any,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None,
        expires_at: Optional[datetime] = None
    ) -> str:
        """
        发送消息
        
        Args:
            recipient: 接收者ID
            message_type: 消息类型
            content: 消息内容
            priority: 优先级
            metadata: 元数据
            expires_at: 过期时间
            
        Returns:
            消息ID
        """
        message = Message(
            type=message_type,
            priority=priority,
            sender="system",
            recipient=recipient,
            content=content,
            metadata=metadata or {},
            expires_at=expires_at
        )
        
        # 添加到消息历史
        self.message_history.append(message)
        
        # 发送到接收者队列
        if recipient in self.message_queues:
            await self.message_queues[recipient].put(message)
            self.stats["messages_sent"] += 1
            self.logger.debug(f"消息已发送: {message.id} -> {recipient}")
        else:
            self.logger.warning(f"接收者 {recipient} 不存在")
            self.stats["messages_failed"] += 1
        
        return message.id
    
    async def broadcast_message(
        self,
        message_type: MessageType,
        content: Any,
        topic: Optional[str] = None,
        priority: MessagePriority = MessagePriority.NORMAL,
        metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        广播消息
        
        Args:
            message_type: 消息类型
            content: 消息内容
            topic: 主题（如果指定，只发送给订阅者）
            priority: 优先级
            metadata: 元数据
            
        Returns:
            消息ID列表
        """
        message_ids = []
        
        if topic:
            # 发送给主题订阅者
            subscribers = self.subscribers.get(topic, [])
            for agent_id in subscribers:
                message_id = await self.send_message(
                    agent_id, message_type, content, priority, metadata
                )
                message_ids.append(message_id)
        else:
            # 发送给所有智能体
            for agent_id in self.message_queues.keys():
                message_id = await self.send_message(
                    agent_id, message_type, content, priority, metadata
                )
                message_ids.append(message_id)
        
        self.logger.info(f"广播消息已发送: {len(message_ids)} 个接收者")
        
        return message_ids
    
    async def receive_message(self, agent_id: str, timeout: Optional[float] = None) -> Optional[Message]:
        """
        接收消息
        
        Args:
            agent_id: 智能体ID
            timeout: 超时时间
            
        Returns:
            接收到的消息
        """
        if agent_id not in self.message_queues:
            return None
        
        try:
            if timeout:
                message = await asyncio.wait_for(
                    self.message_queues[agent_id].get(),
                    timeout=timeout
                )
            else:
                message = await self.message_queues[agent_id].get()
            
            # 检查消息是否过期
            if message.expires_at and message.expires_at < datetime.now():
                self.logger.warning(f"消息 {message.id} 已过期")
                return None
            
            self.stats["messages_received"] += 1
            return message
            
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            self.logger.error(f"接收消息出错: {e}")
            return None
    
    async def send_task_assignment(
        self,
        agent_id: str,
        task: Dict[str, Any],
        priority: MessagePriority = MessagePriority.NORMAL
    ) -> str:
        """
        发送任务分配消息
        
        Args:
            agent_id: 智能体ID
            task: 任务信息
            priority: 优先级
            
        Returns:
            消息ID
        """
        return await self.send_message(
            agent_id,
            MessageType.TASK_ASSIGNMENT,
            task,
            priority,
            {"task_type": task.get("type", "unknown")}
        )
    
    async def send_task_result(
        self,
        agent_id: str,
        task_id: str,
        result: Dict[str, Any],
        success: bool = True
    ) -> str:
        """
        发送任务结果消息
        
        Args:
            agent_id: 智能体ID
            task_id: 任务ID
            result: 结果信息
            success: 是否成功
            
        Returns:
            消息ID
        """
        return await self.send_message(
            agent_id,
            MessageType.TASK_RESULT,
            {
                "task_id": task_id,
                "result": result,
                "success": success,
                "timestamp": datetime.now().isoformat()
            },
            MessagePriority.HIGH
        )
    
    async def send_status_update(
        self,
        agent_id: str,
        status: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        发送状态更新消息
        
        Args:
            agent_id: 智能体ID
            status: 状态信息
            metadata: 元数据
            
        Returns:
            消息ID
        """
        return await self.send_message(
            agent_id,
            MessageType.STATUS_UPDATE,
            {
                "agent_id": agent_id,
                "status": status,
                "timestamp": datetime.now().isoformat()
            },
            MessagePriority.NORMAL,
            metadata
        )
    
    async def send_coordination_request(
        self,
        requester: str,
        request_type: str,
        data: Dict[str, Any],
        target_agents: Optional[List[str]] = None
    ) -> List[str]:
        """
        发送协调请求
        
        Args:
            requester: 请求者ID
            request_type: 请求类型
            data: 请求数据
            target_agents: 目标智能体列表
            
        Returns:
            消息ID列表
        """
        message_ids = []
        
        if target_agents:
            for agent_id in target_agents:
                message_id = await self.send_message(
                    agent_id,
                    MessageType.COORDINATION,
                    {
                        "requester": requester,
                        "request_type": request_type,
                        "data": data,
                        "timestamp": datetime.now().isoformat()
                    },
                    MessagePriority.HIGH
                )
                message_ids.append(message_id)
        else:
            # 广播给所有智能体
            message_ids = await self.broadcast_message(
                MessageType.COORDINATION,
                {
                    "requester": requester,
                    "request_type": request_type,
                    "data": data,
                    "timestamp": datetime.now().isoformat()
                },
                priority=MessagePriority.HIGH
            )
        
        return message_ids
    
    async def get_message_history(
        self,
        agent_id: Optional[str] = None,
        message_type: Optional[MessageType] = None,
        limit: int = 100
    ) -> List[Message]:
        """
        获取消息历史
        
        Args:
            agent_id: 智能体ID过滤
            message_type: 消息类型过滤
            limit: 限制数量
            
        Returns:
            消息列表
        """
        messages = self.message_history.copy()
        
        if agent_id:
            messages = [m for m in messages if m.sender == agent_id or m.recipient == agent_id]
        
        if message_type:
            messages = [m for m in messages if m.type == message_type]
        
        # 按时间排序
        messages.sort(key=lambda x: x.timestamp, reverse=True)
        
        return messages[:limit]
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        return {
            **self.stats,
            "message_types": self._get_message_type_stats(),
            "active_topics": list(self.subscribers.keys()),
            "message_history_size": len(self.message_history)
        }
    
    def _get_message_type_stats(self) -> Dict[str, int]:
        """获取消息类型统计"""
        stats = {}
        for message in self.message_history:
            msg_type = message.type.value
            stats[msg_type] = stats.get(msg_type, 0) + 1
        return stats
    
    async def _message_processing_loop(self):
        """消息处理循环"""
        while self.running:
            try:
                # 处理消息历史中的过期消息
                current_time = datetime.now()
                expired_messages = [
                    msg for msg in self.message_history
                    if msg.expires_at and msg.expires_at < current_time
                ]
                
                for msg in expired_messages:
                    self.message_history.remove(msg)
                
                await asyncio.sleep(1)
                
            except Exception as e:
                self.logger.error(f"消息处理循环出错: {e}")
                await asyncio.sleep(1)
    
    async def _cleanup_loop(self):
        """清理循环"""
        while self.running:
            try:
                # 清理过期的消息历史（保留最近1000条）
                if len(self.message_history) > 1000:
                    self.message_history = self.message_history[-1000:]
                
                await asyncio.sleep(60)  # 每分钟清理一次
                
            except Exception as e:
                self.logger.error(f"清理循环出错: {e}")
                await asyncio.sleep(60)
