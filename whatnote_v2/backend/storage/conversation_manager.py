import os
import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from logger import info

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
            "messages": [],
            "todo_state": None,
            "todo_status": None
        }
        
        # 保存到文件
        conversation_file = conversations_dir / f"{conversation_id}.json"
        with open(conversation_file, "w", encoding="utf-8") as f:
            json.dump(conversation_data, f, ensure_ascii=False, indent=2)
        
        return conversation_data
    
    def get_conversation(self, board_id: str, conversation_id: str, page: int = 0, limit: int = 20) -> Optional[Dict]:
        """获取指定对话记录，支持分页"""
        conversations_dir = self.get_board_conversations_dir(board_id)
        if not conversations_dir:
            return None
        
        conversation_file = conversations_dir / f"{conversation_id}.json"
        if not conversation_file.exists():
            return None
        
        try:
            with open(conversation_file, "r", encoding="utf-8") as f:
                conversation_data = json.load(f)
            
            # 如果指定了分页参数，则只返回分页后的消息
            if page is not None and limit is not None:
                messages = conversation_data.get("messages", [])
                # 从最新消息开始分页（最新的消息在数组末尾）
                total_messages = len(messages)
                start_index = max(0, total_messages - (page + 1) * limit)
                end_index = total_messages - page * limit
                
                # 获取分页后的消息（从旧到新排序）
                paginated_messages = messages[start_index:end_index]
                
                # 返回分页后的对话数据
                return {
                    "id": conversation_data.get("id"),
                    "title": conversation_data.get("title"),
                    "created_at": conversation_data.get("created_at"),
                    "updated_at": conversation_data.get("updated_at"),
                    "messages": paginated_messages,
                    "total_messages": total_messages,
                    "page": page,
                    "limit": limit,
                    "has_more": start_index > 0,
                    "todo_status": conversation_data.get("todo_status")
                }
            else:
                # 如果不分页，返回完整对话
                return conversation_data
                
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
        conversation = self.get_conversation(board_id, conversation_id, page=None, limit=None)
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
    
    def clear_conversation_messages(self, board_id: str, conversation_id: str) -> bool:
        """清空对话的所有消息（保留对话记录）"""
        conversation = self.get_conversation(board_id, conversation_id, page=None, limit=None)
        if not conversation:
            info(f"[ConversationManager] 清空对话失败，未找到对话: board_id={board_id}, conversation_id={conversation_id}")
            return False
        
        # 清空消息数组，保留其他元数据
        conversation["messages"] = []
        conversation["todo_state"] = None
        conversation["todo_status"] = None
        conversation["updated_at"] = datetime.now().isoformat()
        
        conversations_dir = self.get_board_conversations_dir(board_id)
        conversation_file = conversations_dir / f"{conversation_id}.json"
        
        try:
            with open(conversation_file, "w", encoding="utf-8") as f:
                json.dump(conversation, f, ensure_ascii=False, indent=2)
            info(f"[ConversationManager] 已清空对话消息并重置待办状态: board_id={board_id}, conversation_id={conversation_id}")
            return True
        except Exception as e:
            print(f"清空对话消息失败: {e}")
            return False
    
    def get_conversation_context(self, board_id: str, conversation_id: str, limit: int = 50) -> List[Dict]:
        """获取对话上下文（限制消息数量以控制token使用）"""
        conversation = self.get_conversation(board_id, conversation_id)
        if not conversation:
            return []
        
        messages = conversation.get("messages", [])
        # 返回最近的limit条消息
        return messages[-limit:] if len(messages) > limit else messages

    def get_todo_state(self, board_id: str, conversation_id: str) -> Optional[Dict]:
        """获取对话的todo状态"""
        conversation = self.get_conversation(board_id, conversation_id, page=None, limit=None)
        if not conversation:
            info(f"[ConversationManager] 获取待办状态失败，未找到对话: board_id={board_id}, conversation_id={conversation_id}")
            return None
        status = conversation.get("todo_status")
        info(
            f"[ConversationManager] 读取待办状态: board_id={board_id}, conversation_id={conversation_id}, "
            f"has_todos={status.get('has_todos') if status else False}, "
            f"completed={status.get('completed_count') if status else 0}, "
            f"total={status.get('total') if status else 0}"
        )
        return {
            "state": conversation.get("todo_state"),
            "status": conversation.get("todo_status")
        }

    def save_todo_state(self, board_id: str, conversation_id: str, todo_state: Optional[Dict], todo_status: Optional[Dict]) -> bool:
        """保存对话的todo状态"""
        conversation = self.get_conversation(board_id, conversation_id, page=None, limit=None)
        if not conversation:
            return False

        conversation["todo_state"] = todo_state
        conversation["todo_status"] = todo_status
        conversation["updated_at"] = datetime.now().isoformat()

        conversations_dir = self.get_board_conversations_dir(board_id)
        conversation_file = conversations_dir / f"{conversation_id}.json"

        try:
            with open(conversation_file, "w", encoding="utf-8") as f:
                json.dump(conversation, f, ensure_ascii=False, indent=2)
            if todo_status:
                info(
                    f"[ConversationManager] 已保存待办状态: board_id={board_id}, conversation_id={conversation_id}, "
                    f"completed={todo_status.get('completed_count')}, total={todo_status.get('total')}, "
                    f"remaining={todo_status.get('remaining_count')}"
                )
            else:
                info(
                    f"[ConversationManager] 已保存待办状态（无活跃待办）: board_id={board_id}, conversation_id={conversation_id}"
                )
            return True
        except Exception as e:
            print(f"保存todo状态失败: {e}")
            return False
