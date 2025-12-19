from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from typing import Optional, Dict, Any
import json
import uuid
import asyncio
import shutil
import os
from pathlib import Path
from logger import error, info
from .schemas import AgentProfile, AgentSchedule
from tools.vision_tools import VisionToolHandlers, ToolStatus

router = APIRouter()

# This will be populated by __init__.py
chat_manager = None
api_config_manager = None

@router.post("/send")
async def send_chat_message(request: Request):
    """Send a message to the chat room."""
    try:
        data = await request.json()
        content = data.get("content")
        sender_name = data.get("sender_name", "User")
        reply_to = data.get("reply_to")
        
        if not content:
            raise HTTPException(status_code=400, detail="Content is required")
        
        # For now, we assume a single 'user' identity
        user_id = "user_main" 
        room_id = data.get("room_id", "casual_lounge") # Default to new room
        
        msg = await chat_manager.post_message(
            room_id, 
            user_id, 
            sender_name, 
            content,
            reply_to=reply_to
        )
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
                    status = agent.is_online()
                    data['is_online'] = status['is_online']
                    data['status_code'] = status['status_code']
                    agents_data.append(data)
    else:
        for agent in chat_manager.agents.values():
            data = agent.profile.dict()
            status = agent.is_online()
            data['is_online'] = status['is_online']
            data['status_code'] = status['status_code']
            agents_data.append(data)
            
    return {"agents": agents_data}

@router.get("/agents/{agent_id}")
async def get_agent_details(agent_id: str):
    """Get detailed info for a single agent including routine."""
    agent = chat_manager.agents.get(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
        
    data = agent.profile.dict()
    status = agent.is_online()
    data['is_online'] = status['is_online']
    data['status_code'] = status['status_code']
    data['current_activity'] = status['activity']
    data['is_generating_routine'] = agent.is_generating_routine
    data['last_processed_msg_id'] = agent.profile.last_processed_msg_id
    
    return {"agent": data}

@router.post("/agents/{agent_id}/regenerate_routine")
async def regenerate_agent_routine(agent_id: str):
    """Force regeneration of daily routine."""
    try:
        routine = await chat_manager.regenerate_agent_routine(agent_id)
        return {"status": "success", "daily_routine": routine}
    except ValueError:
        raise HTTPException(status_code=404, detail="Agent not found")
    except Exception as e:
        error(f"Routine regeneration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

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
            "type": r.type, # Include type
            "system_prompt": r.system_prompt,
            "is_paused": r.is_paused,
            "active_agents": r.active_agents, # Include list of agents
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

@router.post("/dm/create")
async def create_dm(request: Request):
    """Create or get a DM room."""
    try:
        data = await request.json()
        agent_id = data.get("agent_id")
        user_id = "user_main" # Hardcoded for now
        
        if not agent_id:
            raise HTTPException(status_code=400, detail="Agent ID required")
            
        room = chat_manager.create_dm_room(user_id, agent_id)
        return {"status": "success", "room": room.dict(exclude={'history'})}
    except Exception as e:
        error(f"Failed to create DM: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/rooms/{room_id}/pause")
async def pause_room(room_id: str, request: Request):
    """Pause or resume a room."""
    try:
        data = await request.json()
        paused = data.get("paused", True) # Default to pause if not specified
        
        if chat_manager.toggle_pause_room(room_id, paused):
            status_str = "paused" if paused else "resumed"
            return {"status": "success", "message": f"Room {status_str}"}
        else:
            raise HTTPException(status_code=404, detail="Room not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

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
            for msg_obj in response:
                content = msg_obj.get("content", "")
                reply_to = msg_obj.get("reply_to")
                await chat_manager.post_message(
                    room_id=room_id,
                    sender_id=agent.profile.id,
                    sender_name=agent.profile.name,
                    content=content,
                    reply_to=reply_to
                )
            return {"status": "success", "response": response}
        else:
            return {"status": "failed", "reason": "No response"}
    except Exception as e:
        error(f"Debug trigger failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/upload_image")
async def upload_chat_image(
    file: UploadFile = File(...),
    room_id: str = Form(...),
    sender_name: str = Form("User")
):
    """Upload image, analyze it, and post as a message."""
    try:
        # 1. Save Image
        # Ensure directory exists
        images_dir = Path(chat_manager.data_dir) / "images"
        images_dir.mkdir(exist_ok=True, parents=True)
        
        file_ext = Path(file.filename).suffix
        if not file_ext:
            file_ext = ".jpg"
            
        filename = f"img_{uuid.uuid4().hex[:8]}{file_ext}"
        file_path = images_dir / filename
        
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # 2. Analyze Image
        description = "[Image analysis skipped]"
        
        if api_config_manager:
            try:
                handlers = VisionToolHandlers(api_config_manager)
                # Mock args and context
                args = {"image_path": str(file_path), "query": "Please describe this image in detail for a chat context. If it contains text, please extract it. Keep it concise."}
                context = {"call_id": "upload_trigger"}
                
                info(f"[CyberChat] Analyzing uploaded image: {filename}")
                result = await handlers.analyze_image(args, context)
                
                if result.status == ToolStatus.SUCCESS:
                    raw_desc = result.data.get("description", "")
                    description = f"[User uploaded an image. Visual description: {raw_desc}]"
                else:
                    description = f"[User uploaded an image. Analysis error: {result.error}]"
            except Exception as e:
                error(f"[CyberChat] Vision analysis failed: {e}")
                description = f"[User uploaded an image. Analysis failed.]"
        else:
             error(f"[CyberChat] Vision analysis skipped: api_config_manager not available")

        # 3. Post Message
        # Content = Description (for LLM)
        # Payload = URL + Description (for UI)
        
        # URL construction: Assuming /static/files maps to DATA_DIR
        # images_dir is in DATA_DIR/cyber_chat/images
        # So relative path from DATA_DIR is cyber_chat/images/filename
        rel_path = f"cyber_chat/images/{filename}"
        image_url = f"/static/files/{rel_path}"
        
        payload = {
            "type": "image",
            "url": image_url,
            "description": description
        }
        
        msg = await chat_manager.post_message(
            room_id,
            "user_main",
            sender_name,
            content=description,
            msg_type="image",
            payload=payload
        )
        
        return {"status": "success", "message": msg}
        
    except Exception as e:
        error(f"Error uploading image: {e}")
        import traceback
        error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))
