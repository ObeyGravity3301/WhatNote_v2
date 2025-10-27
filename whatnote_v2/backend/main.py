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
from storage.conversation_manager import ConversationManager
from storage.api_config_manager import APIConfigManager
from llm_service import LLMService
from document_converter import document_converter

app = FastAPI(title="WhatNote V2 API", version="2.0.0")

# 挂载静态文件服务 - 简单可靠的文件访问方式
app.mount("/static/files", StaticFiles(directory=str(DATA_DIR)), name="static_files")

def analyze_outline_page_coverage(outline_data, total_pages):
    """
    分析大纲的页码覆盖情况，记录重叠页面信息（用于后续注释融合）
    
    Args:
        outline_data: 大纲数据
        total_pages: 总页数
    
    Returns:
        dict: {
            'overlapping_pages': dict,  # 页码 -> [章节编号列表]
            'coverage': dict,
            'statistics': dict
        }
    """
    if not outline_data or 'outline' not in outline_data:
        return {
            'overlapping_pages': {},
            'coverage': {},
            'statistics': {'valid': False}
        }
    
    outline = outline_data['outline']
    if not outline:
        return {
            'overlapping_pages': {},
            'coverage': {},
            'statistics': {'valid': False}
        }
    
    # 记录每个页面被哪些章节覆盖
    page_to_sections = {}  # 页码 -> [章节信息列表]
    
    for i, section in enumerate(outline):
        if 'page_start' not in section or 'page_end' not in section:
            continue
        
        start = section['page_start']
        end = section['page_end']
        section_num = section.get('section_number', i + 1)
        section_title = section.get('title', f'章节{section_num}')
        
        # 验证页码范围合法性
        if start < 1 or end < 1 or start > end:
            continue
        
        if start > total_pages or end > total_pages:
            continue
        
        # 记录每个页面属于哪些章节
        for page in range(start, end + 1):
            if page not in page_to_sections:
                page_to_sections[page] = []
            page_to_sections[page].append({
                'section_number': section_num,
                'section_title': section_title,
                'section_index': i
            })
    
    # 识别重叠页面（被多个章节覆盖的页面）
    overlapping_pages = {}
    for page, sections in page_to_sections.items():
        if len(sections) > 1:
            overlapping_pages[page] = sections
    
    # 统计信息
    covered_pages = set(page_to_sections.keys())
    missing_pages = []
    for page in range(1, total_pages + 1):
        if page not in covered_pages:
            missing_pages.append(page)
    
    coverage = {
        'total_pages': total_pages,
        'covered_pages': len(covered_pages),
        'missing_pages': missing_pages,
        'coverage_rate': len(covered_pages) / total_pages if total_pages > 0 else 0
    }
    
    statistics = {
        'valid': True,
        'total_sections': len(outline),
        'overlapping_pages_count': len(overlapping_pages),
        'multi_annotated_pages': list(overlapping_pages.keys()),  # 需要融合注释的页面
        'max_overlap_count': max([len(sections) for sections in overlapping_pages.values()]) if overlapping_pages else 0
    }
    
    return {
        'overlapping_pages': overlapping_pages,
        'coverage': coverage,
        'statistics': statistics
    }

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
    try:
        file_watcher.stop_watching()
        info("文件监控服务已停止")
    except Exception as e:
        info(f"停止文件监控服务时出错: {e}")
    
    # 等待一下让线程完全停止
    import time
    time.sleep(0.1)

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
conversation_manager = ConversationManager(file_manager)
api_config_manager = APIConfigManager(DATA_DIR)
llm_service = LLMService(api_config_manager)

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
        
        # 检查是否是纯内容更新（只有content字段，没有其他窗口属性）
        content_only_update = "content" in window_data and len([k for k in window_data.keys() if k not in ["id", "updated_at", "content"]]) == 0
        
        if content_only_update:
            # 纯内容更新：只更新.md文件
            content = window_data["content"]
            content_manager.update_window_content_only(board_id, window_id, content)
            info(f"更新窗口内容成功: {window_id}")
        else:
            # 窗口属性更新（可能包含位置、大小、隐藏状态等）
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

