"""
规划智能体

负责任务分解、角色分配和执行计划制定
"""

import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from langchain_core.language_models.llms import BaseLLM
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from .base import BaseAgent, AgentCapabilities, AgentStatus
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PlannerAgent(BaseAgent):
    """规划智能体"""
    
    def __init__(self, agent_id: str, llm: BaseLLM, **kwargs):
        capabilities = AgentCapabilities(
            can_plan=True,
            can_analyze_data=True,
            max_tokens=2000,
            supported_formats=["text", "json", "yaml"]
        )
        
        system_prompt = """你是一个专业的任务规划智能体。你的职责是：

1. 分析用户输入的复杂任务
2. 将任务分解为多个可执行的子任务
3. 为每个子任务分配合适的智能体
4. 制定执行顺序和依赖关系
5. 监控任务执行进度并调整计划

请始终以结构化的方式输出规划结果，包括：
- 任务分解
- 智能体分配
- 执行顺序
- 依赖关系
- 预期输出格式"""

        super().__init__(
            agent_id=agent_id,
            name="任务规划智能体",
            description="负责复杂任务的分解和规划",
            llm=llm,
            capabilities=capabilities,
            system_prompt=system_prompt,
            **kwargs
        )
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行任务规划
        
        Args:
            task: 任务描述字典，包含任务类型、描述、要求等
            
        Returns:
            规划结果字典
        """
        try:
            self.update_status(AgentStatus.EXECUTING, "开始任务规划")
            self.current_task = task
            
            # 分析任务
            task_analysis = await self._analyze_task(task)
            
            # 分解任务
            subtasks = await self._decompose_task(task_analysis)
            
            # 分配智能体
            agent_assignments = await self._assign_agents(subtasks)
            
            # 制定执行计划
            execution_plan = await self._create_execution_plan(subtasks, agent_assignments)
            
            # 生成规划结果
            result = {
                "task_id": task.get("id", str(uuid.uuid4())),
                "original_task": task,
                "analysis": task_analysis,
                "subtasks": subtasks,
                "agent_assignments": agent_assignments,
                "execution_plan": execution_plan,
                "estimated_duration": self._estimate_duration(subtasks),
                "created_at": datetime.now().isoformat(),
                "status": "planned"
            }
            
            self.add_task_to_history(task, result)
            self.update_status(AgentStatus.COMPLETED, "任务规划完成")
            
            return result
            
        except Exception as e:
            self.logger.error(f"任务规划失败: {e}")
            self.update_status(AgentStatus.ERROR, f"规划失败: {str(e)}")
            raise
    
    async def _analyze_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """分析任务特征和要求"""
        prompt = f"""
请分析以下任务的类型、复杂度、要求和约束：

任务描述: {task.get('description', '')}
任务类型: {task.get('type', 'unknown')}
额外要求: {task.get('requirements', {})}

请从以下维度进行分析：
1. 任务复杂度（简单/中等/复杂）
2. 所需技能领域
3. 预期输出格式
4. 时间约束
5. 资源需求
6. 潜在风险点

请以JSON格式输出分析结果。
"""
        
        analysis_text = await self.think(prompt)
        
        try:
            # 尝试解析JSON
            analysis = json.loads(analysis_text)
        except json.JSONDecodeError:
            # 如果解析失败，创建基础分析
            analysis = {
                "complexity": "medium",
                "skill_domains": ["general"],
                "output_format": "text",
                "time_constraint": "flexible",
                "resource_requirements": [],
                "risks": []
            }
        
        return analysis
    
    async def _decompose_task(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """将任务分解为子任务"""
        prompt = f"""
基于以下任务分析，将任务分解为具体的可执行子任务：

任务分析: {json.dumps(analysis, ensure_ascii=False, indent=2)}

请将任务分解为3-8个具体的子任务，每个子任务应该：
1. 有明确的输入和输出
2. 可以独立执行
3. 有清晰的验收标准
4. 估计执行时间

