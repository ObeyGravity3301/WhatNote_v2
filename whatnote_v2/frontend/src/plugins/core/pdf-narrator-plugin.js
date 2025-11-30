import React, { useState, useEffect, useRef, useCallback } from 'react';
import ReactDOM from 'react-dom';

const NarratorPluginComponent = (props) => {
  const { windowId, boardId, pageControl } = props;
  const [showPanel, setShowPanel] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentScript, setCurrentScript] = useState('');
  const [lastSavedScript, setLastSavedScript] = useState(''); // To track changes
  
  const [isGenerating, setIsGenerating] = useState(false);
  const [scripts, setScripts] = useState({}); // { [page]: string } - Cache
  
  const [isGeneratingAudio, setIsGeneratingAudio] = useState(false);
  const [audioUrl, setAudioUrl] = useState(null);
  const [audioUrls, setAudioUrls] = useState({}); // { [page]: url }
  
  // 批量处理状态
  const [isBatchProcessing, setIsBatchProcessing] = useState(false);
  const [batchProgress, setBatchProgress] = useState({ current: 0, total: 0, type: '', message: '' });
  const stopBatchRef = useRef(false);

  // 自动演示模式
  const [isAutoMode, setIsAutoMode] = useState(false);

  // 提示词设置
  const DEFAULT_PROMPT = `你是一位专业的演讲者。请根据这页 PPT 的内容，为我撰写一份口语化的演讲稿。
要求：
1. 时间控制在 30-60 秒。
2. 语言自然流畅，适合朗读。
3. 不要念标题，而是解释核心观点。
4. 使用第一人称。
请直接输出演讲稿内容，不要包含任何 Markdown 格式或额外说明。`;
  
  const [customPrompt, setCustomPrompt] = useState(DEFAULT_PROMPT);

  const audioRef = useRef(null);

  // 初始化加载
  useEffect(() => {
    if (boardId && windowId) {
      // 加载缓存的讲稿 (LocalStorage backup)
      const scriptKey = `narrator_scripts_${boardId}_${windowId}`;
      const savedScripts = JSON.parse(localStorage.getItem(scriptKey) || '{}');
      setScripts(savedScripts);

      // 加载缓存的语音URL
      const audioKey = `narrator_audios_${boardId}_${windowId}`;
      const savedAudios = JSON.parse(localStorage.getItem(audioKey) || '{}');
      setAudioUrls(savedAudios);
      
      // 加载提示词设置
      const savedPrompt = localStorage.getItem('narrator_prompt_template');
      if (savedPrompt) setCustomPrompt(savedPrompt);
    }
  }, [boardId, windowId]);

  // 加载当前页数据 (优先从后端获取讲稿)
  useEffect(() => {
    if (showPanel && pageControl) {
      const page = pageControl.currentPage;
      
      // 尝试从后端加载
      fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/scripts/${page}`)
        .then(res => res.json())
        .then(data => {
            if (data.success && data.content) {
                setCurrentScript(data.content);
                setLastSavedScript(data.content);
                setScripts(prev => ({...prev, [page]: data.content}));
            } else {
                // Fallback to cache or empty
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
      
      const url = audioUrls[page];
      setAudioUrl(url || null);
      
      if (audioRef.current) {
        if (url) {
          audioRef.current.src = url;
          if (isAutoMode) {
            audioRef.current.play().catch(e => console.warn('自动播放失败:', e));
            setIsPlaying(true);
          } else {
            setIsPlaying(false);
          }
        } else {
          audioRef.current.removeAttribute('src');
          setIsPlaying(false);
          if (isAutoMode) {
             setIsAutoMode(false);
             alert(`第 ${page} 页没有语音，自动演示已暂停`);
          }
        }
      }
    }
  }, [pageControl?.currentPage, showPanel, boardId, windowId]); // Dependencies updated

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

    const response = await fetch(
      `http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/${page}/generate`,
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
    const response = await fetch('http://localhost:8081/api/tts/generate', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text: text,
        text_lang: 'zh',
        speed_factor: 1.0
      })
    });
    const data = await response.json();
    if (!data.success) throw new Error(data.detail || 'TTS Failed');
    return `http://localhost:8081${data.audio_url}`;
  };

  // 批量处理
  const startBatch = async (type) => {
    if (!boardId || !windowId) return;
    if (isBatchProcessing) {
        stopBatchRef.current = true;
        return;
    }

    const total = pageControl.totalPages;
    if (!window.confirm(`确定要为所有 ${total} 页生成${type === 'script' ? '讲稿' : '语音'}吗？\n这可能需要几分钟，请保持页面开启。`)) return;

    setIsBatchProcessing(true);
    stopBatchRef.current = false;
    setBatchProgress({ current: 0, total, type, message: '准备中...' });

    try {
      if (type === 'script') {
          let outlineData = null;
          let subdivisionData = null;

          // 1. 获取大纲数据 (Stage 1 结果)
          try {
              const res = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/outline-data`);
              if (res.ok) outlineData = await res.json();
          } catch(e) {}

          if (!outlineData || !outlineData.outline) {
              setBatchProgress({ current: 0, total: 100, type: 'analyzing', message: '未找到文档结构，正在执行大纲分析 (1/2)...' });
              try {
                  await runSSETask(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/outline`, (d) => {
                      if (d.type === 'status') setBatchProgress(p => ({...p, message: d.message}));
                  });
                  outlineData = await (await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/outline-data`)).json();
              } catch (err) {
                  console.error('大纲分析失败', err);
              }
          }

          // 2. 获取细分数据 (Stage 2 结果)
          try {
              const res = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/subdivision-data`);
              if (res.ok) subdivisionData = await res.json();
          } catch(e) {}

          if ((!subdivisionData || !subdivisionData.subdivisions) && outlineData && outlineData.outline) {
              setBatchProgress({ current: 0, total: 100, type: 'analyzing', message: '正在细分文档结构 (2/2)...' });
              try {
                  await runSSETask(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/subdivide`, (d) => {
                      if (d.type === 'status') setBatchProgress(p => ({...p, message: d.message}));
                  });
                  subdivisionData = await (await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/subdivision-data`)).json();
              } catch (err) {
                  console.error('细分分析失败', err);
              }
          }

          let sections = outlineData?.outline || [];
          
          // 3. Fallback
          if (sections.length === 0) {
              console.warn('无法获取文档结构，使用默认分块');
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

          // 4. Batch Generation
          for (const [index, section] of sections.entries()) {
              if (stopBatchRef.current) break;
              
              const sectionStart = section.page_start;
              setBatchProgress({ 
                  current: sectionStart, 
                  total: total, 
                  type: 'script',
                  message: `正在生成: ${section.title || `第 ${index+1} 部分`}...` 
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
                              subdivision_data: subdivisionData?.subdivisions?.[index],
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
                                          
                                          // Save to Backend
                                          fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/scripts/${page}`, {
                                              method: 'PUT',
                                              headers: {'Content-Type': 'application/json'},
                                              body: JSON.stringify({ content: content })
                                          });

                                          // Save to Local
                                          const storageKey = `narrator_scripts_${boardId}_${windowId}`;
                                          const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
                                          saved[page] = content;
                                          localStorage.setItem(storageKey, JSON.stringify(saved));
                                          setScripts(prev => ({ ...prev, [page]: content }));
                                          
                                          if (page === pageControl.currentPage) {
                                              setCurrentScript(content);
                                              setLastSavedScript(content);
                                          }
                                          setBatchProgress(prev => ({ ...prev, current: page }));
                                      }
                                  } catch (e) {}
                              }
                          }
                      }
                  }
              } catch (err) {
                  console.error(`Section ${index} batch error:`, err);
              }
          }

      } else if (type === 'audio') {
        setBatchProgress({ current: 0, total, type: 'audio', message: '开始批量合成语音...' });
        for (let i = 1; i <= total; i++) {
            if (stopBatchRef.current) break;
            try {
                // Try to load script if not in cache
                let text = scripts[i];
                if (!text) {
                    const res = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/scripts/${i}`);
                    const d = await res.json();
                    if(d.success && d.content) text = d.content;
                }

                if (text && !audioUrls[i]) {
                   setBatchProgress(prev => ({ ...prev, current: i, message: `正在合成第 ${i} 页语音...` }));
                   const url = await fetchAudioForText(text);
                   
                   const storageKey = `narrator_audios_${boardId}_${windowId}`;
                   const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
                   saved[i] = url;
                   localStorage.setItem(storageKey, JSON.stringify(saved));
                   setAudioUrls(prev => ({ ...prev, [i]: url }));
                }
            } catch (err) {
              console.error(`Page ${i} batch audio error:`, err);
            }
            setBatchProgress(prev => ({ ...prev, current: i }));
            await new Promise(r => setTimeout(r, 50));
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
    setCurrentScript('正在生成讲稿...');

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
        setCurrentScript('生成出错: ' + error.message);
    } finally {
        setIsGenerating(false);
    }
  };

  // 单页生成语音
  const generateAudio = async () => {
    if (!currentScript) { alert('请先生成讲稿'); return; }
    setIsGeneratingAudio(true);
    try {
        const url = await fetchAudioForText(currentScript);
        const page = pageControl.currentPage;
        const storageKey = `narrator_audios_${boardId}_${windowId}`;
        const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
        saved[page] = url;
        localStorage.setItem(storageKey, JSON.stringify(saved));
        setAudioUrls(prev => ({ ...prev, [page]: url }));
        setAudioUrl(url);
        if (audioRef.current) {
            audioRef.current.src = url;
            audioRef.current.play();
            setIsPlaying(true);
        }
    } catch (e) {
        alert('语音生成失败: ' + e.message);
    } finally {
        setIsGeneratingAudio(false);
    }
  };

  const togglePlay = () => {
    if (audioRef.current && audioUrl) {
      if (isPlaying) {
        audioRef.current.pause();
        setIsAutoMode(false);
      } else {
        audioRef.current.play();
      }
      setIsPlaying(!isPlaying);
    }
  };

  const startPresentation = () => {
      if (!audioUrl) {
          alert('当前页没有语音，无法开始演示');
          return;
      }
      setIsAutoMode(true);
      if (audioRef.current) {
          audioRef.current.play();
          setIsPlaying(true);
      }
  };

  const handleSaveSettings = () => {
      localStorage.setItem('narrator_prompt_template', customPrompt);
      setShowSettings(false);
  };

  // 获取Portal容器
  const containerId = `pdf-plugin-bottom-panel-${windowId}`;
  const container = document.getElementById(containerId);

  return (
    <>
      <button
        onClick={() => setShowPanel(!showPanel)}
        style={{
          padding: '1px 8px',
          fontSize: '11px',
          backgroundColor: showPanel ? '#a0a0a0' : '#c0c0c0',
          border: '2px outset #c0c0c0',
          borderRadius: '0px',
          cursor: 'pointer',
          fontFamily: 'MS Sans Serif, sans-serif',
          height: '20px',
          minWidth: '50px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginLeft: '8px'
        }}
        title="打开智能讲解控制台"
      >
        🗣️ 讲解
      </button>
      
      {showPanel && container && ReactDOM.createPortal(
          <div style={{
            width: '100%',
            height: '180px',
            backgroundColor: '#c0c0c0',
            borderTop: '2px outset #ffffff',
            fontFamily: 'MS Sans Serif, sans-serif',
            fontSize: '12px',
            display: 'flex',
            flexDirection: 'column'
          }}>
            {/* 内容区域 */}
            <div style={{ padding: '8px', display: 'flex', gap: '10px', flex: 1, overflow: 'hidden' }}>
               {/* 左侧：Settings OR Script */}
               {showSettings ? (
                   <div style={{ 
                     flex: 1,
                     border: '2px inset #ffffff', 
                     padding: '6px', 
                     backgroundColor: '#d4d0c8',
                     display: 'flex',
                     flexDirection: 'column',
                     gap: '4px'
                   }}>
                       <div style={{fontWeight: 'bold', color: '#000080'}}>讲稿生成设置 (Prompt)</div>
                       <textarea 
                           value={customPrompt}
                           onChange={(e) => setCustomPrompt(e.target.value)}
                           style={{
                               flex: 1,
                               width: '100%',
                               resize: 'none',
                               fontFamily: 'monospace',
                               fontSize: '11px'
                           }}
                       />
                       <div style={{display: 'flex', gap: '5px', justifyContent: 'flex-end'}}>
                           <button onClick={() => setCustomPrompt(DEFAULT_PROMPT)}>恢复默认</button>
                           <button onClick={handleSaveSettings} style={{fontWeight: 'bold'}}>保存设置</button>
                       </div>
                   </div>
               ) : (
                   <div style={{ 
                     flex: 1,
                     border: '2px inset #ffffff', 
                     padding: '0px', 
                     backgroundColor: '#ffffff',
                     overflowY: 'hidden',
                     fontSize: '12px',
                     position: 'relative',
                     display: 'flex',
                     flexDirection: 'column'
                   }}>
                     <div style={{ 
                       fontWeight: 'bold', 
                       color: '#000080',
                       backgroundColor: '#f0f0f0',
                       padding: '2px 6px',
                       borderBottom: '1px solid #ccc',
                       fontSize: '11px',
                       flexShrink: 0
                     }}>
                       [第 {pageControl.currentPage} 页讲稿]
                     </div>
                     <textarea
                        value={currentScript}
                        onChange={(e) => setCurrentScript(e.target.value)}
                        placeholder={isGenerating ? "正在生成..." : "在这里输入或编辑讲稿..."}
                        style={{
                            flex: 1,
                            width: '100%',
                            border: 'none',
                            outline: 'none',
                            resize: 'none',
                            padding: '6px',
                            fontFamily: 'inherit',
                            fontSize: '12px',
                            lineHeight: '1.4',
                            color: '#333'
                        }}
                     />
                   </div>
               )}
    
               {/* 右侧：控制按钮 */}
               <div style={{ 
                 width: '180px', 
                 display: 'flex', 
                 flexDirection: 'column', 
                 gap: '6px',
                 justifyContent: 'center' 
               }}>
                  <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '4px', gap: '4px' }}>
                    <button
                      onClick={() => setShowSettings(!showSettings)}
                      title="设置"
                      style={{
                        backgroundColor: showSettings ? '#a0a0a0' : '#c0c0c0',
                        border: '1px outset #ffffff',
                        width: '16px',
                        height: '16px',
                        fontSize: '10px',
                        lineHeight: '10px',
                        cursor: 'pointer',
                        padding: 0,
                        textAlign: 'center'
                      }}
                    >
                      ⚙️
                    </button>
                    <button
                      onClick={() => { setShowPanel(false); setIsAutoMode(false); }}
                      title="关闭讲解"
                      style={{
                        backgroundColor: '#c0c0c0',
                        border: '1px outset #ffffff',
                        width: '16px',
                        height: '16px',
                        fontSize: '10px',
                        lineHeight: '10px',
                        cursor: 'pointer',
                        padding: 0,
                        fontWeight: 'bold'
                      }}
                    >
                      ✕
                    </button>
                  </div>
    
                  <div style={{ display: 'flex', gap: '4px' }}>
                    <button
                        onClick={generateScript}
                        disabled={isGenerating || isBatchProcessing}
                        style={{
                        flex: 1,
                        padding: '4px',
                        backgroundColor: isGenerating ? '#a0a0a0' : '#c0c0c0',
                        border: '2px outset #ffffff',
                        cursor: (isGenerating || isBatchProcessing) ? 'wait' : 'pointer'
                        }}
                    >
                        📝生成讲稿
                    </button>
                    <button
                        onClick={generateAudio}
                        disabled={isGeneratingAudio || !currentScript || isBatchProcessing}
                        style={{
                        flex: 1,
                        padding: '4px',
                        backgroundColor: (isGeneratingAudio || !currentScript) ? '#a0a0a0' : '#c0c0c0',
                        border: '2px outset #ffffff',
                        cursor: (isGeneratingAudio || !currentScript || isBatchProcessing) ? 'not-allowed' : 'pointer'
                        }}
                    >
                        🔊生成语音
                    </button>
                  </div>
    
                  <div style={{ 
                      marginTop: '4px', 
                      border: '1px dotted #808080', 
                      padding: '4px',
                      backgroundColor: '#d4d0c8'
                  }}>
                    <div style={{ fontSize: '10px', marginBottom: '2px', color: '#444' }}>批量操作 (全文档):</div>
                    <div style={{ display: 'flex', gap: '4px' }}>
                        <button 
                            onClick={() => startBatch('script')}
                            disabled={isBatchProcessing}
                            style={{ flex: 1, fontSize: '10px', cursor: 'pointer' }}>
                            {isBatchProcessing && batchProgress.type === 'script' ? '停止' : '全部讲稿'}
                        </button>
                        <button 
                            onClick={() => startBatch('audio')}
                            disabled={isBatchProcessing}
                            style={{ flex: 1, fontSize: '10px', cursor: 'pointer' }}>
                            {isBatchProcessing && batchProgress.type === 'audio' ? '停止' : '全部语音'}
                        </button>
                    </div>
                  </div>
    
                  <div style={{ height: '4px' }}></div>
    
                  <div style={{ display: 'flex', gap: '4px', justifyContent: 'center' }}>
                    <button
                      title="上一页"
                      onClick={() => { setIsAutoMode(false); pageControl.goToPreviousPage(); }}
                      style={{ minWidth: '30px', border: '2px outset #ffffff', background: '#c0c0c0', cursor: 'pointer' }}
                    >
                      ⏮
                    </button>
                    <button
                      onClick={isAutoMode ? togglePlay : startPresentation}
                      disabled={!audioUrl}
                      title={isAutoMode ? "暂停演示" : "开始演示 (自动翻页)"}
                      style={{ 
                        flex: 1, 
                        border: '2px outset #ffffff', 
                        background: isAutoMode ? '#a0ffcd' : '#c0c0c0', 
                        cursor: !audioUrl ? 'not-allowed' : 'pointer',
                        fontWeight: 'bold',
                        fontSize: '11px'
                      }}
                    >
                      {isPlaying ? '⏸' : (isAutoMode ? '▶' : '▶ 演示')}
                    </button>
                    <button
                      title="下一页"
                      onClick={() => { setIsAutoMode(false); pageControl.goToNextPage(); }}
                      style={{ minWidth: '30px', border: '2px outset #ffffff', background: '#c0c0c0', cursor: 'pointer' }}
                    >
                      ⏭
                    </button>
                  </div>
               </div>
            </div>
            
            <div style={{ 
              borderTop: '1px inset #ffffff', 
              padding: '2px 4px', 
              color: '#666',
              fontSize: '11px',
              display: 'flex',
              justifyContent: 'space-between',
              flexShrink: 0
            }}>
              <span>
                {isBatchProcessing 
                    ? (batchProgress.message || `批量处理中: ${batchProgress.current} / ${batchProgress.total}`)
                    : (isGenerating ? '正在生成讲稿...' : (isGeneratingAudio ? '正在合成语音...' : (isAutoMode ? '正在演示...' : '就绪')))
                }
              </span>
              <span>{currentScript !== lastSavedScript ? '💾 正在保存...' : '✅ 已保存'} {audioUrl ? '🔊 有语音' : ''}</span>
            </div>
            
            <audio 
                ref={audioRef} 
                onEnded={() => {
                    setIsPlaying(false);
                    if (isAutoMode) {
                        if (pageControl.currentPage < pageControl.totalPages) {
                            pageControl.goToNextPage();
                        } else {
                            setIsAutoMode(false);
                            alert('演示结束');
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

  onEnable: () => {
    console.log('[PdfNarratorPlugin] 插件已启用');
  }
};

export default PdfNarratorPlugin;
