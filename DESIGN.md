# 多智能体系统 (MAS) 设计文档

目标：在当前基于 FastAPI 的模板项目上实现一个可扩展、可观测、多进程/分布式的多智能体系统（MAS）。

本文档面向开发者与架构师，包含架构概览、组件职责、接口定义、消息 schema、数据库模型、工作流、错误处理、测试与部署建议，以及 MVP 验收条件。

---

## 1. 概要

-   目标：使用已有基础设施（RabbitMQ、Redis、Postgres、TaskIQ worker）实现 agent 的注册、调度、异步执行与互通。
-   首个交付（MVP）：实现一个 Echo Agent，验证消息传递、TaskIQ worker 调度、持久化与监控链路。

非功能性要求：可扩展性、容错性、可观测性与 API 认证（项目已有 fastapi-users 支持）。

---

## 2. 总体架构（文字描述）

-   FastAPI（API 网关）：管理 agent、提交任务、查询状态。
-   Orchestrator / Scheduler：任务拆分、路由、重试与调度策略（可作为 FastAPI 内部模块或独立服务）。
-   Messaging（RabbitMQ）：Agent-to-Agent 及 Orchestrator-to-Agent 的消息传输。
-   Worker（TaskIQ）：承载 agent 的执行逻辑，运行 agent 的 `handle_message`。
-   Redis：缓存、分布式锁、短期状态。
-   Postgres：持久化 agent 注册信息、任务/消息历史与审计日志。
-   监控/日志：Prometheus metrics + structured logs（trace_id 链路追踪）。

请求流程（简化）：HTTP 请求 -> Orchestrator -> publish Message -> RabbitMQ -> TaskIQ worker -> Agent.handle_message -> publish 或写 DB -> API 查询

---

## 3. 组件与目录建议

建议在 `multi_agent/` 下新增模块：

-   `agents/`：Agent 抽象与实现（`base.py`, `echo.py`, `planner.py`, ...）。
-   `messaging/`：AMQP helper、消息（`schemas.py`）。
-   `orchestrator/`：`scheduler.py`, `registry.py`。
-   `services/`：复用现有 rabbit/redis lifespans 与 DI。
-   `db/models/`：新增 `agents`, `tasks`, `messages` 表。
-   `tests/`：unit 与 integration tests。

---

## 4. Agent 抽象契约

建议在 `agents/base.py` 定义接口：

-   class Agent:
    -   `id`, `type`（字符串）
    -   `async def handle_message(self, message: Message) -> Optional[Union[Message, TaskResult, List[Message]]]`
    -   `async def start(self)`, `async def stop(self)`（可选，用于常驻 agent）。

设计要点：

-   `handle_message` 输入/输出使用 pydantic `Message`。
-   尽量短时间返回；长任务应拆分为 TaskIQ 子任务。
-   错误以标准化结构/异常上报，Orchestrator 根据策略处理。

边界情况需考虑：消息重复（幂等）、超时/重试、并发锁冲突、状态恢复。

---

## 5. 消息 Schema（示例）

在 `messaging/schemas.py` 使用 pydantic：

```python
from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from datetime import datetime
import uuid

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: str
    sender: Optional[str] = None
    target: Optional[str] = None
    payload: Dict[str, Any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = {}
    trace_id: Optional[str] = None

```

说明：`type` 决定路由；`trace_id` 用于分布式追踪；`id` 保证幂等处理。

---

## 6. RabbitMQ 交换与队列设计

-   Exchanges:
    -   `agents.direct`（direct）：点对点路由（routing key = agent_id 或 agent_type）
    -   `agents.topic`（topic）：事件广播
-   Queues:
    -   `agent.<agent_id>` 或 `agent_type.<type>`（持久队列）
-   Routing keys:
    -   `agent.<id>` 或 `type.<agent_type>`

使用持久队列与显式 ack，失败时根据策略重试或转入 dead-letter。

