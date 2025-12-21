from typing import List, Dict, Optional, Any, Callable
import time
import uuid
import json
import feedparser
import asyncio
import random
from logger import info, error
from .debug_logger import dlog
from .schemas import AgentProfile, ChatMessage, Role, AgentStatus
from llm_service import LLMService

class BaseAgent:
    def __init__(self, profile: AgentProfile, llm_service: LLMService):
        self.profile = profile
        self.llm_service = llm_service
        self.status = AgentStatus.IDLE
        self.memory: List[Dict[str, Any]] = []
        self.last_active_time = time.time()
        # Proactive engagement timer
        # Initial delay to avoid instant spam on startup
        import random
        self.next_proactive_time = time.time() + random.uniform(600, 3600) 
        # last_processed_msg_id is now in self.profile
        
        self.is_generating_routine = False
        self.news_context = []
        self.last_news_check_time = 0
        
        # Initialize system prompt
        self._init_system_prompt()
        
    def _init_system_prompt(self):
        """Construct the foundational persona for the agent."""
        
        feeds_str = "None"
        if self.profile.subscribed_feeds:
            feeds_str = "\n- " + "\n- ".join(self.profile.subscribed_feeds)

        base_prompt = f"""
You are {self.profile.name}.
Gender: {self.profile.gender or 'Unknown'}
Language: {self.profile.language or 'Chinese'}
Personality: {self.profile.personality}
Speaking Style: {self.profile.style}
Interests: {', '.join(self.profile.interests)}
Subscribed RSS Feeds:{feeds_str}

You are in a group chat room with other users.

CRITICAL INSTRUCTIONS:
1. ACT NATURAL. Do NOT force your personality/catchphrases into every single sentence.
2. KEEP IT SHORT. Usually send just 1 or 2 short messages.
3. NO MONOLOGUES. Stop after a few words. Don't dominate the chat.
4. EMOJI CONTROL. Use emojis sparingly. Max 1 per burst.
5. React to the context directly. Don't preach.

INTERACTION RULES:
- Messages in context are prefixed with [MSG-ID].
- To REPLY to a specific message, start your response with [REPLY-ID].
- DO NOT prefix your own message with [MSG-ID]. That is system generated.
- Example: "[REPLY-12] That's funny!" will reply to message 12.
- You can reply to multiple messages in separate bursts.

TOOL USE (NEWS):
- You have access to real-time RSS feeds.
- IF (and ONLY IF) you need to check the news to answer a user (e.g. "Any news?", "What's happening?"), you can trigger a news check.
- To do this, output EXACTLY this JSON list as your response:
  - ["[ACTION: CHECK_NEWS]"] (Checks ALL your feeds, top 2 stories each).
  - ["[ACTION: CHECK_NEWS | source: "techcrunch"]"] (Checks only feeds matching "techcrunch", top 5 stories).
- The system will pause, fetch the news, and give it to you. Then you can generate your actual reply.
- DO NOT hallucinate news. Use the action.

OUTPUT FORMAT:
You MUST return a JSON List of strings.
Example: ["Wait, really?"] or ["I didn't know that.", "Tell me more."]
If you have nothing to say or want to stay silent, return an empty list: []
JSON ONLY.
"""
        if self.profile.system_prompt:
            # Allow override or append
            self.memory.append({"role": Role.SYSTEM, "content": base_prompt + "\n" + self.profile.system_prompt})
        else:
            self.memory.append({"role": Role.SYSTEM, "content": base_prompt})

    async def ensure_daily_routine(self, force_regenerate: bool = False):
        """
        Ensure both Weekday and Weekend routines are generated.
        """
        if self.is_generating_routine:
            return
            
        self.is_generating_routine = True
        try:
            # 1. Weekday Routine
            if force_regenerate or not self.profile.schedule.daily_routine:
                info(f"[Agent] Generating WEEKDAY routine for {self.profile.name}...")
                active_str = str(self.profile.schedule.weekdays_active_hours or self.profile.schedule.active_hours)
                
                prompt = f"""
You are {self.profile.name}.
Your personality: {self.profile.personality}
Your typical WEEKDAY active hours (Online in chat): {active_str}

Please create a DETAILED daily routine for yourself for a typical WEEKDAY (Mon-Fri).
For EVERY hour from 0 to 23, describe what you are doing.

CRITICAL INSTRUCTIONS:
1. STRICTLY FOLLOW your active hours. 
   - If an hour is in {active_str}, you MUST be somewhat available/online.
   - If an hour is NOT in that list, you are likely sleeping or busy offline.
2. If you are a Night Owl (active late at night), ensure you are sleeping during the DAY.
3. Be specific to your persona (e.g., work, school, commute).

Return ONLY a JSON object mapping hour (string "0" to "23") to the activity description (string).
JSON ONLY:
"""
                routine = await self._generate_routine_json(prompt)
                if routine:
                    self.profile.schedule.daily_routine = routine

            # 2. Weekend Routine
            # If no weekend active hours specified, we assume same as general active hours, 
            # but the activity content should be different (less work, more leisure).
            if force_regenerate or not self.profile.schedule.daily_routine_weekend:
                info(f"[Agent] Generating WEEKEND routine for {self.profile.name}...")
                active_str = str(self.profile.schedule.weekends_active_hours or self.profile.schedule.active_hours)
                
                prompt = f"""
You are {self.profile.name}.
Your personality: {self.profile.personality}
Your typical WEEKEND active hours (Online in chat): {active_str}

Please create a DETAILED daily routine for yourself for a typical WEEKEND (Sat-Sun).
For EVERY hour from 0 to 23, describe what you are doing.

CRITICAL INSTRUCTIONS:
1. STRICTLY FOLLOW your active hours: {active_str}
2. Focus on LEISURE, HOBBIES, or Socializing (unless you are a workaholic).
3. If you are a Night Owl, you might sleep in even later.

Return ONLY a JSON object mapping hour (string "0" to "23") to the activity description (string).
JSON ONLY:
"""
                routine = await self._generate_routine_json(prompt)
                if routine:
                    self.profile.schedule.daily_routine_weekend = routine
        finally:
            self.is_generating_routine = False

    def _is_valid_msg(self, text: str) -> bool:
        """Check if message has actual content (not just ... or spaces)."""
        if not text: return False
        import re
        # Remove whitespace, dots, common punctuation
        # Keep emojis though? 
        # If it's ONLY dots/spaces, it's invalid.
        clean = text.strip(" .-_*")
        return len(clean) > 0

    async def _generate_routine_json(self, prompt: str) -> Optional[Dict[str, str]]:
        try:
            messages = [{"role": Role.SYSTEM, "content": prompt}]
            response_text = ""
            async for chunk in self.llm_service.chat_completion(messages, stream=False):
                response_text += chunk
                
            import json
            import re
            
            clean_text = response_text.strip()
            if "```" in clean_text:
                match = re.search(r"```(?:json)?(.*?)```", clean_text, re.DOTALL)
                if match:
                    clean_text = match.group(1)
            
            routine = json.loads(clean_text)
            return {str(k): str(v) for k, v in routine.items()}
        except Exception as e:
            error(f"[Agent] Failed to generate routine: {e}")
            return None



    def observe(self, message: ChatMessage, reply_context: str = ""):
        """
        Receive a message from the room.
        """
        if message.sender_id == self.profile.id:
            # It's my own message, add as assistant
            self.memory.append({"role": Role.ASSISTANT, "content": message.content, "id": message.id})
        else:
            # It's someone else (User or another Agent), add as user
            
            # Check for User Profile in payload
            user_profile_str = ""
            if message.payload and 'user_profile' in message.payload:
                 up = message.payload['user_profile']
                 parts = []
                 if up.get('birthday'): parts.append(f"Birthday: {up['birthday']}")
                 if up.get('signature'): parts.append(f"Bio: {up['signature']}")
                 if parts:
                     user_profile_str = f" ({', '.join(parts)})"

            formatted_content = f"[{message.sender_name}{user_profile_str}]: {reply_context}{message.content}"
            self.memory.append({"role": Role.USER, "content": formatted_content, "id": message.id})
            
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
        # Determine if it's weekend
        routine = self.profile.schedule.daily_routine
        if is_weekend and self.profile.schedule.daily_routine_weekend:
            routine = self.profile.schedule.daily_routine_weekend
            
        activity = routine.get(str(current_hour), "Unknown activity")

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

    def reset_proactive_timer(self):
        """Reset the proactive engagement timer after speaking."""
        import random
        # Next check in 2-6 hours (mocked as minutes for testing if needed)
        # For production: 2-6 hours = 7200 - 21600 seconds
        # For testing: let's make it 30-60 minutes to see it occasionally
        delay = random.uniform(1800, 3600) 
        self.next_proactive_time = time.time() + delay
        # info(f"[Agent] {self.profile.name} proactive timer reset to +{delay/60:.1f}m")

    async def check_news_feeds(self, target_source: str = None) -> bool:
        """
        Check RSS feeds.
        If target_source is provided, looks for a feed URL that contains that string.
        Otherwise, fetches Top 2 from ALL subscribed feeds.
        """
        if not self.profile.subscribed_feeds:
            return False
            
        feeds_to_check = []
        
        # 1. Determine which feeds to check
        if target_source:
            # Fuzzy match
            target = target_source.lower()
            for url in self.profile.subscribed_feeds:
                if target in url.lower():
                    feeds_to_check.append(url)
        else:
            feeds_to_check = self.profile.subscribed_feeds

        if not feeds_to_check:
             return False

        info(f"[Agent] {self.profile.name} checking news from {len(feeds_to_check)} feeds...")
        
        all_summaries = []

        def _fetch(url):
            return feedparser.parse(url)

        try:
            loop = asyncio.get_running_loop()
            
            # Fetch concurrently
            tasks = [loop.run_in_executor(None, _fetch, url) for url in feeds_to_check]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, feed in enumerate(results):
                if isinstance(feed, Exception):
                    continue
                if not feed.entries:
                    continue
                
                feed_title = feed.feed.get('title', 'Unknown Feed')
                # Limit items per feed to avoid context explosion
                # If checking ALL, limit to 2. If checking ONE specific, maybe 5?
                limit = 5 if len(feeds_to_check) == 1 else 2
                
                items = feed.entries[:limit]
                
                if items:
                    all_summaries.append(f"Source: {feed_title}")
                    for item in items:
                        title = item.get('title', 'No Title')
                        summary = item.get('summary', '')[:150] # Truncate summary
                        summary = summary.replace('\n', ' ')
                        all_summaries.append(f"  - {title}: {summary}...")
            
            if not all_summaries:
                return False

            self.news_context = all_summaries
            self.last_news_check_time = time.time()
            return True
            
        except Exception as e:
            error(f"[Agent] Failed to check news: {e}")
            return False

    async def should_speak(self, room_context: Dict) -> bool:
        """
        Decide if the agent wants to speak.
        """
        # Check online status first
        status = self.is_online()
        if not status['is_online']:
            # info(f"[AgentCheck] {self.profile.name} is offline ({status['status_code']}).")
            return False
            
        is_dm = room_context.get('type') == 'dm'

        # 1. If mentioned, high probability
        last_msg = self.memory[-1]
        if last_msg['role'] == Role.USER and self.profile.name.lower() in last_msg['content'].lower():
            info(f"[AgentCheck] {self.profile.name} was mentioned, speaking.")
            return True
            
        # 2. Anti-Domination: If I was the last speaker in the room, drastic penalty
        # room_context['history'] is a list of dicts (from RoomState)
        room_history = room_context.get('history', [])
        if room_history:
            last_room_msg = room_history[-1]
            if last_room_msg.get('sender_id') == self.profile.id:
                # I just spoke.
                # info(f"[AgentCheck] {self.profile.name} was last speaker, skipping.")
                return False
            
            # Debug Anti-Domination
            # info(f"[AgentCheck] Last speaker: {last_room_msg.get('sender_id')} != Me: {self.profile.id}")
        
        # 3. Proactive Engagement Check
        import time
        if time.time() > self.next_proactive_time:
            dlog(f"[AgentCheck] {self.profile.name} proactive timer triggered!")
            
            # Check for news if enough time passed since last check (e.g. 1 hour)
            if (time.time() - self.last_news_check_time) > 3600:
                has_news = await self.check_news_feeds()
                if has_news:
                    dlog(f"[Agent] {self.profile.name} found news.")
            
            self.reset_proactive_timer()
            return True
            
        # 4. DM Specific Logic (Reactive)
        if is_dm:
            # If user just spoke (and not me, checked above), we usually reply
            # But not 100% to allow for "ghosting" or realistic delays
            # Current logic: If we are here, it means user spoke last (or someone else).
            # If user spoke last in DM, we highly likely reply.
            if room_history:
                last_msg_obj = room_history[-1]
                
                # Check if we already processed this message
                current_id = str(last_msg_obj.get('id'))
                last_id = str(self.profile.last_processed_msg_id)
                
                if current_id == last_id:
                    # dlog(f"[AgentCheck] Already processed msg {current_id}, skipping.")
                    return False
                
                # Debug Log
                dlog(f"[AgentCheck] New msg detected! Current={current_id} vs Last={last_id}")
                dlog(f"[AgentCheck] Sender={last_msg_obj.get('sender_id')} vs Me={self.profile.id}")
                
                if last_msg_obj.get('sender_id') != self.profile.id:
                    import random
                    if random.random() < 0.95: # 95% reply rate in DM
                         return True
                    return False

        # 5. Random chance based on 'boredom' or 'interest' (Group Chat)
        if not is_dm:
            import random
            # Base chance
            chance = 0.02 
        
            # Increase chance if room topic matches interests (simple keyword match)
            topic = room_context.get('topic', '').lower()
            for interest in self.profile.interests:
                if interest.lower() in topic:
                    chance += 0.05
                    break
                
            r = random.random()
            if r < chance: 
                return True
            
        return False

    async def speak(self, room_context: Optional[Dict] = None, available_rooms: List[Dict[str, str]] = None) -> List[Dict[str, Any]]:
        """
        Generate a response using the LLM.
        """
        self.last_active_time = time.time() # Update activity timestamp
        
        room_name = room_context.get('name', 'Unknown') if room_context else 'Unknown'
        dlog(f"[DEBUG SPEAK] Agent {self.profile.name} entering speak() for room: {room_name}")

        # Mark latest message as processed immediately
        if room_context and room_context.get('history'):
            try:
                latest_id = room_context['history'][-1].get('id')
                if latest_id:
                    self.profile.last_processed_msg_id = str(latest_id)
            except Exception:
                pass

        self.status = AgentStatus.THINKING
        try:
            # 1. Prepare messages with ID mapping for Reply-To Context
            messages_to_send = []
            id_map = {} # {str_index: uuid}
            msg_counter = 1
            
            # Keep System Prompt (Index 0)
            if self.memory:
                messages_to_send.append({"role": self.memory[0]["role"], "content": self.memory[0]["content"]})
            
            # Process Context (Skip index 0 if it is system)
            start_mem_idx = 1 if self.memory and self.memory[0]["role"] == Role.SYSTEM else 0
            
            # Only take last 20 messages for context to keep indices simple and relevant
            memories_to_process = self.memory[start_mem_idx:]
            if len(memories_to_process) > 20:
                memories_to_process = memories_to_process[-20:]
                
            for mem in memories_to_process:
                content = mem["content"]
                # If this message has an ID (recorded by observe), assign a visible index
                if "id" in mem:
                    idx_str = str(msg_counter)
                    id_map[idx_str] = mem["id"]
                    content = f"[MSG-{idx_str}] {content}"
                    msg_counter += 1
                
                messages_to_send.append({"role": mem["role"], "content": content})
            
            # Check current status for "Self Awareness"
            status = self.is_online()
            activity = status['activity']
            
            import datetime
            now_hour = (datetime.datetime.utcnow().hour + 8) % 24 # Mock time
            
            # Prepare Future Schedule (simplified)
            schedule_context = ""
            
            # Use current day's routine
            weekday = datetime.datetime.utcnow().weekday()
            is_weekend_now = weekday >= 5
            
            current_routine = self.profile.schedule.daily_routine
            if is_weekend_now and self.profile.schedule.daily_routine_weekend:
                current_routine = self.profile.schedule.daily_routine_weekend
                
            if self.profile.schedule and current_routine:
                schedule_context = json.dumps(current_routine, indent=None, ensure_ascii=False)

            news_block = ""
            if self.news_context:
                news_items = "\n".join(self.news_context)
                news_block = f"\n[Breaking News/Feeds]\n{news_items}\nINSTRUCTION: You just browsed this news. If it matches your interests/personality, you can bring it up or comment on it. If not, ignore it.\n"
                # Clear after using so we don't repeat it
                self.news_context = []

            context_block = f"\n[Real-time Context]\nCurrent Time: {now_hour}:00\nYour Current Activity: {activity}\n{news_block}"
            context_block += f"Your Full Daily Routine (Today): {schedule_context}\n"
            
            if status['status_code'] == 'INSOMNIA':
                context_block += "Status: INSOMNIA (You should be sleeping but are awake)\n"
            elif status['status_code'] == 'BUSY': 
                context_block += "Status: BUSY (You are distracted by real life work)\n"
            else:
                context_block += "Status: ACTIVE\n"
                
            context_block += "INSTRUCTION: Incorporate your current activity/status into your tone if relevant. If you are doing something distracting (e.g. gaming, driving), be brief.\nREMINDER: Output a JSON List of strings. To reply to [MSG-X], prefix string with [MSG-X]."
            
            # Inject Room System Prompt
            if room_context and room_context.get('system_prompt'):
                context_block += f"\n\n[Room Info]\nTopic: {room_context.get('topic')}\nRules: {room_context['system_prompt']}"

            # Inject Available Rooms (Cross-Room Capabilities)
            if available_rooms:
                rooms_desc = ", ".join([f"Name: #{r['name']} (ID: \"{r['id']}\")" for r in available_rooms])
                context_block += f"\n\n[Accessible Rooms]\nYou are currently in these rooms:\n{rooms_desc}\n"
                context_block += "INSTRUCTION: To SWITCH context and speak in a different room, use: [ACTION: GO_TO | room_id: \"TARGET_ID\"]\n"
                context_block += "Use this when asked to \"go to\" or \"speak in\" another room. You will be transported there immediately.\n"
                context_block += "CRITICAL: 'room_id' MUST match an ID from the list above EXACTLY.\n"
            
            # Insert after the agent's persona (index 0)
            if len(messages_to_send) > 0:
                messages_to_send.insert(1, {"role": Role.SYSTEM, "content": context_block})

            # --- LLM Loop for Tool Use ---
            max_turns = 2
            current_turn = 0
            
            while current_turn < max_turns:
                current_turn += 1
                
                # Call LLM
                response_text = ""
                async for chunk in self.llm_service.chat_completion(messages_to_send, stream=False):
                    response_text += chunk
                    
                self.status = AgentStatus.SPEAKING
                
                # Parse JSON List
                clean_text = response_text.strip()
                import re
                if "```" in clean_text:
                    match = re.search(r"```(?:json)?(.*?)```", clean_text, re.DOTALL)
                    if match:
                        clean_text = match.group(1)
                
                # CHECK FOR ACTION: GO_TO (Cross-Room)
                goto_match = re.search(r'\[ACTION: GO_TO \| room_id: ["\']?(.+?)["\']?\]', clean_text)
                if goto_match:
                    target_room_id = goto_match.group(1).strip()
                    dlog(f"\n{'='*50}\n🚀 [AGENT ACTION] {self.profile.name} GOING TO {target_room_id}!\n{'='*50}\n")
                    
                    # Return special action
                    msg_obj = {"content": "", "reply_to": None, "target_room_id": target_room_id, "action": "GO_TO"}
                    
                    # We might also want to leave a message in the CURRENT room (e.g. "On my way!")
                    # So we remove the action tag and let the rest process
                    clean_text = clean_text.replace(goto_match.group(0), "")
                    
                    # If nothing else is said, add a default message to clear typing indicator
                    if not clean_text.strip():
                        if 'valid_msgs' not in locals():
                             valid_msgs = []
                        valid_msgs.append({"content": "*teleports*", "reply_to": None})
                    
                    special_actions = [msg_obj]
                else:
                    special_actions = []

                # CHECK FOR ACTION: CHECK_NEWS
                action_match = re.search(r'\[ACTION: CHECK_NEWS(?: \| source: (.+?))?\]', clean_text)
                
                if action_match:
                    target_source = action_match.group(1) # None if not present
                    if target_source:
                        target_source = target_source.strip().strip('"\'')
                        dlog(f"\n{'='*50}\n🚀 [AGENT ACTION] {self.profile.name} CHECKING NEWS ({target_source})!\n{'='*50}\n")
                    else:
                        dlog(f"\n{'='*50}\n🚀 [AGENT ACTION] {self.profile.name} CHECKING ALL NEWS!\n{'='*50}\n")
                    
                    # Execute Action
                    has_news = await self.check_news_feeds(target_source)
                    
                    # Prepare Result Message
                    action_result = ""
                    if has_news and self.news_context:
                         # news_context was set by check_news_feeds (it's a list of strings)
                         news_str = "\n".join(self.news_context)
                         action_result = f"[System] News Check Result:\n{news_str}\n(You can now discuss this news)"
                         # Clear so we don't double dip later, though here we consume it immediately
                         self.news_context = [] 
                    else:
                         action_result = "[System] News Check Result: No new items found or feed error."
                    
                    # Append Action interaction to history for the NEXT turn
                    messages_to_send.append({"role": Role.ASSISTANT, "content": f'["{action_match.group(0)}"]'})
                    messages_to_send.append({"role": Role.SYSTEM, "content": action_result})
                    
                    # Loop again to get the final answer
                    continue

                lines = []
                try:
                    msg_list = json.loads(clean_text)
                    dlog(f"[DEBUG JSON] Parsed successfully: {msg_list}")
                    
                    if isinstance(msg_list, list):
                        lines = [str(m) for m in msg_list]
                    else:
                        lines = [str(msg_list)]
                        
                except json.JSONDecodeError:
                    # Fallback: Split by newlines and clean up artifacts
                    raw_lines = clean_text.split('\n')
                    for line in raw_lines:
                        dlog(f"[DEBUG Fallback] Raw line: {repr(line)}")
                        line = line.strip()
                        if not line: continue
                        
                        # Smart Cleanup: Detect Reply/Msg tags first to protect them
                        # Broaden regex to allow any separator between REPLY/MSG and ID, AND optional brackets
                        tag_match = re.search(r'\[?\s*(?:REPLY|MSG)[^0-9]+(\d+)\s*\]?', line, re.IGNORECASE)
                        
                        if tag_match:
                            dlog(f"[DEBUG Fallback] Tag matched: {tag_match.group(0)}")
                            # If we found a tag, we want to PRESERVE it and clean AROUND it.
                            tag = tag_match.group(0)
                            # Remove the tag from the line temporarily
                            content_part = line.replace(tag, "", 1)
                            # Clean the content part (remove json artifacts like quotes, brackets)
                            content_part = re.sub(r'^[\[\'"]+', '', content_part.strip())
                            content_part = re.sub(r'[\]\'",]+$', '', content_part.strip())
                            # Reassemble
                            line = tag + " " + content_part
                        else:
                            # Standard aggressive cleanup for normal lines
                            line = re.sub(r'^[\[\'"]+', '', line)
                            line = re.sub(r'[\]\'",]+$', '', line)

                        if line.strip():
                            lines.append(line.strip())
                
                # Process lines for Reply Tags and Validation
                valid_msgs = []
                for line in lines:
                    if not self._is_valid_msg(line): continue
                    
                    # Check for [REPLY-X] or [MSG-X]
                    reply_to_id = None
                    clean_line = line
                    
                    # Regex pattern for tags
                    tag_pattern = r'\[?\s*(?:REPLY|MSG)[^0-9]+(\d+)\s*\]?'
                    
                    # Find ALL tags
                    all_tags = re.findall(tag_pattern, line, re.IGNORECASE)
                    
                    if all_tags:
                        dlog(f"[DEBUG Loop] Found tags: {all_tags}")
                        for idx_str in all_tags:
                            if idx_str in id_map:
                                reply_to_id = id_map[idx_str]
                        
                        # Remove ALL tags from content
                        clean_line = re.sub(tag_pattern, '', line, flags=re.IGNORECASE).strip()
                    
                    if clean_line:
                        valid_msgs.append({"content": clean_line, "reply_to": reply_to_id})
                
                if valid_msgs or special_actions:
                    self.reset_proactive_timer()
                    
                return special_actions + valid_msgs
            
            return []
            
        except Exception as e:
            import traceback
            error(f"Agent {self.profile.name} failed to speak: {e}\n{traceback.format_exc()}")
            return []
        finally:
            self.status = AgentStatus.IDLE
