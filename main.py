"""
多智能体协作系统主程序

启动Web服务器和后台任务处理
"""

import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logging, get_logger
from src.web.app import app

# 设置日志
setup_logging(level="INFO")
logger = get_logger(__name__)


def main():
    """主函数"""
    try:
        logger.info("启动多智能体协作系统...")
        
        # 检查配置文件
        config_file = project_root / "config.yaml"
        if not config_file.exists():
            logger.error(f"配置文件不存在: {config_file}")
            logger.info("请先创建配置文件 config.yaml")
            return
        
        # 启动Web服务器
        import uvicorn
        
        logger.info("启动Web服务器...")
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=5000,
            log_level="info",
            access_log=True
        )
        
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在关闭系统...")
    except Exception as e:
        logger.error(f"系统启动失败: {e}")
        raise


if __name__ == "__main__":
    main()
