"""
后台执行器

负责异步后台任务执行和持久化
"""

import asyncio
import json
import sqlite3
import uuid
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime, timedelta
from pathlib import Path
from dataclasses import dataclass, asdict

from ..utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BackgroundTask:
    """后台任务数据结构"""
    id: str
    name: str
    task_type: str
    data: Dict[str, Any]
    status: str = "pending"  # pending, running, completed, failed, cancelled
    priority: int = 1
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.metadata is None:
            self.metadata = {}


class BackgroundExecutor:
    """后台执行器"""
    
    def __init__(self, db_path: str = "background_tasks.db"):
        self.db_path = db_path
        self.logger = get_logger(__name__)
        
        # 任务存储
        self.tasks: Dict[str, BackgroundTask] = {}
        self.task_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        
        # 任务处理器
        self.task_handlers: Dict[str, Callable] = {}
        
        # 运行状态
        self.running = False
        self.workers: List[asyncio.Task] = []
        self.worker_count = 3
        
        # 数据库连接
        self.db_conn: Optional[sqlite3.Connection] = None
        
        # 统计信息
        self.stats = {
            "total_tasks": 0,
            "completed_tasks": 0,
            "failed_tasks": 0,
            "active_tasks": 0
        }
    
    async def start(self):
        """启动后台执行器"""
        if self.running:
            return
        
        try:
            self.logger.info("启动后台执行器...")
            
            # 初始化数据库
            await self._init_database()
            
            # 加载持久化的任务
            await self._load_persisted_tasks()
            
            # 启动工作线程
            self.running = True
            for i in range(self.worker_count):
                worker = asyncio.create_task(self._worker(f"worker-{i}"))
                self.workers.append(worker)
            
            self.logger.info(f"后台执行器已启动，工作线程数: {self.worker_count}")
            
        except Exception as e:
            self.logger.error(f"后台执行器启动失败: {e}")
            raise
    
    async def stop(self):
        """停止后台执行器"""
        if not self.running:
            return
        
        try:
            self.logger.info("停止后台执行器...")
            
            self.running = False
            
            # 等待工作线程完成
            for worker in self.workers:
                worker.cancel()
            
            await asyncio.gather(*self.workers, return_exceptions=True)
            self.workers.clear()
            
            # 关闭数据库连接
            if self.db_conn:
                self.db_conn.close()
                self.db_conn = None
            
            self.logger.info("后台执行器已停止")
            
        except Exception as e:
            self.logger.error(f"停止后台执行器时出错: {e}")
    
    async def _init_database(self):
        """初始化数据库"""
        try:
            self.db_conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.db_conn.row_factory = sqlite3.Row
            
            # 创建任务表
            cursor = self.db_conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS background_tasks (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    task_type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    status TEXT NOT NULL,
                    priority INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    started_at TEXT,
                    completed_at TEXT,
                    result TEXT,
                    error TEXT,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    timeout INTEGER,
                    metadata TEXT
                )
            """)
            
            self.db_conn.commit()
            self.logger.info("数据库初始化完成")
            
        except Exception as e:
            self.logger.error(f"数据库初始化失败: {e}")
            raise
    
    async def _load_persisted_tasks(self):
        """加载持久化的任务"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                SELECT * FROM background_tasks 
                WHERE status IN ('pending', 'running')
                ORDER BY priority DESC, created_at ASC
            """)
            
            rows = cursor.fetchall()
            
            for row in rows:
                task = BackgroundTask(
                    id=row['id'],
                    name=row['name'],
                    task_type=row['task_type'],
                    data=json.loads(row['data']),
                    status=row['status'],
                    priority=row['priority'],
                    created_at=datetime.fromisoformat(row['created_at']),
                    started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
                    completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
                    result=json.loads(row['result']) if row['result'] else None,
                    error=row['error'],
                    retry_count=row['retry_count'],
                    max_retries=row['max_retries'],
                    timeout=row['timeout'],
                    metadata=json.loads(row['metadata']) if row['metadata'] else {}
                )
                
                self.tasks[task.id] = task
                
                # 重新加入队列
                if task.status == "pending":
                    await self.task_queue.put((task.priority, task.id))
            
            self.logger.info(f"加载了 {len(rows)} 个持久化任务")
            
        except Exception as e:
            self.logger.error(f"加载持久化任务失败: {e}")
    
    async def _persist_task(self, task: BackgroundTask):
        """持久化任务"""
        try:
            cursor = self.db_conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO background_tasks 
                (id, name, task_type, data, status, priority, created_at, started_at, 
                 completed_at, result, error, retry_count, max_retries, timeout, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                task.id,
                task.name,
                task.task_type,
                json.dumps(task.data),
                task.status,
                task.priority,
                task.created_at.isoformat(),
                task.started_at.isoformat() if task.started_at else None,
                task.completed_at.isoformat() if task.completed_at else None,
                json.dumps(task.result) if task.result else None,
                task.error,
                task.retry_count,
                task.max_retries,
                task.timeout,
                json.dumps(task.metadata)
            ))
            
            self.db_conn.commit()
            
        except Exception as e:
            self.logger.error(f"持久化任务失败: {e}")
    
    def register_handler(self, task_type: str, handler: Callable):
        """
        注册任务处理器
        
        Args:
            task_type: 任务类型
            handler: 处理函数
        """
        self.task_handlers[task_type] = handler
        self.logger.info(f"注册任务处理器: {task_type}")
    
    async def submit_task(
        self,
        name: str,
        task_type: str,
        data: Dict[str, Any],
        priority: int = 1,
        timeout: Optional[int] = None,
        max_retries: int = 3,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        提交后台任务
        
        Args:
            name: 任务名称
            task_type: 任务类型
            data: 任务数据
            priority: 优先级（数字越小优先级越高）
            timeout: 超时时间（秒）
            max_retries: 最大重试次数
            metadata: 元数据
            
        Returns:
            任务ID
        """
        task_id = str(uuid.uuid4())
        
        task = BackgroundTask(
            id=task_id,
            name=name,
            task_type=task_type,
            data=data,
            priority=priority,
            timeout=timeout,
            max_retries=max_retries,
            metadata=metadata or {}
        )
        
        # 添加到内存
        self.tasks[task_id] = task
        
        # 持久化
        await self._persist_task(task)
        
        # 加入队列
        await self.task_queue.put((priority, task_id))
        
        self.stats["total_tasks"] += 1
        self.stats["active_tasks"] += 1
        
        self.logger.info(f"后台任务已提交: {task_id} - {name}")
        
        return task_id
    
    async def get_task(self, task_id: str) -> Optional[BackgroundTask]:
        """
        获取任务信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务信息
        """
        return self.tasks.get(task_id)
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        取消任务
        
        Args:
            task_id: 任务ID
            
        Returns:
            是否成功取消
        """
        task = self.tasks.get(task_id)
        if not task or task.status in ["completed", "failed", "cancelled"]:
            return False
        
        task.status = "cancelled"
        task.completed_at = datetime.now()
        
        await self._persist_task(task)
        
        self.stats["active_tasks"] -= 1
        
        self.logger.info(f"任务已取消: {task_id}")
        
        return True
    
    async def get_task_list(
        self,
        status: Optional[str] = None,
        task_type: Optional[str] = None,
        limit: int = 100
    ) -> List[BackgroundTask]:
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
            tasks = [t for t in tasks if t.task_type == task_type]
        
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
            stats[task.task_type] = stats.get(task.task_type, 0) + 1
        return stats
    
    def _get_status_distribution(self) -> Dict[str, int]:
        """获取状态分布"""
        stats = {}
        for task in self.tasks.values():
            stats[task.status] = stats.get(task.status, 0) + 1
        return stats
    
    def _get_average_execution_time(self) -> float:
        """获取平均执行时间"""
        completed_tasks = [
            task for task in self.tasks.values()
            if task.status == "completed" and task.started_at and task.completed_at
        ]
        
        if not completed_tasks:
            return 0.0
        
        total_time = sum(
            (task.completed_at - task.started_at).total_seconds()
            for task in completed_tasks
        )
        
        return total_time / len(completed_tasks)
    
    async def _worker(self, worker_name: str):
        """工作线程"""
        self.logger.info(f"工作线程启动: {worker_name}")
        
        while self.running:
            try:
                # 等待任务
                priority, task_id = await asyncio.wait_for(
                    self.task_queue.get(),
                    timeout=1.0
                )
                
                task = self.tasks.get(task_id)
                if not task or task.status != "pending":
                    continue
                
                # 检查超时
                if task.timeout and task.created_at + timedelta(seconds=task.timeout) < datetime.now():
                    task.status = "failed"
                    task.error = "任务超时"
                    task.completed_at = datetime.now()
                    await self._persist_task(task)
                    self.stats["active_tasks"] -= 1
                    self.stats["failed_tasks"] += 1
                    continue
                
                # 执行任务
                await self._execute_task(task, worker_name)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error(f"工作线程 {worker_name} 出错: {e}")
                await asyncio.sleep(1)
        
        self.logger.info(f"工作线程停止: {worker_name}")
    
    async def _execute_task(self, task: BackgroundTask, worker_name: str):
        """执行任务"""
        try:
            self.logger.info(f"开始执行任务: {task.id} - {task.name} (worker: {worker_name})")
            
            # 更新任务状态
            task.status = "running"
            task.started_at = datetime.now()
            await self._persist_task(task)
            
            # 获取处理器
            handler = self.task_handlers.get(task.task_type)
            if not handler:
                raise ValueError(f"未找到任务类型 {task.task_type} 的处理器")
            
            # 执行任务
            result = await handler(task.data)
            
            # 更新任务结果
            task.status = "completed"
            task.completed_at = datetime.now()
            task.result = result
            
            await self._persist_task(task)
            
            self.stats["active_tasks"] -= 1
            self.stats["completed_tasks"] += 1
            
            self.logger.info(f"任务执行完成: {task.id} - {task.name}")
            
        except Exception as e:
            self.logger.error(f"任务执行失败: {task.id} - {e}")
            
            # 检查是否需要重试
            if task.retry_count < task.max_retries:
                task.retry_count += 1
                task.status = "pending"
                task.error = str(e)
                
                await self._persist_task(task)
                
                # 重新加入队列
                await self.task_queue.put((task.priority, task.id))
                
                self.logger.info(f"任务将重试: {task.id} (第 {task.retry_count} 次)")
            else:
                task.status = "failed"
                task.error = str(e)
                task.completed_at = datetime.now()
                
                await self._persist_task(task)
                
                self.stats["active_tasks"] -= 1
                self.stats["failed_tasks"] += 1
                
                self.logger.error(f"任务最终失败: {task.id} - {e}")
    
    async def cleanup_old_tasks(self, days: int = 30):
        """
        清理旧任务
        
        Args:
            days: 保留天数
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # 从数据库删除旧任务
            cursor = self.db_conn.cursor()
            cursor.execute("""
                DELETE FROM background_tasks 
                WHERE completed_at IS NOT NULL 
                AND completed_at < ?
            """, (cutoff_date.isoformat(),))
            
            deleted_count = cursor.rowcount
            self.db_conn.commit()
            
            # 从内存中删除
            old_task_ids = [
                task_id for task_id, task in self.tasks.items()
                if task.completed_at and task.completed_at < cutoff_date
            ]
            
            for task_id in old_task_ids:
                del self.tasks[task_id]
            
            self.logger.info(f"清理了 {deleted_count} 个旧任务")
            
        except Exception as e:
            self.logger.error(f"清理旧任务失败: {e}")
