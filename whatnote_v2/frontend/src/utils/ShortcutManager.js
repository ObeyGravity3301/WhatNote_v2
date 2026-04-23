class ShortcutManager {
  constructor() {
    this.actions = {}; // { id: { label, defaultKey, category, description } }
    this.overrides = {}; // { id: keyString }
    this.listeners = new Set();
    this.initDefaults(); // Add this line
    this.load();
  }

  initDefaults() {
    // 1. System
    this.register('system.start_menu', { label: '打开开始菜单', defaultKey: 'Alt+S', category: '系统', description: '打开左下角开始菜单' });
    this.register('system.ai_assistant', { label: '打开AI助手', defaultKey: 'Alt+C', category: '系统', description: '打开AI助手聊天窗口' });
    this.register('system.calendar', { label: '打开日历', defaultKey: 'Alt+D', category: '系统', description: '打开日历与计划窗口' });
    
    // 2. Window Management
    this.register('window.minimize', { label: '最小化当前窗口', defaultKey: 'Ctrl+M', category: '窗口', description: '最小化当前获得焦点的窗口' });
    // this.register('window.close', { label: '关闭当前窗口', defaultKey: 'Alt+W', category: '窗口', description: '关闭当前获得焦点的窗口' });
    
    // 3. Desktop
    this.register('desktop.rename', { label: '重命名', defaultKey: 'F2', category: '桌面', description: '重命名选中的桌面图标' });
    this.register('desktop.delete', { label: '删除', defaultKey: 'Delete', category: '桌面', description: '删除选中的桌面图标或窗口' });
    
    // 4. PDF Reader
    this.register('pdf.prev_page', { label: '上一页', defaultKey: 'ArrowLeft', category: 'PDF阅读器', description: 'PDF 翻到上一页' });
    this.register('pdf.next_page', { label: '下一页', defaultKey: 'ArrowRight', category: 'PDF阅读器', description: 'PDF 翻到下一页' });
    this.register('pdf.toggle_narrator', { label: '切换讲解模式', defaultKey: 'n', category: 'PDF阅读器', description: '打开/关闭讲解控制台' });
    
    // 5. Narrator Player
    this.register('narrator.play_pause', { label: '播放/暂停', defaultKey: 'Space', category: 'PDF讲解', description: '播放或暂停讲解语音' });
    this.register('narrator.rewind', { label: '上一句', defaultKey: ',', category: 'PDF讲解', description: '跳转到上一句字幕' });
    this.register('narrator.forward', { label: '下一句', defaultKey: '.', category: 'PDF讲解', description: '跳转到下一句字幕' });
  }

  load() {
    try {
      const saved = localStorage.getItem('whatnote_shortcuts');
      if (saved) {
        this.overrides = JSON.parse(saved);
      }
    } catch (e) {
      console.error('Failed to load shortcuts', e);
    }
  }

  save() {
    try {
      localStorage.setItem('whatnote_shortcuts', JSON.stringify(this.overrides));
      this.notify();
    } catch (e) {
      console.error('Failed to save shortcuts', e);
    }
  }

  register(id, config) {
    if (!this.actions[id]) {
      this.actions[id] = config;
      // If we have an override, we don't need to do anything
      // If no override, the default is used
    }
  }

  // Get the effective key string for an action
  get(id) {
    return this.overrides[id] || this.actions[id]?.defaultKey;
  }

  // Set a custom key for an action
  set(id, keyString) {
    this.overrides[id] = keyString;
    this.save();
  }

  // Reset an action to default
  reset(id) {
    delete this.overrides[id];
    this.save();
  }

  // Check if an event matches an action
  matches(id, event) {
    const targetKey = this.get(id);
    if (!targetKey) return false;
    
    const eventKey = this.getEventKeyString(event);
    const isMatch = eventKey.toLowerCase() === targetKey.toLowerCase();
    
    if (isMatch || event.key === 'n' || event.key === 'N' || event.altKey) {
        console.log(`[ShortcutManager] Checking '${id}': Target='${targetKey}', Event='${eventKey}', Match=${isMatch}`);
    }
    
    return isMatch;
  }

  getEventKeyString(event) {
    const keys = [];
    if (event.ctrlKey) keys.push('Ctrl');
    if (event.altKey) keys.push('Alt');
    if (event.shiftKey) keys.push('Shift');
    if (event.metaKey) keys.push('Meta');
    
    let key = event.key;
    
    // Normalize Chinese punctuation to English and handle shift variants
    if (key === '，' || key === '<') key = ',';
    if (key === '。' || key === '>') key = '.';
    if (key === '！') key = '!';
    if (key === '？') key = '?';
    if (key === '：') key = ':';
    if (key === '；') key = ';';
    if (key === '（') key = '(';
    if (key === '）') key = ')';
    
    // Normalize key names
    if (key === ' ') key = 'Space';
    if (key === 'Control') return ''; // Modifier only
    if (key === 'Alt') return '';
    if (key === 'Shift') return '';
    if (key === 'Meta') return '';
    
    // Arrow keys
    // ArrowUp, ArrowDown, ArrowLeft, ArrowRight are standard
    
    if (key) keys.push(key);
    
    return keys.join('+');
  }

  getAllActions() {
    return Object.entries(this.actions).map(([id, config]) => ({
      id,
      ...config,
      currentKey: this.get(id)
    }));
  }

  subscribe(listener) {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  notify() {
    this.listeners.forEach(listener => listener());
  }
}

const instance = new ShortcutManager();
export default instance;


