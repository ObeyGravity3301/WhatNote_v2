from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import uuid
import asyncio
from logger import error, info
from .schemas import AgentProfile, AgentSchedule

router = APIRouter()

# This will be populated by __init__.py
chat_manager = None

@router.post("/send")
async def send_chat_message(request: Request):
    """Send a message to the chat room."""
    try:
        data = await request.json()
        content = data.get("content")
        sender_name = data.get("sender_name", "User")
        
        if not content:
            raise HTTPException(status_code=400, detail="Content is required")
        
        # For now, we assume a single 'user' identity
        user_id = "user_main" 
        room_id = data.get("room_id", "casual_lounge") # Default to new room
        
        msg = await chat_manager.post_message(room_id, user_id, sender_name, content)
        return {"status": "success", "message": msg}
    except Exception as e:
        error(f"Error sending chat message: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/stream")
async def stream_chat_messages(request: Request):
    """SSE stream for chat messages."""
    async def event_generator():
        # Subscribe to the manager
        queue = await chat_manager.subscribe()
        try:
            while True:
                # Check for client disconnect
                if await request.is_disconnected():
                    break
                    
                # Wait for next message
                msg = await queue.get()
                # 必须使用 json.dumps(default=str) 处理 timestamp 等字段
                yield f"data: {json.dumps(msg.dict(), default=str)}\n\n"
        except asyncio.CancelledError:
            pass
        except Exception as e:
            error(f"SSE Error: {e}")
        finally:
            chat_manager.unsubscribe(queue)
            
    return StreamingResponse(event_generator(), media_type="text/event-stream")

@router.get("/agents")
async def get_chat_agents(room_id: Optional[str] = None):
    """Get agents. If room_id provided, return agents in that room."""
    agents_data = []
    
    if room_id:
        room = chat_manager.get_room(room_id)
        if room:
            for agent_id in room.active_agents:
                agent = chat_manager.agents.get(agent_id)
                if agent:
                    data = agent.profile.dict()
                    data['is_online'] = agent.is_online()
                    agents_data.append(data)
    else:
        for agent in chat_manager.agents.values():
            data = agent.profile.dict()
            data['is_online'] = agent.is_online()
            agents_data.append(data)
            
    return {"agents": agents_data}

@router.post("/agents/generate")
async def generate_agent(request: Request):
    """Generate an agent profile using LLM (Dry Run)."""
    try:
        data = await request.json()
        description = data.get("description")
        if not description:
            raise HTTPException(status_code=400, detail="Description required")
            
        profile = await chat_manager.generate_agent_profile(description)
        return {"status": "success", "agent": profile.dict()}
    except Exception as e:
        error(f"Agent generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/agents")
async def create_agent(request: Request):
    """Create (save) an agent."""
    try:
        data = await request.json()
        # Validate minimal fields
        if 'name' not in data or 'personality' not in data:
            raise HTTPException(status_code=400, detail="Invalid agent data")
            
        # If ID not provided, generate one
        if 'id' not in data:
            data['id'] = f"{data['name'].lower()}_{str(uuid.uuid4())[:4]}"
            
        # Parse schedule
        if 'schedule' in data and isinstance(data['schedule'], dict):
            # Ensure active_hours is valid
            try:
                data['schedule'] = AgentSchedule(**data['schedule'])
            except:
                # Fallback
                data['schedule'] = AgentSchedule()
            
        profile = AgentProfile(**data)
        chat_manager.create_agent(profile) # This saves it
        return {"status": "success", "agent": profile.dict()}
    except Exception as e:
        error(f"Agent creation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rooms")
async def create_room(request: Request):
    """Create a new chat room."""
    try:
        data = await request.json()
        name = data.get("name")
        topic = data.get("topic")
        system_prompt = data.get("system_prompt", "")
        
        if not name:
            raise HTTPException(status_code=400, detail="Room name required")
            
        room_id = f"room_{str(uuid.uuid4())[:8]}"
        room = chat_manager.create_room(room_id, name, topic)
        room.system_prompt = system_prompt
        chat_manager.save_room(room_id)
        
        return {"status": "success", "room": room.dict(exclude={'history'})}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rooms")
async def list_rooms():
    """List all chat rooms."""
    return {"rooms": [
        {
            "id": r.id, 
            "name": r.name, 
            "topic": r.topic, 
            "system_prompt": r.system_prompt,
            "active_agents_count": len(r.active_agents)
        } 
        for r in chat_manager.rooms.values()
    ]}

@router.post("/rooms/{room_id}/join")
async def join_room(room_id: str, request: Request):
    """Add an agent to a room."""
    try:
        data = await request.json()
        agent_id = data.get("agent_id")
        if not agent_id:
            raise HTTPException(status_code=400, detail="Agent ID required")
            
        chat_manager.add_agent_to_room(agent_id, room_id)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rooms/{room_id}/invite") # Alias for join
async def invite_agent(room_id: str, request: Request):
    return await join_room(room_id, request)

@router.get("/history")
async def get_chat_history(room_id: str = "casual_lounge"):
    """Get recent chat history."""
    room = chat_manager.get_room(room_id)
    return {"history": room.history if room else []}

@router.post("/control")
async def control_chat(request: Request):
    """Start or stop the chat loop."""
    try:
        data = await request.json()
        action = data.get("action")
        
        if action == "start":
            await chat_manager.start_loop()
            return {"status": "success", "message": "CyberChat loop started"}
        elif action == "stop":
            await chat_manager.stop_loop()
            return {"status": "success", "message": "CyberChat loop stopped"}
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/debug/trigger")
async def debug_trigger_speech(request: Request):
    """Debug: Force a specific agent to speak in a room."""
    try:
        data = await request.json()
        agent_id = data.get("agent_id")
        room_id = data.get("room_id", "casual_lounge")
        
        agent = chat_manager.agents.get(agent_id)
        room = chat_manager.get_room(room_id)
        
        if not agent or not room:
            raise HTTPException(status_code=404, detail="Agent or Room not found")
            
        response = await agent.speak(room.dict())
        if response:
            await chat_manager.post_message(
                room_id=room_id,
                sender_id=agent.profile.id,
                sender_name=agent.profile.name,
                content=response
            )
            return {"status": "success", "response": response}
        else:
            return {"status": "failed", "reason": "No response"}
    except Exception as e:
        error(f"Debug trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

