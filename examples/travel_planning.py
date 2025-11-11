"""
旅行规划示例

演示如何使用多智能体系统进行旅行规划
"""

import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.coordinator import MultiAgentCoordinator
from src.utils.config import Config
from src.utils.logger import setup_logging, get_logger

# 设置日志
setup_logging(level="INFO")
logger = get_logger(__name__)


async def main():
    """主函数"""
    try:
        logger.info("开始旅行规划示例")
        
        # 加载配置
        config = Config()
        
        # 创建协调器
        coordinator = MultiAgentCoordinator(config)
        await coordinator.initialize()
        
        # 创建旅行规划任务
        task_data = {
            "type": "travel_planning",
            "description": "规划一次7天的日本东京之旅，包括景点、美食、住宿和交通安排",
            "requirements": {
                "destination": "东京, 日本",
                "duration": "7天",
                "budget": 15000,
                "interests": ["文化", "美食", "购物", "历史"],
                "travel_style": "舒适型",
                "group_size": 2,
                "preferred_accommodation": "酒店",
                "dietary_requirements": "无特殊要求",
                "language_preference": "中文"
            }
        }
        
        logger.info(f"提交任务: {task_data['description']}")
        
        # 提交任务
        task_id = await coordinator.submit_task(task_data)
        logger.info(f"任务已提交，ID: {task_id}")
        
        # 监控任务执行
        while True:
            status = await coordinator.get_task_status(task_id)
            if not status:
                logger.error("无法获取任务状态")
                break
            
            logger.info(f"任务状态: {status['status']}")
            
            if status['status'] in ['completed', 'failed']:
                break
            
            await asyncio.sleep(5)
        
        # 获取最终结果
        if status['status'] == 'completed':
            result = await coordinator.get_task_result(task_id)
            logger.info("任务执行完成！")
            logger.info("=" * 50)
            logger.info("旅行规划结果:")
            logger.info("=" * 50)
            
            # 打印结果摘要
            if 'final_output' in result:
                print("\n" + "=" * 50)
                print("最终旅行规划:")
                print("=" * 50)
                print(result['final_output'])
                print("=" * 50)
            
            # 打印执行摘要
            if 'execution_summary' in result:
                summary = result['execution_summary']
                print(f"\n执行摘要:")
                print(f"- 总子任务数: {summary.get('total_subtasks', 0)}")
                print(f"- 完成子任务数: {summary.get('completed_subtasks', 0)}")
                print(f"- 执行时间: {summary.get('execution_time', 0):.2f}秒")
                print(f"- 分配的智能体: {', '.join(summary.get('assigned_agents', []))}")
        else:
            logger.error(f"任务执行失败: {status.get('error', '未知错误')}")
        
        # 关闭协调器
        await coordinator.shutdown()
        
    except Exception as e:
        logger.error(f"示例执行失败: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
