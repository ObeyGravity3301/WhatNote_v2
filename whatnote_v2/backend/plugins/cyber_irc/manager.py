import asyncio
import uuid
import time
import random
import json
import os
from pathlib import Path
from typing import List, Dict, Optional, Callable
from .schemas import AgentProfile, ChatMessage, RoomState, Role
from .base import BaseAgent
from llm_service import LLMService
from logger import info, error

class CyberChatManager:
    def __init__(self, llm_service: LLMService, data_dir: Path):
        self.llm_service = llm_service
        self.data_dir = data_dir / "cyber_chat"
        self.rooms_dir = self.data_dir / "rooms"
        self.users_dir = self.data_dir / "users"
        
        # Create directories
        self.rooms_dir.mkdir(parents=True, exist_ok=True)
        self.users_dir.mkdir(parents=True, exist_ok=True)
        
        info(f"[CyberChat] Init. Data dir: {self.data_dir.absolute()}")

        self.rooms: Dict[str, RoomState] = {}
        self.agents: Dict[str, BaseAgent] = {}
        self.subscribers: List[asyncio.Queue] = []
        self.is_running = False
        
        # Attempt to load state
        self.load_agents()
        self.load_state()
        
    def load_agents(self):
        """Load persisted agents."""
        try:
            if self.users_dir.exists():
                for agent_file in self.users_dir.glob("*.json"):
                    try:
                        with open(agent_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            # Check for minimal required fields
                            if 'id' not in data or 'name' not in data: continue
                            
                            # Handle schedule if present
                            from .schemas import AgentSchedule
                            if 'schedule' in data and data['schedule']:
                                data['schedule'] = AgentSchedule(**data['schedule'])
                            
                            profile = AgentProfile(**data)
                            self.create_agent(profile, save=False) # Already saved
                    except Exception as e:
                        error(f"[CyberChat] Failed to load agent {agent_file}: {e}")
        except Exception as e:
            error(f"[CyberChat] Failed to load agents: {e}")

    def save_agent(self, agent: BaseAgent):
        """Save agent profile to disk."""
        try:
            file_path = self.users_dir / f"{agent.profile.id}.json"
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(agent.profile.dict(), f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            error(f"[CyberChat] Failed to save agent {agent.profile.id}: {e}")

    def load_state(self):
        """Load all rooms."""
        try:
            # Scan directory for json files
            if self.rooms_dir.exists():
                for room_file in self.rooms_dir.glob("*.json"):
                    try:
                        with open(room_file, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            # Create RoomState
                            room_id = data.get('id')
                            if not room_id: continue
                            
                            room = RoomState(
                                id=room_id,
                                name=data.get('name', 'Unknown Room'),
                                topic=data.get('topic', ''),
                                active_agents=data.get('active_agents', [])
                            )
                            
                            # Restore History
                            if 'history' in data:
                                room.history = [ChatMessage(**msg) for msg in data['history']]
                            
                            self.rooms[room_id] = room
                            info(f"[CyberChat] Loaded room: {room_id} ({len(room.history)} msgs)")
                    except Exception as e:
                        error(f"[CyberChat] Failed to load room {room_file}: {e}")
        except Exception as e:
            error(f"[CyberChat] Failed to load state: {e}")

    def save_room(self, room_id: str):
        """Save specific room."""
        room = self.rooms.get(room_id)
        if not room: return
        try:
            file_path = self.rooms_dir / f"{room_id}.json"
            # Manually construct dict to avoid serialization issues
            data = {
                "id": room.id,
                "name": room.name,
                "topic": room.topic,
                "active_agents": room.active_agents,
                "history": [msg.dict() for msg in room.history]
            }
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        except Exception as e:
            error(f"[CyberChat] Failed to save room {room_id}: {e}")

    def create_room(self, id: str, name: str, topic: str) -> RoomState:
        if id in self.rooms:
            return self.rooms[id]
        
        room = RoomState(
            id=id,
            name=name,
            topic=topic,
            active_agents=[]
        )
        self.rooms[id] = room
        self.save_room(id)
        info(f"[CyberChat] Created room: {id}")
        return room
    
    def get_room(self, room_id: str) -> Optional[RoomState]:
        return self.rooms.get(room_id)

    def replay_history(self):
        """Replay loaded history to agents so they have context."""
        for room_id, room in self.rooms.items():
            if not room.history: continue
            
            info(f"[CyberChat] Replaying {len(room.history)} messages for room {room_id}...")
            # Only replay to agents IN this room
            for msg in room.history:
                for agent_id in room.active_agents:
                    agent = self.agents.get(agent_id)
                    if agent:
                        agent.observe(msg)
        
    async def subscribe(self) -> asyncio.Queue:
        """Subscribe to chat events."""
        q = asyncio.Queue()
        self.subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self.subscribers:
            self.subscribers.remove(q)

    def create_agent(self, profile: AgentProfile, save: bool = True) -> BaseAgent:
        agent = BaseAgent(profile, self.llm_service)
        self.agents[agent.profile.id] = agent
        info(f"[CyberChat] Agent created: {profile.name}")
        if save:
            self.save_agent(agent)
        return agent

    async def generate_agent_profile(self, description: str) -> AgentProfile:
        """Use LLM to generate a full agent profile from a short description."""
        prompt = f"""
        Create a detailed persona for a chatroom agent based on this description: "{description}".
        
        Return ONLY a JSON object with the following fields:
        - name: A creative username (no spaces preferred).
        - personality: A concise description of their personality.
        - interests: A list of 3-5 topics they are interested in.
        - style: A description of their speaking style (e.g., slang, formal, emoji usage).
        - system_prompt: Additional instructions for the LLM to act as this character.
        - active_hours: A list of integers (0-23) used as default fallback.
        - weekdays_active_hours: A list of integers (0-23) for Mon-Fri schedule.
        - weekends_active_hours: A list of integers (0-23) for Sat-Sun schedule.
        - random_online_chance: Float 0.0-1.0 (prob to be online when offline, e.g. insomnia).
        - random_offline_chance: Float 0.0-1.0 (prob to be offline when online, e.g. busy).
        
        JSON:
        """
        
        messages = [{"role": "user", "content": prompt}]
        
        response_text = ""
        async for chunk in self.llm_service.chat_completion(messages, stream=False):
            response_text += chunk
            
        try:
            # Clean up markdown code blocks
            clean_text = response_text.strip()
            if "```" in clean_text:
                import re
                match = re.search(r"```(?:json)?(.*?)```", clean_text, re.DOTALL)
                if match:
                    clean_text = match.group(1)
            
            data = json.loads(clean_text)
            
            from .schemas import AgentSchedule
            
            # Smart schedule parsing
            schedule_data = {
                "active_hours": data.get('active_hours', list(range(9, 23))),
                "timezone_offset": data.get('timezone_offset', 8)
            }
            if 'weekdays_active_hours' in data:
                schedule_data['weekdays_active_hours'] = data['weekdays_active_hours']
            if 'weekends_active_hours' in data:
                schedule_data['weekends_active_hours'] = data['weekends_active_hours']
            if 'random_online_chance' in data:
                schedule_data['random_online_chance'] = data['random_online_chance']
            if 'random_offline_chance' in data:
                schedule_data['random_offline_chance'] = data['random_offline_chance']
                
            schedule = AgentSchedule(**schedule_data)
            
            # Generate ID from name + random
            import uuid
            agent_id = f"{data.get('name', 'user').lower()}_{str(uuid.uuid4())[:4]}"
            
            profile = AgentProfile(
                id=agent_id,
                name=data.get('name', 'NewUser'),
                personality=data.get('personality', 'A generic user.'),
                interests=data.get('interests', []),
                style=data.get('style', 'Normal conversation.'),
                system_prompt=data.get('system_prompt', ''),
                schedule=schedule
            )
            return profile
        except Exception as e:
            error(f"[CyberChat] Failed to parse generated agent: {e} | Raw: {response_text}")
            raise ValueError("Failed to generate agent profile") from e

    def add_agent_to_room(self, agent_id: str, room_id: str):
        if agent_id not in self.agents or room_id not in self.rooms:
            return
        
        room = self.rooms[room_id]
        if agent_id not in room.active_agents:
            room.active_agents.append(agent_id)
            self.save_room(room_id)
            info(f"[CyberChat] Added {agent_id} to {room_id}")

    def remove_agent_from_room(self, agent_id: str, room_id: str):
        if room_id in self.rooms:
            room = self.rooms[room_id]
            if agent_id in room.active_agents:
                room.active_agents.remove(agent_id)
                self.save_room(room_id)
                info(f"[CyberChat] Removed {agent_id} from {room_id}")

    async def post_message(self, room_id: str, sender_id: str, sender_name: str, content: str, msg_type: str = "text"):
        """
        Post a message to a specific room.
        """
        room = self.rooms.get(room_id)
        if not room:
            error(f"[CyberChat] Post failed: Room {room_id} not found")
            return None

        msg = ChatMessage(
            id=str(uuid.uuid4()),
            room_id=room_id,
            sender_id=sender_id,
            sender_name=sender_name,
            content=content,
            type=msg_type
        )
        
        # 1. Add to History
        room.history.append(msg)
        if len(room.history) > 100:
            room.history.pop(0)

        self.save_room(room_id)

        # 2. Broadcast to Agents in this room
        for agent_id in room.active_agents:
            agent = self.agents.get(agent_id)
            if agent:
                agent.observe(msg)

        # 3. Notify Frontend
        for q in self.subscribers:
            try:
                q.put_nowait(msg)
            except asyncio.QueueFull:
                pass
            
        return msg

    async def start_loop(self):
        if self.is_running:
            return
        self.is_running = True
        asyncio.create_task(self._loop())
        info("[CyberChat] Autonomous loop started.")

    async def stop_loop(self):
        self.is_running = False
        info("[CyberChat] Autonomous loop stopped.")

    async def _loop(self):
        """
        The Heartbeat.
        Iterate over all rooms.
        """
        info("[CyberChat] Heartbeat loop running...")
        while self.is_running:
            try:
                await asyncio.sleep(random.uniform(3, 8))
                # info(f"[CyberChat] Tick. Active rooms: {len(self.rooms)}") 
                
                # Check each room independently
                for room_id, room in self.rooms.items():
                    if not room.active_agents:
                        # info(f"[CyberChat] Room {room_id} has no active agents.")
                        continue
                        
                    # Shuffle agents
                    agent_ids = list(room.active_agents)
                    random.shuffle(agent_ids)
                    
                    for agent_id in agent_ids:
                        agent = self.agents.get(agent_id)
                        if not agent: continue
                        
                        # Check if agent wants to speak in this room context
                        should_speak = await agent.should_speak(room.dict())
                        
                        if should_speak:
                            info(f"[CyberChat][{room_id}] {agent.profile.name} decided to speak.")
                            response = await agent.speak(room.dict()) # Pass room context
                            if response:
                                await self.post_message(
                                    room_id=room_id,
                                    sender_id=agent.profile.id,
                                    sender_name=agent.profile.name,
                                    content=response
                                )
                                await asyncio.sleep(2) 
                                break # One person per room per tick
                
            except Exception as e:
                error(f"[CyberChat] Loop error: {e}")
                await asyncio.sleep(5)
