import os
import json
import shutil
from pathlib import Path
from config import DATA_DIR
from typing import Dict, List, Optional
from datetime import datetime
from storage.trash_manager import TrashManager

class FileSystemManager:
    def __init__(self, data_dir: str | Path = None):
        # 统一使用 config.DATA_DIR，除非显式传入
        self.data_dir = Path(data_dir) if data_dir else Path(DATA_DIR)
        self.courses_dir = self.data_dir / "courses"
        self.trash_manager = TrashManager()
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保基础目录存在"""
        self.courses_dir.mkdir(parents=True, exist_ok=True)
    
    def create_course(self, name: str, description: str = "") -> Dict:
        """创建课程文件夹"""
        course_id = f"course-{int(datetime.now().timestamp() * 1000)}"
        course_dir = self.courses_dir / course_id
        course_dir.mkdir(exist_ok=True)
        
        course_info = {
            "id": course_id,
            "name": name,
            "description": description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "boards": []
        }
        
        with open(course_dir / "course_info.json", "w", encoding="utf-8") as f:
            json.dump(course_info, f, ensure_ascii=False, indent=2)
        
        return course_info
    
    def create_board(self, course_id: str, board_name: str) -> Dict:
        """创建展板文件夹"""
        course_dir = self.courses_dir / course_id
        if not course_dir.exists():
            raise ValueError(f"课程不存在: {course_id}")
        
        board_id = f"board-{int(datetime.now().timestamp() * 1000)}"
        board_dir = course_dir / board_id
        board_dir.mkdir(exist_ok=True)
        
        # 创建展板子目录（简化结构）
        subdirs = ["windows", "files"]
        for subdir in subdirs:
            (board_dir / subdir).mkdir(exist_ok=True)
        
        # 创建pages文件夹用于存储PDF文本提取结果
        pages_dir = board_dir / "files" / "pages"
        pages_dir.mkdir(exist_ok=True)
        
        board_info = {
            "id": board_id,
            "name": board_name,
            "course_id": course_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "windows": []
        }
        
        with open(board_dir / "board_info.json", "w", encoding="utf-8") as f:
            json.dump(board_info, f, ensure_ascii=False, indent=2)
        
        # 更新课程信息
        self._update_course_boards(course_id, board_id)
        
        return board_info
    
    def _update_course_boards(self, course_id: str, board_id: str):
        """更新课程信息中的展板列表"""
        course_info_path = self.courses_dir / course_id / "course_info.json"
        if course_info_path.exists():
            with open(course_info_path, "r", encoding="utf-8") as f:
                course_info = json.load(f)
            
            if board_id not in course_info["boards"]:
                course_info["boards"].append(board_id)
                course_info["updated_at"] = datetime.now().isoformat()
                
                with open(course_info_path, "w", encoding="utf-8") as f:
                    json.dump(course_info, f, ensure_ascii=False, indent=2)
    
    def get_courses(self) -> List[Dict]:
        """获取所有课程，支持自定义排序"""
        courses = []
        for course_dir in self.courses_dir.iterdir():
            if course_dir.is_dir():
                course_info_path = course_dir / "course_info.json"
                if course_info_path.exists():
                    with open(course_info_path, "r", encoding="utf-8") as f:
                        courses.append(json.load(f))
        
        # 读取课程排序文件
        order_path = self.courses_dir / "courses_order.json"
        if order_path.exists():
            try:
                with open(order_path, "r", encoding="utf-8") as f:
                    order = json.load(f)
                # 根据排序文件进行排序
                course_map = {c["id"]: c for c in courses}
                sorted_courses = []
                # 首先按顺序添加在排序文件中的课程
                for course_id in order:
                    if course_id in course_map:
                        sorted_courses.append(course_map.pop(course_id))
                # 然后添加不在排序文件中的剩余课程（如果有的话）
                sorted_courses.extend(course_map.values())
                return sorted_courses
            except Exception as e:
                print(f"读取课程排序失败: {e}")
        
        return courses
    
    def get_boards(self, course_id: str) -> List[Dict]:
        """获取课程的所有展板，遵循 course_info.json 中的顺序"""
        course_dir = self.courses_dir / course_id
        if not course_dir.exists():
            return []
        
        course_info_path = course_dir / "course_info.json"
        if not course_info_path.exists():
            return []
            
        with open(course_info_path, "r", encoding="utf-8") as f:
            course_info = json.load(f)
            
        board_ids = course_info.get("boards", [])
        boards_map = {}
        
        # 扫描实际存在的展板
        for board_dir in course_dir.iterdir():
            if board_dir.is_dir() and board_dir.name.startswith("board-"):
                board_info_path = board_dir / "board_info.json"
                if board_info_path.exists():
                    with open(board_info_path, "r", encoding="utf-8") as f:
                        board_data = json.load(f)
                        boards_map[board_data["id"]] = board_data
        
        # 按照 course_info.json 中的顺序返回
        sorted_boards = []
        for b_id in board_ids:
            if b_id in boards_map:
                sorted_boards.append(boards_map.pop(b_id))
        
        # 将不在列表中的展板（如果有的话）添加到末尾
        sorted_boards.extend(boards_map.values())
        return sorted_boards

    def reorder_courses(self, course_ids: List[str]) -> bool:
        """保存课程排序"""
        try:
            order_path = self.courses_dir / "courses_order.json"
            with open(order_path, "w", encoding="utf-8") as f:
                json.dump(course_ids, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存课程排序失败: {e}")
            return False

    def reorder_boards(self, course_id: str, board_ids: List[str]) -> bool:
        """保存展板排序"""
        try:
            course_info_path = self.courses_dir / course_id / "course_info.json"
            if not course_info_path.exists():
                return False
                
            with open(course_info_path, "r", encoding="utf-8") as f:
                course_info = json.load(f)
                
            course_info["boards"] = board_ids
            course_info["updated_at"] = datetime.now().isoformat()
            
            with open(course_info_path, "w", encoding="utf-8") as f:
                json.dump(course_info, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存展板排序失败: {e}")
            return False
            
    def get_board_info(self, board_id: str) -> Optional[Dict]:
        """获取展板信息"""
        for course_dir in self.courses_dir.iterdir():
            if course_dir.is_dir():
                board_dir = course_dir / board_id
                if board_dir.exists():
                    board_info_path = board_dir / "board_info.json"
                    if board_info_path.exists():
                        with open(board_info_path, "r", encoding="utf-8") as f:
                            return json.load(f)
        return None
    
    def delete_course(self, course_id: str) -> bool:
        """删除课程（移动到回收站）"""
        course_dir = self.courses_dir / course_id
        if course_dir.exists():
            # 读取课程信息
            course_info = {}
            course_info_path = course_dir / "course_info.json"
            if course_info_path.exists():
                with open(course_info_path, "r", encoding="utf-8") as f:
                    course_info = json.load(f)
            
            # 移动到回收站
            success = self.trash_manager.move_course_to_trash(course_id, course_dir, course_info)
            return success is not None
        return False

    def delete_board(self, board_id: str) -> bool:
        """删除展板（移动到回收站）"""
        for course_dir in self.courses_dir.iterdir():
            if course_dir.is_dir():
                board_dir = course_dir / board_id
                if board_dir.exists():
                    # 读取展板信息
                    board_info = {}
                    board_info_path = board_dir / "board_info.json"
                    if board_info_path.exists():
                        with open(board_info_path, "r", encoding="utf-8") as f:
                            board_info = json.load(f)
                    
                    # 移动到回收站
                    success = self.trash_manager.move_board_to_trash(board_id, board_dir, board_info)
                    if success:
                        # 从课程信息中移除
                        self._remove_board_from_course(course_dir, board_id)
                        return True
        return False
    
    def _remove_board_from_course(self, course_dir: Path, board_id: str):
        """从课程信息中移除展板"""
        course_info_path = course_dir / "course_info.json"
        if course_info_path.exists():
            with open(course_info_path, "r", encoding="utf-8") as f:
                course_info = json.load(f)
            
            if board_id in course_info["boards"]:
                course_info["boards"].remove(board_id)
                course_info["updated_at"] = datetime.now().isoformat()
                
                with open(course_info_path, "w", encoding="utf-8") as f:
                    json.dump(course_info, f, ensure_ascii=False, indent=2)

    def rename_course(self, course_id: str, new_name: str) -> bool:
        """重命名课程"""
        course_dir = self.courses_dir / course_id
        course_info_path = course_dir / "course_info.json"
        if course_info_path.exists():
            with open(course_info_path, "r", encoding="utf-8") as f:
                course_info = json.load(f)
            
            course_info["name"] = new_name
            course_info["updated_at"] = datetime.now().isoformat()
            
            with open(course_info_path, "w", encoding="utf-8") as f:
                json.dump(course_info, f, ensure_ascii=False, indent=2)
            return True
        return False

    def rename_board(self, board_id: str, new_name: str) -> bool:
        """重命名展板"""
        for course_dir in self.courses_dir.iterdir():
            if course_dir.is_dir():
                board_dir = course_dir / board_id
                if board_dir.exists():
                    board_info_path = board_dir / "board_info.json"
                    if board_info_path.exists():
                        with open(board_info_path, "r", encoding="utf-8") as f:
                            board_info = json.load(f)
                        
                        board_info["name"] = new_name
                        board_info["updated_at"] = datetime.now().isoformat()
                        
                        with open(board_info_path, "w", encoding="utf-8") as f:
                            json.dump(board_info, f, ensure_ascii=False, indent=2)
                        return True
        return False

    def ensure_course_exists(self, course_id: str):
        """确保课程文件夹和元数据文件存在（用于恢复展板时自动重建课程壳）"""
        course_dir = self.courses_dir / course_id
        if not course_dir.exists():
            course_dir.mkdir(parents=True, exist_ok=True)
            print(f"自动重建缺失的课程目录: {course_id}")
            
        course_info_path = course_dir / "course_info.json"
        if not course_info_path.exists():
            # 自动创建一个基础的课程信息文件
            course_info = {
                "id": course_id,
                "name": f"已恢复课程 ({course_id[:8]})",
                "description": "自动恢复的课程壳",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat(),
                "boards": []
            }
            with open(course_info_path, "w", encoding="utf-8") as f:
                json.dump(course_info, f, ensure_ascii=False, indent=2)
            print(f"自动重建缺失的课程信息文件: {course_info_path}")

    def register_board_to_course(self, course_id: str, board_id: str):
        """将展板显式注册到课程的元数据中"""
        self._update_course_boards(course_id, board_id)
        print(f"展板 {board_id} 已重新注册到课程 {course_id}")
