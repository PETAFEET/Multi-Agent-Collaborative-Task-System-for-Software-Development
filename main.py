from fastapi import FastAPI

app = FastAPI()


@app.get("/")
async def root():
    """根路径 - 返回欢迎消息"""
    return {"message": "欢迎使用 FastAPI 最小框架"}


@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
