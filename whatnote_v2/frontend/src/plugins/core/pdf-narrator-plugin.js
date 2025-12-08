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
  
  // 模型管理
  const [gptModels, setGptModels] = useState([]);
  const [sovitsModels, setSovitsModels] = useState([]);
  const [selectedGPT, setSelectedGPT] = useState('');
  const [selectedSoVITS, setSelectedSoVITS] = useState('');
  
  // 参考音频设置
  const [refText, setRefText] = useState('');
  const [refLang, setRefLang] = useState('zh');
  const [refAudioExists, setRefAudioExists] = useState(false);
  const [targetLang, setTargetLang] = useState('zh');
  
  // 批量处理状态
  const [isBatchProcessing, setIsBatchProcessing] = useState(false);
  const [batchProgress, setBatchProgress] = useState({ current: 0, total: 0, type: '', message: '' });
  const stopBatchRef = useRef(false);

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
                // 如果本地没存，顺便存一下
                localStorage.setItem('narrator_ref_text', data.text || '');
                localStorage.setItem('narrator_ref_lang', data.language || 'zh');
            }
        })
        .catch(e => console.warn('Failed to sync ref audio info', e));
    }
  }, [boardId, windowId]);

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
      if (showSettings) {
          fetchModels();
      }
  }, [showSettings, fetchModels]);

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
          alert('切换模型失败，请检查后端连接');
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
                
                // 2. 如果有讲稿，尝试检查/获取音频
                // 为了解决刷新页面后音频按钮灰显的问题，我们在这里主动请求一次
                // 后端如果存在音频文件，会直接返回，不会重新生成，速度很快
                // 如果不存在，目前后端逻辑是生成，我们通过 frontend 传个标记位 'check_exist' 虽然目前后端可能没处理，
                // 但基于用户反馈"再点生成就直接播放了"，说明后端有缓存机制。
                // 我们可以利用这一点，静默请求一次。
                // 为了保险起见，我们不在这里自动请求，而是优化 UI 显示逻辑：
                // 如果有讲稿，即便 audioUrls 里没有，也显示“生成语音”按钮（目前就是这样）。
                // 用户的问题是“播放按键是灰色的”，这是因为 audioUrl 是 null。
                // 
                // 改进：自动尝试恢复 audioUrl (使用 GET 仅检查/获取，不生成)
                if (!audioUrls[page]) {
                    fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/audio/${page}`, {
                        method: 'GET'
                    })
                    .then(async (res) => {
                        if (res.ok) {
                            const blob = await res.blob();
                            const url = URL.createObjectURL(blob);
                            setAudioUrls(prev => ({ ...prev, [page]: url }));
                            // 如果当前还在这一页，就更新 current audioUrl
                            if (pageControl.currentPage === page) {
                                setAudioUrl(url);
                            }
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
      
      // Reset audio for this page on mount/change if not in cache
      // (Wait for user interaction to fetch)
      const url = audioUrls[page];
      setAudioUrl(url || null);
      
      if (audioRef.current) {
          if(url) {
              // Only update src if it changed to avoid reloading/interrupting
              if (audioRef.current.src !== url) {
                  audioRef.current.src = url;
                  audioRef.current.load(); // Force load
              }

              if(isAutoMode) {
                  const p = audioRef.current.play();
                  if (p !== undefined) {
                      p.catch(e => {
                          console.warn("Auto-play failed", e);
                          setIsPlaying(false);
                      });
                  }
                  setIsPlaying(true);
              } else {
                  // Ensure stopped if not auto mode (and we just switched/loaded)
                  if (!audioRef.current.paused) {
                      audioRef.current.pause();
                  }
                  setIsPlaying(false);
              }
          } else {
              audioRef.current.removeAttribute('src');
              setIsPlaying(false);
          }
      }

    }
  }, [pageControl?.currentPage, showPanel, boardId, windowId]);

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
    
    // response is blob
    const blob = await response.blob();
    return URL.createObjectURL(blob);
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
    setBatchProgress({ current: 0, total, type, message: '准备中...' });

    try {
      if (type === 'script') {
          // ... (Previous batch script logic remains same, simplified for brevity)
          // Assume this part is unchanged
          let outlineData = null;
          let subdivisionData = null;
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
              setBatchProgress({ current: 0, total: 100, type: 'analyzing', message: '正在细分文档结构 (2/2)...' });
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
          
          // 预处理：计算每个分段的“生成目标范围”（去重）
          // 规则：如果分段与上一分段重叠，重叠部分由上一分段负责，当前分段只负责后续部分
          // 但当前分段仍需读取重叠部分作为上下文
          sections.forEach((section, idx) => {
              let targetStart = section.page_start;
              const targetEnd = section.page_end;
              
              if (idx > 0) {
                  const prevSection = sections[idx - 1];
                  // 如果上一分段的结束页 >= 当前分段的开始页，说明有重叠
                  // 当前分段从上一分段结束页 + 1 开始生成
                  if (prevSection.page_end >= targetStart) {
                      targetStart = prevSection.page_end + 1;
                  }
              }
              
              section.target_page_start = targetStart;
              section.target_page_end = targetEnd;
          });

          const processSection = async () => {
              while (sectionCursor < sections.length) {
                  if (stopBatchRef.current) break;
                  const index = sectionCursor++;
                  const section = sections[index];
                  
                  // 如果目标范围无效（例如完全被上一分段包含），则跳过
                  if (section.target_page_start > section.target_page_end) {
                      console.log(`Skipping section ${index} (fully overlapped)`);
                      setBatchProgress(prev => ({
                           ...prev, 
                           current: Math.min(section.page_end, prev.total),
                           message: `跳过重复分段 ${index + 1}...`
                      }));
                      continue;
                  }

                  // Avoid rapid state updates for progress to prevent UI jitter
                  setBatchProgress({ 
                      current: section.target_page_start, 
                      total: total, 
                      type: 'script',
                      message: `正在生成: ${section.title || `第 ${index+1} 部分`} (并⾏处理中)...` 
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
                                      start: section.target_page_start,
                                      end: section.target_page_end
                                  },
                                  subdivision_data: subdivisionData?.subdivisions?.[index],
                                  // 发送所有之前的分段摘要，构建完整的上下文链
                                  context_history: subdivisionData?.subdivisions?.slice(0, index).map(s => ({
                                      title: s.title,
                                      summary: s.section_summary
                                  })),
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
                                              
                                              // Update Cache
                                              const storageKey = `narrator_scripts_${boardId}_${windowId}`;
                                              
                                              // 简单的去重/跳过逻辑：如果已有内容且内容长度大于10，暂时不覆盖（可选）
                                              // 但用户可能想重新生成，所以通常覆盖是预期的。
                                              // 问题在于：分段可能有重叠页面。
                                              // 例如 Section 1: Page 1-5, Section 2: Page 5-10
                                              // Page 5 会被生成两次。
                                              // 后生成的会覆盖前面的。
                                              // 如果是并发，顺序不确定，可能导致 Page 5 内容随机。
                                              // 
                                              // 改进方案：
                                              // 检查当前 state 中的 scripts[page] 是否已经存在且非空。
                                              // 如果存在，可以选择追加、忽略或覆盖。
                                              // 这里我们采用【智能合并】策略：
                                              // 如果该页已经在本次批量任务中被标记为"已生成"（需要额外状态跟踪），则跳过。
                                              // 但由于并发，状态更新有延迟。
                                              // 
                                              // 临时方案：直接覆盖。最后写入的赢。
                                              // 考虑到通常重叠页是过渡页，内容应该差异不大，或者后者更准确（上下文不同）。
                                              // 
                                              // 更佳方案：在 section 划分时就避免重叠。
                                              // 目前后端 analyze_outline_page_coverage 确实会产生重叠。
                                              // 前端这里简单做：覆盖。
                                              
                                              // React state update
                                              setScripts(prev => ({ ...prev, [page]: content }));

                                              // If it's current page
                                              if (page === pageControl.currentPage) {
                                                  setCurrentScript(content);
                                                  setLastSavedScript(content);
                                              }
                                              
                                              // Persist
                                              try {
                                                  const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
                                                  saved[page] = content;
                                                  localStorage.setItem(storageKey, JSON.stringify(saved));
                                              } catch(e) {}

                                              setBatchProgress(prev => ({ ...prev, current: page }));
                                          }
                                      } catch (e) {}
                                  }
                              }
                          }
                      }
                  } catch (err) { console.error(err); }
              }
          };

          const workers = Array(Math.min(sections.length, CONCURRENCY)).fill(null).map(() => processSection());
          await Promise.all(workers);

      } else if (type === 'audio') {
        setBatchProgress({ current: 0, total, type: 'audio', message: '开始批量合成语音...' });
        for (let i = 1; i <= total; i++) {
            if (stopBatchRef.current) break;
            try {
                let text = scripts[i];
                if (!text) {
                    const res = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/scripts/${i}`);
                    const d = await res.json();
                    if(d.success && d.content) text = d.content;
                }

                if (text && !audioUrls[i]) {
                   setBatchProgress(prev => ({ ...prev, current: i, message: `正在合成第 ${i} 页语音...` }));
                   
                   // Call same endpoint
                   const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/narrator/audio/${i}`, {
                      method: 'POST',
                      headers: { 'Content-Type': 'application/json' },
                      body: JSON.stringify({
                        text: text,
                        prompt_lang: "zh"
                      })
                   });
                   if(response.ok) {
                       const blob = await response.blob();
                       const url = URL.createObjectURL(blob);
                       const storageKey = `narrator_audios_${boardId}_${windowId}`;
                       const saved = JSON.parse(localStorage.getItem(storageKey) || '{}');
                       saved[i] = url;
                       localStorage.setItem(storageKey, JSON.stringify(saved));
                       setAudioUrls(prev => ({ ...prev, [i]: url }));
                   }
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
    // if (!currentScript) { alert('请先生成讲稿'); return; }
    if (!currentScript) return; // Fail silently or rely on UI state (button disabled)
    
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
        
        // Use setTimeout to allow state update and DOM to settle
        setTimeout(() => {
            if (audioRef.current) {
                if (audioRef.current.src !== url) {
                    audioRef.current.src = url;
                    audioRef.current.load();
                }
                const p = audioRef.current.play();
                if (p !== undefined) {
                    p.catch(e => {
                        console.warn("Auto-play after gen failed", e);
                        setIsPlaying(false);
                    });
                }
                setIsPlaying(true);
            }
        }, 100);
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
        setIsPlaying(false);
      } else {
        setIsPlaying(true);
        setIsAutoMode(true); // Manually playing implies entering the current mode
        const playPromise = audioRef.current.play();
        if (playPromise !== undefined) {
            playPromise.catch(error => {
                console.warn("Playback failed/interrupted", error);
                setIsPlaying(false);
                setIsAutoMode(false);
            });
        }
      }
    }
  };

  const startPresentation = () => {
      if (!audioUrl) {
          alert('当前页没有语音，无法开始演示');
          return;
      }
      setIsAutoMode(true);
      if (audioRef.current) {
          setIsPlaying(true);
          const p = audioRef.current.play();
          if (p !== undefined) {
              p.catch(e => {
                  console.warn("Presentation start failed", e);
                  setIsPlaying(false);
                  setIsAutoMode(false);
              });
          }
      }
  };

  const togglePlaybackMode = () => {
      const modes = ['page_once', 'page_loop', 'doc_once', 'doc_loop'];
      const nextIndex = (modes.indexOf(playbackMode) + 1) % modes.length;
      setPlaybackMode(modes[nextIndex]);
  };

  const getPlaybackModeIcon = () => {
      switch(playbackMode) {
          case 'page_once': return '➡️ 单页';
          case 'page_loop': return '🔂 单页循环';
          case 'doc_once': return '⏩ 全文';
          case 'doc_loop': return '🔁 全文循环';
          default: return '⏩';
      }
  };

  const handleSaveSettings = () => {
      localStorage.setItem('narrator_prompt_template', customPrompt);
      localStorage.setItem('narrator_gpt_model', selectedGPT);
      localStorage.setItem('narrator_sovits_model', selectedSoVITS);
      localStorage.setItem('narrator_ref_text', refText);
      localStorage.setItem('narrator_ref_lang', refLang);
      localStorage.setItem('narrator_target_lang', targetLang);
      setShowSettings(false);
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
            // 上传成功后，如果 text 是空的，前端给个提示让用户去填，但不要弹窗阻断
            if (!refText || !refText.trim()) {
               // 可以用一个状态显示“请填写文本”的提示，或者直接聚焦到文本框
               // 这里简化处理，不做强提示，因为用户马上就会去填
            }
            // 自动保存设置（虽然 text 可能是空的，但音频已经上去了）
            handleSaveSettings();
            // alert('参考音频上传成功！请确保在下方文本框中输入该音频对应的文字内容。');
        }
        else alert('上传失败: ' + (data.detail || 'Unknown error'));
    } catch (e) {
        alert('上传出错: ' + e.message);
    }
  };

  const checkTTSStatus = async () => {
    try {
        const res = await fetch('http://localhost:8081/api/tts/status');
        const data = await res.json();
        alert(`TTS 服务状态: ${data.status}\n${data.error || ''}`);
    } catch (e) {
        alert('无法连接到后端服务');
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
            height: showSettings ? 'calc(100% - 30px)' : '180px', // 30px is roughly top bar height
            position: showSettings ? 'absolute' : 'static',
            bottom: 0,
            top: showSettings ? '30px' : 'auto',
            left: 0,
            zIndex: showSettings ? 100 : 'auto',
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
                     gap: '8px', // Increased gap
                     overflowY: 'auto' // Scrollable
                   }}>
                       <div style={{fontWeight: 'bold', color: '#000080'}}>讲稿生成设置 (Prompt)</div>
                       <textarea 
                           value={customPrompt}
                           onChange={(e) => setCustomPrompt(e.target.value)}
                           style={{
                               height: '80px', // Fixed height
                               minHeight: '80px',
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
                       
                       <div style={{ borderTop: '1px solid #999', paddingTop: '4px' }}>
                            <div style={{fontWeight: 'bold', color: '#000080', marginBottom: '8px', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                                <span>参考音色 (Reference Audio)</span>
                                <span style={{fontSize: '10px', color: refAudioExists ? 'green' : 'red', fontWeight: 'normal'}}>
                                    {refAudioExists ? '✅ 已上传' : '❌ 未上传'}
                                </span>
                            </div>
                            
                            {/* Step 1: Language & Upload */}
                            <div style={{marginBottom: '8px', border: '1px dotted #666', padding: '4px', backgroundColor: '#ece9d8'}}>
                                <div style={{fontSize: '11px', fontWeight: 'bold', color: '#444', marginBottom: '4px'}}>第一步：选择语种并上传音频</div>
                                <div style={{display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px'}}>
                                    <label style={{fontSize: '11px', color: '#444'}}>语种:</label>
                                    <select 
                                        value={refLang} 
                                        onChange={e => setRefLang(e.target.value)}
                                        style={{fontSize: '11px'}}
                                    >
                                        <option value="zh">中文 (Chinese)</option>
                                        <option value="en">英文 (English)</option>
                                        <option value="ja">日文 (Japanese)</option>
                                    </select>
                                </div>

                                <div style={{display: 'flex', gap: '4px', alignItems: 'center'}}>
                                    <input 
                                        type="file" 
                                        accept=".wav,.mp3" 
                                        id={`ref-audio-upload-${windowId}`} 
                                        style={{display: 'none'}} 
                                        onChange={(e) => {
                                            if(e.target.files[0]) handleUploadRef(e.target.files[0]);
                                            e.target.value = null; // reset
                                        }}
                                    />
                                    <button 
                                        onClick={() => {
                                            // 如果没有填写文本，先提示但不阻止选择文件
                                            // 但 handleUploadRef 内部会检查
                                            // 既然反过来了，我们允许先选文件，但最好是点击按钮只选文件，然后保存时再上传
                                            // 为了简化逻辑，我们保持现有的 flow，但是如果点击上传时没文本，提示输入文本
                                            document.getElementById(`ref-audio-upload-${windowId}`).click();
                                        }} 
                                        style={{
                                            flex:1, 
                                            padding: '4px 8px', 
                                            fontWeight: 'bold'
                                        }}
                                    >
                                        📤 上传音频 (5-10s)
                                    </button>
                                    <button onClick={checkTTSStatus} title="检查服务状态">📡</button>
                                </div>
                            </div>

                            {/* Step 2: Text Input */}
                            <div style={{marginBottom: '8px', border: '1px dotted #666', padding: '4px', backgroundColor: '#fff'}}>
                                <div style={{fontSize: '11px', fontWeight: 'bold', color: '#444', marginBottom: '4px'}}>第二步：输入音频中说的话 (上传后会自动保存)</div>
                                <textarea 
                                    value={refText}
                                    onChange={(e) => setRefText(e.target.value)}
                                    placeholder="请在这里输入您刚才上传的音频中的文字内容..."
                                    style={{
                                        width: '100%',
                                        height: '60px',
                                        fontSize: '12px',
                                        resize: 'none',
                                        fontFamily: 'sans-serif',
                                        border: '1px solid #ccc'
                                    }}
                                />
                            </div>
                            
                            <div style={{fontSize: '10px', color: '#666', marginTop: '2px'}}>
                                * 上传成功后，参考音色将自动保存，无需再次点击底部的保存按钮。
                            </div>
                       </div>

                       <div style={{ borderTop: '1px solid #999', paddingTop: '4px' }}>
                            <div style={{fontWeight: 'bold', color: '#000080', marginBottom: '4px', display: 'flex', justifyContent: 'space-between', alignItems: 'center'}}>
                                <span>模型选择 (Model)</span>
                                <button onClick={fetchModels} title="刷新模型列表" style={{fontSize: '10px', padding: '0 4px', cursor: 'pointer'}}>🔄</button>
                            </div>
                            <div style={{display: 'flex', flexDirection: 'column', gap: '4px'}}>
                                <div style={{display: 'flex', alignItems: 'center', gap: '4px'}}>
                                    <label style={{width: '50px'}}>输出语言:</label>
                                    <select 
                                        style={{flex: 1}} 
                                        value={targetLang} 
                                        onChange={e => setTargetLang(e.target.value)}
                                    >
                                        <option value="zh">中英混合 (Chinese-English)</option>
                                        <option value="en">纯英文 (English)</option>
                                        <option value="ja">日英混合 (Japanese-English)</option>
                                        <option value="auto">多语种混合 (Auto)</option>
                                    </select>
                                </div>
                                <div style={{display: 'flex', alignItems: 'center', gap: '4px'}}>
                                    <label style={{width: '50px'}}>GPT:</label>
                                    <select 
                                        style={{flex: 1}} 
                                        value={selectedGPT} 
                                        onChange={e => changeModel('gpt', e.target.value)}
                                    >
                                        <option value="">使用默认预训练模型</option>
                                        {gptModels.map(m => <option key={m} value={m}>{m}</option>)}
                                    </select>
                                </div>
                                <div style={{display: 'flex', alignItems: 'center', gap: '4px'}}>
                                    <label style={{width: '50px'}}>SoVITS:</label>
                                    <select 
                                        style={{flex: 1}} 
                                        value={selectedSoVITS} 
                                        onChange={e => changeModel('sovits', e.target.value)}
                                    >
                                        <option value="">使用默认预训练模型</option>
                                        {sovitsModels.map(m => <option key={m} value={m}>{m}</option>)}
                                    </select>
                                </div>
                            </div>
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
                        onClick={togglePlaybackMode}
                        title={`切换播放模式: ${getPlaybackModeIcon()}`}
                        style={{
                            border: '2px outset #ffffff',
                            background: '#c0c0c0',
                            cursor: 'pointer',
                            fontSize: '10px',
                            minWidth: '24px',
                            padding: '0 2px'
                        }}
                    >
                        {getPlaybackModeIcon().split(' ')[0]}
                    </button>

                    <button
                      onClick={isAutoMode ? togglePlay : startPresentation}
                      disabled={!audioUrl}
                      title={isAutoMode ? "暂停" : "开始播放"}
                      style={{ 
                        flex: 1, 
                        border: '2px outset #ffffff', 
                        background: isAutoMode ? '#a0ffcd' : '#c0c0c0', 
                        cursor: !audioUrl ? 'not-allowed' : 'pointer',
                        fontWeight: 'bold',
                        fontSize: '11px'
                      }}
                    >
                      {isPlaying ? '⏸' : '▶'}
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
                    : (isGenerating ? '正在生成讲稿...' : (isGeneratingAudio ? '正在合成语音...' : (isAutoMode ? `正在播放 (${getPlaybackModeIcon()})` : '就绪')))
                }
              </span>
              <span>{currentScript !== lastSavedScript ? '💾 正在保存...' : '✅ 已保存'} {audioUrl ? '🔊 有语音' : ''}</span>
            </div>
            
            <audio 
                ref={audioRef} 
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
