"""
研究报告示例

演示如何使用多智能体系统进行研究报告撰写
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
        logger.info("开始研究报告示例")
        
        # 加载配置
        config = Config()
        
        # 创建协调器
        coordinator = MultiAgentCoordinator(config)
        await coordinator.initialize()
        
        # 创建研究报告任务
        task_data = {
            "type": "research_report",
            "description": "撰写一份关于人工智能在医疗领域应用的研究报告",
            "requirements": {
                "title": "人工智能在医疗领域的应用现状与前景分析",
                "research_scope": "医疗AI",
                "report_length": "5000-8000字",
                "sections": [
                    "摘要",
                    "引言",
                    "文献综述",
                    "技术分析",
                    "应用案例",
                    "挑战与机遇",
                    "结论与建议"
                ],
                "requirements": [
                    "学术严谨性",
                    "数据支撑",
                    "案例分析",
                    "图表说明",
                    "参考文献",
                    "未来展望"
                ],
                "target_audience": "医疗行业从业者、研究人员、政策制定者",
                "citation_style": "APA",
                "language": "中文"
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
            logger.info("研究报告结果:")
            logger.info("=" * 50)
            
            # 打印结果摘要
            if 'final_output' in result:
                print("\n" + "=" * 50)
                print("最终研究报告:")
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