# 窗口文件上传API - 专门用于将文本窗口转换为文件窗口
@app.post("/api/boards/{board_id}/windows/{window_id}/upload")
async def upload_file_to_window(
    board_id: str,
    window_id: str,
    file: UploadFile = File(...)
):
    """上传文件到指定窗口，将文本窗口转换为文件窗口"""
    try:
        info(f"开始上传文件到窗口: {window_id}, 文件名: {file.filename}")
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        target_window = None
        for window in windows:
            if window.get('id') == window_id:
                target_window = window
                break
        
        if not target_window:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        if target_window.get('type') != 'text':
            raise HTTPException(status_code=400, detail="只能向文本窗口上传文件")
        
        # 确定文件类型
        file_extension = Path(file.filename).suffix.lower()
        file_type_map = {
            '.jpg': 'image', '.jpeg': 'image', '.png': 'image', '.gif': 'image', '.bmp': 'image', '.webp': 'image',
            '.mp4': 'video', '.avi': 'video', '.mov': 'video', '.wmv': 'video', '.flv': 'video', '.webm': 'video',
            '.mp3': 'audio', '.wav': 'audio', '.flac': 'audio', '.aac': 'audio', '.ogg': 'audio',
            '.pdf': 'pdf',
            '.doc': 'document', '.docx': 'document', '.ppt': 'document', '.pptx': 'document', '.xls': 'document', '.xlsx': 'document',
            '.txt': 'text', '.md': 'text'
        }
        
        original_window_type = file_type_map.get(file_extension, 'generic')
        window_type = original_window_type
        
        # 如果是Word文档，需要转换为PDF
        if original_window_type == 'document' and file_extension in ['.doc', '.docx']:
            info(f"检测到Word文档，准备转换为PDF: {file.filename}")
            # 暂时保持document类型，在转换成功后再改为pdf
        
        # 保存文件
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix=f"_{file.filename}") as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name
        
        # 如果是Word文档，先转换为PDF
        final_file_path = temp_path
        final_filename = file.filename
        final_window_type = window_type
        
        if original_window_type == 'document' and file_extension in ['.doc', '.docx', '.ppt', '.pptx', '.xls', '.xlsx']:
            try:
                # 创建临时输出目录
                temp_output_dir = tempfile.mkdtemp()
                
                # 转换Office文档为PDF
                pdf_path = document_converter.convert_office_to_pdf(temp_path, temp_output_dir)
                
                if pdf_path and Path(pdf_path).exists():
                    if pdf_path.endswith('.pdf'):
                        # 转换为PDF成功
                        final_file_path = pdf_path
                        final_filename = Path(file.filename).stem + ".pdf"
                        final_window_type = 'pdf'
                        info(f"Office文档转换为PDF成功: {file.filename} -> {final_filename}")
                    elif pdf_path.endswith('.html'):
                        # 转换为HTML成功
                        final_file_path = pdf_path
                        final_filename = Path(file.filename).stem + ".html"
                        final_window_type = 'document'  # HTML文件也作为document类型处理
                        info(f"Office文档转换为HTML成功: {file.filename} -> {final_filename}")
                    elif pdf_path.endswith('.txt'):
                        # 转换为文本成功
                        final_file_path = pdf_path
                        final_filename = Path(file.filename).stem + ".txt"
                        final_window_type = 'text'
                        info(f"Office文档转换为文本成功: {file.filename} -> {final_filename}")
                    else:
                        # 其他格式，保持原文件
                        info(f"Office文档转换失败，保持原格式: {file.filename}")
                        final_window_type = 'document'
                else:
                    # 转换失败，保持原文件
                    info(f"Office文档转换失败，保持原格式: {file.filename}")
                    final_window_type = 'document'
                
            except Exception as e:
                error(f"Office文档转换异常: {e}")
                # 转换失败，保持原文件
                final_window_type = 'document'
        
        # 使用content_manager保存文件并转换窗口，传递原文件路径
        success = content_manager.convert_text_window_to_file_window(
            board_id, window_id, final_file_path, final_filename, final_window_type, temp_path
        )
        
        # 删除临时文件
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
            if final_file_path != temp_path and os.path.exists(final_file_path):
                os.remove(final_file_path)
        except Exception as e:
            print(f"删除临时文件失败: {e}")
        
        if not success:
            raise HTTPException(status_code=500, detail="文件上传和窗口转换失败")
        
        # 获取更新后的窗口信息
        updated_windows = content_manager.get_board_windows(board_id)
        updated_window = None
        for window in updated_windows:
            if window.get('id') == window_id:
                updated_window = window
                break
        
        if not updated_window:
            raise HTTPException(status_code=500, detail="无法获取更新后的窗口信息")
        
        info(f"文件上传和窗口转换成功: {file.filename} -> {window_type}")
        
        # 如果是PDF文件，自动提取文本
        if final_window_type == 'pdf':
            try:
                info(f"开始自动提取PDF文本: {window_id}")
                text_extraction_success = content_manager.extract_pdf_text_to_pages(
                    board_id, window_id, updated_window
                )
                if text_extraction_success:
                    info(f"PDF文本自动提取成功: {window_id}")
                else:
                    info(f"PDF文本自动提取失败: {window_id}")
            except Exception as e:
                info(f"PDF文本自动提取异常: {e}")
        
        return {
            "message": "文件上传成功",
            "filename": file.filename,
            "window_type": final_window_type,  # 使用最终确定的窗口类型
            "file_path": updated_window.get('file_path', ''),
            "content": updated_window.get('content', ''),
            "text_extracted": final_window_type == 'pdf'  # 标记是否进行了文本提取
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"窗口文件上传失败: {e}")
        import traceback
        error(f"详细错误信息: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# PDF文本提取API
@app.post("/api/boards/{board_id}/windows/{window_id}/extract-text")
async def extract_pdf_text(board_id: str, window_id: str):
    """提取PDF文本并保存到pages文件夹"""
    try:
        info(f"开始提取PDF文本: {window_id}")
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        target_window = None
        for window in windows:
            if window.get('id') == window_id:
                target_window = window
                break
        
        if not target_window:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        if target_window.get('type') != 'pdf':
            raise HTTPException(status_code=400, detail="只能提取PDF窗口的文本")
        
        # 提取PDF文本
        success = content_manager.extract_pdf_text_to_pages(board_id, window_id, target_window)
        
        if not success:
            raise HTTPException(status_code=500, detail="PDF文本提取失败")
        
        info(f"PDF文本提取成功: {window_id}")
        return {"message": "PDF文本提取成功", "window_id": window_id}
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"PDF文本提取失败: {e}")
        import traceback
        error(f"详细错误信息: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# PDF注释管理API
@app.get("/api/boards/{board_id}/windows/{window_id}/annotations/{page}")
async def get_pdf_annotation(board_id: str, window_id: str, page: int):
    """获取PDF指定页面的注释"""
    try:
        info(f"获取PDF注释: {window_id}, 页面: {page}")
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        target_window = None
        for window in windows:
            if window.get('id') == window_id:
                target_window = window
                break
        
        if not target_window:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        if target_window.get('type') != 'pdf':
            raise HTTPException(status_code=400, detail="只有PDF文件支持注释功能")
        
        # 获取注释内容
        annotation_content = content_manager.get_pdf_annotation(board_id, window_id, page)
        
        return {
            "success": True,
            "page": page,
            "content": annotation_content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"获取PDF注释失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取PDF注释失败: {str(e)}")

@app.put("/api/boards/{board_id}/windows/{window_id}/annotations/{page}")
async def save_pdf_annotation(board_id: str, window_id: str, page: int, annotation_data: Dict):
    """保存PDF指定页面的注释"""
    try:
        info(f"保存PDF注释: {window_id}, 页面: {page}")
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        target_window = None
        for window in windows:
            if window.get('id') == window_id:
                target_window = window
                break
        
        if not target_window:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        if target_window.get('type') != 'pdf':
            raise HTTPException(status_code=400, detail="只有PDF文件支持注释功能")
        
        # 保存注释内容
        content = annotation_data.get('content', '')
        result = content_manager.save_pdf_annotation(board_id, window_id, page, content)
        
        return {
            "success": True,
            "page": page,
            "message": "注释保存成功",
            "result": result
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"保存PDF注释失败: {e}")
        raise HTTPException(status_code=500, detail=f"保存PDF注释失败: {str(e)}")

@app.get("/api/boards/{board_id}/windows/{window_id}/annotations/{page}/info")
async def get_pdf_annotation_info(board_id: str, window_id: str, page: int):
    """获取PDF注释文件信息（创建时间、修改时间等）"""
    try:
        info(f"获取PDF注释文件信息: {window_id}, 页面: {page}")
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        target_window = None
        for window in windows:
            if window.get('id') == window_id:
                target_window = window
                break
        
        if not target_window:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        if target_window.get('type') != 'pdf':
            raise HTTPException(status_code=400, detail="只有PDF文件支持注释功能")
        
        # 获取注释文件信息
        file_info = content_manager.get_pdf_annotation_file_info(board_id, window_id, page)
        
        return {
            "success": True,
            "page": page,
            "file_info": file_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"获取PDF注释文件信息失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取PDF注释文件信息失败: {str(e)}")

@app.post("/api/boards/{board_id}/windows/{window_id}/annotations/{page}/generate")
async def generate_pdf_annotation(
    board_id: str, 
    window_id: str, 
    page: int,
    request: Request
):
    """使用LLM生成PDF指定页面的注释"""
    try:
        info(f"生成PDF注释: board_id={board_id}, window_id={window_id}, page={page}")
        
        # 获取请求体中的自定义提示词（如果有）
        request_body = await request.json() if request.headers.get('content-type') == 'application/json' else {}
        custom_prompt_template = request_body.get('promptTemplate', '')
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        target_window = None
        for window in windows:
            if window.get('id') == window_id:
                target_window = window
                break
        
        if not target_window:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        if target_window.get('type') != 'pdf':
            raise HTTPException(status_code=400, detail="只有PDF文件支持注释功能")
        
        # 读取前一页、当前页、下一页的内容
        page_contents = content_manager.get_pdf_page_contents(board_id, window_id, page)
        
        if not page_contents.get('current'):
            raise HTTPException(status_code=404, detail="当前页面内容不存在")
        
        # 构建发送给LLM的提示词
        prompt_parts = []
        prompt_parts.append("请根据以下PDF页面内容生成注释。注意：我提供了前后页面的内容是为了防止页面分割导致内容不连续，你的注释应该主要针对当前页面。\n")
        
        if page_contents.get('previous'):
            prompt_parts.append(f"【上一页内容（第{page-1}页）】\n{page_contents['previous']}\n")
        
        prompt_parts.append(f"【当前页内容（第{page}页）】\n{page_contents['current']}\n")
        
        if page_contents.get('next'):
            prompt_parts.append(f"【下一页内容（第{page+1}页）】\n{page_contents['next']}\n")
        
        # 使用自定义提示词或默认提示词
        if custom_prompt_template:
            # 替换占位符
            task_prompt = custom_prompt_template.replace('{page}', str(page))
            prompt_parts.append(f"\n{task_prompt}")
        else:
            # 默认提示词
            prompt_parts.append(f"\n请为第{page}页生成注释，包括：\n1. 页面主要内容概要\n2. 重要知识点\n3. 需要注意的细节\n\n请用Markdown格式输出。")
        
        # 统一添加：不要代码框
        prompt_parts.append("\n**重要：请直接输出Markdown文本，不要在外面包裹```markdown```代码框。**")
        
        full_prompt = "\n".join(prompt_parts)
        info(f"生成的完整提示词长度: {len(full_prompt)} 字符")
        
        # 创建或获取该PDF的注释对话上下文
        # 同一个PDF文件的所有注释放在同一个json文件中
        pdf_filename = target_window.get('title', 'unknown')
        annotation_conv_id = f"annotation-{window_id}"  # 只用window_id，不包含page
        
        info(f"注释对话ID: {annotation_conv_id}")
        
        # 获取或创建对话（不使用分页参数）
        conversation = conversation_manager.get_conversation(board_id, annotation_conv_id, page=None, limit=None)
        if not conversation:
            info(f"创建新的注释对话: {annotation_conv_id}")
            # 创建新的注释对话
            conversation = conversation_manager.create_conversation(
                board_id, 
                title=f"PDF注释生成记录 - {pdf_filename}"
            )
            # 更新conversation_id为我们自定义的
            conversations_dir = conversation_manager.get_board_conversations_dir(board_id)
            old_file = conversations_dir / f"{conversation['id']}.json"
            new_file = conversations_dir / f"{annotation_conv_id}.json"
            if old_file.exists():
                old_file.rename(new_file)
                info(f"对话文件重命名: {conversation['id']} -> {annotation_conv_id}")
            conversation['id'] = annotation_conv_id
        else:
            info(f"使用现有注释对话: {annotation_conv_id}, 历史消息数: {len(conversation.get('messages', []))}")
        
        # 添加用户消息到对话历史（包含关键信息用于记录）
        user_message = {
            "role": "user",
            "content": full_prompt,
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "action": "generate_annotation",
                "pdf_filename": pdf_filename,
                "window_id": window_id,
                "page": page,
                "total_pages": "unknown",  # 可以后续从窗口信息中获取
                "style": request_body.get('style', 'default'),
                "has_previous_page": bool(page_contents.get('previous')),
                "has_next_page": bool(page_contents.get('next'))
            }
        }
        
        # 调用LLM生成注释（只使用当前消息，不使用历史对话）
        # 注释生成每次都是独立的，不需要上下文
        messages = [user_message]
        info(f"注释生成使用独立上下文，不包含历史消息")
        
        # 准备SSE流式响应
        async def generate_annotation_stream():
            accumulated_content = ""
            
            try:
                async for chunk in llm_service.chat_completion(messages, stream=True):
                    if chunk:
                        accumulated_content += chunk
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
                
                # 保存LLM响应到对话历史（包含元数据）
                assistant_message = {
                    "role": "assistant",
                    "content": accumulated_content,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "content_length": len(accumulated_content),
                        "generated_at": datetime.now().isoformat()
                    }
                }
                conversation_manager.add_message(board_id, annotation_conv_id, user_message)
                conversation_manager.add_message(board_id, annotation_conv_id, assistant_message)
                info(f"注释对话已保存: {annotation_conv_id}")
                
                # 将生成的注释插入到note文件的最前面
                info(f"开始保存注释: board_id={board_id}, window_id={window_id}, page={page}")
                info(f"生成的注释长度: {len(accumulated_content)} 字符")
                
                existing_note = content_manager.get_pdf_annotation(board_id, window_id, page)
                info(f"现有注释长度: {len(existing_note) if existing_note else 0} 字符")
                
                # 标注这是LLM生成的注释
                llm_annotation = f"<!-- LLM生成的注释 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -->\n\n"
                llm_annotation += accumulated_content
                llm_annotation += "\n\n---\n\n"
                
                # 如果有现有注释，追加在后面
                if existing_note:
                    llm_annotation += existing_note
                
                info(f"最终注释内容长度: {len(llm_annotation)} 字符")
                
                # 保存注释
                save_result = content_manager.save_pdf_annotation(board_id, window_id, page, llm_annotation)
                info(f"注释保存结果: {save_result}")
                
                # 在主对话（AI助手）中添加系统通知
                try:
                    # 查找该展板的主对话
                    conversations_dir = conversation_manager.get_board_conversations_dir(board_id)
                    if conversations_dir:
                        # 查找最新的主对话（conv-开头的）
                        main_conversations = sorted(
                            conversations_dir.glob("conv-*.json"),
                            key=lambda x: x.stat().st_mtime,
                            reverse=True
                        )
                        
                        if main_conversations:
                            # 获取最新的主对话ID
                            main_conv_file = main_conversations[0]
                            main_conv_id = main_conv_file.stem
                            
                            # 添加系统消息
                            system_notification = {
                                "role": "system",
                                "content": f"[系统通知] 用户对PDF文件《{pdf_filename}》的第{page}页执行了注释生成操作。",
                                "timestamp": datetime.now().isoformat(),
                                "metadata": {
                                    "type": "annotation_action",
                                    "pdf_filename": pdf_filename,
                                    "window_id": window_id,
                                    "page": page,
                                    "action": "generate_annotation"
                                }
                            }
                            
                            conversation_manager.add_message(board_id, main_conv_id, system_notification)
                            info(f"已向主对话添加系统通知: {main_conv_id}")
                            
                            # 通知前端刷新主对话
                            yield f"data: {json.dumps({'type': 'notification_added', 'conversation_id': main_conv_id}, ensure_ascii=False)}\n\n"
                        else:
                            info("未找到主对话，跳过系统通知")
                    
                except Exception as e:
                    # 系统通知失败不影响主流程
                    error(f"添加系统通知失败: {e}")
                
                yield f"data: {json.dumps({'type': 'done', 'success': True}, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                error(f"生成注释失败: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_annotation_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"生成PDF注释失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成PDF注释失败: {str(e)}")

@app.post("/api/boards/{board_id}/windows/{window_id}/annotations/{page}/generate-visual")
async def generate_pdf_annotation_visual(
    board_id: str, 
    window_id: str, 
    page: int,
    request: Request
):
    """使用LLM基于PDF页面图像生成注释（视觉生成）"""
    try:
        info(f"视觉生成PDF注释: board_id={board_id}, window_id={window_id}, page={page}")
        
        # 获取请求体
        request_body = await request.json() if request.headers.get('content-type') == 'application/json' else {}
        custom_prompt_template = request_body.get('promptTemplate', '')
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        target_window = None
        for window in windows:
            if window.get('id') == window_id:
                target_window = window
                break
        
        if not target_window:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        if target_window.get('type') != 'pdf':
            raise HTTPException(status_code=400, detail="只有PDF文件支持视觉注释功能")
        
        # 渲染PDF页面为图像
        image_path = content_manager.render_pdf_page_to_image(board_id, window_id, page)
        
        if not image_path:
            raise HTTPException(status_code=500, detail="PDF页面渲染失败")
        
        info(f"PDF页面已渲染为图像: {image_path}")
        
        # 读取图像文件
        with open(image_path, 'rb') as f:
            image_data = f.read()
        
        # 转换为base64
        import base64
        base64_image = base64.b64encode(image_data).decode('utf-8')
        
        # 构建发送给LLM的提示词
        if custom_prompt_template:
            task_prompt = custom_prompt_template.replace('{page}', str(page))
        else:
            task_prompt = f"请根据这张PDF页面的图像生成注释。这是第{page}页的内容。\n\n请生成：\n1. 页面主要内容概要\n2. 重要知识点\n3. 图表、公式的说明（如果有）\n4. 需要注意的细节\n\n请用Markdown格式输出。"
        
        task_prompt += "\n**重要：请直接输出Markdown文本，不要在外面包裹```markdown```代码框。**"
        
        # 创建或获取该PDF的注释对话上下文
        pdf_filename = target_window.get('title', 'unknown')
        annotation_conv_id = f"annotation-{window_id}"
        
        conversation = conversation_manager.get_conversation(board_id, annotation_conv_id, page=None, limit=None)
        if not conversation:
            conversation = conversation_manager.create_conversation(
                board_id, 
                title=f"PDF注释生成记录 - {pdf_filename}"
            )
            conversations_dir = conversation_manager.get_board_conversations_dir(board_id)
            old_file = conversations_dir / f"{conversation['id']}.json"
            new_file = conversations_dir / f"{annotation_conv_id}.json"
            if old_file.exists():
                old_file.rename(new_file)
            conversation['id'] = annotation_conv_id
        
        # 构建消息（包含图像）
        user_message = {
            "role": "user",
            "content": [
                {
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/png;base64,{base64_image}"
                    }
                },
                {
                    "type": "text",
                    "text": task_prompt
                }
            ],
            "timestamp": datetime.now().isoformat(),
            "metadata": {
                "action": "generate_visual_annotation",
                "pdf_filename": pdf_filename,
                "window_id": window_id,
                "page": page,
                "style": request_body.get('style', 'default'),
                "image_path": image_path
            }
        }
        
        # 调用LLM生成注释（独立上下文）
        messages = [user_message]
        
        # 准备SSE流式响应
        async def generate_visual_annotation_stream():
            accumulated_content = ""
            
            try:
                async for chunk in llm_service.chat_completion(messages, stream=True):
                    if chunk:
                        accumulated_content += chunk
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
                
                # 保存LLM响应到对话历史
                assistant_message = {
                    "role": "assistant",
                    "content": accumulated_content,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "content_length": len(accumulated_content),
                        "generated_at": datetime.now().isoformat(),
                        "method": "visual"
                    }
                }
                conversation_manager.add_message(board_id, annotation_conv_id, user_message)
                conversation_manager.add_message(board_id, annotation_conv_id, assistant_message)
                
                # 保存注释到note文件
                existing_note = content_manager.get_pdf_annotation(board_id, window_id, page)
                
                llm_annotation = f"<!-- LLM视觉生成的注释 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -->\n\n"
                llm_annotation += accumulated_content
                llm_annotation += "\n\n---\n\n"
                
                if existing_note:
                    llm_annotation += existing_note
                
                content_manager.save_pdf_annotation(board_id, window_id, page, llm_annotation)
                
                # 在主对话中添加系统通知（包含图像路径）
                try:
                    conversations_dir = conversation_manager.get_board_conversations_dir(board_id)
                    if conversations_dir:
                        main_conversations = sorted(
                            conversations_dir.glob("conv-*.json"),
                            key=lambda x: x.stat().st_mtime,
                            reverse=True
                        )
                        
                        if main_conversations:
                            main_conv_id = main_conversations[0].stem
                            
                            system_notification = {
                                "role": "system",
                                "content": f"[系统通知] 用户对PDF文件《{pdf_filename}》的第{page}页执行了视觉生成注释操作。",
                                "timestamp": datetime.now().isoformat(),
                                "metadata": {
                                    "type": "annotation_action",
                                    "pdf_filename": pdf_filename,
                                    "window_id": window_id,
                                    "page": page,
                                    "action": "generate_visual_annotation",
                                    "thumbnail_path": image_path
                                }
                            }
                            
                            conversation_manager.add_message(board_id, main_conv_id, system_notification)
                            info(f"已向主对话添加视觉生成系统通知: {main_conv_id}")
                            
                            yield f"data: {json.dumps({'type': 'notification_added', 'conversation_id': main_conv_id}, ensure_ascii=False)}\n\n"
                
                except Exception as e:
                    error(f"添加系统通知失败: {e}")
                
                yield f"data: {json.dumps({'type': 'done', 'success': True, 'image_path': image_path}, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                error(f"视觉生成注释失败: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_visual_annotation_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"视觉生成PDF注释失败: {e}")
        raise HTTPException(status_code=500, detail=f"视觉生成PDF注释失败: {str(e)}")

