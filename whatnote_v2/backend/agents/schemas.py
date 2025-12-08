from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from enum import Enum
import time

class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"

class AgentStatus(str, Enum):
    IDLE = "idle"
    THINKING = "thinking"
    SPEAKING = "speaking"
    OFFLINE = "offline"

class AgentSchedule(BaseModel):
    """Defines when an agent is active/online."""
    # Simple hour-based schedule (0-23)
    active_hours: List[int] = Field(default_factory=lambda: list(range(9, 23)), description="List of active hours (0-23)")
    timezone_offset: int = Field(default=8, description="UTC offset (e.g. 8 for Beijing)")

class AgentProfile(BaseModel):
    id: str
    name: str
    avatar: Optional[str] = "default_avatar.png"
    personality: str = Field(..., description="The personality description of the agent")
    interests: List[str] = Field(default_factory=list, description="Topics the agent is interested in")
    style: str = Field(..., description="Speaking style, e.g., 'sarcastic', 'formal', 'slang-heavy'")
    system_prompt: Optional[str] = None # Calculated from personality and style
    schedule: Optional[AgentSchedule] = Field(default_factory=AgentSchedule) # Activity schedule

class ChatMessage(BaseModel):
    id: str
    room_id: str
    sender_id: str
    sender_name: str
    content: str
    timestamp: float = Field(default_factory=time.time)
    type: str = "text" # text, image, system
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RoomState(BaseModel):
    id: str
    name: str
    topic: str
    system_prompt: str = "" # Room-specific context/rules
    active_agents: List[str]
    history: List[ChatMessage] = []
