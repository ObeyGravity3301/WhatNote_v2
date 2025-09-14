"""
最简单的测试服务器
"""
from fastapi import FastAPI
import uvicorn

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/test")
def test():
    return {"message": "测试成功"}

if __name__ == "__main__":
    print("启动测试服务器...")
    uvicorn.run(app, host="127.0.0.1", port=8082)