---

## 7. 数据模型（建议 SQLAlchemy 表）

-   `agents` 表：id UUID PK, type, status, last_heartbeat, metadata JSONB, created_at
-   `tasks` 表：id UUID PK, type, status, payload JSONB, result JSONB, created_by, created_at, finished_at
-   `messages` 表（可选）：id, msg_type, sender, target, payload JSONB, trace_id, created_at

目标是支持审计与重放；messages 表可按需要打开以便调试。

---

## 8. Orchestrator / Scheduler（职责）

-   接收外部任务并决定路由：单 agent 或多 agent workflow
-   拆分任务、调度到相应队列
-   管理重试/超时/回退策略
-   维护 agent registry（根据 heartbeat 更新）

策略示例：优先按 capability 路由 -> 没实例则按 type 路由 -> 重试使用指数回退

---

## 9. API 设计（建议路由）

-   POST `/agents/` - 注册 agent（测试用）
-   GET `/agents/` - 列表 agent
-   GET `/agents/{id}` - agent 详情
-   POST `/tasks/` - 提交任务（body: Message 或 TaskSpec）
-   GET `/tasks/{task_id}` - 查询任务
-   POST `/agents/{id}/message` - 向 agent 发送 message（调试）

使用 JWT 保护敏感路由（项目已有 fastapi-users）。

---

## 10. TaskIQ 与 worker 集成

-   在线程/进程中运行 TaskIQ worker，注册任务函数 `run_agent_message(message_json)`：
    -   反序列化 Message
    -   查找 Agent class/instance 并调用 `handle_message`
    -   持久化结果或 publish 返回消息

确保 worker 容器不意外映射 HTTP 端口（compose 已修复）。

---

## 11. 错误处理与幂等性

-   使用 `message.id` 或 `trace_id` 做幂等控制（DB/Redis 去重索引）。
-   对暂时性错误使用重试；对不可恢复错误标为 failed 并上报告警。
-   记录详细错误到 `tasks` 表及日志。

---

## 12. 监控与日志

-   日志：结构化 JSON，包含 message_id, task_id, agent_id, trace_id, duration, status
-   Prometheus 指标：agent_tasks_processed_total, agent_task_duration_seconds, agent_tasks_in_queue
-   建议引入 OpenTelemetry 或在日志中使用 `trace_id` 以便串联调用

---

## 13. 测试计划

-   单元测试：Agent 逻辑、消息序列化
-   集成测试：使用 docker-compose 启动 RabbitMQ/Redis/Postgres + worker；通过 API 提交任务并断言结果
-   CI：在 GitHub Actions 中运行 docker-compose 或使用 services（rabbitmq/postgres/redis）并执行 pytest

---

## 14. 部署建议

-   开发阶段：docker-compose
-   生产建议：Kubernetes（将 TaskIQ worker 作为 Deployment，API 作为 Deployment，RabbitMQ 使用集群或托管服务）
-   配置管理：使用环境变量（项目的 `MULTI_AGENT_` 前缀），密钥使用 secret 管理

---

## 15. MVP 验收标准（Echo Agent）

1. API 能成功提交任务并返回 task_id。
2. TaskIQ worker 从队列接收消息并执行 EchoAgent，处理结果记录在 `tasks` 表或 result queue。
3. 日志能显示 trace_id，且能从 API 端一路追踪到 worker 日志。

---

## 16. 后续迭代建议（路线图）

-   Iteration 0：准备 schema、Agent 基类、CI skeleton
-   Iteration 1：实现 Echo Agent、集成测试、简单监控
-   Iteration 2：实现 Registry & Scheduler、另一个 Agent 类型
-   Iteration 3：健壮性改进、K8s 部署、自动扩缩容

---

如果你想，我可以把 Iteration 1 的工作拆成具体的 GitHub issue 列表并生成对应的测试用例与代码模板（把文件直接打成 patch）。

---

文档结束。
