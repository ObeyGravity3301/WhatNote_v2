
/**
 * CyberIRC 98 Plugin (v2.0)
 * Multi-room, Autonomous Agent Management, LLM Persona Generation.
 */
import React, { useState, useEffect, useRef } from 'react';

// --- Styles ---
const styles = {
  container: {
    height: '100%',
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
    backgroundColor: '#000000',
    color: '#00ff00',
    fontFamily: '"Courier New", Courier, monospace',
    fontSize: '14px',
    overflow: 'hidden',
  },
  toolbar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '4px 8px',
    borderBottom: '1px solid #004400',
    backgroundColor: '#001100',
    fontSize: '12px',
  },
  mainArea: {
    flex: 1,
    display: 'flex',
    overflow: 'hidden',
    borderBottom: '2px solid #008800',
  },
  chatArea: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflowY: 'auto',
    padding: '8px',
    borderRight: '1px solid #004400',
  },
  sidebar: {
    width: '180px',
    backgroundColor: '#000a00',
    borderLeft: '1px solid #004400',
    display: 'flex',
    flexDirection: 'column',
  },
  sidebarSection: {
    padding: '8px',
    borderBottom: '1px solid #002200',
    flexShrink: 0,
  },
  sidebarTitle: {
    marginBottom: '6px',
    textDecoration: 'underline',
    color: '#008800',
    fontSize: '11px',
    display: 'flex',
    justifyContent: 'space-between',
    cursor: 'default',
  },
  sidebarList: {
    overflowY: 'auto',
    flex: 1,
  },
  inputArea: {
    height: '40px',
    display: 'flex',
    alignItems: 'center',
    padding: '4px',
    backgroundColor: '#002200',
  },
  input: {
    flex: 1,
    backgroundColor: '#000000',
    color: '#00ff00',
    border: '1px solid #008800',
    padding: '4px 8px',
    fontFamily: 'inherit',
    outline: 'none',
  },
  button: {
    marginLeft: '8px',
    backgroundColor: '#004400',
    color: '#00ff00',
    border: '1px solid #008800',
    padding: '2px 8px',
    cursor: 'pointer',
    fontFamily: 'inherit',
    fontSize: '12px',
  },
  actionButton: {
    backgroundColor: 'transparent',
    color: '#00aa00',
    border: '1px solid #004400',
    padding: '1px 4px',
    cursor: 'pointer',
    fontSize: '10px',
    marginLeft: '4px',
  },
  message: {
    marginBottom: '6px',
    lineHeight: '1.4',
    wordBreak: 'break-all',
  },
  timestamp: {
    color: '#006600',
    marginRight: '8px',
    fontSize: '11px',
  },
  sender: {
    fontWeight: 'bold',
    marginRight: '8px',
  },
  systemMsg: {
    color: '#00aaaa',
    fontStyle: 'italic',
  },
  listItem: {
    marginBottom: '4px',
    fontSize: '12px',
    display: 'flex',
    alignItems: 'center',
    cursor: 'pointer',
    padding: '2px',
  },
  listItemActive: {
    backgroundColor: '#003300',
  },
  statusDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    marginRight: '6px',
  },
  modalOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.8)',
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 100,
  },
  modal: {
    backgroundColor: '#001100',
    border: '2px solid #00ff00',
    padding: '16px',
    width: '400px',
    maxWidth: '90%',
    boxShadow: '0 0 20px rgba(0, 255, 0, 0.2)',
  },
  modalTitle: {
    fontSize: '16px',
    borderBottom: '1px solid #00ff00',
    marginBottom: '12px',
    paddingBottom: '4px',
  },
  formGroup: {
    marginBottom: '12px',
  },
  label: {
    display: 'block',
    marginBottom: '4px',
    fontSize: '12px',
    color: '#00aa00',
  },
  formInput: {
    width: '100%',
    backgroundColor: '#000000',
    color: '#00ff00',
    border: '1px solid #006600',
    padding: '4px',
    fontFamily: 'inherit',
  },
  modalButtons: {
    display: 'flex',
    justifyContent: 'flex-end',
    marginTop: '16px',
  },
  replyQuote: {
    borderLeft: '2px solid #008800',
    marginBottom: '4px',
    fontSize: '10px',
    color: '#aaa',
    backgroundColor: 'rgba(0, 50, 0, 0.3)',
    padding: '2px 4px',
    cursor: 'pointer',
    opacity: 0.8
  },
  replyBar: {
    backgroundColor: '#002200',
    color: '#aaa',
    fontSize: '11px',
    padding: '4px 8px',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    borderTop: '1px solid #004400',
    borderBottom: '1px solid #004400'
  }
};

const API_BASE = 'http://localhost:8081/api/chat';

// --- Helper Components ---

const Modal = ({ title, children, onClose, onConfirm, confirmText = "OK", isLoading = false }) => (
  <div style={styles.modalOverlay}>
    <div style={styles.modal}>
      <div style={styles.modalTitle}>{title}</div>
      {children}
      <div style={styles.modalButtons}>
        <button style={{...styles.button, backgroundColor: '#330000', borderColor: '#660000'}} onClick={onClose} disabled={isLoading}>CANCEL</button>
        <button style={styles.button} onClick={onConfirm} disabled={isLoading}>
          {isLoading ? 'PROCESSING...' : confirmText}
        </button>
      </div>
    </div>
  </div>
);

// --- Main Component ---

