
"""
任务管理器

负责任务的创建、调度、监控和管理
"""

# Celery 实例定义
from celery import Celery
celery = Celery('task_manager', broker='redis://localhost:6379/0')


import asyncio
import uuid
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from enum import Enum
from dataclasses import dataclass, field

from ..utils.logger import get_logger

logger = get_logger(__name__)


class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"         # 等待中
    PLANNING = "planning"       # 规划中
    EXECUTING = "executing"     # 执行中
    MONITORING = "monitoring"   # 监控中
    COMPLETED = "completed"     # 已完成
    FAILED = "failed"          # 失败
    CANCELLED = "cancelled"     # 已取消
    PAUSED = "paused"          # 已暂停


class TaskPriority(Enum):
    """任务优先级枚举"""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    URGENT = 4


@dataclass
class TaskInfo:
    """任务信息"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    name: str = ""
    description: str = ""
    priority: TaskPriority = TaskPriority.NORMAL
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_agents: List[str] = field(default_factory=list)
    subtasks: List[Dict[str, Any]] = field(default_factory=list)
    execution_plan: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None  # 超时时间（秒）
    metadata: Dict[str, Any] = field(default_factory=dict)


class TaskManager:
    """任务管理器"""
    
    def __init__(self):
        self.logger = get_logger(__name__)
        
        # 任务存储
        self.tasks: Dict[str, TaskInfo] = {}
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        
        # 任务类型处理器
        self.task_handlers: Dict[str, Callable] = {}
        
        # 状态监听器
        self.status_listeners: List[Callable] = []
        
        # 统计信息
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "active_tasks": 0
        }
        
        # 运行状态
        self.running = False
        self.processing_task = None
    
    async def start(self):
        """启动任务管理器"""
        if self.running:
            return
        
        self.running = True
        self.logger.info("任务管理器启动")
        
        # 启动任务处理循环
        asyncio.create_task(self._task_processing_loop())
        
        # 启动超时检查循环
        asyncio.create_task(self._timeout_check_loop())
    
    async def stop(self):
        """停止任务管理器"""
        self.running = False
        self.logger.info("任务管理器停止")
    
    def register_task_handler(self, task_type: str, handler: Callable):
        """
        注册任务类型处理器
        
        Args:
            task_type: 任务类型
            handler: 处理函数
        """
        self.task_handlers[task_type] = handler
        self.logger.info(f"注册任务处理器: {task_type}")
    
    def add_status_listener(self, listener: Callable):
        """
        添加状态监听器
        
        Args:
            listener: 监听函数
        """
        self.status_listeners.append(listener)
    
    async def create_task(
        self,
        task_type: str,
        name: str,
        description: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        timeout: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        创建新任务
        
        Args:
            task_type: 任务类型
            name: 任务名称
            description: 任务描述
            priority: 优先级
            timeout: 超时时间
            metadata: 元数据
            
        Returns:
            任务ID
        """
        task = TaskInfo(
            type=task_type,
            name=name,
            description=description,
            priority=priority,
            timeout=timeout,
            metadata=metadata or {}
        )
        
        self.tasks[task.id] = task
        self.stats["total_tasks"] += 1
        self.stats["active_tasks"] += 1
        
        # 添加到任务队列（优先级队列）
        await self.task_queue.put((priority.value, task.id))
        
        self.logger.info(f"创建任务: {task.id} - {name}")
        
        # 通知状态监听器
        await self._notify_status_change(task.id, TaskStatus.PENDING)
        
        return task.id
    
    async def get_task(self, task_id: str) -> Optional[TaskInfo]:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息
        """
        return self.tasks.get(task_id)
    
    async def get_task_status(self, task_id: str) -> Optional[TaskStatus]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态
        """
        task = self.tasks.get(task_id)
        return task.status if task else None
    
    async def update_task_status(self, task_id: str, status: TaskStatus, error: Optional[str] = None):
        """
        更新任务状态
        
        Args:
            task_id: 任务ID
            status: 新状态
            error: 错误信息（如果有）
        """
        task = self.tasks.get(task_id)
        if not task:
            return
        
        old_status = task.status
        task.status = status
        
        if status == TaskStatus.EXECUTING and not task.started_at:
            task.started_at = datetime.now()
        elif status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            task.completed_at = datetime.now()
            self.stats["active_tasks"] -= 1
            
            if status == TaskStatus.COMPLETED:
                self.stats["completed_tasks"] += 1
            elif status == TaskStatus.FAILED:
                self.stats["failed_tasks"] += 1
        
        if error:
            task.error = error
        
        self.logger.info(f"任务 {task_id} 状态更新: {old_status.value} -> {status.value}")
        
        # 通知状态监听器
        await self._notify_status_change(task_id, status, error)
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功取消
        """
        task = self.tasks.get(task_id)
        if not task or task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            return False
        
        await self.update_task_status(task_id, TaskStatus.CANCELLED)
        self.logger.info(f"任务 {task_id} 已取消")
        
        return True
    
    async def pause_task(self, task_id: str) -> bool:
        """
        暂停任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功暂停
        """
        task = self.tasks.get(task_id)
        if not task or task.status not in [TaskStatus.EXECUTING, TaskStatus.MONITORING]:
            return False
        
        await self.update_task_status(task_id, TaskStatus.PAUSED)
        self.logger.info(f"任务 {task_id} 已暂停")
        
        return True
    
    async def resume_task(self, task_id: str) -> bool:
        """
        恢复任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功恢复
        """
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.PAUSED:
            return False
        
        await self.update_task_status(task_id, TaskStatus.EXECUTING)
        self.logger.info(f"任务 {task_id} 已恢复")
        
        return True
    
    async def retry_task(self, task_id: str) -> bool:
        """
        重试任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功重试
        """
        task = self.tasks.get(task_id)
        if not task or task.status != TaskStatus.FAILED:
            return False
        
        if task.retry_count >= task.max_retries:
            self.logger.warning(f"任务 {task_id} 已达到最大重试次数")
            return False
        
        task.retry_count += 1
        task.status = TaskStatus.PENDING
        task.error = None
        
        # 重新加入队列
        await self.task_queue.put((task.priority.value, task.id))
        
        self.logger.info(f"任务 {task_id} 重试 (第 {task.retry_count} 次)")
        
        return True
    
    async def get_task_list(
        self,
        status: Optional[TaskStatus] = None,
        task_type: Optional[str] = None,
        limit: int = 100
    ) -> List[TaskInfo]:
        """
        获取任务列表
        
        Args:
            status: 状态过滤
            task_type: 类型过滤
            limit: 限制数量
            
        Returns:
            任务列表
        """
        tasks = list(self.tasks.values())
        
        if status:
            tasks = [t for t in tasks if t.status == status]
        
        if task_type:
            tasks = [t for t in tasks if t.type == task_type]
        
        # 按创建时间排序
        tasks.sort(key=lambda x: x.created_at, reverse=True)
        
        return tasks[:limit]
    
    async def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            统计信息字典
        """
        return {
            **self.stats,
            "task_types": self._get_task_type_stats(),
            "status_distribution": self._get_status_distribution(),
            "average_execution_time": self._get_average_execution_time()
        }
    
    def _get_task_type_stats(self) -> Dict[str, int]:
        """获取任务类型统计"""
        stats = {}
        for task in self.tasks.values():
            stats[task.type] = stats.get(task.type, 0) + 1
        return stats
    
    def _get_status_distribution(self) -> Dict[str, int]:
        """获取状态分布"""
        stats = {}
        for task in self.tasks.values():
            status = task.status.value
            stats[status] = stats.get(status, 0) + 1
        return stats
    
    def _get_average_execution_time(self) -> float:
        """获取平均执行时间"""
        completed_tasks = [
            task for task in self.tasks.values()
            if task.status == TaskStatus.COMPLETED and task.started_at and task.completed_at
        ]
        
        if not completed_tasks:
            return 0.0
        
        total_time = sum(
            (task.completed_at - task.started_at).total_seconds()
            for task in completed_tasks
        )
        
        return total_time / len(completed_tasks)
    
    async def _task_processing_loop(self):
        """任务处理循环"""
        while self.running:
            try:
                # 等待任务
                priority, task_id = await self.task_queue.get()
                task = self.tasks.get(task_id)
                
                if not task or task.status != TaskStatus.PENDING:
                    continue
                
                # 检查是否超时
                if task.timeout and task.created_at + timedelta(seconds=task.timeout) < datetime.now():
                    await self.update_task_status(task_id, TaskStatus.FAILED, "任务超时")
                    continue
                
                self.processing_task = task_id
                await self.update_task_status(task_id, TaskStatus.EXECUTING)
                
                # 执行任务
                await self._execute_task(task)
                
            except Exception as e:
                self.logger.error(f"任务处理循环出错: {e}")
                if self.processing_task:
                    await self.update_task_status(self.processing_task, TaskStatus.FAILED, str(e))
                self.processing_task = None
            
            await asyncio.sleep(0.1)
    
    async def _execute_task(self, task: TaskInfo):
        """执行任务"""
        try:
            handler = self.task_handlers.get(task.type)
            if not handler:
                raise ValueError(f"未找到任务类型 {task.type} 的处理器")
            
            # 执行任务处理器
            result = await handler(task)
            
            # 更新任务结果
            task.results = result
            await self.update_task_status(task.id, TaskStatus.COMPLETED)
            
        except Exception as e:
            self.logger.error(f"任务 {task.id} 执行失败: {e}")
            await self.update_task_status(task.id, TaskStatus.FAILED, str(e))
        
        finally:
            self.processing_task = None
    
    async def _timeout_check_loop(self):
        """超时检查循环"""
        while self.running:
            try:
                current_time = datetime.now()
                
                for task in self.tasks.values():
                    if (task.status in [TaskStatus.EXECUTING, TaskStatus.MONITORING] and
                        task.timeout and
                        task.started_at and
                        task.started_at + timedelta(seconds=task.timeout) < current_time):
                        
                        await self.update_task_status(task.id, TaskStatus.FAILED, "任务执行超时")
                
                await asyncio.sleep(10)  # 每10秒检查一次
                
            except Exception as e:
                self.logger.error(f"超时检查出错: {e}")
                await asyncio.sleep(10)
    
    async def _notify_status_change(self, task_id: str, status: TaskStatus, error: Optional[str] = None):
        """通知状态变化"""
        for listener in self.status_listeners:
            try:
                await listener(task_id, status, error)
            except Exception as e:
                self.logger.error(f"状态监听器出错: {e}")