@app.post("/api/boards/{board_id}/windows/{window_id}/annotations/batch/outline")
async def generate_batch_outline(
    board_id: str,
    window_id: str,
    request: Request
):
    """生成PDF批量注释大纲（使用LLM3进行全局分析）"""
    try:
        info(f"生成批量注释大纲: board_id={board_id}, window_id={window_id}")
        
        # 配置参数
        SMALL_FILE_THRESHOLD = 30000  # 小文件阈值（字符数）
        PAGES_PER_GROUP = 10  # 大文件分组时每组页数
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        target_window = None
        for window in windows:
            if window.get('id') == window_id:
                target_window = window
                break
        
        if not target_window:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        if target_window.get('type') != 'pdf':
            raise HTTPException(status_code=400, detail="只有PDF文件支持批量注释功能")
        
        pdf_filename = target_window.get('title', 'unknown')
        info(f"开始分析PDF文件: {pdf_filename}")
        
        # 读取PDF所有页面内容
        all_pages_content = []
        total_chars = 0
        page_num = 1
        
        while True:
            page_content = content_manager.get_pdf_page_contents(board_id, window_id, page_num)
            if not page_content.get('current'):
                break
            
            page_text = page_content['current']
            all_pages_content.append({
                'page': page_num,
                'content': page_text,
                'length': len(page_text)
            })
            total_chars += len(page_text)
            page_num += 1
        
        total_pages = len(all_pages_content)
        info(f"PDF总页数: {total_pages}, 总字符数: {total_chars}")
        
        if total_pages == 0:
            raise HTTPException(status_code=400, detail="PDF文件无内容")
        
        # 创建或获取大纲对话记录
        outline_conv_id = f"outline-pdf-{window_id}-3"
        conversation = conversation_manager.get_conversation(board_id, outline_conv_id, page=None, limit=None)
        if not conversation:
            conversation = conversation_manager.create_conversation(
                board_id,
                title=f"批量注释大纲 - {pdf_filename}"
            )
            conversations_dir = conversation_manager.get_board_conversations_dir(board_id)
            old_file = conversations_dir / f"{conversation['id']}.json"
            new_file = conversations_dir / f"{outline_conv_id}.json"
            if old_file.exists():
                old_file.rename(new_file)
            conversation['id'] = outline_conv_id
        
        # 准备SSE流式响应
        async def generate_outline_stream():
            try:
                # 判断使用哪种方法
                if total_chars <= SMALL_FILE_THRESHOLD:
                    # 方法1：小文件，直接发送全部内容给LLM3
                    info(f"使用直接方法（文件较小）: {total_chars} 字符")
                    yield f"data: {json.dumps({'type': 'status', 'message': '文件较小，直接分析中...'}, ensure_ascii=False)}\n\n"
                    
                    # 构建完整文本
                    full_text = "\n\n".join([
                        f"=== 第{p['page']}页 ===\n{p['content']}"
                        for p in all_pages_content
                    ])
                    
                    # 构建提示词
                    prompt = f"""你是一位专业的文档分析助手。请分析以下PDF文档的全部内容，并生成一个结构化的大纲。

**文档信息**：
- 文件名: {pdf_filename}
- 总页数: {total_pages}

**文档内容**：
{full_text}

**任务要求**：
1. 分析文档的整体结构和内容
2. 将文档划分为若干个逻辑部分（章节、主题等）
3. 为每个部分提供：
   - 部分编号（从1开始）
   - 简洁的标题
   - 简要描述（50-100字）
   - 起始页码和结束页码（可以根据内容逻辑自然划分，重要内容可以跨章节）

**输出格式**（必须严格遵守JSON格式）：
```json
{{
  "outline": [
    {{
      "section_number": 1,
      "title": "章节标题",
      "description": "章节描述",
      "page_start": 1,
      "page_end": 5
    }},
    {{
      "section_number": 2,
      "title": "章节标题",
      "description": "章节描述",
      "page_start": 5,
      "page_end": 10
    }}
  ]
}}
```

**提示**：
- 页码范围应该根据内容的逻辑结构划分
- 重要的跨章节内容可以在多个部分中出现
- 确保所有页码从1到{total_pages}都被覆盖

请直接输出JSON，不要添加任何额外的说明文字或代码块标记。"""
                    
                    # 发送给LLM3
                    user_message = {
                        "role": "user",
                        "content": prompt,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": {
                            "action": "generate_batch_outline",
                            "pdf_filename": pdf_filename,
                            "window_id": window_id,
                            "total_pages": total_pages,
                            "total_chars": total_chars,
                            "method": "direct"
                        }
                    }
                    
                    messages = [user_message]
                    accumulated_content = ""
                    
                    async for chunk in llm_service.chat_completion(messages, stream=True):
                        if chunk:
                            accumulated_content += chunk
                            yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
                    
                    # 保存助手消息
                    assistant_message = {
                        "role": "assistant",
                        "content": accumulated_content,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": {
                            "action": "generate_batch_outline",
                            "method": "direct",
                            "total_pages": total_pages,
                            "total_chars": total_chars
                        }
                    }
                    
                    conversation_manager.add_message(board_id, outline_conv_id, user_message)
                    conversation_manager.add_message(board_id, outline_conv_id, assistant_message)
                    
                    # 解析JSON结果
                    try:
                        # 尝试提取JSON（可能被包裹在代码块中）
                        content = accumulated_content.strip()
                        if content.startswith('```'):
                            # 移除代码块标记
                            lines = content.split('\n')
                            content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content
                        
                        outline_data = json.loads(content)
                        
                        # 分析页码覆盖情况，记录重叠信息
                        analysis_result = analyze_outline_page_coverage(outline_data, total_pages)
                        
                        # 将重叠信息添加到大纲数据中
                        outline_data['page_analysis'] = {
                            'overlapping_pages': analysis_result['overlapping_pages'],
                            'statistics': analysis_result['statistics'],
                            'coverage': analysis_result['coverage']
                        }
                        
                        # 记录重叠情况
                        if analysis_result['statistics']['overlapping_pages_count'] > 0:
                            overlap_count = analysis_result['statistics']['overlapping_pages_count']
                            info(f"检测到{overlap_count}个重叠页面，将用于后续注释融合")
                            info(f"重叠页面列表: {analysis_result['statistics']['multi_annotated_pages']}")
                            yield f"data: {json.dumps({'type': 'info', 'message': f'检测到{overlap_count}个页面会被多次注释，后续将自动融合'}, ensure_ascii=False)}\n\n"
                        
                        # 保存大纲数据（包含重叠信息）到文件
                        outline_file = conversation_manager.get_board_conversations_dir(board_id) / f"outline-{window_id}-data.json"
                        with open(outline_file, 'w', encoding='utf-8') as f:
                            json.dump(outline_data, f, ensure_ascii=False, indent=2)
                        info(f"大纲数据已保存: {outline_file}")
                        
                        # 在主对话（AI助手）中添加系统通知
                        try:
                            conversations_dir = conversation_manager.get_board_conversations_dir(board_id)
                            if conversations_dir:
                                # 查找最新的主对话（conv-开头的）
                                main_conversations = sorted(
                                    conversations_dir.glob("conv-*.json"),
                                    key=lambda x: x.stat().st_mtime,
                                    reverse=True
                                )
                                
                                if main_conversations:
                                    main_conv_file = main_conversations[0]
                                    main_conv_id = main_conv_file.stem
                                    
                                    # 准备大纲摘要（用于LLM理解）
                                    sections_summary = []
                                    for section in outline_data.get('outline', []):
                                        sections_summary.append({
                                            "index": section.get('section_number', len(sections_summary)),
                                            "title": section.get('title', section.get('section_title', '未命名')),
                                            "pages": [section.get('page_start'), section.get('page_end')]
                                        })
                                    
                                    # 添加系统消息
                                    system_notification = {
                                        "role": "system",
                                        "content": f"📚 用户对PDF文件《{pdf_filename}》生成了文档大纲，共{len(sections_summary)}个分段。",
                                        "timestamp": datetime.now().isoformat(),
                                        "metadata": {
                                            "type": "batch_outline_generated",
                                            "pdf_filename": pdf_filename,
                                            "window_id": window_id,
                                            "total_sections": len(sections_summary),
                                            "sections_summary": sections_summary
                                        }
                                    }
                                    
                                    conversation_manager.add_message(board_id, main_conv_id, system_notification)
                                    info(f"已向主对话添加大纲生成通知: {main_conv_id}")
                                    
                                    yield f"data: {json.dumps({'type': 'notification_added', 'conversation_id': main_conv_id}, ensure_ascii=False)}\n\n"
                                else:
                                    info("未找到主对话，跳过系统通知")
                        except Exception as e:
                            error(f"添加系统通知失败: {e}")
                        
                        yield f"data: {json.dumps({'type': 'outline', 'outline': outline_data}, ensure_ascii=False)}\n\n"
                    except json.JSONDecodeError as e:
                        error(f"解析大纲JSON失败: {e}")
                        yield f"data: {json.dumps({'type': 'error', 'error': 'JSON解析失败，请查看原始输出'}, ensure_ascii=False)}\n\n"
                    
                else:
                    # 方法2：大文件，分割后发送给多个子模型
                    info(f"使用分割方法（文件较大）: {total_chars} 字符")
                    yield f"data: {json.dumps({'type': 'status', 'message': '文件较大，使用分组分析...'}, ensure_ascii=False)}\n\n"
                    
                    # 分割页面
                    groups = []
                    for i in range(0, total_pages, PAGES_PER_GROUP):
                        group_pages = all_pages_content[i:i+PAGES_PER_GROUP]
                        groups.append({
                            'group_number': len(groups) + 1,
                            'pages': group_pages,
                            'page_start': group_pages[0]['page'],
                            'page_end': group_pages[-1]['page']
                        })
                    
                    info(f"分为{len(groups)}组进行分析")
                    yield f"data: {json.dumps({'type': 'status', 'message': f'分为{len(groups)}组进行分析...'}, ensure_ascii=False)}\n\n"
                    
                    # 对每组进行分析
                    group_outlines = []
                    for group in groups:
                        group_num = group['group_number']
                        page_start = group['page_start']
                        page_end = group['page_end']
                        status_message = f'正在分析第{group_num}组 (第{page_start}-{page_end}页)...'
                        yield f"data: {json.dumps({'type': 'status', 'message': status_message}, ensure_ascii=False)}\n\n"
                        
                        # 构建组文本
                        group_text = "\n\n".join([
                            f"=== 第{p['page']}页 ===\n{p['content']}"
                            for p in group['pages']
                        ])
                        
                        # 构建子模型提示词
                        sub_prompt = f"""你是一位专业的文档分析助手。请分析以下PDF文档片段的内容，并生成一个结构化的大纲。

**文档信息**：
- 文件名: {pdf_filename}
- 分析范围: 第{group['page_start']}-{group['page_end']}页（共{total_pages}页）
- 组号: {group_num}/{len(groups)}

**文档片段内容**：
{group_text}

**任务要求**：
1. 分析这个片段的结构和内容
2. 将片段划分为若干个逻辑部分
3. 为每个部分提供：
   - 部分编号（从1开始，仅用于本组内）
   - 简洁的标题
   - 简要描述（50-100字）
   - 起始页码和结束页码（根据内容逻辑自然划分）

**输出格式**（必须严格遵守JSON格式）：
```json
{{
  "outline": [
    {{
      "section_number": 1,
      "title": "章节标题",
      "description": "章节描述",
      "page_start": {group['page_start']},
      "page_end": {group['page_end']}
    }}
  ]
}}
```

请直接输出JSON，不要添加任何额外的说明文字或代码块标记。"""
                        
                        # 创建子对话记录
                        sub_conv_id = f"outline-pdf-{window_id}-3{chr(64+group_num)}"  # 3A, 3B, 3C...
                        sub_conversation = conversation_manager.get_conversation(board_id, sub_conv_id, page=None, limit=None)
                        if not sub_conversation:
                            sub_conversation = conversation_manager.create_conversation(
                                board_id,
                                title=f"批量注释大纲-分组{group_num} - {pdf_filename}"
                            )
                            conversations_dir = conversation_manager.get_board_conversations_dir(board_id)
                            old_file = conversations_dir / f"{sub_conversation['id']}.json"
                            new_file = conversations_dir / f"{sub_conv_id}.json"
                            if old_file.exists():
                                old_file.rename(new_file)
                            sub_conversation['id'] = sub_conv_id
                        
                        # 发送给子模型
                        sub_user_message = {
                            "role": "user",
                            "content": sub_prompt,
                            "timestamp": datetime.now().isoformat(),
                            "metadata": {
                                "action": "generate_batch_outline_sub",
                                "pdf_filename": pdf_filename,
                                "window_id": window_id,
                                "group_number": group_num,
                                "page_start": group['page_start'],
                                "page_end": group['page_end'],
                                "method": "split"
                            }
                        }
                        
                        sub_messages = [sub_user_message]
                        sub_accumulated_content = ""
                        
                        async for chunk in llm_service.chat_completion(sub_messages, stream=True):
                            if chunk:
                                sub_accumulated_content += chunk
                                # 将子模型的输出也流式传递给前端
                                yield f"data: {json.dumps({'type': 'group_content', 'group': group_num, 'content': chunk}, ensure_ascii=False)}\n\n"
                        
                        # 保存子模型消息
                        sub_assistant_message = {
                            "role": "assistant",
                            "content": sub_accumulated_content,
                            "timestamp": datetime.now().isoformat(),
                            "metadata": {
                                "action": "generate_batch_outline_sub",
                                "group_number": group_num,
                                "method": "split"
                            }
                        }
                        
                        conversation_manager.add_message(board_id, sub_conv_id, sub_user_message)
                        conversation_manager.add_message(board_id, sub_conv_id, sub_assistant_message)
                        
                        # 解析子模型结果
                        try:
                            content = sub_accumulated_content.strip()
                            if content.startswith('```'):
                                lines = content.split('\n')
                                content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content
                            
                            sub_outline_data = json.loads(content)
                            group_outlines.append({
                                'group_number': group_num,
                                'outline': sub_outline_data.get('outline', [])
                            })
                            yield f"data: {json.dumps({'type': 'group_done', 'group': group_num, 'outline': sub_outline_data}, ensure_ascii=False)}\n\n"
                        except json.JSONDecodeError as e:
                            error(f"解析分组{group_num}大纲JSON失败: {e}")
                            group_outlines.append({
                                'group_number': group_num,
                                'outline': [],
                                'error': str(e)
                            })
                    
                    # 汇总所有分组结果
                    yield f"data: {json.dumps({'type': 'status', 'message': '正在汇总所有分组结果...'}, ensure_ascii=False)}\n\n"
                    
                    # 构建汇总提示词
                    groups_summary = "\n\n".join([
                        f"**分组{g['group_number']}**:\n{json.dumps(g['outline'], ensure_ascii=False, indent=2)}"
                        for g in group_outlines if 'error' not in g
                    ])
                    
                    merge_prompt = f"""你是一位专业的文档分析助手。我已经将一个PDF文档分成{len(groups)}组进行了分析，现在需要你将所有分组的大纲整合成一个统一的、连贯的大纲。

**文档信息**：
- 文件名: {pdf_filename}
- 总页数: {total_pages}

**各分组大纲**：
{groups_summary}

**任务要求**：
1. 整合所有分组的大纲，形成一个连贯的整体大纲
2. 合理组织章节结构，重要内容可以在多个章节中体现
3. 调整部分编号，确保从1开始连续
4. 优化章节标题和描述，使其更加清晰连贯
5. 尽量确保所有页码从1到{total_pages}都被覆盖

**输出格式**（必须严格遵守JSON格式）：
```json
{{
  "outline": [
    {{
      "section_number": 1,
      "title": "章节标题",
      "description": "章节描述",
      "page_start": 1,
      "page_end": 5
    }},
    {{
      "section_number": 2,
      "title": "章节标题",
      "description": "章节描述",
      "page_start": 6,
      "page_end": 10
    }}
  ]
}}
```

**提示**：
- 页码范围应该根据内容的逻辑结构划分
- 重要的跨章节内容可以在多个部分中出现
- 尽量确保所有页码从1到{total_pages}都被覆盖

请直接输出JSON，不要添加任何额外的说明文字或代码块标记。"""
                    
                    # 发送给LLM3进行汇总
                    merge_user_message = {
                        "role": "user",
                        "content": merge_prompt,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": {
                            "action": "generate_batch_outline_merge",
                            "pdf_filename": pdf_filename,
                            "window_id": window_id,
                            "total_pages": total_pages,
                            "total_groups": len(groups),
                            "method": "split_merge"
                        }
                    }
                    
                    merge_messages = [merge_user_message]
                    merge_accumulated_content = ""
                    
                    async for chunk in llm_service.chat_completion(merge_messages, stream=True):
                        if chunk:
                            merge_accumulated_content += chunk
                            yield f"data: {json.dumps({'type': 'merge_content', 'content': chunk}, ensure_ascii=False)}\n\n"
                    
                    # 保存汇总消息
                    merge_assistant_message = {
                        "role": "assistant",
                        "content": merge_accumulated_content,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": {
                            "action": "generate_batch_outline_merge",
                            "method": "split_merge",
                            "total_pages": total_pages,
                            "total_groups": len(groups)
                        }
                    }
                    
                    conversation_manager.add_message(board_id, outline_conv_id, merge_user_message)
                    conversation_manager.add_message(board_id, outline_conv_id, merge_assistant_message)
                    
                    # 解析最终大纲
                    try:
                        content = merge_accumulated_content.strip()
                        if content.startswith('```'):
                            lines = content.split('\n')
                            content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content
                        
                        final_outline_data = json.loads(content)
                        
                        # 分析页码覆盖情况，记录重叠信息
                        analysis_result = analyze_outline_page_coverage(final_outline_data, total_pages)
                        
                        # 将重叠信息添加到大纲数据中
                        final_outline_data['page_analysis'] = {
                            'overlapping_pages': analysis_result['overlapping_pages'],
                            'statistics': analysis_result['statistics'],
                            'coverage': analysis_result['coverage']
                        }
                        
                        # 记录重叠情况
                        if analysis_result['statistics']['overlapping_pages_count'] > 0:
                            overlap_count = analysis_result['statistics']['overlapping_pages_count']
                            info(f"检测到{overlap_count}个重叠页面，将用于后续注释融合")
                            info(f"重叠页面列表: {analysis_result['statistics']['multi_annotated_pages']}")
                            yield f"data: {json.dumps({'type': 'info', 'message': f'检测到{overlap_count}个页面会被多次注释，后续将自动融合'}, ensure_ascii=False)}\n\n"
                        
                        # 保存大纲数据（包含重叠信息）到文件
                        outline_file = conversation_manager.get_board_conversations_dir(board_id) / f"outline-{window_id}-data.json"
                        with open(outline_file, 'w', encoding='utf-8') as f:
                            json.dump(final_outline_data, f, ensure_ascii=False, indent=2)
                        info(f"大纲数据已保存: {outline_file}")
                        
                        # 在主对话（AI助手）中添加系统通知
                        try:
                            conversations_dir = conversation_manager.get_board_conversations_dir(board_id)
                            if conversations_dir:
                                # 查找最新的主对话（conv-开头的）
                                main_conversations = sorted(
                                    conversations_dir.glob("conv-*.json"),
                                    key=lambda x: x.stat().st_mtime,
                                    reverse=True
                                )
                                
                                if main_conversations:
                                    main_conv_file = main_conversations[0]
                                    main_conv_id = main_conv_file.stem
                                    
                                    # 准备大纲摘要（用于LLM理解）
                                    sections_summary = []
                                    for section in final_outline_data.get('outline', []):
                                        sections_summary.append({
                                            "index": section.get('section_number', len(sections_summary)),
                                            "title": section.get('title', section.get('section_title', '未命名')),
                                            "pages": [section.get('page_start'), section.get('page_end')]
                                        })
                                    
                                    # 添加系统消息
                                    system_notification = {
                                        "role": "system",
                                        "content": f"📚 用户对PDF文件《{pdf_filename}》生成了文档大纲，共{len(sections_summary)}个分段。",
                                        "timestamp": datetime.now().isoformat(),
                                        "metadata": {
                                            "type": "batch_outline_generated",
                                            "pdf_filename": pdf_filename,
                                            "window_id": window_id,
                                            "total_sections": len(sections_summary),
                                            "sections_summary": sections_summary
                                        }
                                    }
                                    
                                    conversation_manager.add_message(board_id, main_conv_id, system_notification)
                                    info(f"已向主对话添加大纲生成通知: {main_conv_id}")
                                    
                                    yield f"data: {json.dumps({'type': 'notification_added', 'conversation_id': main_conv_id}, ensure_ascii=False)}\n\n"
                                else:
                                    info("未找到主对话，跳过系统通知")
                        except Exception as e:
                            error(f"添加系统通知失败: {e}")
                        
                        yield f"data: {json.dumps({'type': 'outline', 'outline': final_outline_data}, ensure_ascii=False)}\n\n"
                    except json.JSONDecodeError as e:
                        error(f"解析最终大纲JSON失败: {e}")
                        yield f"data: {json.dumps({'type': 'error', 'error': 'JSON解析失败，请查看原始输出'}, ensure_ascii=False)}\n\n"
                
                yield f"data: {json.dumps({'type': 'done', 'success': True}, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                error(f"生成批量注释大纲失败: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_outline_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"生成批量注释大纲失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成批量注释大纲失败: {str(e)}")

