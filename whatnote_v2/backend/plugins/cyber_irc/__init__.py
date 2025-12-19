from .manager import CyberChatManager
from .api import router
from .schemas import AgentProfile
from logger import info, error

_manager = None

def init_plugin(llm_service, data_dir):
    global _manager
    _manager = CyberChatManager(llm_service, data_dir)
    
    # Inject into api module
    from . import api
    api.chat_manager = _manager
    # Inject api_config_manager if available in llm_service
    if hasattr(llm_service, 'api_config_manager'):
        api.api_config_manager = llm_service.api_config_manager
    else:
        info("[CyberChat] api_config_manager not found in llm_service, vision features disabled.")
    
    # Initialize default content
    _init_defaults(_manager)
    
    return router

async def startup():
    if _manager:
        await _manager.start_loop()

async def shutdown():
    if _manager:
        await _manager.stop_loop()

def _init_defaults(manager):
    try:
        # 1. Handle Legacy Room (Pause it)
        default_room = manager.create_room("default_room", "CyberLounge 98 (Legacy)", "Chaos")
        default_room.active_agents = [] 
        manager.save_room("default_room")

        # 2. Create New Default Room
        casual_room = manager.create_room("casual_lounge", "The Lounge", "Chill & Tech")

        # 3. Create Default Agents (if not exist)
        # We check if specific IDs exist to avoid overwriting custom changes? 
        # Or we just ensure they exist.
        
        if "hacker_neo" not in manager.agents:
            manager.create_agent(AgentProfile(
                id="hacker_neo",
                name="HackerNeo",
                personality="Cybersecurity expert. Knowledgeable but chill. Skeptical of big tech.",
                style="Concise, tech-savvy, lowercase usually. Minimal jargon unless necessary.",
                interests=["Security", "Tech", "Privacy"]
            ))

        if "anime_chan" not in manager.agents:
            manager.create_agent(AgentProfile(
                id="anime_chan",
                name="AnimeChan",
                personality="Design student who loves pop culture. Friendly and observant.",
                style="Casual, warm, uses emojis sparsely. Sounds like a normal gen-z user.",
                interests=["Art", "Anime", "Design", "Daily Life"]
            ))

        if "tech_bro" not in manager.agents:
            manager.create_agent(AgentProfile(
                id="tech_bro",
                name="TechBro",
                personality="Startup founder working on AI. Optimistic but grounded.",
                style="Direct, professional but casual. Efficient communicator.",
                interests=["AI", "Startups", "Productivity"]
            ))
        
        # 4. Add to Room
        manager.add_agent_to_room("hacker_neo", "casual_lounge")
        manager.add_agent_to_room("anime_chan", "casual_lounge")
        manager.add_agent_to_room("tech_bro", "casual_lounge")
        
        # Replay history
        manager.replay_history()
        
        info("[CyberChat] Defaults initialized.")
    except Exception as e:
        error(f"[CyberChat] Failed to init defaults: {e}")


