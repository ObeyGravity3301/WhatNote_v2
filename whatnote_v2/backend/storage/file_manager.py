import os
import json
import shutil
from pathlib import Path
from config import DATA_DIR
from typing import Dict, List, Optional
from datetime import datetime

class FileSystemManager:
    def __init__(self, data_dir: str | Path = None):
        # 统一使用 config.DATA_DIR，除非显式传入
        self.data_dir = Path(data_dir) if data_dir else Path(DATA_DIR)
        self.courses_dir = self.data_dir / "courses"
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
        """获取所有课程"""
        courses = []
        for course_dir in self.courses_dir.iterdir():
            if course_dir.is_dir():
                course_info_path = course_dir / "course_info.json"
                if course_info_path.exists():
                    with open(course_info_path, "r", encoding="utf-8") as f:
                        courses.append(json.load(f))
        return courses
    
    def get_boards(self, course_id: str) -> List[Dict]:
        """获取课程的所有展板"""
        course_dir = self.courses_dir / course_id
        if not course_dir.exists():
            return []
        
        boards = []
        for board_dir in course_dir.iterdir():
            if board_dir.is_dir() and board_dir.name.startswith("board-"):
                board_info_path = board_dir / "board_info.json"
                if board_info_path.exists():
                    with open(board_info_path, "r", encoding="utf-8") as f:
                        boards.append(json.load(f))
        return boards
    
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
    
    def delete_board(self, board_id: str) -> bool:
        """删除展板文件夹"""
        for course_dir in self.courses_dir.iterdir():
            if course_dir.is_dir():
                board_dir = course_dir / board_id
                if board_dir.exists():
                    shutil.rmtree(board_dir)
                    # 更新课程信息
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