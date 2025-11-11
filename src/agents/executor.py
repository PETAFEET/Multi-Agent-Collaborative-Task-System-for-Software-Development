"""
执行智能体

负责执行具体的子任务
"""

import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime

from langchain_core.language_models.llms import BaseLLM
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from .base import BaseAgent, AgentCapabilities, AgentStatus
from ..utils.logger import get_logger

logger = get_logger(__name__)


class ExecutorAgent(BaseAgent):
    """执行智能体"""
    
    def __init__(self, agent_id: str, llm: BaseLLM, **kwargs):
        capabilities = AgentCapabilities(
            can_execute=True,
            can_write_code=True,
            can_analyze_data=True,
            max_tokens=1000,
            supported_formats=["text", "json", "code"]
        )
        
        system_prompt = """你是一个专业的任务执行智能体。你的职责是：

1. 接收并理解分配给你的子任务
2. 制定详细的执行步骤
3. 调用相应的工具和API完成任务
4. 生成结构化的执行结果
5. 向监督智能体报告执行状态

请始终以清晰、结构化的方式输出执行结果，包括：
- 执行步骤
- 中间结果
- 最终输出
- 执行状态
- 错误信息（如有）"""

        super().__init__(
            agent_id=agent_id,
            name="任务执行智能体",
            description="负责执行具体的子任务",
            llm=llm,
            capabilities=capabilities,
            system_prompt=system_prompt,
            **kwargs
        )
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行子任务
        
        Args:
            task: 子任务描述字典
            
        Returns:
            执行结果字典
        """
        try:
            self.update_status(AgentStatus.EXECUTING, f"开始执行任务: {task.get('name', 'Unknown')}")
            self.current_task = task
            
            # 分析任务要求
            task_analysis = await self._analyze_subtask(task)
            
            # 制定执行计划
            execution_steps = await self._create_execution_steps(task_analysis)
            
            # 执行步骤
            execution_results = await self._execute_steps(execution_steps, task)
            
            # 生成最终结果
            final_result = await self._generate_final_result(execution_results, task)
            
            # 创建执行报告
            result = {
                "task_id": task.get("id", str(uuid.uuid4())),
                "subtask": task,
                "analysis": task_analysis,
                "execution_steps": execution_steps,
                "step_results": execution_results,
                "final_result": final_result,
                "execution_time": datetime.now().isoformat(),
                "status": "completed",
                "success": True
            }
            
            self.add_task_to_history(task, result)
            self.update_status(AgentStatus.COMPLETED, "任务执行完成")
            
            return result
            
        except Exception as e:
            self.logger.error(f"任务执行失败: {e}")
            self.update_status(AgentStatus.ERROR, f"执行失败: {str(e)}")
            
            # 返回错误结果
            error_result = {
                "task_id": task.get("id", str(uuid.uuid4())),
                "subtask": task,
                "error": str(e),
                "execution_time": datetime.now().isoformat(),
                "status": "failed",
                "success": False
            }
            
            self.add_task_to_history(task, error_result)
            return error_result
    
    async def _analyze_subtask(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """分析子任务要求"""
        prompt = f"""
请分析以下子任务的执行要求：

子任务信息:
- ID: {task.get('id', 'N/A')}
- 名称: {task.get('name', 'N/A')}
- 描述: {task.get('description', 'N/A')}
- 输入要求: {task.get('input_requirements', 'N/A')}
- 预期输出: {task.get('expected_output', 'N/A')}
- 优先级: {task.get('priority', 'N/A')}

请分析：
1. 任务类型和复杂度
2. 所需的具体操作步骤
3. 需要的工具或资源
4. 输出格式要求
5. 质量检查标准

请以JSON格式输出分析结果。
"""
        
        analysis_text = await self.think(prompt)
        
        try:
            analysis = json.loads(analysis_text)
        except json.JSONDecodeError:
            analysis = {
                "task_type": "general",
                "complexity": "medium",
                "required_operations": ["analyze", "process", "generate"],
                "tools_needed": [],
                "output_format": "text",
                "quality_checks": ["completeness", "accuracy"]
            }
        
        return analysis
    
    async def _create_execution_steps(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        """创建执行步骤"""
        prompt = f"""
基于以下任务分析，制定详细的执行步骤：

任务分析: {json.dumps(analysis, ensure_ascii=False, indent=2)}

请制定3-10个具体的执行步骤，每个步骤应该：
1. 有明确的操作描述
2. 有清晰的输入和输出
3. 可以独立验证
4. 估计执行时间

