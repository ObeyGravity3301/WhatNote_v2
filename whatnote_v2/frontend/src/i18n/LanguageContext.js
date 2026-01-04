import React, { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react';
import translations from './translations';

const LanguageContext = createContext();

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (!context) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};

export const LanguageProvider = ({ children, initialSettings }) => {
  const [language, setLanguage] = useState(initialSettings?.language || 'zh-CN');
  const [theme, setTheme] = useState(initialSettings?.theme || 'win98');

  // 当外部传入的设置变化时同步状态
  useEffect(() => {
    if (initialSettings?.language) setLanguage(initialSettings.language);
    if (initialSettings?.theme) setTheme(initialSettings.theme);
  }, [initialSettings]);

  /**
   * 核心翻译函数 t(key)
   * 查找优先级：
   * 1. translations[key][theme][language]
   * 2. translations[key]['default'][language]
   * 3. translations[key]['default']['zh-CN']
   */
  const t = useCallback((key) => {
    const entry = translations[key];
    if (!entry) return key;

    // 1. 尝试当前主题下的翻译
    if (entry[theme] && entry[theme][language]) {
      return entry[theme][language];
    }

    // 2. 尝试默认翻译下的当前语言
    if (entry['default'] && entry['default'][language]) {
      return entry['default'][language];
    }

    // 3. 回退到默认中文
    if (entry['default'] && entry['default']['zh-CN']) {
      return entry['default']['zh-CN'];
    }

    return key;
  }, [language, theme]);

  const updateLanguage = useCallback(async (newLang) => {
    try {
      const response = await fetch(`http://localhost:8081/api/personalization/language`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ language: newLang })
      });
      if (response.ok) {
        setLanguage(newLang);
        return true;
      }
    } catch (err) {
      console.error('Failed to update language:', err);
    }
    return false;
  }, []);

  const value = useMemo(() => ({
    language,
    theme,
    setTheme,
    t,
    updateLanguage
  }), [language, theme, t, updateLanguage]);

  return (
    <LanguageContext.Provider value={value}>
      {children}
    </LanguageContext.Provider>
  );
};

