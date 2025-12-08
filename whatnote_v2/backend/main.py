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
import shutil
import zipfile
import aiohttp
import uuid
from typing import List, Dict, Optional
from pathlib import Path

# 配置 GPT-SoVITS 默认地址
GPT_SOVITS_URL = "http://127.0.0.1:9880"
from datetime import datetime
from config import API_HOST, API_PORT, DATA_DIR
from logger import info, error

# 导入新的存储管理器
from storage.file_manager import FileSystemManager
from storage.content_manager import ContentManager
from storage.file_watcher import FileWatcher
from storage.conversation_manager import ConversationManager
from storage.api_config_manager import APIConfigManager
from storage.theme_manager import ThemeManager
from llm_service import LLMService
from agents.manager import CyberChatManager
from agents.schemas import AgentProfile
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
    """应用启动时启动文件监控服务和注册工具"""
    info("启动文件监控服务...")
    file_watcher.start_watching()
    
    # 注册内置工具（每次启动都执行，内部会覆盖旧定义）
    try:
        from tools import tool_registry, register_builtin_tools
        register_builtin_tools(tool_registry, content_manager, file_manager, DATA_DIR)
        info(f"✅ 当前已注册 {len(tool_registry.get_all_tools())} 个工具")
    except Exception as e:
        error(f"❌ 注册工具失败: {e}")
        import traceback
        error(traceback.format_exc())

    # 启动聊天管理器
    await chat_manager.start_loop()

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭时停止文件监控服务"""
    info("停止文件监控服务...")
    try:
        file_watcher.stop_watching()
        info("文件监控服务已停止")
    except Exception as e:
        info(f"停止文件监控服务时出错: {e}")
    
    # 停止聊天管理器
    await chat_manager.stop_loop()
    
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
llm_service = LLMService(api_config_manager, content_manager, conversation_manager)
theme_manager = ThemeManager()

# 初始化 CyberChat 管理器
chat_manager = CyberChatManager(llm_service, DATA_DIR)

# 1. 处理旧房间 (暂停)
default_room = chat_manager.create_room("default_room", "CyberLounge 98 (Legacy)", "Chaos")
default_room.active_agents = [] # 清空活跃成员以暂停自动对话
chat_manager.save_room("default_room")

# 2. 创建新房间 (Casual Lounge)
casual_room = chat_manager.create_room("casual_lounge", "The Lounge", "Chill & Tech")

# 初始化默认 Agents (使用优化后的 Prompt)
try:
    chat_manager.create_agent(AgentProfile(
        id="hacker_neo",
        name="HackerNeo",
        personality="Cybersecurity expert. Knowledgeable but chill. Skeptical of big tech.",
        style="Concise, tech-savvy, lowercase usually. Minimal jargon unless necessary.",
        interests=["Security", "Tech", "Privacy"]
    ))

    chat_manager.create_agent(AgentProfile(
        id="anime_chan",
        name="AnimeChan",
        personality="Design student who loves pop culture. Friendly and observant.",
        style="Casual, warm, uses emojis sparsely. Sounds like a normal gen-z user.",
        interests=["Art", "Anime", "Design", "Daily Life"]
    ))

    chat_manager.create_agent(AgentProfile(
        id="tech_bro",
        name="TechBro",
        personality="Startup founder working on AI. Optimistic but grounded.",
        style="Direct, professional but casual. Efficient communicator.",
        interests=["AI", "Startups", "Productivity"]
    ))
    
    # 3. 将 Agent 加入新房间
    chat_manager.add_agent_to_room("hacker_neo", "casual_lounge")
    chat_manager.add_agent_to_room("anime_chan", "casual_lounge")
    chat_manager.add_agent_to_room("tech_bro", "casual_lounge")
    
    # 重放历史记录给 Agent
    chat_manager.replay_history()
    
    info("[Main] CyberChat Agents initialized in casual_lounge.")
except Exception as e:
    error(f"[Main] Failed to initialize CyberChat agents: {e}")


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

# --- CyberChat API ---

@app.post("/api/chat/send")
async def send_chat_message(request: Request):
    """Send a message to the chat room."""
    try:
        data = await request.json()
        content = data.get("content")
        sender_name = data.get("sender_name", "User")
        
        if not content:
            raise HTTPException(status_code=400, detail="Content is required")
        
        # For now, we assume a single 'user' identity
        user_id = "user_main" 
        room_id = data.get("room_id", "casual_lounge") # Default to new room
        
        msg = await chat_manager.post_message(room_id, user_id, sender_name, content)
        return {"status": "success", "message": msg}
    except Exception as e:
        error(f"Error sending chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/stream")
async def stream_chat_messages(request: Request):
    """SSE stream for chat messages."""
    async def event_generator():
        # Subscribe to the manager
        queue = await chat_manager.subscribe()
        try:
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    break
                    
                # Wait for next message
                msg = await queue.get()
                # 必须使用 json.dumps(default=str) 处理 timestamp 等字段
                yield f"data: {json.dumps(msg.dict(), default=str)}\n\n"
        except asyncio.CancelledError:
            pass
        except Exception as e:
            error(f"SSE Error: {e}")
        finally:
            chat_manager.unsubscribe(queue)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.get("/api/chat/agents")
async def get_chat_agents(room_id: Optional[str] = None):
    """Get agents. If room_id provided, return agents in that room."""
    if room_id:
        room = chat_manager.get_room(room_id)
        if not room:
            return {"agents": []}
        agents = []
        for agent_id in room.active_agents:
            agent = chat_manager.agents.get(agent_id)
            if agent:
                agents.append(agent.profile.dict())
        return {"agents": agents}
    else:
        # Return all agents
        return {"agents": [a.profile.dict() for a in chat_manager.agents.values()]}

@app.post("/api/chat/agents/generate")
async def generate_agent(request: Request):
    """Generate an agent profile using LLM."""
    data = await request.json()
    description = data.get("description")
    if not description:
        raise HTTPException(status_code=400, detail="Description required")
        
    try:
        profile = await chat_manager.generate_agent_profile(description)
        # Create and save the agent immediately
        chat_manager.create_agent(profile)
        return {"status": "success", "agent": profile.dict()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/rooms")
async def get_chat_rooms():
    """List all chat rooms."""
    return {"rooms": [
        {
            "id": r.id, 
            "name": r.name, 
            "topic": r.topic, 
            "active_agents_count": len(r.active_agents)
        } 
        for r in chat_manager.rooms.values()
    ]}

@app.post("/api/chat/rooms")
async def create_chat_room(request: Request):
    """Create a new chat room."""
    data = await request.json()
    name = data.get("name")
    topic = data.get("topic", "")
    system_prompt = data.get("system_prompt", "")
    
    if not name:
        raise HTTPException(status_code=400, detail="Room name required")
        
    room_id = f"room_{uuid.uuid4().hex[:8]}"
    room = chat_manager.create_room(room_id, name, topic)
    # Update extra fields
    room.system_prompt = system_prompt
    chat_manager.save_room(room_id)
    
    return {"status": "success", "room": room.dict()}

@app.post("/api/chat/rooms/{room_id}/invite")
async def invite_agent(room_id: str, request: Request):
    """Invite an agent to a room."""
    data = await request.json()
    agent_id = data.get("agent_id")
    
    if not agent_id:
        raise HTTPException(status_code=400, detail="Agent ID required")
        
    if room_id not in chat_manager.rooms:
        raise HTTPException(status_code=404, detail="Room not found")
        
    chat_manager.add_agent_to_room(agent_id, room_id)
    return {"status": "success", "message": f"Added {agent_id} to {room_id}"}

@app.get("/api/chat/history")
async def get_chat_history(room_id: str = "casual_lounge"):
    """Get recent chat history."""
    room = chat_manager.get_room(room_id)
    return {"history": room.history if room else []}


@app.get("/api/tools/status")
async def tools_status():
    """工具状态检查端点"""
    from tools import tool_registry
    return {
        "total_tools": len(tool_registry.get_all_tools()),
        "tools": [t['function']['name'] for t in tool_registry.get_all_tools()]
    }

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

# 日历任务API
@app.get("/api/calendar/tasks")
async def get_all_calendar_tasks():
    """获取所有日历任务"""
    try:
        from tools.calendar_tools import CalendarToolHandlers
        handler = CalendarToolHandlers(DATA_DIR)
        calendar_data = handler._load_calendar_data()
        return calendar_data
    except Exception as e:
        error(f"获取日历任务失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/calendar/tasks")
async def save_calendar_tasks(tasks_data: Dict):
    """保存所有日历任务"""
    try:
        from tools.calendar_tools import CalendarToolHandlers
        handler = CalendarToolHandlers(DATA_DIR)
        handler._save_calendar_data(tasks_data)
        info(f"保存日历任务成功")
        return {"message": "保存成功"}
    except Exception as e:
        error(f"保存日历任务失败: {e}")
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

@app.post("/api/boards/{board_id}/migrate-version-configs")
async def migrate_version_configs(board_id: str):
    """迁移PDF版本配置到新位置（xxx.pdf.versions.json）"""
    try:
        result = content_manager.migrate_version_configs_to_new_location(board_id)
        if 'error' in result:
            raise HTTPException(status_code=500, detail=result['error'])
        info(f"版本配置迁移完成: {board_id}")
        return {"message": "版本配置迁移完成", "result": result}
    except HTTPException:
        raise
    except Exception as e:
        error(f"迁移版本配置失败: {e}")
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


# ---------------------------------------------------------------------------
# 个性化设置与壁纸管理 API
# ---------------------------------------------------------------------------

@app.get("/api/personalization/settings/{board_id}")
async def get_personalization_settings(board_id: str):
    try:
        settings = theme_manager.get_settings(board_id)
        return settings
    except Exception as e:
        error(f"获取个性化设置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/personalization/wallpapers/default")
async def upload_default_wallpaper(file: UploadFile = File(...)):
    try:
        wallpaper = theme_manager.save_default_wallpaper(file)
        info("默认壁纸更新成功")
        return {"message": "默认壁纸更新成功", "wallpaper": wallpaper}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error(f"上传默认壁纸失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/personalization/wallpapers/default/image")
async def serve_default_wallpaper():
    path = theme_manager.get_default_wallpaper_path()
    if not path:
        raise HTTPException(status_code=404, detail="默认壁纸不存在")

    media_type = mimetypes.guess_type(path.name)[0] or "image/png"
    return FileResponse(path, media_type=media_type)


@app.post("/api/boards/{board_id}/wallpapers")
async def upload_board_wallpaper(board_id: str, file: UploadFile = File(...)):
    try:
        wallpaper = theme_manager.save_board_wallpaper(board_id, file)
        info(f"展板壁纸上传成功: {board_id}")
        return {"message": "壁纸上传成功", "wallpaper": wallpaper}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error(f"上传展板壁纸失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/boards/{board_id}/wallpapers")
async def list_board_wallpapers(board_id: str):
    try:
        settings = theme_manager.get_settings(board_id)
        return {
            "defaultWallpaper": settings.get("defaultWallpaper"),
            "boardWallpapers": settings.get("boardWallpapers", []),
            "selectedBoardWallpaperId": settings.get("selectedBoardWallpaperId"),
            "appliedWallpaper": settings.get("appliedWallpaper"),
        }
    except Exception as e:
        error(f"获取展板壁纸列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/boards/{board_id}/wallpapers/selection")
async def select_board_wallpaper(board_id: str, data: Dict):
    wallpaper_id = data.get("wallpaperId")
    display_mode = data.get("displayMode")
    try:
        settings = theme_manager.select_board_wallpaper(board_id, wallpaper_id, display_mode)
        return {
            "selectedBoardWallpaperId": settings.get("selectedBoardWallpaperId"),
            "appliedWallpaper": settings.get("appliedWallpaper"),
            "boardDisplayMode": settings.get("boardDisplayMode"),
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error(f"设置展板壁纸失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.put("/api/personalization/wallpapers/default/display-mode")
async def update_default_wallpaper_display_mode(data: Dict):
    display_mode = data.get("displayMode")
    try:
        mode = theme_manager.set_default_display_mode(display_mode)
        return {"defaultDisplayMode": mode}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        error(f"更新默认壁纸显示模式失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/boards/{board_id}/wallpapers/{wallpaper_id}/image")
async def serve_board_wallpaper(board_id: str, wallpaper_id: str):
    path = theme_manager.get_board_wallpaper_path(board_id, wallpaper_id)
    if not path:
        raise HTTPException(status_code=404, detail="壁纸不存在")

    media_type = mimetypes.guess_type(path.name)[0] or "image/png"
    return FileResponse(path, media_type=media_type)


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

@app.get("/api/boards/{board_id}/files/{filename}")
async def get_board_file(board_id: str, filename: str):
    """获取展板文件（自动查找课程路径）"""
    try:
        # 查找展板目录
        board_dir = None
        for course_dir in content_manager.file_manager.courses_dir.iterdir():
            if course_dir.is_dir():
                potential_board_dir = course_dir / board_id
                if potential_board_dir.exists():
                    board_dir = potential_board_dir
                    break
        
        if not board_dir:
            raise HTTPException(status_code=404, detail="展板不存在")
            
        file_path = board_dir / "files" / filename
        
        if not file_path.exists():
            # 尝试 URL 解码文件名再次查找
            import urllib.parse
            decoded_filename = urllib.parse.unquote(filename)
            file_path = board_dir / "files" / decoded_filename
            
            if not file_path.exists():
                raise HTTPException(status_code=404, detail="文件不存在")
        
        return FileResponse(file_path)
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"获取文件失败: {e}")
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
        previous_script = request_body.get('previous_script', '')
        next_script = request_body.get('next_script', '')
        
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
        prompt_parts.append("请根据以下PDF页面内容生成注释/讲稿。注意：我提供了前后页面的内容以及可能的讲稿参考，是为了防止页面分割导致内容不连续，你的输出应该主要针对当前页面，并保持上下文连贯。\n")
        
        if page_contents.get('previous'):
            prompt_parts.append(f"【上一页内容（第{page-1}页）】\n{page_contents['previous']}\n")
            if previous_script:
                prompt_parts.append(f"【上一页已生成的讲稿参考】\n{previous_script}\n")
        
        prompt_parts.append(f"【当前页内容（第{page}页）】\n{page_contents['current']}\n")
        
        if next_script:
            prompt_parts.append(f"【下一页已生成的讲稿参考】\n{next_script}\n")
        
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
            task_prompt = f"""请仔细识别这张PDF页面图像中的所有文本内容。这是第{page}页。

