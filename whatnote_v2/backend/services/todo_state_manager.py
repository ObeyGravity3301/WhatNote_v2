import json
import threading
import time
from pathlib import Path
from typing import Dict, Optional

from logger import info, error
from tools.todo_tools import TodoTracker


class TodoStateManager:
    """
    负责在多个会话之间共享 TodoTracker。
    - 以 (board_id, conversation_id) 为 key 缓存在内存
    - 同步持久化到 DATA_DIR/todo_states 目录
    - 可选：回退到 ConversationManager 的历史持久化
    """

    def __init__(self, data_dir: Path, conversation_manager=None):
        self.data_dir = Path(data_dir)
        self.storage_dir = self.data_dir / "todo_states"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.conversation_manager = conversation_manager
        self._lock = threading.Lock()
        self._trackers: Dict[str, TodoTracker] = {}

    @staticmethod
    def _make_key(board_id: str, conversation_id: str) -> str:
        return f"{board_id}:{conversation_id}"

    def _state_file(self, board_id: str, conversation_id: str) -> Path:
        return self.storage_dir / f"{board_id}_{conversation_id}.json"

    def get_tracker(self, board_id: str, conversation_id: str) -> TodoTracker:
        """
        获取指定会话的 tracker，如果不存在则创建并尝试从磁盘或 conversation_manager 恢复。
        """
        if not board_id or not conversation_id:
            info("[TodoStateManager] 缺少 board_id 或 conversation_id，返回新的临时 tracker")
            return TodoTracker()

        key = self._make_key(board_id, conversation_id)
        with self._lock:
            if key in self._trackers:
                return self._trackers[key]

            tracker = TodoTracker()
            payload = self._load_state_from_disk(board_id, conversation_id)
            if payload and payload.get("state"):
                tracker.load_state(payload.get("state"))
                info(f"[TodoStateManager] 从磁盘恢复待办状态: {board_id}/{conversation_id}")
            elif self.conversation_manager:
                persisted = self.conversation_manager.get_todo_state(board_id, conversation_id)
                if persisted and persisted.get("state"):
                    tracker.load_state(persisted.get("state"))
                    info(f"[TodoStateManager] 从 ConversationManager 恢复待办状态: {board_id}/{conversation_id}")

            self._trackers[key] = tracker
            return tracker

    def get_status(self, board_id: str, conversation_id: str) -> Optional[Dict]:
        """获取当前状态（如果 tracker 不存在会自动加载）"""
        if not board_id or not conversation_id:
            return None
        tracker = self.get_tracker(board_id, conversation_id)
        if not tracker:
            return None
        return tracker.get_status()

    def save_tracker(self, board_id: str, conversation_id: str, tracker: TodoTracker, reason: str = "状态更新"):
        """将 tracker 状态持久化到磁盘，并可选更新 ConversationManager"""
        if not board_id or not conversation_id or tracker is None:
            return

        key = self._make_key(board_id, conversation_id)
        state = tracker.get_state()
        status = tracker.get_status()
        payload = {
            "board_id": board_id,
            "conversation_id": conversation_id,
            "state": state,
            "status": status,
            "updated_at": time.time(),
            "reason": reason
        }

        with self._lock:
            if state:
                try:
                    self.storage_dir.mkdir(parents=True, exist_ok=True)
                    with open(self._state_file(board_id, conversation_id), "w", encoding="utf-8") as f:
                        json.dump(payload, f, ensure_ascii=False, indent=2)
                    info(f"[TodoStateManager] 已保存状态: {board_id}/{conversation_id}, 原因: {reason}")
                except Exception as exc:
                    error(f"[TodoStateManager] 保存状态失败: {exc}")
            else:
                file_path = self._state_file(board_id, conversation_id)
                if file_path.exists():
                    file_path.unlink()
                    info(f"[TodoStateManager] 已删除空状态文件: {board_id}/{conversation_id}")
                if key in self._trackers:
                    del self._trackers[key]

        if self.conversation_manager:
            try:
                self.conversation_manager.save_todo_state(board_id, conversation_id, state, status)
            except Exception as exc:
                error(f"[TodoStateManager] 保存到 ConversationManager 失败: {exc}")

    def reset_tracker(self, board_id: str, conversation_id: str):
        """删除内存及磁盘中的 tracker"""
        if not board_id or not conversation_id:
            return

        key = self._make_key(board_id, conversation_id)
        with self._lock:
            self._trackers.pop(key, None)
        state_path = self._state_file(board_id, conversation_id)
        if state_path.exists():
            state_path.unlink()
            info(f"[TodoStateManager] 已删除会话待办文件: {state_path}")

        if self.conversation_manager:
            try:
                self.conversation_manager.save_todo_state(board_id, conversation_id, None, None)
            except Exception as exc:
                error(f"[TodoStateManager] 重置 ConversationManager 状态失败: {exc}")

    def _load_state_from_disk(self, board_id: str, conversation_id: str) -> Optional[Dict]:
        state_path = self._state_file(board_id, conversation_id)
        if not state_path.exists():
            return None
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as exc:
            error(f"[TodoStateManager] 读取状态文件失败: {state_path}, 错误: {exc}")
            return None

