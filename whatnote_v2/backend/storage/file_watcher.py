"""
文件监控服务
使用 watchdog 监控文件系统变化，并通过 WebSocket 通知前端
"""

import os
import json
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
from datetime import datetime
import re
import time

class FileWatcherHandler(FileSystemEventHandler):
    def __init__(self, file_watcher):
        super().__init__()
        self.file_watcher = file_watcher
        
    def on_created(self, event):
        if not event.is_directory:
            try:
                if self.file_watcher.loop and self.file_watcher.loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.file_watcher.handle_file_created(event.src_path), 
                        self.file_watcher.loop
                    )
            except Exception as e:
                print(f"处理文件创建事件失败: {e}")
    
    def on_modified(self, event):
        if not event.is_directory:
            try:
                if self.file_watcher.loop and self.file_watcher.loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.file_watcher.handle_file_modified(event.src_path), 
                        self.file_watcher.loop
                    )
            except Exception as e:
                print(f"处理文件修改事件失败: {e}")
    
    def on_deleted(self, event):
        if not event.is_directory:
            try:
                if self.file_watcher.loop and self.file_watcher.loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.file_watcher.handle_file_deleted(event.src_path), 
                        self.file_watcher.loop
                    )
            except Exception as e:
                print(f"处理文件删除事件失败: {e}")
    
    def on_moved(self, event):
        if not event.is_directory:
            try:
                if self.file_watcher.loop and self.file_watcher.loop.is_running():
                    asyncio.run_coroutine_threadsafe(
                        self.file_watcher.handle_file_moved(event.src_path, event.dest_path), 
                        self.file_watcher.loop
                    )
            except Exception as e:
                print(f"处理文件移动事件失败: {e}")