请以JSON数组格式输出执行步骤，每个步骤包含：
- step_id: 步骤ID
- name: 步骤名称
- description: 详细描述
- input: 输入要求
- output: 预期输出
- estimated_time: 估计时间（分钟）
- tools: 需要的工具列表
- validation: 验证方法
"""
        
        steps_text = await self.think(prompt)
        
        try:
            steps = json.loads(steps_text)
        except json.JSONDecodeError:
            # 如果解析失败，创建基础步骤
            steps = [
                {
                    "step_id": "step_1",
                    "name": "准备阶段",
                    "description": "准备执行所需的基础信息和资源",
                    "input": "任务描述和要求",
                    "output": "准备就绪状态",
                    "estimated_time": 2,
                    "tools": [],
                    "validation": "检查准备是否完整"
                },
                {
                    "step_id": "step_2",
                    "name": "核心执行",
                    "description": "执行任务的核心逻辑",
                    "input": "准备阶段的输出",
                    "output": "核心执行结果",
                    "estimated_time": 5,
                    "tools": ["llm"],
                    "validation": "检查结果质量"
                },
                {
                    "step_id": "step_3",
                    "name": "结果整理",
                    "description": "整理和格式化执行结果",
                    "input": "核心执行结果",
                    "output": "最终输出",
                    "estimated_time": 1,
                    "tools": [],
                    "validation": "检查格式和完整性"
                }
            ]
        
        return steps
    
    async def _execute_steps(self, steps: List[Dict[str, Any]], task: Dict[str, Any]) -> List[Dict[str, Any]]:
        """执行步骤"""
        results = []
        context = {"task": task}
        
        for step in steps:
            try:
                self.logger.info(f"执行步骤: {step['name']}")
                
                # 执行单个步骤
                step_result = await self._execute_single_step(step, context)
                results.append(step_result)
                
                # 更新上下文
                context[f"step_{step['step_id']}_result"] = step_result
                
                # 验证步骤结果
                if not self._validate_step_result(step, step_result):
                    self.logger.warning(f"步骤 {step['name']} 验证失败")
                
            except Exception as e:
                self.logger.error(f"步骤 {step['name']} 执行失败: {e}")
                results.append({
                    "step_id": step["step_id"],
                    "name": step["name"],
                    "status": "failed",
                    "error": str(e),
                    "output": None
                })
        
        return results
    
    async def _execute_single_step(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个步骤"""
        prompt = f"""
请执行以下步骤：

步骤信息:
- 名称: {step['name']}
- 描述: {step['description']}
- 输入要求: {step['input']}
- 预期输出: {step['output']}

上下文信息:
{json.dumps(context, ensure_ascii=False, indent=2)}

请按照步骤要求执行操作，并输出结果。
"""
        
        try:
            response = await self.think(prompt, context)
            
            return {
                "step_id": step["step_id"],
                "name": step["name"],
                "status": "completed",
                "output": response,
                "execution_time": datetime.now().isoformat(),
                "error": None
            }
            
        except Exception as e:
            return {
                "step_id": step["step_id"],
                "name": step["name"],
                "status": "failed",
                "output": None,
                "execution_time": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _validate_step_result(self, step: Dict[str, Any], result: Dict[str, Any]) -> bool:
        """验证步骤结果"""
        if result["status"] != "completed":
            return False
        
        if not result["output"]:
            return False
        
        # 这里可以添加更复杂的验证逻辑
        return True
    
    async def _generate_final_result(self, step_results: List[Dict[str, Any]], task: Dict[str, Any]) -> Dict[str, Any]:
        """生成最终结果"""
        prompt = f"""
基于以下步骤执行结果，生成最终的任务输出：

原始任务: {json.dumps(task, ensure_ascii=False, indent=2)}

步骤执行结果:
{json.dumps(step_results, ensure_ascii=False, indent=2)}

请整合所有步骤的结果，生成符合任务要求的最终输出。
确保输出格式符合预期输出要求: {task.get('expected_output', 'N/A')}
"""
        
        try:
            final_output = await self.think(prompt)
            
            return {
                "content": final_output,
                "format": "text",
                "generated_at": datetime.now().isoformat(),
                "step_count": len(step_results),
                "successful_steps": len([r for r in step_results if r["status"] == "completed"])
            }
            
        except Exception as e:
            self.logger.error(f"生成最终结果失败: {e}")
            return {
                "content": f"执行过程中出现错误: {str(e)}",
                "format": "text",
                "generated_at": datetime.now().isoformat(),
                "step_count": len(step_results),
                "successful_steps": 0,
                "error": str(e)
            }