**任务要求**：
1. 提取页面中所有可见的文字（包括标题、正文、列表、标注等）
2. 保持原文的语言（英文就用英文，中文就用中文）
3. 保持原文的结构和格式
4. 如果有公式、图表，请描述它们的内容和作用
5. 如果有表格，请用Markdown表格格式呈现

**重要提示**：
- 不要编造或添加原文中没有的内容
- 不要用你自己的话概括，要逐字提取原文
- 保持专业术语的准确性
- 如果有不确定的字符，用 [?] 标记

请直接输出提取的文本内容，使用Markdown格式，不要包裹在代码框中。"""
        
        
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
        # ⚠️ 视觉任务需要使用支持多模态的模型
        messages = [user_message]
        
        # 准备SSE流式响应
        async def generate_visual_annotation_stream():
            accumulated_content = ""
            
            try:
                # 检测当前提供商和模型
                current_provider = llm_service.api_config_manager.get_current_provider()
                current_config = llm_service.api_config_manager.get_current_config()
                current_model = current_config.get('model', '')
                
                # 视觉模型映射
                vision_model_map = {
                    'qwen': 'qwen-vl-plus',
                    'openai': 'gpt-4o',
                    'anthropic': 'claude-3-5-sonnet-20241022',
                    'gemini': 'gemini-1.5-pro'
                }
                
                # 检查当前模型是否支持视觉
                visual_capable_models = ['qwen-vl-plus', 'qwen-vl-max', 'qwen-long', 
                                        'gpt-4o', 'gpt-4-turbo', 'gpt-4-vision-preview',
                                        'claude-3-5-sonnet', 'claude-3-opus', 'claude-3-sonnet',
                                        'gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro-vision']
                
                # 确定使用的模型
                if any(model in current_model for model in visual_capable_models):
                    # 当前模型支持视觉，直接使用
                    use_model = None  # 不覆盖
                    info(f"[视觉提取] 使用当前模型: {current_model}")
                else:
                    # 当前模型不支持视觉，临时切换
                    use_model = vision_model_map.get(current_provider, 'qwen-vl-plus')
                    info(f"[视觉提取] 当前模型 {current_model} 不支持视觉，临时使用: {use_model}")
                
                async for chunk in llm_service.chat_completion(messages, stream=True, override_model=use_model):
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
                        "method": "visual",
                        "model_used": llm_service.api_config_manager.get_current_config().get('model', 'unknown')
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
                    
                    # 对每组进行分析 (并发处理)
                    info(f"开始并发分析 {len(groups)} 个分组 (并发数: 3)")
                    
                    import asyncio
                    queue = asyncio.Queue()
                    semaphore = asyncio.Semaphore(3) # 并发限制
                    
                    async def process_group(group):
                        async with semaphore:
                            group_num = group['group_number']
                            page_start = group['page_start']
                            page_end = group['page_end']
                            
                            try:
                                await queue.put(f"data: {json.dumps({'type': 'status', 'message': f'正在并发分析第{group_num}组 (第{page_start}-{page_end}页)...'}, ensure_ascii=False)}\n\n")
                                
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
                                        # 将子模型的输出也流式传递给前端 (可选，如果前端不展示可以忽略，但为了保持兼容性还是传一下)
                                        # 注意：并发时这可能会导致前端接收到的 group_content 混杂，但只要前端按 group 字段区分或者忽略就没问题
                                        # 鉴于目前 narrator plugin 忽略此消息，我们只在 debug 级别发送，或者保留原样
                                        # await queue.put(f"data: {json.dumps({'type': 'group_content', 'group': group_num, 'content': chunk}, ensure_ascii=False)}\n\n")
                                        pass 
                                
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
                                        lines = content.split('\\n')
                                        content = '\\n'.join(lines[1:-1]) if len(lines) > 2 else content
                                    
                                    sub_outline_data = json.loads(content)
                                    
                                    # 发送完成信号
                                    await queue.put(f"data: {json.dumps({'type': 'group_done', 'group': group_num, 'outline': sub_outline_data}, ensure_ascii=False)}\n\n")
                                    
                                    return {
                                        'group_number': group_num,
                                        'outline': sub_outline_data.get('outline', [])
                                    }
                                except json.JSONDecodeError as e:
                                    error(f"解析分组{group_num}大纲JSON失败: {e}")
                                    return {
                                        'group_number': group_num,
                                        'outline': [],
                                        'error': str(e)
                                    }
                            except Exception as e:
                                error(f"分组{group_num}分析出错: {e}")
                                return {
                                    'group_number': group_num,
                                    'outline': [],
                                    'error': str(e)
                                }

                    # 创建任务
                    tasks = [asyncio.create_task(process_group(g)) for g in groups]
                    
                    # 等待任务并管理队列
                    async def result_waiter():
                        results = await asyncio.gather(*tasks)
                        await queue.put(None) # 结束信号
                        return results
                        
                    waiter_task = asyncio.create_task(result_waiter())
                    
                    # 从队列中读取消息并yield
                    while True:
                        msg = await queue.get()
                        if msg is None:
                            break
                        yield msg
                        
                    # 获取最终结果
                    results = await waiter_task
                    
                    # 整理结果（按组号排序）
                    group_outlines = sorted(results, key=lambda x: x['group_number'])
                    
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

@app.get("/api/boards/{board_id}/windows/{window_id}/annotations/batch/summary-note")
async def get_batch_summary_note(board_id: str, window_id: str):
    """获取已生成的全文档笔记"""
    try:
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        target_window = None
        for window in windows:
            if window.get('id') == window_id:
                target_window = window
                break
        
        if not target_window:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        # 查找PDF文件所在的目录
        pdf_file_path = Path(target_window.get('content'))
        if not pdf_file_path.is_absolute():
            # 如果是相对路径，需要找到它所在的展板目录
            board_dir = None
            for course_dir in content_manager.file_manager.courses_dir.iterdir():
                if course_dir.is_dir():
                    potential_board_dir = course_dir / board_id
                    if potential_board_dir.exists():
                        board_dir = potential_board_dir
                        break
            
            if board_dir:
                pdf_file_path = board_dir / pdf_file_path
        
        if pdf_file_path and pdf_file_path.exists():
            pdf_name = pdf_file_path.stem
            pages_dir = pdf_file_path.parent / "pages" / pdf_name
            summary_file_path = pages_dir / "summary_note.md"
            
            if summary_file_path.exists():
                with open(summary_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                return {"success": True, "content": content}
            else:
                return {"success": False, "message": "笔记文件不存在"}
        else:
            raise HTTPException(status_code=404, detail="PDF文件路径无效")
            
    except HTTPException:
        raise
    except Exception as e:
        error(f"加载全文档笔记失败: {e}")
        raise HTTPException(status_code=500, detail=f"加载全文档笔记失败: {str(e)}")

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

# ============================================
# PDF页面内容提取API（多模态LLM）
# ============================================

@app.get("/api/boards/{board_id}/windows/{window_id}/pages/thumbnails")
async def render_pages_thumbnails(board_id: str, window_id: str):
    """渲染所有页面的轻量级缩略图"""
    try:
        info(f"开始渲染页面缩略图: board_id={board_id}, window_id={window_id}")
        
        # 获取窗口数据
        windows = content_manager.get_board_windows(board_id)
        window_data = None
        for window in windows:
            if window.get('id') == window_id:
                window_data = window
                break
        
        if not window_data:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        pdf_path = Path(window_data['content'])
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="PDF文件不存在")
        
        # 获取PDF总页数
        import fitz
        pdf_document = fitz.open(pdf_path)
        total_pages = len(pdf_document)
        pdf_document.close()
        
        # 构建缩略图目录
        pdf_name = pdf_path.stem
        pages_dir = pdf_path.parent / "pages" / pdf_name
        thumbnails_dir = pages_dir / "thumbnails"
        thumbnails_dir.mkdir(parents=True, exist_ok=True)
        
        info(f"PDF总页数: {total_pages}")
        info(f"缩略图目录: {thumbnails_dir}")
        
        # 渲染所有页面的缩略图
        rendered_count = 0
        for page_num in range(1, total_pages + 1):
            thumbnail_path = thumbnails_dir / f"page_{page_num:03d}.png"
            
            # 如果缩略图已存在，跳过
            if thumbnail_path.exists():
                rendered_count += 1
                continue
            
            try:
                # 使用低DPI快速渲染（1.0倍缩放 = 72dpi）
                pdf_document = fitz.open(pdf_path)
                pdf_page = pdf_document[page_num - 1]
                
                # 低质量快速渲染
                mat = fitz.Matrix(1.0, 1.0)  # 1倍缩放，速度快
                pix = pdf_page.get_pixmap(matrix=mat)
                
                # 保存缩略图
                pix.save(str(thumbnail_path))
                pdf_document.close()
                
                rendered_count += 1
                info(f"渲染缩略图: 第{page_num}页")
                
            except Exception as e:
                error(f"渲染第{page_num}页缩略图失败: {e}")
                if 'pdf_document' in locals():
                    pdf_document.close()
        
        return {
            "success": True,
            "total_pages": total_pages,
            "rendered_count": rendered_count,
            "thumbnails_dir": str(thumbnails_dir.relative_to(pdf_path.parent))
        }
        
    except Exception as e:
        error(f"渲染缩略图失败: {e}")
        raise HTTPException(status_code=500, detail=f"渲染缩略图失败: {str(e)}")

@app.get("/api/boards/{board_id}/windows/{window_id}/pages/info")
async def get_pages_extraction_info(board_id: str, window_id: str):
    """
    获取所有页面的提取信息
    返回：每页的字数、是否已提取等信息
    """
    try:
        info(f"📋 获取页面提取信息: board_id={board_id}, window_id={window_id}")
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        window_data = None
        for window in windows:
            if window.get('id') == window_id:
                window_data = window
                break
        
        if not window_data:
            error(f"窗口不存在: {window_id}")
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        info(f"窗口数据: type={window_data.get('type')}, title={window_data.get('title')}")
        
        window_content = window_data.get('content', '')
        if not window_content:
            raise HTTPException(status_code=404, detail="窗口内容为空")
        
        # 转换为绝对路径
        pdf_path = Path(window_content)
        if not pdf_path.is_absolute():
            board_dir = Path(storage_base_dir) / board_id
            pdf_path = board_dir / window_content
        
        if not pdf_path.exists():
            error(f"PDF文件不存在: {pdf_path}")
            raise HTTPException(status_code=404, detail="PDF文件不存在")
        
        info(f"PDF路径: {pdf_path}")
        
        # 获取PDF总页数
        import pypdf
        pdf_reader = pypdf.PdfReader(str(pdf_path))
        total_pages = len(pdf_reader.pages)
        
        info(f"PDF总页数: {total_pages}")
        
        # 获取PDF文件名（不含扩展名）
        pdf_name = pdf_path.stem
        
        # 获取pages目录（统一的路径结构）
        pages_dir = pdf_path.parent / "pages" / pdf_name
        
        # 第一遍：收集所有页面的图片统计信息
        all_pages_image_stats = []
        import fitz
        try:
            pdf_doc = fitz.open(pdf_path)
            for page_num in range(1, total_pages + 1):
                try:
                    pdf_page = pdf_doc[page_num - 1]
                    image_list = pdf_page.get_images(full=True)
                    
                    page_image_count = len(image_list)
                    page_image_size = 0
                    large_images = 0  # 大图片数量（>10KB）
                    
                    for img in image_list:
                        xref = img[0]
                        try:
                            base_image = pdf_doc.extract_image(xref)
                            image_bytes = base_image["image"]
                            img_size = len(image_bytes)
                            page_image_size += img_size
                            
                            # 统计大图片（>10KB，通常是内容图片而非装饰）
                            if img_size > 10240:  # 10KB
                                large_images += 1
                        except:
                            pass
                    
                    all_pages_image_stats.append({
                        'page': page_num,
                        'count': page_image_count,
                        'size': page_image_size,
                        'large_count': large_images
                    })
                except Exception as e:
                    all_pages_image_stats.append({
                        'page': page_num,
                        'count': 0,
                        'size': 0,
                        'large_count': 0
                    })
            pdf_doc.close()
        except Exception as e:
            error(f"打开PDF文件失败: {e}")
            all_pages_image_stats = [{'page': i, 'count': 0, 'size': 0, 'large_count': 0} for i in range(1, total_pages + 1)]
        
        # 计算基准值：使用第一页和最后一页图片数量的最小值
        # 原理：首尾页通常是封面/目录/参考文献，最能代表"纯装饰"的基准
        if len(all_pages_image_stats) >= 2:
            first_page = all_pages_image_stats[0]
            last_page = all_pages_image_stats[-1]
            
            # 只取图片数量作为基准
            baseline_count = min(first_page['count'], last_page['count'])
            
            info(f"📊 图片基准数量（取自第1页和第{len(all_pages_image_stats)}页的最小值）:")
            info(f"   第1页: {first_page['count']}张")
            info(f"   第{len(all_pages_image_stats)}页: {last_page['count']}张")
            info(f"   → 基准: {baseline_count}张")
        elif len(all_pages_image_stats) == 1:
            # 只有一页，直接用第一页
            baseline_count = all_pages_image_stats[0]['count']
            info(f"📊 图片基准数量（单页文档）: {baseline_count}张")
        else:
            # 没有页面
            baseline_count = 0
            info(f"📊 图片基准数量: 0张（无页面）")
        
        # 收集每页的信息
        pages_info = []
        for page_num in range(1, total_pages + 1):
            # LLM提取的文件（新格式）
            page_file = pages_dir / f"{pdf_name}_page_{page_num:03d}_llm.md"
            
            if page_file.exists():
                # 读取文件内容统计字数
                try:
                    with open(page_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 简单统计：去除空白后的字符数
                        char_count = len(content.strip())
                        
                        # 尝试提取版本信息
                        version_info = {
                            'has_text': '文本提取' in content or '## 文本内容' in content,
                            'has_description': '图片描述' in content or '## 图片描述' in content
                        }
                        
                        pages_info.append({
                            'page': page_num,
                            'extracted': True,
                            'char_count': char_count,
                            'versions': version_info,
                            'file_path': str(page_file)
                        })
                except Exception as e:
                    error(f"读取页面文件失败: {e}")
                    pages_info.append({
                        'page': page_num,
                        'extracted': False,
                        'char_count': 0,
                        'versions': {'has_text': False, 'has_description': False}
                    })
            else:
                # 尝试提取原始文字统计字数和检测图片
                try:
                    page = pdf_reader.pages[page_num - 1]
                    text = page.extract_text() or ''
                    char_count = len(text.strip())
                    
                    # 从之前统计的数据中获取图片信息
                    page_stats = all_pages_image_stats[page_num - 1]
                    image_count = page_stats['count']
                    total_image_size = page_stats['size']
                    large_image_count = page_stats['large_count']
                    
                    # 判断是否需要LLM提取（简化规则）
                    # 规则1：文字很少（<=50字）
                    low_text = char_count <= 50
                    
                    # 规则2：图片数量超过基准值（说明有额外的内容图片）
                    has_extra_images = image_count > baseline_count
                    
                    # 综合判断：文字少 OR 图片数量超基准
                    needs_llm = low_text or has_extra_images
                    
                    pages_info.append({
                        'page': page_num,
                        'extracted': False,
                        'char_count': char_count,
                        'versions': {'has_text': False, 'has_description': False},
                        'original_text_available': char_count > 50,
                        'image_count': image_count,
                        'total_image_size': total_image_size,
                        'large_image_count': large_image_count,
                        'baseline_count': baseline_count,  # 新增：基准值
                        'extra_images': max(0, image_count - baseline_count),  # 新增：超出基准的图片数
                        'needs_llm_extraction': needs_llm
                    })
                except Exception as e:
                    error(f"提取原始文字失败: {e}")
                    pages_info.append({
                        'page': page_num,
                        'extracted': False,
                        'char_count': 0,
                        'versions': {'has_text': False, 'has_description': False},
                        'original_text_available': False,
                        'image_count': 0,
                        'total_image_size': 0,
                        'needs_llm_extraction': True
                    })
        
        return {
            'success': True,
            'total_pages': total_pages,
            'pages': pages_info
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"获取页面提取信息失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"获取页面提取信息失败: {str(e)}")

@app.post("/api/boards/{board_id}/windows/{window_id}/pages/extract")
async def extract_pages_content(
    board_id: str,
    window_id: str,
    request_data: Dict
):
    """
    使用多模态LLM提取指定页面的内容
    请求体：{ "pages": [1, 2, 3], "dpi": 300 }
    返回：SSE流式响应
    """
    try:
        pages_to_extract = request_data.get('pages', [])
        dpi = request_data.get('dpi', 300)
        
        if not pages_to_extract:
            raise HTTPException(status_code=400, detail="未指定要提取的页面")
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        window_data = None
        for window in windows:
            if window.get('id') == window_id:
                window_data = window
                break
        
        if not window_data:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        window_content = window_data.get('content', '')
        if not window_content:
            raise HTTPException(status_code=404, detail="窗口内容为空")
        
        # 转换为绝对路径
        pdf_path = Path(window_content)
        if not pdf_path.is_absolute():
            board_dir = Path(storage_base_dir) / board_id
            pdf_path = board_dir / window_content
        
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="PDF文件不存在")
        
        # 获取PDF文件名（不含扩展名），用于统一命名
        pdf_name = pdf_path.stem
        
        info(f"🚀 开始并行提取 {len(pages_to_extract)} 个页面")
        
        # 检测并确定使用的模型（批量提取使用视觉模型）
        current_provider = llm_service.api_config_manager.get_current_provider()
        current_config = llm_service.api_config_manager.get_current_config()
        current_model = current_config.get('model', '')
        
        vision_model_map = {
            'qwen': 'qwen-vl-plus',
            'openai': 'gpt-4o',
            'anthropic': 'claude-3-5-sonnet-20241022',
            'gemini': 'gemini-1.5-pro'
        }
        
        visual_capable_models = ['qwen-vl-plus', 'qwen-vl-max', 'qwen-long', 
                                'gpt-4o', 'gpt-4-turbo', 'gpt-4-vision-preview',
                                'claude-3-5-sonnet', 'claude-3-opus', 'claude-3-sonnet',
                                'gemini-1.5-pro', 'gemini-1.5-flash', 'gemini-pro-vision']
        
        if any(model in current_model for model in visual_capable_models):
            use_model = None
            info(f"[批量提取] 使用当前模型: {current_model}")
        else:
            use_model = vision_model_map.get(current_provider, 'qwen-vl-plus')
            info(f"[批量提取] 当前模型 {current_model} 不支持视觉，临时使用: {use_model}")
        
        # 定义单个页面的提取任务（返回结果而不是yield）
        async def extract_single_page(page_num: int):
            """提取单个页面的内容（独立任务，不依赖其他页面）"""
            try:
                info(f"🚀 [任务{page_num}] 开始提取")
                
                # 渲染PDF页面为图片
                image_path = content_manager.render_pdf_page_to_image(board_id, window_id, page_num)
                if not image_path:
                    raise Exception(f"渲染失败")
                
                # 读取图片
                with open(image_path, 'rb') as f:
                    img_bytes = f.read()
                
                import base64
                img_base64 = base64.b64encode(img_bytes).decode('utf-8')
                info(f"✅ [任务{page_num}] 图片渲染完成: {len(img_bytes)} bytes")
                
                # 调用多模态LLM（每页独立，无历史对话）
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"""你正在分析PDF第{page_num}页的截图。请完成以下两个独立任务：

