"""
智能体测试

测试各种智能体的功能
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock

from src.agents import PlannerAgent, ExecutorAgent, MonitorAgent, BrowserAgent
from src.utils.logger import setup_logging

# 设置测试日志
setup_logging(level="DEBUG")


class TestPlannerAgent:
    """规划智能体测试"""
    
    @pytest.fixture
    def mock_llm(self):
        """模拟LLM"""
        llm = Mock()
        llm.ainvoke = AsyncMock(return_value=Mock(content="测试回复"))
        return llm
    
    @pytest.fixture
    def planner_agent(self, mock_llm):
        """创建规划智能体实例"""
        return PlannerAgent(
            agent_id="test_planner",
            llm=mock_llm
        )
    
    @pytest.mark.asyncio
    async def test_planner_execute(self, planner_agent):
        """测试规划智能体执行"""
        task = {
            "type": "travel_planning",
            "description": "规划一次旅行",
            "requirements": {"destination": "东京"}
        }
        
        result = await planner_agent.execute(task)
        
        assert result is not None
        assert "task_id" in result
        assert "subtasks" in result
        assert "agent_assignments" in result
        assert "execution_plan" in result
    
    @pytest.mark.asyncio
    async def test_planner_think(self, planner_agent):
        """测试规划智能体思考"""
        response = await planner_agent.think("测试提示")
        
        assert response is not None
        assert isinstance(response, str)
    
    def test_planner_status_info(self, planner_agent):
        """测试规划智能体状态信息"""
        status_info = planner_agent.get_status_info()
        
        assert "agent_id" in status_info
        assert "name" in status_info
        assert "status" in status_info
        assert status_info["agent_id"] == "test_planner"


class TestExecutorAgent:
    """执行智能体测试"""
    
    @pytest.fixture
    def mock_llm(self):
        """模拟LLM"""
        llm = Mock()
        llm.ainvoke = AsyncMock(return_value=Mock(content="测试回复"))
        return llm
    
    @pytest.fixture
    def executor_agent(self, mock_llm):
        """创建执行智能体实例"""
        return ExecutorAgent(
            agent_id="test_executor",
            llm=mock_llm
        )
    
    @pytest.mark.asyncio
    async def test_executor_execute(self, executor_agent):
        """测试执行智能体执行"""
        task = {
            "id": "test_task",
            "name": "测试任务",
            "description": "执行测试任务",
            "input_requirements": "输入要求",
            "expected_output": "预期输出"
        }
        
        result = await executor_agent.execute(task)
        
        assert result is not None
        assert "task_id" in result
        assert "final_result" in result
        assert result["success"] is True
    
    @pytest.mark.asyncio
    async def test_executor_health_check(self, executor_agent):
        """测试执行智能体健康检查"""
        health = await executor_agent.health_check()
        
        assert isinstance(health, bool)


class TestMonitorAgent:
    """监督智能体测试"""
    
    @pytest.fixture
    def mock_llm(self):
        """模拟LLM"""
        llm = Mock()
        llm.ainvoke = AsyncMock(return_value=Mock(content="测试回复"))
        return llm
    
    @pytest.fixture
    def monitor_agent(self, mock_llm):
        """创建监督智能体实例"""
        return MonitorAgent(
            agent_id="test_monitor",
            llm=mock_llm
        )
    
    @pytest.mark.asyncio
    async def test_monitor_execute(self, monitor_agent):
        """测试监督智能体执行"""
        task = {
            "type": "task_monitoring",
            "task_id": "test_task",
            "execution_data": {
                "subtasks": [],
                "execution_results": []
            }
        }
        
        result = await monitor_agent.execute(task)
        
        assert result is not None
        assert "task_id" in result
        assert "monitor_type" in result


class TestBrowserAgent:
    """浏览器智能体测试"""
    
    @pytest.fixture
    def mock_llm(self):
        """模拟LLM"""
        llm = Mock()
        llm.ainvoke = AsyncMock(return_value=Mock(content="测试回复"))
        return llm
    
    @pytest.fixture
    def browser_agent(self, mock_llm):
        """创建浏览器智能体实例"""
        return BrowserAgent(
            agent_id="test_browser",
            llm=mock_llm
        )
    
    @pytest.mark.asyncio
    async def test_browser_execute(self, browser_agent):
        """测试浏览器智能体执行"""
        task = {
            "id": "test_browser_task",
            "name": "浏览器测试任务",
            "description": "执行浏览器操作",
            "target_url": "https://example.com",
            "operation_type": "navigate"
        }
        
        result = await browser_agent.execute(task)
        
        assert result is not None
        assert "task_id" in result
        assert "final_result" in result


if __name__ == "__main__":
    pytest.main([__file__])
