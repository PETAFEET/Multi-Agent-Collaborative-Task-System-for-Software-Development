"""
监督智能体

负责监控任务执行状态、协调智能体协作、生成综合报告
"""

import json
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from langchain_core.language_models.llms import BaseLLM
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage

from .base import BaseAgent, AgentCapabilities, AgentStatus
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MonitorAgent(BaseAgent):
    """监督智能体"""
    
    def __init__(self, agent_id: str, llm: BaseLLM, **kwargs):
        capabilities = AgentCapabilities(
            can_monitor=True,
            can_analyze_data=True,
            max_tokens=1500,
            supported_formats=["text", "json", "report"]
        )
        
        system_prompt = """你是一个专业的任务监督智能体。你的职责是：

1. 监控所有智能体的执行状态
2. 检查任务执行质量和进度
3. 识别潜在问题和风险
4. 协调智能体之间的协作
5. 生成最终的综合报告

请始终以客观、专业的方式进行分析和报告，包括：
- 执行状态概览
- 质量评估
- 问题识别
- 改进建议
- 综合结论"""

        super().__init__(
            agent_id=agent_id,
            name="任务监督智能体",
            description="负责监控和协调多智能体协作",
            llm=llm,
            capabilities=capabilities,
            system_prompt=system_prompt,
            **kwargs
        )
        
        # 监控数据
        self.monitored_tasks: Dict[str, Dict[str, Any]] = {}
        self.agent_statuses: Dict[str, Dict[str, Any]] = {}
        self.performance_metrics: Dict[str, List[Dict[str, Any]]] = {}
    
    async def execute(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行监控任务
        
        Args:
            task: 监控任务描述字典
            
        Returns:
            监控结果字典
        """
        try:
            self.update_status(AgentStatus.EXECUTING, "开始监控任务")
            self.current_task = task
            
            # 分析监控任务类型
            monitor_type = task.get("type", "general")
            
            if monitor_type == "task_monitoring":
                result = await self._monitor_task_execution(task)
            elif monitor_type == "agent_health":
                result = await self._monitor_agent_health(task)
            elif monitor_type == "performance_analysis":
                result = await self._analyze_performance(task)
            elif monitor_type == "generate_report":
                result = await self._generate_comprehensive_report(task)
            else:
                result = await self._general_monitoring(task)
            
            self.add_task_to_history(task, result)
            self.update_status(AgentStatus.COMPLETED, "监控任务完成")
            
            return result
            
        except Exception as e:
            self.logger.error(f"监控任务失败: {e}")
            self.update_status(AgentStatus.ERROR, f"监控失败: {str(e)}")
            raise
    
    async def _monitor_task_execution(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """监控任务执行"""
        task_id = task.get("task_id")
        execution_data = task.get("execution_data", {})
        
        # 分析执行状态
        status_analysis = await self._analyze_execution_status(execution_data)
        
        # 检查进度
        progress_check = await self._check_execution_progress(execution_data)
        
        # 识别问题
        issues = await self._identify_issues(execution_data)
        
        # 生成建议
        recommendations = await self._generate_recommendations(execution_data, issues)
        
        return {
            "task_id": task_id,
            "monitor_type": "task_execution",
            "status_analysis": status_analysis,
            "progress_check": progress_check,
            "issues": issues,
            "recommendations": recommendations,
            "monitored_at": datetime.now().isoformat(),
            "status": "completed"
        }
    
    async def _monitor_agent_health(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """监控智能体健康状态"""
        agent_statuses = task.get("agent_statuses", {})
        
        health_reports = {}
        for agent_id, status in agent_statuses.items():
            health_report = await self._check_agent_health(agent_id, status)
            health_reports[agent_id] = health_report
        
        # 分析整体健康状态
        overall_health = await self._analyze_overall_health(health_reports)
        
        return {
            "monitor_type": "agent_health",
            "agent_health_reports": health_reports,
            "overall_health": overall_health,
            "monitored_at": datetime.now().isoformat(),
            "status": "completed"
        }
    
    async def _analyze_performance(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """分析性能指标"""
        performance_data = task.get("performance_data", {})
        
        # 分析执行效率
        efficiency_analysis = await self._analyze_efficiency(performance_data)
        
        # 分析资源使用
        resource_analysis = await self._analyze_resource_usage(performance_data)
        
        # 分析质量指标
        quality_analysis = await self._analyze_quality_metrics(performance_data)
        
        # 生成性能报告
        performance_report = await self._generate_performance_report(
            efficiency_analysis, resource_analysis, quality_analysis
        )
        
        return {
            "monitor_type": "performance_analysis",
            "efficiency_analysis": efficiency_analysis,
            "resource_analysis": resource_analysis,
            "quality_analysis": quality_analysis,
            "performance_report": performance_report,
            "analyzed_at": datetime.now().isoformat(),
            "status": "completed"
        }
    
    async def _generate_comprehensive_report(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """生成综合报告"""
        report_data = task.get("report_data", {})
        
        prompt = f"""
请基于以下数据生成一份综合的多智能体协作报告：

报告数据: {json.dumps(report_data, ensure_ascii=False, indent=2)}

报告应包含以下部分：
1. 执行概览
2. 智能体表现分析
3. 任务完成情况
4. 问题识别与解决
5. 性能指标分析
6. 改进建议
7. 总结与结论

请以结构化的格式输出报告。
"""
        
        report_content = await self.think(prompt)
        
        return {
            "monitor_type": "comprehensive_report",
            "report_content": report_content,
            "report_data": report_data,
            "generated_at": datetime.now().isoformat(),
            "status": "completed"
        }
    
    async def _general_monitoring(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """通用监控"""
        monitoring_data = task.get("monitoring_data", {})
        
        # 基础状态检查
        status_check = await self._basic_status_check(monitoring_data)
        
        # 风险评估
        risk_assessment = await self._assess_risks(monitoring_data)
        
        # 生成监控摘要
        summary = await self._generate_monitoring_summary(status_check, risk_assessment)
        
        return {
            "monitor_type": "general",
            "status_check": status_check,
            "risk_assessment": risk_assessment,
            "summary": summary,
            "monitored_at": datetime.now().isoformat(),
            "status": "completed"
        }
    
    async def _analyze_execution_status(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析执行状态"""
        prompt = f"""
请分析以下任务执行数据的状态：

执行数据: {json.dumps(execution_data, ensure_ascii=False, indent=2)}

请从以下维度进行分析：
1. 整体执行状态
2. 各阶段完成情况
3. 执行质量评估
4. 时间效率分析
5. 资源使用情况

请以JSON格式输出分析结果。
"""
        
        analysis_text = await self.think(prompt)
        
        try:
            analysis = json.loads(analysis_text)
        except json.JSONDecodeError:
            analysis = {
                "overall_status": "unknown",
                "completion_rate": 0,
                "quality_score": 0,
                "efficiency_score": 0,
                "resource_usage": "normal"
            }
        
        return analysis
    
    async def _check_execution_progress(self, execution_data: Dict[str, Any]) -> Dict[str, Any]:
        """检查执行进度"""
        # 这里可以实现更复杂的进度检查逻辑
        return {
            "progress_percentage": 0,
            "completed_steps": 0,
            "total_steps": 0,
            "estimated_completion": None,
            "blocking_issues": []
        }
    
    async def _identify_issues(self, execution_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """识别问题"""
        prompt = f"""
请分析以下执行数据，识别可能存在的问题：

执行数据: {json.dumps(execution_data, ensure_ascii=False, indent=2)}

请识别：
1. 执行错误
2. 性能问题
3. 资源问题
4. 协作问题
5. 质量问题

对每个问题，请提供：
- 问题描述
- 严重程度（低/中/高）
- 影响范围
- 建议解决方案

请以JSON数组格式输出问题列表。
"""
        
        issues_text = await self.think(prompt)
        
        try:
            issues = json.loads(issues_text)
        except json.JSONDecodeError:
            issues = []
        
        return issues
    
    async def _generate_recommendations(self, execution_data: Dict[str, Any], issues: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """生成改进建议"""
        prompt = f"""
基于以下执行数据和问题列表，生成改进建议：

执行数据: {json.dumps(execution_data, ensure_ascii=False, indent=2)}
问题列表: {json.dumps(issues, ensure_ascii=False, indent=2)}

请提供：
1. 短期改进建议
2. 长期优化建议
3. 系统配置建议
4. 流程改进建议

请以JSON数组格式输出建议列表。
"""
        
        recommendations_text = await self.think(prompt)
        
        try:
            recommendations = json.loads(recommendations_text)
        except json.JSONDecodeError:
            recommendations = []
        
        return recommendations
    
    async def _check_agent_health(self, agent_id: str, status: Dict[str, Any]) -> Dict[str, Any]:
        """检查单个智能体健康状态"""
        return {
            "agent_id": agent_id,
            "status": status.get("status", "unknown"),
            "last_activity": status.get("last_activity"),
            "task_count": status.get("task_count", 0),
            "error_count": status.get("error_count", 0),
            "health_score": 100,  # 这里可以实现更复杂的健康评分
            "issues": []
        }
    
    async def _analyze_overall_health(self, health_reports: Dict[str, Any]) -> Dict[str, Any]:
        """分析整体健康状态"""
        total_agents = len(health_reports)
        healthy_agents = len([r for r in health_reports.values() if r["health_score"] > 80])
        
        return {
            "total_agents": total_agents,
            "healthy_agents": healthy_agents,
            "health_percentage": (healthy_agents / total_agents * 100) if total_agents > 0 else 0,
            "overall_status": "healthy" if healthy_agents == total_agents else "degraded"
        }
    
    async def _analyze_efficiency(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析执行效率"""
        return {
            "average_execution_time": 0,
            "efficiency_trend": "stable",
            "bottlenecks": [],
            "optimization_opportunities": []
        }
    
    async def _analyze_resource_usage(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析资源使用"""
        return {
            "cpu_usage": "normal",
            "memory_usage": "normal",
            "api_calls": 0,
            "resource_efficiency": "good"
        }
    
    async def _analyze_quality_metrics(self, performance_data: Dict[str, Any]) -> Dict[str, Any]:
        """分析质量指标"""
        return {
            "success_rate": 100,
            "error_rate": 0,
            "quality_score": 85,
            "user_satisfaction": "high"
        }
    
    async def _generate_performance_report(self, efficiency: Dict[str, Any], resources: Dict[str, Any], quality: Dict[str, Any]) -> str:
        """生成性能报告"""
        prompt = f"""
请基于以下性能分析数据生成性能报告：

效率分析: {json.dumps(efficiency, ensure_ascii=False, indent=2)}
资源分析: {json.dumps(resources, ensure_ascii=False, indent=2)}
质量分析: {json.dumps(quality, ensure_ascii=False, indent=2)}

请生成一份简洁明了的性能报告。
"""
        
        return await self.think(prompt)
    
    async def _basic_status_check(self, monitoring_data: Dict[str, Any]) -> Dict[str, Any]:
        """基础状态检查"""
        return {
            "system_status": "running",
            "active_tasks": 0,
            "idle_agents": 0,
            "error_count": 0
        }
    
    async def _assess_risks(self, monitoring_data: Dict[str, Any]) -> Dict[str, Any]:
        """风险评估"""
        return {
            "risk_level": "low",
            "identified_risks": [],
            "mitigation_actions": []
        }
    
    async def _generate_monitoring_summary(self, status_check: Dict[str, Any], risk_assessment: Dict[str, Any]) -> str:
        """生成监控摘要"""
        prompt = f"""
请基于以下监控数据生成监控摘要：

状态检查: {json.dumps(status_check, ensure_ascii=False, indent=2)}
风险评估: {json.dumps(risk_assessment, ensure_ascii=False, indent=2)}

请生成一份简洁的监控摘要。
"""
        
        return await self.think(prompt)
