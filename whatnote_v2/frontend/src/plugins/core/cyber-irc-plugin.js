
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
  const [currentRoom, setCurrentRoom] = useState({ id: 'casual_lounge', name: 'The Lounge' });
  const [rooms, setRooms] = useState([]);
  const [messages, setMessages] = useState([]);
  const [agents, setAgents] = useState([]); // Agents IN current room
  const [allAgents, setAllAgents] = useState([]); // All agents for invite
  const [inputValue, setInputValue] = useState('');
  const [isConnected, setIsConnected] = useState(false);
  const chatEndRef = useRef(null);

  // UI State
  const [showCreateRoom, setShowCreateRoom] = useState(false);
  const [showCreateAgent, setShowCreateAgent] = useState(false);
  const [showInviteAgent, setShowInviteAgent] = useState(false);
  
  // Form State
  const [newRoomName, setNewRoomName] = useState('');
  const [newRoomTopic, setNewRoomTopic] = useState('');
  const [newRoomSystem, setNewRoomSystem] = useState('');
  const [agentDescription, setAgentDescription] = useState('');
  const [generatedAgent, setGeneratedAgent] = useState(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [selectedAgentId, setSelectedAgentId] = useState('');

  // --- Data Fetching ---

  const fetchRooms = async () => {
    try {
      const res = await fetch(`${API_BASE}/rooms`);
      const data = await res.json();
      setRooms(data.rooms || []);
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
    fetchRooms();
    fetchAllAgents();
  }, []);

  // Room Switch
  useEffect(() => {
    if (currentRoom?.id) {
      setMessages([]); // Clear previous msgs visually first
      fetchHistory(currentRoom.id);
      fetchAgentsInRoom(currentRoom.id);
    }
  }, [currentRoom]);

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // SSE Connection
  useEffect(() => {
    const eventSource = new EventSource('http://localhost:8081/api/chat/stream');
    
    eventSource.onopen = () => {
      setIsConnected(true);
    };

    eventSource.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        // Only show if belongs to current room OR is a system broadcast
        if (msg.room_id === currentRoom.id || !msg.room_id) {
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

  // --- Actions ---

  const handleSend = async () => {
    if (!inputValue.trim()) return;
    const content = inputValue;
    setInputValue('');
    try {
      await fetch(`${API_BASE}/send`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content, room_id: currentRoom.id, sender_name: "User" })
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

  // --- Render ---

  return (
    <div style={styles.container}>
      {/* Header */}
      <div style={styles.toolbar}>
        <div style={{fontWeight: 'bold'}}>#{currentRoom.name}</div>
        <div style={{fontSize: '10px', color: '#aaaaaa'}}>{currentRoom.topic}</div>
        <div>{isConnected ? '[ONLINE]' : '[CONNECTING...]'}</div>
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
              <div style={styles.listItem}><div style={{...styles.statusDot, backgroundColor: '#fff'}}></div>User</div>
              {agents.map(a => (
                <div key={a.id} style={styles.listItem} title={a.personality}>
                  <div style={{...styles.statusDot, backgroundColor: getSenderColor(a.name)}}></div>
                  {a.name}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Chat Log */}
        <div style={styles.chatArea}>
          {messages.map((msg, idx) => (
            <div key={msg.id || idx} style={styles.message}>
              <span style={styles.timestamp}>[{formatTime(msg.timestamp)}]</span>
              {msg.type === 'system' ? (
                <span style={styles.systemMsg}>*** {msg.content}</span>
              ) : (
                <>
                  <span style={{...styles.sender, color: getSenderColor(msg.sender_name)}}>
                    &lt;{msg.sender_name}&gt;
                  </span>
                  <span>{msg.content}</span>
                </>
              )}
            </div>
          ))}
          <div ref={chatEndRef} />
        </div>
      </div>

      {/* Input */}
      <div style={styles.inputArea}>
        <span style={{marginRight: '8px', color: '#00ff00'}}>&gt;</span>
        <input
          style={styles.input}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleSend()}
          placeholder={`Message #${currentRoom.name}...`}
        />
        <button style={styles.button} onClick={handleSend}>SEND</button>
      </div>

      {/* Modals */}
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
              <p><strong style={{color: '#fff'}}>Role:</strong> {generatedAgent.personality}</p>
              <p><strong style={{color: '#fff'}}>Style:</strong> {generatedAgent.style}</p>
              
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
