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

    async def ensure_daily_routine(self):
        """
        If daily_routine is empty, generate it using the Agent's own persona.
        """
        if self.profile.schedule.daily_routine:
            return

        info(f"[Agent] Generating daily routine for {self.profile.name}...")
        
        # Get appropriate active hours for reference
        # We just use generic active_hours for the prompt context
        active_str = str(self.profile.schedule.active_hours)
        
        prompt = f"""
You are {self.profile.name}.
Your personality: {self.profile.personality}
Your typical active hours (Online in chat): {active_str}

Please create a DETAILED daily routine for yourself for a typical day (24 hours).
For EVERY hour from 0 to 23, describe what you are doing.

- If you are OFFLINE, describe your real-life activity (e.g., Sleeping, Commuting, Working at office, In class).
- If you are ONLINE, describe the context (e.g., Chilling on sofa, Procrastinating at work, Late night gaming).

Return ONLY a JSON object mapping hour (string "0" to "23") to the activity description (string).
Example:
{{
    "0": "Sleeping",
    "1": "Sleeping",
    ...
    "9": "Commuting to work, checking messages on phone",
    "10": "Working on spreadsheets (Secretly chatting)"
}}
JSON ONLY:
"""
        
        try:
            messages = [{"role": Role.SYSTEM, "content": prompt}]
            response_text = ""
            async for chunk in self.llm_service.chat_completion(messages, stream=False):
                response_text += chunk
                
            # Parse JSON
            import json
            import re
            
            clean_text = response_text.strip()
            if "```" in clean_text:
                match = re.search(r"```(?:json)?(.*?)```", clean_text, re.DOTALL)
                if match:
                    clean_text = match.group(1)
            
            routine = json.loads(clean_text)
            # Ensure keys are strings
            self.profile.schedule.daily_routine = {str(k): str(v) for k, v in routine.items()}
            info(f"[Agent] Generated routine for {self.profile.name}: {len(self.profile.schedule.daily_routine)} entries.")
            
        except Exception as e:
            error(f"[Agent] Failed to generate routine: {e}")


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

    def is_online(self) -> Dict[str, Any]:
        """
        Check if agent is online based on schedule.
        Returns: {'is_online': bool, 'status_code': str, 'activity': str}
        """
        if not self.profile.schedule:
            return {'is_online': True, 'status_code': 'ACTIVE', 'activity': 'Unknown'}
            
        import datetime
        import random
        
        # UTC time + offset (Default 8 for Beijing)
        offset = self.profile.schedule.timezone_offset
        now = datetime.datetime.utcnow() + datetime.timedelta(hours=offset)
        current_hour = now.hour
        weekday = now.weekday() # 0=Mon, 6=Sun
        is_weekend = weekday >= 5
        
        # Get Activity Description
        activity = self.profile.schedule.daily_routine.get(str(current_hour), "Unknown activity")

        # Determine base active hours
        active_hours = self.profile.schedule.active_hours
        if is_weekend and self.profile.schedule.weekends_active_hours:
            active_hours = self.profile.schedule.weekends_active_hours
        elif not is_weekend and self.profile.schedule.weekdays_active_hours:
            active_hours = self.profile.schedule.weekdays_active_hours
            
        is_active = current_hour in active_hours
        status_code = 'ACTIVE' if is_active else 'OFFLINE'
        
        # Apply randomness (Simulate Insomnia / Emergency)
        time_seed = f"{now.strftime('%Y-%m-%d-%H')}-{self.profile.name}"
        random.seed(time_seed)
        r_val = random.random()
        
        if not is_active:
            # Chance to wake up randomly (Insomnia)
            if r_val < self.profile.schedule.random_online_chance:
                is_active = True
                status_code = "INSOMNIA"
        else:
            # Chance to go offline randomly (Busy)
            if r_val < self.profile.schedule.random_offline_chance:
                is_active = False
                status_code = "BUSY"
                
        # Reset seed to avoid affecting other random calls
        random.seed()
        
        return {'is_online': is_active, 'status_code': status_code, 'activity': activity}

    async def should_speak(self, room_context: Dict) -> bool:
        """
        Decide if the agent wants to speak.
        """
        # Check online status first
        status = self.is_online()
        if not status['is_online']:
            info(f"[AgentCheck] {self.profile.name} is offline ({status['status_code']}).")
            return False

        # 1. If mentioned, high probability
        last_msg = self.memory[-1]
        if last_msg['role'] == Role.USER and self.profile.name.lower() in last_msg['content'].lower():
            info(f"[AgentCheck] {self.profile.name} was mentioned, speaking.")
            return True
            
        # 2. Random chance based on 'boredom' or 'interest'
        import random
        # Base chance INCREASED for testing
        chance = 0.3 
        
        # Increase chance if room topic matches interests (simple keyword match)
        topic = room_context.get('topic', '').lower()
        for interest in self.profile.interests:
            if interest.lower() in topic:
                chance += 0.2
                break
                
        r = random.random()
        # info(f"[AgentCheck] {self.profile.name} roll: {r:.2f} < {chance:.2f}?")
        if r < chance: 
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
            
            # Check current status for "Self Awareness"
            status = self.is_online()
            activity = status['activity']
            
            status_prompt = ""
            import datetime
            now_hour = (datetime.datetime.utcnow().hour + 8) % 24 # Mock time
            
            context_block = f"\n[Real-time Context]\nCurrent Time: {now_hour}:00\nYour Current Activity: {activity}\n"
            
            if status['status_code'] == 'INSOMNIA':
                context_block += "Status: INSOMNIA (You should be sleeping but are awake)\n"
            elif status['status_code'] == 'BUSY': 
                context_block += "Status: BUSY (You are distracted by real life work)\n"
            else:
                context_block += "Status: ACTIVE\n"
                
            context_block += "INSTRUCTION: Incorporate your current activity/status into your tone if relevant. If you are doing something distracting (e.g. gaming, driving), be brief."

            # Inject Room System Prompt if available to give context about WHAT group this is
            if room_context and room_context.get('system_prompt'):
                context_block += f"\n\n[Room Info]\nTopic: {room_context.get('topic')}\nRules: {room_context['system_prompt']}"
            
            # Insert after the agent's persona (index 0)
            if len(messages_to_send) > 0:
                messages_to_send.insert(1, {"role": Role.SYSTEM, "content": context_block})

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