const CyberIRCWindow = ({ window: windowData }) => {
  // State
  // Try to load last room from localStorage, default to null
  const [currentRoom, setCurrentRoom] = useState(() => {
    try {
        const saved = localStorage.getItem('cyber_irc_last_room');
        if (saved) return JSON.parse(saved);
    } catch(e) {}
    // Safe default instead of null
    return { id: null, name: 'Connecting...', topic: '', type: 'group' };
  });
  const [rooms, setRooms] = useState([]);
  const [dms, setDms] = useState([]); // Direct Messages
  const [messages, setMessages] = useState([]);
  const [typingUsers, setTypingUsers] = useState([]); // [Name, Name]
  const [agents, setAgents] = useState([]); // Agents IN current room
  const [allAgents, setAllAgents] = useState([]); // All agents for invite
  const [inputValue, setInputValue] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const chatEndRef = useRef(null);
  const chatAreaRef = useRef(null); // Ref for scrolling container
  const shouldScrollRef = useRef(true); // Track if we should auto-scroll
  const fileInputRef = useRef(null);
  const [isUploading, setIsUploading] = useState(false);

  // UI State
  const [showCreateRoom, setShowCreateRoom] = useState(false);
  const [showCreateAgent, setShowCreateAgent] = useState(false);
  const [showInviteAgent, setShowInviteAgent] = useState(false);
  const [showProfile, setShowProfile] = useState(null); // { agent data }
  const [viewWeekendRoutine, setViewWeekendRoutine] = useState(false); // Toggle for profile view
  
  // Form State
  const [newRoomName, setNewRoomName] = useState('');
  const [newRoomTopic, setNewRoomTopic] = useState('');
  const [newRoomSystem, setNewRoomSystem] = useState('');
  const [agentDescription, setAgentDescription] = useState('');
  const [generatedAgent, setGeneratedAgent] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState('');

  const [isRegenerating, setIsRegenerating] = useState(false);
  const [targetAgentStatus, setTargetAgentStatus] = useState(null); // { last_processed_msg_id, ... }
  const [replyingTo, setReplyingTo] = useState(null); // Message object being replied to
  const [viewingImage, setViewingImage] = useState(null); // URL of image being viewed

  // User Profile State
  const [showUserProfile, setShowUserProfile] = useState(false);
  const [userProfile, setUserProfile] = useState(() => {
      try {
          const saved = localStorage.getItem('cyber_irc_user_profile');
          if (saved) return JSON.parse(saved);
      } catch(e) {}
      return { name: 'User', birthday: '', signature: '' };
  });

  // --- Data Fetching ---

  const fetchAgentDetails = async (agentId) => {
    try {
        const res = await fetch(`${API_BASE}/agents/${agentId}`);
        const data = await res.json();
        return data.agent;
    } catch (e) { 
        console.error(e); 
        return null;
    }
  };

  const fetchRooms = async () => {
    try {
      const res = await fetch(`${API_BASE}/rooms`);
      const data = await res.json();
      const allRooms = data.rooms || [];
      
      setRooms(allRooms.filter(r => r.type !== 'dm'));
      setDms(allRooms.filter(r => r.type === 'dm'));
      
      // Sync currentRoom state
      // Use functional update to ensure we check against the LATEST currentRoom
      setCurrentRoom(prev => {
          if (!prev?.id) return prev;
          
          // Find the room in the fresh list that matches the CURRENTLY selected room ID
          const updated = allRooms.find(r => r.id === prev.id);
          
          if (updated) {
             // Only update if properties changed
             if (prev.is_paused === updated.is_paused && 
                 prev.active_agents_count === updated.active_agents_count &&
                 prev.topic === updated.topic) {
                 return prev;
             }
             return {...prev, ...updated};
          }
          return prev;
      });
    } catch (e) { console.error(e); }
  };

  const fetchAgentsInRoom = async (roomId) => {
    try {
      const res = await fetch(`${API_BASE}/agents?room_id=${roomId}`);
      const data = await res.json();
      setAgents(data.agents || []);
    } catch (e) { console.error(e); }
  };

  const fetchAllAgents = async () => {
    try {
      const res = await fetch(`${API_BASE}/agents`);
      const data = await res.json();
      setAllAgents(data.agents || []);
    } catch (e) { console.error(e); }
  };

  const fetchHistory = async (roomId) => {
    try {
      const res = await fetch(`${API_BASE}/history?room_id=${roomId}`);
      const data = await res.json();
      if (data.history) {
        setMessages(data.history); // Replace history on room switch
      }
    } catch (e) { console.error(e); }
  };

  // --- Effects ---

  // Initial Load
  useEffect(() => {
    // Wrap async init in a function
    const init = async () => {
        await fetchAllAgents();
        
        try {
          const res = await fetch(`${API_BASE}/rooms`);
          const data = await res.json();
          const allRooms = data.rooms || [];
          
          setRooms(allRooms.filter(r => r.type !== 'dm'));
          setDms(allRooms.filter(r => r.type === 'dm'));
          
          // Only set default room if we have NONE selected (first load ever)
          // currentRoom is initialized with { id: null ... } if nothing in localStorage
          if (!currentRoom.id && allRooms.length > 0) {
            const defaultRoom = allRooms.find(r => r.type === 'group') || allRooms[0];
            setCurrentRoom(defaultRoom);
          }
        } catch(e) { console.error(e); }
    };
    init();
  }, []); // Run ONCE

  // Room Switch
  useEffect(() => {
    console.log("[CyberIRC] Room switched to:", currentRoom?.id, currentRoom?.name);
    if (currentRoom?.id) {
      setMessages([]); // Clear previous msgs visually first
      setTypingUsers([]); // Clear typing status
      fetchHistory(currentRoom.id);
      fetchAgentsInRoom(currentRoom.id);
      
      // Save to localStorage
      localStorage.setItem('cyber_irc_last_room', JSON.stringify(currentRoom));
    }
  }, [currentRoom?.id]);

  // Auto-scroll logic
  useEffect(() => {
    // If it's a room switch (messages cleared or changed completely), force scroll
    // But for incremental messages, check shouldScrollRef
    if (shouldScrollRef.current) {
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Handle Scroll Event to update shouldScrollRef
  const handleChatScroll = (e) => {
      const { scrollTop, scrollHeight, clientHeight } = e.target;
      // If within 50px of bottom, enable auto-scroll
      const isNearBottom = scrollHeight - scrollTop - clientHeight < 50;
      shouldScrollRef.current = isNearBottom;
  };
  
  // Reset auto-scroll on room switch
  useEffect(() => {
      shouldScrollRef.current = true;
  }, [currentRoom?.id]);

  // SSE Connection
  useEffect(() => {
    const eventSource = new EventSource('http://localhost:8081/api/chat/stream');
    
    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        
        // Typing Event
        if (msg.type === 'typing_start') {
            if (msg.room_id === currentRoom.id) {
                setTypingUsers(prev => {
                    if (!prev.includes(msg.sender_name)) return [...prev, msg.sender_name];
                    return prev;
                });
                // Auto-clear typing after 10s (failsafe)
                setTimeout(() => {
                    setTypingUsers(prev => prev.filter(u => u !== msg.sender_name));
                }, 10000);
            }
            return;
        }

        // Regular Message
        // Only show if belongs to current room OR is a system broadcast
        if (msg.room_id === currentRoom.id || !msg.room_id) {
          // Remove from typing list
          setTypingUsers(prev => prev.filter(u => u !== msg.sender_name));
          
          setMessages(prev => {
             // Dedup
             if (prev.some(m => m.id === msg.id)) return prev;
             return [...prev, msg];
          });
        }
      } catch (e) { console.error(e); }
    };

    eventSource.onerror = () => setIsConnected(false);
    return () => eventSource.close();
  }, [currentRoom.id]); // Re-bind not strictly needed if logic inside checks room_id, but safer

  // Auto-refresh profile if generating
  useEffect(() => {
    let interval;
    if (showProfile && (showProfile.is_generating_routine || isRegenerating)) {
        interval = setInterval(async () => {
            const updated = await fetchAgentDetails(showProfile.id);
            if (updated) {
                // Check if generation finished
                if (!updated.is_generating_routine && showProfile.is_generating_routine) {
                    setIsRegenerating(false);
                }
                setShowProfile(updated);
            }
        }, 2000);
    }
    return () => clearInterval(interval);
  }, [showProfile, isRegenerating]);

  // Poll for target agent status in DM
  useEffect(() => {
    let interval;
    if (currentRoom.type === 'dm' && currentRoom.active_agents) {
        const agentId = currentRoom.active_agents.find(id => id !== 'user_main');
        if (agentId) {
            const poll = async () => {
                const data = await fetchAgentDetails(agentId);
                if (data) {
                    setTargetAgentStatus(data);
                }
            };
            poll();
            interval = setInterval(poll, 3000);
        }
    } else {
        setTargetAgentStatus(null);
    }
    return () => clearInterval(interval);
  }, [currentRoom.id, currentRoom.type, currentRoom.active_agents]);

  // --- Actions ---

  const handleSaveUserProfile = () => {
      localStorage.setItem('cyber_irc_user_profile', JSON.stringify(userProfile));
      setShowUserProfile(false);
  };

  const handleSend = async () => {
    if (!inputValue.trim()) return;
    const content = inputValue;
    const replyId = replyingTo?.id; // Capture ID
    
    setInputValue('');
    setReplyingTo(null); // Clear reply state immediately
    
    try {
      await fetch(`${API_BASE}/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            content, 
            room_id: currentRoom.id, 
            sender_name: userProfile.name,
            reply_to: replyId,
            payload: {
                user_profile: {
                    birthday: userProfile.birthday,
                    signature: userProfile.signature
                }
            }
        })
      });
    } catch (e) { console.error(e); }
  };

  const handleCreateRoom = async () => {
    try {
      const res = await fetch(`${API_BASE}/rooms`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: newRoomName, topic: newRoomTopic, system_prompt: newRoomSystem })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setShowCreateRoom(false);
        setNewRoomName(''); setNewRoomTopic(''); setNewRoomSystem('');
        fetchRooms();
        setCurrentRoom(data.room); // Switch to new room
      }
    } catch (e) { alert(e.message); }
  };

  const handleGenerateAgent = async () => {
    setIsGenerating(true);
    try {
      const res = await fetch(`${API_BASE}/agents/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description: agentDescription })
      });
      const data = await res.json();
      if (data.status === 'success') {
        setGeneratedAgent(data.agent); // Preview
      }
    } catch (e) { alert("Generation failed: " + e.message); }
    setIsGenerating(false);
  };

  const handleConfirmAgent = async () => {
    if (!generatedAgent) return;
    try {
      const res = await fetch(`${API_BASE}/agents`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(generatedAgent) // Save it
      });
      const data = await res.json();
      if (data.status === 'success') {
        setShowCreateAgent(false);
        setGeneratedAgent(null);
        setAgentDescription('');
        fetchAllAgents();
        // Auto invite to current room? Maybe ask.
        await fetch(`${API_BASE}/rooms/${currentRoom.id}/invite`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ agent_id: data.agent.id })
        });
        fetchAgentsInRoom(currentRoom.id);
      }
    } catch (e) { alert(e.message); }
  };

  const handleInviteAgent = async () => {
    if (!selectedAgentId) return;
    try {
        await fetch(`${API_BASE}/rooms/${currentRoom.id}/invite`, {
            method: 'POST', headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ agent_id: selectedAgentId })
        });
        setShowInviteAgent(false);
        fetchAgentsInRoom(currentRoom.id);
    } catch (e) { alert(e.message); }
  };

  const handleShowProfile = async (agentId) => {
    const agent = await fetchAgentDetails(agentId);
    if (agent) setShowProfile(agent);
  };

  const handleImageUpload = () => {
      fileInputRef.current?.click();
  };

  const uploadImageFile = async (file) => {
      setIsUploading(true);
      const formData = new FormData();
      formData.append('file', file);
      formData.append('room_id', currentRoom.id);
      formData.append('sender_name', userProfile.name);
      
      try {
          const res = await fetch(`${API_BASE}/upload_image`, {
              method: 'POST',
              body: formData
          });
          const data = await res.json();
          if (data.status !== 'success') {
              alert("Upload failed: " + (data.detail || "Unknown error"));
          }
      } catch (err) {
          alert("Upload error: " + err.message);
      } finally {
          setIsUploading(false);
      }
  };

  const handleFileSelect = async (e) => {
      const file = e.target.files[0];
      if (!file) return;
      await uploadImageFile(file);
      e.target.value = null;
  };

  const handlePaste = async (e) => {
      const items = e.clipboardData?.items;
      if (!items) return;

      for (let i = 0; i < items.length; i++) {
          if (items[i].type.indexOf('image') !== -1) {
              e.preventDefault();
              const file = items[i].getAsFile();
              if (file) {
                  await uploadImageFile(file);
              }
              return; 
          }
      }
  };

  const handleTogglePause = async () => {
    try {
        const newStatus = !currentRoom.is_paused;
        await fetch(`${API_BASE}/rooms/${currentRoom.id}/pause`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paused: newStatus })
        });
        fetchRooms(); // Sync state
    } catch (e) { console.error(e); }
  };

  const handleRegenerateRoutine = async () => {
    if (!showProfile) return;
    setIsRegenerating(true);
    try {
        console.log('[CyberIRC] Regenerating routine for:', showProfile.id);
        const res = await fetch(`${API_BASE}/agents/${showProfile.id}/regenerate_routine`, {
            method: 'POST'
        });
        const data = await res.json();
        if (data.status === 'success') {
            console.log('[CyberIRC] Regeneration success:', data.daily_routine);
            // Deep merge to ensure React detects change
            const newProfile = JSON.parse(JSON.stringify(showProfile));
            newProfile.schedule.daily_routine = data.daily_routine;
            setShowProfile(newProfile);
        } else {
            console.error('[CyberIRC] Regeneration failed:', data);
            alert("Failed: " + JSON.stringify(data));
        }
    } catch (e) { 
        console.error('[CyberIRC] Error:', e);
        alert("Regeneration failed: " + e.message); 
    }
    setIsRegenerating(false);
  };

  const handleCreateDm = async (agentId) => {
    try {
        console.log("[CyberIRC] Creating DM with:", agentId);
        const res = await fetch(`${API_BASE}/dm/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ agent_id: agentId })
        });
        const data = await res.json();
        console.log("[CyberIRC] Create DM response:", data);
        
        if (data.status === 'success') {
            const newRoom = data.room;
            
            // 1. Force update DMs list immediately
            setDms(prev => {
                const exists = prev.find(r => r.id === newRoom.id);
                if (exists) return prev;
                return [...prev, newRoom];
            });

            // 2. Set Current Room immediately
            console.log("[CyberIRC] Setting current room to:", newRoom);
            
            // Use setTimeout to break out of batching/render cycle issues
            setTimeout(() => {
                setCurrentRoom(newRoom);
                console.log("[CyberIRC] setCurrentRoom called inside timeout");
            }, 0);
            
            // 3. Close Modal
            setShowProfile(null);
            
            // 4. Fetch latest data in background
            fetchRooms();
        }
    } catch (e) { 
        console.error("[CyberIRC] Failed to start DM:", e);
        alert("Failed to start DM: " + e.message); 
    }
  };

  // --- Helpers ---
  
  const formatTime = (ts) => {
    const date = new Date(ts * 1000);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
  };

  const getSenderColor = (name) => {
    if (name === 'User') return '#ffffff';
    let hash = 0;
    for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
    const c = (hash & 0x00FFFFFF).toString(16).toUpperCase();
    return '#' + '00000'.substring(0, 6 - c.length) + c;
  };

  const isMessageUnread = (msg, index) => {
      // Only for user messages in DM
      if (currentRoom.type !== 'dm' || msg.sender_id !== 'user_main') return false;
      
      // If we don't know status yet, assume unread? Or read? Assume unread.
      if (!targetAgentStatus?.last_processed_msg_id) return true;
      
      // If this message IS the last processed one, it's read.
      if (msg.id === targetAgentStatus.last_processed_msg_id) return false;
      
      // If this message is AFTER the last processed one, it's unread.
      // We need to find the index of last_processed_msg_id in messages array.
      const lastProcessedIndex = messages.findIndex(m => m.id === targetAgentStatus.last_processed_msg_id);
      
      if (lastProcessedIndex === -1) {
          // The last processed message is not in current view (maybe too old?)
          // If we assume messages are sorted by time asc:
          // If msg timestamp > now? Hard to say without comparing IDs.
          // Fallback: If we can't find the processed ID, assume all recent messages are unread?
          // Or assume read if it's very old?
          // Let's assume unread for safety if we can't link it.
          return true;
      }
      
      return index > lastProcessedIndex;
  };

  // --- Render ---

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.toolbar}>
        <div style={{fontWeight: 'bold'}}>#{currentRoom.name}</div>
        <div style={{fontSize: '10px', color: '#aaaaaa'}}>{currentRoom.topic}</div>
        
        <div style={{display:'flex', alignItems:'center'}}>
            {currentRoom.is_paused && <span style={{color:'orange', marginRight:'8px', fontSize:'10px'}}>[PAUSED]</span>}
            <button 
                style={{...styles.actionButton, marginRight:'8px', color: currentRoom.is_paused ? '#00ff00' : '#ffaa00', border: '1px solid currentColor'}} 
                onClick={handleTogglePause}
            >
                {currentRoom.is_paused ? 'RESUME' : 'PAUSE'}
            </button>
            <div>{isConnected ? '[ONLINE]' : '[CONNECTING...]'}</div>
        </div>
      </div>

      <div style={styles.mainArea}>
        {/* Sidebar */}
        <div style={styles.sidebar}>
          {/* Rooms */}
          <div style={{...styles.sidebarSection, maxHeight: '40%'}}>
            <div style={styles.sidebarTitle}>
              <span>ROOMS</span>
              <button style={styles.actionButton} onClick={() => setShowCreateRoom(true)}>+</button>
            </div>
            <div style={styles.sidebarList}>
              {rooms.map(r => (
                <div 
                  key={r.id} 
                  style={{...styles.listItem, ...(r.id === currentRoom.id ? styles.listItemActive : {})}}
                  onClick={() => setCurrentRoom(r)}
                >
                  <span style={{color: '#00aa00'}}>#</span> {r.name}
                </div>
              ))}
            </div>
          </div>

          {/* DMs */}
          <div style={{...styles.sidebarSection, maxHeight: '30%'}}>
            <div style={styles.sidebarTitle}>
              <span>DIRECT MESSAGES</span>
            </div>
            <div style={styles.sidebarList}>
              {dms.map(r => (
                <div 
                  key={r.id} 
                  style={{...styles.listItem, ...(r.id === currentRoom.id ? styles.listItemActive : {})}}
                  onClick={() => setCurrentRoom(r)}
                >
                  <span style={{color: '#00aaaa'}}>@</span> {r.name}
                </div>
              ))}
            </div>
          </div>

          {/* Agents */}
          <div style={{...styles.sidebarSection, flex: 1, borderBottom: 'none'}}>
            <div style={styles.sidebarTitle}>
              <span>MEMBERS ({agents.length})</span>
              <div>
                <button style={styles.actionButton} onClick={() => setShowInviteAgent(true)}>INV</button>
                <button style={styles.actionButton} onClick={() => setShowCreateAgent(true)}>NEW</button>
              </div>
            </div>
            <div style={styles.sidebarList}>
              <div style={{...styles.listItem, cursor:'pointer'}} onClick={() => setShowUserProfile(true)}>
                  <div style={{...styles.statusDot, backgroundColor: '#00ff00'}}></div>
                  {userProfile.name} (You) <span style={{fontSize:'9px', color:'#aaa', marginLeft:'4px'}}>[EDIT]</span>
              </div>
              {agents.map(a => (
                <div key={a.id} style={styles.listItem} title={a.personality} onClick={() => handleShowProfile(a.id)}>
                  <div style={{...styles.statusDot, backgroundColor: a.is_online ? '#00ff00' : '#555555'}}></div>
                  <span style={{color: a.is_online ? '#fff' : '#888'}}>{a.name}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Chat Log */}
        <div 
            style={styles.chatArea} 
            ref={chatAreaRef}
            onScroll={handleChatScroll}
        >
          {messages.map((msg, idx) => {
            const replyTarget = msg.reply_to ? messages.find(m => m.id === msg.reply_to) : null;
            return (
            <div key={msg.id || idx} style={styles.message}>
              <span style={styles.timestamp}>[{formatTime(msg.timestamp)}]</span>
              {msg.type === 'system' ? (
                <span style={styles.systemMsg}>*** {msg.content}</span>
              ) : (
                <div style={{display:'inline-block', width:'100%', verticalAlign:'top'}}>
                  {replyTarget && (
                      <div style={styles.replyQuote}>
                          <span style={{fontWeight:'bold'}}>{replyTarget.sender_name}: </span>
                          {replyTarget.content.length > 60 ? replyTarget.content.substring(0,60)+'...' : replyTarget.content}
                      </div>
                  )}
                  <span 
                    style={{...styles.sender, color: getSenderColor(msg.sender_name), cursor:'pointer'}}
                    title="Click to reply"
                    onClick={() => setReplyingTo(msg)}
                  >
                    &lt;{msg.sender_name}&gt;
                  </span>
                  
                  {msg.type === 'image' && msg.payload?.url ? (
                      <div style={{marginTop: '4px', marginBottom: '4px'}}>
                          <img 
                              src={`http://localhost:8081${msg.payload.url}`} 
                              alt="User uploaded" 
                              style={{
                                  maxWidth: '300px', 
                                  maxHeight: '200px', 
                                  border: '1px solid #004400', 
                                  display: 'block',
                                  cursor: 'pointer'
                              }}
                              onClick={() => setViewingImage(`http://localhost:8081${msg.payload.url}`)}
                          />
                          <div style={{fontSize: '10px', color: '#666', fontStyle: 'italic'}}>
                              {msg.content}
                          </div>
                      </div>
                  ) : (
                      <span>{msg.content}</span>
                  )}

                  {isMessageUnread(msg, idx) && (
                      <span style={{marginLeft: '8px', color: '#666', fontSize: '10px', fontStyle: 'italic'}}>
                          [Unread{targetAgentStatus && !targetAgentStatus.is_online ? ' - Offline' : ''}]
                      </span>
                  )}
                </div>
              )}
            </div>
          )})}
          <div ref={chatEndRef} />
          
          {/* Typing Indicator */}
          {typingUsers.length > 0 && (
            <div style={{padding: '4px', fontSize: '10px', color: '#00aaaa', fontStyle: 'italic'}}>
                {typingUsers.join(', ')} is typing...
            </div>
          )}
          
          {/* Debug Info for Unread Status */}
          {currentRoom.type === 'dm' && (
              <div style={{fontSize: '9px', color: '#444', marginTop: '4px'}}>
                  DEBUG: LastProcessedID: {targetAgentStatus?.last_processed_msg_id || 'null'} | 
                  Unread: {messages.filter((m, i) => isMessageUnread(m, i)).length} |
                  Status: {targetAgentStatus?.is_online ? 'ONLINE' : 'OFFLINE'} ({targetAgentStatus?.status_code})
              </div>
          )}
        </div>
      </div>

      {/* Reply Bar */}
      {replyingTo && (
          <div style={styles.replyBar}>
              <div>
                  <span style={{color: '#00aa00'}}>Replying to {replyingTo.sender_name}: </span>
                  <span style={{fontStyle:'italic'}}>"{replyingTo.content.substring(0, 30)}{replyingTo.content.length>30?'...':''}"</span>
              </div>
              <button style={styles.actionButton} onClick={() => setReplyingTo(null)}>CANCEL</button>
          </div>
      )}

      {/* Input */}
      <div style={styles.inputArea}>
        <span style={{marginRight: '8px', color: '#00ff00'}}>&gt;</span>
        
        <input 
            type="file" 
            ref={fileInputRef} 
            style={{display: 'none'}} 
            accept="image/*"
            onChange={handleFileSelect}
        />
        
         <button 
            style={{...styles.button, marginRight: '8px', padding: '2px 6px', fontSize: '14px'}} 
            onClick={handleImageUpload}
            disabled={isUploading}
            title="Upload Image"
         >
            {isUploading ? '...' : '📷'}
         </button>

        <input
          style={styles.input}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          onPaste={handlePaste}
          placeholder={`Message #${currentRoom.name}...`}
        />
        <button style={styles.button} onClick={handleSend}>SEND</button>
      </div>

      {/* Modals */}
      {viewingImage && (
        <div 
            style={{
                position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                backgroundColor: 'rgba(0,0,0,0.9)', 
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                zIndex: 200
            }}
            onClick={() => setViewingImage(null)}
        >
            <div style={{position: 'relative', maxWidth: '90%', maxHeight: '90%'}} onClick={e => e.stopPropagation()}>
                <img 
                    src={viewingImage} 
                    alt="Full size" 
                    style={{maxWidth: '100%', maxHeight: '100%', border: '2px solid #00ff00', objectFit: 'contain'}}
                />
                <button 
                    style={{
                        position: 'absolute', top: '-30px', right: 0,
                        backgroundColor: 'transparent', color: '#00ff00', border: 'none',
                        fontSize: '20px', cursor: 'pointer', fontFamily: 'monospace'
                    }}
                    onClick={() => setViewingImage(null)}
                >
                    [CLOSE]
                </button>
            </div>
        </div>
      )}

      {showProfile && (
        <Modal title={`USER PROFILE: ${showProfile.name.toUpperCase()}`} onClose={() => setShowProfile(null)} onConfirm={() => setShowProfile(null)} confirmText="CLOSE">
            <div style={{maxHeight: '400px', overflowY: 'auto'}}>
                <div style={{display:'flex', alignItems:'center', marginBottom:'12px'}}>
                    <div style={{width:'40px', height:'40px', borderRadius:'50%', backgroundColor: getSenderColor(showProfile.name), marginRight:'12px'}}></div>
                    <div>
                        <div style={{fontWeight:'bold', fontSize:'14px'}}>{showProfile.name}</div>
                        <div style={{fontSize:'10px', color:'#aaa'}}>{showProfile.id}</div>
                    </div>
                    <div style={{marginLeft:'auto', textAlign:'right'}}>
                        <div style={{color: showProfile.is_online ? '#00ff00' : '#ff0000', fontWeight:'bold'}}>
                            {showProfile.is_online ? 'ONLINE' : 'OFFLINE'}
                        </div>
                        <div style={{fontSize:'10px', color:'#aaa'}}>{showProfile.status_code}</div>
                    </div>
                </div>
                
                <div style={{marginBottom:'12px', display:'flex', justifyContent:'center'}}>
                    <button 
                        style={{...styles.button, width: '100%', backgroundColor:'#003300'}}
                        onClick={() => handleCreateDm(showProfile.id)}
                    >
                        [ SEND MESSAGE ]
                    </button>
                </div>

              <div style={{marginBottom:'12px', borderBottom:'1px solid #333', paddingBottom:'8px'}}>
                  <strong style={{color:'#00aa00', fontSize:'11px'}}>PERSONALITY</strong>
                  <div style={{fontSize:'12px', marginTop:'4px'}}>{showProfile.personality}</div>
                  <div style={{fontSize:'11px', color:'#888', marginTop:'4px'}}>
                      {showProfile.gender} | {showProfile.language}
                      {showProfile.birthday && ` | 🎂 ${showProfile.birthday}`}
                  </div>
                  {showProfile.signature && (
                      <div style={{fontSize:'11px', color:'#00aaaa', marginTop:'4px', fontStyle:'italic'}}>
                          "{showProfile.signature}"
                      </div>
                  )}
              </div>

              {showProfile.subscribed_feeds && showProfile.subscribed_feeds.length > 0 && (
                  <div style={{marginBottom:'12px', borderBottom:'1px solid #333', paddingBottom:'8px'}}>
                      <strong style={{color:'#00aa00', fontSize:'11px'}}>SUBSCRIBED FEEDS</strong>
                      <div style={{marginTop:'4px'}}>
                          {showProfile.subscribed_feeds.map((feed, idx) => (
                              <div key={idx} style={{fontSize:'11px', color:'#ccc', marginBottom:'2px'}}>
                                  • {feed}
                              </div>
                          ))}
                      </div>
                  </div>
              )}

              <div style={{marginBottom:'12px', borderBottom:'1px solid #333', paddingBottom:'8px'}}>
                  <strong style={{color:'#00aa00', fontSize:'11px'}}>CURRENT STATUS</strong>
                    <div style={{fontSize:'12px', marginTop:'4px', fontStyle:'italic', color:'#00ffff'}}>
                        "{showProfile.current_activity || 'Unknown activity'}"
                    </div>
                </div>

                <div>
                    <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                        <strong style={{color:'#00aa00', fontSize:'11px'}}>
                            DAILY ROUTINE ({viewWeekendRoutine ? 'WEEKEND' : 'WEEKDAY'})
                        </strong>
                        <div>
                            <button 
                                style={{...styles.actionButton, border:'1px solid #444', fontSize:'9px', padding:'2px 6px', marginRight:'4px', color: '#fff'}}
                                onClick={() => setViewWeekendRoutine(!viewWeekendRoutine)}
                            >
                                {viewWeekendRoutine ? 'SHOW WEEKDAY' : 'SHOW WEEKEND'}
                            </button>
                            <button 
                                style={{...styles.actionButton, border:'1px solid #004400', fontSize:'9px', padding:'2px 6px'}}
                                onClick={handleRegenerateRoutine}
                                disabled={isRegenerating || showProfile.is_generating_routine}
                            >
                                {(isRegenerating || showProfile.is_generating_routine) ? 'GENERATING...' : 'REGENERATE'}
                            </button>
                        </div>
                    </div>
                    <div style={{marginTop:'8px', marginLeft:'4px', borderLeft:'1px solid #333', paddingLeft:'8px', position: 'relative'}}>
                        {(isRegenerating || showProfile.is_generating_routine) && (
                            <div style={{
                                position: 'absolute', top: 0, left: 0, right: 0, bottom: 0,
                                backgroundColor: 'rgba(0,0,0,0.7)', display: 'flex', 
                                alignItems: 'center', justifyContent: 'center', zIndex: 10
                            }}>
                                <span style={{color: '#00ff00', fontWeight: 'bold'}}>Thinking...</span>
                            </div>
                        )}
                        {Object.entries(
                            (viewWeekendRoutine 
                                ? showProfile.schedule?.daily_routine_weekend 
                                : showProfile.schedule?.daily_routine) || {}
                            )
                            .sort((a,b) => parseInt(a[0]) - parseInt(b[0]))
                            .map(([hour, activity]) => (
                            <div key={hour} style={{fontSize:'11px', marginBottom:'4px', display:'flex'}}>
                                <span style={{color:'#aaa', width:'40px', flexShrink:0}}>{hour.padStart(2,'0')}:00</span>
                                <span style={{color: '#fff'}}>{activity}</span>
                            </div>
                        ))}
                        {(!showProfile.schedule?.daily_routine || Object.keys(showProfile.schedule.daily_routine).length === 0) && (
                            <div style={{color:'#666', fontStyle:'italic'}}>Generating routine... (Check back later)</div>
                        )}
                    </div>
                </div>
            </div>
        </Modal>
      )}

      {showUserProfile && (
        <Modal title="EDIT MY PROFILE" onClose={() => setShowUserProfile(false)} onConfirm={handleSaveUserProfile} confirmText="SAVE">
            <div style={styles.formGroup}>
                <label style={styles.label}>Nickname</label>
                <input style={styles.formInput} value={userProfile.name} onChange={e => setUserProfile({...userProfile, name: e.target.value})} />
            </div>
            <div style={styles.formGroup}>
                <label style={styles.label}>Birthday (MM-DD)</label>
                <input style={styles.formInput} value={userProfile.birthday} onChange={e => setUserProfile({...userProfile, birthday: e.target.value})} placeholder="e.g. 05-21" />
            </div>
            <div style={styles.formGroup}>
                <label style={styles.label}>Signature / Bio</label>
                <input style={styles.formInput} value={userProfile.signature} onChange={e => setUserProfile({...userProfile, signature: e.target.value})} placeholder="Short bio..." />
            </div>
        </Modal>
      )}

      {showCreateRoom && (
        <Modal title="CREATE NEW ROOM" onClose={() => setShowCreateRoom(false)} onConfirm={handleCreateRoom} confirmText="CREATE">
          <div style={styles.formGroup}>
            <label style={styles.label}>Room Name</label>
            <input style={styles.formInput} value={newRoomName} onChange={e => setNewRoomName(e.target.value)} placeholder="e.g. WarRoom" />
          </div>
          <div style={styles.formGroup}>
            <label style={styles.label}>Topic</label>
            <input style={styles.formInput} value={newRoomTopic} onChange={e => setNewRoomTopic(e.target.value)} placeholder="e.g. Strategic Ops" />
          </div>
          <div style={styles.formGroup}>
            <label style={styles.label}>System Prompt / Rules</label>
            <textarea style={{...styles.formInput, height: '60px'}} value={newRoomSystem} onChange={e => setNewRoomSystem(e.target.value)} placeholder="Define the context and rules for this room..." />
          </div>
        </Modal>
      )}

      {showCreateAgent && (
        <Modal 
          title={generatedAgent ? "CONFIRM AGENT" : "GENERATE NEW AGENT"} 
          onClose={() => { setShowCreateAgent(false); setGeneratedAgent(null); }} 
          onConfirm={generatedAgent ? handleConfirmAgent : handleGenerateAgent} 
          confirmText={generatedAgent ? "SAVE & JOIN" : "GENERATE"}
          isLoading={isGenerating}
        >
          {!generatedAgent ? (
            <div style={styles.formGroup}>
              <label style={styles.label}>Describe the Agent Persona</label>
              <textarea 
                style={{...styles.formInput, height: '100px'}} 
                value={agentDescription} 
                onChange={e => setAgentDescription(e.target.value)} 
                placeholder="e.g. A nervous physics professor obsessed with quantum entanglement who stays up late..." 
              />
            </div>
          ) : (
            <div style={{fontSize: '12px', color: '#ccc', maxHeight: '300px', overflowY: 'auto'}}>
              <p><strong style={{color: '#fff'}}>Name:</strong> {generatedAgent.name}</p>
              <p><strong style={{color: '#fff'}}>Gender:</strong> {generatedAgent.gender || 'Unknown'}</p>
              <p><strong style={{color: '#fff'}}>Language:</strong> {generatedAgent.language || 'Chinese'}</p>
              <p><strong style={{color: '#fff'}}>Role:</strong> {generatedAgent.personality}</p>
              <p><strong style={{color: '#fff'}}>Style:</strong> {generatedAgent.style}</p>
              
              {generatedAgent.subscribed_feeds && generatedAgent.subscribed_feeds.length > 0 && (
                  <div style={{marginTop: '8px', borderTop: '1px solid #333', paddingTop: '4px'}}>
                      <strong style={{color: '#00ff00'}}>SUBSCRIBED FEEDS</strong>
                      <div style={{marginTop:'4px'}}>
                          {generatedAgent.subscribed_feeds.map((feed, idx) => (
                              <div key={idx} style={{fontSize:'11px', color:'#ccc'}}>• {feed}</div>
                          ))}
                      </div>
                  </div>
              )}

              <div style={{marginTop: '8px', borderTop: '1px solid #333', paddingTop: '4px'}}>
                <strong style={{color: '#00ff00'}}>SCHEDULE</strong>
                
                <div style={{marginTop: '4px'}}>
                   <span style={{color: '#aaa'}}>Weekdays: </span>
                   {generatedAgent.schedule?.weekdays_active_hours 
                      ? generatedAgent.schedule.weekdays_active_hours.join(',') 
                      : (generatedAgent.schedule?.active_hours || []).join(',')
                   }
                </div>
                
                <div style={{marginTop: '4px'}}>
                   <span style={{color: '#aaa'}}>Weekends: </span>
                   {generatedAgent.schedule?.weekends_active_hours 
                      ? generatedAgent.schedule.weekends_active_hours.join(',') 
                      : (generatedAgent.schedule?.active_hours || []).join(',')
                   }
                </div>
                
                <div style={{marginTop: '8px', display: 'flex', justifyContent: 'space-between'}}>
                    <div>
                        <span style={{color: '#aaa'}}>Insomnia Chance: </span>
                        {((generatedAgent.schedule?.random_online_chance || 0) * 100).toFixed(0)}%
                    </div>
                    <div>
                        <span style={{color: '#aaa'}}>Busy Chance: </span>
                        {((generatedAgent.schedule?.random_offline_chance || 0) * 100).toFixed(0)}%
                    </div>
                </div>
              </div>
            </div>
          )}
        </Modal>
      )}

      {showInviteAgent && (
        <Modal title="INVITE AGENT" onClose={() => setShowInviteAgent(false)} onConfirm={handleInviteAgent} confirmText="INVITE">
          <div style={styles.formGroup}>
            <label style={styles.label}>Select Agent</label>
            <select 
                style={styles.formInput} 
                value={selectedAgentId} 
                onChange={e => setSelectedAgentId(e.target.value)}
            >
                <option value="">-- Select --</option>
                {allAgents.filter(a => !agents.find(existing => existing.id === a.id)).map(a => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                ))}
            </select>
          </div>
        </Modal>
      )}
    </div>
  );
};

