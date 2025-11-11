"""
多智能体协调器

负责协调多个智能体的协作，管理任务分发和执行
"""

import asyncio
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass, field

from langchain_core.language_models.llms import BaseLLM
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

from ..agents import PlannerAgent, ExecutorAgent, MonitorAgent, BrowserAgent
from ..utils.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class CompatibleChatOpenAI(ChatOpenAI):
    """兼容旧版API的ChatOpenAI包装类，移除max_completion_tokens参数"""
    
    def __init__(self, **kwargs):
        """初始化，确保不使用max_completion_tokens"""
        # 移除 max_completion_tokens，只使用 max_tokens
        kwargs.pop('max_completion_tokens', None)
        super().__init__(**kwargs)
    
    @property
    def _default_params(self):
        """覆盖默认参数，移除max_completion_tokens"""
        params = super()._default_params.copy()
        # 移除 max_completion_tokens 参数
        params.pop('max_completion_tokens', None)
        return params
    
    def _get_invocation_params(self, stop=None, **kwargs):
        """覆盖调用参数，移除max_completion_tokens"""
        params = super()._get_invocation_params(stop=stop, **kwargs)
        # 移除 max_completion_tokens，只保留 max_tokens
        params.pop('max_completion_tokens', None)
        return params


@dataclass
class Task:
    """任务数据结构"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    description: str = ""
    requirements: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, planning, executing, completed, failed
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    assigned_agents: List[str] = field(default_factory=list)
    subtasks: List[Dict[str, Any]] = field(default_factory=list)
    execution_plan: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class MultiAgentCoordinator:
    """多智能体协调器"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = get_logger(__name__)
        
        # 智能体实例
        self.agents: Dict[str, Any] = {}
        self.agent_status: Dict[str, str] = {}
        
        # 任务管理
        self.tasks: Dict[str, Task] = {}
        self.task_queue: asyncio.Queue = asyncio.Queue()
        
        # 通信管理
        self.message_handlers: Dict[str, callable] = {}
        
        # 初始化标志
        self.initialized = False
    
    async def initialize(self):
        """初始化协调器"""
        try:
            self.logger.info("初始化多智能体协调器...")
            
            # 初始化智能体
            await self._initialize_agents()
            
            # 设置消息处理器
            self._setup_message_handlers()
            
            # 启动任务处理循环
            asyncio.create_task(self._task_processing_loop())
            
            self.initialized = True
            self.logger.info("多智能体协调器初始化完成")
            
        except Exception as e:
            self.logger.error(f"协调器初始化失败: {e}")
            raise
    
    import uuid
    from typing import Dict, Any

    # 假设你的 Agent 类都已经导入
    from ..agents import PlannerAgent, ExecutorAgent, MonitorAgent, BrowserAgent
    from ..agents.base import BaseAgent


    async def _initialize_agents(self) -> None:
        """初始化所有智能体"""
        agent_configs: Dict[str, Any] = self.config.get("agents", {})

        for agent_type, raw_config in agent_configs.items():
            try:
                # 1. 创建 LLM 实例
                llm = self._create_llm(raw_config)

                # 2. 弹出会与显式参数冲突的键，避免重复传值
                config = raw_config.copy()          # 防止修改原配置
                name: str = config.pop("name", agent_type)          # 默认用类型名
                description: str = config.pop("description", "")
                # agent_id 我们自己生成，不允许配置里再传
                _ = config.pop("agent_id", None)

                agent_id = f"{agent_type}_{uuid.uuid4().hex[:8]}"

                # 3. 按类型实例化
                if agent_type == "planner":
                    agent = PlannerAgent(
                        name=name,
                        agent_id=agent_id,
                        llm=llm,
                        description=description,
                        **config,
                    )
                elif agent_type == "executor":
                    agent = ExecutorAgent(
                        name=name,
                        agent_id=agent_id,
                        llm=llm,
                        description=description,
                        **config,
                    )
                elif agent_type == "monitor":
                    agent = MonitorAgent(
                        name=name,
                        agent_id=agent_id,
                        llm=llm,
                        description=description,
                        **config,
                    )
                elif agent_type == "browser":
                    agent = BrowserAgent(
                        name=name,
                        agent_id=agent_id,
                        llm=llm,
                        description=description,
                        **config,
                    )
                else:
                    self.logger.warning(f"未知的智能体类型: {agent_type}")
                    continue

                # 4. 注册到协调器
                self.agents[agent.agent_id] = agent
                self.agent_status[agent.agent_id] = "idle"
                self.logger.info(f"智能体 {agent.name} 初始化完成")

            except Exception as e:
                import traceback, sys
                traceback.print_exc()   # 把完整堆栈打出来  
                self.logger.error(f"智能体 {agent_type} 初始化失败: {e}")  
              
    def _create_llm(self, config: Dict[str, Any]) -> BaseLLM:
        """创建LLM实例"""
        provider = config.get("provider", "openai")
        model = config.get("model", "gpt-3.5-turbo")
        
        if provider == "openai":
            # 使用兼容包装类，移除 max_completion_tokens 参数以兼容旧版 API
            llm = CompatibleChatOpenAI(
                model=model,
                temperature=config.get("temperature", 0.7),
                api_key=self.config.get("models.providers.openai.api_key"),
                base_url=self.config.get("models.providers.openai.base_url"),
                max_tokens=config.get("max_tokens", 1000)
            )
            return llm
        elif provider == "anthropic":
            return ChatAnthropic(
                model=model,
                temperature=config.get("temperature", 0.7),
                max_tokens=config.get("max_tokens", 1000),
                api_key=self.config.get("models.providers.anthropic.api_key")
            )
        else:
            raise ValueError(f"不支持的LLM提供商: {provider}")
    
    def _setup_message_handlers(self):
        """设置消息处理器"""
        self.message_handlers = {
            "task_completed": self._handle_task_completed,
            "task_failed": self._handle_task_failed,
            "agent_status_update": self._handle_agent_status_update,
            "coordination_request": self._handle_coordination_request
        }
    
    async def submit_task(self, task_data: Dict[str, Any]) -> str:
        """
        提交新任务
        
        Args:
            task_data: 任务数据字典
            
        Returns:
            任务ID
        """
        if not self.initialized:
            await self.initialize()
        
        # 创建任务对象
        task = Task(
            type=task_data.get("type", "general"),
            description=task_data.get("description", ""),
            requirements=task_data.get("requirements", {}),
            status="pending"
        )
        
        # 添加到任务字典
        self.tasks[task.id] = task
        
        # 添加到任务队列
        await self.task_queue.put(task.id)
        
        self.logger.info(f"任务 {task.id} 已提交: {task.description[:50]}...")
        
        return task.id
    
    async def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务状态字典
        """
        task = self.tasks.get(task_id)
        if not task:
            return None
        
        return {
            "task_id": task.id,
            "type": task.type,
            "description": task.description,
            "status": task.status,
            "created_at": task.created_at.isoformat(),
            "started_at": task.started_at.isoformat() if task.started_at else None,
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "assigned_agents": task.assigned_agents,
            "subtasks_count": len(task.subtasks),
            "error": task.error
        }
    
    async def get_task_result(self, task_id: str) -> Optional[Dict[str, Any]]:
        """
        获取任务结果
        
        Args:
            task_id: 任务ID
            
        Returns:
            任务结果字典
        """
        task = self.tasks.get(task_id)
        if not task or task.status != "completed":
            return None
        
        return task.results
    
    async def get_agent_status(self) -> Dict[str, Any]:
        """
        获取所有智能体状态
        
        Returns:
            智能体状态字典
        """
        status_info = {}
        for agent_id, agent in self.agents.items():
            status_info[agent_id] = {
                "agent_id": agent_id,
                "name": agent.name,
                "status": agent.status.value,
                "current_task": agent.current_task,
                "task_count": len(agent.task_history),
                "capabilities": agent.capabilities.dict()
            }
        
        return status_info
    
    async def _task_processing_loop(self):
        """任务处理循环"""
        while True:
            try:
                # 等待新任务
                task_id = await self.task_queue.get()
                task = self.tasks.get(task_id)
                
                if not task:
                    continue
                
                self.logger.info(f"开始处理任务: {task_id}")
                
                # 更新任务状态
                task.status = "planning"
                task.started_at = datetime.now()
                
                # 执行任务
                await self._execute_task(task)
                
            except Exception as e:
                self.logger.error(f"任务处理循环出错: {e}")
                await asyncio.sleep(1)
    
    async def _execute_task(self, task: Task):
        """执行任务"""
        try:
            # 1. 任务规划阶段
            self.logger.info(f"任务 {task.id} 进入规划阶段")
            planner = self._get_agent_by_type("planner")
            if not planner:
                raise ValueError("未找到规划智能体")
            
            planning_result = await planner.execute({
                "id": task.id,
                "type": task.type,
                "description": task.description,
                "requirements": task.requirements
            })
            
            task.subtasks = planning_result.get("subtasks", [])
            task.execution_plan = planning_result.get("execution_plan", {})
            task.assigned_agents = list(planning_result.get("agent_assignments", {}).values())
            
            # 2. 任务执行阶段
            task.status = "executing"
            self.logger.info(f"任务 {task.id} 进入执行阶段")
            
            execution_results = []
            for subtask in task.subtasks:
                subtask_id = subtask["id"]
                agent_type = planning_result.get("agent_assignments", {}).get(subtask_id, "executor")
                
                # 获取对应的智能体
                agent = self._get_agent_by_type(agent_type)
                if not agent:
                    self.logger.warning(f"未找到智能体类型: {agent_type}")
                    continue
                
                # 执行子任务
                subtask_result = await agent.execute(subtask)
                execution_results.append(subtask_result)
            
            # 3. 任务监督阶段
            self.logger.info(f"任务 {task.id} 进入监督阶段")
            monitor = self._get_agent_by_type("monitor")
            if monitor:
                monitoring_result = await monitor.execute({
                    "type": "task_monitoring",
                    "task_id": task.id,
                    "execution_data": {
                        "subtasks": task.subtasks,
                        "execution_results": execution_results,
                        "execution_plan": task.execution_plan
                    }
                })
            else:
                monitoring_result = {"status": "no_monitor"}
            
            # 4. 生成最终结果
            task.results = {
                "planning_result": planning_result,
                "execution_results": execution_results,
                "monitoring_result": monitoring_result,
                "final_output": self._generate_final_output(planning_result, execution_results, monitoring_result),
                "execution_summary": {
                    "total_subtasks": len(task.subtasks),
                    "completed_subtasks": len([r for r in execution_results if r.get("success", False)]),
                    "execution_time": (datetime.now() - task.started_at).total_seconds(),
                    "assigned_agents": task.assigned_agents
                }
            }
            
            task.status = "completed"
            task.completed_at = datetime.now()
            
            self.logger.info(f"任务 {task.id} 执行完成")
            
        except Exception as e:
            self.logger.error(f"任务 {task.id} 执行失败: {e}")
            task.status = "failed"
            task.error = str(e)
            task.completed_at = datetime.now()
    
    def _get_agent_by_type(self, agent_type: str) -> Optional[Any]:
        """根据类型获取智能体"""
        for agent in self.agents.values():
            if agent_type in agent.__class__.__name__.lower():
                return agent
        return None
    
    def _generate_final_output(self, planning_result: Dict[str, Any], execution_results: List[Dict[str, Any]], monitoring_result: Dict[str, Any]) -> Dict[str, Any]:
        """生成最终输出"""
        return {
            "summary": "任务执行完成",
            "planning": planning_result,
            "execution": execution_results,
            "monitoring": monitoring_result,
            "generated_at": datetime.now().isoformat()
        }
    
    async def _handle_task_completed(self, message: Dict[str, Any]):
        """处理任务完成消息"""
        task_id = message.get("task_id")
        self.logger.info(f"任务 {task_id} 完成")
    
    async def _handle_task_failed(self, message: Dict[str, Any]):
        """处理任务失败消息"""
        task_id = message.get("task_id")
        error = message.get("error")
        self.logger.error(f"任务 {task_id} 失败: {error}")
    
    async def _handle_agent_status_update(self, message: Dict[str, Any]):
        """处理智能体状态更新消息"""
        agent_id = message.get("agent_id")
        status = message.get("status")
        self.agent_status[agent_id] = status
        self.logger.info(f"智能体 {agent_id} 状态更新为: {status}")
    
    async def _handle_coordination_request(self, message: Dict[str, Any]):
        """处理协调请求消息"""
        request_type = message.get("type")
        self.logger.info(f"收到协调请求: {request_type}")
    
    async def shutdown(self):
        """关闭协调器"""
        self.logger.info("关闭多智能体协调器...")
        
        # 等待当前任务完成
        while not self.task_queue.empty():
            await asyncio.sleep(0.1)
        
        # 清理资源
        for agent in self.agents.values():
            if hasattr(agent, 'cleanup'):
                await agent.cleanup()
        
        self.logger.info("多智能体协调器已关闭")
