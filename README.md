# Multi-Agent-Collaborative-Task-System-for-Software-Development

## FastAPI 最小可运行框架

这是一个最小的 FastAPI 应用框架，包含基本的路由和健康检查端点。

### 安装依赖

```bash
pip install -r requirements.txt
```

### 运行应用

#### 方法 1: 使用 Python 直接运行

```bash
python main.py
```

#### 方法 2: 使用 uvicorn 命令运行

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 访问应用

应用启动后，可以访问以下端点：

- 主页: http://localhost:8000/
- 健康检查: http://localhost:8000/health
- API 文档 (Swagger UI): http://localhost:8000/docs
- API 文档 (ReDoc): http://localhost:8000/redoc

### 项目结构

```
.
├── main.py           # FastAPI 应用主文件
├── requirements.txt  # 项目依赖
└── README.md        # 项目说明文档
```