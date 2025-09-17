import os
import json
import shutil
import time
from pathlib import Path
from config import DATA_DIR
from typing import Dict, List, Optional
from datetime import datetime
from .trash_manager import TrashManager
import pypdf

class ContentManager:
    def __init__(self, file_manager):
        self.file_manager = file_manager
        self.trash_manager = TrashManager()
    
    def save_window_content(self, board_id: str, window_data: Dict) -> bool:
        """保存窗口内容到展板文件夹（新存储结构：内容存储到.md文件，配置存储到.json文件）"""
        board_info = self.file_manager.get_board_info(board_id)
        if not board_info:
            return False
        
        # 找到展板目录
        board_dir = None
        for course_dir in self.file_manager.courses_dir.iterdir():
            if course_dir.is_dir():
                potential_board_dir = course_dir / board_id
                if potential_board_dir.exists():
                    board_dir = potential_board_dir
                    break
        
        if not board_dir:
            return False
        
        # 统一使用files目录存储所有文件（JSON和实际文件）
        files_dir = board_dir / "files"
        files_dir.mkdir(exist_ok=True)
        
        window_type = window_data.get("type", "text")
        window_title = window_data.get("title", "新建项目")
        safe_name = self._sanitize_filename(window_title)
        
        # 新存储逻辑：文本类型窗口
        if window_type == "text":
            # 1. 保存内容到.md文件
            md_file_name = f"{safe_name}.md"
            md_file_path = files_dir / md_file_name
            
            # 获取内容并保存到.md文件
            content = window_data.get("content", "")
            with open(md_file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            # 2. 保存配置到.json文件（不包含content）
            json_file_name = f"{safe_name}.md.json"
            json_file_path = files_dir / json_file_name
            
            # 准备存储的窗口数据（移除content，设置file_path指向.md文件）
            storage_data = {k: v for k, v in window_data.items() if k != 'content'}
            storage_data['file_path'] = f"files/{md_file_name}"
            
            with open(json_file_path, "w", encoding="utf-8") as f:
                json.dump(storage_data, f, ensure_ascii=False, indent=2)
            
            print(f"保存窗口内容: {window_title}")
            print(f"  内容文件: {md_file_name}")
            print(f"  配置文件: {json_file_name}")
            
            return True
        
        # 其他类型窗口的兼容处理
        else:
            return self._handle_legacy_window_storage(board_dir, window_data)
    
    def _handle_legacy_window_storage(self, board_dir: Path, window_data: Dict) -> bool:
        """处理非文本类型窗口的存储（兼容旧逻辑）"""
        files_dir = board_dir / "files"
        files_dir.mkdir(exist_ok=True)
        
        # 处理文件存储逻辑
        if self._handle_window_file_storage(board_dir, window_data):
            # JSON文件命名逻辑
            file_path = window_data.get("file_path")
            window_type = window_data.get("type", "text")
            
            if window_type == "generic":
                # 通用窗口：使用窗口标题命名JSON文件
                window_title = window_data.get("title", "新建项目")
                safe_name = self._sanitize_filename(window_title)
                json_file_name = f"{safe_name}.json"
            elif file_path and file_path.startswith("files/"):
                # 有具体文件路径的窗口
                actual_filename = file_path[6:]  # 移除 "files/" 前缀
                json_file_name = f"{actual_filename}.json"
            else:
                # 兜底方案
                window_title = window_data.get("title", "未命名")
                file_extension = self._get_file_extension(window_type)
                safe_name = self._sanitize_filename(window_title)
                json_file_name = f"{safe_name}{file_extension}.json"
            
            json_file_path = files_dir / json_file_name
            
            # 准备存储的窗口数据（移除content，添加file_path）
            storage_data = {k: v for k, v in window_data.items() if k != 'content'}
            if 'file_path' not in storage_data or storage_data['file_path'] is None:
                if window_type == "generic":
                    # 通用窗口不设置file_path
                    storage_data['file_path'] = None
                else:
                    storage_data['file_path'] = self._get_file_path_for_window(window_data)
            
            with open(json_file_path, "w", encoding="utf-8") as f:
                json.dump(storage_data, f, ensure_ascii=False, indent=2)
            
            return True
        
        return False

    def delete_window_content(self, board_id: str, window_id: str) -> bool:
        """删除窗口内容，包括关联的文件"""
        board_info = self.file_manager.get_board_info(board_id)
        if not board_info:
            return False

        # 找到展板目录
        board_dir = None
        for course_dir in self.file_manager.courses_dir.iterdir():
            if course_dir.is_dir():
                potential_board_dir = course_dir / board_id
                if potential_board_dir.exists():
                    board_dir = potential_board_dir
                    break

        if not board_dir:
            return False

        files_dir = board_dir / "files"
        
        # 查找包含指定window_id的JSON文件
        window_file = None
        window_data = None
        
        for json_file in files_dir.glob("*.json"):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("id") == window_id:
                    window_file = json_file
                    window_data = data
                    break
            except Exception as e:
                print(f"读取JSON文件失败: {json_file}, 错误: {e}")
                continue
        
        if window_file and window_data:
            try:
                # 删除关联的实际文件（基于新的命名规则：xxx.ext.json）
                self._delete_window_associated_files_new_naming(files_dir, window_file.name)
                
                # 删除窗口配置JSON文件
                window_file.unlink()
                
                # 清理图标位置信息
                self._cleanup_icon_position(board_dir, window_id)
                
                # 不再从 board_info.json 中移除窗口，只使用 files/ 目录管理
                return True
                
            except Exception as e:
                print(f"删除窗口文件失败: {e}")
        
        return False
    
    def _cleanup_icon_position(self, board_dir: Path, window_id: str):
        """清理删除窗口的图标位置信息"""
        try:
            icon_positions_file = board_dir / "icon_positions.json"
            if icon_positions_file.exists():
                with open(icon_positions_file, "r", encoding="utf-8") as f:
                    positions = json.load(f)
                
                # 移除对应窗口的位置信息
                if window_id in positions:
                    del positions[window_id]
                    print(f"从图标位置文件中移除: {window_id}")
                    
                    # 保存更新后的位置信息
                    with open(icon_positions_file, "w", encoding="utf-8") as f:
                        json.dump(positions, f, ensure_ascii=False, indent=2)
                    
                    print(f"图标位置清理完成")
        except Exception as e:
            print(f"清理图标位置失败: {e}")
    
    def move_window_to_trash(self, board_id: str, window_id: str) -> bool:
        """将窗口及其文件移动到回收站"""
        try:
            # 找到展板目录
            board_dir = None
            for course_dir in self.file_manager.courses_dir.iterdir():
                if course_dir.is_dir():
                    potential_board_dir = course_dir / board_id
                    if potential_board_dir.exists():
                        board_dir = potential_board_dir
                        break
            
            if not board_dir:
                print(f"展板目录不存在: {board_id}")
                return False
            
            files_dir = board_dir / "files"
            if not files_dir.exists():
                print(f"文件目录不存在: {files_dir}")
                return False
            
            # 查找窗口对应的JSON文件
            window_json_file = None
            window_data = None
            for json_file in files_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("id") == window_id:
                        window_json_file = json_file
                        window_data = data
                        break
                except Exception as e:
                    print(f"读取JSON文件失败: {json_file}, 错误: {e}")
                    continue
            
            if not window_json_file or not window_data:
                print(f"未找到窗口配置: {window_id}")
                return False
            
            # 获取实际文件路径
            actual_filename = window_json_file.name[:-5]  # 移除 .json 后缀
            actual_file_path = files_dir / actual_filename
            
            success = True
            
            # 移动实际文件到回收站（如果存在）
            if actual_file_path.exists():
                if not self.trash_manager.move_to_trash(actual_file_path, window_data, board_id):
                    print(f"移动文件到回收站失败: {actual_file_path}")
                    success = False
            
            # 移动JSON配置文件到回收站
            if window_json_file.exists():
                json_window_data = {**window_data, "is_json_config": True}
                if not self.trash_manager.move_to_trash(window_json_file, json_window_data, board_id):
                    print(f"移动JSON配置文件到回收站失败: {window_json_file}")
                    success = False
            
            # 如果是PDF窗口，同时移动对应的pages文件夹到回收站
            if window_data.get('type') == 'pdf':
                # 使用JSON文件名来推断PDF文件名
                pdf_filename = actual_filename  # actual_filename已经是去掉.json后缀的文件名
                pages_result = self.trash_manager.move_pdf_pages_to_trash(board_dir, pdf_filename)
                if pages_result:
                    print(f"PDF pages文件夹清理成功: {pdf_filename}")
                else:
                    print(f"移动PDF pages文件夹到回收站失败: {pdf_filename}")
            
            if success:
                print(f"窗口已移动到回收站: {window_id}")
            
            return success
            
        except Exception as e:
            print(f"移动窗口到回收站失败: {e}")
            return False

    def _delete_window_associated_files(self, board_dir: Path, window_data: Dict):
        """删除窗口关联的文件"""
        try:
            # 检查窗口是否有关联的文件
            content = window_data.get('content', '')
            if not content:
                return
            
            # 处理不同类型的文件路径
            file_to_delete = None
            
            if isinstance(content, str):
                if content.startswith('http://localhost:8081/api/boards/'):
                    # 从URL中提取文件路径
                    # 格式: http://localhost:8081/api/boards/{board_id}/files/serve?path={file_path}
                    if 'path=' in content:
                        file_path = content.split('path=')[-1]
                        # URL解码
                        import urllib.parse
                        file_path = urllib.parse.unquote(file_path)
                        file_to_delete = Path(file_path)
                elif content.startswith('/api/boards/'):
                    # 旧格式的相对路径
                    if 'path=' in content:
                        file_path = content.split('path=')[-1]
                        import urllib.parse
                        file_path = urllib.parse.unquote(file_path)
                        file_to_delete = Path(file_path)
                elif not content.startswith('http'):
                    # 直接的文件路径
                    file_to_delete = board_dir / "files" / content
            
            # 删除文件
            if file_to_delete and file_to_delete.exists():
                print(f"删除关联文件: {file_to_delete}")
                file_to_delete.unlink()
            elif file_to_delete:
                print(f"关联文件不存在，跳过删除: {file_to_delete}")
                
        except Exception as e:
            print(f"删除关联文件失败: {e}")

    def _delete_window_associated_files_new(self, board_dir: Path, window_id: str, window_data: Dict):
        """删除窗口关联的文件（新存储结构）"""
        try:
            files_dir = board_dir / "files"
            
            # 根据窗口类型删除对应的文件
            window_type = window_data.get('type', 'text')
            
            # 查找所有以window_id开头的文件（除了.json文件）
            for file_path in files_dir.iterdir():
                if file_path.is_file() and file_path.stem == window_id and file_path.suffix != '.json':
                    print(f"删除关联文件: {file_path}")
                    file_path.unlink()
                    
        except Exception as e:
            print(f"删除关联文件失败: {e}")

    def _delete_window_associated_files_by_basename(self, files_dir: Path, base_name: str):
        """根据基础文件名删除关联文件"""
        try:
            # 查找所有具有相同基础名称但不同扩展名的文件
            for file_path in files_dir.iterdir():
                if file_path.is_file() and file_path.stem == base_name and file_path.suffix != '.json':
                    print(f"删除关联文件: {file_path}")
                    file_path.unlink()
                    
        except Exception as e:
            print(f"删除关联文件失败: {e}")

    def _delete_window_associated_files_new_naming(self, files_dir: Path, json_filename: str):
        """根据新的命名规则删除关联文件 (xxx.ext.json -> xxx.ext)"""
        try:
            # 从JSON文件名推导出实际文件名
            # 例如：新建文本.txt.json -> 新建文本.txt
            if json_filename.endswith('.json'):
                actual_filename = json_filename[:-5]  # 移除 .json 后缀
                actual_file_path = files_dir / actual_filename
                
                if actual_file_path.exists():
                    print(f"删除关联文件: {actual_file_path}")
                    actual_file_path.unlink()
                else:
                    print(f"关联文件不存在: {actual_file_path}")
                    
        except Exception as e:
            print(f"删除关联文件失败: {e}")

    def _remove_window_from_board(self, board_dir: Path, window_id: str):
        """从展板信息中移除窗口"""
        board_info_path = board_dir / "board_info.json"
        if board_info_path.exists():
            with open(board_info_path, "r", encoding="utf-8") as f:
                board_info = json.load(f)
            
            # 移除窗口
            board_info["windows"] = [w for w in board_info["windows"] if w.get("id") != window_id]
            board_info["updated_at"] = datetime.now().isoformat()
            
            with open(board_info_path, "w", encoding="utf-8") as f:
                json.dump(board_info, f, ensure_ascii=False, indent=2)

    def _update_board_windows(self, board_dir: Path, window_data: Dict):
        """更新展板信息中的窗口列表"""
        board_info_path = board_dir / "board_info.json"
        if board_info_path.exists():
            with open(board_info_path, "r", encoding="utf-8") as f:
                board_info = json.load(f)
            
            # 检查窗口是否已存在
            window_exists = False
            for i, window in enumerate(board_info["windows"]):
                if window["id"] == window_data["id"]:
                    board_info["windows"][i] = window_data
                    window_exists = True
                    break
            
            if not window_exists:
                board_info["windows"].append(window_data)
            
            board_info["updated_at"] = datetime.now().isoformat()
            
            with open(board_info_path, "w", encoding="utf-8") as f:
                json.dump(board_info, f, ensure_ascii=False, indent=2)
    
    def save_file_to_board(self, board_id: str, file_type: str, file_path: str, filename: str, window_id: str = None) -> str:
        """保存文件到展板文件夹，并重命名JSON配置文件以保持一致"""
        print("\n" + "="*80)
        print("UPLOAD_DEBUG: 开始文件上传流程")
        print(f"输入参数: board_id={board_id}")
        print(f"输入参数: filename={filename}")  
        print(f"输入参数: window_id={window_id}")
        print(f"输入参数: file_type={file_type}")
        print(f"源文件: {file_path}")
        print("="*80)
        board_info = self.file_manager.get_board_info(board_id)
        if not board_info:
            raise ValueError(f"展板不存在: {board_id}")
        
        # 找到展板目录
        board_dir = None
        for course_dir in self.file_manager.courses_dir.iterdir():
            if course_dir.is_dir():
                potential_board_dir = course_dir / board_id
                if potential_board_dir.exists():
                    board_dir = potential_board_dir
                    break
        
        if not board_dir:
            raise ValueError(f"展板目录不存在: {board_id}")
        
        # 统一使用files目录
        target_dir = board_dir / "files"
        target_dir.mkdir(exist_ok=True)
        print(f"STEP1: 目标目录 = {target_dir}")
        
        # 获取原文件名（不含扩展名）作为新的基础名称
        original_basename = Path(filename).stem
        file_extension = Path(filename).suffix
        safe_basename = self._sanitize_filename(original_basename)
        print(f"STEP2: 文件名解析")
        print(f"  - 原始文件名: {filename}")
        print(f"  - basename: '{original_basename}'")
        print(f"  - extension: '{file_extension}'")
        print(f"  - safe_basename: '{safe_basename}'")
        
        print(f"STEP3: 处理窗口逻辑")
        existing_filename = None
        if window_id:
            print(f"  - 有window_id，处理现有窗口: {window_id}")
            # 如果有window_id，说明是上传到现有窗口，需要替换占位文件
            existing_filename = self._get_existing_filename_for_window(target_dir, window_id)
            print(f"  - 查找现有文件: '{existing_filename}'")
            if existing_filename:
                # 使用上传文件的原始名称，但检查冲突
                new_filename = self._generate_unique_filename(target_dir, safe_basename, file_extension)
                new_basename = Path(new_filename).stem
                print(f"生成新文件名: '{new_filename}' (basename: '{new_basename}')")
                
                # 先更新JSON文件（在删除旧文件之前）
                print(f"更新JSON文件: window_id={window_id}, new_filename='{new_filename}'")
                self._update_window_json_file(target_dir, window_id, new_filename)
                print(f"JSON文件更新完成")
                
                # 然后删除现有的占位文件（如果存在）
                existing_file_path = target_dir / existing_filename
                if existing_file_path.exists():
                    existing_file_path.unlink()
                    print(f"删除占位文件: {existing_filename}")
                else:
                    print(f"占位文件不存在: {existing_filename}")
            else:
                # 如果找不到现有文件，使用上传文件的名称
                new_filename = self._generate_unique_filename(target_dir, safe_basename, file_extension)
                new_basename = Path(new_filename).stem
                print(f"没有现有文件，生成新文件名: '{new_filename}'")
        else:
            print(f"没有window_id，创建新文件")
            # 如果没有window_id，说明是新文件，生成唯一的文件名
            new_filename = self._generate_unique_filename(target_dir, safe_basename, file_extension)
            new_basename = Path(new_filename).stem
            print(f"生成新文件名: '{new_filename}'")
        
        # 如果提供了window_id但没有现有文件，需要更新JSON配置文件
        if window_id and not existing_filename:
            print(f"更新JSON文件（没有现有文件的情况）: window_id={window_id}, new_filename='{new_filename}'")
            self._update_window_json_file(target_dir, window_id, new_filename)
        
        # 如果有window_id，使用两步法避免文件监控器干扰
        print("开始两步法上传")
        if window_id:
            # 步骤1：先创建临时文件
            temp_filename = f"_temp_{int(time.time() * 1000)}_{new_filename}"
            temp_path = target_dir / temp_filename
            print(f"步骤1: 创建临时文件 '{temp_filename}'")
            shutil.copy2(file_path, temp_path)
            print(f"临时文件创建成功: {temp_path}")
            
            # 步骤2：更新JSON文件
            print(f"步骤2: 确保JSON文件存在")
            self._ensure_json_file_exists(target_dir, window_id, new_filename)
            
            # 步骤3：重命名为最终文件名
            target_path = target_dir / new_filename
            print(f"步骤3: 重命名 '{temp_filename}' -> '{new_filename}'")
            temp_path.rename(target_path)
            print(f"文件重命名完成: {new_filename}")
        else:
            # 没有window_id的情况，直接复制
            target_path = target_dir / new_filename
            shutil.copy2(file_path, target_path)
        
        return str(target_path)
    
    def get_board_files(self, board_id: str, file_type: str) -> List[str]:
        """获取展板中的文件列表"""
        board_info = self.file_manager.get_board_info(board_id)
        if not board_info:
            return []
        
        # 找到展板目录
        board_dir = None
        for course_dir in self.file_manager.courses_dir.iterdir():
            if course_dir.is_dir():
                potential_board_dir = course_dir / board_id
                if potential_board_dir.exists():
                    board_dir = potential_board_dir
                    break
        
        if not board_dir:
            return []
        
        target_dir = board_dir / "files"
        if not target_dir.exists():
            return []
        
        return [f.name for f in target_dir.iterdir() if f.is_file()]
    
    def get_board_windows(self, board_id: str) -> List[Dict]:
        """获取展板的所有窗口"""
        board_info = self.file_manager.get_board_info(board_id)
        if not board_info:
            return []
        
        # 找到展板目录
        board_dir = None
        for course_dir in self.file_manager.courses_dir.iterdir():
            if course_dir.is_dir():
                potential_board_dir = course_dir / board_id
                if potential_board_dir.exists():
                    board_dir = potential_board_dir
                    break
        
        if not board_dir:
            return []
        
        files_dir = board_dir / "files"
        if not files_dir.exists():
            return []
        
        windows = []
        seen_window_ids = set()  # 用于去重
        
        # 扫描files目录，查找所有JSON配置文件（新命名规则：xxx.ext.json）
        for file_path in files_dir.iterdir():
            if file_path.is_file() and file_path.suffix == ".json":
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        window_data = json.load(f)
                    
                    # 检查窗口ID是否重复
                    window_id = window_data.get('id')
                    if window_id in seen_window_ids:
                        print(f"警告: 发现重复的窗口ID，跳过文件: {file_path.name} (ID: {window_id})")
                        continue
                    
                    seen_window_ids.add(window_id)
                    
                    # 从对应的文件中加载内容
                    window_type = window_data.get('type', 'text')
                    
                    if window_type == 'generic':
                        # 通用窗口没有内容文件，content为空
                        window_data['content'] = ''
                    elif 'file_path' in window_data and window_data['file_path'] is not None:
                        content_file_path = board_dir / window_data['file_path']
                        if content_file_path.exists():
                            try:
                                # 根据文件类型决定如何加载内容
                                if window_type == 'text':
                                    # 文本类型：从文件读取内容，尝试多种编码
                                    try:
                                        with open(content_file_path, "r", encoding="utf-8") as f:
                                            window_data['content'] = f.read()
                                    except UnicodeDecodeError:
                                        try:
                                            with open(content_file_path, "r", encoding="gbk") as f:
                                                window_data['content'] = f.read()
                                        except UnicodeDecodeError:
                                            try:
                                                with open(content_file_path, "r", encoding="gb2312") as f:
                                                    window_data['content'] = f.read()
                                            except UnicodeDecodeError:
                                                # 如果所有编码都失败，使用二进制模式读取并忽略错误
                                                with open(content_file_path, "r", encoding="utf-8", errors="ignore") as f:
                                                    window_data['content'] = f.read()
                                else:
                                    # 对于媒体文件，content存储文件路径或URL
                                    window_data['content'] = str(content_file_path)
                            except Exception as e:
                                print(f"读取内容文件失败: {content_file_path}, 错误: {e}")
                                window_data['content'] = ""
                        else:
                            window_data['content'] = ""
                    else:
                        # 兼容旧数据或没有file_path的情况
                        window_data['content'] = window_data.get('content', '')
                    
                    windows.append(window_data)
                except Exception as e:
                    print(f"读取窗口配置文件失败: {file_path}, 错误: {e}")
                    continue
        
        # 扫描files目录，为没有JSON配置的文件创建窗口配置
        self._auto_create_windows_for_orphaned_files(board_id, files_dir, windows)
        
        return windows
    
    def _auto_create_windows_for_orphaned_files(self, board_id: str, files_dir: Path, existing_windows: List[Dict]):
        """为没有JSON配置的文件自动创建窗口配置"""
        try:
            if not files_dir.exists():
                return
            
            # 获取所有现有JSON文件对应的实际文件名（新命名规则：xxx.ext.json）
            existing_json_files = set()
            for json_file in files_dir.glob("*.json"):
                # 从 xxx.ext.json 推导出 xxx.ext
                if json_file.name.endswith('.json'):
                    actual_filename = json_file.name[:-5]  # 移除 .json 后缀
                    existing_json_files.add(actual_filename)
            
            # 扫描所有非JSON文件
            for file_path in files_dir.iterdir():
                if file_path.is_file() and file_path.suffix != '.json':
                    # 检查是否已有对应的JSON配置文件
                    if file_path.name not in existing_json_files:
                        print(f"发现孤立文件，自动创建窗口配置: {file_path}")
                        
                        # 根据文件扩展名确定窗口类型
                        window_type = self._get_window_type_from_extension(file_path.suffix)
                        
                        # 生成唯一的window_id
                        window_id = f"window_{int(time.time() * 1000)}"
                        
                        # 创建窗口配置
                        window_data = {
                            "id": window_id,
                            "type": window_type,
                            "title": file_path.name,  # 使用完整的文件名（包含扩展名）作为标题
                            "position": {"x": 100, "y": 100},
                            "size": {"width": 400, "height": 300},
                            "file_path": f"files/{file_path.name}",
                            "created_at": datetime.now().isoformat(),
                            "updated_at": datetime.now().isoformat(),
                            "hidden": False
                        }
                        
                        # 保存JSON配置文件（新命名规则：xxx.ext.json）
                        json_path = files_dir / f"{file_path.name}.json"
                        with open(json_path, "w", encoding="utf-8") as f:
                            json.dump(window_data, f, ensure_ascii=False, indent=2)
                        
                        # 添加到现有窗口列表中
                        existing_windows.append(window_data)
                        
        except Exception as e:
            print(f"自动创建窗口配置失败: {e}")
    
    def _get_window_type_from_extension(self, extension: str) -> str:
        """根据文件扩展名确定窗口类型"""
        ext = extension.lower()
        
        # 图片类型
        if ext in ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg']:
            return 'image'
        
        # 视频类型
        if ext in ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv', '.m4v']:
            return 'video'
        
        # 音频类型
        if ext in ['.mp3', '.wav', '.flac', '.aac', '.ogg', '.wma', '.m4a']:
            return 'audio'
        
        # PDF类型
        if ext == '.pdf':
            return 'pdf'
        
        # 文本类型
        if ext in ['.txt', '.md', '.json', '.xml', '.csv', '.log']:
            return 'text'
        
        # 默认为文本类型
        return 'text'
    
    def _rename_window_json_file(self, files_dir: Path, window_id: str, new_basename: str):
        """重命名窗口的JSON配置文件以匹配上传的文件名（新命名规则）"""
        try:
            # 查找包含指定window_id的JSON文件
            for json_file in files_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("id") == window_id:
                        # 获取文件路径以确定新的JSON文件名
                        file_path = data.get("file_path", "")
                        if file_path.startswith("files/"):
                            actual_filename = file_path[6:]  # 移除 "files/" 前缀
                            # 使用新命名规则：xxx.ext.json
                            new_json_filename = f"{actual_filename}.json"
                        else:
                            # 兜底方案
                            window_type = data.get("type", "text")
                            file_extension = self._get_file_extension(window_type)
                            new_json_filename = f"{new_basename}{file_extension}.json"
                        
                        new_json_path = files_dir / new_json_filename
                        
                        # 更新JSON数据中的标题 - 使用完整的文件名（包含扩展名）
                        if file_path.startswith("files/"):
                            actual_filename = file_path[6:]  # 移除 "files/" 前缀
                            data["title"] = actual_filename  # 使用完整的文件名
                        else:
                            # 兜底方案：使用basename + extension
                            window_type = data.get("type", "text")
                            file_extension = self._get_file_extension(window_type)
                            data["title"] = f"{new_basename}{file_extension}"
                        data["updated_at"] = datetime.now().isoformat()
                        
                        # 保存到新位置
                        with open(new_json_path, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        
                        # 删除旧文件（如果不是同一个文件）
                        if new_json_path != json_file:
                            json_file.unlink()
                        
                        print(f"重命名JSON配置文件: {json_file.name} -> {new_json_path.name}")
                        break
                        
                except Exception as e:
                    print(f"读取JSON文件失败: {json_file}, 错误: {e}")
                    continue
                    
        except Exception as e:
            print(f"重命名JSON文件失败: {e}")
    
    def _update_window_json_file(self, files_dir: Path, window_id: str, new_filename: str):
        """更新窗口的JSON配置文件，用于文件上传后的更新"""
        try:
            # 查找包含指定window_id的JSON文件
            old_json_file = None
            window_data = None
            
            for json_file in files_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("id") == window_id:
                        old_json_file = json_file
                        window_data = data
                        break
                except Exception as e:
                    print(f"读取JSON文件失败: {json_file}, 错误: {e}")
                    continue
            
            if not old_json_file or not window_data:
                print(f"未找到窗口 {window_id} 对应的JSON文件")
                return
            
            # 更新窗口数据
            window_data["title"] = new_filename  # 使用完整的新文件名
            window_data["file_path"] = f"files/{new_filename}"
            window_data["updated_at"] = datetime.now().isoformat()
            
            # 确定新的JSON文件名：新文件名.json
            new_json_filename = f"{new_filename}.json"
            new_json_path = files_dir / new_json_filename
            
            # 保存更新的JSON文件
            with open(new_json_path, "w", encoding="utf-8") as f:
                json.dump(window_data, f, ensure_ascii=False, indent=2)
            
            # 删除旧的JSON文件（如果不是同一个文件）
            if new_json_path != old_json_file:
                old_json_file.unlink()
                print(f"更新JSON文件: {old_json_file.name} -> {new_json_filename}")
            else:
                print(f"更新JSON文件: {new_json_filename}")
                
        except Exception as e:
            print(f"更新JSON配置文件失败: {e}")
    
    def update_window_content_only(self, board_id: str, window_id: str, content: str):
        """更新窗口的文字内容（新存储结构：更新.md文件）"""
        try:
            # 找到展板目录
            board_dir = None
            for course_dir in self.file_manager.courses_dir.iterdir():
                if course_dir.is_dir():
                    potential_board_dir = course_dir / board_id
                    if potential_board_dir.exists():
                        board_dir = potential_board_dir
                        break
            
            if not board_dir:
                print(f"展板目录不存在: {board_id}")
                return
            
            files_dir = board_dir / "files"
            if not files_dir.exists():
                print(f"文件目录不存在: {files_dir}")
                return
            
            # 查找窗口对应的JSON文件
            for json_file in files_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    if data.get("id") == window_id:
                        window_type = data.get("type", "text")
                        
                        if window_type == "text":
                            # 文本类型：更新对应的.md文件
                            if 'file_path' in data and data['file_path']:
                                content_file_path = board_dir / data['file_path']
                                if content_file_path.exists():
                                    # 更新文件内容，尝试检测编码
                                    try:
                                        with open(content_file_path, "w", encoding="utf-8") as f:
                                            f.write(content)
                                    except UnicodeEncodeError:
                                        # 如果UTF-8编码失败，尝试GBK编码
                                        try:
                                            with open(content_file_path, "w", encoding="gbk") as f:
                                                f.write(content)
                                        except UnicodeEncodeError:
                                            # 最后使用UTF-8并忽略错误
                                            with open(content_file_path, "w", encoding="utf-8", errors="ignore") as f:
                                                f.write(content)
                                    
                                    # 更新JSON文件的时间戳
                                    data["updated_at"] = datetime.now().isoformat()
                                    with open(json_file, "w", encoding="utf-8") as f:
                                        json.dump(data, f, ensure_ascii=False, indent=2)
                                    
                                    print(f"更新窗口内容: {window_id} -> {content_file_path.name}")
                                    return
                                else:
                                    print(f"内容文件不存在: {content_file_path}")
                            else:
                                print(f"窗口 {window_id} 没有关联的内容文件")
                        else:
                            # 非文本类型：保持原有逻辑
                            data["content"] = content
                            data["updated_at"] = datetime.now().isoformat()
                            
                        with open(json_file, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        
                            print(f"更新窗口内容: {window_id} -> {content}")
                        return
                        
                except Exception as e:
                    print(f"读取JSON文件失败: {json_file}, 错误: {e}")
                    continue
            
            print(f"未找到窗口 {window_id} 对应的JSON文件")
            
        except Exception as e:
            print(f"更新窗口内容失败: {e}")
    
    def _ensure_json_file_exists(self, files_dir: Path, window_id: str, new_filename: str):
        """确保JSON文件存在并正确指向新文件"""
        print(f"_ensure_json_file_exists called:")
        print(f"   files_dir: {files_dir}")
        print(f"   window_id: {window_id}")
        print(f"   new_filename: {new_filename}")
        try:
            # 检查是否已经存在正确的JSON文件
            expected_json_path = files_dir / f"{new_filename}.json"
            print(f"期望的JSON文件路径: {expected_json_path}")
            
            if expected_json_path.exists():
                print(f"JSON文件已存在，验证内容...")
                # JSON文件已存在，验证内容是否正确
                with open(expected_json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if data.get("id") == window_id and data.get("title") == new_filename:
                    print(f"JSON文件已正确存在: {expected_json_path.name}")
                    return
                else:
                    print(f"JSON文件内容不正确: id={data.get('id')}, title={data.get('title')}")
            else:
                print(f"JSON文件不存在: {expected_json_path}")
            
            # JSON文件不存在或不正确，需要创建/更新
            print(f"创建/更新JSON文件: {expected_json_path.name}")
            
            # 查找现有的窗口数据
            existing_data = None
            print(f"搜索现有窗口数据...")
            for json_file in files_dir.glob("*.json"):
                print(f"   检查文件: {json_file.name}")
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("id") == window_id:
                        existing_data = data
                        # 删除旧的JSON文件（如果不是目标文件）
                        if json_file != expected_json_path:
                            json_file.unlink()
                            print(f"删除旧JSON文件: {json_file.name}")
                        break
                except Exception as e:
                    print(f"读取JSON文件失败: {json_file}, 错误: {e}")
                    continue
            
            if existing_data:
                # 更新现有数据
                existing_data["title"] = new_filename
                existing_data["file_path"] = f"files/{new_filename}"
                existing_data["updated_at"] = datetime.now().isoformat()
            else:
                # 创建新的窗口数据（这种情况不应该发生，但作为兜底）
                existing_data = {
                    "id": window_id,
                    "title": new_filename,
                    "type": "image",  # 默认类型，应该从上下文获取
                    "x": 100,
                    "y": 100,
                    "width": 400,
                    "height": 300,
                    "file_path": f"files/{new_filename}",
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }
            
            # 保存JSON文件
            with open(expected_json_path, "w", encoding="utf-8") as f:
                json.dump(existing_data, f, ensure_ascii=False, indent=2)
            
            print(f"JSON文件已更新: {expected_json_path.name}")
            
        except Exception as e:
            print(f"确保JSON文件存在失败: {e}")
    
    def _get_existing_filename_for_window(self, files_dir: Path, window_id: str) -> str:
        """获取窗口对应的现有文件名"""
        print(f"    _get_existing_filename_for_window: 查找窗口 {window_id} 的现有文件")
        try:
            # 查找包含指定window_id的JSON文件
            json_files = list(files_dir.glob("*.json"))
            print(f"    找到 {len(json_files)} 个JSON文件: {[f.name for f in json_files]}")
            
            for json_file in json_files:
                print(f"    检查JSON文件: {json_file.name}")
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    file_window_id = data.get("id")
                    print(f"      文件中的window_id: {file_window_id}")
                    if file_window_id == window_id:
                        # 从窗口数据中的file_path获取实际文件名
                        file_path = data.get("file_path", "")
                        print(f"      JSON中的file_path: '{file_path}'")
                        if file_path.startswith("files/"):
                            actual_filename = file_path[6:]  # 移除 "files/" 前缀
                            print(f"      返回文件名(从file_path): '{actual_filename}'")
                            return actual_filename
                        # 兜底：从JSON文件名推导（xxx.ext.json -> xxx.ext）
                        elif json_file.name.endswith('.json'):
                            actual_filename = json_file.name[:-5]  # 移除 .json 后缀
                            print(f"      返回文件名(从JSON文件名): '{actual_filename}'")
                            return actual_filename
                        break
                except Exception as e:
                    print(f"读取JSON文件失败: {json_file}, 错误: {e}")
                    continue
            return None
        except Exception as e:
            print(f"获取现有文件名失败: {e}")
            return None
    
    def clean_board_info_redundancy(self, board_id: str = None):
        """清理board_info.json中的冗余windows数据"""
        try:
            if board_id:
                # 清理指定展板
                self._clean_single_board_info(board_id)
            else:
                # 清理所有展板
                for course_dir in self.file_manager.courses_dir.iterdir():
                    if course_dir.is_dir():
                        for board_dir in course_dir.iterdir():
                            if board_dir.is_dir() and board_dir.name.startswith("board-"):
                                board_id = board_dir.name
                                self._clean_single_board_info(board_id)
        except Exception as e:
            print(f"清理board_info冗余数据失败: {e}")
    
    def _clean_single_board_info(self, board_id: str):
        """清理单个展板的board_info.json"""
        try:
            # 找到展板目录
            board_dir = None
            for course_dir in self.file_manager.courses_dir.iterdir():
                if course_dir.is_dir():
                    potential_board_dir = course_dir / board_id
                    if potential_board_dir.exists():
                        board_dir = potential_board_dir
                        break
            
            if not board_dir:
                return
            
            board_info_path = board_dir / "board_info.json"
            if board_info_path.exists():
                with open(board_info_path, "r", encoding="utf-8") as f:
                    board_info = json.load(f)
                
                # 移除windows字段，只保留基本信息
                if "windows" in board_info:
                    del board_info["windows"]
                    print(f"从 {board_id} 的 board_info.json 中移除了 windows 字段")
                
                # 更新时间戳
                board_info["updated_at"] = datetime.now().isoformat()
                
                # 保存清理后的数据
                with open(board_info_path, "w", encoding="utf-8") as f:
                    json.dump(board_info, f, ensure_ascii=False, indent=2)
                    
        except Exception as e:
            print(f"清理单个board_info失败: {board_id}, 错误: {e}")
    
    def migrate_to_new_json_naming(self, board_id: str = None):
        """迁移到新的JSON命名规则（xxx.ext.json）"""
        try:
            if board_id:
                # 迁移指定展板
                self._migrate_single_board_json_naming(board_id)
            else:
                # 迁移所有展板
                for course_dir in self.file_manager.courses_dir.iterdir():
                    if course_dir.is_dir():
                        for board_dir in course_dir.iterdir():
                            if board_dir.is_dir() and board_dir.name.startswith("board-"):
                                board_id = board_dir.name
                                self._migrate_single_board_json_naming(board_id)
        except Exception as e:
            print(f"迁移JSON命名规则失败: {e}")
    
    def _migrate_single_board_json_naming(self, board_id: str):
        """迁移单个展板的JSON命名规则"""
        try:
            # 找到展板目录
            board_dir = None
            for course_dir in self.file_manager.courses_dir.iterdir():
                if course_dir.is_dir():
                    potential_board_dir = course_dir / board_id
                    if potential_board_dir.exists():
                        board_dir = potential_board_dir
                        break
            
            if not board_dir:
                return
            
            files_dir = board_dir / "files"
            if not files_dir.exists():
                return
            
            # 查找所有旧格式的JSON文件（xxx.json）
            for json_file in files_dir.glob("*.json"):
                try:
                    # 检查是否是旧格式（不包含扩展名的JSON文件）
                    json_basename = json_file.stem
                    
                    # 查找对应的实际文件
                    actual_file = None
                    for file_path in files_dir.iterdir():
                        if file_path.is_file() and file_path.suffix != '.json' and file_path.stem == json_basename:
                            actual_file = file_path
                            break
                    
                    if actual_file:
                        # 读取JSON数据
                        with open(json_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        
                        # 创建新的JSON文件名（xxx.ext.json）
                        new_json_filename = f"{actual_file.name}.json"
                        new_json_path = files_dir / new_json_filename
                        
                        # 如果新文件名不同，执行迁移
                        if new_json_path != json_file:
                            # 更新file_path字段
                            data["file_path"] = f"files/{actual_file.name}"
                            data["updated_at"] = datetime.now().isoformat()
                            
                            # 保存到新位置
                            with open(new_json_path, "w", encoding="utf-8") as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                            
                            # 删除旧文件
                            json_file.unlink()
                            
                            print(f"迁移JSON文件: {json_file.name} -> {new_json_filename}")
                        
                except Exception as e:
                    print(f"迁移JSON文件失败: {json_file}, 错误: {e}")
                    continue
                    
        except Exception as e:
            print(f"迁移单个展板JSON命名规则失败: {board_id}, 错误: {e}")
    
    def fix_duplicate_windows(self, board_id: str) -> Dict:
        """修复重复的窗口ID问题"""
        try:
            # 找到展板目录
            board_dir = None
            for course_dir in self.file_manager.courses_dir.iterdir():
                if course_dir.is_dir():
                    potential_board_dir = course_dir / board_id
                    if potential_board_dir.exists():
                        board_dir = potential_board_dir
                        break
            
            if not board_dir:
                return {"error": "展板目录不存在"}
            
            files_dir = board_dir / "files"
            if not files_dir.exists():
                return {"error": "文件目录不存在"}
            
            # 收集所有窗口数据
            windows_by_id = {}
            
            for json_file in files_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        window_data = json.load(f)
                    
                    window_id = window_data.get("id")
                    if window_id:
                        if window_id not in windows_by_id:
                            windows_by_id[window_id] = []
                        windows_by_id[window_id].append({
                            "data": window_data,
                            "file": json_file
                        })
                except Exception as e:
                    print(f"读取JSON文件失败: {json_file}, 错误: {e}")
                    continue
            
            # 找到重复的窗口ID
            duplicates = {k: v for k, v in windows_by_id.items() if len(v) > 1}
            
            if not duplicates:
                return {"message": "没有发现重复的窗口ID", "duplicates_count": 0}
            
            # 处理重复窗口
            fixed_count = 0
            for window_id, windows in duplicates.items():
                print(f"处理重复窗口ID: {window_id}, 共 {len(windows)} 个")
                
                # 按优先级排序：有content的优先，更新时间晚的优先
                def priority_score(w):
                    data = w["data"]
                    score = 0
                    # 有content加分
                    if data.get("content") and data["content"].strip():
                        score += 100
                    # 文件名不是"新建"的加分
                    title = data.get("title", "")
                    if not title.startswith("新建"):
                        score += 50
                    return score
                
                windows.sort(key=priority_score, reverse=True)
                
                # 保留第一个（优先级最高的），删除其他的
                for i, window in enumerate(windows[1:], 1):
                    try:
                        window["file"].unlink()  # 删除JSON文件
                        print(f"删除重复窗口文件: {window['file'].name}")
                        fixed_count += 1
                    except Exception as e:
                        print(f"删除文件失败: {window['file']}, 错误: {e}")
            
            return {
                "message": f"成功修复 {len(duplicates)} 组重复窗口",
                "duplicates_count": len(duplicates),
                "fixed_count": fixed_count
            }
            
        except Exception as e:
            print(f"修复重复窗口失败: {e}")
            return {"error": str(e)}

    def rename_window_and_file(self, board_id: str, window_id: str, new_name: str) -> Dict:
        """重命名窗口及其关联的文件"""
        try:
            # 找到展板目录
            board_dir = None
            for course_dir in self.file_manager.courses_dir.iterdir():
                if course_dir.is_dir():
                    potential_board_dir = course_dir / board_id
                    if potential_board_dir.exists():
                        board_dir = potential_board_dir
                        break
            
            if not board_dir:
                return {"success": False, "error": "展板目录不存在"}
            
            files_dir = board_dir / "files"
            if not files_dir.exists():
                return {"success": False, "error": "文件目录不存在"}
            
            # 查找窗口对应的JSON文件
            window_json_file = None
            window_data = None
            for json_file in files_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("id") == window_id:
                        window_json_file = json_file
                        window_data = data
                        break
                except Exception as e:
                    print(f"读取JSON文件失败: {json_file}, 错误: {e}")
                    continue
            
            if not window_json_file or not window_data:
                return {"success": False, "error": "未找到窗口配置"}
            
            # 获取当前文件信息
            current_filename = window_json_file.name[:-5]  # 移除 .json 后缀
            current_file_path = files_dir / current_filename
            
            # 获取文件扩展名
            file_extension = Path(current_filename).suffix
            window_type = window_data.get("type", "text")
            
            # 如果没有扩展名，根据窗口类型添加默认扩展名
            if not file_extension:
                extension_map = {
                    "image": ".jpg",
                    "video": ".mp4", 
                    "audio": ".mp3",
                    "pdf": ".pdf",
                    "text": ".txt"
                }
                file_extension = extension_map.get(window_type, ".txt")
            
            # 清理新名称
            safe_new_name = self._sanitize_filename(new_name)
            new_filename = f"{safe_new_name}{file_extension}"
            
            # 检查名称冲突并生成唯一名称
            final_filename = self._generate_unique_filename(files_dir, safe_new_name, file_extension)
            final_file_path = files_dir / final_filename
            final_json_filename = f"{final_filename}.json"
            final_json_path = files_dir / final_json_filename
            
            # 重命名实际文件（如果存在）
            if current_file_path.exists():
                current_file_path.rename(final_file_path)
                print(f"重命名文件: {current_filename} -> {final_filename}")
            
            # 更新窗口数据 - title使用完整的最终文件名（包含扩展名和冲突后缀）
            window_data["title"] = final_filename  # 使用实际存储的文件名
            window_data["file_path"] = f"files/{final_filename}"
            window_data["updated_at"] = datetime.now().isoformat()
            
            # 保存更新的JSON文件
            with open(final_json_path, "w", encoding="utf-8") as f:
                json.dump(window_data, f, ensure_ascii=False, indent=2)
            
            # 删除旧的JSON文件
            if final_json_path != window_json_file:
                window_json_file.unlink()
                print(f"删除旧JSON文件: {window_json_file.name}")
            
            return {
                "success": True,
                "new_filename": final_filename,
                "old_filename": current_filename
            }
            
        except Exception as e:
            print(f"重命名窗口和文件失败: {e}")
            return {"success": False, "error": str(e)}

    def get_icon_positions(self, board_id: str) -> Dict:
        """获取展板的图标位置数据"""
        # 找到展板目录
        board_dir = None
        for course_dir in self.file_manager.courses_dir.iterdir():
            if course_dir.is_dir():
                potential_board_dir = course_dir / board_id
                if potential_board_dir.exists():
                    board_dir = potential_board_dir
                    break
        
        if not board_dir:
            return {}
        
        icon_positions_file = board_dir / "icon_positions.json"
        if not icon_positions_file.exists():
            return {}
        
        try:
            with open(icon_positions_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    
    def save_icon_positions(self, board_id: str, icon_positions: List[Dict]) -> bool:
        """保存展板的图标位置数据"""
        # 找到展板目录
        board_dir = None
        for course_dir in self.file_manager.courses_dir.iterdir():
            if course_dir.is_dir():
                potential_board_dir = course_dir / board_id
                if potential_board_dir.exists():
                    board_dir = potential_board_dir
                    break
        
        if not board_dir:
            return False
        
        # 将列表转换为字典格式，以windowId为键
        positions_dict = {}
        for item in icon_positions:
            window_id = item.get("windowId")
            if window_id:
                positions_dict[window_id] = {
                    "position": item.get("position"),
                    "gridPosition": item.get("gridPosition")
                }
        
        icon_positions_file = board_dir / "icon_positions.json"
        
        try:
            with open(icon_positions_file, "w", encoding="utf-8") as f:
                json.dump(positions_dict, f, ensure_ascii=False, indent=2)
            return True
        except Exception:
            return False
    
    def _handle_window_file_storage(self, board_dir: Path, window_data: Dict) -> bool:
        """处理窗口文件存储逻辑 - 新的通用系统"""
        window_type = window_data.get("type", "text")
        window_title = window_data.get("title", "新建项目")
        
        if window_type == "generic":
            # 通用窗口：只设置JSON相关信息，不创建实际内容文件
            # 文件路径将在用户选择类型后动态设置
            window_data["file_path"] = None  # 暂时不设置文件路径
            return True
        else:
            # 其他类型窗口的兼容性处理（暂时保留）
            # 这部分将在后续阶段移除
            return True
    
    def _get_file_extension(self, window_type: str) -> str:
        """根据窗口类型获取文件扩展名"""
        extensions = {
            "text": ".txt",
            "image": ".jpg", 
            "video": ".mp4",
            "audio": ".mp3",
            "pdf": ".pdf"
        }
        return extensions.get(window_type, ".txt")
    
    def _generate_unique_filename(self, files_dir: Path, base_name: str, extension: str) -> str:
        """生成唯一的文件名"""
        # 清理文件名中的非法字符
        safe_name = self._sanitize_filename(base_name)
        
        # 检查文件是否存在，如果存在则添加编号
        file_name = f"{safe_name}{extension}"
        if not (files_dir / file_name).exists():
            return file_name
        
        # 添加编号直到找到唯一名称
        counter = 1
        while True:
            file_name = f"{safe_name}({counter}){extension}"
            if not (files_dir / file_name).exists():
                return file_name
            counter += 1
    
    def _sanitize_filename(self, filename: str) -> str:
        """清理文件名中的非法字符"""
        import re
        # 移除或替换Windows文件名中的非法字符
        illegal_chars = r'[<>:"/\\|?*]'
        safe_name = re.sub(illegal_chars, '_', filename)
        # 移除首尾空格和点
        safe_name = safe_name.strip('. ')
        # 如果为空，使用默认名称
        return safe_name if safe_name else "未命名"
    
    def _get_file_path_for_window(self, window_data: Dict) -> str:
        """获取窗口对应的文件路径"""
        window_type = window_data.get("type", "text")
        window_title = window_data.get("title", "未命名")
        extension = self._get_file_extension(window_type)
        safe_name = self._sanitize_filename(window_title)
        return f"files/{safe_name}{extension}"
    
    def rename_window_file(self, board_id: str, window_id: str, old_title: str, new_title: str) -> bool:
        """重命名窗口对应的文件（新存储结构：.md文件 + .md.json配置）"""
        # 找到展板目录
        board_dir = None
        for course_dir in self.file_manager.courses_dir.iterdir():
            if course_dir.is_dir():
                potential_board_dir = course_dir / board_id
                if potential_board_dir.exists():
                    board_dir = potential_board_dir
                    break
        
        if not board_dir:
            print(f"展板目录不存在: {board_id}")
            return False
        
        files_dir = board_dir / "files"
        if not files_dir.exists():
            print(f"文件目录不存在: {files_dir}")
            return False
        
        try:
            # 查找窗口的JSON配置文件
            window_json_file = None
            window_data = None
            
            for json_file in files_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("id") == window_id:
                        window_json_file = json_file
                        window_data = data
                        break
                except Exception as e:
                    print(f"读取JSON文件失败: {json_file}, 错误: {e}")
                    continue
            
            if not window_json_file or not window_data:
                print(f"未找到窗口配置: {window_id}")
                return False
            
            window_type = window_data.get("type", "text")
            old_safe_name = self._sanitize_filename(old_title)
            new_safe_name = self._sanitize_filename(new_title)
            
            print(f"开始重命名窗口文件: {old_title} -> {new_title}")
            print(f"  窗口类型: {window_type}")
            print(f"  旧安全名称: {old_safe_name}")
            print(f"  新安全名称: {new_safe_name}")
            
            if window_type == "text":
                # 文本窗口：重命名 .md 文件和 .md.json 文件
                old_md_file = files_dir / f"{old_safe_name}.md"
                new_md_file = files_dir / f"{new_safe_name}.md"
                old_json_file = files_dir / f"{old_safe_name}.md.json"
                new_json_file = files_dir / f"{new_safe_name}.md.json"
                
                # 重命名内容文件
                if old_md_file.exists():
                    if new_md_file.exists():
                        new_md_file.unlink()  # 删除冲突文件
                    old_md_file.rename(new_md_file)
                    print(f"  重命名内容文件: {old_md_file.name} -> {new_md_file.name}")
                
                # 更新配置数据
                window_data["title"] = new_title
                window_data["file_path"] = f"files/{new_safe_name}.md"
                window_data["updated_at"] = datetime.now().isoformat()
                
                # 重命名配置文件
                if old_json_file.exists():
                    if new_json_file.exists():
                        new_json_file.unlink()  # 删除冲突文件
                    
                    # 写入更新后的配置到新文件
                    with open(new_json_file, "w", encoding="utf-8") as f:
                        json.dump(window_data, f, ensure_ascii=False, indent=2)
                
                    # 删除旧配置文件
                    old_json_file.unlink()
                    print(f"  重命名配置文件: {old_json_file.name} -> {new_json_file.name}")
                
            else:
                # 非文本窗口：重命名实际文件和对应的 .json 配置
                file_path = window_data.get("file_path", "")
                if file_path and file_path.startswith("files/"):
                    old_filename = file_path[6:]  # 移除 "files/" 前缀
                    old_file = files_dir / old_filename
                    
                    # 保持原文件扩展名
                    old_ext = Path(old_filename).suffix
                    new_filename = f"{new_safe_name}{old_ext}"
                    new_file = files_dir / new_filename
                    
                    # 重命名实际文件
                    if old_file.exists():
                        if new_file.exists():
                            new_file.unlink()  # 删除冲突文件
                        old_file.rename(new_file)
                        print(f"  重命名实际文件: {old_filename} -> {new_filename}")
                    
                    # 重命名JSON配置文件
                    old_json_file = files_dir / f"{old_filename}.json"
                    new_json_file = files_dir / f"{new_filename}.json"
                    
                    if old_json_file.exists():
                        # 更新配置数据
                        window_data["title"] = new_title
                        window_data["file_path"] = f"files/{new_filename}"
                        window_data["updated_at"] = datetime.now().isoformat()
                        
                        # 写入更新后的配置到新文件
                        with open(new_json_file, "w", encoding="utf-8") as f:
                            json.dump(window_data, f, ensure_ascii=False, indent=2)
                        
                        # 删除旧配置文件
                        old_json_file.unlink()
                        print(f"  重命名配置文件: {old_json_file.name} -> {new_json_file.name}")
            
            print(f"窗口文件重命名完成: {old_title} -> {new_title}")
            return True
            
        except Exception as e:
            print(f"重命名文件失败: {e}")
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")
        
        return False
    
    def convert_text_window_to_file_window(self, board_id: str, window_id: str, temp_file_path: str, filename: str, window_type: str) -> bool:
        """将文本窗口转换为文件窗口"""
        try:
            # 找到展板目录
            board_dir = None
            for course_dir in self.file_manager.courses_dir.iterdir():
                if course_dir.is_dir():
                    potential_board_dir = course_dir / board_id
                    if potential_board_dir.exists():
                        board_dir = potential_board_dir
                        break
            
            if not board_dir:
                print(f"展板目录不存在: {board_id}")
                return False
            
            files_dir = board_dir / "files"
            if not files_dir.exists():
                print(f"文件目录不存在: {files_dir}")
                return False
            
            # 查找窗口对应的JSON文件
            window_json_file = None
            window_data = None
            for json_file in files_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("id") == window_id:
                        window_json_file = json_file
                        window_data = data
                        break
                except Exception as e:
                    print(f"读取JSON文件失败: {json_file}, 错误: {e}")
                    continue
            
            if not window_json_file or not window_data:
                print(f"未找到窗口配置: {window_id}")
                return False
            
            # 删除原有的.md文件（如果存在）
            if window_data.get('file_path'):
                old_content_file = board_dir / window_data['file_path']
                if old_content_file.exists():
                    old_content_file.unlink()
                    print(f"删除原有内容文件: {old_content_file}")
            
            # 生成新的文件名
            safe_filename = self._sanitize_filename(filename)
            new_file_path = files_dir / safe_filename
            
            # 移动临时文件到目标位置
            import shutil
            shutil.move(temp_file_path, new_file_path)
            print(f"文件保存到: {new_file_path}")
            
            # 更新窗口数据
            window_data['type'] = window_type
            window_data['title'] = safe_filename
            window_data['file_path'] = f"files/{safe_filename}"
            window_data['content'] = f"files/{safe_filename}"  # 对于文件窗口，content存储文件路径
            window_data['updated_at'] = datetime.now().isoformat()
            
            # 生成新的JSON文件名
            new_json_filename = f"{safe_filename}.json"
            new_json_path = files_dir / new_json_filename
            
            # 保存更新的JSON文件
            with open(new_json_path, "w", encoding="utf-8") as f:
                json.dump(window_data, f, ensure_ascii=False, indent=2)
            
            # 删除旧的JSON文件
            if new_json_path != window_json_file:
                window_json_file.unlink()
                print(f"删除旧JSON文件: {window_json_file}")
            
            print(f"窗口转换成功: {window_id} -> {window_type}")
            print(f"新文件名: {safe_filename}")
            print(f"新JSON文件: {new_json_filename}")
            
            return True
            
        except Exception as e:
            print(f"转换文本窗口到文件窗口失败: {e}")
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")
        return False
    
    def find_window_board(self, window_id: str) -> Optional[str]:
        """查找窗口所在的板块ID"""
        try:
            for course_dir in self.file_manager.courses_dir.iterdir():
                if not course_dir.is_dir():
                    continue
                    
                for board_dir in course_dir.iterdir():
                    if not board_dir.is_dir() or not board_dir.name.startswith("board-"):
                        continue
                    
                    # 检查files目录中的JSON文件
                    files_dir = board_dir / "files"
                    if not files_dir.exists():
                        continue
                    
                    for json_file in files_dir.glob("*.json"):
                        try:
                            with open(json_file, "r", encoding="utf-8") as f:
                                window_data = json.load(f)
                            if window_data.get("id") == window_id:
                                return board_dir.name
                        except Exception:
                            continue
            return None
        except Exception as e:
            print(f"查找窗口板块失败: {e}")
            return None
    
    def convert_window_to_text(self, board_id: str, window_id: str) -> bool:
        """将通用窗口转换为文本窗口"""
        try:
            # 找到板块目录
            board_dir = None
            for course_dir in self.file_manager.courses_dir.iterdir():
                if course_dir.is_dir():
                    potential_board_dir = course_dir / board_id
                    if potential_board_dir.exists():
                        board_dir = potential_board_dir
                        break
            
            if not board_dir:
                print(f"找不到板块目录: {board_id}")
                return False
            
            files_dir = board_dir / "files"
            if not files_dir.exists():
                print(f"找不到files目录: {files_dir}")
                return False
            
            # 查找窗口的JSON文件
            window_json_file = None
            window_data = None
            
            for json_file in files_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("id") == window_id:
                        window_json_file = json_file
                        window_data = data
                        break
                except Exception:
                    continue
            
            if not window_json_file or not window_data:
                print(f"找不到窗口JSON文件: {window_id}")
                return False
            
            # 检查是否为通用窗口
            if window_data.get("type") != "generic":
                print(f"窗口不是通用类型: {window_data.get('type')}")
                return False
            
            # 生成新的文件名
            window_title = window_data.get("title", "新建项目")
            safe_name = self._sanitize_filename(window_title)
            
            # 处理重名冲突
            md_file_name = self._generate_unique_filename(files_dir, safe_name, ".md")
            json_file_name = f"{md_file_name}.json"
            
            # 创建Markdown文件
            md_file_path = files_dir / md_file_name
            with open(md_file_path, "w", encoding="utf-8") as f:
                f.write("# " + window_title + "\n\n")  # 添加默认标题
            
            # 更新窗口数据
            window_data["type"] = "text"
            window_data["file_path"] = f"files/{md_file_name}"
            window_data["updated_at"] = datetime.now().isoformat()
            
            # 重命名JSON文件
            new_json_file_path = files_dir / json_file_name
            
            # 如果新JSON文件名与旧的不同，需要重命名
            if window_json_file.name != json_file_name:
                # 先保存更新后的数据到新文件
                with open(new_json_file_path, "w", encoding="utf-8") as f:
                    json.dump(window_data, f, ensure_ascii=False, indent=2)
                
                # 删除旧的JSON文件
                window_json_file.unlink()
            else:
                # 文件名相同，直接更新内容
                with open(window_json_file, "w", encoding="utf-8") as f:
                    json.dump(window_data, f, ensure_ascii=False, indent=2)
            
            print(f"成功将窗口转换为文本: {window_id} -> {md_file_name}")
            return True
            
        except Exception as e:
            print(f"转换窗口失败: {e}")
            return False
    
    def update_window_content(self, board_id: str, window_id: str, content: str) -> bool:
        """更新窗口内容到文件"""
        try:
            # 找到板块目录
            board_dir = None
            for course_dir in self.file_manager.courses_dir.iterdir():
                if course_dir.is_dir():
                    potential_board_dir = course_dir / board_id
                    if potential_board_dir.exists():
                        board_dir = potential_board_dir
                        break
            
            if not board_dir:
                print(f"找不到板块目录: {board_id}")
                return False
            
            files_dir = board_dir / "files"
            if not files_dir.exists():
                print(f"找不到files目录: {files_dir}")
                return False
            
            # 查找窗口的JSON文件以获取文件路径
            window_json_file = None
            window_data = None
            
            for json_file in files_dir.glob("*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if data.get("id") == window_id:
                        window_json_file = json_file
                        window_data = data
                        break
                except Exception:
                    continue
            
            if not window_json_file or not window_data:
                print(f"找不到窗口JSON文件: {window_id}")
                return False
            
            # 获取内容文件路径
            file_path = window_data.get("file_path")
            if not file_path:
                print(f"窗口没有关联的内容文件: {window_id}")
                return False
            
            # 内容文件的完整路径
            if file_path.startswith("files/"):
                content_file_path = board_dir / file_path
            else:
                content_file_path = files_dir / file_path
            
            # 写入内容到文件
            with open(content_file_path, "w", encoding="utf-8") as f:
                f.write(content)
            
            # 更新JSON文件的更新时间
            window_data["updated_at"] = datetime.now().isoformat()
            with open(window_json_file, "w", encoding="utf-8") as f:
                json.dump(window_data, f, ensure_ascii=False, indent=2)
            
            print(f"成功更新窗口内容: {window_id}")
            return True
            
        except Exception as e:
            print(f"更新窗口内容失败: {e}")
            return False
    
    def extract_pdf_text_to_pages(self, board_id: str, window_id: str, window_data: Dict) -> bool:
        """提取PDF文本并保存到pages文件夹"""
        try:
            # 找到展板目录
            board_dir = None
            for course_dir in self.file_manager.courses_dir.iterdir():
                if course_dir.is_dir():
                    potential_board_dir = course_dir / board_id
                    if potential_board_dir.exists():
                        board_dir = potential_board_dir
                        break
            
            if not board_dir:
                print(f"展板目录不存在: {board_id}")
                return False
            
            # 获取PDF文件路径
            pdf_file_path = None
            if window_data.get('file_path'):
                pdf_file_path = board_dir / window_data['file_path']
            
            if not pdf_file_path or not pdf_file_path.exists():
                print(f"PDF文件不存在: {pdf_file_path}")
                return False
            
            # 创建pages文件夹结构
            pages_dir = board_dir / "files" / "pages"
            pages_dir.mkdir(exist_ok=True)
            
            # 获取PDF文件名（不含扩展名）
            pdf_name = pdf_file_path.stem
            pdf_pages_dir = pages_dir / pdf_name
            pdf_pages_dir.mkdir(exist_ok=True)
            
            print(f"开始提取PDF文本: {pdf_file_path}")
            
            # 使用pypdf提取文本
            with open(pdf_file_path, 'rb') as file:
                pdf_reader = pypdf.PdfReader(file)
                total_pages = len(pdf_reader.pages)
                
                print(f"PDF总页数: {total_pages}")
                
                for page_num in range(total_pages):
                    try:
                        page = pdf_reader.pages[page_num]
                        text = page.extract_text()
                        
                        # 保存到MD文件
                        page_filename = f"{pdf_name}_page_{page_num + 1:03d}.md"
                        page_file_path = pdf_pages_dir / page_filename
                        
                        # 创建MD文件内容
                        md_content = f"# {pdf_name} - 第 {page_num + 1} 页\n\n"
                        md_content += f"来源: {window_data.get('title', 'unknown.pdf')}\n"
                        md_content += f"提取时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        md_content += f"页码: {page_num + 1}/{total_pages}\n\n"
                        md_content += "---\n\n"
                        
                        if text.strip():
                            md_content += text.strip()
                        else:
                            md_content += "*此页面没有可提取的文本内容*"
                        
                        # 写入文件
                        with open(page_file_path, 'w', encoding='utf-8') as f:
                            f.write(md_content)
                        
                        print(f"已保存第 {page_num + 1} 页文本: {page_filename}")
                        
                    except Exception as e:
                        print(f"提取第 {page_num + 1} 页文本失败: {e}")
                        continue
                
                print(f"PDF文本提取完成: {total_pages} 页 -> {pdf_pages_dir}")
                return True
                
        except Exception as e:
            print(f"PDF文本提取失败: {e}")
            import traceback
            print(f"详细错误信息: {traceback.format_exc()}")
            return False 