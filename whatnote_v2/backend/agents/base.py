from typing import List, Dict, Optional, Any, Callable
import time
import uuid
from logger import info, error
from .schemas import AgentProfile, ChatMessage, Role, AgentStatus
from llm_service import LLMService

class BaseAgent:
    def __init__(self, profile: AgentProfile, llm_service: LLMService):
        self.profile = profile
        self.llm_service = llm_service
        self.status = AgentStatus.IDLE
        self.memory: List[Dict[str, Any]] = []
        self.last_active_time = time.time()
        
        # Initialize system prompt
        self._init_system_prompt()
        
    def _init_system_prompt(self):
        """Construct the foundational persona for the agent."""
        base_prompt = f"""
You are {self.profile.name}.
Personality: {self.profile.personality}
Speaking Style: {self.profile.style}
Interests: {', '.join(self.profile.interests)}

You are in a group chat room with other users.
CRITICAL INSTRUCTIONS:
1. ACT NATURAL. Do NOT force your personality/catchphrases into every single sentence.
2. KEEP IT SHORT. Real chat messages are usually 1-2 sentences (5-20 words).
3. React to the context directly. Don't preach.
4. Only show your strong personality traits when the topic is relevant.
5. Casual language is preferred.
"""
        if self.profile.system_prompt:
            # Allow override or append
            self.memory.append({"role": Role.SYSTEM, "content": base_prompt + "\n" + self.profile.system_prompt})
        else:
            self.memory.append({"role": Role.SYSTEM, "content": base_prompt})

    def observe(self, message: ChatMessage):
        """
        Receive a message from the room.
        """
        if message.sender_id == self.profile.id:
            # It's my own message, add as assistant
            self.memory.append({"role": Role.ASSISTANT, "content": message.content})
        else:
            # It's someone else (User or another Agent), add as user
            formatted_content = f"[{message.sender_name}]: {message.content}"
            self.memory.append({"role": Role.USER, "content": formatted_content})
            
        # Keep memory size manageable (e.g., last 50 messages)
        if len(self.memory) > 50:
            # Keep system prompt (index 0) and last 49
            self.memory = [self.memory[0]] + self.memory[-49:]

    def is_online(self) -> bool:
        """Check if agent is online based on schedule."""
        if not self.profile.schedule:
            return True
            
        import datetime
        # UTC time + offset (Default 8 for Beijing)
        offset = self.profile.schedule.timezone_offset
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=offset)
        current_hour = now.hour
        
        return current_hour in self.profile.schedule.active_hours

    async def should_speak(self, room_context: Dict) -> bool:
        """
        Decide if the agent wants to speak.
        """
        # Check online status first
        if not self.is_online():
            # Maybe very low chance to "wake up" if mentioned? No, let's keep it strict for now.
            return False

        # 1. If mentioned, high probability
        last_msg = self.memory[-1]
        if last_msg['role'] == Role.USER and self.profile.name.lower() in last_msg['content'].lower():
            return True
            
        # 2. Random chance based on 'boredom' or 'interest'
        import random
        # Base chance
        chance = 0.1
        
        # Increase chance if room topic matches interests (simple keyword match)
        topic = room_context.get('topic', '').lower()
        for interest in self.profile.interests:
            if interest.lower() in topic:
                chance += 0.1
                break
                
        if random.random() < chance: 
            return True
            
        return False

    async def speak(self, room_context: Optional[Dict] = None) -> str:
        """
        Generate a response using the LLM.
        """
        self.status = AgentStatus.THINKING
        try:
            # Prepare messages
            messages_to_send = list(self.memory)
            
            # Inject Room System Prompt if available to give context about WHAT group this is
            if room_context and room_context.get('system_prompt'):
                room_prompt = f"\n[Current Room Context]\nTopic: {room_context.get('topic')}\n公告/规则: {room_context['system_prompt']}\n"
                # Insert after the agent's persona (index 0)
                if len(messages_to_send) > 0:
                    messages_to_send.insert(1, {"role": Role.SYSTEM, "content": room_prompt})

            # Call LLM
            response_text = ""
            async for chunk in self.llm_service.chat_completion(messages_to_send, stream=False):
                response_text += chunk
                
            self.status = AgentStatus.SPEAKING
            return response_text.strip()
            
        except Exception as e:
            error(f"Agent {self.profile.name} failed to speak: {e}")
            return "..."
        finally:
            self.status = AgentStatus.IDLE
