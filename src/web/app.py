"""
FastAPI Web应用

提供多智能体系统的Web界面和API
"""

import asyncio
import json
from typing import Dict, List, Any, Optional
from datetime import datetime

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from ..core.coordinator import MultiAgentCoordinator
from ..core.task_manager import TaskManager, TaskPriority
from ..core.communication import CommunicationManager
from ..utils.config import Config
from ..utils.logger import get_logger

logger = get_logger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="多智能体协作系统",
    description="基于LangChain的多智能体协作任务系统",
    version="1.0.0"
)

# 全局变量
coordinator: Optional[MultiAgentCoordinator] = None
task_manager: Optional[TaskManager] = None
communication_manager: Optional[CommunicationManager] = None
config: Optional[Config] = None

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket连接建立，当前连接数: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(f"WebSocket连接断开，当前连接数: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except:
                self.disconnect(connection)

manager = ConnectionManager()

# Pydantic模型
class TaskRequest(BaseModel):
    type: str
    description: str
    requirements: Optional[Dict[str, Any]] = {}
    priority: Optional[str] = "normal"

class TaskResponse(BaseModel):
    task_id: str
    status: str
    message: str

class AgentStatus(BaseModel):
    agent_id: str
    name: str
    status: str
    current_task: Optional[str]
    task_count: int

# 启动事件
@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    global coordinator, task_manager, communication_manager, config
    
    try:
        logger.info("正在初始化多智能体系统...")
        
        # 加载配置
        config = Config()
        if not config.validate():
            raise ValueError("配置验证失败")
        
        # 初始化通信管理器
        communication_manager = CommunicationManager()
        await communication_manager.start()
        
        # 初始化任务管理器
        task_manager = TaskManager()
        await task_manager.start()
        
        # 初始化协调器
        coordinator = MultiAgentCoordinator(config)
        await coordinator.initialize()
        
        logger.info("多智能体系统初始化完成")
        
    except Exception as e:
        logger.error(f"系统初始化失败: {e}")
        raise

# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时清理"""
    global coordinator, task_manager, communication_manager
    
    try:
        logger.info("正在关闭多智能体系统...")
        
        if coordinator:
            await coordinator.shutdown()
        
        if task_manager:
            await task_manager.stop()
        
        if communication_manager:
            await communication_manager.stop()
        
        logger.info("多智能体系统已关闭")
        
    except Exception as e:
        logger.error(f"系统关闭时出错: {e}")

# 静态文件和模板
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")
templates = Jinja2Templates(directory="src/web/templates")

# 路由
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """主页"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/tasks", response_model=TaskResponse)
async def create_task(task_request: TaskRequest):
    """创建新任务"""
    try:
        if not coordinator:
            raise HTTPException(status_code=500, detail="系统未初始化")
        
        # 转换优先级
        priority_map = {
            "low": TaskPriority.LOW,
            "normal": TaskPriority.NORMAL,
            "high": TaskPriority.HIGH,
            "urgent": TaskPriority.URGENT
        }
        priority = priority_map.get(task_request.priority, TaskPriority.NORMAL)
        
        # 创建任务
        task_id = await coordinator.submit_task({
            "type": task_request.type,
            "description": task_request.description,
            "requirements": task_request.requirements
        })
        
        # 广播任务创建消息
        await manager.broadcast({
            "type": "task_created",
            "task_id": task_id,
            "task_type": task_request.type,
            "description": task_request.description
        })
        
        return TaskResponse(
            task_id=task_id,
            status="created",
            message="任务创建成功"
        )
        
    except Exception as e:
        logger.error(f"创建任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """获取任务信息"""
    try:
        if not coordinator:
            raise HTTPException(status_code=500, detail="系统未初始化")
        
        task_status = await coordinator.get_task_status(task_id)
        if not task_status:
            raise HTTPException(status_code=404, detail="任务不存在")
        
        return task_status
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks/{task_id}/result")
async def get_task_result(task_id: str):
    """获取任务结果"""
    try:
        if not coordinator:
            raise HTTPException(status_code=500, detail="系统未初始化")
        
        result = await coordinator.get_task_result(task_id)
        if not result:
            raise HTTPException(status_code=404, detail="任务结果不存在")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取任务结果失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/agents", response_model=List[AgentStatus])
async def get_agents():
    """获取智能体状态"""
    try:
        if not coordinator:
            raise HTTPException(status_code=500, detail="系统未初始化")
        
        agent_status = await coordinator.get_agent_status()
        
        agents = []
        for agent_id, status in agent_status.items():
            # 修正 current_task 字段类型，确保为字符串
            current_task = status["current_task"]
            if isinstance(current_task, dict):
                current_task = current_task.get("id", str(current_task))
            agents.append(AgentStatus(
                agent_id=agent_id,
                name=status["name"],
                status=status["status"],
                current_task=current_task,
                task_count=status["task_count"]
            ))
        
        return agents
        
    except Exception as e:
        logger.error(f"获取智能体状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/tasks")
async def list_tasks(limit: int = 50, status: Optional[str] = None):
    """获取任务列表"""
    try:
        if not task_manager:
            raise HTTPException(status_code=500, detail="任务管理器未初始化")
        
        # 这里应该从任务管理器获取任务列表
        # 为了简化，返回空列表
        return []
        
    except Exception as e:
        logger.error(f"获取任务列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket连接"""
    await manager.connect(websocket)
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # 处理不同类型的消息
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
            elif message.get("type") == "subscribe":
                # 处理订阅请求
                pass
            
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket错误: {e}")
        manager.disconnect(websocket)

# 健康检查
@app.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "coordinator_initialized": coordinator is not None,
        "task_manager_initialized": task_manager is not None,
        "communication_manager_initialized": communication_manager is not None
    }

# 系统信息
@app.get("/api/system/info")
async def get_system_info():
    """获取系统信息"""
    return {
        "name": "多智能体协作系统",
        "version": "1.0.0",
        "description": "基于LangChain的多智能体协作任务系统",
        "features": [
            "多智能体协作",
            "任务自动分解",
            "实时监控",
            "Web界面",
            "MCP集成",
            "浏览器操作"
        ],
        "supported_task_types": [
            "travel_planning",
            "code_development", 
            "research_report",
            "general"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
