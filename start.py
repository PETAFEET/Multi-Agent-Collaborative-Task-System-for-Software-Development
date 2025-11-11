"""
启动脚本

提供多种启动方式
"""

import asyncio
import sys
import os
import argparse
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.utils.logger import setup_logging, get_logger
from src.utils.config import Config

# 设置日志
setup_logging(level="INFO")
logger = get_logger(__name__)


def start_web_server(host="0.0.0.0", port=5000, debug=False):
    """启动Web服务器"""
    try:
        logger.info("启动Web服务器...")
        
        import uvicorn
        from src.web.app import app
        
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="debug" if debug else "info",
            access_log=True,
            reload=debug
        )
        
    except Exception as e:
        logger.error(f"Web服务器启动失败: {e}")
        raise


def start_background_worker():
    """启动后台工作进程"""
    try:
        logger.info("启动后台工作进程...")
        
        from src.core.background_executor import BackgroundExecutor
        
        async def main():
            executor = BackgroundExecutor()
            await executor.start()
            
            try:
                # 保持运行
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                logger.info("收到中断信号，正在停止...")
            finally:
                await executor.stop()
        
        asyncio.run(main())
        
    except Exception as e:
        logger.error(f"后台工作进程启动失败: {e}")
        raise


def run_example(example_name):
    """运行示例"""
    try:
        logger.info(f"运行示例: {example_name}")
        
        if example_name == "travel":
            from examples.travel_planning import main
        elif example_name == "code":
            from examples.code_development import main
        elif example_name == "research":
            from examples.research_report import main
        else:
            logger.error(f"未知的示例: {example_name}")
            return
        
        asyncio.run(main())
        
    except Exception as e:
        logger.error(f"运行示例失败: {e}")
        raise


def check_config():
    """检查配置"""
    try:
        logger.info("检查配置...")
        
        config = Config()
        
        if not config.validate():
            logger.error("配置验证失败")
            return False
        
        logger.info("配置检查通过")
        return True
        
    except Exception as e:
        logger.error(f"配置检查失败: {e}")
        return False


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="多智能体协作系统启动脚本")
    parser.add_argument(
        "command",
        choices=["web", "worker", "example", "check"],
        help="启动命令"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Web服务器主机地址"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5000,
        help="Web服务器端口"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    parser.add_argument(
        "--example",
        choices=["travel", "code", "research"],
        help="要运行的示例"
    )
    
    args = parser.parse_args()
    
    try:
        if args.command == "web":
            start_web_server(args.host, args.port, args.debug)
        elif args.command == "worker":
            start_background_worker()
        elif args.command == "example":
            if not args.example:
                logger.error("请指定要运行的示例")
                return
            run_example(args.example)
        elif args.command == "check":
            if not check_config():
                sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("收到中断信号，正在退出...")
    except Exception as e:
        logger.error(f"启动失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
