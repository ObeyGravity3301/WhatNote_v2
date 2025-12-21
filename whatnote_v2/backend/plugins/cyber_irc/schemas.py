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
    active_hours: List[int] = Field(default_factory=lambda: list(range(9, 23)), description="List of active hours (0-23) used as fallback")
    
    # Advanced: Weekday vs Weekend
    weekdays_active_hours: Optional[List[int]] = Field(None, description="Active hours for Mon-Fri")
    weekends_active_hours: Optional[List[int]] = Field(None, description="Active hours for Sat-Sun")
    
    timezone_offset: int = Field(default=8, description="UTC offset (e.g. 8 for Beijing)")
    
    # Randomness
    random_online_chance: float = Field(default=0.0, description="Chance (0-1) to be online during offline hours (e.g. Insomnia)")
    random_offline_chance: float = Field(default=0.0, description="Chance (0-1) to be offline during active hours (e.g. Busy)")
    
    # Detailed 24h Routine
    daily_routine: Dict[str, str] = Field(default_factory=dict, description="Activity description for each hour (0-23) - Weekday")
    daily_routine_weekend: Optional[Dict[str, str]] = Field(default=None, description="Activity description for each hour (0-23) - Weekend")


class AgentProfile(BaseModel):
    id: str
    name: str
    avatar: Optional[str] = "default_avatar.png"
    gender: Optional[str] = Field(None, description="Gender identity (e.g. Male, Female, Non-binary, AI)")
    birthday: Optional[str] = Field(None, description="Birthday (MM-DD)")
    signature: Optional[str] = Field(None, description="Short bio or signature")
    language: Optional[str] = Field("Chinese", description="Primary language (e.g. Chinese, English)")
    personality: str = Field(..., description="The personality description of the agent")
    interests: List[str] = Field(default_factory=list, description="Topics the agent is interested in")
    style: str = Field(..., description="Speaking style, e.g., 'sarcastic', 'formal', 'slang-heavy'")
    system_prompt: Optional[str] = None # Calculated from personality and style
    schedule: Optional[AgentSchedule] = Field(default_factory=AgentSchedule) # Activity schedule
    subscribed_feeds: List[str] = Field(default_factory=list, description="List of RSS feed URLs this agent subscribes to")
    last_processed_msg_id: Optional[str] = None # Last message ID processed by the agent (for persistence)

class ChatMessage(BaseModel):
    id: str
    room_id: str
    sender_id: str
    sender_name: str
    content: str
    timestamp: float = Field(default_factory=time.time)
    type: str = "text" # text, image, system
    reply_to: Optional[str] = None # ID of the message being replied to
    payload: Optional[Dict[str, Any]] = None # For structured content (e.g. image url, file path)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class RoomState(BaseModel):
    id: str
    name: str
    topic: str
    type: str = "group" # group, dm
    system_prompt: str = "" # Room-specific context/rules
    is_paused: bool = False # If true, agents won't auto-speak
    active_agents: List[str]
    history: List[ChatMessage] = []
