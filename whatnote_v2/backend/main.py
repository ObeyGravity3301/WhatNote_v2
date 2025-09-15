"""
WhatNote V2 Backend API
使用绝对导入，通过run.py设置sys.path
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi import Request
import mimetypes
from fastapi.staticfiles import StaticFiles
import asyncio
import json
import os
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime
from config import API_HOST, API_PORT, DATA_DIR
from logger import info, error

# 导入新的存储管理器
from storage.file_manager import FileSystemManager
from storage.content_manager import ContentManager
from storage.file_watcher import FileWatcher

app = FastAPI(title="WhatNote V2 API", version="2.0.0")

# 挂载静态文件服务 - 简单可靠的文件访问方式
app.mount("/static/files", StaticFiles(directory=str(DATA_DIR)), name="static_files")

# 应用启动和关闭事件
@app.on_event("startup")
async def startup_event():
    """应用启动时启动文件监控服务"""
    info("启动文件监控服务...")
    file_watcher.start_watching()

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时停止文件监控服务"""
    info("停止文件监控服务...")
    file_watcher.stop_watching()

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket连接管理
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        info(f"WebSocket连接已建立，当前连接数: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            info(f"WebSocket连接已断开，当前连接数: {len(self.active_connections)}")

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except Exception as e:
            error(f"发送消息失败: {e}")

    async def broadcast(self, message: str):
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except Exception as e:
                error(f"广播消息失败: {e}")
                disconnected.append(connection)
        
        # 移除断开的连接
        for connection in disconnected:
            self.disconnect(connection)

# 初始化存储管理器
file_manager = FileSystemManager(DATA_DIR)
content_manager = ContentManager(file_manager)

# 初始化WebSocket连接管理器
manager = ConnectionManager()

# 初始化文件监控服务
file_watcher = FileWatcher(DATA_DIR, manager)
file_watcher.set_managers(file_manager, content_manager)

# 静态文件服务
import os
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def root():
    """根路径 - 返回HTML页面"""
    from fastapi.responses import FileResponse
    import os
    
    # 返回静态HTML文件
    html_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(html_path):
        return FileResponse(html_path)
    else:
        return {"message": "WhatNote V2 API"}

@app.get("/api/health")
async def health_check():
    """健康检查端点"""
    return {"status": "ok", "service": "WhatNote V2"}

# 课程相关API
@app.get("/api/courses")
async def get_courses():
    """获取所有课程"""
    try:
        courses = file_manager.get_courses()
        return {"courses": courses}
    except Exception as e:
        error(f"获取课程失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/courses")
async def create_course(name: str, description: str = ""):
    """创建新课程"""
    try:
        course = file_manager.create_course(name, description)
        info(f"创建课程成功: {course['id']}")
        return course
    except Exception as e:
        error(f"创建课程失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/courses/{course_id}/boards")
async def get_boards(course_id: str):
    """获取课程的所有展板"""
    try:
        boards = file_manager.get_boards(course_id)
        return {"boards": boards}
    except Exception as e:
        error(f"获取展板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/courses/{course_id}/boards")
async def create_board(course_id: str, board_name: str):
    """创建新展板"""
    try:
        board = file_manager.create_board(course_id, board_name)
        info(f"创建展板成功: {board['id']}")
        return board
    except Exception as e:
        error(f"创建展板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/boards/{board_id}")
async def get_board_info(board_id: str):
    """获取展板信息"""
    try:
        board_info = file_manager.get_board_info(board_id)
        if not board_info:
            raise HTTPException(status_code=404, detail="展板不存在")
        return board_info
    except HTTPException:
        raise
    except Exception as e:
        error(f"获取展板信息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/boards/{board_id}")
async def delete_board(board_id: str):
    """删除展板"""
    try:
        success = file_manager.delete_board(board_id)
        if not success:
            raise HTTPException(status_code=404, detail="展板不存在")
        info(f"删除展板成功: {board_id}")
        return {"message": "展板删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        error(f"删除展板失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 窗口管理API
@app.post("/api/boards/{board_id}/windows")
async def create_window(board_id: str, window_data: Dict):
    """创建窗口"""
    try:
        window_data["id"] = f"window_{int(datetime.now().timestamp() * 1000)}"
        window_data["created_at"] = datetime.now().isoformat()
        window_data["updated_at"] = datetime.now().isoformat()
        
        success = content_manager.save_window_content(board_id, window_data)
        if not success:
            raise HTTPException(status_code=404, detail="展板不存在")
        
        info(f"创建窗口成功: {window_data['id']}")
        return window_data
    except HTTPException:
        raise
    except Exception as e:
        error(f"创建窗口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/boards/{board_id}/windows/{window_id}")
async def update_window(board_id: str, window_id: str, window_data: Dict):
    """更新窗口"""
    try:
        # 检查是否需要重命名文件
        old_title = None
        if "title" in window_data:
            # 获取旧的窗口数据以比较标题
            try:
                windows = content_manager.get_board_windows(board_id)
                old_window = next((w for w in windows if w["id"] == window_id), None)
                if old_window and old_window.get("title") != window_data["title"]:
                    old_title = old_window.get("title")
            except Exception:
                pass
        
        window_data["id"] = window_id
        window_data["updated_at"] = datetime.now().isoformat()
        
        # 检查是否是内容更新
        if "content" in window_data:
            # 内容更新：直接更新.md文件
            content = window_data["content"]
            content_manager.update_window_content_only(board_id, window_id, content)
            info(f"更新窗口内容成功: {window_id}")
        else:
            # 非内容更新：处理标题重命名等
            if old_title:
                content_manager.rename_window_file(board_id, window_id, old_title, window_data["title"])
            
            success = content_manager.save_window_content(board_id, window_data)
            if not success:
                raise HTTPException(status_code=404, detail="展板不存在")
        
        info(f"更新窗口成功: {window_id}")
        return window_data
    except HTTPException:
        raise
    except Exception as e:
        error(f"更新窗口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/boards/{board_id}/windows/{window_id}")
async def delete_window(board_id: str, window_id: str, permanent: bool = False):
    """删除窗口（移动到回收站或永久删除）"""
    try:
        if permanent:
            # 永久删除
            success = content_manager.delete_window_content(board_id, window_id)
            message = "窗口永久删除成功"
        else:
            # 移动到回收站
            success = content_manager.move_window_to_trash(board_id, window_id)
            message = "窗口已移动到回收站"
        
        if not success:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        info(f"{message}: {window_id}")
        return {"message": message}
    except HTTPException:
        raise
    except Exception as e:
        error(f"删除窗口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 窗口转换API
@app.post("/api/windows/{window_id}/convert-to-text")
async def convert_window_to_text(window_id: str):
    """将通用窗口转换为文本窗口"""
    try:
        # 查找窗口所在的板块
        board_id = content_manager.find_window_board(window_id)
        if not board_id:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        # 执行转换
        success = content_manager.convert_window_to_text(board_id, window_id)
        if not success:
            raise HTTPException(status_code=400, detail="转换失败，可能窗口不是通用类型")
        
        info(f"窗口转换为文本成功: {window_id}")
        return {"message": "转换成功", "window_id": window_id}
    except HTTPException:
        raise
    except Exception as e:
        error(f"转换窗口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/windows/{window_id}/content")
async def update_window_content(window_id: str, content_data: Dict):
    """更新窗口内容"""
    try:
        # 查找窗口所在的板块
        board_id = content_manager.find_window_board(window_id)
        if not board_id:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        # 更新内容
        content = content_data.get("content", "")
        success = content_manager.update_window_content(board_id, window_id, content)
        if not success:
            raise HTTPException(status_code=400, detail="更新内容失败")
        
        info(f"窗口内容更新成功: {window_id}")
        return {"message": "内容更新成功", "window_id": window_id}
    except HTTPException:
        raise
    except Exception as e:
        error(f"更新窗口内容失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/boards/{board_id}/clean-storage")
async def clean_board_storage(board_id: str):
    """清理展板存储结构，移除board_info.json中的冗余数据"""
    try:
        content_manager.clean_board_info_redundancy(board_id)
        info(f"展板存储结构清理完成: {board_id}")
        return {"message": "存储结构清理完成"}
    except Exception as e:
        error(f"清理存储结构失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/clean-all-storage")
async def clean_all_storage():
    """清理所有展板的存储结构"""
    try:
        content_manager.clean_board_info_redundancy()
        info("所有展板存储结构清理完成")
        return {"message": "所有存储结构清理完成"}
    except Exception as e:
        error(f"清理所有存储结构失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/migrate-json-naming")
async def migrate_json_naming():
    """迁移到新的JSON命名规则（xxx.ext.json）"""
    try:
        content_manager.migrate_to_new_json_naming()
        info("JSON命名规则迁移完成")
        return {"message": "JSON命名规则迁移完成"}
    except Exception as e:
        error(f"迁移JSON命名规则失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/boards/{board_id}/fix-duplicate-windows")
async def fix_duplicate_windows(board_id: str):
    """修复重复的窗口ID问题"""
    try:
        result = content_manager.fix_duplicate_windows(board_id)
        info(f"重复窗口修复完成: {board_id}")
        return {"message": "重复窗口修复完成", "details": result}
    except Exception as e:
        error(f"修复重复窗口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/boards/{board_id}/windows/{window_id}/rename")
async def rename_window(board_id: str, window_id: str, data: Dict):
    """重命名窗口及其关联的文件"""
    try:
        new_name = data.get("new_name", "").strip()
        if not new_name:
            raise HTTPException(status_code=400, detail="新名称不能为空")
        
        result = content_manager.rename_window_and_file(board_id, window_id, new_name)
        if result["success"]:
            info(f"窗口重命名成功: {window_id} -> {new_name}")
            return {"message": "重命名成功", "new_filename": result["new_filename"]}
        else:
            raise HTTPException(status_code=400, detail=result["error"])
    except HTTPException:
        raise
    except Exception as e:
        error(f"重命名窗口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/boards/{board_id}/windows")
async def get_board_windows(board_id: str):
    """获取展板的所有窗口"""
    try:
        windows = content_manager.get_board_windows(board_id)
        return {"windows": windows}
    except Exception as e:
        error(f"获取窗口失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 图标位置管理API
@app.get("/api/boards/{board_id}/icon-positions")
async def get_icon_positions(board_id: str):
    """获取展板的图标位置数据"""
    try:
        positions = content_manager.get_icon_positions(board_id)
        return {"iconPositions": positions}
    except Exception as e:
        error(f"获取图标位置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/boards/{board_id}/icon-positions")
async def save_icon_positions(board_id: str, data: Dict):
    """保存展板的图标位置数据"""
    try:
        icon_positions = data.get("iconPositions", [])
        content_manager.save_icon_positions(board_id, icon_positions)
        info(f"保存图标位置成功: {board_id}")
        return {"message": "图标位置保存成功"}
    except Exception as e:
        error(f"保存图标位置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 文件上传API
@app.post("/api/boards/{board_id}/upload")
async def upload_file(
    board_id: str,
    request: Request,
    file: UploadFile = File(...),
    file_type: Optional[str] = Form(None),
    q_file_type: Optional[str] = Query(None, alias="file_type"),
    window_id: Optional[str] = Form(None),
    q_window_id: Optional[str] = Query(None, alias="window_id"),
):
    """上传文件到展板"""
    try:
        # 兼容从查询参数传入 file_type 和 window_id
        file_type_value = file_type or q_file_type
        window_id_value = window_id or q_window_id
        # 验证文件类型
        allowed_types = ["images", "videos", "pdfs", "audios", "texts"]
        if not file_type_value or file_type_value not in allowed_types:
            raise HTTPException(status_code=400, detail="不支持的文件类型")
        
        # 保存文件到临时位置（使用系统临时目录，避免FileWatcher检测）
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # 移动到展板文件夹，使用window_id命名
        file_path = content_manager.save_file_to_board(board_id, file_type_value, temp_path, file.filename, window_id_value)
        
        # 删除临时文件
        os.remove(temp_path)
        
        info(f"文件上传成功: {file.filename} -> {file_path}")
        # 构造绝对URL，避免前端在 3000 端口使用相对路径访问
        base_url = f"http://{API_HOST}:{API_PORT}"
        absolute_url = f"{base_url}/api/boards/{board_id}/files/serve?path={str(file_path)}"
        
        # 如果有window_id，更新窗口的content字段为文件URL
        if window_id_value:
            try:
                info(f"开始更新窗口内容: window_id={window_id_value}")
                # 获取当前窗口数据
                windows = content_manager.get_board_windows(board_id)
                info(f"获取到窗口列表，共 {len(windows)} 个窗口")
                
                target_window = None
                for window in windows:
                    if window.get('id') == window_id_value:
                        target_window = window
                        info(f"找到目标窗口: {window_id_value}")
                        break
                
                if target_window:
                    info(f"更新前窗口内容: {target_window.get('content', 'None')}")
                    # 只更新窗口的content字段，不再调用save_window_content避免重复处理
                    # save_file_to_board已经正确更新了文件路径和标题
                    content_manager.update_window_content_only(board_id, window_id_value, absolute_url)
                    info(f"窗口内容已更新: {window_id_value} -> {absolute_url}")
                else:
                    error(f"未找到目标窗口: {window_id_value}")
            except Exception as e:
                error(f"更新窗口内容失败: {e}")
                import traceback
                error(f"详细错误信息: {traceback.format_exc()}")
        
        return {
            "message": "文件上传成功",
            "file_path": str(file_path),
            "filename": file.filename,
            "file_url": absolute_url
        }
    except HTTPException:
        raise
    except Exception as e:
        error(f"文件上传失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/media/serve")
async def serve_media_file(path: str):
    """全新的媒体文件服务API - 避免路由冲突"""
    try:
        print(f"🔧 媒体服务请求: path={path}")
        
        # 直接使用传入的绝对路径
        file_path = Path(path)
        
        # 基本验证：文件必须存在且是文件
        if not file_path.exists():
            print(f"❌ 文件不存在: {file_path}")
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if not file_path.is_file():
            print(f"❌ 路径不是文件: {file_path}")
            raise HTTPException(status_code=400, detail="路径不是文件")
        
        # 获取MIME类型
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        print(f"✅ 返回媒体文件: {file_path.name}, MIME: {mime_type}")
        
        # 直接返回文件
        return FileResponse(
            path=str(file_path),
            media_type=mime_type,
            filename=file_path.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ 媒体服务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 文件列表API已移除，避免与 /files/serve 路由冲突

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket日志端点"""
    await manager.connect(websocket)
    try:
        while True:
            # 接收客户端消息并回显
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                log_message = f"收到日志消息: {message_data.get('message', '')}"
                info(log_message)
                
                # 广播给所有连接的客户端
                response = {
                    "type": "log", 
                    "message": log_message,
                    "timestamp": time.time()
                }
                await manager.broadcast(json.dumps(response, ensure_ascii=False))
            except json.JSONDecodeError:
                await websocket.send_text("无效的JSON格式")
    except WebSocketDisconnect:
        manager.disconnect(websocket)

        # 设置正确的媒体类型和 inline 显示，并支持 Range 请求（视频/音频常用）
        mime_type, _ = mimetypes.guess_type(str(requested))
        file_size = requested.stat().st_size
        range_header = request.headers.get('range') or request.headers.get('Range')
        if range_header:
            # e.g. bytes=0- or bytes=100-200
            try:
                units, range_spec = range_header.split('=')
                start_str, end_str = range_spec.split('-')
                start = int(start_str) if start_str else 0
                end = int(end_str) if end_str else file_size - 1
                start = max(0, start)
                end = min(file_size - 1, end)
                length = end - start + 1

                def file_iter(path_obj, s, e, chunk_size: int = 1024 * 1024):
                    with open(path_obj, 'rb') as f:
                        f.seek(s)
                        remaining = e - s + 1
                        while remaining > 0:
                            chunk = f.read(min(chunk_size, remaining))
                            if not chunk:
                                break
                            remaining -= len(chunk)
                            yield chunk

                headers = {
                    'Content-Range': f'bytes {start}-{end}/{file_size}',
                    'Accept-Ranges': 'bytes',
                    'Content-Length': str(length),
                    'Content-Disposition': f'inline; filename="{requested.name}"',
                }
                return StreamingResponse(
                    file_iter(requested, start, end),
                    status_code=206,
                    media_type=mime_type or 'application/octet-stream',
                    headers=headers,
                )
            except Exception as e:
                error(f"Range 解析失败: {e}")

        # 无 Range：整文件返回
        headers = {
            'Accept-Ranges': 'bytes',
            'Content-Disposition': f'inline; filename="{requested.name}"',
        }
        return FileResponse(
            str(requested),
            media_type=mime_type or 'application/octet-stream',
            headers=headers,
        )
    except HTTPException:
        raise
    except Exception as e:
        error(f"文件读取失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket日志端点"""
    await manager.connect(websocket)
    try:
        while True:
            # 接收客户端消息并回显
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
                log_message = f"收到日志消息: {message_data.get('message', '')}"
                info(log_message)
                
                # 广播给所有连接的客户端
                response = {
                    "type": "log",
                    "message": log_message,
                    "timestamp": asyncio.get_event_loop().time()
                }
                await manager.broadcast(json.dumps(response))
                
            except json.JSONDecodeError:
                error("收到无效的JSON消息")
                await manager.send_personal_message(
                    json.dumps({"error": "无效的JSON格式"}), 
                    websocket
                )
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        error(f"WebSocket错误: {e}")
        manager.disconnect(websocket)

# 回收站相关API
@app.get("/api/trash")
async def get_trash_items():
    """获取回收站中的所有项目"""
    try:
        items = content_manager.trash_manager.get_trash_items()
        return {"items": items}
    except Exception as e:
        error(f"获取回收站项目失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/trash/{trash_id}/restore")
async def restore_from_trash(trash_id: str):
    """从回收站恢复文件"""
    try:
        success = content_manager.trash_manager.restore_from_trash(trash_id)
        if not success:
            raise HTTPException(status_code=404, detail="回收站项目不存在")
        
        info(f"从回收站恢复成功: {trash_id}")
        return {"message": "文件恢复成功"}
    except HTTPException:
        raise
    except Exception as e:
        error(f"从回收站恢复失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/trash/{trash_id}")
async def permanently_delete_trash(trash_id: str):
    """永久删除回收站中的文件"""
    try:
        success = content_manager.trash_manager.permanently_delete(trash_id)
        if not success:
            raise HTTPException(status_code=404, detail="回收站项目不存在")
        
        info(f"永久删除成功: {trash_id}")
        return {"message": "文件永久删除成功"}
    except HTTPException:
        raise
    except Exception as e:
        error(f"永久删除失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/trash")
async def empty_trash():
    """清空回收站"""
    try:
        success = content_manager.trash_manager.empty_trash()
        if not success:
            raise HTTPException(status_code=500, detail="清空回收站失败")
        
        info("回收站已清空")
        return {"message": "回收站已清空"}
    except Exception as e:
        error(f"清空回收站失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/trash/size")
async def get_trash_size():
    """获取回收站大小"""
    try:
        size = content_manager.trash_manager.get_trash_size()
        return {"size": size}
    except Exception as e:
        error(f"获取回收站大小失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    info("启动WhatNote V2后端服务...")
    uvicorn.run("main:app", host="127.0.0.1", port=8081, reload=False) 