class FileWatcher:
    def __init__(self, data_dir: Path, websocket_manager):
        self.data_dir = Path(data_dir)
        self.websocket_manager = websocket_manager
        self.observer = Observer()
        self.watched_paths = set()
        self.file_manager = None
        self.content_manager = None
        self.loop = None
        
        # 防抖机制：避免频繁的文件修改通知
        self.modified_files = {}  # 存储文件路径和最后修改时间
        self.debounce_delay = 2.0  # 2秒防抖延迟
        
        # 支持的文件类型映射
        self.file_type_mapping = {
            '.txt': 'text',
            '.md': 'text',
            '.jpg': 'image',
            '.jpeg': 'image',
            '.png': 'image',
            '.gif': 'image',
            '.bmp': 'image',
            '.webp': 'image',
            '.mp4': 'video',
            '.avi': 'video',
            '.mov': 'video',
            '.wmv': 'video',
            '.flv': 'video',
            '.webm': 'video',
            '.mp3': 'audio',
            '.wav': 'audio',
            '.flac': 'audio',
            '.aac': 'audio',
            '.ogg': 'audio',
            '.wma': 'audio',
            '.pdf': 'pdf'
        }
    
    def set_managers(self, file_manager, content_manager):
        """设置文件管理器和内容管理器"""
        self.file_manager = file_manager
        self.content_manager = content_manager
    
    def start_watching(self):
        """开始监控文件系统"""
        # 保存当前事件循环
        try:
            self.loop = asyncio.get_event_loop()
        except RuntimeError:
            self.loop = None
        
        courses_dir = self.data_dir / "courses"
        if courses_dir.exists():
            # 监控所有课程目录
            for course_dir in courses_dir.iterdir():
                if course_dir.is_dir():
                    self._watch_course_directory(course_dir)
        
        self.observer.start()
        print(f"文件监控服务已启动，监控目录: {courses_dir}")
    
    def stop_watching(self):
        """停止监控文件系统"""
        self.observer.stop()
        self.observer.join()
        print("文件监控服务已停止")
    
    def _watch_course_directory(self, course_dir: Path):
        """监控单个课程目录"""
        if str(course_dir) not in self.watched_paths:
            handler = FileWatcherHandler(self)
            self.observer.schedule(handler, str(course_dir), recursive=True)
            self.watched_paths.add(str(course_dir))
            print(f"开始监控课程目录: {course_dir}")
    
    def add_course_watch(self, course_id: str):
        """添加新课程的监控"""
        course_dir = self.data_dir / "courses" / course_id
        if course_dir.exists():
            self._watch_course_directory(course_dir)
    
    def _parse_file_path(self, file_path: str) -> Optional[Dict]:
        """解析文件路径，提取课程ID、展板ID等信息"""
        path = Path(file_path)
        
        # 检查是否在files目录中
        if 'files' not in path.parts:
            return None
        
        # 查找路径模式: .../courses/course-xxx/board-xxx/files/filename
        parts = path.parts
        try:
            courses_idx = parts.index('courses')
            course_id = parts[courses_idx + 1]
            board_id = parts[courses_idx + 2]
            
            # 验证ID格式
            if not (course_id.startswith('course-') and board_id.startswith('board-')):
                return None
            
            # 检查是否在files子目录中
            if parts[courses_idx + 3] != 'files':
                return None
            
            return {
                'course_id': course_id,
                'board_id': board_id,
                'filename': path.name,
                'file_path': path,
                'relative_path': f"files/{path.name}"
            }
        except (ValueError, IndexError):
            return None
    
    def _get_window_type_from_extension(self, filename: str) -> str:
        """根据文件扩展名确定窗口类型"""
        ext = Path(filename).suffix.lower()
        return self.file_type_mapping.get(ext, 'text')
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符，但保留扩展名"""
        # 保留完整文件名（包括扩展名）
        # 移除或替换非法字符，但保留点号（用于扩展名）
        illegal_chars = r'[<>:"/\\|?*]'
        safe_name = re.sub(illegal_chars, '_', filename)
        return safe_name.strip(' ') if safe_name.strip(' ') else "未命名"
    
    def _generate_window_id(self) -> str:
        """生成新的窗口ID"""
        return f"window_{int(datetime.now().timestamp() * 1000)}"
    
    async def handle_file_created(self, file_path: str):
        """处理文件创建事件"""
        path_info = self._parse_file_path(file_path)
        if not path_info:
            return
        
        print(f"检测到新文件: {path_info['filename']}")
        
        # 忽略临时文件（以_temp_开头的文件）
        if path_info['filename'].startswith('_temp_'):
            print(f"临时文件 {path_info['filename']}，跳过窗口创建")
            return
        
        # 如果是JSON配置文件，不需要创建窗口
        if path_info['filename'].endswith('.json'):
            print(f"JSON配置文件 {path_info['filename']}，跳过窗口创建")
            return
        
        # 检查是否已存在对应的窗口配置
        if self._window_exists_for_file(path_info['board_id'], path_info['filename']):
            print(f"文件 {path_info['filename']} 已有对应窗口，跳过创建")
            return
        
        # 只为真正的"孤立文件"创建窗口（用户直接拖拽到文件夹的文件）
        await self._create_window_for_file(path_info)
    
    async def handle_file_modified(self, file_path: str):
        """处理文件修改事件（带防抖机制）"""
        path_info = self._parse_file_path(file_path)
        if not path_info:
            return
        
        current_time = time.time()
        file_path_str = str(file_path)
        
        # 检查是否需要防抖
        if file_path_str in self.modified_files:
            last_modified = self.modified_files[file_path_str]
            if current_time - last_modified < self.debounce_delay:
                # 还在防抖期内，忽略此次修改
                return
        
        # 更新最后修改时间
        self.modified_files[file_path_str] = current_time
        
        print(f"检测到文件修改: {path_info['filename']}")
        
        # 通知前端刷新对应窗口内容
        await self._notify_file_content_changed(path_info)
    
    async def handle_file_deleted(self, file_path: str):
        """处理文件删除事件"""
        path_info = self._parse_file_path(file_path)
        if not path_info:
            return
        
        print(f"检测到文件删除: {path_info['filename']}")
        
        # 删除对应的窗口
        await self._delete_window_for_file(path_info)
    
    async def handle_file_moved(self, old_path: str, new_path: str):
        """处理文件移动/重命名事件"""
        old_path_info = self._parse_file_path(old_path)
        new_path_info = self._parse_file_path(new_path)
        
        if not (old_path_info and new_path_info):
            return
        
        print(f"检测到文件重命名: {old_path_info['filename']} -> {new_path_info['filename']}")
        
        # 更新对应窗口的标题
        await self._rename_window_for_file(old_path_info, new_path_info)
    
    def _window_exists_for_file(self, board_id: str, filename: str) -> bool:
        """检查是否已存在对应文件的窗口"""
        if not self.content_manager:
            return False
        
        try:
            # 检查是否已存在对应的JSON配置文件
            filename_without_ext = Path(filename).stem
            
            # 找到展板目录
            board_dir = None
            for course_dir in self.content_manager.file_manager.courses_dir.iterdir():
                if course_dir.is_dir():
                    potential_board_dir = course_dir / board_id
                    if potential_board_dir.exists():
                        board_dir = potential_board_dir
                        break
            
            if not board_dir:
                return False
            
            files_dir = board_dir / "files"
            if not files_dir.exists():
                return False
            
            # 检查是否已有对应的JSON配置文件（新命名规则：xxx.ext.json 或 xxx.md.json）
            # 方法1：检查 filename.json（旧格式）
            json_file_old = files_dir / f"{filename}.json"
            if json_file_old.exists():
                return True
            
            # 方法2：检查 filename.md.json（新格式，适用于文本文件）
            if filename.endswith('.md'):
                json_file_new = files_dir / f"{filename}.md.json"
                if json_file_new.exists():
                    return True
            
            # 方法3：扫描所有JSON文件，检查是否有匹配的file_path
            for json_file in files_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    file_path = data.get("file_path", "")
                    if file_path == f"files/{filename}":
                        print(f"找到匹配的窗口配置: {json_file.name} -> {filename}")
                        return True
                except Exception:
                    continue
            
            # 如果是JSON文件本身，检查是否有对应的实际文件
            if filename.endswith('.json'):
                return True  # JSON文件总是被认为有对应的窗口
            
            return False
        except Exception as e:
            print(f"检查窗口存在性失败: {e}")
            return False
    
    async def _create_window_for_file(self, path_info: Dict):
        """为新文件创建对应的窗口"""
        try:
            window_type = self._get_window_type_from_extension(path_info['filename'])
            window_title = self._sanitize_filename(path_info['filename'])
            window_id = self._generate_window_id()
            
            # 读取文件内容（如果是文本文件）
            content = ""
            if window_type == 'text':
                try:
                    with open(path_info['file_path'], 'r', encoding='utf-8') as f:
                        content = f.read()
                except Exception as e:
                    print(f"读取文件内容失败: {e}")
                    content = ""
            
            # 创建窗口数据
            window_data = {
                'id': window_id,
                'title': window_title,
                'type': window_type,
                'content': content,
                'x': 100,
                'y': 100,
                'width': 400,
                'height': 300,
                'hidden': True,  # 新创建的窗口默认隐藏
                'file_path': path_info['relative_path']
            }
            
            # 保存窗口数据
            if self.content_manager:
                success = self.content_manager.save_window_content(path_info['board_id'], window_data)
                if success:
                    print(f"成功为文件 {path_info['filename']} 创建窗口: {window_id}")
                    
                    # 通知前端有新窗口创建
                    await self._notify_window_created(path_info['board_id'], window_data)
                else:
                    print(f"为文件 {path_info['filename']} 创建窗口失败")
        
        except Exception as e:
            print(f"创建窗口失败: {e}")
    
    async def _notify_file_content_changed(self, path_info: Dict):
        """通知前端文件内容已变化"""
        message = {
            'type': 'file_content_changed',
            'board_id': path_info['board_id'],
            'filename': path_info['filename'],
            'timestamp': datetime.now().isoformat()
        }
        await self._broadcast_message(message)
    
    async def _notify_window_created(self, board_id: str, window_data: Dict):
        """通知前端有新窗口创建"""
        message = {
            'type': 'window_created',
            'board_id': board_id,
            'window_data': window_data,
            'timestamp': datetime.now().isoformat()
        }
        await self._broadcast_message(message)
    
    async def _delete_window_for_file(self, path_info: Dict):
        """删除对应文件的窗口"""
        try:
            if not self.content_manager:
                return
            
            # 特殊处理：如果删除的是JSON文件，检查是否存在转换后的文件
            if path_info['filename'].endswith('.json'):
                await self._handle_json_file_deletion(path_info)
                return
            
            # 查找对应的窗口
            windows = self.content_manager.get_board_windows(path_info['board_id'])
            filename_without_ext = Path(path_info['filename']).stem
            
            for window in windows:
                if window.get('title') == filename_without_ext:
                    window_id = window.get('id')
                    # 删除窗口
                    success = self.content_manager.delete_window_content(path_info['board_id'], window_id)
                    if success:
                        print(f"成功删除文件 {path_info['filename']} 对应的窗口: {window_id}")
                        
                        # 通知前端删除窗口
                        await self._notify_window_deleted(path_info['board_id'], window_id)
                    break
        
        except Exception as e:
            print(f"删除窗口失败: {e}")
    
    async def _handle_json_file_deletion(self, path_info: Dict):
        """处理JSON文件删除 - 检查是否是转换过程"""
        try:
            # 获取JSON文件对应的窗口标题
            json_filename = path_info['filename']
            if json_filename.endswith('.json'):
                # 移除.json后缀
                base_name = json_filename[:-5]
                
                # 找到展板目录
                board_dir = None
                for course_dir in self.content_manager.file_manager.courses_dir.iterdir():
                    if course_dir.is_dir():
                        potential_board_dir = course_dir / path_info['board_id']
                        if potential_board_dir.exists():
                            board_dir = potential_board_dir
                            break
                
                if not board_dir:
                    return
                
                files_dir = board_dir / "files"
                if not files_dir.exists():
                    return
                
                # 检查是否存在转换后的文件（如 新建项目.md.json）
                # 这表明这是一个转换过程，而不是真正的删除
                for possible_file in files_dir.iterdir():
                    if (possible_file.name.endswith('.json') and 
                        possible_file.name != json_filename and
                        possible_file.name.startswith(base_name)):
                        print(f"检测到转换过程，保留窗口: {json_filename} -> {possible_file.name}")
                        return
                
                # 没有找到转换后的文件，说明是真正的删除
                # 但是我们也需要检查对应的窗口ID是否仍然存在
                windows = self.content_manager.get_board_windows(path_info['board_id'])
                
                # 从JSON文件内容中获取窗口ID（如果可能的话）
                # 由于文件已经被删除，我们只能通过标题匹配
                for window in windows:
                    if window.get('title') == base_name:
                        window_id = window.get('id')
                        print(f"删除关联文件: {files_dir / base_name}")
                        
                        # 删除相关的内容文件
                        for content_file in files_dir.iterdir():
                            if (content_file.name.startswith(base_name) and 
                                not content_file.name.endswith('.json')):
                                try:
                                    content_file.unlink()
                                    print(f"删除内容文件: {content_file}")
                                except:
                                    pass
                        
                        # 删除窗口
                        success = self.content_manager.delete_window_content(path_info['board_id'], window_id)
                        if success:
                            print(f"成功删除文件 {json_filename} 对应的窗口: {window_id}")
                            await self._notify_window_deleted(path_info['board_id'], window_id)
                        break
                        
        except Exception as e:
            print(f"处理JSON文件删除失败: {e}")
    
    async def _notify_window_deleted(self, board_id: str, window_id: str):
        """通知前端窗口已删除"""
        message = {
            'type': 'window_deleted',
            'board_id': board_id,
            'window_id': window_id,
            'timestamp': datetime.now().isoformat()
        }
        await self._broadcast_message(message)
    
    async def _rename_window_for_file(self, old_path_info: Dict, new_path_info: Dict):
        """重命名文件对应的窗口"""
        try:
            if not self.content_manager:
                return
            
            # 查找对应的窗口
            windows = self.content_manager.get_board_windows(old_path_info['board_id'])
            old_filename_without_ext = Path(old_path_info['filename']).stem
            new_filename_without_ext = Path(new_path_info['filename']).stem
            
            for window in windows:
                if window.get('title') == old_filename_without_ext:
                    window_id = window.get('id')
                    
                    # 更新窗口标题和文件路径
                    window['title'] = new_filename_without_ext
                    window['file_path'] = new_path_info['relative_path']
                    
                    # 保存更新后的窗口数据
                    success = self.content_manager.save_window_content(new_path_info['board_id'], window)
                    if success:
                        print(f"成功重命名窗口: {old_filename_without_ext} -> {new_filename_without_ext}")
                        
                        # 通知前端窗口已重命名
                        await self._notify_window_renamed(new_path_info['board_id'], window_id, new_filename_without_ext)
                    break
        
        except Exception as e:
            print(f"重命名窗口失败: {e}")
    
    async def _notify_window_renamed(self, board_id: str, window_id: str, new_title: str):
        """通知前端窗口已重命名"""
        message = {
            'type': 'window_renamed',
            'board_id': board_id,
            'window_id': window_id,
            'new_title': new_title,
            'timestamp': datetime.now().isoformat()
        }
        await self._broadcast_message(message)
    
    async def _broadcast_message(self, message: Dict):
        """广播消息给所有WebSocket连接"""
        if self.websocket_manager:
            await self.websocket_manager.broadcast(json.dumps(message))