// --- Plugin Definition ---
const cyberIRCPlugin = {
  id: 'cyber-irc',
  name: 'CyberIRC 98',
  description: 'Connect to the autonomous AI chat network.',
  version: '2.0.0',
  author: 'WhatNote Team',
  type: 'window-type',
  windowType: 'cyber-irc',
  enabledByDefault: true,

  renderWindow: (props) => {
    return <CyberIRCWindow {...props} />;
  },

  getDefaultWindowConfig: () => {
    return {
      type: 'cyber-irc',
      title: 'CyberIRC 98',
      size: { width: 700, height: 500 },
      content: '' 
    };
  },

  getWindowIcon: () => {
    return '📟';
  },

  contextMenuItems: [
    {
      label: 'Open CyberIRC',
      action: 'plugin:cyber-irc:create',
      icon: '📟',
      menuType: 'desktop',
      order: 2
    }
  ],

  handleContextMenuAction: async (action, context) => {
    if (action === 'plugin:cyber-irc:create') {
      const { createWindow, windows = [] } = context;
      if (!createWindow) return;

      const defaultConfig = cyberIRCPlugin.getDefaultWindowConfig();
      const windowData = {
        ...defaultConfig,
        title: `CyberIRC 98 - Session ${windows.length + 1}`,
        position: {
          x: 100 + (windows.length * 20),
          y: 100 + (windows.length * 20)
        }
      };
      await createWindow(windowData);
    }
  },

  onEnable: async (context) => {
    console.log('[CyberIRC] Enabling plugin, starting backend loop...');
    try {
      await fetch('http://localhost:8081/api/chat/control', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'start' }) 
      });
    } catch (e) {
      console.error('[CyberIRC] Failed to start backend:', e);
    }
  },

  onDisable: async (context) => {
    console.log('[CyberIRC] Disabling plugin, stopping backend loop...');
    try {
      await fetch('http://localhost:8081/api/chat/control', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'stop' }) 
      });
    } catch (e) {
      console.error('[CyberIRC] Failed to stop backend:', e);
    }
  }
};

export default cyberIRCPlugin;