**任务1：文本提取（OCR）**
- 识别并提取页面中的**所有文字内容**，包括：
  * 标题、副标题、小标题（所有层级）
  * 正文段落（完整的句子）
  * 列表项（有序和无序列表）
  * 表格中的所有文字（包括表头和数据）
  * 页眉、页脚、页码
  * 标注、注释、说明文字
  * 图中的文字标注和标签
  * 公式中的文字说明
- 保持原有的层次结构和格式
- 使用Markdown格式（# 标题、## 副标题、- 列表、**粗体**等）
- **重要**：提取所有可见文字，不要遗漏任何内容
- **重要**：如果文字是英文，保持英文；如果是中文，保持中文
- **重要**：保持专业术语的准确性，不要猜测或替换
- 如果有不确定的字符，用 [?] 标记

**任务2：图片与图表描述（关键规则）**
**判断标准**：页面中是否包含以下内容？
- 照片/插图（人物、风景、物品、实验设备等）
- 数据图表（柱状图、折线图、饼图、散点图、线图等）
- 流程图、架构图、示意图、框图
- 信息图表（infographic）
- 科学图表（解剖图、结构图、示意图等）
- 地图、地理图
- 任何包含标注、编号的图表（如：标注1-12的解剖图）

**如果有上述内容**：
- **详细描述**图片/照片展示的具体内容
- **描述**图表的类型、数据趋势、关键数据点
- **说明**流程图/架构图的结构和流程
- **描述**图表中的标注和编号（如：1号标注是什么，2号标注是什么）
- **描述**图表的目的和作用
- 如果图表有标题，也要提取标题

