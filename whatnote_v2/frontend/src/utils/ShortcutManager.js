class ShortcutManager {
  constructor() {
    this.actions = {}; // { id: { label, defaultKey, category, description } }
    this.overrides = {}; // { id: keyString }
    this.listeners = new Set();
    this.load();
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
    // Normalize comparison (case insensitive for single letters?)
    // targetKey might be "Ctrl+S", eventKey might be "Ctrl+s"
    return eventKey.toLowerCase() === targetKey.toLowerCase();
  }

  getEventKeyString(event) {
    const keys = [];
    if (event.ctrlKey) keys.push('Ctrl');
    if (event.altKey) keys.push('Alt');
    if (event.shiftKey) keys.push('Shift');
    if (event.metaKey) keys.push('Meta');
    
    let key = event.key;
    
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