@app.post("/api/boards/{board_id}/windows/{window_id}/annotations/batch/subdivide")
async def subdivide_outline_sections(
    board_id: str,
    window_id: str,
    request: Request
):
    """第二阶段：对大纲的每个分段进行细分分析（使用LLM-2）"""
    try:
        info(f"开始第二阶段：细分大纲分段 board_id={board_id}, window_id={window_id}")
        
        # 读取第一阶段生成的大纲数据
        outline_file = conversation_manager.get_board_conversations_dir(board_id) / f"outline-{window_id}-data.json"
        if not outline_file.exists():
            raise HTTPException(status_code=404, detail="未找到大纲数据，请先执行第一阶段生成大纲")
        
        with open(outline_file, 'r', encoding='utf-8') as f:
            outline_data = json.load(f)
        
        if 'outline' not in outline_data or not outline_data['outline']:
            raise HTTPException(status_code=400, detail="大纲数据为空")
        
        outline = outline_data['outline']
        total_sections = len(outline)
        info(f"读取到{total_sections}个分段，准备细分")
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        target_window = None
        for window in windows:
            if window.get('id') == window_id:
                target_window = window
                break
        
        if not target_window:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        pdf_filename = target_window.get('title', 'unknown')
        
        # 准备SSE流式响应
        async def subdivide_stream():
            try:
                import asyncio
                
                # 存储所有细分结果
                all_subdivisions = [None] * total_sections  # 预分配空间，保持顺序
                completed_count = [0]  # 使用列表以便在嵌套函数中修改
                
                # 创建队列用于收集各个分段的事件
                event_queue = asyncio.Queue()
                
                yield f"data: {json.dumps({'type': 'status', 'message': f'开始并行处理{total_sections}个分段...'}, ensure_ascii=False)}\n\n"
                
                # 定义单个分段的处理函数（完全独立）
                async def process_single_section(section_idx, section, queue):
                    try:
                        section_num = section.get('section_number', section_idx + 1)
                        section_title = section.get('title', f'分段{section_num}')
                        page_start = section.get('page_start')
                        page_end = section.get('page_end')
                        
                        await queue.put({'type': 'section_start', 'section': section_num, 'title': section_title, 'pages': f'{page_start}-{page_end}'})
                        
                        # 读取该分段所有页面的内容
                        section_pages_content = []
                        for page_num in range(page_start, page_end + 1):
                            page_content = content_manager.get_pdf_page_contents(board_id, window_id, page_num)
                            if page_content.get('current'):
                                section_pages_content.append({
                                    'page': page_num,
                                    'content': page_content['current']
                                })
                        
                        if not section_pages_content:
                            await queue.put({'type': 'warning', 'message': f'分段{section_num}无内容，跳过'})
                            return None
                        
                        # 构建该分段的完整文本
                        section_full_text = "\n\n".join([
                            f"=== 第{p['page']}页 ===\n{p['content']}"
                            for p in section_pages_content
                        ])
                        
                        # 构建给LLM-2的提示词
                        subdivision_prompt = f"""你是一位专业的文档分析助手。我需要你对以下PDF文档的一个分段进行深入分析和细分。

**文档信息**：
- 文件名: {pdf_filename}
- 当前分段: {section_title}
- 页码范围: 第{page_start}页 - 第{page_end}页

**分段内容**：
{section_full_text}

**任务要求**：
1. 仔细阅读并理解这个分段的内容
2. 生成这个分段的概括性介绍（100-200字）
3. 将这个分段进一步细分为更小的逻辑单元
4. 为每个细分单元提供：
   - 细分编号（从1开始）
   - 简洁的标题
   - 起始页码和结束页码（基于第{page_start}页到第{page_end}页的范围）
5. 如果内容无法进一步细分，则返回一个细分单元，页码范围为第{page_start}页到第{page_end}页

**输出格式**（必须严格遵守JSON格式）：
```json
{{
  "section_summary": "这个分段的概括性介绍...",
  "subdivisions": [
    {{
      "subdivision_number": 1,
      "title": "细分标题",
      "page_start": {page_start},
      "page_end": {page_start}
    }},
    {{
      "subdivision_number": 2,
      "title": "细分标题",
      "page_start": {page_start + 1},
      "page_end": {page_end}
    }}
  ]
}}
```

**提示**：
- 细分应该基于内容的逻辑结构（如：不同的知识点、概念、步骤等）
- 细分的页码范围应该在第{page_start}页到第{page_end}页之内
- 如果内容较少或逻辑统一，可以不细分（只返回一个单元）

请直接输出JSON，不要添加任何额外的说明文字或代码块标记。"""
                        
                        # 创建LLM-2对话记录
                        llm2_conv_id = f"subdivision-{window_id}-section{section_num}-2"
                        llm2_conversation = conversation_manager.get_conversation(board_id, llm2_conv_id, page=None, limit=None)
                        if not llm2_conversation:
                            llm2_conversation = conversation_manager.create_conversation(
                                board_id,
                                title=f"分段细分-{section_title} - {pdf_filename}"
                            )
                            conversations_dir = conversation_manager.get_board_conversations_dir(board_id)
                            old_file = conversations_dir / f"{llm2_conversation['id']}.json"
                            new_file = conversations_dir / f"{llm2_conv_id}.json"
                            if old_file.exists():
                                old_file.rename(new_file)
                            llm2_conversation['id'] = llm2_conv_id
                        
                        # 发送给LLM-2
                        user_message = {
                            "role": "user",
                            "content": subdivision_prompt,
                            "timestamp": datetime.now().isoformat(),
                            "metadata": {
                                "action": "subdivide_section",
                                "pdf_filename": pdf_filename,
                                "window_id": window_id,
                                "section_number": section_num,
                                "section_title": section_title,
                                "page_start": page_start,
                                "page_end": page_end,
                                "total_pages": len(section_pages_content)
                            }
                        }
                        
                        messages = [user_message]
                        accumulated_content = ""
                        
                        # 流式接收LLM-2的响应
                        async for chunk in llm_service.chat_completion(messages, stream=True):
                            if chunk:
                                accumulated_content += chunk
                                await queue.put({'type': 'section_content', 'section': section_num, 'content': chunk})
                        
                        # 保存助手消息
                        assistant_message = {
                            "role": "assistant",
                            "content": accumulated_content,
                            "timestamp": datetime.now().isoformat(),
                            "metadata": {
                                "action": "subdivide_section",
                                "section_number": section_num,
                                "content_length": len(accumulated_content)
                            }
                        }
                        
                        conversation_manager.add_message(board_id, llm2_conv_id, user_message)
                        conversation_manager.add_message(board_id, llm2_conv_id, assistant_message)
                        
                        # 解析JSON结果
                        try:
                            content = accumulated_content.strip()
                            if content.startswith('```'):
                                lines = content.split('\n')
                                content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content
                            
                            subdivision_data = json.loads(content)
                            
                            # 验证细分数据
                            if 'section_summary' in subdivision_data and 'subdivisions' in subdivision_data:
                                subdivision_result = {
                                    'section_number': section_num,
                                    'section_title': section_title,
                                    'page_start': page_start,
                                    'page_end': page_end,
                                    'section_summary': subdivision_data['section_summary'],
                                    'subdivisions': subdivision_data['subdivisions']
                                }
                                
                                # 保存到对应位置
                                all_subdivisions[section_idx] = subdivision_result
                                completed_count[0] += 1
                                
                                await queue.put({'type': 'section_done', 'section': section_num, 'subdivision': subdivision_data, 'completed': completed_count[0], 'total': total_sections})
                                info(f"分段{section_num}细分完成，共{len(subdivision_data['subdivisions'])}个细分单元")
                            else:
                                await queue.put({'type': 'warning', 'message': f'分段{section_num}返回数据格式错误'})
                        
                        except json.JSONDecodeError as e:
                            error(f"解析分段{section_num}细分JSON失败: {e}")
                            await queue.put({'type': 'error', 'message': f'分段{section_num}解析失败'})
                    
                    except Exception as e:
                        error(f"处理分段{section_num}失败: {e}")
                        await queue.put({'type': 'error', 'message': f'分段{section_num}处理失败: {str(e)}'})
                
                # 启动所有分段的并行处理任务
                tasks = []
                for section_idx, section in enumerate(outline):
                    task = asyncio.create_task(process_single_section(section_idx, section, event_queue))
                    tasks.append(task)
                
                info(f"已启动{len(tasks)}个并行任务")
                
                # 创建一个任务来等待所有处理完成
                async def wait_for_completion():
                    await asyncio.gather(*tasks, return_exceptions=True)
                    await event_queue.put({'type': '_all_done'})  # 发送结束信号
                
                completion_task = asyncio.create_task(wait_for_completion())
                
                # 从队列中读取事件并yield
                while True:
                    event = await event_queue.get()
                    
                    if event['type'] == '_all_done':
                        break
                    
                    # 转发事件给客户端
                    yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
                
                # 等待完成任务结束
                await completion_task
                
                # 保存所有细分结果（保留None值以保持索引对应，但记录失败的分段）
                failed_sections = []
                for idx, subdiv in enumerate(all_subdivisions):
                    if subdiv is None:
                        failed_sections.append({
                            'section_index': idx,
                            'section_number': outline[idx].get('section_number', idx + 1),
                            'section_title': outline[idx].get('title', f'分段{idx+1}')
                        })
                
                valid_count = sum(1 for s in all_subdivisions if s is not None)
                
                subdivision_file = conversation_manager.get_board_conversations_dir(board_id) / f"subdivisions-{window_id}-data.json"
                subdivision_complete_data = {
                    'pdf_filename': pdf_filename,
                    'window_id': window_id,
                    'board_id': board_id,
                    'total_sections': total_sections,
                    'completed_sections': valid_count,
                    'failed_sections': failed_sections,
                    'subdivisions': all_subdivisions,  # 保留所有元素，包括None
                    'created_at': datetime.now().isoformat()
                }
                
                with open(subdivision_file, 'w', encoding='utf-8') as f:
                    json.dump(subdivision_complete_data, f, ensure_ascii=False, indent=2)
                
                info(f"所有细分结果已保存: {subdivision_file}")
                
                yield f"data: {json.dumps({'type': 'complete', 'data': subdivision_complete_data}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'success': True}, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                error(f"细分处理失败: {e}")
                import traceback
                error(f"详细错误: {traceback.format_exc()}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            subdivide_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"细分大纲分段失败: {e}")
        raise HTTPException(status_code=500, detail=f"细分大纲分段失败: {str(e)}")

@app.post("/api/boards/{board_id}/windows/{window_id}/annotations/batch/generate-section")
async def generate_section_annotations(
    board_id: str,
    window_id: str,
    request: Request
):
    """为一个分段的所有页面生成注释"""
    try:
        request_body = await request.json()
        section_index = request_body.get('section_index')
        section_data = request_body.get('section_data')
        subdivision_data = request_body.get('subdivision_data')
        annotation_style = request_body.get('annotation_style', 'detailed')
        prompt_template = request_body.get('promptTemplate', '')  # 与单页注释API保持一致
        
        info(f"开始为分段 {section_index} 生成注释")
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        target_window = None
        for window in windows:
            if window['id'] == window_id:
                target_window = window
                break
        
        if not target_window:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        # 获取PDF文件名
        pdf_path = Path(target_window['content'])
        pdf_filename = pdf_path.stem + pdf_path.suffix
        
        page_start = section_data['page_start']
        page_end = section_data['page_end']
        
        async def generate_stream():
            try:
                info(f"generate_stream 开始执行，分段索引: {section_index}")
                yield f"data: {json.dumps({'type': 'status', 'message': f'正在为分段 {section_index + 1} 生成注释...'}, ensure_ascii=False)}\n\n"
                
                # 读取该分段所有页面的内容
                info(f"开始读取页面内容，范围: {page_start} - {page_end}")
                pages_content = []
                for page in range(page_start, page_end + 1):
                    page_data = content_manager.get_pdf_page_contents(board_id, window_id, page)
                    info(f"读取第{page}页，是否有内容: {bool(page_data and page_data.get('current'))}")
                    if page_data and page_data.get('current'):
                        pages_content.append({
                            'page': page,
                            'content': page_data['current']
                        })
                
                info(f"共读取到 {len(pages_content)} 页内容")
                
                if not pages_content:
                    error_msg = f'未找到分段内容，页码范围: {page_start}-{page_end}'
                    error(error_msg)
                    yield f"data: {json.dumps({'type': 'error', 'error': error_msg}, ensure_ascii=False)}\n\n"
                    return
                
                # 构建完整的内容文本
                full_content = ""
                for page_info in pages_content:
                    full_content += f"\n\n=== 第{page_info['page']}页 ===\n{page_info['content']}"
                
                # 获取分段描述
                section_description = subdivision_data.get('section_summary') or section_data.get('description') or ''
                
                # 构建注释要求（使用prompt_template作为用户的注释风格要求）
                if prompt_template:
                    # 用户配置了提示词模板，直接使用
                    annotation_requirement = prompt_template
                else:
                    # 没有配置提示词，使用默认要求
                    annotation_requirement = "请为每一页生成注释，包括：\n1. 页面主要内容概要\n2. 重要知识点\n3. 需要注意的细节"
                
                prompt = f"""你是一个专业的文档注释助手。我需要你为PDF文档的一个分段生成逐页注释。

**分段信息**：
- 分段编号: {section_data.get('section_number', section_index + 1)}
- 分段标题: {section_data.get('title', '未命名')}
- 分段描述: {section_description}
- 页码范围: 第{page_start}页 - 第{page_end}页

**分段完整内容**：
{full_content}

**注释要求**：
{annotation_requirement}

**输出格式**（必须严格遵守JSON格式）：
```json
{{
  "annotations": [
    {{
      "page": {page_start},
      "annotation": "第{page_start}页的注释内容..."
    }},
    {{
      "page": {page_start + 1},
      "annotation": "第{page_start + 1}页的注释内容..."
    }}
  ]
}}
```

请为第{page_start}页到第{page_end}页的每一页都生成注释，确保annotations数组包含所有页面。
每页注释请用Markdown格式输出。
直接输出JSON，不要添加任何额外的说明文字或代码块标记。"""
                
                # 创建或获取LLM对话
                annotation_conv = conversation_manager.create_conversation(
                    board_id,
                    title=f"批量注释-分段{section_index + 1} - {pdf_filename}"
                )
                annotation_conv_id = annotation_conv['id']
                
                # 重命名对话文件
                conversations_dir = conversation_manager.get_board_conversations_dir(board_id)
                old_file = conversations_dir / f"{annotation_conv_id}.json"
                new_filename = f"annotation-{window_id}-section{section_index}.json"
                new_file = conversations_dir / new_filename
                
                if old_file.exists():
                    old_file.rename(new_file)
                    annotation_conv_id = new_filename.replace('.json', '')
                    info(f"注释对话文件已重命名: {new_filename}")
                
                # 创建LLM对话消息
                user_message = {
                    "role": "user",
                    "content": prompt,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "action": "generate_section_annotations",
                        "pdf_filename": pdf_filename,
                        "window_id": window_id,
                        "section_index": section_index,
                        "page_start": page_start,
                        "page_end": page_end,
                        "annotation_style": annotation_style
                    }
                }
                
                messages = [user_message]
                accumulated_content = ""
                
                # 调用LLM
                info(f"开始调用LLM生成分段注释，页码范围: {page_start}-{page_end}")
                async for chunk in llm_service.chat_completion(messages, stream=True):
                    if chunk:
                        accumulated_content += chunk
                        yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
                
                info(f"LLM生成完成，返回内容长度: {len(accumulated_content)}")
                
                # 保存助手消息
                assistant_message = {
                    "role": "assistant",
                    "content": accumulated_content,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "action": "generate_section_annotations",
                        "section_index": section_index,
                        "page_range": f"{page_start}-{page_end}"
                    }
                }
                
                conversation_manager.add_message(board_id, annotation_conv_id, user_message)
                conversation_manager.add_message(board_id, annotation_conv_id, assistant_message)
                info(f"注释对话已保存: {annotation_conv_id}")
                
                # 解析JSON结果
                try:
                    content = accumulated_content.strip()
                    if content.startswith('```'):
                        lines = content.split('\n')
                        content = '\n'.join(lines[1:-1]) if len(lines) > 2 else content
                    
                    result_data = json.loads(content)
                    annotations = result_data.get('annotations', [])
                    
                    # 保存每一页的注释
                    completed_pages = 0
                    for ann in annotations:
                        page_num = ann.get('page')
                        annotation_content = ann.get('annotation', '')
                        
                        if page_num and annotation_content:
                            # 添加生成时间戳和分段标记
                            section_title = section_data.get('title', f'分段{section_index + 1}')
                            page_range = f"{section_data.get('page_start', '?')}-{section_data.get('page_end', '?')}"
                            timestamped_content = f"<!-- 批量生成的注释 - 分段{section_index}: {section_title} (页{page_range}) - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -->\n\n{annotation_content}"
                            
                            # 保存注释到临时文件（用于后续融合）
                            temp_annotations_dir = conversation_manager.get_board_conversations_dir(board_id) / "temp_annotations" / window_id
                            temp_annotations_dir.mkdir(parents=True, exist_ok=True)
                            temp_file = temp_annotations_dir / f"page_{page_num}_section_{section_index}.md"
                            with open(temp_file, 'w', encoding='utf-8') as f:
                                f.write(timestamped_content)
                            
                            # 保存注释到正式位置（可能会被覆盖）
                            save_success = content_manager.save_pdf_annotation(board_id, window_id, page_num, timestamped_content)
                            
                            if save_success:
                                completed_pages += 1
                                yield f"data: {json.dumps({'type': 'page_done', 'page': page_num, 'completed': completed_pages, 'total': len(annotations), 'annotation': timestamped_content}, ensure_ascii=False)}\n\n"
                    
                    # 在主对话（AI助手）中添加系统通知
                    try:
                        conversations_dir = conversation_manager.get_board_conversations_dir(board_id)
                        if conversations_dir:
                            # 查找最新的主对话（conv-开头的）
                            main_conversations = sorted(
                                conversations_dir.glob("conv-*.json"),
                                key=lambda x: x.stat().st_mtime,
                                reverse=True
                            )
                            
                            if main_conversations:
                                main_conv_file = main_conversations[0]
                                main_conv_id = main_conv_file.stem
                                
                                # 获取分段信息
                                section_title = section_data.get('title', section_data.get('section_title', '未命名分段'))
                                section_description = subdivision_data.get('section_summary') or section_data.get('description', '')
                                section_num = section_data.get('section_number', section_index + 1)
                                
                                # 添加系统消息
                                system_notification = {
                                    "role": "system",
                                    "content": f"⚡ 用户对PDF文件《{pdf_filename}》的第{section_num}分段「{section_title}」（第{page_start}-{page_end}页）生成了注释。",
                                    "timestamp": datetime.now().isoformat(),
                                    "metadata": {
                                        "type": "batch_section_annotation_generated",
                                        "pdf_filename": pdf_filename,
                                        "window_id": window_id,
                                        "section_index": section_index,
                                        "section_number": section_num,
                                        "section_title": section_title,
                                        "section_summary": section_description,
                                        "page_range": [page_start, page_end],
                                        "annotation_count": completed_pages
                                    }
                                }
                                
                                conversation_manager.add_message(board_id, main_conv_id, system_notification)
                                info(f"已向主对话添加分段注释生成通知: {main_conv_id}")
                                
                                yield f"data: {json.dumps({'type': 'notification_added', 'conversation_id': main_conv_id}, ensure_ascii=False)}\n\n"
                            else:
                                info("未找到主对话，跳过系统通知")
                    except Exception as e:
                        error(f"添加系统通知失败: {e}")
                    
                    yield f"data: {json.dumps({'type': 'complete', 'completed_pages': completed_pages, 'total_pages': len(annotations)}, ensure_ascii=False)}\n\n"
                    
                except json.JSONDecodeError as e:
                    error(f"解析注释JSON失败: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'error': f'解析结果失败: {str(e)}'}, ensure_ascii=False)}\n\n"
                    
            except Exception as e:
                error(f"生成分段注释失败: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"生成分段注释失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成分段注释失败: {str(e)}")

@app.post("/api/boards/{board_id}/windows/{window_id}/annotations/batch/merge-overlapping")
async def merge_overlapping_annotations(
    board_id: str,
    window_id: str,
    request: Request
):
    """第四阶段：融合重叠页面的注释"""
    try:
        info(f"开始第四阶段：融合重叠页面注释 board_id={board_id}, window_id={window_id}")
        
        # 读取大纲数据获取重叠页面信息
        outline_file = conversation_manager.get_board_conversations_dir(board_id) / f"outline-{window_id}-data.json"
        if not outline_file.exists():
            raise HTTPException(status_code=404, detail="未找到大纲数据")
        
        with open(outline_file, 'r', encoding='utf-8') as f:
            outline_data = json.load(f)
        
        overlapping_pages = outline_data.get('page_analysis', {}).get('overlapping_pages', {})
        
        if not overlapping_pages:
            info("没有重叠页面，跳过融合")
            return {
                'success': True,
                'merged_pages': 0,
                'message': '没有需要融合的重叠页面'
            }
        
        # 创建融合对话记录
        merge_conv = conversation_manager.create_conversation(
            board_id,
            title=f"注释融合 - {window_id}"
        )
        merge_conv_id = f"annotation-{window_id}-merge4"
        
        # 重命名对话文件
        conversations_dir = conversation_manager.get_board_conversations_dir(board_id)
        old_file = conversations_dir / f"{merge_conv['id']}.json"
        new_file = conversations_dir / f"{merge_conv_id}.json"
        if old_file.exists():
            old_file.rename(new_file)
        
        # 准备SSE流式响应
        async def merge_stream():
            try:
                temp_annotations_dir = conversations_dir / "temp_annotations" / window_id
                total_overlapping = len(overlapping_pages)
                completed = 0
                
                yield f"data: {json.dumps({'type': 'status', 'message': f'开始融合{total_overlapping}个重叠页面...'}, ensure_ascii=False)}\n\n"
                
                for page_num_str, section_indices in overlapping_pages.items():
                    page_num = int(page_num_str)
                    
                    info(f"融合第{page_num}页，涉及{len(section_indices)}个分段")
                    
                    # 收集该页面所有分段的注释
                    annotations_parts = []
                    for section_idx in section_indices:
                        temp_file = temp_annotations_dir / f"page_{page_num}_section_{section_idx}.md"
                        if temp_file.exists():
                            with open(temp_file, 'r', encoding='utf-8') as f:
                                content = f.read()
                                annotations_parts.append({
                                    'section_index': section_idx,
                                    'content': content
                                })
                    
                    if len(annotations_parts) > 1:
                        # 构建融合后的注释
                        merged_content = f"<!-- 融合注释 - 第{page_num}页 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} -->\n"
                        merged_content += f"<!-- 此页面在{len(annotations_parts)}个分段中出现，注释已自动融合 -->\n\n"
                        
                        for i, part in enumerate(annotations_parts, 1):
                            section_idx = part['section_index']
                            section_info = outline_data['outline'][section_idx]
                            section_title = section_info.get('title', f'分段{section_idx + 1}')
                            
                            merged_content += f"## 视角{i}：{section_title}\n\n"
                            
                            # 移除原有的注释头部
                            content = part['content']
                            if content.startswith('<!--'):
                                content_lines = content.split('\n')
                                content = '\n'.join(content_lines[1:]).strip()
                            
                            merged_content += content + "\n\n"
                            
                            if i < len(annotations_parts):
                                merged_content += "---\n\n"
                        
                        # 保存融合后的注释
                        save_success = content_manager.save_pdf_annotation(board_id, window_id, page_num, merged_content)
                        
                        if save_success:
                            completed += 1
                            info(f"第{page_num}页融合完成 ({completed}/{total_overlapping})")
                            yield f"data: {json.dumps({'type': 'merge_done', 'page': page_num, 'completed': completed, 'total': total_overlapping, 'sections_count': len(annotations_parts)}, ensure_ascii=False)}\n\n"
                    else:
                        # 只有一个分段，无需融合
                        completed += 1
                        yield f"data: {json.dumps({'type': 'merge_skip', 'page': page_num, 'completed': completed, 'total': total_overlapping}, ensure_ascii=False)}\n\n"
                
                # 清理临时文件
                if temp_annotations_dir.exists():
                    import shutil
                    shutil.rmtree(temp_annotations_dir)
                    info(f"已清理临时注释文件: {temp_annotations_dir}")
                
                # 保存融合日志到对话
                merge_log = {
                    "role": "assistant",
                    "content": f"融合完成：共处理{total_overlapping}个重叠页面",
                    "timestamp": datetime.now().isoformat(),
                    "metadata": {
                        "action": "merge_overlapping_annotations",
                        "window_id": window_id,
                        "total_overlapping": total_overlapping,
                        "completed": completed
                    }
                }
                conversation_manager.add_message(board_id, merge_conv_id, merge_log)
                
                yield f"data: {json.dumps({'type': 'complete', 'merged_pages': completed, 'total_pages': total_overlapping}, ensure_ascii=False)}\n\n"
                yield f"data: {json.dumps({'type': 'done', 'success': True}, ensure_ascii=False)}\n\n"
                
            except Exception as e:
                error(f"融合注释失败: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            merge_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"融合重叠页注释失败: {e}")
        raise HTTPException(status_code=500, detail=f"融合重叠页注释失败: {str(e)}")

@app.get("/api/boards/{board_id}/windows/{window_id}/annotations/batch/outline-data")
async def get_outline_data(board_id: str, window_id: str):
    """获取已保存的大纲数据"""
    try:
        outline_file = conversation_manager.get_board_conversations_dir(board_id) / f"outline-{window_id}-data.json"
        
        if not outline_file.exists():
            raise HTTPException(status_code=404, detail="大纲数据不存在")
        
        with open(outline_file, 'r', encoding='utf-8') as f:
            outline_data = json.load(f)
        
        return outline_data
    except HTTPException:
        raise
    except Exception as e:
        error(f"加载大纲数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"加载大纲数据失败: {str(e)}")

@app.get("/api/boards/{board_id}/windows/{window_id}/annotations/batch/subdivision-data")
async def get_subdivision_data(board_id: str, window_id: str):
    """获取已保存的细分数据"""
    try:
        subdivision_file = conversation_manager.get_board_conversations_dir(board_id) / f"subdivisions-{window_id}-data.json"
        
        if not subdivision_file.exists():
            raise HTTPException(status_code=404, detail="细分数据不存在")
        
        with open(subdivision_file, 'r', encoding='utf-8') as f:
            subdivision_data = json.load(f)
        
        return subdivision_data
    except HTTPException:
        raise
    except Exception as e:
        error(f"加载细分数据失败: {e}")
        raise HTTPException(status_code=500, detail=f"加载细分数据失败: {str(e)}")

@app.post("/api/boards/{board_id}/windows/{window_id}/annotations/semantic-search")
async def semantic_search_annotations(
    board_id: str,
    window_id: str,
    request: Request
):
    """基于LLM的语义搜索"""
    try:
        body = await request.json()
        query = body.get('query', '')
        pdf_url = body.get('pdf_url', '')
        
        if not query.strip():
            raise HTTPException(status_code=400, detail="搜索查询不能为空")
        
        # 获取PDF文件名
        pdf_filename = pdf_url.split('/')[-1] if pdf_url else None
        if not pdf_filename:
            raise HTTPException(status_code=400, detail="无效的PDF URL")
        
        # 读取大纲和细分数据
        outline_file = conversation_manager.get_board_conversations_dir(board_id) / f"outline-{window_id}-data.json"
        subdivision_file = conversation_manager.get_board_conversations_dir(board_id) / f"subdivisions-{window_id}-data.json"
        
        if not outline_file.exists() or not subdivision_file.exists():
            raise HTTPException(status_code=404, detail="大纲或细分数据不存在，请先生成大纲")
        
        with open(outline_file, 'r', encoding='utf-8') as f:
            outline_data = json.load(f)
        
        with open(subdivision_file, 'r', encoding='utf-8') as f:
            subdivision_data = json.load(f)
        
        # 构建合并的大纲结构（大纲 + 细分）
        merged_outline = []
        for i, section in enumerate(outline_data.get('outline', [])):
            section_item = {
                "section_number": section.get('section_number', i + 1),
                "section_title": section.get('section_title', ''),
                "section_pages": [section.get('page_start'), section.get('page_end')],
                "subdivisions": []
            }
            
            # 添加对应的细分数据
            if i < len(subdivision_data.get('subdivisions', [])):
                subdivisions = subdivision_data['subdivisions'][i]
                if subdivisions:
                    for subdiv in subdivisions.get('subdivisions', []):
                        subdiv_item = {
                            "subdivision_title": subdiv.get('title', ''),
                            "subdivision_description": subdiv.get('description', ''),
                            "subdivision_pages": [subdiv.get('page_start'), subdiv.get('page_end')],
                            "parts": []
                        }
                        
                        # 添加部分（如果有）
                        for part in subdiv.get('parts', []):
                            part_item = {
                                "part_name": part.get('name', ''),
                                "part_pages": part.get('pages', [])
                            }
                            subdiv_item['parts'].append(part_item)
                        
                        section_item['subdivisions'].append(subdiv_item)
            
            merged_outline.append(section_item)
        
        # 保存合并后的大纲结构到文件（用于缓存）
        merged_file = conversation_manager.get_board_conversations_dir(board_id) / f"outline_with_subdivisions-{window_id}.json"
        with open(merged_file, 'w', encoding='utf-8') as f:
            json.dump(merged_outline, f, ensure_ascii=False, indent=2)
        
        # 构建LLM提示词
        prompt = f"""你是一个文档导航助手。用户想在PDF文档中查找特定内容。

文档结构：
{json.dumps(merged_outline, ensure_ascii=False, indent=2)}

用户查询：{query}

请分析用户需求，返回最相关的部分（parts）或细分（subdivisions）。
返回JSON格式：
{{
  "results": [
    {{
      "part_name": "部分名称",
      "subdivision_title": "细分标题",
      "section_title": "分段标题",
      "pages": [起始页, 结束页],
      "relevance": "相关性说明"
    }}
  ]
}}

注意：
1. 优先返回最相关的parts，如果没有parts则返回subdivisions
2. 按相关性从高到低排序
3. 最多返回5个结果
4. pages必须是数组格式，包含起止页码
"""

        # 调用LLM API
        api_config = api_config_manager.get_config()
        current_provider = api_config.get('current_provider', 'openai')
        provider_config = api_config.get('providers', {}).get(current_provider, {})
        
        if not provider_config.get('apiKey'):
            raise HTTPException(status_code=400, detail="LLM API未配置")
        
        info(f"语义搜索 - 用户查询: {query}")
        info(f"使用LLM服务商: {current_provider}")
        
        # 使用全局的LLM服务（已经初始化好的）
        # 注意：不要创建新实例，使用已有的全局实例
        
        messages = [
            {"role": "system", "content": "你是一个专业的文档导航助手，擅长理解用户的语义需求并找到文档中最相关的内容。"},
            {"role": "user", "content": prompt}
        ]
        
        # 调用LLM（非流式，收集完整响应）
        info("开始调用LLM进行语义搜索...")
        response_text = ""
        async for chunk in llm_service.chat_completion(messages, stream=True):
            if chunk:
                response_text += chunk
        
        info(f"LLM返回的原始响应长度: {len(response_text)}")
        
        # 解析LLM返回的JSON
        try:
            # 尝试提取JSON（可能包含在markdown代码块中）
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                json_text = response_text[json_start:json_end].strip()
            else:
                json_text = response_text.strip()
            
            result_data = json.loads(json_text)
            results = result_data.get('results', [])
            
        except json.JSONDecodeError as e:
            error(f"LLM返回的JSON解析失败: {e}\n原始响应: {response_text}")
            # 返回空结果而不是报错
            results = []
        
        return {
            "success": True,
            "query": query,
            "results": results
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"语义搜索失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"语义搜索失败: {str(e)}")

@app.get("/api/media/serve")
async def serve_media_file(path: str):
    """全新的媒体文件服务API - 避免路由冲突"""
    try:
        print(f"媒体服务请求: path={path}")
        
        # 直接使用传入的绝对路径
        file_path = Path(path)
        
        # 基本验证：文件必须存在且是文件
        if not file_path.exists():
            print(f"文件不存在: {file_path}")
            raise HTTPException(status_code=404, detail="文件不存在")
        
        if not file_path.is_file():
            print(f"路径不是文件: {file_path}")
            raise HTTPException(status_code=400, detail="路径不是文件")
        
        # 获取MIME类型
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if not mime_type:
            mime_type = 'application/octet-stream'
        
        print(f"返回媒体文件: {file_path.name}, MIME: {mime_type}")
        
        # 直接返回文件
        return FileResponse(
            path=str(file_path),
            media_type=mime_type,
            filename=file_path.name
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"媒体服务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 获取展板文件列表API
@app.get("/api/boards/{board_id}/files")
async def get_board_files(board_id: str):
    """获取展板的所有文件列表（用于聊天发送）"""
    try:
        # 获取展板目录
        board_dir = None
        for course_dir in file_manager.courses_dir.iterdir():
            if course_dir.is_dir():
                potential_board_dir = course_dir / board_id
                if potential_board_dir.exists():
                    board_dir = potential_board_dir
                    break
        
        if not board_dir:
            raise HTTPException(status_code=404, detail="展板不存在")
        
        files_dir = board_dir / "files"
        if not files_dir.exists():
            return {"files": []}
        
        files_list = []
        file_types = ["images", "videos", "pdfs", "audios", "texts"]
        
        # 扫描标准文件类型目录
        for file_type in file_types:
            type_dir = files_dir / file_type
            if type_dir.exists():
                for file_path in type_dir.iterdir():
                    if file_path.is_file() and not file_path.name.startswith('.'):
                        # 获取文件信息
                        file_stat = file_path.stat()
                        file_info = {
                            "name": file_path.name,
                            "type": file_type,
                            "size": file_stat.st_size,
                            "modified": file_stat.st_mtime,
                            "path": str(file_path),
                            "url": f"http://{API_HOST}:{API_PORT}/api/media/serve?path={str(file_path)}"
                        }
                        files_list.append(file_info)
        
        # 也扫描files目录下的直接文件（兼容旧格式）
        for file_path in files_dir.iterdir():
            if file_path.is_file() and not file_path.name.startswith('.') and not file_path.name.endswith('.json'):
                # 根据文件扩展名判断类型
                file_ext = file_path.suffix.lower()
                file_type = "texts"  # 默认类型
                if file_ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']:
                    file_type = "images"
                elif file_ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm']:
                    file_type = "videos"
                elif file_ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg']:
                    file_type = "audios"
                elif file_ext in ['.pdf']:
                    file_type = "pdfs"
                elif file_ext in ['.txt', '.md', '.doc', '.docx']:
                    file_type = "texts"
                
                file_stat = file_path.stat()
                file_info = {
                    "name": file_path.name,
                    "type": file_type,
                    "size": file_stat.st_size,
                    "modified": file_stat.st_mtime,
                    "path": str(file_path),
                    "url": f"http://{API_HOST}:{API_PORT}/api/media/serve?path={str(file_path)}"
                }
                files_list.append(file_info)
        
        # 按修改时间倒序排列
        files_list.sort(key=lambda x: x["modified"], reverse=True)
        
        return {"files": files_list}
    except Exception as e:
        error(f"获取展板文件列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# API配置管理端点
@app.get("/api/llm/config")
async def get_api_config():
    """获取LLM API配置"""
    try:
        config = api_config_manager.get_config()
        # 不返回敏感的API密钥，只返回是否已配置
        safe_config = {
            "current_provider": config.get("current_provider", "openai"),
            "providers": {}
        }
        
        for provider, provider_config in config.get("providers", {}).items():
            safe_config["providers"][provider] = {
                "model": provider_config.get("model", ""),
                "baseUrl": provider_config.get("baseUrl", ""),
                "apiKey": "***" if provider_config.get("apiKey", "").strip() else "",
                "configured": bool(provider_config.get("apiKey", "").strip())
            }
        
        return safe_config
    except Exception as e:
        error(f"获取API配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/llm/config/{provider}")
async def update_provider_config(provider: str, config: dict):
    """更新指定服务商的配置"""
    try:
        # 验证服务商
        valid_providers = ["openai", "anthropic", "gemini", "qwen"]
        if provider not in valid_providers:
            raise HTTPException(status_code=400, detail="不支持的服务商")
        
        # 更新配置
        success = api_config_manager.update_config(provider, config)
        if not success:
            raise HTTPException(status_code=500, detail="更新配置失败")
        
        info(f"更新API配置成功: {provider}")
        return {"success": True, "message": "配置更新成功"}
    except HTTPException:
        raise
    except Exception as e:
        error(f"更新API配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/llm/provider/{provider}")
async def set_current_provider(provider: str):
    """设置当前使用的服务商"""
    try:
        # 验证服务商
        valid_providers = ["openai", "anthropic", "gemini", "qwen"]
        if provider not in valid_providers:
            raise HTTPException(status_code=400, detail="不支持的服务商")
        
        # 设置当前服务商
        success = api_config_manager.set_current_provider(provider)
        if not success:
            raise HTTPException(status_code=500, detail="设置服务商失败")
        
        info(f"设置当前服务商成功: {provider}")
        return {"success": True, "current_provider": provider}
    except HTTPException:
        raise
    except Exception as e:
        error(f"设置服务商失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# LLM对话API端点
@app.post("/api/llm/chat")
async def llm_chat_completion(request: dict):
    """LLM对话补全API"""
    try:
        messages = request.get('messages', [])
        if not messages:
            raise HTTPException(status_code=400, detail="消息列表不能为空")
        
        # 使用流式响应
        async def generate_response():
            async for chunk in llm_service.chat_completion(messages, stream=True):
                # 使用Server-Sent Events格式
                yield f"data: {json.dumps({'content': chunk}, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/plain",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"LLM对话失败: {e}")
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
                    "timestamp": time.time()
                }
                await manager.broadcast(json.dumps(response, ensure_ascii=False))
            except json.JSONDecodeError:
                await websocket.send_text("无效的JSON格式")
    except WebSocketDisconnect:
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

# ==================== LLM对话相关API ====================

@app.get("/api/boards/{board_id}/conversations")
async def get_board_conversations(board_id: str):
    """获取展板的所有对话记录"""
    try:
        conversations = conversation_manager.get_board_conversations(board_id)
        return {"conversations": conversations}
    except Exception as e:
        error(f"获取展板对话记录失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/boards/{board_id}/conversations")
async def create_conversation(board_id: str, title: str = ""):
    """创建新的对话记录"""
    try:
        conversation = conversation_manager.create_conversation(board_id, title)
        info(f"创建对话成功: {conversation['id']}")
        return conversation
    except Exception as e:
        error(f"创建对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/boards/{board_id}/conversations/{conversation_id}")
async def get_conversation(board_id: str, conversation_id: str, page: int = 0, limit: int = 20):
    """获取指定对话记录，支持分页"""
    try:
        conversation = conversation_manager.get_conversation(board_id, conversation_id, page=page, limit=limit)
        if not conversation:
            raise HTTPException(status_code=404, detail="对话不存在")
        return conversation
    except HTTPException:
        raise
    except Exception as e:
        error(f"获取对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/boards/{board_id}/conversations/{conversation_id}/messages")
async def add_message(board_id: str, conversation_id: str, message: Dict):
    """向对话中添加消息"""
    try:
        success = conversation_manager.add_message(board_id, conversation_id, message)
        if not success:
            raise HTTPException(status_code=404, detail="对话不存在")
        info(f"添加消息成功: {conversation_id}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        error(f"添加消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/boards/{board_id}/conversations/{conversation_id}/title")
async def update_conversation_title(board_id: str, conversation_id: str, title: str):
    """更新对话标题"""
    try:
        success = conversation_manager.update_conversation_title(board_id, conversation_id, title)
        if not success:
            raise HTTPException(status_code=404, detail="对话不存在")
        info(f"更新对话标题成功: {conversation_id}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        error(f"更新对话标题失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/api/boards/{board_id}/conversations/{conversation_id}")
async def delete_conversation(board_id: str, conversation_id: str):
    """删除对话记录"""
    try:
        success = conversation_manager.delete_conversation(board_id, conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail="对话不存在")
        info(f"删除对话成功: {conversation_id}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        error(f"删除对话失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/boards/{board_id}/conversations/{conversation_id}/context")
async def get_conversation_context(board_id: str, conversation_id: str, limit: int = 50):
    """获取对话上下文（用于LLM调用）"""
    try:
        context = conversation_manager.get_conversation_context(board_id, conversation_id, limit)
        return {"context": context}
    except Exception as e:
        error(f"获取对话上下文失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# OCR相关API
# ============================================================================

from pydantic import BaseModel

class TextSourceSelection(BaseModel):
    """文字来源选择请求"""
    page_number: int
    source: str  # 'extracted' 或 'ocr'


@app.get("/api/boards/{board_id}/windows/{window_id}/all-pages-text")
async def get_all_pages_text(board_id: str, window_id: str):
    """
    获取所有页面的文字数据（提取+OCR+当前使用）
    """
    from ocr_service import extract_text_from_page
    import fitz
    
    try:
        info(f"🔍 OCR API调用: board_id={board_id}, window_id={window_id}")
        
        # 通过content_manager获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        info(f"📋 获取到{len(windows)}个窗口")
        
        window_data = next((w for w in windows if w['id'] == window_id), None)
        
        if not window_data:
            error(f"❌ 窗口不存在: {window_id}")
            raise HTTPException(status_code=404, detail=f"窗口不存在: {window_id}")
        
        info(f"✅ 找到窗口: {window_data.get('title', 'Untitled')}")
        
        pdf_path = window_data.get('content')
        if not pdf_path:
            error(f"❌ 窗口没有关联的PDF文件")
            raise HTTPException(status_code=404, detail="窗口没有关联的PDF文件")
        
        info(f"📄 PDF路径: {pdf_path}")
        
        if not os.path.exists(pdf_path):
            error(f"❌ PDF文件不存在: {pdf_path}")
            raise HTTPException(status_code=404, detail=f"PDF文件不存在: {pdf_path}")
        
        # 构建pages目录路径
        pdf_filename = os.path.splitext(os.path.basename(pdf_path))[0]
        files_dir = os.path.dirname(pdf_path)
        pages_dir = os.path.join(files_dir, 'pages')
        
        # 确保pages目录存在
        os.makedirs(pages_dir, exist_ok=True)
        
        # 获取PDF总页数
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        doc.close()
        
        # 如果还没有提取过文字，先提取所有页面
        first_page_file = os.path.join(pages_dir, 'page_1_extracted.json')
        if not os.path.exists(first_page_file):
            info(f"首次访问，开始提取所有页面文字...")
            for page_num in range(1, total_pages + 1):
                extracted = extract_text_from_page(pdf_path, page_num)
                extracted_file = os.path.join(pages_dir, f'page_{page_num}_extracted.json')
                with open(extracted_file, 'w', encoding='utf-8') as f:
                    json.dump(extracted, f, ensure_ascii=False, indent=2)
            info(f"✅ 提取完成: {total_pages}页")
        
        # 加载所有页面数据
        pages_data = {}
        
        for page_num in range(1, total_pages + 1):
            extracted_file = os.path.join(pages_dir, f'page_{page_num}_extracted.json')
            ocr_file = os.path.join(pages_dir, f'page_{page_num}_ocr.json')
            active_file = os.path.join(pages_dir, f'page_{page_num}_active.txt')
            
            # 加载提取结果
            extracted = {}
            if os.path.exists(extracted_file):
                with open(extracted_file, 'r', encoding='utf-8') as f:
                    extracted = json.load(f)
            
            # 加载OCR结果
            ocr = None
            if os.path.exists(ocr_file):
                with open(ocr_file, 'r', encoding='utf-8') as f:
                    ocr = json.load(f)
            
            # 加载当前使用的版本
            active = 'extracted'
            if os.path.exists(active_file):
                with open(active_file, 'r', encoding='utf-8') as f:
                    active = f.read().strip()
            elif ocr:
                active = 'ocr'  # 如果有OCR结果且没有指定，默认使用OCR
            
            pages_data[page_num] = {
                'extracted': extracted,
                'ocr': ocr,
                'active': active
            }
        
        return {
            'total_pages': total_pages,
            'pages': pages_data
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"获取页面文字数据失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取页面文字数据失败: {str(e)}")


@app.get("/api/boards/{board_id}/windows/{window_id}/ocr-batch")
async def ocr_batch_pages(board_id: str, window_id: str, pages: str):
    """
    批量OCR指定页面（SSE流式返回）
    
    Args:
        pages: 逗号分隔的页码字符串，例如 "1,3,5,10"
    """
    from ocr_service import ocr_page_image
    
    async def generate():
        try:
            page_numbers = [int(p.strip()) for p in pages.split(',')]
            
            # 通过content_manager获取窗口信息
            windows = content_manager.get_board_windows(board_id)
            window_data = next((w for w in windows if w['id'] == window_id), None)
            
            if not window_data:
                yield f"data: {json.dumps({'type': 'error', 'message': '窗口不存在'})}\n\n"
                return
            
            pdf_path = window_data.get('content')
            if not pdf_path or not os.path.exists(pdf_path):
                yield f"data: {json.dumps({'type': 'error', 'message': 'PDF文件不存在'})}\n\n"
                return
            
            # 构建pages目录路径
            files_dir = os.path.dirname(pdf_path)
            pages_dir = os.path.join(files_dir, 'pages')
            os.makedirs(pages_dir, exist_ok=True)
            
            # 逐页OCR
            for i, page_num in enumerate(page_numbers):
                try:
                    # 发送进度
                    yield f"data: {json.dumps({'type': 'progress', 'completed': i, 'total': len(page_numbers), 'current_page': page_num})}\n\n"
                    
                    # 执行OCR
                    result = ocr_page_image(pdf_path, page_num)
                    
                    # 保存OCR结果
                    ocr_file = os.path.join(pages_dir, f'page_{page_num}_ocr.json')
                    with open(ocr_file, 'w', encoding='utf-8') as f:
                        json.dump(result, f, ensure_ascii=False, indent=2)
                    
                    # 设置为使用OCR结果
                    active_file = os.path.join(pages_dir, f'page_{page_num}_active.txt')
                    with open(active_file, 'w', encoding='utf-8') as f:
                        f.write('ocr')
                    
                    # 发送完成信号
                    yield f"data: {json.dumps({'type': 'page_done', 'page_number': page_num, 'ocr_result': result})}\n\n"
                    
                except Exception as e:
                    error(f"OCR第{page_num}页失败: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'page': page_num, 'message': str(e)})}\n\n"
            
            # 全部完成
            yield f"data: {json.dumps({'type': 'complete', 'total': len(page_numbers)})}\n\n"
            
        except Exception as e:
            error(f"批量OCR失败: {e}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")


@app.post("/api/boards/{board_id}/windows/{window_id}/select-text-source")
async def select_text_source(
    board_id: str,
    window_id: str,
    selection: TextSourceSelection
):
    """
    用户选择使用哪个文字来源
    """
    try:
        # 通过content_manager获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        window_data = next((w for w in windows if w['id'] == window_id), None)
        
        if not window_data:
            raise HTTPException(status_code=404, detail=f"窗口不存在: {window_id}")
        
        pdf_path = window_data.get('content')
        if not pdf_path or not os.path.exists(pdf_path):
            raise HTTPException(status_code=404, detail=f"PDF文件不存在: {pdf_path}")
        
        # 构建pages目录路径
        files_dir = os.path.dirname(pdf_path)
        pages_dir = os.path.join(files_dir, 'pages')
        
        # 保存选择
        active_file = os.path.join(pages_dir, f'page_{selection.page_number}_active.txt')
        with open(active_file, 'w', encoding='utf-8') as f:
            f.write(selection.source)
        
        info(f"✅ 第{selection.page_number}页文字来源切换为: {selection.source}")
        
        return {
            'success': True,
            'page_number': selection.page_number,
            'active_source': selection.source
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"切换文字来源失败: {e}")
        raise HTTPException(status_code=500, detail=f"切换文字来源失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    info("启动WhatNote V2后端服务...")
    uvicorn.run("main:app", host="127.0.0.1", port=8081, reload=False) 