**如果没有上述内容**（纯文字页面、只有文字排版、只有表格）：
- **返回空字符串 ""**
- **不要**描述页面布局
- **不要**描述背景颜色
- **不要**描述文字排版
- **不要**描述logo、页眉页脚（这些是文字）
- **不要**说"本页无图片或图表"

**输出格式（必须是纯JSON）：**
```json
{{
  "text_extraction": "这里是所有文字内容（Markdown格式）",
  "visual_description": "这里只描述图片/图表（如果没有则为空字符串\"\"）"
}}
```

**示例**：
- 纯文字PPT页面 → visual_description: ""
- 包含销售数据柱状图 → visual_description: "柱状图显示2020-2023年销售数据，呈上升趋势..."
- 包含产品照片 → visual_description: "照片展示了一款蓝色的智能手机，屏幕显示..."

只返回JSON，不要markdown代码块标记。"""
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/png;base64,{img_base64}"
                                    }
                                }
                            ]
                        }
                    ]
                
                # 非流式调用LLM（并行任务不使用流式）
                # 使用视觉模型
                accumulated_content = ""
                async for chunk in llm_service.chat_completion(messages, stream=False, override_model=use_model):
                    accumulated_content += chunk
                
                info(f"✅ [任务{page_num}] LLM提取完成: {len(accumulated_content)} 字")
                
                # 解析JSON格式的返回内容
                text_content = ""
                image_content = ""
                
                try:
                    # 移除可能的markdown代码块标记
                    json_content = accumulated_content.strip()
                    if json_content.startswith("```json"):
                        json_content = json_content[7:]
                    if json_content.startswith("```"):
                        json_content = json_content[3:]
                    if json_content.endswith("```"):
                        json_content = json_content[:-3]
                    json_content = json_content.strip()
                    
                    # 解析JSON
                    parsed = json.loads(json_content)
                    text_content = parsed.get("text_extraction", "")
                    image_content = parsed.get("visual_description", "")
                    
                    info(f"页面 {page_num} JSON解析成功")
                except json.JSONDecodeError as e:
                    info(f"页面 {page_num} JSON解析失败，尝试按标记分割: {e}")
                    
                    # 回退到旧的解析方式
                    if "## 文本提取" in accumulated_content and "## 图片描述" in accumulated_content:
                        parts = accumulated_content.split("## 图片描述")
                        if len(parts) == 2:
                            text_content = parts[0].replace("## 文本提取", "").strip()
                            image_content = parts[1].strip()
                        else:
                            text_content = accumulated_content
                            image_content = "（解析失败，仅保存完整内容）"
                    else:
                        # 完全失败，使用完整内容
                        text_content = accumulated_content
                        image_content = "（未能分离视觉描述）"
                
                info(f"页面 {page_num} 最终结果: 文本 {len(text_content)} 字, 视觉描述 {len(image_content)} 字")
                
                # 保存结果（使用统一的命名格式：{pdf_name}_page_{page_num:03d}_llm.md）
                pages_dir = pdf_path.parent / "pages" / pdf_name
                pages_dir.mkdir(parents=True, exist_ok=True)
                
                page_file = pages_dir / f"{pdf_name}_page_{page_num:03d}_llm.md"
                with open(page_file, 'w', encoding='utf-8') as f:
                    f.write(f"# {pdf_name} - 第 {page_num} 页 (LLM提取)\n\n")
                    f.write(f"来源: {pdf_path.name}\n")
                    f.write(f"提取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"页码: {page_num}\n")
                    f.write(f"提取方式: 多模态LLM\n\n")
                    f.write("---\n\n")
                    f.write(accumulated_content)
                
                info(f"💾 [任务{page_num}] 内容已保存")
                
                # 自动设置版本为LLM
                content_manager.save_page_version(board_id, window_id, page_num, 'llm')
                
                info(f"✅ [任务{page_num}] 完成")
                
                # 返回结果
                return {
                    'success': True,
                    'page': page_num,
                    'content': accumulated_content,
                    'textContent': text_content,
                    'imageContent': image_content
                }
                
            except Exception as e:
                error(f"❌ [任务{page_num}] 失败: {e}")
                return {
                    'success': False,
                    'page': page_num,
                    'error': str(e)
                }
            
        # 并行执行所有页面提取任务
        import asyncio
        tasks = [extract_single_page(page_num) for page_num in pages_to_extract]
        
        info(f"🚀 启动 {len(tasks)} 个并行任务")
        
        # 准备SSE流式响应
        async def generate_extraction_stream():
            total_to_extract = len(pages_to_extract)
            completed = 0
            
            # 使用 asyncio.as_completed 实时返回完成的任务
            for coro in asyncio.as_completed(tasks):
                result = await coro
                completed += 1
                
                if result['success']:
                    info(f"✅ 页面 {result['page']} 完成 ({completed}/{total_to_extract})")
                    
                    # 发送完成信号
                    yield f"data: {json.dumps({'type': 'page_complete', 'page': result['page'], 'content': result['content'], 'textContent': result['textContent'], 'imageContent': result['imageContent']}, ensure_ascii=False)}\n\n"
                else:
                    error(f"❌ 页面 {result['page']} 失败")
                    yield f"data: {json.dumps({'type': 'error', 'page': result['page'], 'error': result['error']}, ensure_ascii=False)}\n\n"
            
            # 发送总体完成信号
            info(f"🎉 全部完成: {completed}/{total_to_extract}")
            yield f"data: {json.dumps({'type': 'complete', 'total': total_to_extract}, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_extraction_stream(),
            media_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"提取页面内容失败: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"提取页面内容失败: {str(e)}")

@app.get("/api/boards/{board_id}/windows/{window_id}/pages/{page}/text")
async def get_page_text(board_id: str, window_id: str, page: int):
    """获取指定页面的PyPDF原始文本"""
    try:
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        window_data = None
        for window in windows:
            if window.get('id') == window_id:
                window_data = window
                break
        
        if not window_data:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        window_content = window_data.get('content', '')
        pdf_path = Path(window_content)
        if not pdf_path.is_absolute():
            board_dir = Path(storage_base_dir) / board_id
            pdf_path = board_dir / window_content
        
        if not pdf_path.exists():
            raise HTTPException(status_code=404, detail="PDF文件不存在")
        
        # 使用PyPDF提取文字
        import fitz
        pdf_document = fitz.open(pdf_path)
        
        if page < 1 or page > len(pdf_document):
            pdf_document.close()
            raise HTTPException(status_code=400, detail="页码超出范围")
        
        pdf_page = pdf_document[page - 1]
        text = pdf_page.get_text()
        pdf_document.close()
        
        return {
            'success': True,
            'page': page,
            'text': text
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"获取页面文字失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取页面文字失败: {str(e)}")

@app.get("/api/boards/{board_id}/windows/{window_id}/pages/{page}/content")
async def get_page_content(board_id: str, window_id: str, page: int):
    """获取指定页面的提取内容"""
    try:
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        window_data = None
        for window in windows:
            if window.get('id') == window_id:
                window_data = window
                break
        
        if not window_data:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        window_content = window_data.get('content', '')
        pdf_path = Path(window_content)
        if not pdf_path.is_absolute():
            board_dir = Path(storage_base_dir) / board_id
            pdf_path = board_dir / window_content
        
        # 获取PDF文件名（不含扩展名）
        pdf_name = pdf_path.stem
        
        pages_dir = pdf_path.parent / "pages" / pdf_name
        page_file = pages_dir / f"{pdf_name}_page_{page:03d}_llm.md"
        
        if not page_file.exists():
            raise HTTPException(status_code=404, detail="页面内容未提取")
        
        with open(page_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 尝试从文件内容中提取数据（跳过元数据）
        # 文件格式：元数据头 + --- + 实际内容
        actual_content = content
        if "---\n\n" in content:
            parts = content.split("---\n\n", 1)
            if len(parts) == 2:
                actual_content = parts[1]
        
        # 尝试解析JSON格式（新格式）
        text_content = ""
        image_content = ""
        
        try:
            # 尝试解析为JSON
            json_content = actual_content.strip()
            if json_content.startswith("```json"):
                json_content = json_content[7:]
            if json_content.startswith("```"):
                json_content = json_content[3:]
            if json_content.endswith("```"):
                json_content = json_content[:-3]
            json_content = json_content.strip()
            
            parsed = json.loads(json_content)
            text_content = parsed.get("text_extraction", "")
            image_content = parsed.get("visual_description", "")
            
            info(f"页面 {page} JSON解析成功")
        except:
            # 回退：尝试按标记分割（旧格式）
            if "## 文本提取" in actual_content and "## 图片描述" in actual_content:
                parts = actual_content.split("## 图片描述")
                text_part = parts[0].split("## 文本提取")
                if len(text_part) > 1:
                    text_content = text_part[1].strip()
                if len(parts) > 1:
                    image_content = parts[1].strip()
            else:
                # 完全没有格式，全部作为文本内容
                text_content = actual_content
                image_content = ""
        
        return {
            'success': True,
            'page': page,
            'content': actual_content,
            'text_content': text_content,
            'image_content': image_content
        }
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"获取页面内容失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取页面内容失败: {str(e)}")

@app.put("/api/boards/{board_id}/windows/{window_id}/pages/{page}/content")
async def update_page_content(board_id: str, window_id: str, page: int, request_data: Dict):
    """更新页面内容（用户选择版本后）"""
    try:
        selected_content = request_data.get('content', '')
        selected_version = request_data.get('version', 'llm')  # 'pdf', 'llm'
        
        if not selected_content:
            raise HTTPException(status_code=400, detail="内容不能为空")
        
        # 保存版本配置
        version_saved = content_manager.save_page_version(board_id, window_id, page, selected_version)
        if not version_saved:
            info(f"⚠️ 版本配置保存失败，但继续保存内容")
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        window_data = None
        for window in windows:
            if window.get('id') == window_id:
                window_data = window
                break
        
        if not window_data:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        window_content = window_data.get('content', '')
        pdf_path = Path(window_content)
        if not pdf_path.is_absolute():
            board_dir = Path(storage_base_dir) / board_id
            pdf_path = board_dir / window_content
        
        # 获取PDF文件名（不含扩展名）
        pdf_name = pdf_path.stem
        
        pages_dir = pdf_path.parent / "pages" / pdf_name
        pages_dir.mkdir(parents=True, exist_ok=True)
        
        # 根据版本选择保存到不同文件
        if selected_version == 'llm':
            page_file = pages_dir / f"{pdf_name}_page_{page:03d}_llm.md"
            version_label = "LLM提取"
        else:
            page_file = pages_dir / f"{pdf_name}_page_{page:03d}.md"
            version_label = "PyPDF提取"
        
        with open(page_file, 'w', encoding='utf-8') as f:
            f.write(f"# {pdf_name} - 第 {page} 页 ({version_label})\n\n")
            f.write(f"来源: {pdf_path.name}\n")
            f.write(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"页码: {page}\n")
            f.write(f"版本: {selected_version}\n\n")
            f.write("---\n\n")
            f.write(selected_content)
        
        return {'success': True, 'message': '内容已更新', 'version': selected_version}
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"更新页面内容失败: {e}")
        raise HTTPException(status_code=500, detail=f"更新页面内容失败: {str(e)}")

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

@app.post("/api/llm/chat-with-tools")
async def llm_chat_with_tools(request: dict):
    """支持工具调用的LLM对话API"""
    try:
        messages = request.get('messages', [])
        max_iterations = request.get('max_iterations', 50)
        board_id = request.get('board_id')
        conversation_id = request.get('conversation_id')
        
        if not messages:
            raise HTTPException(status_code=400, detail="消息列表不能为空")
        
        info(f"[API] 开始工具调用对话，消息数: {len(messages)}")
        
        # 使用流式响应返回工具调用过程
        async def generate_response():
            async for event in llm_service.chat_with_tools(messages, max_iterations, board_id, conversation_id):
                # 使用Server-Sent Events格式返回每个事件
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
            yield "data: [DONE]\n\n"
        
        return StreamingResponse(
            generate_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*"
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"工具调用对话失败: {e}")
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


@app.websocket("/ws/console")
async def websocket_console(websocket: WebSocket):
    """WebSocket控制台端点"""
    from tools.console_handler import ConsoleHandler
    from tools import register_builtin_tools
    
    await websocket.accept()
    
    # 为每个连接创建独立的控制台处理器（带 file_manager）
    session_handler = ConsoleHandler(file_manager)
    
    # 注册工具（如果还没注册）
    try:
        from tools import tool_registry
        if len(tool_registry.get_all_tools()) == 0:
            register_builtin_tools(tool_registry, content_manager, file_manager, DATA_DIR)
    except Exception as e:
        error(f"注册工具失败: {e}")
    
    try:
        # 发送欢迎消息
        welcome = {
            "type": "welcome",
            "content": "WhatNote Tool Console v1.0\n\n输入 'help' 查看帮助 | 输入 'courses' 开始导航"
        }
        await websocket.send_json(welcome)
        
        while True:
            # 接收命令
            data = await websocket.receive_text()
            command = data.strip()
            
            if not command:
                continue
            
            # 处理命令
            try:
                response = await session_handler.handle_command(command)
                await websocket.send_json(response)
            except Exception as e:
                error(f"控制台命令执行失败: {e}")
                await websocket.send_json({
                    "type": "error",
                    "content": f"命令执行失败: {str(e)}"
                })
                
    except WebSocketDisconnect:
        info("控制台连接断开")


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

@app.delete("/api/boards/{board_id}/conversations/{conversation_id}/messages")
async def clear_conversation_messages(board_id: str, conversation_id: str):
    """清空对话的所有消息（保留对话记录）"""
    try:
        success = conversation_manager.clear_conversation_messages(board_id, conversation_id)
        if not success:
            raise HTTPException(status_code=404, detail="对话不存在")
        info(f"清空对话消息成功: {conversation_id}")
        return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        error(f"清空对话消息失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/boards/{board_id}/conversations/{conversation_id}/todo-status")
async def get_conversation_todo_status(board_id: str, conversation_id: str):
    """获取会话的待办状态（从对话 JSON 中读取）"""
    try:
        data = conversation_manager.get_todo_state(board_id, conversation_id)
        if data and data.get("status"):
            return {"todo_status": data.get("status")}
        return {"todo_status": None}
    except Exception as e:
        error(f"获取待办状态失败: {e}")
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

if __name__ == "__main__":
    import uvicorn
    info("启动WhatNote V2后端服务...")
    uvicorn.run("main:app", host="127.0.0.1", port=8081, reload=False) 


@app.post("/api/boards/{board_id}/windows/{window_id}/image/extract")
async def extract_image_content(board_id: str, window_id: str, force: bool = False):
    """提取图片窗口的文字内容"""
    try:
        info(f"🚀 开始提取图片内容: window_id={window_id}, force={force}")
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        window_data = None
        for window in windows:
            if window.get('id') == window_id:
                window_data = window
                break
        
        if not window_data:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        # 确定图片路径
        image_path_str = window_data.get('content', '')
        if not image_path_str:
            # 尝试从 file_path 获取
            image_path_str = window_data.get('file_path', '')
            
        if not image_path_str:
             raise HTTPException(status_code=400, detail="窗口没有图片内容")

        # 处理路径
        image_path = Path(image_path_str)
        if not image_path.is_absolute():
             # 1. 尝试直接拼接 DATA_DIR
             path1 = Path(DATA_DIR) / image_path_str
             if path1.exists():
                 image_path = path1
             else:
                 # 2. 尝试作为 board_dir 下的文件
                 # 这里的 board_dir 假设为 DATA_DIR / board_id (兼容旧结构) 或 DATA_DIR / "courses" / ... / board_id
                 # 简单遍历查找
                 found = False
                 for root, dirs, files in os.walk(DATA_DIR):
                     if image_path_str in files:
                         image_path = Path(root) / image_path_str
                         found = True
                         break
                     # 也可以检查相对路径
                     possible = Path(root) / image_path_str
                     if possible.exists() and possible.is_file():
                         image_path = possible
                         found = True
                         break
                 
                 if not found:
                     # 最后的尝试：URL解码
                     if "/static/files/" in image_path_str:
                         try:
                             import urllib.parse
                             rel_path = urllib.parse.unquote(image_path_str.split("/static/files/")[1])
                             path2 = Path(DATA_DIR) / rel_path
                             if path2.exists():
                                 image_path = path2
                         except:
                             pass

        if not image_path.exists():
             raise HTTPException(status_code=404, detail=f"图片文件不存在: {image_path_str}")

        # 确定保存路径
        # 这里的 files_dir 应该是 image_path 的父目录（如果是标准上传的话）
        # 或者是 image_path 的父目录的父目录 + "files" ?
        # 通常 image_path 在 .../files/image.jpg
        files_dir = image_path.parent
        
        # 确保我们找到了 files 目录
        if files_dir.name != "files":
            # 尝试向上查找
            if (files_dir / "files").exists():
                files_dir = files_dir / "files"
            elif (files_dir.parent / "files").exists():
                files_dir = files_dir.parent / "files"
            else:
                # 如果找不到标准的 files 目录，就用 image_path.parent 作为基准
                pass

        image_stem = image_path.stem
        # 使用 pages 目录来避免在桌面上创建图标
        # 结构: .../files/pages/{image_name}/extracted.md
        pages_dir = files_dir / "pages" / image_stem
        pages_dir.mkdir(parents=True, exist_ok=True)
             
        md_filename = f"{image_stem}_extracted.md"
        md_path = pages_dir / md_filename

        # 如果不强制刷新且文件存在，直接返回内容
        if not force and md_path.exists():
            info(f"📄 找到已有提取结果: {md_path}")
            with open(md_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 尝试解析回 JSON 结构
            text_content = ""
            image_content = ""
            
            # 简单解析Markdown
            if "## 文本提取" in content and "## 图片描述" in content:
                parts = content.split("## 图片描述")
                if len(parts) >= 2:
                    text_part = parts[0]
                    if "## 文本提取" in text_part:
                        text_content = text_part.split("## 文本提取")[1].strip()
                    image_content = parts[1].strip()
            else:
                text_content = content
            
            return {
                'success': True,
                'text_content': text_content,
                'image_content': image_content,
                'saved_path': str(md_path),
                'cached': True
            }

        info(f"处理图片: {image_path}")

        # 读取图片并转base64
        import base64
        with open(image_path, 'rb') as f:
            img_bytes = f.read()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        # 构造 Prompt
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """你正在分析一张图片。请完成以下两个独立任务：

