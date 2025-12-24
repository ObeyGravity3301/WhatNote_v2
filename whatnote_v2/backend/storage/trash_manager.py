import json
import shutil
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from config import TRASH_DIR


class TrashManager:
    """回收站管理器"""
    
    def __init__(self):
        """初始化回收站管理器"""
        self.trash_dir = TRASH_DIR
        self.trash_info_file = self.trash_dir / "trash_info.json"
        self._ensure_trash_dir()
    
    def _ensure_trash_dir(self):
        """确保回收站目录存在"""
        self.trash_dir.mkdir(parents=True, exist_ok=True)
        if not self.trash_info_file.exists():
            with open(self.trash_info_file, 'w', encoding='utf-8') as f:
                json.dump([], f, ensure_ascii=False, indent=2)
    
    def _load_trash_info(self) -> List[Dict]:
        """加载回收站信息"""
        try:
            with open(self.trash_info_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"加载回收站信息失败: {e}")
            return []
    
    def _save_trash_info(self, trash_info: List[Dict]):
        """保存回收站信息"""
        try:
            with open(self.trash_info_file, 'w', encoding='utf-8') as f:
                json.dump(trash_info, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存回收站信息失败: {e}")
    
    def move_to_trash(self, file_path: Path, window_data: Dict, board_id: str, parent_id: str = None) -> Optional[str]:
        """将文件移动到回收站
        返回创建的回收站项目ID，失败返回None
        """
        try:
            if not file_path.exists():
                print(f"文件不存在，无法移动到回收站: {file_path}")
                return None
            
            # 生成唯一的回收站文件名
            timestamp = int(time.time() * 1000)
            original_name = file_path.name
            trash_filename = f"{timestamp}_{original_name}"
            trash_file_path = self.trash_dir / trash_filename
            
            # 移动文件到回收站
            if file_path.is_dir():
                shutil.copytree(str(file_path), str(trash_file_path))
                shutil.rmtree(str(file_path))
            else:
                shutil.move(str(file_path), str(trash_file_path))
            
            # 记录回收站信息
            trash_info = self._load_trash_info()
            
            # 计算大小
            file_size = 0
            if trash_file_path.is_dir():
                for f in trash_file_path.glob('**/*'):
                    if f.is_file():
                        file_size += f.stat().st_size
            else:
                file_size = trash_file_path.stat().st_size
                
            trash_id = f"trash_{timestamp}"
            trash_item = {
                "id": trash_id,
                "parent_id": parent_id,
                "original_name": original_name,
                "trash_filename": trash_filename,
                "window_data": window_data,
                "board_id": board_id,
                "deleted_at": datetime.now().isoformat(),
                "original_path": str(file_path.parent),
                "file_size": file_size,
                "item_type": "directory" if trash_file_path.is_dir() else "file"
            }
            trash_info.append(trash_item)
            self._save_trash_info(trash_info)
            
            print(f"项目已移动到回收站: {original_name} -> {trash_filename} (parent: {parent_id})")
            return trash_id
            
        except Exception as e:
            print(f"移动项目到回收站失败: {e}")
            import traceback
            traceback.print_exc()
            return None

    def move_course_to_trash(self, course_id: str, course_path: Path, course_info: Dict) -> Optional[str]:
        """将课程移动到回收站"""
        return self.move_to_trash(course_path, {"type": "course", "data": course_info}, "system")

    def move_board_to_trash(self, board_id: str, board_path: Path, board_info: Dict) -> Optional[str]:
        """将展板移动到回收站"""
        return self.move_to_trash(board_path, {"type": "board", "data": board_info}, board_info.get("course_id", "unknown"))

    def get_trash_items(self) -> List[Dict]:
        """获取回收站中的所有项目"""
        trash_info = self._load_trash_info()
        # 添加文件是否存在的检查
        for item in trash_info:
            trash_file_path = self.trash_dir / item["trash_filename"]
            item["file_exists"] = trash_file_path.exists()
        return trash_info
    
    def restore_from_trash(self, trash_id: str) -> bool:
        """从回收站恢复文件"""
        try:
            trash_info = self._load_trash_info()
            trash_item = None
            item_index = -1
            
            # 查找要恢复的项目
            for i, item in enumerate(trash_info):
                if item["id"] == trash_id:
                    trash_item = item
                    item_index = i
                    break
            
            if not trash_item:
                print(f"回收站中未找到项目: {trash_id}")
                return False
            
            # 1. 恢复主项目
            success = self._restore_single_item(trash_item)
            if not success:
                return False

            # 2. 联动恢复所有子项
            children = [item for item in trash_info if item.get("parent_id") == trash_id]
            for child in children:
                print(f"发现联动子项，正在恢复: {child['original_name']}")
                self._restore_single_item(child)

            # 3. 从回收站信息中移除主项和所有子项
            new_trash_info = [item for item in trash_info if item["id"] != trash_id and item.get("parent_id") != trash_id]
            self._save_trash_info(new_trash_info)
            
            return True
            
        except Exception as e:
            print(f"从回收站恢复文件失败: {e}")
            import traceback
            traceback.print_exc()
            return False

    def _restore_single_item(self, trash_item: Dict) -> bool:
        """还原单个回收站项目（不处理联动）"""
        try:
            trash_file_path = self.trash_dir / trash_item["trash_filename"]
            if not trash_file_path.exists():
                print(f"回收站文件不存在: {trash_item['trash_filename']}")
                return False
            
            # 恢复文件到原位置
            original_dir = Path(trash_item["original_path"])
            original_dir.mkdir(parents=True, exist_ok=True)
            original_file_path = original_dir / trash_item["original_name"]
            
            # 如果原位置已有同名文件，生成新名称
            if original_file_path.exists():
                base_name = Path(trash_item["original_name"]).stem
                extension = Path(trash_item["original_name"]).suffix
                counter = 1
                while original_file_path.exists():
                    new_name = f"{base_name}({counter}){extension}"
                    original_file_path = original_dir / new_name
                    counter += 1
            
            # 移动文件回原位置
            shutil.move(str(trash_file_path), str(original_file_path))
            
            # 方案三处理：如果是展板恢复，确保父课程存在并重新注册
            window_data = trash_item.get("window_data", {})
            if window_data and window_data.get("type") == "board":
                try:
                    from storage.file_manager import FileSystemManager
                    fm = FileSystemManager()
                    board_info = window_data.get("data", {})
                    course_id = board_info.get("course_id")
                    if course_id:
                        fm.ensure_course_exists(course_id)
                        fm.register_board_to_course(course_id, board_info.get("id"))
                except Exception as e:
                    print(f"恢复展板元数据失败: {e}")
            
            print(f"文件已从回收站恢复: {trash_item['original_name']}")
            return True
        except Exception as e:
            print(f"还原单个项目失败: {e}")
            return False
    
    def permanently_delete(self, trash_id: str) -> bool:
        """永久删除回收站中的文件"""
        try:
            trash_info = self._load_trash_info()
            
            # 1. 查找主项
            trash_item = next((item for item in trash_info if item["id"] == trash_id), None)
            if not trash_item:
                print(f"回收站中未找到项目: {trash_id}")
                return False
            
            # 2. 查找所有子项
            children = [item for item in trash_info if item.get("parent_id") == trash_id]
            
            # 3. 删除物理文件（主项和所有子项）
            items_to_delete = [trash_item] + children
            for item in items_to_delete:
                trash_file_path = self.trash_dir / item["trash_filename"]
                if trash_file_path.exists():
                    if trash_file_path.is_dir():
                        shutil.rmtree(trash_file_path)
                    else:
                        trash_file_path.unlink()
                print(f"物理文件已永久删除: {item['original_name']}")
            
            # 4. 从回收站信息中移除主项和所有子项
            new_trash_info = [item for item in trash_info if item["id"] != trash_id and item.get("parent_id") != trash_id]
            self._save_trash_info(new_trash_info)
            
            return True
            
        except Exception as e:
            print(f"永久删除文件失败: {e}")
            return False
    
    def empty_trash(self) -> bool:
        """清空回收站"""
        try:
            trash_info = self._load_trash_info()
            
            # 删除所有回收站文件或文件夹
            for item in trash_info:
                trash_file_path = self.trash_dir / item["trash_filename"]
                if trash_file_path.exists():
                    if trash_file_path.is_dir():
                        shutil.rmtree(trash_file_path)
                    else:
                        trash_file_path.unlink()
            
            # 清空回收站信息
            self._save_trash_info([])
            
            print("回收站已清空")
            return True
            
        except Exception as e:
            print(f"清空回收站失败: {e}")
            return False
    
    def get_trash_size(self) -> int:
        """获取回收站总大小（字节）"""
        try:
            total_size = 0
            trash_info = self._load_trash_info()
            
            for item in trash_info:
                trash_file_path = self.trash_dir / item["trash_filename"]
                if trash_file_path.exists():
                    if trash_file_path.is_dir():
                        for sub_path in trash_file_path.rglob('*'):
                            if sub_path.is_file():
                                total_size += sub_path.stat().st_size
                    else:
                        total_size += trash_file_path.stat().st_size
            
            return total_size
            
        except Exception as e:
            print(f"计算回收站大小失败: {e}")
            return 0
    
    def move_pdf_pages_to_trash(self, board_dir: Path, pdf_filename: str, parent_id: str = None) -> bool:
        """将PDF对应的pages文件夹移动到回收站"""
        try:
            # 获取PDF文件名（不含扩展名）
            pdf_name = Path(pdf_filename).stem
            
            # 查找pages文件夹中对应的PDF文件夹
            pages_dir = board_dir / "files" / "pages"
            pdf_pages_dir = pages_dir / pdf_name
            
            if not pdf_pages_dir.exists():
                print(f"PDF pages文件夹不存在: {pdf_pages_dir}")
                return True  # 不存在也算成功
            
            # 生成唯一的回收站文件夹名
            timestamp = int(time.time() * 1000)
            trash_folder_name = f"{timestamp}_{pdf_name}_pages"
            trash_folder_path = self.trash_dir / trash_folder_name
            
            # 移动整个文件夹到回收站
            shutil.move(str(pdf_pages_dir), str(trash_folder_path))
            
            # 记录回收站信息
            trash_info = self._load_trash_info()
            trash_item = {
                "id": f"trash_{timestamp}_pages",
                "parent_id": parent_id,
                "original_name": f"{pdf_name}_pages",
                "trash_filename": trash_folder_name,
                "type": "pdf_pages_folder",
                "pdf_name": pdf_name,
                "deleted_at": datetime.now().isoformat(),
                "original_path": str(pdf_pages_dir.parent),
                "is_folder": True
            }
            trash_info.append(trash_item)
            self._save_trash_info(trash_info)
            
            print(f"PDF pages文件夹已移动到回收站: {pdf_name} -> {trash_folder_name} (parent: {parent_id})")
            return True
            
        except Exception as e:
            print(f"移动PDF pages文件夹到回收站失败: {e}")
            return False