import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

class ConversationManager:
    """LLM对话记录管理器"""
    
    def __init__(self, file_manager):
        self.file_manager = file_manager
    
    def get_board_conversations_dir(self, board_id: str) -> Optional[Path]:
        """获取指定展板的对话目录"""
        # 遍历所有课程寻找对应的展板
        for course_dir in self.file_manager.courses_dir.iterdir():
            if course_dir.is_dir():
                board_dir = course_dir / board_id
                if board_dir.exists():
                    conversations_dir = board_dir / "llm_conversations"
                    if conversations_dir.exists():
                        return conversations_dir
                    else:
                        # 如果不存在，创建目录
                        conversations_dir.mkdir(exist_ok=True)
                        return conversations_dir
        return None
    
    def create_conversation(self, board_id: str, title: str = "") -> Dict:
        """创建新的对话记录"""
        conversations_dir = self.get_board_conversations_dir(board_id)
        if not conversations_dir:
            raise ValueError(f"找不到展板: {board_id}")
        
        # 生成对话ID
        conversation_id = f"conv-{int(datetime.now().timestamp() * 1000)}"
        
        # 创建对话数据
        conversation_data = {
            "id": conversation_id,
            "title": title or "新对话",
            "board_id": board_id,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "messages": []
        }
        
        # 保存到文件
        conversation_file = conversations_dir / f"{conversation_id}.json"
        with open(conversation_file, "w", encoding="utf-8") as f:
            json.dump(conversation_data, f, ensure_ascii=False, indent=2)
        
        return conversation_data
    
    def get_conversation(self, board_id: str, conversation_id: str) -> Optional[Dict]:
        """获取指定对话记录"""
        conversations_dir = self.get_board_conversations_dir(board_id)
        if not conversations_dir:
            return None
        
        conversation_file = conversations_dir / f"{conversation_id}.json"
        if not conversation_file.exists():
            return None
        
        try:
            with open(conversation_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"读取对话文件失败: {e}")
            return None
    
    def get_board_conversations(self, board_id: str) -> List[Dict]:
        """获取展板的所有对话记录（仅基本信息）"""
        conversations_dir = self.get_board_conversations_dir(board_id)
        if not conversations_dir:
            return []
        
        conversations = []
        for conv_file in conversations_dir.glob("conv-*.json"):
            try:
                with open(conv_file, "r", encoding="utf-8") as f:
                    conv_data = json.load(f)
                    # 只返回基本信息，不包含完整消息历史
                    basic_info = {
                        "id": conv_data.get("id"),
                        "title": conv_data.get("title", "未命名对话"),
                        "created_at": conv_data.get("created_at"),
                        "updated_at": conv_data.get("updated_at"),
                        "message_count": len(conv_data.get("messages", []))
                    }
                    conversations.append(basic_info)
            except Exception as e:
                print(f"读取对话文件失败: {conv_file}, 错误: {e}")
                continue
        
        # 按更新时间倒序排列
        conversations.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        return conversations
    
    def add_message(self, board_id: str, conversation_id: str, message: Dict) -> bool:
        """向对话中添加消息"""
        conversation = self.get_conversation(board_id, conversation_id)
        if not conversation:
            return False
        
        # 添加消息时间戳
        message["timestamp"] = datetime.now().isoformat()
        
        # 如果消息包含文件，确保文件信息完整
        if "files" in message and message["files"]:
            for file_info in message["files"]:
                if "timestamp" not in file_info:
                    file_info["timestamp"] = message["timestamp"]
        
        # 添加消息到对话记录
        conversation["messages"].append(message)
        conversation["updated_at"] = datetime.now().isoformat()
        
        # 保存更新后的对话
        conversations_dir = self.get_board_conversations_dir(board_id)
        conversation_file = conversations_dir / f"{conversation_id}.json"
        
        try:
            with open(conversation_file, "w", encoding="utf-8") as f:
                json.dump(conversation, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"保存对话失败: {e}")
            return False
    
    def update_conversation_title(self, board_id: str, conversation_id: str, new_title: str) -> bool:
        """更新对话标题"""
        conversation = self.get_conversation(board_id, conversation_id)
        if not conversation:
            return False
        
        conversation["title"] = new_title
        conversation["updated_at"] = datetime.now().isoformat()
        
        conversations_dir = self.get_board_conversations_dir(board_id)
        conversation_file = conversations_dir / f"{conversation_id}.json"
        
        try:
            with open(conversation_file, "w", encoding="utf-8") as f:
                json.dump(conversation, f, ensure_ascii=False, indent=2)
            return True
        except Exception as e:
            print(f"更新对话标题失败: {e}")
            return False
    
    def delete_conversation(self, board_id: str, conversation_id: str) -> bool:
        """删除对话记录"""
        conversations_dir = self.get_board_conversations_dir(board_id)
        if not conversations_dir:
            return False
        
        conversation_file = conversations_dir / f"{conversation_id}.json"
        if not conversation_file.exists():
            return False
        
        try:
            conversation_file.unlink()
            return True
        except Exception as e:
            print(f"删除对话失败: {e}")
            return False
    
    def get_conversation_context(self, board_id: str, conversation_id: str, limit: int = 50) -> List[Dict]:
        """获取对话上下文（限制消息数量以控制token使用）"""
        conversation = self.get_conversation(board_id, conversation_id)
        if not conversation:
            return []
        
        messages = conversation.get("messages", [])
        # 返回最近的limit条消息
        return messages[-limit:] if len(messages) > limit else messages