**任务1：文本提取（OCR）**
- 识别并提取图片中的**所有文字内容**。
- 保持原有的层次结构和格式。
- 使用Markdown格式（# 标题、- 列表等）。
- 如果没有文字，返回空字符串。

**任务2：图片内容描述**
- 详细描述图片展示的具体内容。
- 如果是图表，描述图表类型、数据趋势等。
- 如果没有明显内容，返回空字符串。

**输出格式（必须是纯JSON）：**
```json
{
  "text_extraction": "文字内容（Markdown）",
  "visual_description": "图片描述"
}
```
只返回JSON，不要markdown代码块标记。"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_base64}"
                        }
                    }
                ]
            }
        ]

        # 调用LLM
        current_config = llm_service.get_config()
        current_provider = current_config.get('provider', 'qwen')
        
        vision_model_map = {
            'qwen': 'qwen-vl-plus',
            'openai': 'gpt-4o',
            'anthropic': 'claude-3-5-sonnet-20241022',
            'gemini': 'gemini-1.5-pro'
        }
        use_model = vision_model_map.get(current_provider, 'qwen-vl-plus')

        accumulated_content = ""
        async for chunk in llm_service.chat_completion(messages, stream=False, override_model=use_model):
            accumulated_content += chunk
        
        info(f"✅ 图片内容提取完成: {len(accumulated_content)} 字")

        # 解析 JSON
        text_content = ""
        image_content = ""
        try:
            json_content = accumulated_content.strip()
            if json_content.startswith("```json"):
                json_content = json_content[7:]
            if json_content.startswith("```"):
                json_content = json_content[3:]
            if json_content.endswith("```"):
                json_content = json_content[:-3]
            json_content = json_content.strip()
            
            import json
            parsed = json.loads(json_content)
            text_content = parsed.get("text_extraction", "")
            image_content = parsed.get("visual_description", "")
        except Exception as e:
            info(f"JSON解析失败，返回原始内容: {e}")
            text_content = accumulated_content
            image_content = "（解析失败）"

        # 保存结果
        # md_path 已经在上面定义了
        
        final_content = f"# 图片提取内容: {image_path.name}\n\n## 文本提取\n\n{text_content}\n\n## 图片描述\n\n{image_content}"
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
            
        info(f"💾 内容已保存到: {md_path}")
        
        return {
            'success': True,
            'text_content': text_content,
            'image_content': image_content,
            'saved_path': str(md_path),
            'cached': False
        }

    except Exception as e:
        error(f"图片提取失败: {e}")
        import traceback
        error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/boards/{board_id}/windows/{window_id}/annotations/batch/summary-note")
