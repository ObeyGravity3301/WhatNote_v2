"""
WhatNote V2 Backend - 简化版本
专门用于修复文件服务问题
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
import mimetypes
import uvicorn

app = FastAPI(title="WhatNote V2 API", version="2.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "WhatNote V2 Backend - 简化版本"}

@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "WhatNote V2 Simple"}

@app.get("/api/boards/{board_id}/files/serve")
async def serve_board_file(board_id: str, path: str):
    """简单高效的文件服务API"""
    try:
        print(f"文件服务请求: board_id={board_id}, path={path}")
        
        # 直接使用传入的绝对路径
        file_path = Path(path)
        
        # 基本验证：文件必须存在且是文件
        if not file_path.exists():
            print(f"错误: 文件不存在: {file_path}")
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if not file_path.is_file():
            print(f"错误: 路径不是文件: {file_path}")
            raise HTTPException(status_code=400, detail="路径不是文件")
        
        # 获取MIME类型
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        print(f"成功: 返回文件: {file_path.name}, MIME: {mime_type}")
        
        # 直接返回文件
        return FileResponse(
            path=str(file_path),
            media_type=mime_type,
            filename=file_path.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"错误: 文件服务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    print("启动WhatNote V2后端服务（简化版）...")
    uvicorn.run("simple_main:app", host="127.0.0.1", port=8081, reload=False)