请以JSON数组格式输出子任务列表，每个子任务包含：
- id: 子任务ID
- name: 子任务名称
- description: 详细描述
- input_requirements: 输入要求
- expected_output: 预期输出
- estimated_duration: 估计时间（分钟）
- priority: 优先级（1-5）
- dependencies: 依赖的其他子任务ID列表
"""
        
        decomposition_text = await self.think(prompt)
        
        try:
            subtasks = json.loads(decomposition_text)
        except json.JSONDecodeError:
            # 如果解析失败，创建基础分解
            subtasks = [
                {
                    "id": "subtask_1",
                    "name": "任务准备",
                    "description": "准备任务执行所需的基础信息",
                    "input_requirements": "原始任务描述",
                    "expected_output": "准备就绪状态",
                    "estimated_duration": 10,
                    "priority": 1,
                    "dependencies": []
                },
                {
                    "id": "subtask_2", 
                    "name": "任务执行",
                    "description": "执行主要任务逻辑",
                    "input_requirements": "准备阶段的输出",
                    "expected_output": "任务执行结果",
                    "estimated_duration": 30,
                    "priority": 2,
                    "dependencies": ["subtask_1"]
                },
                {
                    "id": "subtask_3",
                    "name": "结果整理",
                    "description": "整理和格式化执行结果",
                    "input_requirements": "任务执行结果",
                    "expected_output": "最终输出",
                    "estimated_duration": 10,
                    "priority": 3,
                    "dependencies": ["subtask_2"]
                }
            ]
        
        return subtasks
    
    async def _assign_agents(self, subtasks: List[Dict[str, Any]]) -> Dict[str, str]:
        """为子任务分配智能体"""
        prompt = f"""
基于以下子任务列表，为每个子任务分配合适的智能体：

子任务列表: {json.dumps(subtasks, ensure_ascii=False, indent=2)}

可用的智能体类型：
- planner: 任务规划智能体（适合分析和规划任务）
- executor: 任务执行智能体（适合执行具体任务）
- monitor: 任务监督智能体（适合监控和协调）
- browser: 浏览器操作智能体（适合需要网页操作的任务）

请为每个子任务分配合适的智能体，以JSON格式输出分配结果：
{{
    "subtask_id": "agent_type"
}}
"""
        
        assignment_text = await self.think(prompt)
        
        try:
            assignments = json.loads(assignment_text)
        except json.JSONDecodeError:
            # 如果解析失败，使用默认分配
            assignments = {}
            for subtask in subtasks:
                if "browser" in subtask.get("description", "").lower():
                    assignments[subtask["id"]] = "browser"
                elif "monitor" in subtask.get("description", "").lower():
                    assignments[subtask["id"]] = "monitor"
                else:
                    assignments[subtask["id"]] = "executor"
        
        return assignments
    
    async def _create_execution_plan(self, subtasks: List[Dict[str, Any]], assignments: Dict[str, str]) -> Dict[str, Any]:
        """创建执行计划"""
        # 根据依赖关系排序子任务
        sorted_subtasks = self._topological_sort(subtasks)
        
        # 创建执行阶段
        execution_phases = []
        current_phase = []
        current_dependencies = set()
        
        for subtask in sorted_subtasks:
            subtask_id = subtask["id"]
            dependencies = set(subtask.get("dependencies", []))
            
            # 如果当前子任务的依赖已经满足，可以加入当前阶段
            if dependencies.issubset(current_dependencies):
                current_phase.append(subtask_id)
            else:
                # 否则开始新阶段
                if current_phase:
                    execution_phases.append({
                        "phase": len(execution_phases) + 1,
                        "subtasks": current_phase,
                        "parallel": len(current_phase) > 1
                    })
                current_phase = [subtask_id]
            
            current_dependencies.add(subtask_id)
        
        # 添加最后一个阶段
        if current_phase:
            execution_phases.append({
                "phase": len(execution_phases) + 1,
                "subtasks": current_phase,
                "parallel": len(current_phase) > 1
            })
        
        return {
            "phases": execution_phases,
            "total_phases": len(execution_phases),
            "estimated_total_duration": sum(
                max(subtask["estimated_duration"] for subtask in subtasks 
                    if subtask["id"] in phase["subtasks"])
                for phase in execution_phases
            )
        }
    
    def _topological_sort(self, subtasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """拓扑排序子任务"""
        # 简化的拓扑排序实现
        sorted_tasks = []
        remaining_tasks = subtasks.copy()
        
        while remaining_tasks:
            # 找到没有未满足依赖的任务
            ready_tasks = []
            for task in remaining_tasks:
                dependencies = set(task.get("dependencies", []))
                completed_ids = {t["id"] for t in sorted_tasks}
                if dependencies.issubset(completed_ids):
                    ready_tasks.append(task)
            
            if not ready_tasks:
                # 如果找不到可执行的任务，可能存在循环依赖
                # 按优先级排序并添加
                ready_tasks = sorted(remaining_tasks, key=lambda x: x.get("priority", 5))
            
            # 添加优先级最高的任务
            next_task = min(ready_tasks, key=lambda x: x.get("priority", 5))
            sorted_tasks.append(next_task)
            remaining_tasks.remove(next_task)
        
        return sorted_tasks
    
    def _estimate_duration(self, subtasks: List[Dict[str, Any]]) -> int:
        """估算总执行时间"""
        return sum(subtask.get("estimated_duration", 0) for subtask in subtasks)
