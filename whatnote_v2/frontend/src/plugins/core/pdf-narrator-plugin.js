import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactDOM from 'react-dom';
import ShortcutManager from '../../utils/ShortcutManager';
import { useLanguage } from '../../i18n/LanguageContext';

const NarratorPluginComponent = (props) => {
  const { t } = useLanguage();
  const { windowId, boardId, documentTitle, pageControl } = props;

  const NARRATOR_TOOLBAR_ITEM_STYLE = {
    padding: '1px 8px',
    fontSize: '11px',
    backgroundColor: 'transparent',
    border: '1px solid transparent',
    borderRadius: '0px',
    cursor: 'pointer',
    fontFamily: 'MS Sans Serif, sans-serif',
    height: '20px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#000000',
    marginLeft: '8px'
  };

  const handleNarratorMouseEnter = (e) => {
    if (e.currentTarget.disabled) return;
    e.currentTarget.style.border = '1px outset #ffffff';
    e.currentTarget.style.backgroundColor = '#c0c0c0';
  };

  const handleNarratorMouseLeave = (e) => {
    e.currentTarget.style.border = '1px solid transparent';
    e.currentTarget.style.backgroundColor = 'transparent';
  };

  const handleNarratorMouseDown = (e) => {
    if (e.currentTarget.disabled) return;
    e.currentTarget.style.border = '1px inset #ffffff';
  };

  const handleNarratorMouseUp = (e) => {
    if (e.currentTarget.disabled) return;
    e.currentTarget.style.border = '1px outset #ffffff';
  };

  const [showPanel, setShowPanel] = useState(false);
  const [viewMode, setViewMode] = useState('player'); // 'player' | 'editor' | 'settings'
  const [showSubtitles, setShowSubtitles] = useState(true);
  
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentScript, setCurrentScript] = useState('');
  const [lastSavedScript, setLastSavedScript] = useState(''); // To track changes
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [scripts, setScripts] = useState({}); // { [page]: string } - Cache
  
  const [isGeneratingAudio, setIsGeneratingAudio] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [audioUrls, setAudioUrls] = useState({}); // { [page]: url }
  const [subtitles, setSubtitles] = useState([]); // Current page subtitles
  const [currentSubtitle, setCurrentSubtitle] = useState('');
  const [audioProgress, setAudioProgress] = useState(0);
  const [audioDuration, setAudioDuration] = useState(0);
  
  // 模型管理
  const [gptModels, setGptModels] = useState([]);
  const [sovitsModels, setSovitsModels] = useState([]);
  const [selectedGPT, setSelectedGPT] = useState('');
  const [selectedSoVITS, setSelectedSoVITS] = useState('');
  
  // TTS 设置
  const [ttsProvider, setTtsProvider] = useState('edge');
  const [ttsVoice, setTtsVoice] = useState('zh-CN-XiaoxiaoNeural');
  const [availableVoices, setAvailableVoices] = useState([]);
  const [sovitsUrl, setSovitsUrl] = useState('http://127.0.0.1:9880');
  const [sovitsPath, setSovitsPath] = useState('');
  const [sovitsStatus, setSovitsStatus] = useState('checking'); // 'checking' | 'online' | 'offline'
  
  // 参考音频设置
  const [refText, setRefText] = useState('');
  const [refLang, setRefLang] = useState('zh');
  const [refAudioExists, setRefAudioExists] = useState(false);
  const [refFilename, setRefFilename] = useState('');
  const [audioTimestamp, setAudioTimestamp] = useState(Date.now());
  const [targetLang, setTargetLang] = useState('zh');
  const [narratorLlmModel, setNarratorLlmModel] = useState('qwen-long');
  const [narratorLlmOptions, setNarratorLlmOptions] = useState([]);
  const SUBTITLE_LEAD_SECONDS = 0.2;
  
  // 批量处理状态
  const [isBatchProcessing, setIsBatchProcessing] = useState(false);
  const [batchProgress, setBatchProgress] = useState({ current: 0, total: 0, type: '', message: '' });
  const stopBatchRef = useRef(false);
  const [scriptExportInfo, setScriptExportInfo] = useState({ available: false, count: 0, pages: [] });
  const [exportingScriptFormat, setExportingScriptFormat] = useState(null);

  // 自动演示模式
  const [isAutoMode, setIsAutoMode] = useState(false);
  // 播放模式: 'page_once' | 'page_loop' | 'doc_once' | 'doc_loop'
  const [playbackMode, setPlaybackMode] = useState('doc_once');

  // 提示词设置
  const DEFAULT_PROMPT = `你是一位专业的演讲者。请根据这页 PPT 的内容，为我撰写一份口语化的演讲稿。
要求：
1. 时间控制在 30-60 秒。
2. 语言自然流畅，适合朗读。
3. 不要念标题，而是解释核心观点。
4. 使用第一人称。
5. 【重要】请务必使用规范的标点符号（句号、问号、感叹号）来区分句子，确保没有超长的无标点长句。

请直接输出演讲稿内容，不要包含任何 Markdown 格式或额外说明。`;
  
  const [customPrompt, setCustomPrompt] = useState(DEFAULT_PROMPT);

  const getFallbackVoices = useCallback((provider) => {
    if (provider === 'edge') {
      return [
        { id: 'zh-CN-XiaoxiaoNeural', name: '晓晓 (女声)' },
        { id: 'zh-CN-YunxiNeural', name: '云希 (男声)' },
        { id: 'zh-CN-YunjianNeural', name: '云健 (男声)' },
        { id: 'zh-CN-XiaoyiNeural', name: '晓依 (女声)' },
        { id: 'zh-TW-HsiaoChenNeural', name: '晓臻 (女声-台湾)' },
        { id: 'zh-HK-HiuGaaiNeural', name: '晓佳 (女声-香港)' }
      ];
    }

    if (provider === 'openai') {
      return [
        { id: 'alloy', name: 'Alloy (通用)' },
        { id: 'echo', name: 'Echo (浑厚)' },
        { id: 'fable', name: 'Fable (叙述)' },
        { id: 'onyx', name: 'Onyx (沉稳)' },
        { id: 'nova', name: 'Nova (清亮)' },
        { id: 'shimmer', name: 'Shimmer (柔和)' }
      ];
    }

    return [];
  }, []);

  const fetchTtsConfig = useCallback(async () => {
    try {
      const res = await fetch('http://localhost:8081/api/tts/config');
      if (res.ok) {
        const config = await res.json();
        setTtsProvider(config.provider || 'edge');
        setTtsVoice(config.voice || 'zh-CN-XiaoxiaoNeural');
        setSovitsUrl(config.sovits_url || 'http://127.0.0.1:9880');
        setSovitsPath(config.sovits_path || '');

        checkTTSConnection(config.sovits_url || 'http://127.0.0.1:9880');
      }
    } catch (e) {
      console.error('Failed to fetch TTS config', e);
    }
  }, []);

  // 初始化获取 TTS 配置
  useEffect(() => {
    fetchTtsConfig();
  }, [fetchTtsConfig]);

  useEffect(() => {
    if (ttsProvider === 'gpt-sovits' && viewMode === 'settings') {
      checkTTSConnection(sovitsUrl);
    }
  }, [ttsProvider, viewMode, sovitsUrl]);

  const checkTTSConnection = async (url) => {
    setSovitsStatus('checking');
    try {
        const testUrl = url || sovitsUrl;
        const res = await fetch(`http://localhost:8081/api/tts/test_connection?url=${encodeURIComponent(testUrl)}`);
        const data = await res.json();
        setSovitsStatus(data.success ? 'online' : 'offline');
    } catch (e) {
        setSovitsStatus('offline');
    }
  };

  const handleDetectLocal = async () => {
    if (!sovitsPath) return;
    try {
        const res = await fetch('http://localhost:8081/api/tts/detect_local', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ path: sovitsPath })
        });
        const data = await res.json();
        if (data.success) {
            alert(`检测成功: ${data.message}\n核心指标: ${data.indicators.join(', ')}`);
        } else {
            alert(`检测失败: ${data.message}`);
        }
    } catch (e) {
        alert('检测出错: ' + e.message);
    }
  };

  const [isStartingSovits, setIsStartingSovits] = useState(false);
  const handleStartSovits = async () => {
    setIsStartingSovits(true);
    try {
        const res = await fetch('http://localhost:8081/api/tts/start_local', { method: 'POST' });
        const data = await res.json();
        if (data.success) {
            setSovitsStatus('online');
            fetchModels(); // 启动成功后刷新模型
        } else {
            alert(`启动失败: ${data.message}`);
            setSovitsStatus('offline');
        }
    } catch (e) {
        alert('启动出错: ' + e.message);
        setSovitsStatus('offline');
    } finally {
        setIsStartingSovits(false);
    }
  };

  // 获取音色列表
  useEffect(() => {
    const fetchVoices = async () => {
      try {
        const res = await fetch(`http://localhost:8081/api/tts/voices?provider=${ttsProvider}`);
        if (res.ok) {
          const data = await res.json();
          if (data.success) {
            const voices = data.voices || [];
            setAvailableVoices(voices.length ? voices : getFallbackVoices(ttsProvider));
            return;
          }
        }
        setAvailableVoices(getFallbackVoices(ttsProvider));
      } catch (e) {
        console.error('Failed to fetch voices', e);
        setAvailableVoices(getFallbackVoices(ttsProvider));
      }
    };
    fetchVoices();
  }, [ttsProvider, getFallbackVoices]);

  useEffect(() => {
    if (ttsProvider === 'gpt-sovits') return;
    if (!availableVoices.length) return;

    const hasCurrentVoice = availableVoices.some(v => v.id === ttsVoice);
    if (!hasCurrentVoice) {
      setTtsVoice(availableVoices[0].id);
    }
  }, [ttsProvider, availableVoices, ttsVoice]);

  const audioRef = useRef(null);

  // 快捷键处理
  useEffect(() => {
    const handleKeyDown = (e) => {
      console.log(`[NarratorPlugin] KeyDown: ${e.key}, PanelOpen:${showPanel}`);
      // 只有当面板显示时才处理
      // 或者如果用户希望即使面板关闭也能翻页？通常讲解模式是打开面板的
      // 且当前窗口必须是活动窗口（由 BoardCanvas 处理焦点，但这里无法直接知道是否聚焦）
      // 实际上，事件监听是挂在 window 上的，需要判断是否聚焦了当前 PDF 窗口
      // 但 NarratorPluginComponent 是渲染在 Toolbar 里的，可能拿不到窗口焦点状态
      // 这里的 props 只有 windowId。
      // 简单的判断：如果面板开启 (showPanel)，则接管快捷键
      
      if (!showPanel) return;
      
      const isInputFocused = 
        document.activeElement.tagName === 'INPUT' ||
        document.activeElement.tagName === 'TEXTAREA' ||
        document.activeElement.isContentEditable;
        
      if (isInputFocused) return;

      // 1. 播放/暂停
      if (ShortcutManager.matches('narrator.play_pause', e)) {
        e.preventDefault();
        if (isAutoMode || isPlaying) {
             togglePlay();
        } else {
             // 如果没在播放，尝试开始演示
             startPresentation();
        }
        return;
      }

      // 2. 快退 (Rewind to previous sentence)
      if (ShortcutManager.matches('narrator.rewind', e)) {
        e.preventDefault();
        e.stopPropagation(); 
        
        if (audioRef.current && audioUrl && Number.isFinite(audioRef.current.currentTime)) {
            const currentTime = audioRef.current.currentTime;
            
            // 如果字幕存在，尝试跳转到上一句
            if (subtitles && subtitles.length > 0) {
                // 找到当前正在播放的字幕索引
                // 宽松匹配：只要字幕的开始时间小于等于当前时间，就认为是候选
                // 我们要找最后一个开始时间 <= 当前时间的字幕
                // 由于 subtitles 是按时间排序的，我们可以反向查找或正向查找
                
                let currentIndex = -1;
                for (let i = 0; i < subtitles.length; i++) {
                    if (currentTime >= subtitles[i].start) {
                        currentIndex = i;
                    } else {
                        break; // 之后的字幕还没开始
                    }
                }
                
                if (currentIndex !== -1) {
                    const currentSub = subtitles[currentIndex];
                    // 如果当前播放进度已经超过当前句子开始时间 1秒，则回到当前句首
                    // 否则回到上一句
                    if (currentTime - currentSub.start > 1.0) {
                        audioRef.current.currentTime = currentSub.start;
                    } else {
                        // 回到上一句
                        if (currentIndex > 0) {
                            audioRef.current.currentTime = subtitles[currentIndex - 1].start;
                        } else {
                            audioRef.current.currentTime = 0;
                        }
                    }
                } else {
                    // 当前时间还在第一句之前
                    audioRef.current.currentTime = 0;
                }
            } else {
                // 没有字幕数据，降级为退后 5 秒
                audioRef.current.currentTime = Math.max(0, currentTime - 5);
            }
        }
        return;
      }

      // 3. 快进 (Forward to next sentence)
      if (ShortcutManager.matches('narrator.forward', e)) {
        e.preventDefault();
        e.stopPropagation();
        
        if (audioRef.current && audioUrl && Number.isFinite(audioDuration) && audioDuration > 0) {
            const currentTime = audioRef.current.currentTime;
            
            if (subtitles && subtitles.length > 0) {
                // 找到下一句字幕
                // 即第一个 start > 当前时间的字幕
                const nextSub = subtitles.find(s => s.start > currentTime + 0.1); // 加一点缓冲防止浮点误差原地踏步
                
                if (nextSub) {
                    audioRef.current.currentTime = nextSub.start;
                } else {
                    // 没有下一句了，跳转到最后或 +5s
                    audioRef.current.currentTime = Math.min(audioDuration, currentTime + 5);
                }
            } else {
                // 降级为快进 5 秒
                audioRef.current.currentTime = Math.min(audioDuration, currentTime + 5);
            }
        }
        return;
      }
      
      // 4. PDF 翻页 (如果 BoardCanvas 没有处理，或者这里想覆盖)
      // BoardCanvas 应该处理通用的 PDF 翻页。但如果我们在讲解模式，可能需要特殊的翻页逻辑（如停止播放）
      // Narrator 翻页逻辑：
      if (ShortcutManager.matches('pdf.prev_page', e)) {
          e.preventDefault();
          setIsAutoMode(false);
          if (pageControl && pageControl.goToPreviousPage) pageControl.goToPreviousPage();
          return;
      }
      
      if (ShortcutManager.matches('pdf.next_page', e)) {
          e.preventDefault();
          setIsAutoMode(false);
          if (pageControl && pageControl.goToNextPage) pageControl.goToNextPage();
          return;
      }
    };
    
    // 只在显示面板时监听
    if (showPanel) {
        window.addEventListener('keydown', handleKeyDown);
    }
    
    return () => {
        window.removeEventListener('keydown', handleKeyDown);
    };
  }, [showPanel, isAutoMode, isPlaying, audioUrl, audioDuration, pageControl, subtitles]); // Add subtitles to dependencies

  // 全局监听 'n' 键切换面板，即使面板关闭
  useEffect(() => {
     // 这个监听器需要在任何时候都生效，只要窗口存在
     // 但为了避免所有 PDF 窗口同时响应，我们需要判断焦点
     // 这是一个难点，因为组件不知道自己是否被聚焦。
     // 解决办法：BoardCanvas 传递 isFocused 属性给 renderToolbarButton
     // 目前 PdfNarratorPlugin.renderToolbarButton 没有接收 isFocused
     // 
     // 替代方案：在 window 级别监听，检查 document.activeElement 是否在当前窗口内
     // 或者依赖 BoardCanvas 传递的消息。
     
     // 暂时先只在组件挂载时监听，如果用户有多个 PDF 窗口，按 N 可能会同时打开所有窗口的讲解模式
     // 这是一个已知限制，除非 BoardCanvas 传递 focus 状态。
     
     const handleToggle = (e) => {
         console.log(`[NarratorPlugin] Toggle Check: ${e.key}, Code:${e.code}`);
         // 检查输入框
         const isInputFocused = 
            document.activeElement.tagName === 'INPUT' ||
            document.activeElement.tagName === 'TEXTAREA' ||
            document.activeElement.isContentEditable;
         if (isInputFocused) return;
         
         if (ShortcutManager.matches('pdf.toggle_narrator', e)) {
             // 简单的焦点检查：看当前焦点元素是否在对应的 window div 内
             const windowEl = document.getElementById(`window-${windowId}`);
             if (windowEl && windowEl.contains(document.activeElement)) {
                 e.preventDefault();
                 setShowPanel(prev => !prev);
             } else {
                 // 放宽限制：如果当前没有输入框聚焦，且按下了 n，尝试切换
                 // 为了避免多窗口冲突，理想情况下应该检查是否是当前激活窗口
                 // 但作为插件组件，很难获取全局激活状态。
                 // 既然用户已经在操作这个窗口（虽然焦点可能在 body），我们假设意图是切换当前窗口。
                 // 如果有多个 PDF 窗口，这确实是个问题。
                 // 但考虑到用户体验，先让它能工作。
                 e.preventDefault();
                 setShowPanel(prev => !prev);
             }
         }
     };
     
     window.addEventListener('keydown', handleToggle);
     return () => window.removeEventListener('keydown', handleToggle);
  }, [windowId]);

  // 初始化加载
  useEffect(() => {
    if (boardId && windowId) {
      // 加载缓存的讲稿 (LocalStorage backup)
      const scriptKey = `narrator_scripts_${boardId}_${windowId}`;
      const savedScripts = JSON.parse(localStorage.getItem(scriptKey) || '{}');
      setScripts(savedScripts);

      // 音频 URL 是 Blob URL，刷新页面后会失效。
      // 所以我们虽然保存了 key，但实际上不能直接用。
      // 我们应该只保存“是否有音频”的状态，或者干脆每次都去后端检查
      // 简单起见，我们每次刷新都清空前端的音频 URL 缓存，强制重新从后端获取（后端是文件流，会生成新的 Blob URL）
      setAudioUrls({}); 
      
      // 加载提示词设置
      const savedPrompt = localStorage.getItem('narrator_prompt_template');
      if (savedPrompt) setCustomPrompt(savedPrompt);

      // 加载模型设置
      const savedGPT = localStorage.getItem('narrator_gpt_model');
      if (savedGPT) setSelectedGPT(savedGPT);
      
      const savedSoVITS = localStorage.getItem('narrator_sovits_model');
      if (savedSoVITS) setSelectedSoVITS(savedSoVITS);

      // 加载参考音频设置
      const savedRefText = localStorage.getItem('narrator_ref_text');
      if (savedRefText) setRefText(savedRefText);
      
      const savedRefLang = localStorage.getItem('narrator_ref_lang');
      if (savedRefLang) setRefLang(savedRefLang);

      const savedTargetLang = localStorage.getItem('narrator_target_lang');
      if (savedTargetLang) setTargetLang(savedTargetLang);

      // 从后端同步最新的 reference info (这解决了刷新后看不到之前上传内容的问题)
      fetch('http://localhost:8081/api/tts/reference')
        .then(res => res.json())
        .then(data => {
            setRefAudioExists(data.exists);
            if(data.exists) {
                if(data.text) setRefText(data.text);
                if(data.language) setRefLang(data.language);
                if(data.filename) setRefFilename(data.filename);
                // 如果本地没存，顺便存一下
                localStorage.setItem('narrator_ref_text', data.text || '');
                localStorage.setItem('narrator_ref_lang', data.language || 'zh');
            }
        })
        .catch(e => console.warn('Failed to sync ref audio info', e));

      fetch('http://localhost:8081/api/narrator/llm-model')
        .then((res) => (res.ok ? res.json() : null))
        .then((data) => {
          if (data?.model) setNarratorLlmModel(data.model);
          if (Array.isArray(data?.options)) setNarratorLlmOptions(data.options);
        })
        .catch((e) => console.warn('Failed to load narrator LLM model', e));
    }
  }, [boardId, windowId]);

  const fetchScriptExportInfo = useCallback(async () => {
    if (!boardId || !windowId) return;
    try {
      const res = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/export-script-status`);
      if (res.ok) {
        const data = await res.json();
        setScriptExportInfo(data || { available: false, count: 0, pages: [] });
      }
    } catch (e) {
      console.warn('Failed to fetch narrator script export status', e);
    }
  }, [boardId, windowId]);

  useEffect(() => {
    if (showPanel) {
      fetchScriptExportInfo();
    }
  }, [showPanel, fetchScriptExportInfo]);

  const handleExportScript = useCallback(async (format) => {
    if (!boardId || !windowId || exportingScriptFormat) return;

    const endpoint = format === 'markdown' ? 'export-script-markdown' : 'export-script-pdf';
    const suffix = format === 'markdown' ? '.md' : '.pdf';
    const defaultStem = (() => {
      const rawTitle = documentTitle || '';
      if (!rawTitle) return 'document';
      return rawTitle.replace(/\.[^.]+$/, '') || 'document';
    })();
    const fallbackFilename = `${defaultStem}-讲稿${suffix}`;

    setExportingScriptFormat(format);
    try {
      const response = await fetch(
        `http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/${endpoint}`
      );
      if (!response.ok) {
        let detail = '导出失败';
        try {
          const err = await response.json();
          detail = err.detail || detail;
        } catch (_) {
          detail = await response.text() || detail;
        }
        throw new Error(detail);
      }

      const blob = await response.blob();
      const disposition = response.headers.get('Content-Disposition') || '';
      let filename = fallbackFilename;
      const utf8Match = disposition.match(/filename\*=UTF-8''([^;]+)/i);
      const quotedMatch = disposition.match(/filename="([^"]+)"/i);
      if (utf8Match?.[1]) {
        try {
          filename = decodeURIComponent(utf8Match[1]);
        } catch (_) {
          filename = utf8Match[1];
        }
      } else if (quotedMatch?.[1]) {
        filename = quotedMatch[1];
      }

      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error(`导出 ${format} 讲稿失败`, e);
      alert((format === 'markdown' ? t('pdf_outline_export_script_md_error') : t('pdf_outline_export_script_error')) + (e.message || 'Unknown error'));
    } finally {
      setExportingScriptFormat(null);
    }
  }, [boardId, windowId, documentTitle, exportingScriptFormat, t]);

  const localScriptPages = Object.entries(scripts)
    .filter(([, content]) => (content || '').trim())
    .map(([page]) => Number(page));
  const exportableScriptPages = Array.from(new Set([
    ...(scriptExportInfo.pages || []),
    ...localScriptPages,
    ...(currentScript && currentScript.trim() ? [pageControl?.currentPage] : [])
  ].filter(Boolean))).sort((a, b) => a - b);
  const totalNarratorPages = pageControl?.totalPages || 0;
  const missingScriptPages = totalNarratorPages > 0
    ? Array.from({ length: totalNarratorPages }, (_, i) => i + 1).filter(page => !exportableScriptPages.includes(page))
    : [];
  const hasFullScriptCoverage = totalNarratorPages > 0 && missingScriptPages.length === 0;
  const canExportScripts = hasFullScriptCoverage && !isBatchProcessing && !isGenerating && !exportingScriptFormat;

  // 加载模型列表
  const fetchModels = useCallback(() => {
      fetch('http://localhost:8081/api/tts/models')
        .then(res => res.json())
        .then(data => {
            setGptModels(data.gpt_weights || []);
            setSovitsModels(data.sovits_weights || []);
            if(data.error) console.warn(data.error);
        })
        .catch(console.error);
  }, []);

  useEffect(() => {
      if (viewMode === 'settings') {
          fetchModels();
      }
  }, [viewMode, fetchModels]);

  const changeModel = async (type, value) => {
      if (type === 'gpt') setSelectedGPT(value);
      else setSelectedSoVITS(value);
      
      try {
          await fetch('http://localhost:8081/api/tts/set_model', {
              method: 'POST',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({
                  gpt_model: type === 'gpt' ? value : selectedGPT,
                  sovits_model: type === 'sovits' ? value : selectedSoVITS
              })
          });
      } catch (e) {
          console.error('切换模型失败:', e);
          alert(t('narrator_switch_fail'));
      }
  };

  // 加载当前页数据 (优先从后端获取讲稿)
  useEffect(() => {
    if (showPanel && pageControl) {
      const page = pageControl.currentPage;
      
      // 1. 获取讲稿
      fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/scripts/${page}`)
        .then(res => res.json())
        .then(data => {
            if (data.success && data.content) {
                setCurrentScript(data.content);
                setLastSavedScript(data.content);
                setScripts(prev => ({...prev, [page]: data.content}));
                
                // 1.5 获取字幕
                fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/subtitles/${page}`)
                    .then(r => r.json())
                    .then(d => {
                        if(d.subtitles) setSubtitles(d.subtitles);
                        else setSubtitles([]);
                    })
                    .catch(() => setSubtitles([]));
                
                // 2. 如果有讲稿，尝试检查/获取音频
                if (!audioUrls[page]) {
                    fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/audio/${page}`, {
                        method: 'GET'
                    })
                    .then(async (res) => {
                        if (res.ok) {
                            const blob = await res.blob();
                            const url = URL.createObjectURL(blob);
                            setAudioUrls(prev => ({ ...prev, [page]: url }));
                        }
                    })
                    .catch(e => console.warn('静默加载音频失败(可能未生成)', e));
                }
            } else {
                const cached = scripts[page] || '';
                setCurrentScript(cached);
                setLastSavedScript(cached);
            }
        })
        .catch(() => {
            const cached = scripts[page] || '';
            setCurrentScript(cached);
            setLastSavedScript(cached);
        });
    }
  }, [pageControl?.currentPage, showPanel, boardId, windowId]);

  // Sync audioUrl with current page's audio
  useEffect(() => {
      if (pageControl) {
          const page = pageControl.currentPage;
      const url = audioUrls[page];
          if (url !== audioUrl) {
      setAudioUrl(url || null);
          }
      }
  }, [audioUrls, pageControl?.currentPage, audioUrl]);

  // Audio Playback Control Effect
  useEffect(() => {
      const audio = audioRef.current;
      if (!audio) return;

      if (audioUrl) {
          // Sync src
          if (audio.src !== audioUrl) {
              audio.src = audioUrl;
              audio.load();
          }
          
          // Handle Auto Play
          if (isAutoMode) {
              // If we are in auto mode, we should be playing
              if (audio.paused) {
                  const p = audio.play();
                  if (p !== undefined) {
                      p.then(() => setIsPlaying(true))
                       .catch(e => {
                          console.warn("Auto-play failed", e);
                          // Optional: keep isAutoMode true to retry or let user intervene
                          setIsPlaying(false);
                      });
                  }
              }
              } else {
              // If not in auto mode, we should pause
              if (!audio.paused) {
                  audio.pause();
                  }
                  setIsPlaying(false);
              }
          } else {
          audio.removeAttribute('src');
              setIsPlaying(false);
          }
  }, [audioUrl, isAutoMode]);

  useEffect(() => {
      const audio = audioRef.current;
      if (!audio || !audioUrl) return;

      const syncSubtitle = () => {
          const currentTime = Math.max(0, (audio.currentTime || 0) + SUBTITLE_LEAD_SECONDS);
          const duration = Number.isFinite(audio.duration) ? audio.duration : 0;
          setAudioProgress(audio.currentTime || 0);
          if (duration) setAudioDuration(duration);

          if (subtitles && subtitles.length > 0) {
              const sub = subtitles.find(s => currentTime >= s.start && currentTime <= s.end);
              setCurrentSubtitle(sub ? sub.text : '');
          } else {
              setCurrentSubtitle('');
          }
      };

      syncSubtitle();
      const intervalId = window.setInterval(syncSubtitle, 50);
      return () => window.clearInterval(intervalId);
  }, [audioUrl, subtitles, SUBTITLE_LEAD_SECONDS]);

  // 自动保存讲稿
  useEffect(() => {
      if (!showPanel || !pageControl) return;
      const page = pageControl.currentPage;
      
      // Debounce save
      const timer = setTimeout(() => {
          if (currentScript !== lastSavedScript) {
              // Save to Backend
              fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/scripts/${page}`, {
                  method: 'PUT',
                  headers: {'Content-Type': 'application/json'},
                  body: JSON.stringify({ content: currentScript })
              }).then(res => res.json()).then(d => {
                  if(d.success) {
                      setLastSavedScript(currentScript);
                      // Update Cache
                      setScripts(prev => ({...prev, [page]: currentScript}));
                      const scriptKey = `narrator_scripts_${boardId}_${windowId}`;
                      const saved = JSON.parse(localStorage.getItem(scriptKey) || '{}');
                      saved[page] = currentScript;
                      localStorage.setItem(scriptKey, JSON.stringify(saved));
                  }
              }).catch(e => console.error('Auto-save failed', e));
          }
      }, 1000);
      
      return () => clearTimeout(timer);
  }, [currentScript, lastSavedScript, pageControl?.currentPage, boardId, windowId, showPanel]);

  // SSE 任务执行辅助函数
  const runSSETask = async (url, onProgress) => {
      const res = await fetch(url, { method: 'POST' });
      if (!res.ok) throw new Error(`Task failed: ${res.status}`);
      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      while(true) {
          const {done, value} = await reader.read();
          if (done) break;
          const chunk = decoder.decode(value, {stream:true});
          const lines = chunk.split('\n\n');
          for(const line of lines) {
               if(line.startsWith('data: ')) {
                   try {
                       const d = JSON.parse(line.substring(6));
                       if(onProgress) onProgress(d);
                       if(d.type === 'error') throw new Error(d.error);
                   } catch(e) { if(e.message.includes('Task failed')) throw e; }
               }
          }
      }
  };

  // 核心：生成单页讲稿 (返回 Promise)
  const fetchScriptForPage = async (page) => {
    const prevScript = scripts[page - 1] || '';
    const nextScript = scripts[page + 1] || '';

    // 使用专用接口，避免污染注释
    const response = await fetch(
      `http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/script-generate/${page}`,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            promptTemplate: customPrompt,
            previous_script: prevScript,
            next_script: nextScript
        })
      }
    );

    if (!response.ok) throw new Error(`API Error: ${response.status}`);

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let fullText = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      const lines = chunk.split('\n\n');
      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.substring(6));
            if (data.content) fullText += data.content;
          } catch (e) {}
        }
      }
    }
    return fullText;
  };

  const fetchAudioForText = async (text) => {
    const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/audio/${pageControl.currentPage}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: text,
        prompt_text: refText || "", 
        prompt_lang: refLang || "zh",
        text_language: targetLang
      })
    });
    
    if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || 'TTS Failed');
    }
    
    const data = await response.json();
    return data; // { success, audio_url, subtitles }
  };

  // 批量处理
  const startBatch = async (type) => {
    if (!boardId || !windowId) return;
    if (isBatchProcessing) {
        stopBatchRef.current = true;
        return;
    }

    // Removed popup confirmation
    // const total = pageControl.totalPages;
    // if (!window.confirm(`确定要为所有 ${total} 页生成${type === 'script' ? '讲稿' : '语音'}吗？\n这可能需要几分钟，请保持页面开启。`)) return;
    const total = pageControl.totalPages;

    setIsBatchProcessing(true);
    stopBatchRef.current = false;
    setBatchProgress({ current: 0, total, type, message: t('narrator_preparing') });

    try {
      if (type === 'script' || type === 'script-missing') {
          const prefix = type === 'script-missing' ? t('narrator_batch_prefix_fill') : t('narrator_batch_prefix_batch');
          setBatchProgress({ current: 0, total, type: 'script', message: t('narrator_batch_start_script').replace('{prefix}', prefix) });
          
          let outlineData = null;
          let subdivisionData = null;
          try {
              const res = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/outline-data`);
              if (res.ok) outlineData = await res.json();
          } catch(e) {}

          if (!outlineData || !outlineData.outline) {
              setBatchProgress({ current: 0, total: 100, type: 'analyzing', message: t('narrator_analyzing_outline') });
              try {
                  await runSSETask(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/outline`, (d) => {
                      if (d.type === 'status') setBatchProgress(p => ({...p, message: d.message}));
                  });
                  outlineData = await (await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/outline-data`)).json();
                  
                  // 触发主界面刷新大纲侧栏
                  window.dispatchEvent(new Event('refreshBoard'));
              } catch (err) {
                  console.error('大纲分析失败', err);
              }
          }

          try {
              const res = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/subdivision-data`);
              if (res.ok) subdivisionData = await res.json();
          } catch(e) {}

          if ((!subdivisionData || !subdivisionData.subdivisions) && outlineData && outlineData.outline) {
              setBatchProgress({ current: 0, total: 100, type: 'analyzing', message: t('narrator_subdividing') });
              try {
                  await runSSETask(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/subdivide`, (d) => {
                      if (d.type === 'status') setBatchProgress(p => ({...p, message: d.message}));
                  });
                  subdivisionData = await (await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/subdivision-data`)).json();
                  
                  // 再次触发刷新以更新细分数据
                  window.dispatchEvent(new Event('refreshBoard'));
              } catch (err) {
                  console.error('细分分析失败', err);
              }
          }

          let sections = outlineData?.outline || [];
          if (sections.length === 0) {
              const chunkSize = 5;
              for (let i = 1; i <= total; i += chunkSize) {
                  sections.push({
                      section_index: Math.floor((i-1)/chunkSize),
                      page_start: i,
                      page_end: Math.min(i + chunkSize - 1, total),
                      title: `Pages ${i}-${Math.min(i + chunkSize - 1, total)}`
                  });
              }
          }

          // Parallel Processing for Scripts
          const CONCURRENCY = 3; 
          let sectionCursor = 0;
          
          // 预处理：计算每个分段的“生成目标范围”（去重且补漏）
          // 规则：确保覆盖从 1 到 total 的所有页面，填补分段间的空隙
          sections.forEach((section, idx) => {
              let targetStart = section.page_start;
              // const targetEnd = section.page_end; // Use mutable let if needed, but we write to section property
              
              if (idx === 0) {
                  targetStart = 1;
              } else {
                  const prevSection = sections[idx - 1];
                  // 强制接续上一分段，填补空隙
                  targetStart = Math.max(targetStart, prevSection.target_page_end + 1);
                  // 如果存在空隙 (prevEnd < targetStart - 1)，将起始点前移以覆盖空隙
                  // 简单做法：总是从 prevEnd + 1 开始
                  targetStart = prevSection.target_page_end + 1;
              }
              
              section.target_page_start = targetStart;
              // 保持原有的结束页，除非它是最后一个
              section.target_page_end = section.page_end;
          });

          // 确保最后一个分段覆盖到最后一页
          if (sections.length > 0) {
              const lastSection = sections[sections.length - 1];
              if (lastSection.target_page_end < total) {
                  lastSection.target_page_end = total;
              }
          }

          console.log('[Narrator] Batch Sections Plan:', sections.map(s => 
            `[${s.section_index}] ${s.target_page_start}-${s.target_page_end} (Orig: ${s.page_start}-${s.page_end})`
          ));

          const processSection = async () => {
              while (sectionCursor < sections.length) {
                  if (stopBatchRef.current) break;
                  const index = sectionCursor++;
                  const section = sections[index];
                  
                  console.log(`[Narrator] Processing batch section ${index}:`, section);
                  
                  // 如果目标范围无效（例如完全被上一分段包含），则跳过
                  if (section.target_page_start > section.target_page_end) {
                      setBatchProgress(prev => ({
                           ...prev, 
                           current: Math.min(section.page_end, prev.total),
                           message: t('narrator_skip_section').replace('{index}', index + 1)
                      }));
                      continue;
                  }

                  // 确定本次需要生成的具体范围列表
                  let targetRanges = [];
                  if (type === 'script-missing') {
                      // 查找空白页面的区间
                      let currentStart = -1;
                      // 确保循环覆盖整个目标范围
                      for (let p = section.target_page_start; p <= section.target_page_end; p++) {
                          const hasContent = scripts[p] && scripts[p].trim().length > 0;
                          if (!hasContent) {
                              if (currentStart === -1) currentStart = p;
                          } else {
                              if (currentStart !== -1) {
                                  targetRanges.push({ start: currentStart, end: p - 1 });
                                  currentStart = -1;
                              }
                          }
                      }
                      if (currentStart !== -1) {
                          targetRanges.push({ start: currentStart, end: section.target_page_end });
                      }
                      console.log(`[Narrator] Missing ranges for section ${index}:`, targetRanges);
                  } else {
                      // 默认模式：生成整个目标范围
                      targetRanges.push({ start: section.target_page_start, end: section.target_page_end });
                  }

                  if (targetRanges.length === 0) {
                      setBatchProgress(prev => ({
                          ...prev,
                          current: Math.min(section.target_page_end, prev.total),
                          message: t('narrator_skip_completed_section').replace('{title}', section.title || (index + 1))
                      }));
                      continue;
                  }

                  // 针对每个子范围进行调用
                  for (const range of targetRanges) {
                      if (stopBatchRef.current) break;

                  // Avoid rapid state updates for progress to prevent UI jitter
                  setBatchProgress({ 
                          current: range.start, 
                      total: total, 
                      type: 'script',
                          message: t('narrator_generating')
                            .replace('{title}', section.title || `Part ${index+1}`)
                            .replace('{range}', `${range.start}-${range.end}`)
                  });

                  try {
                      const response = await fetch(
                          `http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/generate-script-section`,
                          {
                              method: 'POST',
                              headers: { 'Content-Type': 'application/json' },
                              body: JSON.stringify({
                                  section_index: index,
                                  section_data: section,
                                  target_range: {
                                          start: range.start,
                                          end: range.end
                                  },
                                  subdivision_data: subdivisionData?.subdivisions?.[index],
                                  // 发送所有之前的分段摘要，构建完整的上下文链
                                  context_history: subdivisionData?.subdivisions?.slice(0, index)?.map(s => ({
                                      title: s?.title || "",
                                      summary: s?.section_summary || ""
                                  })) || [],
                                  promptTemplate: customPrompt
                              })
                          }
                      );

                      if (response.ok) {
                          const reader = response.body.getReader();
                          const decoder = new TextDecoder();
                          while (true) {
                              const { done, value } = await reader.read();
                              if (done) break;
                              const chunk = decoder.decode(value, { stream: true });
                              const lines = chunk.split('\n\n');
                              for (const line of lines) {
                                  if (line.startsWith('data: ')) {
                                      try {
                                          const data = JSON.parse(line.substring(6));
                                          if (data.type === 'page_done') {
                                              const { page, content } = data;
                                              
                                              // Async save
                                              fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/scripts/${page}`, {
                                                  method: 'PUT',
                                                  headers: {'Content-Type': 'application/json'},
                                                  body: JSON.stringify({ content: content })
                                              }).catch(console.error);
                                              
                                              // React state update
                                              setScripts(prev => ({ ...prev, [page]: content }));

                                              // If it's current page
                                              if (page === pageControl.currentPage) {
                                                  setCurrentScript(content);
                                                  setLastSavedScript(content);
                                              }
                                              
                                              // Persist
                                              try {
                                                      const storageKey = `narrator_scripts_${boardId}_${windowId}`;
                                                  const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
                                                  saved[page] = content;
                                                  localStorage.setItem(storageKey, JSON.stringify(saved));
                                              } catch(e) {}

                                              setBatchProgress(prev => ({ ...prev, current: page }));
                                          } else if (data.type === 'complete') {
                                              const missing = data.missing_pages || [];
                                              if (missing.length > 0) {
                                                  console.warn(`[BatchScript] 分段 ${index} 生成不完整，缺失页面:`, missing);
                                              }
                                              setBatchProgress(prev => ({ 
                                                  ...prev, 
                                                  message: missing.length > 0 ? t('narrator_batch_missing').replace('{pages}', missing.join(', ')) : t('narrator_batch_complete') 
                                              }));
                                          }
                                      } catch (e) {}
                                  }
                              }
                          }
                      }
                  } catch (err) { console.error(err); }
                  }
              }
          };

          const workers = Array(Math.min(sections.length, CONCURRENCY)).fill(null).map(() => processSection());
          await Promise.all(workers);

      } else if (type === 'audio' || type === 'audio-missing') {
        const prefix = type === 'audio-missing' ? t('narrator_batch_prefix_fill') : t('narrator_batch_prefix_batch');
        setBatchProgress({ current: 0, total, type: 'audio', message: t('narrator_batch_start_audio').replace('{prefix}', prefix) });
        
        for (let i = 1; i <= total; i++) {
            if (stopBatchRef.current) break;
            
            // Check if missing logic applies
            if (type === 'audio-missing') {
                let skip = false;
                // 1. Check Frontend Cache first
                if (audioUrls[i]) {
                    skip = true;
                } 
                
                // 2. Check Backend Existence via HEAD request
                if (!skip) {
                    try {
                        const res = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/audio/${i}`, { method: 'HEAD' });
                        if (res.ok) {
                            // Audio exists on backend!
                            // Load it into frontend state so we don't check again, and skip generation
                            const audioRes = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/audio/${i}`);
                            const blob = await audioRes.blob();
                            const url = URL.createObjectURL(blob);
                            setAudioUrls(prev => ({ ...prev, [i]: url }));
                            skip = true;
                        }
                    } catch(e) {}
                }

                if (skip) {
                    // Update progress without generating
                    setBatchProgress(prev => ({ ...prev, current: i, message: t('narrator_skipping').replace('{page}', i) }));
                    // Use a very short timeout to keep UI responsive but fast
                    await new Promise(r => setTimeout(r, 50)); 
                    continue; 
                }
            }

            try {
                let text = scripts[i];
                if (!text) {
                    const res = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/scripts/${i}`);
                    const d = await res.json();
                    if(d.success && d.content) text = d.content;
                }

                // Only generate if we have text
                if (text) {
                   setBatchProgress(prev => ({ ...prev, current: i, message: t('narrator_synthesizing').replace('{page}', i) }));
                   
                   // Call same endpoint
                   const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/audio/${i}`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        text: text,
                        prompt_text: refText || "",
                        prompt_lang: refLang || "zh",
                        text_language: targetLang || "zh"
                      })
                   });
                   const resData = await response.json();
                   if(resData.success && resData.audio_url) {
                       const audioRes = await fetch(`http://localhost:8081${resData.audio_url}`);
                       const blob = await audioRes.blob();
                       const url = URL.createObjectURL(blob);
                       setAudioUrls(prev => ({ ...prev, [i]: url }));
                   }
                }
            } catch (err) {
              console.error(`Page ${i} batch audio error:`, err);
            }
            setBatchProgress(prev => ({ ...prev, current: i }));
            await new Promise(r => setTimeout(r, 1000));
        }
      }
    } finally {
      setIsBatchProcessing(false);
      stopBatchRef.current = false;
    }
  };

  // 单页生成讲稿
  const generateScript = async () => {
    if (!boardId || !windowId || !pageControl) return;
    const page = pageControl.currentPage;
    setIsGenerating(true);
    setCurrentScript(t('narrator_generating_script_status'));

    try {
        const text = await fetchScriptForPage(page);
        
        // Save to Backend
        await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/scripts/${page}`, {
            method: 'PUT',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({ content: text })
        });

        const storageKey = `narrator_scripts_${boardId}_${windowId}`;
        const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
        saved[page] = text;
        localStorage.setItem(storageKey, JSON.stringify(saved));
        setScripts(prev => ({ ...prev, [page]: text }));
        setCurrentScript(text);
        setLastSavedScript(text);
    } catch (error) {
        console.error(error);
        setCurrentScript(t('narrator_gen_error').replace('{error}', error.message));
    } finally {
        setIsGenerating(false);
    }
  };

  // 单页生成语音
  const generateAudio = async () => {
    // if (!currentScript) { alert('请先生成讲稿'); return; }
    if (!currentScript) return; // Fail silently or rely on UI state (button disabled)
    
    setIsGeneratingAudio(true);
    try {
        const resData = await fetchAudioForText(currentScript);
        if(!resData.success) throw new Error('Generation failed');
        
        // Fetch Blob
        const audioRes = await fetch(`http://localhost:8081${resData.audio_url}`);
        const blob = await audioRes.blob();
        const url = URL.createObjectURL(blob);
        const subs = resData.subtitles || [];
        
        const page = pageControl.currentPage;
        
        setAudioUrls(prev => ({ ...prev, [page]: url }));
        setAudioUrl(url);
        setSubtitles(subs);
        
        setIsAutoMode(true);
    } catch (e) {
        alert('语音生成失败: ' + e.message);
    } finally {
        setIsGeneratingAudio(false);
    }
  };

  const togglePlay = () => {
    if (audioRef.current && audioUrl) {
      if (isAutoMode) {
        setIsAutoMode(false);
      } else {
        setIsAutoMode(true);
      }
    }
  };

  const startPresentation = () => {
      if (!audioUrl) {
          alert(t('narrator_no_audio_alert'));
          return;
      }
      setIsAutoMode(true);
  };

  const togglePlaybackMode = () => {
      const modes = ['page_once', 'page_loop', 'doc_once', 'doc_loop'];
      const nextIndex = (modes.indexOf(playbackMode) + 1) % modes.length;
      setPlaybackMode(modes[nextIndex]);
  };

  const getPlaybackModeIcon = () => {
      switch(playbackMode) {
          case 'page_once': return t('narrator_mode_page_once');
          case 'page_loop': return t('narrator_mode_page_loop');
          case 'doc_once': return t('narrator_mode_doc_once');
          case 'doc_loop': return t('narrator_mode_doc_loop');
          default: return '⏩';
      }
  };

  const saveSettingsToLocal = () => {
      localStorage.setItem('narrator_prompt_template', customPrompt);
      localStorage.setItem('narrator_gpt_model', selectedGPT);
      localStorage.setItem('narrator_sovits_model', selectedSoVITS);
      localStorage.setItem('narrator_ref_text', refText);
      localStorage.setItem('narrator_ref_lang', refLang);
      localStorage.setItem('narrator_target_lang', targetLang);
  };

  const handleSaveSettings = async () => {
      saveSettingsToLocal();

      if (narratorLlmModel) {
        try {
          const res = await fetch('http://localhost:8081/api/narrator/llm-model', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ model: narratorLlmModel }),
          });
          if (!res.ok) {
            const err = await res.json().catch(() => ({}));
            console.error('Failed to save narrator LLM model', err.detail || res.statusText);
          }
        } catch (e) {
          console.error('Failed to save narrator LLM model', e);
        }
      }
      
      // 保存 TTS 配置到后端
      try {
          await fetch('http://localhost:8081/api/tts/config', {
              method: 'PUT',
              headers: {'Content-Type': 'application/json'},
              body: JSON.stringify({
                  provider: ttsProvider,
                  voice: ttsVoice,
                  sovits_url: sovitsUrl,
                  sovits_path: sovitsPath
              })
          });
      } catch (e) {
          console.error("Failed to save TTS config", e);
      }

      // Sync reference metadata to backend
      if (refAudioExists) {
          try {
              await fetch('http://localhost:8081/api/tts/reference', {
                  method: 'PUT',
                  headers: {'Content-Type': 'application/json'},
                  body: JSON.stringify({
                      text: refText,
                      language: refLang
                  })
              });
          } catch(e) {
              console.error("Failed to sync reference settings to backend", e);
          }
      }

      // 切换 TTS 服务后，当前页旧音频会失效；清掉缓存并删除当前页成品，避免继续播放旧的 Edge 音频。
      try {
          if (audioRef.current) {
              audioRef.current.pause();
              audioRef.current.removeAttribute('src');
              audioRef.current.load();
          }
          setIsAutoMode(false);
          setIsPlaying(false);
          setCurrentSubtitle('');
          setAudioProgress(0);
          setAudioDuration(0);
          setAudioUrl(null);
          setAudioUrls({});
          setSubtitles([]);

          if (boardId && windowId && pageControl?.currentPage) {
              await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/audio/${pageControl.currentPage}`, {
                  method: 'DELETE'
              });
          }

          await fetchTtsConfig();
      } catch (e) {
          console.error("Failed to refresh TTS state after saving settings", e);
      }

      setViewMode('player');
  };

  const handleUploadRef = async (file) => {
    // 直接上传音频，不检查文本
    const formData = new FormData();
    formData.append('file', file);
    // 如果还没填文本，就传空字符串，后端不应该报错
    formData.append('text', refText || ""); 
    formData.append('language', refLang); 

    try {
        const res = await fetch('http://localhost:8081/api/tts/reference', {
            method: 'POST',
            body: formData
        });
        const data = await res.json();
        if (data.success) {
            setRefAudioExists(true);
            setRefFilename(file.name);
            setAudioTimestamp(Date.now());
            // 上传成功后，如果 text 是空的，前端给个提示让用户去填，但不要弹窗阻断
            if (!refText || !refText.trim()) {
               // 可以用一个状态显示“请填写文本”的提示，或者直接聚焦到文本框
               // 这里简化处理，不做强提示，因为用户马上就会去填
            }
            // 自动保存设置（虽然 text 可能是空的，但音频已经上去了）
            saveSettingsToLocal();
            // alert('参考音频上传成功！请确保在下方文本框中输入该音频对应的文字内容。');
        }
        else alert(t('narrator_upload_fail').replace('{error}', data.detail || 'Unknown error'));
    } catch (e) {
        alert(t('narrator_upload_error').replace('{error}', e.message));
    }
  };

  const checkTTSStatus = async () => {
    try {
        const res = await fetch('http://localhost:8081/api/tts/status');
        const data = await res.json();
        alert(t('narrator_status_alert').replace('{status}', data.status).replace('{error}', data.error || ''));
    } catch (e) {
        alert(t('narrator_conn_error'));
    }
  };

  const formatTime = (seconds) => {
      if (!seconds) return "00:00";
      const m = Math.floor(seconds / 60);
      const s = Math.floor(seconds % 60);
      return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  // 计算当前应该显示的高度
  const calculateHeight = () => {
    if (viewMode === 'settings') {
      return 300; // 设置模式固定高度
    } else {
      // 播放模式
      if (!showSubtitles) {
        return 100; // 关闭字幕时紧凑高度
      } else {
        return 180; // 开启字幕时标准高度
      }
    }
  };

  // 获取Portal容器
  const containerId = `pdf-plugin-bottom-panel-${windowId}`;
  const container = document.getElementById(containerId);

  return (
    <>
      <button
        onClick={() => setShowPanel(!showPanel)}
        style={{
          ...NARRATOR_TOOLBAR_ITEM_STYLE,
          backgroundColor: showPanel ? '#a0a0a0' : 'transparent',
          minWidth: '50px'
        }}
        onMouseEnter={handleNarratorMouseEnter}
        onMouseLeave={handleNarratorMouseLeave}
        onMouseDown={handleNarratorMouseDown}
        onMouseUp={handleNarratorMouseUp}
        title={t('narrator_btn_title')}
      >
        {t('narrator_btn')}
      </button>
      
      {showPanel && container && ReactDOM.createPortal(
          <div style={{
            width: '100%',
            height: `${calculateHeight()}px`,
            position: 'static',
            backgroundColor: '#c0c0c0',
            borderTop: '2px outset #ffffff',
            fontFamily: 'MS Sans Serif, sans-serif',
            fontSize: '12px',
            display: 'flex',
            flexDirection: 'column',
            overflow: 'hidden'
          }}>
            {/* 移除了之前无效的高度调整控制条 */}
            
            {/* --- VIEW: SETTINGS --- */}
            {viewMode === 'settings' && (
               <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '8px', overflowY: 'auto' }}>
                   <div style={{display:'flex', justifyContent:'space-between', marginBottom:'8px', alignItems:'center'}}>
                       <span style={{fontWeight:'bold', color: '#000080'}}>{t('narrator_settings')}</span>
                       <button onClick={() => setViewMode('player')}>{t('narrator_back')}</button>
                   </div>
                   
                   <div style={{ border: '1px dotted #888', padding: '4px', marginBottom: '8px', backgroundColor: '#fff' }}>
                     <div style={{ fontWeight: 'bold', fontSize: '11px', color: '#000080', marginBottom: '4px' }}>
                       {t('narrator_llm_model_label')}
                     </div>
                     <select
                       value={narratorLlmModel}
                       onChange={(e) => setNarratorLlmModel(e.target.value)}
                       style={{ width: '100%', fontSize: '11px' }}
                     >
                       {(narratorLlmOptions.length ? narratorLlmOptions : [
                         { value: 'qwen-long', label: 'qwen-long' },
                         { value: 'qwen-plus', label: 'qwen-plus' },
                         { value: 'qwen3.5-plus', label: 'qwen3.5-plus' },
                       ]).map((opt) => (
                         <option key={opt.value} value={opt.value}>{opt.label}</option>
                       ))}
                     </select>
                     <div style={{ fontSize: '10px', color: '#666', marginTop: '4px', lineHeight: 1.4 }}>
                       {t('narrator_llm_model_hint')}
                     </div>
                   </div>

                   <div style={{fontWeight: 'bold', color: '#444', marginBottom:'2px'}}>{t('narrator_prompt_label')}</div>
                       <textarea 
                           value={customPrompt}
                           onChange={(e) => setCustomPrompt(e.target.value)}
                           style={{ 
                               height: '80px', 
                               minHeight: '80px',
                               width: '100%', 
                               resize: 'vertical', 
                               marginBottom:'8px', 
                               fontSize:'11px',
                               flexShrink: 0,
                               border: '1px inset #888',
                               padding: '4px'
                           }}
                       />
                   
                   <div style={{display:'flex', gap:'10px', marginBottom: '8px'}}>
                       <div style={{flex:1, border:'1px dotted #888', padding:'4px', backgroundColor:'#ece9d8'}}>
                            <div style={{fontWeight:'bold', fontSize:'11px', color:'#000080', marginBottom:'4px', display:'flex', justifyContent:'space-between'}}>
                                <span>TTS 服务设置</span>
                                {ttsProvider === 'gpt-sovits' && (
                                    <span style={{
                                        fontSize:'9px', 
                                        color: sovitsStatus === 'online' ? '#008000' : (sovitsStatus === 'checking' ? '#808000' : '#ff0000')
                                    }}>
                                        ● {sovitsStatus === 'online' ? '已连接' : (sovitsStatus === 'checking' ? '正在连接...' : '未连接')}
                                    </span>
                                )}
                            </div>
                            <div style={{display:'flex', flexDirection:'column', gap:'4px'}}>
                                <div style={{display:'flex', alignItems:'center', gap:'4px'}}>
                                    <span style={{fontSize:'10px', width:'50px'}}>服务商:</span>
                                    <select 
                                        value={ttsProvider} 
                                        onChange={e => setTtsProvider(e.target.value)}
                                        style={{flex:1, fontSize:'11px'}}
                                    >
                                        <option value="edge">Edge TTS (在线/免费)</option>
                                        <option value="openai">OpenAI TTS (在线/收费)</option>
                                        <option value="gpt-sovits">GPT-SoVITS (本地/克隆)</option>
                                    </select>
                                </div>
                                
                                {ttsProvider === 'gpt-sovits' ? (
                                    <>
                                        <div style={{display:'flex', alignItems:'center', gap:'4px'}}>
                                            <span style={{fontSize:'10px', width:'50px'}}>API 地址:</span>
                                            <input 
                                                type="text" 
                                                value={sovitsUrl} 
                                                onChange={e => setSovitsUrl(e.target.value)}
                                                placeholder="http://127.0.0.1:9880"
                                                style={{flex:1, fontSize:'10px', padding:'1px 3px'}}
                                            />
                                            <button 
                                                onClick={() => checkTTSConnection(sovitsUrl)}
                                                style={{fontSize:'9px', padding:'1px 4px'}}
                                            >测试</button>
                                            {sovitsStatus === 'offline' && sovitsPath && (
                                                <button 
                                                    onClick={handleStartSovits}
                                                    disabled={isStartingSovits}
                                                    style={{fontSize:'9px', padding:'1px 4px', backgroundColor: '#e1e1e1', border: '1px solid #999'}}
                                                >
                                                    {isStartingSovits ? '启动中...' : '启动'}
                                                </button>
                                            )}
                                        </div>
                                        <div style={{display:'flex', alignItems:'center', gap:'4px'}}>
                                            <span style={{fontSize:'10px', width:'50px'}}>本地路径:</span>
                                            <input 
                                                type="text" 
                                                value={sovitsPath} 
                                                onChange={e => setSovitsPath(e.target.value)}
                                                placeholder="GPT-SoVITS 根目录"
                                                style={{flex:1, fontSize:'10px', padding:'1px 3px'}}
                                            />
                                            <button 
                                                onClick={handleDetectLocal}
                                                style={{fontSize:'9px', padding:'1px 4px'}}
                                            >探测</button>
                                        </div>
                                    </>
                                ) : (
                                    <div style={{display:'flex', alignItems:'center', gap:'4px'}}>
                                        <span style={{fontSize:'10px', width:'50px'}}>音色:</span>
                                        <select 
                                            value={ttsVoice} 
                                            onChange={e => setTtsVoice(e.target.value)}
                                            style={{flex:1, fontSize:'11px'}}
                                        >
                                            {!availableVoices.length && (
                                                <option value="">暂无可用音色</option>
                                            )}
                                            {availableVoices.map(v => (
                                                <option key={v.id} value={v.id}>{v.name}</option>
                                            ))}
                                        </select>
                                    </div>
                                )}
                            </div>
                       </div>
                   </div>

                   <div style={{display:'flex', gap:'10px'}}>
                       <div style={{flex:1, border:'1px dotted #888', padding:'4px', backgroundColor:'#ece9d8', opacity: ttsProvider === 'gpt-sovits' ? 1 : 0.5}}>
                            <div style={{fontWeight:'bold', fontSize:'11px'}}>{t('narrator_reference_label')} {ttsProvider !== 'gpt-sovits' && '(仅SoVITS可用)'}</div>
                            <div style={{display:'flex', gap:'4px', marginTop:'4px', alignItems:'center'}}>
                                <select value={refLang} onChange={e => setRefLang(e.target.value)} style={{width:'60px'}}>
                                    <option value="zh">{t('lang_zh')}</option>
                                    <option value="en">{t('lang_en')}</option>
                                    <option value="ja">{t('lang_ja')}</option>
                                    </select>
                                
                                {!refAudioExists ? (
                                    <button onClick={() => document.getElementById(`ref-up-${windowId}`).click()} style={{flex:1}}>{t('narrator_upload_ref')}</button>
                                ) : (
                                    <>
                                        <div style={{flex:1, border:'1px inset #fff', background:'#fff', padding:'2px', height:'20px', display:'flex', alignItems:'center', overflow:'hidden'}}>
                                            <span style={{fontSize:'10px', color:'#000080', whiteSpace:'nowrap', textOverflow:'ellipsis', overflow:'hidden'}} title={refFilename}>
                                                {refFilename || 'default.wav'}
                                            </span>
                                </div>
                                        <button onClick={() => document.getElementById(`ref-up-${windowId}`).click()} style={{width:'auto', padding:'0 6px'}} title={t('narrator_change_ref')}>📂</button>
                                    </>
                                )}
                                
                                <input type="file" accept=".wav,.mp3" id={`ref-up-${windowId}`} style={{display:'none'}} 
                                    onChange={(e) => { if(e.target.files[0]) handleUploadRef(e.target.files[0]); }} />
                            </div>
                            
                            {refAudioExists && (
                                <audio controls src={`http://localhost:8081/api/tts/reference/audio?t=${audioTimestamp}`} style={{width:'100%', height:'25px', marginTop:'4px'}} />
                            )}
                            
                            <textarea value={refText} onChange={e => setRefText(e.target.value)} placeholder={t('narrator_ref_text_placeholder')} 
                                style={{width:'100%', height: refAudioExists ? '30px' : '55px', marginTop:'4px', fontSize:'10px', resize:'none'}} />
                            </div>

                       <div style={{flex:1, border:'1px dotted #888', padding:'4px', backgroundColor:'#fff'}}>
                            <div style={{fontWeight:'bold', fontSize:'11px'}}>{t('narrator_model_label')}</div>
                            <div style={{display:'flex', flexDirection:'column', gap:'4px', marginTop:'4px'}}>
                                <div style={{display:'flex', alignItems:'center'}}>
                                    <span style={{width:'40px'}}>{t('narrator_output_lang')}</span>
                                    <select value={targetLang} onChange={e => setTargetLang(e.target.value)} style={{flex:1}}>
                                        <option value="zh">{t('narrator_mixed_zh')}</option>
                                        <option value="en">{t('narrator_pure_en')}</option>
                                        <option value="ja">{t('narrator_mixed_ja')}</option>
                                        <option value="auto">{t('narrator_auto_lang')}</option>
                                    </select>
                                </div>
                                <div style={{display:'flex', alignItems:'center'}}>
                                    <span style={{width:'40px'}}>GPT:</span>
                                    <select value={selectedGPT} onChange={e => changeModel('gpt', e.target.value)} style={{flex:1}}>
                                        <option value="">Default</option>
                                        {gptModels.map(m => <option key={m} value={m}>{m}</option>)}
                                    </select>
                                </div>
                                <div style={{display:'flex', alignItems:'center'}}>
                                    <span style={{width:'40px'}}>SoVITS:</span>
                                    <select value={selectedSoVITS} onChange={e => changeModel('sovits', e.target.value)} style={{flex:1}}>
                                        <option value="">Default</option>
                                        {sovitsModels.map(m => <option key={m} value={m}>{m}</option>)}
                                    </select>
                                </div>
                            </div>
                       </div>
                   </div>
                   
                   <div style={{marginTop:'8px', textAlign:'right'}}>
                       <button onClick={fetchModels} style={{marginRight:'8px'}}>{t('narrator_refresh_models')}</button>
                       <button onClick={handleSaveSettings} style={{fontWeight:'bold', padding:'2px 8px'}}>{t('narrator_save_settings')}</button>
                   </div>
               </div>
            )}

            {/* --- VIEW: EDITOR --- */}
            {viewMode === 'editor' && (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '8px' }}>
                    <div style={{display:'flex', justifyContent:'space-between', marginBottom:'4px', alignItems:'center'}}>
                       <span style={{fontWeight:'bold', color: '#000080'}}>{t('narrator_script_page').replace('{page}', pageControl.currentPage)}</span>
                       <button onClick={() => setViewMode('player')}>{t('narrator_back_to_player')}</button>
                     </div>
                     <textarea
                        value={currentScript}
                        onChange={(e) => setCurrentScript(e.target.value)}
                        style={{ flex: 1, resize: 'none', padding: '4px', fontFamily:'inherit', fontSize:'12px' }}
                        placeholder={t('narrator_edit_placeholder')}
                    />
                    <div style={{textAlign:'right', fontSize:'10px', color:'#666', marginTop:'2px'}}>
                        {currentScript !== lastSavedScript ? t('narrator_saving') : t('narrator_saved')}
                    </div>
                   </div>
               )}
    
            {/* --- VIEW: PLAYER --- */}
            {viewMode === 'player' && (
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
                    
                    {/* 1. Subtitle Bar */}
                    {showSubtitles ? (
                        <div style={{ 
                            flex: 1, // Takes remaining space
                            backgroundColor: 'rgba(0,0,0,0.85)',
                            color: '#fff',
                            display: 'flex', 
                            alignItems: 'center',
                            justifyContent: 'center',
                            padding: '0 30px',
                            position: 'relative',
                            textAlign: 'center',
                            fontSize: '15px',
                            fontWeight: 'bold',
                            lineHeight: '1.4',
                            overflowY: 'auto'
                        }}>
                            {currentSubtitle || (audioUrl ? (isPlaying ? "..." : t('narrator_click_to_play')) : t('narrator_no_audio'))}
                            <button
                                onClick={() => setShowSubtitles(false)}
                                style={{
                                    position: 'absolute', right: '4px', top: '4px', 
                                    background:'transparent', border:'none', color:'#888', cursor:'pointer', fontSize:'10px'
                                }}
                                title={t('narrator_hide_subtitles')}
                            >✕</button>
                        </div>
                    ) : (
                        /* 当字幕关闭时，添加一个弹性占位符，将进度条和控制栏推到底部 */
                        <div style={{ flex: 1 }} />
                    )}
                    
                    {/* 2. Progress Bar */}
                    <div style={{
                        height: '28px', 
                        backgroundColor: '#e0e0e0', 
                        borderTop: '1px solid #999',
                        borderBottom: '1px solid #999',
                        display: 'flex',
                        alignItems: 'center',
                        padding: '0 8px',
                        gap: '8px',
                        fontSize: '11px',
                        fontFamily: 'monospace',
                        color: '#333'
                    }}>
                        <span style={{minWidth:'35px', textAlign:'right'}}>{formatTime(audioProgress)}</span>
                        <input 
                              type="range" 
                              min="0" 
                              max={audioDuration || 100} 
                              value={audioProgress || 0} 
                              onChange={(e) => {
                                  const val = parseFloat(e.target.value);
                                  if (audioRef.current) {
                                      audioRef.current.currentTime = val;
                                      setAudioProgress(val);
                                  }
                              }}
                              style={{flex: 1, height: '4px', cursor: 'pointer'}}
                              disabled={!audioUrl}
                        />
                        <span style={{minWidth:'35px'}}>{formatTime(audioDuration)}</span>
                        {!showSubtitles && (
                            <button onClick={() => setShowSubtitles(true)} style={{border:'1px solid #999', background:'#fff', cursor:'pointer', fontSize:'10px', padding:'0 4px'}}>{t('narrator_show_subtitles')}</button>
                        )}
                  </div>
    
                    {/* 3. Controls Bar */}
                  <div style={{ 
                        height: '46px',
                        backgroundColor: '#c0c0c0',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        padding: '0 6px'
                  }}>
                        {/* Left: Generators */}
                        <div style={{display: 'flex', gap: '4px', alignItems:'center'}}>
                            <div style={{display:'flex', flexDirection:'column', gap:'1px'}}>
                                <button onClick={generateScript} title={t('narrator_gen_script')} disabled={isGenerating} style={{fontSize:'10px', padding:'0 4px', whiteSpace: 'nowrap'}}>📝 {t('narrator_script_short')}</button>
                                <button onClick={generateAudio} title={t('narrator_gen_audio')} disabled={isGeneratingAudio} style={{fontSize:'10px', padding:'0 4px', whiteSpace: 'nowrap'}}>🔊 {t('narrator_audio_short')}</button>
                    </div>
                            <div style={{display:'flex', flexDirection:'column', gap:'1px'}}>
                                <button onClick={() => startBatch('script')} title={t('narrator_batch_script')} disabled={isBatchProcessing} style={{fontSize:'10px', padding:'0 4px', whiteSpace: 'nowrap'}}>📚 {t('narrator_batch_script_short')}</button>
                                <button onClick={() => startBatch('audio')} title={t('narrator_batch_audio')} disabled={isBatchProcessing} style={{fontSize:'10px', padding:'0 4px', whiteSpace: 'nowrap'}}>💿 {t('narrator_batch_audio_short')}</button>
                            </div>
                            <div style={{display:'flex', flexDirection:'column', gap:'1px'}}>
                                <button onClick={() => startBatch('script-missing')} title={t('narrator_missing_script')} disabled={isBatchProcessing} style={{fontSize:'10px', padding:'0 4px', whiteSpace: 'nowrap'}}>➕ {t('narrator_fill_short')}</button>
                                <button onClick={() => startBatch('audio-missing')} title={t('narrator_missing_audio')} disabled={isBatchProcessing} style={{fontSize:'10px', padding:'0 4px', whiteSpace: 'nowrap'}}>➕ {t('narrator_fill_short')}</button>
                            </div>
                            <div style={{display:'flex', flexDirection:'column', gap:'1px'}}>
                                <button
                                    onClick={() => handleExportScript('pdf')}
                                    title={canExportScripts ? `${t('pdf_outline_export_script')} (${exportableScriptPages.length}/${totalNarratorPages}页)` : `需先生成全部页面讲稿 (${exportableScriptPages.length}/${totalNarratorPages}页，缺少${missingScriptPages.length}页)`}
                                    disabled={!canExportScripts}
                                    style={{fontSize:'10px', padding:'0 4px', whiteSpace: 'nowrap'}}
                                >
                                    {exportingScriptFormat === 'pdf' ? '...' : '📤 PDF'}
                                </button>
                                <button
                                    onClick={() => handleExportScript('markdown')}
                                    title={canExportScripts ? `${t('pdf_outline_export_script_md')} (${exportableScriptPages.length}/${totalNarratorPages}页)` : `需先生成全部页面讲稿 (${exportableScriptPages.length}/${totalNarratorPages}页，缺少${missingScriptPages.length}页)`}
                                    disabled={!canExportScripts}
                                    style={{fontSize:'10px', padding:'0 4px', whiteSpace: 'nowrap'}}
                                >
                                    {exportingScriptFormat === 'markdown' ? '...' : '📝 MD'}
                                </button>
                            </div>
                            <span style={{fontSize:'10px', color:'#666', marginLeft:'2px'}}>
                                {isBatchProcessing ? batchProgress.current + '/' + batchProgress.total : ''}
                            </span>
                  </div>
    
                        {/* Center: Playback (The STAR) */}
                        <div style={{display: 'flex', gap: '12px', alignItems: 'center'}}>
                    <button
                      onClick={() => { setIsAutoMode(false); pageControl.goToPreviousPage(); }}
                                title={t('narrator_prev_page')}
                                style={{fontSize:'18px', background:'transparent', border:'none', cursor:'pointer', color:'#000'}}
                            >⏮</button>
                    <button
                      onClick={isAutoMode ? togglePlay : startPresentation}
                      disabled={!audioUrl}
                      title={t('narrator_play_pause')}
                      style={{ 
                                    width: '36px', height: '36px', borderRadius:'50%', 
                                    fontSize: '18px', fontWeight:'bold', 
                                    background: isPlaying ? '#fff' : '#000080', 
                                    color: isPlaying ? '#000' : '#fff',
                                    border: '2px outset #fff', cursor: 'pointer',
                                    display:'flex', alignItems:'center', justifyContent:'center'
                      }}
                    >
                      {isPlaying ? '⏸' : '▶'}
                    </button>
                    <button
                      onClick={() => { setIsAutoMode(false); pageControl.goToNextPage(); }}
                                title={t('narrator_next_page')}
                                style={{fontSize:'18px', background:'transparent', border:'none', cursor:'pointer', color:'#000'}}
                            >⏭</button>
                            <button 
                                onClick={togglePlaybackMode} 
                                title={`${t('narrator_mode_label')} ${getPlaybackModeIcon()}`} 
                                style={{width:'auto', minWidth:'24px', background:'transparent', border:'none', cursor:'pointer', fontSize:'14px', whiteSpace:'nowrap'}}
                    >
                                {getPlaybackModeIcon().split(' ')[0]}
                    </button>
                  </div>

                        {/* Right: Tools */}
                        <div style={{display: 'flex', gap: '6px', alignItems:'center'}}>
                            <button onClick={() => setViewMode('editor')} title={t('narrator_edit')} style={{padding:'4px', whiteSpace:'nowrap'}}>✏️ {t('narrator_edit').split(' ')[1] || t('narrator_edit')}</button>
                            <button onClick={() => setViewMode('settings')} title={t('narrator_settings')} style={{padding:'4px'}}>⚙️</button>
                            <div style={{width:'1px', height:'20px', background:'#888', margin:'0 2px'}}></div>
                            <button onClick={() => setShowPanel(false)} title={t('narrator_close')} style={{padding:'4px', fontWeight:'bold', color:'red'}}>✕</button>
               </div>
            </div>
            </div>
            )}
            
            <audio 
                ref={audioRef} 
                onTimeUpdate={(e) => {
                    const t = e.target.currentTime;
                    const d = e.target.duration;
                    setAudioProgress(t);
                    setAudioDuration(d);
                }}
                onEnded={() => {
                    // setIsPlaying(false); // Don't stop immediately, logic below decides
                    
                    if (playbackMode === 'page_loop') {
                         audioRef.current.currentTime = 0;
                         const p = audioRef.current.play();
                         if(p) p.catch(console.warn);
                    } else if (playbackMode === 'page_once') {
                         setIsPlaying(false);
                         setIsAutoMode(false);
                    } else if (playbackMode === 'doc_once') {
                        setIsPlaying(false); // Pause briefly while changing page
                        if (pageControl.currentPage < pageControl.totalPages) {
                            pageControl.goToNextPage();
                            // useEffect will handle auto-play because isAutoMode is true
                        } else {
                            setIsAutoMode(false);
                            // alert('演示结束');
                        }
                    } else if (playbackMode === 'doc_loop') {
                        setIsPlaying(false);
                        if (pageControl.currentPage < pageControl.totalPages) {
                            pageControl.goToNextPage();
                        } else {
                             // Loop back to start
                             if (pageControl.goToPage) pageControl.goToPage(1);
                             else if (pageControl.setPage) pageControl.setPage(1);
                             else {
                                 // Fallback: try checking if we can go to previous multiple times or just alert
                                 console.warn("No direct jump found, stopping loop");
                                 setIsAutoMode(false);
                             }
                        }
                    }
                }} 
                style={{ display: 'none' }} 
            />
          </div>,
          container
      )}
    </>
  );
};

const PdfNarratorPlugin = {
  id: 'pdf-narrator-plugin',
  name: 'PPT 智能讲解员',
  description: '自动生成讲稿并配合语音进行 PPT 演示',
  version: '1.0.0',
  author: 'WhatNote Team',
  type: 'toolbar-feature',
  targetWindowTypes: ['pdf-pagination'],
  enabledByDefault: true,
  
  renderToolbarButton: (props) => {
    return <NarratorPluginComponent {...props} />;
  },

  onEnable: async () => {
    console.log('[PdfNarratorPlugin] 插件已启用');
    try {
      await fetch('http://localhost:8081/api/narrator/control', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'start' }) 
      });
    } catch (e) {
      console.error('[PdfNarratorPlugin] Failed to enable backend:', e);
    }
  },

  onDisable: async () => {
    console.log('[PdfNarratorPlugin] 插件已禁用');
    try {
      await fetch('http://localhost:8081/api/narrator/control', { 
        method: 'POST', 
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action: 'stop' }) 
      });
    } catch (e) {
      console.error('[PdfNarratorPlugin] Failed to disable backend:', e);
    }
  }
};

export default PdfNarratorPlugin;