async def generate_batch_summary_note(
    board_id: str,
    window_id: str,
    request: Request
):
    """生成PDF全文档阅读笔记（使用Split-Merge策略）"""
    try:
        # 获取请求体参数
        body = await request.json()
        summary_style = body.get('summary_style', 'detailed')
        custom_prompt = body.get('custom_prompt', '')
        
        info(f"生成全文档阅读笔记: board_id={board_id}, window_id={window_id}, style={summary_style}")
        
        # 预设Prompt模板
        SUMMARY_PROMPTS = {
            'detailed': """你是一位专业的学术和文档分析助手。请仔细阅读以下PDF文档的全部内容，生成一份详尽的、结构清晰的**全文档阅读笔记**。

**笔记生成要求**：
1. **核心观点提炼**：首先用简练的语言概括文档的核心主旨（Executive Summary）。
2. **结构化内容梳理**：按照文档的逻辑结构（章节或主题），详细记录关键信息、重要数据、论点和结论。请保留足够的细节，不要只是列大纲，另外，需要在重点或者细节位置提供页码，以(page XXX)的形式提供。
3. **重要概念解析**：解释文档中出现的关键术语和概念。
4. **总结与启示**：总结文档的价值，并给出你的阅读心得或批判性思考。
5. **格式要求**：使用标准Markdown格式，利用多级标题、列表、加粗等使笔记易于阅读。

请直接输出Markdown格式的笔记内容。""",
            'concise': """请阅读文档内容，生成一份**简洁的摘要笔记**。

**要求**：
1. 提炼核心论点，忽略次要细节。
2. 使用要点列表（Bullet points）形式呈现。
3. 控制篇幅，专注于“文档讲了什么”和“主要结论是什么”。
4. 适合快速浏览。""",
            'academic': """请以**学术综述**的风格撰写这份文档的笔记。

**要求**：
1. **背景与问题**：文档研究了什么问题？背景是什么？
2. **方法与论证**：作者使用了什么方法或论据？
3. **主要发现**：得出了什么结论？
4. **学术价值**：该文档在相关领域的贡献是什么？
5. **引用与术语**：准确引用文中的专业术语。""",
            'outline': """请为这份文档生成一份**大纲式笔记**。

**要求**：
1. 严格遵循文档的目录结构。
2. 在每个层级下，用简短的句子概括该部分的内容。
3. 重点展示文档的逻辑框架和层次关系。
4. 适合梳理文档结构。"""
        }
        
        # 确定Prompt模板
        base_prompt_template = custom_prompt if summary_style == 'custom' else SUMMARY_PROMPTS.get(summary_style, SUMMARY_PROMPTS['detailed'])
        
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
        
        # 创建或获取总笔记对话记录
        summary_conv_id = f"summary-note-{window_id}"
        conversation = conversation_manager.get_conversation(board_id, summary_conv_id, page=None, limit=None)
        if not conversation:
            conversation = conversation_manager.create_conversation(
                board_id,
                title=f"全文档笔记 - {pdf_filename}"
            )
            conversations_dir = conversation_manager.get_board_conversations_dir(board_id)
            old_file = conversations_dir / f"{conversation['id']}.json"
            new_file = conversations_dir / f"{summary_conv_id}.json"
            if old_file.exists():
                old_file.rename(new_file)
            conversation['id'] = summary_conv_id
        
        # 准备SSE流式响应
        async def generate_summary_stream():
            try:
                # 判断使用哪种方法
                if total_chars <= SMALL_FILE_THRESHOLD:
                    # 方法1：小文件，直接发送全部内容
                    info(f"使用直接方法（文件较小）: {total_chars} 字符")
                    yield f"data: {json.dumps({'type': 'status', 'message': '文件较小，直接生成笔记中...'}, ensure_ascii=False)}\n\n"
                    
                    # 构建完整文本
                    full_text = "\n\n".join([
                        f"=== 第{p['page']}页 ===\n{p['content']}"
                        for p in all_pages_content
                    ])
                    
                    # 构建最终提示词
                    prompt = f"""{base_prompt_template}

**文档信息**：
- 文件名: {pdf_filename}
- 总页数: {total_pages}

**文档内容**：
{full_text}"""
                    
                    # 发送给LLM
                    user_message = {
                        "role": "user",
                        "content": prompt,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": {
                            "action": "generate_batch_summary_note",
                            "pdf_filename": pdf_filename,
                            "window_id": window_id,
                            "total_pages": total_pages,
                            "total_chars": total_chars,
                            "method": "direct",
                            "style": summary_style
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
                            "action": "generate_batch_summary_note",
                            "method": "direct",
                            "total_pages": total_pages,
                            "total_chars": total_chars
                        }
                    }
                    
                    conversation_manager.add_message(board_id, summary_conv_id, user_message)
                    conversation_manager.add_message(board_id, summary_conv_id, assistant_message)
                    
                    # === 新增：保存总笔记到文件（小文件模式） ===
                    try:
                        # 1. 找到PDF文件所在的目录
                        pdf_file_path = Path(target_window.get('content'))
                        if not pdf_file_path.is_absolute():
                            # 如果是相对路径，需要找到它所在的展板目录
                            board_dir = None
                            for course_dir in content_manager.file_manager.courses_dir.iterdir():
                                if course_dir.is_dir():
                                    potential_board_dir = course_dir / board_id
                                    if potential_board_dir.exists():
                                        board_dir = potential_board_dir
                                        break
                            
                            if board_dir:
                                pdf_file_path = board_dir / pdf_file_path
                        
                        if pdf_file_path and pdf_file_path.exists():
                            pdf_name = pdf_file_path.stem
                            pages_dir = pdf_file_path.parent / "pages" / pdf_name
                            pages_dir.mkdir(parents=True, exist_ok=True)
                            
                            summary_file_path = pages_dir / "summary_note.md"
                            
                            with open(summary_file_path, 'w', encoding='utf-8') as f:
                                f.write(accumulated_content)
                            
                            info(f"✅ 全文档笔记已保存至: {summary_file_path}")
                            yield f"data: {json.dumps({'type': 'saved', 'path': str(summary_file_path)}, ensure_ascii=False)}\n\n"
                        else:
                            error(f"无法保存笔记文件，PDF路径不存在: {pdf_file_path}")
                    except Exception as e:
                        error(f"保存笔记文件失败: {e}")
                    # ============================

                    yield f"data: {json.dumps({'type': 'complete', 'content': accumulated_content}, ensure_ascii=False)}\n\n"
                    
                else:
                    # 方法2：大文件，Split-Merge策略
                    info(f"使用Split-Merge方法（文件较大）: {total_chars} 字符")
                    yield f"data: {json.dumps({'type': 'status', 'message': '文件较大，使用分组分析策略...'}, ensure_ascii=False)}\n\n"
                    
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
                    yield f"data: {json.dumps({'type': 'status', 'message': f'分为{len(groups)}组进行逐个分析...'}, ensure_ascii=False)}\n\n"
                    
                    # 对每组进行分析（生成局部笔记）
                    group_notes = []
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
                        
                        # 构建子模型提示词 - 局部笔记
                        sub_prompt = f"""你是一位专业的文档分析助手。请分析以下PDF文档片段的内容，生成一份**局部阅读笔记**。

**文档信息**：
- 文件名: {pdf_filename}
- 分析范围: 第{group['page_start']}-{group['page_end']}页（共{total_pages}页）
- 组号: {group_num}/{len(groups)}

**文档片段内容**：
{group_text}

**任务要求**：
1. 仔细阅读该片段，提取其中的关键信息、主要论点和重要数据。
2. **不要生成大纲**，而是生成内容详实的笔记段落。
3. 如果片段包含完整的章节，请明确章节标题。
4. 标记出该部分中最重要的概念。
5. 保持客观、准确。

请输出Markdown格式的笔记内容。"""
                        
                        # 创建子对话记录
                        sub_conv_id = f"summary-note-{window_id}-part{group_num}"
                        sub_conversation = conversation_manager.get_conversation(board_id, sub_conv_id, page=None, limit=None)
                        if not sub_conversation:
                            sub_conversation = conversation_manager.create_conversation(
                                board_id,
                                title=f"全文档笔记-分组{group_num} - {pdf_filename}"
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
                                "action": "generate_batch_summary_note_sub",
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
                                # 将子模型的输出也流式传递给前端（作为进度预览）
                                yield f"data: {json.dumps({'type': 'group_content', 'group': group_num, 'content': chunk}, ensure_ascii=False)}\n\n"
                        
                        # 保存子模型消息
                        sub_assistant_message = {
                            "role": "assistant",
                            "content": sub_accumulated_content,
                            "timestamp": datetime.now().isoformat(),
                            "metadata": {
                                "action": "generate_batch_summary_note_sub",
                                "group_number": group_num,
                                "method": "split"
                            }
                        }
                        
                        conversation_manager.add_message(board_id, sub_conv_id, sub_user_message)
                        conversation_manager.add_message(board_id, sub_conv_id, sub_assistant_message)
                        
                        group_notes.append({
                            'group_number': group_num,
                            'content': sub_accumulated_content
                        })
                        yield f"data: {json.dumps({'type': 'group_done', 'group': group_num}, ensure_ascii=False)}\n\n"
                    
                    # 汇总所有分组笔记
                    yield f"data: {json.dumps({'type': 'status', 'message': '所有分组分析完成，正在整合成总笔记...'}, ensure_ascii=False)}\n\n"
                    
                    # 构建汇总提示词 - Merge
                    groups_summary = "\n\n".join([
                        f"=== 第{g['group_number']}部分笔记 ===\n{g['content']}"
                        for g in group_notes
                    ])
                    
                    merge_prompt = f"""{base_prompt_template}

**文档信息**：
- 文件名: {pdf_filename}
- 总页数: {total_pages}

**各部分局部笔记（原始素材）**：
{groups_summary}

**特别指示**：
以上内容是基于文档分段生成的局部笔记。请根据你的笔记风格要求，将这些素材整合成一份完整的、连贯的全文档笔记。确保整合后的内容流畅，不要有明显的拼接痕迹。"""
                    
                    # 发送给LLM进行汇总
                    merge_user_message = {
                        "role": "user",
                        "content": merge_prompt,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": {
                            "action": "generate_batch_summary_note_merge",
                            "pdf_filename": pdf_filename,
                            "window_id": window_id,
                            "total_pages": total_pages,
                            "total_groups": len(groups),
                            "method": "split_merge",
                            "style": summary_style
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
                            "action": "generate_batch_summary_note_merge",
                            "method": "split_merge",
                            "total_pages": total_pages,
                            "total_groups": len(groups)
                        }
                    }
                    
                    conversation_manager.add_message(board_id, summary_conv_id, merge_user_message)
                    conversation_manager.add_message(board_id, summary_conv_id, merge_assistant_message)

                    # === 新增：保存总笔记到文件 ===
                    try:
                        # 1. 找到PDF文件所在的目录
                        pdf_file_path = Path(target_window.get('content'))
                        if not pdf_file_path.is_absolute():
                            # 如果是相对路径，需要找到它所在的展板目录
                            # 这里使用与content_manager中相同的逻辑
                            board_dir = None
                            for course_dir in content_manager.file_manager.courses_dir.iterdir():
                                if course_dir.is_dir():
                                    potential_board_dir = course_dir / board_id
                                    if potential_board_dir.exists():
                                        board_dir = potential_board_dir
                                        break
                            
                            if board_dir:
                                pdf_file_path = board_dir / pdf_file_path
                        
                        if pdf_file_path and pdf_file_path.exists():
                            pdf_name = pdf_file_path.stem
                            pages_dir = pdf_file_path.parent / "pages" / pdf_name
                            pages_dir.mkdir(parents=True, exist_ok=True)
                            
                            summary_file_path = pages_dir / "summary_note.md"
                            
                            with open(summary_file_path, 'w', encoding='utf-8') as f:
                                f.write(merge_accumulated_content)
                            
                            info(f"✅ 全文档笔记已保存至: {summary_file_path}")
                            yield f"data: {json.dumps({'type': 'saved', 'path': str(summary_file_path)}, ensure_ascii=False)}\n\n"
                        else:
                            error(f"无法保存笔记文件，PDF路径不存在: {pdf_file_path}")
                            yield f"data: {json.dumps({'type': 'error', 'error': '无法保存笔记文件，PDF路径无效'}, ensure_ascii=False)}\n\n"

                    except Exception as e:
                        error(f"保存笔记文件失败: {e}")
                        yield f"data: {json.dumps({'type': 'error', 'error': f'保存文件失败: {str(e)}'}, ensure_ascii=False)}\n\n"
                    # ============================
                    
                    yield f"data: {json.dumps({'type': 'complete', 'content': merge_accumulated_content}, ensure_ascii=False)}\n\n"

            except Exception as e:
                error(f"生成全文档笔记失败: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_summary_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"生成全文档笔记失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成全文档笔记失败: {str(e)}")


# ... imports ...
from pydantic import BaseModel

# ... other models ...

class TTSRequest(BaseModel):
    text: str
    text_lang: str = "zh"
    ref_audio_path: Optional[str] = None
    prompt_text: Optional[str] = None
    prompt_lang: Optional[str] = "zh"
    top_k: int = 5
    top_p: float = 1
    temperature: float = 1
    text_split_method: str = "cut5"
    batch_size: int = 1
    batch_threshold: float = 0.75
    split_bucket: bool = True
    speed_factor: float = 1.0
    fragment_interval: float = 0.3
    seed: int = -1
    media_type: str = "wav"
    streaming_mode: bool = False
    parallel_infer: bool = True
    repetition_penalty: float = 1.35

# ... other endpoints ...

@app.post("/api/tts/generate")
async def generate_tts(request: TTSRequest):
    """调用 GPT-SoVITS 生成语音"""
    try:
        info(f"收到 TTS 请求: {request.text[:50]}...")
        
        # 构造 GPT-SoVITS 请求数据
        # 根据官方 API 文档，通常是一个 POST 请求到默认端口 9880
        # 端点通常是 /tts 或 /
        
        # 简单起见，这里先实现基本的 /tts 端点调用
        payload = request.dict()
        
        # 如果没有提供参考音频，使用默认的（这里需要您配置一个默认参考音频路径）
        # TODO: 在设置中允许用户上传或选择参考音频
        if not payload.get("ref_audio_path"):
            # 这里暂时硬编码一个示例，实际部署时需要替换为存在的音频文件
            # 或者让 GPT-SoVITS 使用它自己的默认值（如果支持）
            # 更好的做法是让前端必须传递，或者后端提供一个默认文件
            pass

        timeout = aiohttp.ClientTimeout(total=300) # 5分钟超时
        async with aiohttp.ClientSession(timeout=timeout) as session:
            # 尝试调用 GPT-SoVITS API
            # 注意：GPT-SoVITS 的 API 结构可能随版本变化，这里假设是标准的 GET/POST
            # 我们可以尝试 GET 方式，因为它比较简单
            
            # 构建 GET 参数 (GPT-SoVITS 常用方式)
            params = {
                "text": request.text,
                "text_lang": request.text_lang,
                "ref_audio_path": request.ref_audio_path or "default_ref.wav", # 需替换
                "prompt_text": request.prompt_text or "",
                "prompt_lang": request.prompt_lang,
                "text_split_method": request.text_split_method,
                "batch_size": request.batch_size,
                "media_type": request.media_type,
                "speed_factor": request.speed_factor
            }
            
            # 如果有参考音频路径，使用它
            # 这里为了测试，如果用户没有传参考音频，我们暂时不传这个参数，看看 GPT-SoVITS 是否有默认行为
            # 或者报错。通常 GPT-SoVITS 需要参考音频。
            
            # 模拟：如果连接失败，返回错误
            try:
                async with session.get(f"{GPT_SOVITS_URL}/tts", params=params) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise HTTPException(status_code=response.status, detail=f"GPT-SoVITS Error: {error_text}")
                    
                    # 读取音频数据
                    audio_data = await response.read()
                    
                    # 保存文件
                    filename = f"tts_{uuid.uuid4()}.{request.media_type}"
                    # 假设我们把音频保存在第一个课程的第一个展板的 files/audio 目录下
                    # 或者更简单，放在 static/temp 目录下
                    save_dir = DATA_DIR / "temp" / "audio"
                    save_dir.mkdir(parents=True, exist_ok=True)
                    save_path = save_dir / filename
                    
                    with open(save_path, "wb") as f:
                        f.write(audio_data)
                    
                    # 返回 URL
                    audio_url = f"/static/files/temp/audio/{filename}"
                    return {"success": True, "audio_url": audio_url, "duration": 0} # 暂不计算时长

            except aiohttp.ClientConnectorError:
                raise HTTPException(status_code=503, detail="无法连接到 GPT-SoVITS 服务，请确认服务已启动 (默认端口 9880)")

    except Exception as e:
        error(f"TTS 生成失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/boards/{board_id}/windows/{window_id}/annotations/batch/generate-script-section")
async def generate_narrator_script_section(
    board_id: str,
    window_id: str,
    request: Request
):
    """批量生成讲稿：为一个分段的所有页面生成演讲稿"""
    try:
        request_body = await request.json()
        section_index = request_body.get('section_index', 0)
        section_data = request_body.get('section_data')
        subdivision_data = request_body.get('subdivision_data')
        previous_subdivision = request_body.get('previous_subdivision')  # 获取上一分段信息
        prompt_template = request_body.get('promptTemplate', '')
        
        info(f"开始为分段 {section_index} 批量生成讲稿")
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        target_window = None
        for window in windows:
            if window.get('id') == window_id:
                target_window = window
                break
        
        if not target_window:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        page_start = section_data['page_start']
        page_end = section_data['page_end']
        
        # 获取目标生成范围（去重后）
        target_range = request_body.get('target_range', {})
        target_start = target_range.get('start', page_start)
        target_end = target_range.get('end', page_end)
        
        async def generate_stream():
            try:
                yield f"data: {json.dumps({'type': 'status', 'message': f'正在为第 {target_start}-{target_end} 页生成讲稿...'}, ensure_ascii=False)}\n\n"
                
                # 读取该分段所有页面的内容（作为完整上下文，即使不在目标范围内）
                pages_content = []
                for page in range(page_start, page_end + 1):
                    page_data = content_manager.get_pdf_page_contents(board_id, window_id, page)
                    if page_data and page_data.get('current'):
                        pages_content.append({
                            'page': page,
                            'content': page_data['current']
                        })
                
                if not pages_content:
                    error_msg = f'未找到分段内容，页码范围: {page_start}-{page_end}'
                    yield f"data: {json.dumps({'type': 'error', 'error': error_msg}, ensure_ascii=False)}\n\n"
                    return
                
                # 构建完整的内容文本
                full_content = ""
                for page_info in pages_content:
                    full_content += f"\n\n=== 第{page_info['page']}页 ===\n{page_info['content']}"
                
                # 获取分段描述
                section_description = ''
                if subdivision_data:
                     section_description = subdivision_data.get('section_summary') or section_data.get('description') or ''

                # 获取上一分段描述（用于上下文连贯）
                previous_context_text = ""
                if previous_subdivision:
                    prev_summary = previous_subdivision.get('section_summary', '')
                    prev_title = previous_subdivision.get('title', '')
                    if prev_summary:
                        previous_context_text = f"\n**前情提要（上一分段上下文）**：\n- 上一分段标题: {prev_title}\n- 上一分段主要内容: {prev_summary}\n- 提示：请承接上述内容，保持演讲的连贯性，避免生硬的开场。"

                # 默认讲稿要求
                default_req = "请为每一页撰写一份口语化的演讲稿。\n要求：\n1. 时间控制在 30-60 秒。\n2. 语言自然流畅，适合朗读。\n3. 不要念标题，而是解释核心观点。\n4. 使用第一人称。"
                script_requirement = prompt_template if prompt_template else default_req
                
                prompt = f"""你是一位专业的演讲者。请根据以下PDF分段内容（包含上下文），为指定范围的页面撰写演讲稿。

**分段上下文信息**：
- 分段标题: {section_data.get('title', '未命名')}
- 分段描述: {section_description}
- 完整上下文页码: 第{page_start}页 - 第{page_end}页
{previous_context_text}

**分段完整内容**：
{full_content}

**任务目标**：
请仅为 **第{target_start}页 到 第{target_end}页** 生成演讲稿。
（第{page_start}页到第{target_start-1}页的内容仅供参考，不需要生成讲稿）

**讲稿要求**：
{script_requirement}

**输出格式**（必须严格遵守JSON格式）：
```json
{{
  "scripts": [
    {{
      "page": {target_start},
      "script": "第{target_start}页的演讲稿内容..."
    }},
    {{
      "page": {target_start + 1},
      "script": "第{target_start + 1}页的演讲稿内容..."
    }}
  ]
}}
```
请确保scripts数组包含从 **{target_start}** 到 **{target_end}** 的所有页面。
直接输出JSON，不要添加任何额外的说明文字。"""
                
                messages = [{
                    "role": "user",
                    "content": prompt,
                    "timestamp": datetime.now().isoformat()
                }]
                
                accumulated_content = ""
                
                # 调用LLM
                async for chunk in llm_service.chat_completion(messages, stream=True):
                    if chunk:
                        accumulated_content += chunk
                
                # 解析结果
                try:
                    content = accumulated_content.strip()
                    if content.startswith('```'):
                        lines = content.split('\n')
                        if lines[0].startswith('```'): lines = lines[1:]
                        if lines[-1].startswith('```'): lines = lines[:-1]
                        content = '\n'.join(lines)
                    
                    result_data = json.loads(content)
                    scripts = result_data.get('scripts', [])
                    
                    for script_item in scripts:
                        page = script_item.get('page')
                        text = script_item.get('script')
                        if page and text:
                            yield f"data: {json.dumps({'type': 'page_done', 'page': page, 'content': text}, ensure_ascii=False)}\n\n"
                    
                    yield f"data: {json.dumps({'type': 'complete', 'total': len(scripts)}, ensure_ascii=False)}\n\n"
                    
                except json.JSONDecodeError as e:
                    error(f"解析讲稿JSON失败: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'error': f'JSON解析失败: {str(e)}'}, ensure_ascii=False)}\n\n"

            except Exception as e:
                error(f"批量生成讲稿失败: {e}")
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
        error(f"批量生成讲稿接口错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/boards/{board_id}/windows/{window_id}/narrator/scripts/{page}")
async def get_narrator_script(board_id: str, window_id: str, page: int):
    try:
        content = content_manager.get_narrator_script(board_id, window_id, page)
        return {"success": True, "content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/api/boards/{board_id}/windows/{window_id}/narrator/scripts/{page}")
async def save_narrator_script(board_id: str, window_id: str, page: int, request: Request):
    try:
        data = await request.json()
        content = data.get('content', '')
        success = content_manager.save_narrator_script(board_id, window_id, page, content)
        return {"success": success}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/boards/{board_id}/windows/{window_id}/narrator/audio/{page}")
async def get_narrator_audio(
    board_id: str,
    window_id: str,
    page: int
):
    """获取PDF指定页面的语音文件（仅获取，不生成）"""
    try:
        existing_audio_path = content_manager.get_narrator_audio_path(board_id, window_id, page)
        if existing_audio_path:
            return FileResponse(existing_audio_path, media_type="audio/wav")
        raise HTTPException(status_code=404, detail="语音文件不存在")
    except HTTPException:
        raise
    except Exception as e:
        error(f"获取语音失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取语音失败: {str(e)}")

@app.post("/api/boards/{board_id}/windows/{window_id}/narrator/audio/{page}")
async def generate_narrator_audio(
    board_id: str,
    window_id: str,
    page: int,
    request: Request
):
    """生成PDF指定页面的语音（强制重新生成）"""
    try:
        # 1. 获取参数
        request_body = await request.json()
        text = request_body.get('text', '')
        prompt_audio_path = request_body.get('prompt_audio_path', '') # 前端暂未传，预留
        text_language = request_body.get('text_language', 'zh')
        
        if not text:
            raise HTTPException(status_code=400, detail="缺少文本内容")
            
        # 3. 准备 TTS 请求
        ref_audio_path = prompt_audio_path
        prompt_text = request_body.get('prompt_text', '')
        prompt_lang = request_body.get('prompt_lang', 'zh')
        
        # 默认参考音频路径
        ref_dir = DATA_DIR / "ref_audio"
        default_ref_path = ref_dir / "default.wav"
        
        if not ref_audio_path and default_ref_path.exists():
            ref_audio_path = str(default_ref_path.absolute())
            meta_path = ref_dir / "default.json"
            if meta_path.exists():
                try:
                    with open(meta_path, 'r') as f:
                        meta = json.load(f)
                        if not prompt_text:
                            prompt_text = meta.get('text', '')
                        if not prompt_lang:
                            prompt_lang = meta.get('language', 'zh')
                except:
                    pass
        
        # 如果还是没有，尝试使用 GPT-SoVITS 目录下的示例音频作为最后的 Fallback
        if not ref_audio_path:
             # 这是一个 hack，让用户第一次能跑通
             # 如果没有 default.wav，我们报错提示用户上传
             raise HTTPException(status_code=400, detail="未设置参考音频，请在设置中上传一段5-10秒的参考音频")

        # 4. 调用 TTS 服务
        payload = {
            "text": text,
            "text_language": text_language,
            "refer_wav_path": ref_audio_path,
            "prompt_text": prompt_text,
            "prompt_language": prompt_lang,
            "cut_punc": "，。！"
        }
        
        info(f"调用TTS: {GPT_SOVITS_URL}, text len: {len(text)}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{GPT_SOVITS_URL}/", json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    error(f"TTS API Error: {error_text}")
                    raise HTTPException(status_code=response.status, detail=f"TTS服务错误: {error_text}")
                
                audio_content = await response.read()
                
        # 5. 保存并返回
        saved_path = content_manager.save_narrator_audio(board_id, window_id, page, audio_content)
        
        if saved_path:
            return FileResponse(saved_path, media_type="audio/wav")
        else:
            raise HTTPException(status_code=500, detail="保存音频失败")

    except HTTPException:
        raise
    except Exception as e:
        error(f"生成语音失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成语音失败: {str(e)}")

@app.get("/api/tts/reference")
async def get_tts_reference():
    """获取当前默认参考音频信息"""
    try:
        ref_dir = DATA_DIR / "ref_audio"
        meta_path = ref_dir / "default.json"
        wav_path = ref_dir / "default.wav"
        
        if not meta_path.exists() or not wav_path.exists():
            return {"exists": False}
            
        with open(meta_path, 'r') as f:
            meta = json.load(f)
            
        return {
            "exists": True,
            "text": meta.get("text", ""),
            "language": meta.get("language", "zh")
        }
    except Exception as e:
        error(f"获取参考音频信息失败: {e}")
        return {"exists": False, "error": str(e)}

@app.post("/api/tts/reference")
async def upload_tts_reference(
    file: UploadFile = File(...),
    text: str = Form(...),
    language: str = Form("zh")
):
    """上传默认参考音频"""
    try:
        ref_dir = DATA_DIR / "ref_audio"
        ref_dir.mkdir(parents=True, exist_ok=True)
        
        file_path = ref_dir / "default.wav"
        meta_path = ref_dir / "default.json"
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 即使text为空，也保存下来（或者合并旧的text？不，前端会负责传正确的）
        # 如果text是空的，我们尝试读取旧的meta里的text，避免覆盖成空（如果是为了修正的话）
        # 但根据前端逻辑，上传时text可能就是空的。
        # 我们这里允许保存空text，生成时如果为空会报错。
        
        meta_data = {"text": text, "language": language}
        # 如果传入的text是空的，尝试保留旧的text
        if not text and meta_path.exists():
            try:
                with open(meta_path, 'r') as f:
                    old_meta = json.load(f)
                    if old_meta.get('text'):
                        meta_data['text'] = old_meta['text']
            except:
                pass

        with open(meta_path, "w") as f:
            json.dump(meta_data, f)
            
        return {"success": True, "message": "参考音频已更新"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")

@app.get("/api/tts/status")
async def get_tts_status():
    """检查TTS服务状态"""
    try:
        async with aiohttp.ClientSession() as session:
            # 尝试调用 control 接口或直接 ping
            async with session.get(f"{GPT_SOVITS_URL}/control") as response:
                # 只要能连通就行，哪怕返回 405 Method Not Allowed
                return {"status": "online", "version": "v2"}
    except Exception as e:
        return {"status": "offline", "error": str(e)}


@app.get("/api/tts/models")
async def get_tts_models():
    """获取可用的GPT和SoVITS模型列表"""
    try:
        # 详细的路径调试信息
        cwd = Path.cwd().resolve()
        info(f"当前工作目录: {cwd}")
        
        # 尝试定位 GPT-SoVITS 目录
        # 策略：向上一级一级查找，直到找到 GPT-SoVITS
        candidate_dir = cwd
        base_dir = None
        
        # 向上查找3层
        for _ in range(4):
            check_path = candidate_dir / "GPT-SoVITS"
            # info(f"尝试查找: {check_path}") # 调试用
            if check_path.exists() and (check_path / "GPT_weights").exists():
                base_dir = check_path
                break
            
            # 也许 GPT-SoVITS 就在当前目录的上一级 (即 candidate_dir 是兄弟目录)
            sibling_path = candidate_dir.parent / "GPT-SoVITS"
            if sibling_path.exists() and (sibling_path / "GPT_weights").exists():
                base_dir = sibling_path
                break
                
            candidate_dir = candidate_dir.parent
            
        if not base_dir:
            # 最后的硬编码尝试
            hardcoded = Path("/home/obeygravity/Projects/GPT-SoVITS")
            if hardcoded.exists():
                base_dir = hardcoded
        
        if not base_dir:
            error(f"未找到 GPT-SoVITS 目录, start_from={cwd}")
            return {"gpt_weights": [], "sovits_weights": [], "error": f"未找到 GPT-SoVITS 目录 (cwd: {cwd})"}

        info(f"定位到 GPT-SoVITS 目录: {base_dir}")

        gpt_weights = []
        gpt_dir = base_dir / "GPT_weights"
        if gpt_dir.exists():
            gpt_weights = [f.name for f in gpt_dir.glob("*.ckpt")]
            
        sovits_weights = []
        sovits_dir = base_dir / "SoVITS_weights"
        if sovits_dir.exists():
            sovits_weights = [f.name for f in sovits_dir.glob("*.pth")]
            
        info(f"找到 GPT模型: {len(gpt_weights)}个, SoVITS模型: {len(sovits_weights)}个")
        return {
            "gpt_weights": sorted(gpt_weights),
            "sovits_weights": sorted(sovits_weights)
        }
    except Exception as e:
        error(f"获取模型列表失败: {e}")
        return {"gpt_weights": [], "sovits_weights": [], "error": str(e)}

@app.post("/api/tts/set_model")
async def set_tts_model(request: Request):
    """切换GPT-SoVITS模型"""
    try:
        data = await request.json()
        gpt_name = data.get("gpt_model")
        sovits_name = data.get("sovits_model")
        
        # 重新定位 base_dir (同上)
        possible_paths = [
            Path("../../GPT-SoVITS"), 
            Path("../GPT-SoVITS"),
            Path("GPT-SoVITS"),
        ]
        base_dir = None
        for p in possible_paths:
            if p.exists() and (p / "GPT_weights").exists():
                base_dir = p.resolve() # 获取绝对路径
                break
        
        if not base_dir:
            raise HTTPException(status_code=500, detail="未找到 GPT-SoVITS 目录")

        payload = {}
        if gpt_name:
            payload["gpt_model_path"] = str(base_dir / "GPT_weights" / gpt_name)
        if sovits_name:
            payload["sovits_model_path"] = str(base_dir / "SoVITS_weights" / sovits_name)
            
        info(f"切换模型: {payload}")
        
        async with aiohttp.ClientSession() as session:
            async with session.post(f"{GPT_SOVITS_URL}/set_model", json=payload) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise HTTPException(status_code=resp.status, detail=f"切换失败: {text}")
                return await resp.json()
                
    except Exception as e:
        error(f"切换模型出错: {e}")
        raise HTTPException(status_code=500, detail=str(e))

