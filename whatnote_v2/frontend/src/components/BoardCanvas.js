import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import './BoardCanvas.css';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';

// LaTeX 分隔符标准化函数
const normalizeLatexDelimiters = (text) => {
  return text
    .replace(/\\\(/g, '$')
    .replace(/\\\)/g, '$')
    .replace(/\\\[/g, '$$')
    .replace(/\\\]/g, '$$');
};

// 简单的文本编辑器组件，支持实时预览和打字机模式
function TextEditorWithPreview({ window: windowData, onContentChange }) {
  // 调试模式检测 - 必须在所有其他代码之前定义
  const isDebugMode = typeof window !== 'undefined' && 
    (window.location.search.includes('debug=true') || window.location.hash.includes('debug'));

  const [isLiveMode, setIsLiveMode] = useState(true); // 默认开启实时模式
  const [isTypewriterMode, setIsTypewriterMode] = useState(true); // 默认开启打字机模式
  const [cursorPosition, setCursorPosition] = useState({ line: 1, column: 1 });
  const [localContent, setLocalContent] = useState(windowData.content || '');
  const textareaRef = useRef(null);
  const previewRef = useRef(null);
  const saveTimeoutRef = useRef(null);

  // 检测是否有内容（用于控制上传按钮显示）
  const hasContent = useMemo(() => {
    return localContent && localContent.trim().length > 0;
  }, [localContent]);

  // 处理文件上传
  const handleFileUpload = () => {
    // 创建文件输入元素
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = '*/*'; // 接受所有文件类型
    fileInput.style.display = 'none';
    
    // 添加文件选择事件监听
    fileInput.addEventListener('change', async (event) => {
      const file = event.target.files[0];
      if (!file) return;
      
      console.log('选择上传文件:', file.name, file.type, file.size);
      
      try {
        // 调用父组件的上传处理函数
        if (onContentChange) {
          await onContentChange(file, 'upload');
        }
      } catch (error) {
        console.error('文件上传失败:', error);
        alert('文件上传失败: ' + error.message);
      }
      
      // 清理文件输入元素
      document.body.removeChild(fileInput);
    });
    
    // 添加到DOM并触发点击
    document.body.appendChild(fileInput);
    fileInput.click();
  };

  // 计算光标位置
  const calculateCursorPosition = (textarea) => {
    if (!textarea) return { line: 1, column: 1 };
    
    const text = textarea.value;
    const cursorPos = textarea.selectionStart;
    const textBeforeCursor = text.substring(0, cursorPos);
    const lines = textBeforeCursor.split('\n');
    
    return {
      line: lines.length,
      column: lines[lines.length - 1].length + 1
    };
  };

  // 更新光标位置
  const updateCursorPosition = () => {
    if (textareaRef.current) {
      const pos = calculateCursorPosition(textareaRef.current);
      setCursorPosition(pos);
    }
  };


  // 优化的防抖保存函数
  const debouncedSave = useCallback((content) => {
    // 清除之前的定时器
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
    }
    
    // 1秒防抖保存，避免过于频繁的保存请求
    saveTimeoutRef.current = setTimeout(() => {
      console.log('💾 执行自动保存，内容长度:', content.length);
      onContentChange(content);
    }, 1000);
  }, [onContentChange]);

  // 处理内容变化
  const handleContentChange = (e) => {
    const newContent = e.target.value;
    setLocalContent(newContent);
    updateCursorPosition();
    debouncedSave(newContent);
  };

  // 立即保存函数（用于失去焦点时）
  const saveImmediately = useCallback(() => {
    if (saveTimeoutRef.current) {
      clearTimeout(saveTimeoutRef.current);
      saveTimeoutRef.current = null;
    }
    console.log('⚡ 立即保存内容，长度:', localContent.length);
    onContentChange(localContent);
  }, [localContent, onContentChange]);

  // 同步外部内容变化
  useEffect(() => {
    if (windowData.content !== localContent) {
      setLocalContent(windowData.content || '');
    }
  }, [windowData.content]); // 移除localContent依赖，避免无限循环

  // 组件卸载时清理定时器
  useEffect(() => {
    return () => {
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
      }
    };
  }, []);

  // 性能优化的同步请求管理
  const syncRequestRef = useRef(null);
  
  // 存储上一次的光标行号，避免重复同步
  const lastCursorLineRef = useRef(1);
  
  // 处理光标移动事件（使用 requestAnimationFrame 优化性能）
  const handleCursorEvents = () => {
    updateCursorPosition();
    
    // 触发智能滚动同步
    if (!isScrollingSyncing && isTypewriterMode) {
      // 取消之前的同步请求
      if (syncRequestRef.current) {
        cancelAnimationFrame(syncRequestRef.current);
      }
      
      // 使用 requestAnimationFrame 进行性能优化
      syncRequestRef.current = requestAnimationFrame(() => {
        const cursorCoords = getCursorCoordinates();
        
        // 只有当光标行号真正改变时才触发同步
        if (cursorCoords.line !== lastCursorLineRef.current) {
          lastCursorLineRef.current = cursorCoords.line;
          
          // 添加调试信息
          if (isDebugMode) {
            console.log('🎯 光标行号变化:', {
              新行号: cursorCoords.line,
              进度: (cursorCoords.progress * 100).toFixed(1) + '%',
              触发打字机同步: true
            });
          }
          
          syncScrollByCoordinates(cursorCoords);
        } else if (isDebugMode) {
          console.log('🎯 光标事件忽略（行号未变化）:', {
            当前行: cursorCoords.line,
            触发打字机同步: false
          });
        }
      });
    }
  };

  // 智能滚动状态
  const [isScrollingSyncing, setIsScrollingSyncing] = useState(false);
  const scrollSyncTimeoutRef = useRef(null);

  // 简化的光标位置计算（基于滚动比例）
  const getCursorCoordinates = () => {
    if (!textareaRef.current) return { progress: 0, line: 1 };
    
    const textarea = textareaRef.current;
    const cursorPos = textarea.selectionStart;
    const text = textarea.value;
    
    // 计算光标所在行号
    const textBeforeCursor = text.substring(0, cursorPos);
    const currentLine = textBeforeCursor.split('\n').length;
    const totalLines = text.split('\n').length;
    
    // 简单的进度计算：基于行数
    const lineProgress = totalLines > 1 ? (currentLine - 1) / (totalLines - 1) : 0;
    
    // 获取 textarea 的滚动信息
    const scrollProgress = textarea.scrollHeight > textarea.clientHeight 
      ? textarea.scrollTop / (textarea.scrollHeight - textarea.clientHeight)
      : 0;
    
    // 综合考虑光标位置和滚动位置
    const finalProgress = Math.max(lineProgress, scrollProgress);
    
    if (isDebugMode) {
      console.log('🔍 坐标计算详情:', {
        光标位置: cursorPos,
        当前行: currentLine,
        总行数: totalLines,
        行进度: (lineProgress * 100).toFixed(1) + '%',
        滚动进度: (scrollProgress * 100).toFixed(1) + '%',
        最终进度: (finalProgress * 100).toFixed(1) + '%',
        textarea滚动高度: textarea.scrollHeight,
        textarea可见高度: textarea.clientHeight,
        当前滚动位置: textarea.scrollTop
      });
    }
    
    return {
      progress: Math.max(0, Math.min(1, finalProgress)),
      line: currentLine,
      scrollTop: textarea.scrollTop,
      scrollHeight: textarea.scrollHeight,
      clientHeight: textarea.clientHeight
    };
  };

  // 编辑器滚动事件处理
  const handleEditorScroll = () => {
    // 编辑器滚动时不触发打字机模式同步
    // 打字机模式应该只跟随光标位置变化，而不是滚动位置变化
    if (isDebugMode) {
      console.log('📜 编辑器滚动事件被忽略（避免干扰打字机模式）');
    }
    return;
  };

  // 预览区域滚动事件处理
  const handlePreviewScroll = () => {
    if (isScrollingSyncing) return;
    
    setIsScrollingSyncing(true);
    if (scrollSyncTimeoutRef.current) {
      clearTimeout(scrollSyncTimeoutRef.current);
    }
    
    // 这里可以实现从预览反向同步到编辑器的逻辑
    
    scrollSyncTimeoutRef.current = setTimeout(() => {
      setIsScrollingSyncing(false);
    }, 100);
  };

  // 同步滚动到对应的预览元素
  const syncScrollByCoordinates = (cursorCoords) => {
    if (!previewRef.current || isScrollingSyncing) return;
    
    // 查找对应的元素
    const targetElement = findElementByLine(cursorCoords.line);
    
    if (isDebugMode) {
      console.log('🎯 元素定位测试:', {
        光标行号: cursorCoords.line,
        找到的元素: targetElement ? {
          标签: targetElement.tagName,
          类名: targetElement.className,
          行号属性: targetElement.getAttribute('data-line'),
          块索引属性: targetElement.getAttribute('data-block-index'),
          内容预览: targetElement.textContent.substring(0, 50) + '...'
        } : '未找到元素'
      });
    }
    
    // 执行滚动同步
    if (targetElement) {
      const previewContainer = previewRef.current;
      
      // 获取元素相对于滚动容器的位置
      const containerRect = previewContainer.getBoundingClientRect();
      const elementRect = targetElement.getBoundingClientRect();
      
      // 计算元素相对于容器顶部的位置
      const relativeTop = elementRect.top - containerRect.top + previewContainer.scrollTop;
      const relativeBottom = relativeTop + elementRect.height;
      const containerHeight = previewContainer.clientHeight;
      const currentScrollTop = previewContainer.scrollTop;
      
      // 智能滚动策略：只有当元素不可见时才滚动
      let scrollTop = currentScrollTop; // 默认不滚动
      
      // 如果元素在视窗上方，滚动到元素顶部
      if (relativeTop < currentScrollTop) {
        scrollTop = relativeTop - 50; // 留50px边距
      }
      // 如果元素在视窗下方，滚动到元素可见
      else if (relativeBottom > currentScrollTop + containerHeight) {
        scrollTop = relativeBottom - containerHeight + 50; // 留50px边距
      }
      // 如果元素已经可见，不需要滚动
      
      console.log('🎯 滚动同步执行:', {
        光标行号: cursorCoords.line,
        目标元素: {
          标签: targetElement.tagName,
          类名: targetElement.className,
          块索引: targetElement.getAttribute('data-block-index'),
          行号: targetElement.getAttribute('data-line'),
          高度: elementRect.height,
          内容预览: targetElement.textContent.substring(0, 50) + '...'
        },
        元素位置: { 顶部: relativeTop, 底部: relativeBottom },
        视窗范围: { 顶部: currentScrollTop, 底部: currentScrollTop + containerHeight },
        滚动决策: 
          relativeTop < currentScrollTop ? '元素在上方，需向上滚动' :
          relativeBottom > currentScrollTop + containerHeight ? '元素在下方，需向下滚动' :
          '元素已可见，无需滚动',
        当前滚动位置: currentScrollTop,
        计算的滚动位置: scrollTop,
        最终滚动位置: Math.max(0, scrollTop),
        是否需要滚动: scrollTop !== currentScrollTop
      });
      
      const targetScrollTop = Math.max(0, scrollTop);
      const beforeScroll = previewContainer.scrollTop;
      
      // 设置滚动同步标志，防止循环
      setIsScrollingSyncing(true);
      
      previewContainer.scrollTo({
        top: targetScrollTop,
        behavior: 'smooth'
      });
      
      // 验证滚动是否生效（延迟检查，因为smooth滚动是异步的）
      setTimeout(() => {
        const afterScroll = previewContainer.scrollTop;
        console.log('📊 滚动验证:', {
          滚动前位置: beforeScroll,
          目标位置: targetScrollTop,
          滚动后位置: afterScroll,
          是否成功: Math.abs(afterScroll - targetScrollTop) < 10,
          容器可滚动: previewContainer.scrollHeight > previewContainer.clientHeight,
          容器信息: {
            scrollHeight: previewContainer.scrollHeight,
            clientHeight: previewContainer.clientHeight,
            scrollTop: previewContainer.scrollTop
          }
        });
        
        // 重置滚动同步标志
        setIsScrollingSyncing(false);
      }, 800);
    } else {
      console.log('⚠️ 滚动失败: 未找到目标元素，光标行号:', cursorCoords.line);
    }
  };

  // 根据光标行号直接查找对应的预览元素
  const findElementByLine = (currentLine) => {
    if (!previewRef.current) return null;
    
    // 方法0：直接按精确行号查找（适用于按行拆分的渲染）
    let directElement = previewRef.current.querySelector(`[data-line="${currentLine}"]`);
    if (directElement) {
      if (isDebugMode) {
        console.log('✅ 直接精确行号查找成功:', {
          光标行号: currentLine,
          找到元素: directElement.tagName,
          类名: directElement.className,
          内容: directElement.textContent.substring(0, 30) + '...'
        });
      }
      return directElement;
    }
    
    // 首先尝试找到光标所在的源码块
    const blockIndex = buildSourceLineMapping.lineToBlock.get(currentLine);
    const sourceBlock = buildSourceLineMapping.blocks[blockIndex];
    
    if (isDebugMode) {
      console.log('🔍 行号映射查找:', {
        光标行号: currentLine,
        找到的块索引: blockIndex,
        源码块信息: sourceBlock ? {
          类型: sourceBlock.type,
          起始行: sourceBlock.startLine,
          结束行: sourceBlock.endLine,
          内容预览: sourceBlock.content.substring(0, 50) + '...'
        } : '未找到'
      });
    }
    
    if (blockIndex !== undefined && sourceBlock) {
      // 方法1：根据块索引查找
      let targetElement = previewRef.current.querySelector(`[data-block-index="${blockIndex}"]`);
      
      if (isDebugMode) {
        console.log('🔍 块索引查找尝试:', {
          查找选择器: `[data-block-index="${blockIndex}"]`,
          找到元素: !!targetElement,
          元素详情: targetElement ? {
            标签: targetElement.tagName,
            类名: targetElement.className,
            块索引属性: targetElement.getAttribute('data-block-index'),
            行号属性: targetElement.getAttribute('data-line')
          } : '未找到'
        });
      }
      
      if (targetElement) {
        if (isDebugMode) {
          console.log('✅ 通过块索引找到元素:', {
            块索引: blockIndex,
            元素标签: targetElement.tagName,
            元素类名: targetElement.className,
            元素内容: targetElement.textContent.substring(0, 30) + '...'
          });
        }
        return targetElement;
      }
      
      // 方法2：根据起始行号查找
      targetElement = previewRef.current.querySelector(`[data-line="${sourceBlock.startLine}"]`);
      
      if (isDebugMode) {
        console.log('🔍 行号查找尝试:', {
          查找选择器: `[data-line="${sourceBlock.startLine}"]`,
          找到元素: !!targetElement,
          元素详情: targetElement ? {
            标签: targetElement.tagName,
            行号属性: targetElement.getAttribute('data-line')
          } : '未找到'
        });
      }
      
      if (targetElement) {
        if (isDebugMode) {
          console.log('✅ 通过起始行号找到元素:', {
            起始行号: sourceBlock.startLine,
            元素标签: targetElement.tagName,
            元素类名: targetElement.className,
            元素内容: targetElement.textContent.substring(0, 30) + '...'
          });
        }
        return targetElement;
      }
    }
    
    // 方法3：直接根据当前行号查找最接近的元素
    const allElements = Array.from(previewRef.current.querySelectorAll('[data-line]'));
    let closestElement = null;
    let minDistance = Infinity;
    
    if (isDebugMode) {
      console.log('🔍 备用查找方案，所有可用元素:', allElements.map((el, index) => ({
        索引: index,
        标签: el.tagName,
        行号: el.getAttribute('data-line'),
        块索引: el.getAttribute('data-block-index'),
        类名: el.className,
        内容: el.textContent.substring(0, 20) + '...'
      })));
    }
    
    allElements.forEach(element => {
      const elementLine = parseInt(element.getAttribute('data-line')) || 1;
      const distance = Math.abs(elementLine - currentLine);
      
      if (distance < minDistance) {
        minDistance = distance;
        closestElement = element;
      }
    });
    
    if (isDebugMode && closestElement) {
      console.log('✅ 通过行号距离找到最近元素:', {
        目标行号: currentLine,
        最近元素行号: closestElement.getAttribute('data-line'),
        距离: minDistance,
        元素标签: closestElement.tagName,
        元素内容: closestElement.textContent.substring(0, 30) + '...'
      });
    }
    
    return closestElement;
  };

  // 获取块类型的辅助函数（移到前面避免初始化顺序问题）
  const getBlockType = useCallback((content) => {
    if (content.match(/^#{1,6}\s/)) return 'heading';
    if (content.match(/^[-*+]\s/)) return 'list';
    if (content.match(/^\d+\.\s/)) return 'ordered-list';
    if (content.match(/^>\s/)) return 'blockquote';
    if (content.match(/^```/)) return 'code';
    return 'paragraph';
  }, []);

  // 构建源码行号到内容块的精确映射
  const buildSourceLineMapping = useMemo(() => {
    if (!localContent) return { lineToBlock: new Map(), blocks: [] };
    
    const lines = localContent.split('\n');
    const blocks = [];
    const lineToBlock = new Map();
    
    let currentBlock = null;
    let blockStartLine = 1;
    
    for (let i = 0; i < lines.length; i++) {
      const lineNumber = i + 1;
      const lineContent = lines[i];
      const trimmedContent = lineContent.trim();
      
      // 检查是否是新块的开始
      const isBlockStart = trimmedContent.match(/^#{1,6}\s/) || // 标题
                           trimmedContent.match(/^[-*+]\s/) || // 无序列表  
                           trimmedContent.match(/^\d+\.\s/) || // 有序列表
                           trimmedContent.match(/^>\s/) || // 引用
                           trimmedContent.match(/^```/); // 代码块
      
      const isEmpty = trimmedContent === '';
      
      // 如果遇到空行，结束当前块
      if (isEmpty && currentBlock && currentBlock.content.trim()) {
        blocks.push(currentBlock);
        currentBlock = null;
      }
      // 如果是块开始标记，先结束当前块，再开始新块
      else if (isBlockStart) {
        if (currentBlock && currentBlock.content.trim()) {
          blocks.push(currentBlock);
        }
        currentBlock = {
          startLine: lineNumber,
          endLine: lineNumber,
          content: lineContent,
          type: getBlockType(trimmedContent)
        };
      }
      // 如果有内容且当前没有块，开始新的段落块
      else if (trimmedContent && !currentBlock) {
        currentBlock = {
          startLine: lineNumber,
          endLine: lineNumber,
          content: lineContent,
          type: 'paragraph'
        };
      }
      // 如果有内容且在当前块中，继续当前块
      else if (trimmedContent && currentBlock) {
        currentBlock.endLine = lineNumber;
        currentBlock.content += '\n' + lineContent;
      }
      
      // 暂时不在这里设置映射，等所有块都解析完再统一设置
    }
    
    // 添加最后一个块
    if (currentBlock && currentBlock.content.trim()) {
      blocks.push(currentBlock);
    }
    
    // 更新行号映射
    blocks.forEach((block, blockIndex) => {
      for (let line = block.startLine; line <= block.endLine; line++) {
        lineToBlock.set(line, blockIndex);
      }
    });
    
    // 调试信息：显示解析结果
    if (isDebugMode && blocks.length > 0) {
      console.log('📋 源码块解析结果:', blocks.map((block, index) => ({
        索引: index,
        类型: block.type,
        起始行: block.startLine,
        结束行: block.endLine,
        内容: block.content.substring(0, 30) + '...'
      })));
      
      console.log('📋 行号映射表:', Array.from(lineToBlock.entries()).map(([line, blockIndex]) => ({
        行号: line,
        块索引: blockIndex
      })));
    }
    
    return { lineToBlock, blocks };
  }, [localContent, getBlockType, isDebugMode]);

  // 创建增强的块级 Markdown 组件（支持坐标同步）
  // 直接创建，不使用 useMemo 缓存
  const createMarkdownComponents = () => {
    // 创建一个唯一的渲染ID来确保每次都是全新的组件
    const renderingId = Date.now() + Math.random();
    
    // 调试信息（仅在调试模式下显示）
    if (isDebugMode) {
    console.log('🔄 重新创建 markdownComponents', {
      渲染ID: renderingId,
      总源码块数: buildSourceLineMapping.blocks.length,
      问题分析: {
        多行段落示例: buildSourceLineMapping.blocks.filter(block => 
          block.endLine - block.startLine > 0
        ).slice(0, 3).map(block => ({
          类型: block.type,
          起始行: block.startLine,
          结束行: block.endLine,
          跨越行数: block.endLine - block.startLine + 1,
          内容预览: block.content.substring(0, 50) + '...'
        }))
      },
      前5个块: buildSourceLineMapping.blocks.slice(0, 5).map((block, i) => ({
        索引: i,
        起始行: block.startLine,
        结束行: block.endLine,
        类型: block.type,
        内容: block.content.substring(0, 20) + '...'
      }))
    });
    }
    
    // 使用闭包确保每次重新创建组件时blockIndex都从0开始
    let renderBlockIndex = 0;
    
    const createBlockElement = (tagName, blockType, children, props) => {
      const currentBlockIndex = renderBlockIndex++;
      const block = buildSourceLineMapping.blocks[currentBlockIndex];
      const startLine = block ? block.startLine : 1;
      const endLine = block ? block.endLine : startLine;
      
      // 方案1：如果是多行块，按行拆分渲染
      if (block && block.endLine > block.startLine && (blockType === 'paragraph' || blockType === 'blockquote')) {
        const lines = block.content.split('\n');
        const Element = tagName.toLowerCase();
        
        return (
          <div className={`md-block-container md-${blockType}-container`}>
            {lines.map((lineContent, lineIndex) => {
              const currentLine = block.startLine + lineIndex;
              return (
                <section 
                  key={`${renderingId}-${currentBlockIndex}-line-${lineIndex}`}
                  className={`md-block md-${blockType} md-line`} 
                  data-line={currentLine}
                  data-end-line={currentLine}
                  data-block-index={`${currentBlockIndex}-${lineIndex}`}
                  data-block-type={blockType}
                  data-rendering-id={renderingId}
                  {...props}
                >
                  <Element>{lineContent}</Element>
                </section>
              );
            })}
          </div>
        );
      }
      
      // 调试信息（仅在调试模式下显示前10个元素）
      if (isDebugMode && currentBlockIndex < 10) {
        console.log(`🏗️ 渲染元素${currentBlockIndex}:`, {
          标签: tagName,
          块类型: blockType,
          当前块索引: currentBlockIndex,
          渲染ID: renderingId,
          总块数: buildSourceLineMapping.blocks.length,
          源码块: block ? {
            起始行: block.startLine,
            结束行: block.endLine,
            类型: block.type,
            内容: block.content.substring(0, 30) + '...'
          } : '⚠️ 无对应源码块',
          将设置的属性: {
            'data-block-index': currentBlockIndex,
            'data-line': startLine,
            'data-end-line': endLine,
            'data-block-type': blockType,
            'data-rendering-id': renderingId
          },
          渲染内容: String(children).substring(0, 30) + '...'
        });
      }
      
      const Element = tagName.toLowerCase();
      return (
        <section 
          key={`${renderingId}-${currentBlockIndex}`}
          className={`md-block md-${blockType}`} 
          data-line={startLine} 
          data-end-line={endLine}
          data-block-index={currentBlockIndex}
          data-block-type={blockType}
          data-rendering-id={renderingId}
          {...props}
        >
          <Element>{children}</Element>
        </section>
      );
    };
    
    return {
      p: ({ children, ...props }) => {
        return createBlockElement('p', 'paragraph', children, props);
      },
      h1: ({ children, ...props }) => {
        return createBlockElement('h1', 'heading', children, props);
      },
      h2: ({ children, ...props }) => {
        return createBlockElement('h2', 'heading', children, props);
      },
      h3: ({ children, ...props }) => {
        return createBlockElement('h3', 'heading', children, props);
      },
      h4: ({ children, ...props }) => {
        return createBlockElement('h4', 'heading', children, props);
      },
      h5: ({ children, ...props }) => {
        return createBlockElement('h5', 'heading', children, props);
      },
      h6: ({ children, ...props }) => {
        return createBlockElement('h6', 'heading', children, props);
      },
      li: ({ children, ...props }) => {
        return createBlockElement('li', 'list-item', children, props);
      },
      blockquote: ({ children, ...props }) => {
        return createBlockElement('blockquote', 'blockquote', children, props);
      },
      pre: ({ children, ...props }) => {
        return createBlockElement('pre', 'code', children, props);
      }
    };
  };
  
  const markdownComponents = createMarkdownComponents();

  // 默认实时模式：左右分屏布局，无工具栏
  return (
    <div style={{ 
      height: '100%', 
      display: 'flex', 
      flexDirection: 'column',
      overflow: 'hidden' // 防止整体滚动
    }}>
      {/* 工具栏 - Windows 98 风格 */}
      <div style={{
        backgroundColor: '#c0c0c0',
        borderBottom: '2px outset #c0c0c0',
        padding: '2px 4px',
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
        height: '24px'
      }}>
        {/* 上传按钮 - 只在没有内容时显示 */}
        {!hasContent && (
          <button
            onClick={() => {
              console.log('上传功能被点击');
              handleFileUpload();
            }}
            style={{
              padding: '1px 8px',
              fontSize: '11px',
              backgroundColor: '#c0c0c0',
              border: '2px outset #c0c0c0',
              borderRadius: '0px',
              cursor: 'pointer',
              fontFamily: 'MS Sans Serif, sans-serif',
              height: '20px',
              minWidth: '60px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
            onMouseDown={(e) => {
              e.target.style.border = '2px inset #c0c0c0';
              e.target.style.backgroundColor = '#a0a0a0';
            }}
            onMouseUp={(e) => {
              e.target.style.border = '2px outset #c0c0c0';
              e.target.style.backgroundColor = '#c0c0c0';
            }}
            onMouseLeave={(e) => {
              e.target.style.border = '2px outset #c0c0c0';
              e.target.style.backgroundColor = '#c0c0c0';
            }}
          >
            上传...
          </button>
        )}
        
        {/* 当有内容时显示状态提示 */}
        {hasContent && (
          <div style={{
            fontSize: '11px',
            color: '#000000',
            fontFamily: 'MS Sans Serif, sans-serif',
            padding: '2px 8px'
          }}>
            编辑模式
          </div>
        )}
      </div>

      {/* 调试面板 */}
      {isDebugMode && (
        <div style={{
          backgroundColor: '#ffffcc',
          border: '2px solid #ffcc00',
          padding: '8px',
          fontSize: '12px',
          fontFamily: 'monospace',
          display: 'flex',
          gap: '20px',
          alignItems: 'center',
          flexWrap: 'wrap'
        }}>
          <span><strong>🐛 调试模式</strong></span>
          <span>当前行: <strong>{cursorPosition.line}</strong></span>
          <span>源码块数: <strong>{buildSourceLineMapping.blocks.length}</strong></span>
          <button
            onClick={() => {
              console.log('📋 源码块映射:', buildSourceLineMapping.blocks);
              console.log('📋 行号到块的映射:', Array.from(buildSourceLineMapping.lineToBlock.entries()));
              const cursorCoords = getCursorCoordinates();
              console.log('🎯 当前光标坐标:', cursorCoords);
              
              // 先检查所有渲染的元素
              const allRenderedElements = Array.from(previewRef.current?.querySelectorAll('[data-block-index]') || []);
              console.log('🏗️ 所有渲染的元素 (总共' + allRenderedElements.length + '个):', allRenderedElements.map((el, index) => ({
                DOM索引: index,
                块索引属性: el.getAttribute('data-block-index'),
                行号属性: el.getAttribute('data-line'),
                结束行属性: el.getAttribute('data-end-line'),
                块类型属性: el.getAttribute('data-block-type'),
                标签: el.tagName,
                类名: el.className,
                内容: el.textContent.substring(0, 30) + '...'
              })));
              
              // 检查是否有重复的块索引
              const blockIndexCounts = {};
              allRenderedElements.forEach(el => {
                const blockIndex = el.getAttribute('data-block-index');
                blockIndexCounts[blockIndex] = (blockIndexCounts[blockIndex] || 0) + 1;
              });
              console.log('🔍 块索引统计:', blockIndexCounts);
              
              // 查找对应的元素
              const targetEl = findElementByLine(cursorCoords.line);
              if (targetEl) {
                // 高亮整个元素
                targetEl.style.backgroundColor = '#ffff00';
                targetEl.style.border = '2px solid #ff0000';
                
                // 在元素内部显示坐标指示器
                const coordIndicator = document.createElement('div');
                coordIndicator.style.cssText = `
                  position: absolute;
                  left: 0;
                  top: 0;
                  right: 0;
                  bottom: 0;
                  border: 2px solid #00ff00;
                  background: rgba(0, 255, 0, 0.1);
                  z-index: 1001;
                  pointer-events: none;
                `;
                coordIndicator.className = 'coord-indicator';
                targetEl.style.position = 'relative';
                targetEl.appendChild(coordIndicator);
                
                // 显示坐标信息
                const infoDiv = document.createElement('div');
                infoDiv.style.cssText = `
                  position: absolute;
                  top: -25px;
                  left: 0;
                  background: #000;
                  color: #fff;
                  padding: 2px 6px;
                  font-size: 10px;
                  border-radius: 3px;
                  z-index: 1002;
                `;
                infoDiv.textContent = `行:${cursorCoords.line} 进度:${(cursorCoords.progress*100).toFixed(1)}%`;
                infoDiv.className = 'coord-info';
                targetEl.appendChild(infoDiv);
                
                setTimeout(() => {
                  targetEl.style.backgroundColor = '';
                  targetEl.style.border = '';
                  targetEl.style.position = '';
                  document.querySelectorAll('.coord-indicator, .coord-info').forEach(el => el.remove());
                }, 3000);
              }
              console.log('🎯 找到的目标元素:', targetEl);
            }}
            style={{
              padding: '4px 8px',
              fontSize: '11px',
              backgroundColor: '#ff9999',
              border: '1px solid #cc0000',
              cursor: 'pointer'
            }}
          >
            高亮当前对应元素
          </button>
          <button
            onClick={() => {
              const allElements = previewRef.current?.querySelectorAll('[data-block-index]');
              allElements?.forEach(el => {
                const blockIndex = el.getAttribute('data-block-index');
                const lineNum = el.getAttribute('data-line');
                const sourceBlock = buildSourceLineMapping.blocks[parseInt(blockIndex)];
                
                el.style.position = 'relative';
                
                // 显示块索引和行号范围
                const badge = document.createElement('span');
                badge.textContent = `块${blockIndex}:${lineNum}${sourceBlock ? `-${sourceBlock.endLine}` : ''}`;
                badge.style.cssText = `
                  position: absolute;
                  top: -2px;
                  right: -2px;
                  background: #0066cc;
                  color: white;
                  font-size: 9px;
                  padding: 2px 4px;
                  border-radius: 3px;
                  z-index: 1000;
                  white-space: nowrap;
                `;
                badge.className = 'debug-badge';
                el.appendChild(badge);
              });
              setTimeout(() => {
                document.querySelectorAll('.debug-badge').forEach(badge => badge.remove());
              }, 4000);
            }}
            style={{
              padding: '4px 8px',
              fontSize: '11px',
              backgroundColor: '#99ff99',
              border: '1px solid #00cc00',
              cursor: 'pointer'
            }}
          >
            显示所有行号标记
          </button>
        </div>
      )}
      {/* 左右分屏编辑区域 - 占满整个窗口 */}
      <div style={{ 
        flex: 1, 
        display: 'flex',
        overflow: 'hidden' // 确保子元素不会溢出
      }}>
        {/* 左侧：编辑器容器 */}
        <div style={{ 
          flex: 1, 
          display: 'flex',
          flexDirection: 'column',
          borderRight: '2px solid #808080',
          overflow: 'hidden'
        }}>
          <textarea
            ref={textareaRef}
            value={localContent}
            onChange={handleContentChange}
            onInput={handleCursorEvents}
            onKeyUp={handleCursorEvents}
            onClick={handleCursorEvents}
            onFocus={handleCursorEvents}
            onBlur={saveImmediately}
            onSelect={handleCursorEvents}
            onScroll={handleEditorScroll}
            style={{
              flex: 1,
              margin: 0,
              padding: '8px',
              border: 'none',
              outline: 'none',
              fontFamily: 'Courier New, monospace',
              fontSize: '14px',
              lineHeight: '1.4',
              resize: 'none',
              backgroundColor: '#ffffff',
              color: '#000000',
              overflowY: 'auto',
              overflowX: 'hidden'
            }}
            placeholder="在这里输入 Markdown 内容..."
          />
        </div>
        
        {/* 右侧：预览区域容器 */}
        <div style={{ 
          flex: 1, 
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden'
        }}>
          <div 
            ref={previewRef}
            onScroll={handlePreviewScroll}
            style={{ 
              flex: 1,
              margin: 0,
              padding: '8px',
              backgroundColor: '#ffffff',
              color: '#000000',
              overflowY: 'auto',
              overflowX: 'hidden',
              fontFamily: 'Times New Roman, serif',
              fontSize: '13px',
              lineHeight: '1.6'
            }}
          >
            <ReactMarkdown 
              key={`markdown-${localContent.length}-${buildSourceLineMapping.blocks.length}`}
              remarkPlugins={[remarkGfm, remarkMath]} 
              rehypePlugins={[rehypeKatex]}
              components={markdownComponents}
            >
              {normalizeLatexDelimiters(String(localContent || ''))}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
}

function BoardCanvas({ 
  boardId, 
  boardName,
  onWindowsChange,
  minimizedWindows,
  hiddenWindows, 
  focusedWindowId,
  onWindowMinimize,
  onWindowFocus,
  onWindowClose,
  onWindowShow,
  onWindowHide,
  onBatchWindowHide,
  onClearHiddenWindows,
  onWindowDelete
}) {
  const [windows, setWindows] = useState([]);
  const [isDragging, setIsDragging] = useState(false);
  const [dragData, setDragData] = useState(null);
  const [showCreateMenu, setShowCreateMenu] = useState(false);
  const [isResizing, setIsResizing] = useState(false);
  const [windowZIndexes, setWindowZIndexes] = useState({});
  const [editingTitleId, setEditingTitleId] = useState(null); // 正在编辑标题的窗口ID
  const [editingTitleValue, setEditingTitleValue] = useState(''); // 编辑中的标题值
  
  // 桌面图标系统状态
  const [desktopIcons, setDesktopIcons] = useState([]);
  const [selectedIconId, setSelectedIconId] = useState(null);
  const [isDraggingIcon, setIsDraggingIcon] = useState(false);
  const [iconDragData, setIconDragData] = useState(null);
  
  // 右键菜单状态
  const [contextMenu, setContextMenu] = useState({
    visible: false,
    x: 0,
    y: 0,
    type: 'desktop', // 'desktop' 或 'icon'
    targetIconId: null
  });
  
  // 桌面网格配置
  const GRID_SIZE = 80; // 网格单元大小
  const GRID_MARGIN = 20; // 距离边缘的边距
  const ICON_SIZE = 60; // 图标大小
  
  // 桌面网格管理器
  const desktopGridRef = useRef(new Set()); // 已占用的网格位置 "x,y"
  
  // 网格位置计算辅助函数
  const pixelToGrid = (pixelX, pixelY) => {
    const gridX = Math.round((pixelX - GRID_MARGIN) / GRID_SIZE);
    const gridY = Math.round((pixelY - GRID_MARGIN) / GRID_SIZE);
    return { gridX: Math.max(0, gridX), gridY: Math.max(0, gridY) };
  };
  
  const gridToPixel = (gridX, gridY) => {
    return {
      x: GRID_MARGIN + gridX * GRID_SIZE,
      y: GRID_MARGIN + gridY * GRID_SIZE
    };
  };
  
  // 查找下一个可用的网格位置（从上到下，从左到右）
  const findNextAvailableGridPosition = () => {
    // 获取画布区域的实际尺寸
    // 通过查询DOM元素获取准确的画布尺寸
    const canvasArea = document.querySelector('.canvas-area');
    let canvasWidth, canvasHeight;
    
    if (canvasArea) {
      const rect = canvasArea.getBoundingClientRect();
      canvasWidth = rect.width;
      canvasHeight = rect.height;
    } else {
      // 备用方案：使用窗口尺寸估算
      canvasWidth = window.innerWidth - 250; // 减去侧边栏宽度
      canvasHeight = window.innerHeight - 100; // 减去顶部栏高度
    }
    
    const maxCols = Math.floor((canvasWidth - GRID_MARGIN * 2) / GRID_SIZE);
    const maxRows = Math.floor((canvasHeight - GRID_MARGIN * 2) / GRID_SIZE);
    
    // 按行优先搜索（从左到右，然后从上到下）- 符合Windows桌面习惯
    for (let row = 0; row < maxRows; row++) {
      for (let col = 0; col < maxCols; col++) {
        const gridKey = `${col},${row}`;
        if (!desktopGridRef.current.has(gridKey)) {
          desktopGridRef.current.add(gridKey);
          return { gridX: col, gridY: row };
        }
      }
    }
    
    // 如果没有找到空位，返回默认位置
    return { gridX: 0, gridY: 0 };
  };
  
  // 更新网格占用状态
  const updateGridOccupancy = (icons) => {
    desktopGridRef.current.clear();
    icons.forEach(icon => {
      if (icon.gridPosition) {
        const gridKey = `${icon.gridPosition.gridX},${icon.gridPosition.gridY}`;
        desktopGridRef.current.add(gridKey);
      }
    });
  };
  
  // 保存图标位置到后端
  const saveIconPositions = async (icons) => {
    try {
      const iconPositions = icons.map(icon => ({
        windowId: icon.windowId,
        position: icon.position,
        gridPosition: icon.gridPosition
      }));
      
      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/icon-positions`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ iconPositions }),
      });
      
      if (!response.ok) {
        console.error('图标位置保存失败:', response.status);
      }
    } catch (error) {
      console.error('保存图标位置失败:', error);
    }
  };
  
  // 隐藏窗口状态管理

  const resizeState = useRef({ active: false, windowId: null, startX: 0, startY: 0, startW: 0, startH: 0, originalW: 0, originalH: 0 });
  const dragState = useRef({ active: false, windowId: null, startX: 0, startY: 0, initialX: 0, initialY: 0, originalX: 0, originalY: 0 });
  const windowSaveTimeoutRef = useRef(null); // 重命名避免与TextEditor中的saveTimeoutRef冲突
  const maxZIndexRef = useRef(100);
  const periodicSaveIntervalRef = useRef(null); // 定期保存间隔引用
  const isSavingStateRef = useRef(false); // 标记是否正在保存窗口状态
  const previousBoardIdRef = useRef(null); // 记录前一个展板ID

  // 检查窗口是否有真实的媒体内容
  const hasRealMediaContent = (window) => {
    // 如果有content且是URL或路径，说明已上传
    if (window.content && (
      window.content.includes('http') || 
      window.content.includes('/api/boards/') ||
      window.content.includes('\\') || window.content.includes('/')
    )) {
      return true;
    }
    // 如果有file_path且不是空的占位符文件，说明有内容
    if (window.file_path && window.file_path.startsWith('files/')) {
      // 检查实际文件是否存在且有内容（通过检查是否为新创建的占位符）
      const filename = window.file_path.substring(6);
      // 如果文件名不是默认的占位符名称，认为是有效文件
      if (!filename.startsWith('新建') && !filename.startsWith('untitled')) {
        return true;
      }
      // 即使是新建的，如果有非空content也认为有效
      if (window.content && window.content.trim() !== '') {
        return true;
      }
    }
    return false;
  };

  // 生成缩略图函数 - 移动到前面避免依赖问题
  const generateThumbnail = (window) => {
    const hasMediaContent = hasRealMediaContent(window);

    switch (window.type) {
      case 'text':
        return '📝';
      case 'image':
        if (hasMediaContent) {
          // 返回图片URL作为缩略图
          return toMediaUrl(window);
        }
        return '🖼️';
      case 'video':
        if (hasMediaContent) {
          return '🎬'; // 视频有内容时显示电影图标
        }
        return '🎥';
      case 'audio':
        if (hasMediaContent) {
          return '🎼'; // 音频有内容时显示乐谱图标
        }
        return '🎵';
      case 'pdf':
        if (hasMediaContent) {
          return '📑'; // PDF有内容时显示文档图标
        }
        return '📄';
      default:
        return '🪟';
    }
  };

  // toMediaUrl 函数 - 移动到前面避免依赖问题
  const toMediaUrl = (windowOrContent) => {
    console.log('🔗 toMediaUrl 被调用:', { windowOrContent });
    
    // 兼容旧的调用方式（直接传content）和新的调用方式（传window对象）
    let content, filePath;
    
    if (typeof windowOrContent === 'object' && windowOrContent !== null) {
      // 新方式：传入window对象
      content = windowOrContent.content;
      filePath = windowOrContent.file_path;
    } else {
      // 旧方式：直接传入content
      content = windowOrContent;
    }
    
    // 优先使用 file_path 生成静态文件URL（最可靠）
    if (filePath && typeof filePath === 'string' && filePath.startsWith('files/')) {
      const filename = filePath.substring(6); // 移除 "files/" 前缀
      // 从boardId推断course ID (假设URL格式一致)
      const courseId = 'course-1756987907632'; // TODO: 应该动态获取
      const staticUrl = `http://localhost:8081/static/files/courses/${courseId}/${boardId}/files/${filename}`;
      console.log('🔗 从file_path生成静态URL:', staticUrl);
      return staticUrl;
    }
    
    // 备用：使用 content 字段
    if (content && typeof content === 'string') {
      if (content.startsWith('http://') || content.startsWith('https://')) {
        console.log('🔗 使用content中的完整URL:', content);
        return content;
      }
      if (content.startsWith('/api/')) {
        const fullUrl = `http://localhost:8081${content}`;
        console.log('🔗 使用content中的相对API路径:', fullUrl);
        return fullUrl;
      }
      // 如果content是绝对路径，编码处理
      if (content.includes('\\') || content.includes('/')) {
        const encodedUrl = `http://localhost:8081/api/boards/${boardId}/files/serve?path=${encodeURIComponent(content)}`;
        console.log('🔗 从content生成编码URL:', encodedUrl);
        return encodedUrl;
      }
    }
    
    console.log('🔗 无法生成有效URL，返回空字符串');
    return '';
  };

  // 获取展板窗口数据的函数 - 移动到useEffect之前避免临时死区问题
  const fetchBoardWindows = useCallback(async () => {
    try {
      console.log('🔄 fetchBoardWindows 开始加载展板窗口数据, boardId:', boardId);
      
      if (!boardId) {
        console.log('❌ boardId 为空，跳过加载');
        return;
      }
      
      // 并行加载窗口数据和图标位置数据
      console.log('📤 发送请求获取窗口数据和图标位置');
      const [windowsResponse, iconPositionsResponse] = await Promise.all([
        fetch(`http://localhost:8081/api/boards/${boardId}/windows`),
        fetch(`http://localhost:8081/api/boards/${boardId}/icon-positions`)
      ]);
      
      console.log('📥 窗口数据响应状态:', windowsResponse.status);
      console.log('📥 图标位置响应状态:', iconPositionsResponse.status);
      
      if (windowsResponse.ok) {
        const windowsData = await windowsResponse.json();
        const list = windowsData.windows || [];
        console.log('✅ 成功加载窗口数据:', list.length, '个窗口');
        console.log('📋 窗口详情:', list.map(w => ({ id: w.id, title: w.title, type: w.type, hidden: w.hidden })));
        
        // 加载图标位置数据
        let iconPositionsMap = {};
        if (iconPositionsResponse.ok) {
          const iconData = await iconPositionsResponse.json();
          iconPositionsMap = iconData.iconPositions || {};
          console.log('✅ 成功加载图标位置数据:', Object.keys(iconPositionsMap).length, '个位置');
        } else {
          console.log('⚠️ 图标位置数据加载失败，使用默认位置');
        }
        
        // 打印每个窗口的位置和大小信息
        list.forEach((w, index) => {
          console.log(`窗口 ${index + 1} 从后端加载:`);
          console.log('  ID:', w.id);
          console.log('  类型:', w.type);
          console.log('  位置:', `x:${w.position?.x}, y:${w.position?.y}`);
          console.log('  大小:', `w:${w.size?.width}, h:${w.size?.height}`);
          console.log('  隐藏:', w.hidden);
        });
        
        // 批量恢复隐藏状态，避免闪烁
        const hiddenWindowIds = list.filter(w => w.hidden === true).map(w => w.id);
        console.log('检查隐藏状态:', list.map(w => ({ id: w.id, hidden: w.hidden })));
        console.log('需要恢复隐藏状态的窗口:', hiddenWindowIds);
        
        if (hiddenWindowIds.length > 0 && onBatchWindowHide) {
          console.log('批量恢复隐藏状态的窗口:', hiddenWindowIds);
          onBatchWindowHide(hiddenWindowIds);
        } else {
          console.log('没有需要恢复隐藏状态的窗口');
        }
        
        // 创建包含图标位置信息的桌面图标数据
        const iconsWithPositions = list.map(window => {
          const savedPosition = iconPositionsMap[window.id];
          
          if (savedPosition) {
            // 使用保存的位置和网格信息
            return {
              id: window.id,
              windowId: window.id,
              title: window.title,
              type: window.type,
              content: window.content,
              position: savedPosition.position,
              gridPosition: savedPosition.gridPosition,
              thumbnail: generateThumbnail(window),
              isHidden: window.hidden === true
            };
          } else {
            // 新图标：分配下一个可用的网格位置
            const gridPos = findNextAvailableGridPosition();
            const pixelPos = gridToPixel(gridPos.gridX, gridPos.gridY);
            console.log(`🎯 为新窗口 ${window.title} 分配网格位置: (${gridPos.gridX},${gridPos.gridY})`);
            
            return {
              id: window.id,
              windowId: window.id,
              title: window.title,
              type: window.type,
              content: window.content,
              position: pixelPos,
              gridPosition: gridPos,
              thumbnail: generateThumbnail(window),
              isHidden: window.hidden === true
            };
          }
        });
        
        // 更新网格占用状态和桌面图标
        updateGridOccupancy(iconsWithPositions);
        setDesktopIcons(iconsWithPositions);
        
        // 设置窗口数据，确保每个窗口都有必需的属性
        const validatedWindows = list.map(window => ({
          ...window,
          // 处理位置数据：支持嵌套格式 (position.x) 和扁平格式 (x)
          position: window.position || { 
            x: window.x || 100, 
            y: window.y || 100 
          },
          // 处理大小数据：支持嵌套格式 (size.width) 和扁平格式 (width)
          size: window.size || { 
            width: window.width || 400, 
            height: window.height || 300 
          }
        }));
        setWindows(validatedWindows);
        
        // 迁移修复：将历史存量的相对 /api/ 路径改为 8081 绝对路径，避免走到 3000
        for (const w of list) {
          if (typeof w.content === 'string' && w.content.startsWith('/api/')) {
            const fixed = `http://localhost:8081${w.content}`;
            if (fixed !== w.content) {
              const updated = { ...w, content: fixed };
              await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${w.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updated),
              });
            }
          }
        }
      } else {
        console.error('获取窗口失败:', windowsResponse.status);
      }
    } catch (error) {
      console.error('获取窗口失败:', error);
    }
  }, [boardId, onBatchWindowHide]);

  useEffect(() => {
    if (boardId) {
      console.log('🔄 展板ID变化，清理状态并重新加载:', boardId);
      
      // 在切换展板前，先强制保存当前展板的所有窗口状态
      const saveCurrentBoardState = async () => {
        if (windows.length > 0 && previousBoardIdRef.current) {
          console.log('💾 展板切换前强制保存当前窗口状态...');
          isSavingStateRef.current = true;
          
          const savePromises = windows.map(async (window) => {
            try {
              const isHidden = hiddenWindows && hiddenWindows.has(window.id);
              // 使用前一个展板ID来保存当前窗口状态
              const response = await fetch(`http://localhost:8081/api/boards/${previousBoardIdRef.current}/windows/${window.id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                  ...window,
                  hidden: isHidden,
                  updated_at: new Date().toISOString()
                }),
              });
              return response.ok;
            } catch (error) {
              console.error('展板切换前保存失败:', window.id, error);
              return false;
            }
          });
          
          await Promise.all(savePromises);
          console.log('✅ 展板切换前保存完成');
          
          // 短暂延迟确保保存操作完成
          await new Promise(resolve => setTimeout(resolve, 500));
          isSavingStateRef.current = false;
        }
      };
      
      // 执行保存并继续切换流程
      saveCurrentBoardState().then(() => {
        // 清理缓存数据
        console.log('🧹 清理浏览器缓存数据');
        
        // 先清空隐藏状态，避免切换时闪烁
        if (onClearHiddenWindows) {
          onClearHiddenWindows();
        }
        
        // 重置所有状态
        console.log('🧹 重置组件状态');
        setWindows([]); // 清空窗口数据
        setDesktopIcons([]); // 清空桌面图标
        setIsDragging(false);
        setIsResizing(false);
        setWindowZIndexes({});
        setEditingTitleId(null); // 重置编辑状态
        setEditingTitleValue('');
        maxZIndexRef.current = 100;
        
        // 清理事件监听器
        cleanupResizeListeners();
        cleanupDragListeners();
        
        // 重新加载窗口数据
        console.log('🔄 开始重新加载窗口数据');
        fetchBoardWindows();
        
        // 更新前一个展板ID为当前展板ID
        previousBoardIdRef.current = boardId;
      }).catch((error) => {
        console.error('❌ 展板切换前保存失败:', error);
        // 即使保存失败，也继续切换流程
        fetchBoardWindows();
        previousBoardIdRef.current = boardId;
      });
    }
  }, [boardId]);

  // 监听文件监控事件
  useEffect(() => {
    const handleFileWatcherUpdate = (event) => {
      const { type, board_id, window_id } = event.detail;
      
      // 只处理当前展板的事件
      if (board_id && board_id !== boardId) {
        return;
      }
      
      // 如果正在保存窗口状态，忽略文件变化事件，避免循环重新加载
      if (isSavingStateRef.current) {
        console.log('🚫 正在保存窗口状态，忽略文件监控事件:', event.detail);
        return;
      }
      
      console.log('📡 BoardCanvas收到文件监控事件:', event.detail);
      
      switch (type) {
        case 'reload_windows':
          // 重新加载窗口数据和桌面图标 - 使用完整的加载函数确保一致性
          console.log('🔄 文件监控触发：重新加载展板数据');
          fetchBoardWindows();
          break;
        case 'window_deleted':
          // 移除对应的桌面图标
          setDesktopIcons(prev => prev.filter(icon => icon.windowId !== window_id));
          break;
        default:
          console.log('未处理的文件监控事件类型:', type);
      }
    };

    // 添加事件监听器
    window.addEventListener('fileWatcherUpdate', handleFileWatcherUpdate);
    
    // 清理函数
    return () => {
      window.removeEventListener('fileWatcherUpdate', handleFileWatcherUpdate);
    };
  }, [boardId, fetchBoardWindows]);

  // 通知App组件窗口变化
  useEffect(() => {
    if (onWindowsChange) {
      onWindowsChange(windows);
    }
  }, [windows, onWindowsChange]);

  // 同步窗口数据到桌面图标 - 包括所有窗口（显示和隐藏的）
  useEffect(() => {
    console.log('🎯 同步窗口数据到桌面图标');
    console.log('🎯 当前窗口数量:', windows.length);
    console.log('🎯 当前桌面图标数量:', desktopIcons.length);
    console.log('🎯 隐藏窗口数量:', hiddenWindows.size);
    
    const icons = windows.map(window => {
      // 查找是否已有该图标，保持位置和网格信息
      const existingIcon = desktopIcons.find(icon => icon.id === window.id);
      
      if (existingIcon) {
        console.log(`🎯 保持现有图标位置: ${window.title} (${window.id})`);
        // 保持现有图标的位置和网格信息
      return {
        id: window.id,
        windowId: window.id,
        title: window.title,
        type: window.type,
        content: window.content,
          position: existingIcon.position,
          gridPosition: existingIcon.gridPosition,
        thumbnail: generateThumbnail(window),
          isHidden: hiddenWindows.has(window.id)
        };
      } else {
        // 新图标：分配下一个可用的网格位置
        const gridPos = findNextAvailableGridPosition();
        const pixelPos = gridToPixel(gridPos.gridX, gridPos.gridY);
        
        console.log(`🎯 创建新图标: ${window.title} (${window.id}) 位置: (${gridPos.gridX},${gridPos.gridY})`);
        
        return {
          id: window.id,
          windowId: window.id,
          title: window.title,
          type: window.type,
          content: window.content,
          position: pixelPos,
          gridPosition: gridPos,
          thumbnail: generateThumbnail(window),
          isHidden: hiddenWindows.has(window.id)
        };
      }
    });
    
    console.log('🎯 生成的图标数据:', icons.map(i => ({ id: i.id, title: i.title, isHidden: i.isHidden })));
    
    // 更新网格占用状态
    updateGridOccupancy(icons);
    setDesktopIcons(icons);
    
    console.log('🎯 桌面图标同步完成');
  }, [windows, hiddenWindows]);

  // 窗口焦点管理
  const handleWindowFocusLocal = (windowId) => {
    console.log('窗口获得焦点:', windowId);
    
    // 通知App组件焦点变化
    if (onWindowFocus) {
      onWindowFocus(windowId);
    }
    
    // 更新z-index，让当前窗口置顶
    setWindowZIndexes(prev => {
      const newZIndex = maxZIndexRef.current + 1;
      maxZIndexRef.current = newZIndex;
      
      return {
        ...prev,
        [windowId]: newZIndex
      };
    });
  };

  // 获取窗口的z-index
  const getWindowZIndex = (windowId) => {
    if (isDragging && dragState.current.windowId === windowId) {
      return 9999; // 拖拽时最高
    }
    if (isResizing && resizeState.current.windowId === windowId) {
      return 9999; // 缩放时最高
    }
    return windowZIndexes[windowId] || 100;
  };

  // 开始编辑窗口标题
  const startEditingTitle = (windowId, currentTitle) => {
    setEditingTitleId(windowId);
    setEditingTitleValue(currentTitle);
    console.log('开始编辑标题:', windowId, currentTitle);
  };

  // 完成标题编辑
  const finishEditingTitle = async () => {
    if (!editingTitleId) return;
    
    const newTitle = editingTitleValue.trim();
    if (newTitle === '') {
      // 如果标题为空，取消编辑
      setEditingTitleId(null);
      setEditingTitleValue('');
      return;
    }

    try {
      const windowObj = windows.find(w => w.id === editingTitleId);
      if (windowObj && windowObj.title !== newTitle) {
        const updatedWindow = { 
          ...windowObj, 
          title: newTitle
        };
        
        const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${editingTitleId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updatedWindow),
        });

        if (response.ok) {
          // 更新本地状态
          setWindows(prevWindows => 
            prevWindows.map(w => 
              w.id === editingTitleId 
                ? { ...w, title: newTitle }
                : w
            )
          );
          console.log('标题更新成功:', newTitle);
        } else {
          console.error('更新标题失败:', response.status);
        }
      }
    } catch (error) {
      console.error('更新标题错误:', error);
    }

    setEditingTitleId(null);
    setEditingTitleValue('');
  };

  // 取消标题编辑
  const cancelEditingTitle = () => {
    setEditingTitleId(null);
    setEditingTitleValue('');
    console.log('取消编辑标题');
  };

  // 窗口类型名称映射
  const getWindowTypeName = (type) => {
    const typeNames = {
      text: '文本',
      image: '图片',
      video: '视频',
      audio: '音频',
      pdf: 'PDF'
    };
    return typeNames[type] || '窗口';
  };

  // 生成唯一的窗口名称，处理重复名称
  const generateUniqueWindowName = (baseName, existingWindows = windows) => {
    const existingNames = existingWindows.map(w => w.title.toLowerCase());
    
    // 如果基础名称不存在，直接返回
    if (!existingNames.includes(baseName.toLowerCase())) {
      return baseName;
    }
    
    // 找到合适的编号
    let counter = 1;
    let newName;
    do {
      newName = `${baseName}(${counter})`;
      counter++;
    } while (existingNames.includes(newName.toLowerCase()));
    
    return newName;
  };

  // 从文件名提取基础名称（去掉扩展名）
  const getBaseNameFromFileName = (fileName) => {
    if (!fileName) return '';
    const lastDotIndex = fileName.lastIndexOf('.');
    return lastDotIndex > 0 ? fileName.substring(0, lastDotIndex) : fileName;
  };

  // 根据文件类型确定窗口类型
  const getWindowTypeFromFile = (file) => {
    const fileName = file.name.toLowerCase();
    const fileType = file.type.toLowerCase();
    
    // 图片类型
    if (fileType.startsWith('image/') || /\.(jpg|jpeg|png|gif|bmp|webp|svg)$/.test(fileName)) {
      return 'image';
    }
    
    // 视频类型
    if (fileType.startsWith('video/') || /\.(mp4|avi|mov|wmv|flv|webm|mkv|m4v)$/.test(fileName)) {
      return 'video';
    }
    
    // 音频类型
    if (fileType.startsWith('audio/') || /\.(mp3|wav|flac|aac|ogg|wma|m4a)$/.test(fileName)) {
      return 'audio';
    }
    
    // PDF类型
    if (fileType === 'application/pdf' || fileName.endsWith('.pdf')) {
      return 'pdf';
    }
    
    // 文本类型
    if (fileType.startsWith('text/') || /\.(txt|md|json|xml|csv|log)$/.test(fileName)) {
      return 'text';
    }
    
    // 默认为文本类型
    return 'text';
  };

  // 处理文件拖放
  const handleFileDrop = async (files, dropX, dropY) => {
    console.log('🚀 handleFileDrop 开始处理文件');
    if (!files || files.length === 0) {
      console.log('❌ 没有文件需要处理');
      return;
    }
    
    if (!boardId) {
      console.log('❌ 没有选中的展板ID');
      return;
    }
    
    console.log(`🚀 开始处理 ${files.length} 个文件`);
    
    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      console.log(`🚀 处理第 ${i + 1} 个文件: ${file.name}`);
      
      try {
        // 确定窗口类型
        const windowType = getWindowTypeFromFile(file);
        const baseTitle = getBaseNameFromFileName(file.name);
        const uniqueTitle = generateUniqueWindowName(baseTitle);
        
        console.log(`📋 文件信息:
          - 文件名: ${file.name}
          - 文件类型: ${file.type}
          - 窗口类型: ${windowType}
          - 窗口标题: ${uniqueTitle}
          - 拖放位置: (${dropX}, ${dropY})`);
        
        // 创建窗口
        const windowData = {
          type: windowType,
          title: uniqueTitle,
          content: '',
          position: { 
            x: Math.round(dropX + Math.random() * 50), // 添加一点随机偏移避免重叠
            y: Math.round(dropY + Math.random() * 50) 
          },
          size: { width: 400, height: 300 }
        };

        console.log('📤 发送创建窗口请求:', windowData);
        const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(windowData),
        });

        console.log('📥 创建窗口响应状态:', response.status);
        
        if (response.ok) {
          const newWindow = await response.json();
          console.log('✅ 创建窗口成功:', newWindow);
          
          // 确定文件类型目录
          const fileCategory = windowType === 'image' ? 'images' : 
                              windowType === 'video' ? 'videos' :
                              windowType === 'audio' ? 'audios' :
                              windowType === 'pdf' ? 'pdfs' : 'files';
          
          console.log(`📤 开始上传文件到类别: ${fileCategory}`);
          
          // 上传文件并更新窗口内容
          await handleUpload(newWindow.id, fileCategory, [file]);
          
          console.log('✅ 文件上传完成，准备刷新窗口列表');
          
          // 重新加载窗口数据以显示新窗口
          setTimeout(() => {
            console.log('🔄 刷新窗口列表');
            fetchBoardWindows();
          }, 500);
        } else {
          const errorText = await response.text();
          console.error('❌ 创建窗口失败:', response.status, errorText);
        }
      } catch (error) {
        console.error('❌ 处理文件拖放失败:', error);
      }
    }
  };

  // 拖放状态
  const [isDragOver, setIsDragOver] = useState(false);

  // 拖放事件处理
  const handleDragEnter = (e) => {
    e.preventDefault();
    console.log('🔵 handleDragEnter 触发');
    setIsDragOver(true);
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    console.log('🔵 handleDragLeave 触发');
    // 只有当鼠标真正离开canvas-area时才取消状态
    if (!e.currentTarget.contains(e.relatedTarget)) {
      setIsDragOver(false);
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'copy';
    console.log('🔵 handleDragOver 触发，文件数量:', e.dataTransfer.files.length);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragOver(false);
    console.log('🔥 handleDrop 触发！');
    
    const files = Array.from(e.dataTransfer.files);
    console.log('🔥 拖放的文件:', files.map(f => ({ name: f.name, type: f.type, size: f.size })));
    
    if (files.length > 0) {
      // 获取拖放位置
      const rect = e.currentTarget.getBoundingClientRect();
      const dropX = e.clientX - rect.left;
      const dropY = e.clientY - rect.top;
      
      console.log('🔥 文件拖放到位置:', dropX, dropY, '文件数量:', files.length);
      console.log('🔥 当前boardId:', boardId);
      handleFileDrop(files, dropX, dropY);
    } else {
      console.log('❌ 没有检测到文件');
    }
  };

  // 创建新的打字机模式项目窗口
  const handleCreateProject = async () => {
    try {
      const baseTitle = '新建项目';
      const uniqueTitle = generateUniqueWindowName(baseTitle);
      
      const windowData = {
        type: 'text',  // 固定为文本类型，支持打字机模式
        title: uniqueTitle,
        content: '',   // 初始内容为空
        position: { 
          x: Math.round(100 + Math.random() * 200), 
          y: Math.round(100 + Math.random() * 200) 
        },
        size: { width: 800, height: 600 }  // 更大的窗口尺寸，适合打字机模式
      };

      console.log('🎯 创建新项目窗口:', windowData);

      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(windowData),
      });

      if (response.ok) {
        const newWindow = await response.json();
        console.log('✅ 创建项目窗口成功:', newWindow);
        
        // 直接添加到本地状态，避免重新加载所有窗口
        setWindows(prev => [...prev, newWindow]);
        
        // 新创建的窗口自动获得焦点
        setTimeout(() => {
          handleWindowFocusLocal(newWindow.id);
        }, 100);
      } else {
        console.error('❌ 创建项目窗口失败:', response.status);
      }
    } catch (error) {
      console.error('❌ 创建项目窗口异常:', error);
    }
  };

  const handleCreateWindow = async (type) => {
    try {
      const baseTitle = `新建${getWindowTypeName(type)}`;
      const uniqueTitle = generateUniqueWindowName(baseTitle);
      
      const windowData = {
        type,
        title: uniqueTitle,
        content: '',
        position: { 
          x: Math.round(100 + Math.random() * 200), 
          y: Math.round(100 + Math.random() * 200) 
        },
        size: { width: 300, height: 200 }
      };

      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(windowData),
      });

      if (response.ok) {
        const newWindow = await response.json();
        console.log('创建窗口成功:', newWindow);
        
        // 直接添加到本地状态，避免重新加载所有窗口
        setWindows(prev => [...prev, newWindow]);
        setShowCreateMenu(false);
        
        // 新创建的窗口自动获得焦点
        setTimeout(() => {
          handleWindowFocusLocal(newWindow.id);
        }, 100);
      }
    } catch (error) {
      console.error('创建窗口失败:', error);
    }
  };

  // 统一的文件上传处理
  const handleUpload = async (windowId, fileCategory, files) => {
    console.log('📤 handleUpload 开始:', { windowId, fileCategory, filesCount: files?.length });
    if (!files || files.length === 0) return;
    
    const file = files[0];
    console.log('📤 上传文件信息:', {
      name: file.name,
      size: file.size,
      type: file.type,
      lastModified: file.lastModified
    });
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('window_id', windowId); // 传递window_id用于新的命名规则
    
    try {
      const url = `http://localhost:8081/api/boards/${boardId}/upload?file_type=${encodeURIComponent(fileCategory)}`;
      console.log('📤 发送上传请求到:', url);
      
      const resp = await fetch(url, {
        method: 'POST',
        body: formData,
      });
      
      console.log('📤 上传响应状态:', resp.status, resp.statusText);
      
      if (resp.ok) {
        const data = await resp.json();
        console.log('📤 服务器响应数据:', data);
        
        // 优先保存可直接访问的 file_url，避免路径与编码问题
        const contentValue = data.file_url || data.file_path;
        console.log('📤 选择的content值:', contentValue);
        const target = windows.find(w => w.id === windowId);
        if (target) {
          const fileName = file.name;
          const baseFileName = getBaseNameFromFileName(fileName);
          
          // 简化逻辑：直接使用文件名重命名窗口
          const newTitle = generateUniqueWindowName(baseFileName, windows.filter(w => w.id !== windowId));
          
          const updated = { 
            ...target, 
            content: contentValue,
            title: newTitle
          };
          
          await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(updated),
          });
          
          // 更新本地状态
          setWindows(prevWindows => 
            prevWindows.map(w => 
              w.id === windowId 
                ? { ...w, content: contentValue, title: newTitle }
                : w
            )
          );
          
          if (window.__whatnoteLog) {
            window.__whatnoteLog(`上传完成: ${file.name} -> ${contentValue}，窗口已重命名为: ${newTitle}`, 'message');
          }
        }
      } else {
        const errText = await resp.text();
        if (window.__whatnoteLog) window.__whatnoteLog(`上传失败(${resp.status}): ${errText}`, 'error');
      }
    } catch (err) {
      console.error('上传失败:', err);
    }
  };
  // 将 \( ... \) / \[ ... \] 转为 $...$ / $$...$$，兼容用户输入
  const normalizeLatexDelimiters = (text) => {
    if (!text) return '';
    // 块公式 \\[[...]] -> $$...$$
    let result = text.replace(/\\\[(\s*[\s\S]*?)\\\]/g, (m, g1) => `$$${g1}$$`);
    // 行内公式 \\(...\) -> $...$
    result = result.replace(/\\\((\s*[\s\S]*?)\\\)/g, (m, g1) => `$${g1}$`);
    return result;
  };


  const handleWindowMove = async (windowId, newPosition) => {
    try {
      const window = windows.find(w => w.id === windowId);
      if (window) {
        const updatedWindow = { ...window, position: newPosition };
        
        const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(updatedWindow),
        });

        if (response.ok) {
          // 不需要重新获取，本地状态已经是最新的
        }
      }
    } catch (error) {
      console.error('更新窗口位置失败:', error);
    }
  };


  // 统一的窗口状态保存函数
  const saveWindowState = async (windowId, updates) => {
    try {
      const window = windows.find(w => w.id === windowId);
      if (!window) {
        console.error('❌ 未找到要保存的窗口:', windowId);
        return false;
      }
      
      // 设置保存状态标记
      isSavingStateRef.current = true;
      
      // 合并更新数据，优先使用传入的hidden值
      const updatedWindow = { 
        ...window, 
        ...updates,
        // 确保必要字段存在
        id: windowId,
        updated_at: new Date().toISOString(),
        // 如果updates中没有hidden字段，则根据hiddenWindows状态判断
        hidden: updates.hasOwnProperty('hidden') 
          ? updates.hidden 
          : (hiddenWindows && hiddenWindows.has(windowId) ? true : false),
        // 确保位置和大小数据格式正确
        position: updates.position || window.position || { x: 100, y: 100 },
        size: updates.size || window.size || { width: 400, height: 300 }
      };
      
      // 只在非内容更新时输出详细日志
      if (!updates.hasOwnProperty('content')) {
        console.log('💾 保存窗口状态:', windowId, '更新字段:', Object.keys(updates));
        console.log('📍 窗口位置:', updatedWindow.position);
        console.log('📏 窗口大小:', updatedWindow.size);
        console.log('👁️ 隐藏状态:', updatedWindow.hidden);
      }
      
      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updatedWindow),
      });

      if (response.ok) {
        const result = await response.json();
        console.log('✅ 窗口状态保存成功:', windowId);
        
        // 延迟清除保存状态标记，给文件监控一些时间
        setTimeout(() => {
          isSavingStateRef.current = false;
        }, 2000);
        
        return true;
      } else {
        const errorText = await response.text();
        console.error('❌ 窗口状态保存失败:', response.status, errorText);
        isSavingStateRef.current = false;
        return false;
      }
    } catch (error) {
      console.error('❌ 保存窗口状态异常:', error);
      isSavingStateRef.current = false;
      return false;
    }
  };

  // 优化的窗口内容保存函数
  const handleWindowContentChange = async (windowId, newContent, mode = 'content') => {
    try {
      if (mode === 'upload' && newContent instanceof File) {
        // 处理文件上传
        console.log('📁 开始上传文件:', newContent.name, newContent.type, newContent.size);
        await handleFileUploadToWindow(windowId, newContent);
      } else {
        // 处理内容更新
        console.log('📝 保存窗口内容:', windowId, '内容长度:', newContent.length);
        
        // 更新本地状态
        setWindows(prevWindows => 
          prevWindows.map(w => 
            w.id === windowId 
              ? { ...w, content: newContent }
              : w
          )
        );
        
        // 保存到后端
        await saveWindowState(windowId, { content: newContent });
        console.log('✅ 窗口内容保存成功:', windowId);
      }
    } catch (error) {
      console.error('❌ 窗口内容保存失败:', error);
    }
  };

  // 处理文件上传到窗口
  const handleFileUploadToWindow = async (windowId, file) => {
    try {
      // 创建FormData
      const formData = new FormData();
      formData.append('file', file);
      
      // 获取窗口信息
      const window = windows.find(w => w.id === windowId);
      if (!window) {
        throw new Error('窗口不存在');
      }
      
      console.log('📤 上传文件到窗口:', windowId, '文件名:', file.name);
      
      // 发送上传请求
      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/upload`, {
        method: 'POST',
        body: formData,
      });
      
      if (response.ok) {
        const result = await response.json();
        console.log('✅ 文件上传成功:', result);
        
        // 更新本地窗口状态
        setWindows(prevWindows => 
          prevWindows.map(w => 
            w.id === windowId 
              ? { 
                  ...w, 
                  type: result.window_type,
                  title: result.filename,
                  file_path: result.file_path,
                  content: result.content || ''
                }
              : w
          )
        );
        
        // 刷新窗口列表以获取最新状态
        await fetchBoardWindows();
        
      } else {
        const errorData = await response.json();
        throw new Error(errorData.detail || '上传失败');
      }
      
    } catch (error) {
      console.error('❌ 文件上传失败:', error);
      throw error;
    }
  };

  // 关闭窗口（隐藏而不删除）- 使用App传来的处理函数
  const handleWindowCloseLocal = async (windowId) => {
    console.log('BoardCanvas: 关闭窗口（隐藏）:', windowId);
    if (onWindowClose) {
      onWindowClose(windowId);
      // 立即保存隐藏状态到后端，明确设置hidden为true
      await saveWindowState(windowId, { hidden: true });
    }
  };

  // 真正删除窗口（将来通过右键菜单调用）
  const handleWindowDelete = async (windowId) => {
    if (window.confirm('确定要将这个窗口移动到回收站吗？')) {
      try {
        const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}`, {
          method: 'DELETE',
        });

        if (response.ok) {
          console.log('开始移动窗口到回收站:', windowId);
          // 从本地窗口列表中移除
          setWindows(prev => {
            const filtered = prev.filter(w => w.id !== windowId);
            console.log('从窗口列表移除窗口:', windowId, '剩余窗口数:', filtered.length);
            return filtered;
          });
          // 通知App组件处理状态更新（App组件会处理隐藏状态的清理）
          if (onWindowDelete) {
            onWindowDelete(windowId);
          }
          console.log('✅ 窗口已移动到回收站:', windowId);
        }
      } catch (error) {
        console.error('移动窗口到回收站失败:', error);
      }
    }
  };
  
  // 永久删除窗口
  const handleWindowPermanentDelete = async (windowId) => {
    if (window.confirm('确定要永久删除这个窗口及其内容吗？此操作无法撤销！')) {
      try {
        const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}?permanent=true`, {
          method: 'DELETE',
        });

        if (response.ok) {
          console.log('开始永久删除窗口:', windowId);
          // 从本地窗口列表中移除
          setWindows(prev => {
            const filtered = prev.filter(w => w.id !== windowId);
            console.log('从窗口列表移除窗口:', windowId, '剩余窗口数:', filtered.length);
            return filtered;
          });
          // 通知App组件处理状态更新（App组件会处理隐藏状态的清理）
          if (onWindowDelete) {
            onWindowDelete(windowId);
          }
          console.log('✅ 窗口永久删除成功:', windowId);
        }
      } catch (error) {
        console.error('永久删除窗口失败:', error);
      }
    }
  };

  const handleWindowMinimizeLocal = (windowId) => {
    console.log('最小化/恢复窗口:', windowId);
    if (onWindowMinimize) {
      onWindowMinimize(windowId);
    }
  };

  // 桌面图标交互函数
  const handleIconDoubleClick = async (iconId) => {
    const window = windows.find(w => w.id === iconId);
    if (window) {
      // 如果窗口是隐藏的，先显示
      if (hiddenWindows && hiddenWindows.has(iconId)) {
        console.log('恢复隐藏窗口:', iconId);
        if (onWindowShow) {
          onWindowShow(iconId); // 从隐藏列表中移除
          // 立即保存显示状态到后端，明确设置hidden为false
          await saveWindowState(iconId, { hidden: false });
        }
        // 显示后设置焦点
        setTimeout(() => {
          handleWindowFocusLocal(iconId);
        }, 50);
      } else if (minimizedWindows.has(iconId)) {
        // 如果窗口是最小化的，先恢复
        handleWindowMinimizeLocal(iconId);
      } else {
        // 否则直接聚焦
        handleWindowFocusLocal(iconId);
      }
    }
  };

  const handleIconClick = (iconId) => {
    setSelectedIconId(iconId);
  };

  const handleDesktopClick = (e) => {
    if (e.target === e.currentTarget) {
      setSelectedIconId(null);
    }
  };

  const startIconDrag = (e, iconId) => {
    e.preventDefault();
    
    const icon = desktopIcons.find(icon => icon.id === iconId);
    const dragData = {
      iconId: iconId,
      startX: e.clientX,
      startY: e.clientY,
      initialX: icon?.position?.x || 0,
      initialY: icon?.position?.y || 0
    };
    
    setIsDraggingIcon(true);
    setIconDragData(dragData);
  };

  const handleIconDrag = (e) => {
    if (!isDraggingIcon || !iconDragData) return;
    
    const deltaX = e.clientX - iconDragData.startX;
    const deltaY = e.clientY - iconDragData.startY;
    
    const newX = Math.max(0, iconDragData.initialX + deltaX);
    const newY = Math.max(0, iconDragData.initialY + deltaY);
    
    // 限制拖拽范围在画布内
    const canvasWidth = window.innerWidth - 250;
    const canvasHeight = window.innerHeight - 100;
    const clampedX = Math.min(newX, canvasWidth - ICON_SIZE);
    const clampedY = Math.min(newY, canvasHeight - ICON_SIZE);
    
    setDesktopIcons(prev => prev.map(icon => 
      icon.id === iconDragData.iconId 
        ? {
            ...icon,
            position: {
              x: clampedX,
              y: clampedY
            }
          }
        : icon
    ));
  };

  const stopIconDrag = () => {
    if (!iconDragData) return;
    
    // 获取当前拖拽图标的最新位置
    const draggedIcon = desktopIcons.find(icon => icon.id === iconDragData.iconId);
    if (draggedIcon) {
      // 将像素位置转换为网格位置（吸附到最近的网格）
      const { gridX, gridY } = pixelToGrid(draggedIcon.position?.x || 0, draggedIcon.position?.y || 0);
      const snappedPixelPos = gridToPixel(gridX, gridY);
      
      // 检查目标网格位置是否被占用（排除自己）
      const gridKey = `${gridX},${gridY}`;
      const currentIcon = desktopIcons.find(icon => icon.id === iconDragData.iconId);
      const isSamePosition = currentIcon?.gridPosition?.gridX === gridX && 
                            currentIcon?.gridPosition?.gridY === gridY;
      
      const isOccupied = desktopGridRef.current.has(gridKey) && !isSamePosition;
      
      if (isOccupied) {
        // 如果目标位置被占用，恢复到原始位置
        setDesktopIcons(prev => prev.map(icon => 
          icon.id === iconDragData.iconId 
            ? {
                ...icon,
                position: { x: iconDragData.initialX, y: iconDragData.initialY }
              }
            : icon
        ));
      } else {
        // 更新图标位置和网格信息
        setDesktopIcons(prev => {
          const updatedIcons = prev.map(icon => {
            if (icon.id === iconDragData.iconId) {
              // 释放旧的网格位置
              if (icon.gridPosition) {
                const oldGridKey = `${icon.gridPosition.gridX},${icon.gridPosition.gridY}`;
                desktopGridRef.current.delete(oldGridKey);
              }
              
              // 占用新的网格位置
              desktopGridRef.current.add(gridKey);
              
              return {
                ...icon,
                position: snappedPixelPos,
                gridPosition: { gridX, gridY }
              };
            }
            return icon;
          });
          
          // 保存图标位置到后端
          saveIconPositions(updatedIcons);
          return updatedIcons;
        });
      }
    }
    
    setIsDraggingIcon(false);
    setIconDragData(null);
  };

  // 右键菜单处理函数
  const showContextMenu = (e, type, targetIconId = null) => {
    e.preventDefault();
    setContextMenu({
      visible: true,
      x: e.clientX,
      y: e.clientY,
      type,
      targetIconId
    });
  };

  const hideContextMenu = () => {
    setContextMenu(prev => ({ ...prev, visible: false }));
  };

  // 桌面右键菜单处理
  const handleDesktopRightClick = (e) => {
    e.preventDefault();
    // 在桌面空白区域或空展板提示上显示右键菜单
    showContextMenu(e, 'desktop');
  };

  // 图标右键菜单处理
  const handleIconRightClick = (e, iconId) => {
    e.stopPropagation();
    showContextMenu(e, 'icon', iconId);
  };

  // 右键菜单项点击处理
  const handleContextMenuAction = (action, targetId = null) => {
    hideContextMenu();
    
    switch (action) {
      case 'new-project':
        // 创建新的打字机模式文本窗口
        handleCreateProject();
        break;
      case 'rename':
        if (targetId) {
          // 开始重命名图标对应的窗口
          console.log('🎯 开始重命名流程:', targetId);
          console.log('🎯 当前桌面图标数量:', desktopIcons.length);
          console.log('🎯 当前窗口数量:', windows.length);
          
          setEditingTitleId(targetId);
          // 优先从桌面图标获取标题，如果找不到则从窗口获取
          const icon = desktopIcons.find(i => i.id === targetId);
          const window = windows.find(w => w.id === targetId);
          const currentTitle = icon?.title || window?.title || '';
          setEditingTitleValue(currentTitle);
          
          console.log('🎯 找到的图标:', icon);
          console.log('🎯 找到的窗口:', window);
          console.log('🎯 设置编辑标题ID:', targetId);
          console.log('🎯 设置编辑标题值:', currentTitle);
        }
        break;
      case 'delete':
        if (targetId) {
          // 删除窗口
          handleWindowDelete(targetId);
        }
        break;
      default:
        break;
    }
  };

  // 添加图标拖拽事件监听器
  useEffect(() => {
    if (isDraggingIcon) {
      document.addEventListener('mousemove', handleIconDrag);
      document.addEventListener('mouseup', stopIconDrag);
      return () => {
        document.removeEventListener('mousemove', handleIconDrag);
        document.removeEventListener('mouseup', stopIconDrag);
      };
    }
  }, [isDraggingIcon, iconDragData, handleIconDrag, stopIconDrag]);

  // 全局点击事件监听器，用于隐藏右键菜单
  useEffect(() => {
    const handleGlobalClick = (e) => {
      if (contextMenu.visible) {
        hideContextMenu();
      }
    };

    document.addEventListener('click', handleGlobalClick);
    return () => {
      document.removeEventListener('click', handleGlobalClick);
    };
  }, [contextMenu.visible]);

  // 清理拖拽事件监听器
  const cleanupDragListeners = () => {
    document.removeEventListener('mousemove', handleDragging);
    document.removeEventListener('mouseup', stopDrag);
    document.removeEventListener('mouseleave', stopDrag);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
  };

  // 新的拖拽系统 - 使用鼠标事件而非drag API
  const startDrag = (e, windowId) => {
    console.log('🔵 startDrag 函数被调用，窗口ID:', windowId);
    e.preventDefault();
    e.stopPropagation();
    
    const windowObj = windows.find(w => w.id === windowId);
    if (!windowObj) return;
    
    // 拖拽时设置焦点
    handleWindowFocusLocal(windowId);
    
    // 清理任何现有的拖拽监听器
    cleanupDragListeners();
    
    dragState.current = {
      active: true,
      windowId,
      startX: e.clientX,
      startY: e.clientY,
      initialX: windowObj.position?.x || 100,
      initialY: windowObj.position?.y || 100,
      originalX: windowObj.position?.x || 100, // 记录开始拖拽时的原始位置
      originalY: windowObj.position?.y || 100,
    };
    
    setIsDragging(true);
    document.addEventListener('mousemove', handleDragging, { passive: false });
    document.addEventListener('mouseup', stopDrag, { once: true });
    document.addEventListener('mouseleave', stopDrag, { once: true });
    
    // 添加视觉反馈
    document.body.style.cursor = 'move';
    document.body.style.userSelect = 'none';
  };

  const handleDragging = (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    const ds = dragState.current;
    if (!ds.active) {
      cleanupDragListeners();
      return;
    }
    
    // 记录当前鼠标位置
    ds.lastX = e.clientX;
    ds.lastY = e.clientY;
    
    const deltaX = e.clientX - ds.startX;
    const deltaY = e.clientY - ds.startY;
    
    setWindows(prev => prev.map(w => w.id === ds.windowId ? ({
      ...w,
      position: { 
        x: Math.max(0, ds.initialX + deltaX), 
        y: Math.max(0, ds.initialY + deltaY) 
      }
    }) : w));
  };

  const stopDrag = async () => {
    console.log('🔵 stopDrag 函数被调用');
    const ds = dragState.current;
    if (!ds.active) {
      console.log('⚠️ 拖拽状态未激活，跳过');
      return;
    }
    
    // 立即标记为非活动状态
    dragState.current.active = false;
    setIsDragging(false);
    
    // 清理事件监听器和样式
    cleanupDragListeners();
    
    // 计算最终位置 - 如果没有实际拖拽，保持原位置
    console.log('拖拽状态数据:', {
      initialX: ds.initialX,
      initialY: ds.initialY,
      startX: ds.startX,
      startY: ds.startY,
      lastX: ds.lastX,
      lastY: ds.lastY,
      hasLastPosition: ds.lastX !== undefined && ds.lastY !== undefined
    });
    
    let finalPosition;
    if (ds.lastX !== undefined && ds.lastY !== undefined) {
      // 有实际拖拽
      finalPosition = {
        x: Math.max(0, ds.initialX + ds.lastX - ds.startX),
        y: Math.max(0, ds.initialY + ds.lastY - ds.startY)
      };
      console.log('计算最终位置（有拖拽）:', finalPosition);
    } else {
      // 没有实际拖拽，保持原位置
      finalPosition = {
        x: ds.initialX,
        y: ds.initialY
      };
      console.log('计算最终位置（无拖拽）:', finalPosition);
    }
    
    // 使用状态更新回调确保拿到最新状态
    setWindows(prevWindows => {
      const target = prevWindows.find(w => w.id === ds.windowId);
      if (target) {
        const updatedTarget = { ...target, position: finalPosition };
        
        // 使用原始位置进行比较，而不是当前状态
        const positionChanged = ds.originalX !== finalPosition.x || ds.originalY !== finalPosition.y;
        console.log('检查窗口位置变化:');
        console.log('  窗口ID:', target.id);
        console.log('  原始位置:', `x:${ds.originalX}, y:${ds.originalY}`);
        console.log('  最终位置:', `x:${finalPosition.x}, y:${finalPosition.y}`);
        console.log('  是否改变:', positionChanged);
        
        if (positionChanged) {
          // 延迟保存，防抖机制
          if (windowSaveTimeoutRef.current) {
            clearTimeout(windowSaveTimeoutRef.current);
          }
          
          windowSaveTimeoutRef.current = setTimeout(async () => {
            console.log('准备保存窗口位置:', {
              windowId: target.id,
              position: finalPosition,
            });
            
            // 使用统一的保存函数，确保包含所有状态
            await saveWindowState(target.id, { position: finalPosition });
          }, 300); // 300ms 防抖
        } else {
          console.log('窗口位置未改变，跳过保存');
        }
        
        // 返回更新后的状态
        return prevWindows.map(w => w.id === ds.windowId ? updatedTarget : w);
      }
      return prevWindows;
    });
  };

  // 开始调整尺寸
  const startResize = (e, windowObj) => {
    console.log('🔴 startResize 函数被调用，窗口ID:', windowObj.id);
    e.preventDefault();
    e.stopPropagation();
    
    // 缩放时设置焦点
    handleWindowFocusLocal(windowObj.id);
    
    // 清理任何现有的事件监听器
    cleanupResizeListeners();
    
    resizeState.current = {
      active: true,
      windowId: windowObj.id,
      startX: e.clientX,
      startY: e.clientY,
      startW: windowObj.size.width,
      startH: windowObj.size.height,
      originalW: windowObj.size.width, // 记录开始缩放时的原始大小
      originalH: windowObj.size.height,
    };
    
    // 添加事件监听器到document而不是window，确保更好的事件处理
    document.addEventListener('mousemove', handleResizing, { passive: false });
    document.addEventListener('mouseup', stopResize, { once: true });
    document.addEventListener('mouseleave', stopResize, { once: true }); // 鼠标离开文档时也停止
    
    // 添加视觉反馈
    document.body.style.cursor = 'nw-resize';
    document.body.style.userSelect = 'none';
    setIsResizing(true);
  };

  // 清理缩放事件监听器
  const cleanupResizeListeners = () => {
    document.removeEventListener('mousemove', handleResizing);
    document.removeEventListener('mouseup', stopResize);
    document.removeEventListener('mouseleave', stopResize);
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    setIsResizing(false);
  };

  // 调整中
  const handleResizing = (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    const rs = resizeState.current;
    if (!rs.active) {
      cleanupResizeListeners();
      return;
    }
    
    // 记录当前鼠标位置
    rs.lastX = e.clientX;
    rs.lastY = e.clientY;
    
    const dx = e.clientX - rs.startX;
    const dy = e.clientY - rs.startY;
    
    // 计算新尺寸
    const newWidth = Math.max(200, rs.startW + dx);
    const newHeight = Math.max(150, rs.startH + dy);
    
    setWindows(prev => prev.map(w => w.id === rs.windowId ? ({
      ...w,
      size: { width: newWidth, height: newHeight }
    }) : w));
  };

  // 结束调整并保存
  const stopResize = async () => {
    console.log('🔴 stopResize 函数被调用');
    const rs = resizeState.current;
    if (!rs.active) {
      console.log('⚠️ 缩放状态未激活，跳过');
      return;
    }
    
    // 立即标记为非活动状态
    resizeState.current.active = false;
    
    // 清理事件监听器和样式
    cleanupResizeListeners();
    
    // 计算最终尺寸 - 如果没有实际缩放，保持原尺寸
    console.log('缩放状态数据:', {
      startW: rs.startW,
      startH: rs.startH,
      startX: rs.startX,
      startY: rs.startY,
      lastX: rs.lastX,
      lastY: rs.lastY,
      hasLastPosition: rs.lastX !== undefined && rs.lastY !== undefined
    });
    
    let finalSize;
    if (rs.lastX !== undefined && rs.lastY !== undefined) {
      // 有实际缩放
      finalSize = {
        width: Math.max(200, rs.startW + rs.lastX - rs.startX),
        height: Math.max(150, rs.startH + rs.lastY - rs.startY)
      };
      console.log('计算最终尺寸（有缩放）:', finalSize);
    } else {
      // 没有实际缩放，保持原尺寸
      finalSize = {
        width: rs.startW,
        height: rs.startH
      };
      console.log('计算最终尺寸（无缩放）:', finalSize);
    }
    
    // 使用状态更新回调确保拿到最新状态
    setWindows(prevWindows => {
      const target = prevWindows.find(w => w.id === rs.windowId);
      if (target) {
        const updatedTarget = { ...target, size: finalSize };
        
        // 使用原始大小进行比较，而不是当前状态
        const sizeChanged = rs.originalW !== finalSize.width || rs.originalH !== finalSize.height;
        console.log('检查窗口大小变化:');
        console.log('  窗口ID:', target.id);
        console.log('  原始大小:', `w:${rs.originalW}, h:${rs.originalH}`);
        console.log('  最终大小:', `w:${finalSize.width}, h:${finalSize.height}`);
        console.log('  是否改变:', sizeChanged);
        
        if (sizeChanged) {
          // 延迟保存，防抖机制
          if (windowSaveTimeoutRef.current) {
            clearTimeout(windowSaveTimeoutRef.current);
          }
          
          windowSaveTimeoutRef.current = setTimeout(async () => {
            console.log('准备保存窗口大小:', {
              windowId: target.id,
              size: finalSize,
            });
            
            // 使用统一的保存函数，确保包含所有状态
            await saveWindowState(target.id, { size: finalSize });
          }, 300); // 300ms 防抖
        } else {
          console.log('窗口大小未改变，跳过保存');
        }
        
        // 返回更新后的状态
        return prevWindows.map(w => w.id === rs.windowId ? updatedTarget : w);
      }
      return prevWindows;
    });
  };

  // 定期保存所有窗口状态
  const saveAllWindowStates = useCallback(async () => {
    if (windows.length === 0) return;
    
    // 设置保存状态标记
    isSavingStateRef.current = true;
    
    console.log('🔄 定期保存所有窗口状态...');
    for (const window of windows) {
      try {
        // 获取当前隐藏状态
        const isHidden = hiddenWindows && hiddenWindows.has(window.id);
        
        // 保存窗口的完整状态（不再设置标记，因为已经在外层设置）
        const windowToSave = windows.find(w => w.id === window.id);
        if (!windowToSave) continue;
        
        const updatedWindow = { 
          ...windowToSave, 
          position: window.position,
          size: window.size,
          hidden: isHidden,
          id: window.id,
          updated_at: new Date().toISOString()
        };
        
        const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${window.id}`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(updatedWindow),
        });

        if (response.ok) {
          console.log('✅ 窗口状态保存成功:', window.id);
        } else {
          console.error('❌ 窗口状态保存失败:', window.id, response.status);
        }
      } catch (error) {
        console.error('❌ 定期保存窗口状态失败:', window.id, error);
      }
    }
    
    console.log('✅ 定期保存完成');
    
    // 延迟清除保存状态标记
    setTimeout(() => {
      isSavingStateRef.current = false;
    }, 3000);
  }, [windows, hiddenWindows, boardId]);

  // 启动定期保存
  useEffect(() => {
    // 每30秒定期保存一次所有窗口状态
    periodicSaveIntervalRef.current = setInterval(saveAllWindowStates, 30000);
    
    return () => {
      if (periodicSaveIntervalRef.current) {
        clearInterval(periodicSaveIntervalRef.current);
      }
    };
  }, [saveAllWindowStates]);

  // 页面卸载前保存所有窗口状态
  useEffect(() => {
    const handleBeforeUnload = async (event) => {
      // 同步保存所有窗口状态
      if (windows.length > 0) {
        console.log('🚪 页面即将卸载，强制保存所有窗口状态');
        
        // 创建同步保存Promise数组
        const savePromises = windows.map(async (window) => {
          try {
            const isHidden = hiddenWindows && hiddenWindows.has(window.id);
            return fetch(`http://localhost:8081/api/boards/${boardId}/windows/${window.id}`, {
              method: 'PUT',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                ...window,
                hidden: isHidden,
                updated_at: new Date().toISOString()
              }),
              keepalive: true // 确保请求在页面卸载时仍能发送
            });
          } catch (error) {
            console.error('页面卸载保存失败:', window.id, error);
          }
        });
        
        // 等待所有保存完成（但不阻塞页面卸载）
        Promise.all(savePromises).then(() => {
          console.log('✅ 页面卸载前保存完成');
        }).catch((error) => {
          console.error('❌ 页面卸载前保存出错:', error);
        });
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, [windows, hiddenWindows, boardId]);

  // 组件卸载时清理事件监听器
  useEffect(() => {
    return () => {
      cleanupResizeListeners();
      cleanupDragListeners();
      // 清理保存定时器
      if (windowSaveTimeoutRef.current) {
        clearTimeout(windowSaveTimeoutRef.current);
      }
      // 清理定期保存间隔
      if (periodicSaveIntervalRef.current) {
        clearInterval(periodicSaveIntervalRef.current);
      }
    };
  }, []);

  // 右键菜单组件
  const ContextMenu = ({ visible, x, y, type, onAction }) => {
    if (!visible) return null;

    const desktopMenuItems = [
      { 
        label: '新建项目', 
        action: 'new-project',
        icon: '📝'
      }
    ];

    const iconMenuItems = [
      { 
        label: '重命名', 
        action: 'rename',
        icon: '✏️'
      },
      { type: 'separator' },
      { 
        label: '删除', 
        action: 'delete',
        icon: '🗑️'
      }
    ];

    const menuItems = type === 'desktop' ? desktopMenuItems : iconMenuItems;

    return (
      <div 
        className="context-menu" 
        style={{ 
          left: x, 
          top: y,
          position: 'fixed'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {menuItems.map((item, index) => {
          if (item.type === 'separator') {
            return <div key={index} className="context-menu-separator" />;
          }
          
          return (
            <div
              key={index}
              className={`context-menu-item ${item.hasSubmenu ? 'has-submenu' : ''}`}
              onClick={() => !item.hasSubmenu && onAction(item.action)}
            >
              <div className="context-menu-icon">{item.icon}</div>
              {item.label}
              {item.hasSubmenu && (
                <>
                  <div className="context-menu-submenu-arrow" />
                  <div className="context-submenu">
                    {item.submenuItems.map((subItem, subIndex) => (
                      <div
                        key={subIndex}
                        className="context-menu-item"
                        onClick={(e) => {
                          e.stopPropagation();
                          onAction(subItem.action);
                        }}
                      >
                        <div className="context-menu-icon">{subItem.icon}</div>
                        {subItem.label}
                      </div>
                    ))}
                  </div>
                </>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  if (!boardId) {
    return (
      <div className="board-canvas">
        <div className="welcome-screen">
          <h2>欢迎使用 WhatNote V2</h2>
          <p>请选择一个展板开始工作</p>
        </div>
      </div>
    );
  }

  return (
    <div className="board-canvas">
      <div className="canvas-header">
        <h2>{boardName || '未命名展板'}</h2>
        <div className="canvas-toolbar">
          <button 
            className="create-window-btn"
            onClick={() => setShowCreateMenu(!showCreateMenu)}
          >
            + 创建窗口
          </button>
          
          {showCreateMenu && (
            <div className="create-menu">
              <button onClick={() => handleCreateWindow('text')}>
                📝 文本框
              </button>
              <button onClick={() => handleCreateWindow('image')}>
                🖼️ 图片框
              </button>
              <button onClick={() => handleCreateWindow('video')}>
                🎥 视频框
              </button>
                <button onClick={() => handleCreateWindow('audio')}>
                  🎵 音频框
                </button>
              <button onClick={() => handleCreateWindow('pdf')}>
                📄 PDF框
              </button>
            </div>
          )}
        </div>
      </div>
      
      <div 
        className={`canvas-area ${isDragOver ? 'drag-over' : ''}`}
        onMouseDown={(e) => {
          // 点击空白区域时取消所有窗口焦点和图标选择
          if (e.target === e.currentTarget) {
            if (onWindowFocus) {
              onWindowFocus(null);
            }
            handleDesktopClick(e);
          }
        }}
        onContextMenu={handleDesktopRightClick}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
      >
        {/* 桌面图标 */}
        {desktopIcons.map(icon => (
          <div
            key={icon.id}
            className={`desktop-icon ${selectedIconId === icon.id ? 'selected' : ''} ${icon.isHidden ? 'hidden-window' : ''}`}
            style={{
              left: icon.position?.x || 20,
              top: icon.position?.y || 20,
              position: 'absolute'
            }}
            onClick={() => handleIconClick(icon.id)}
            onDoubleClick={() => handleIconDoubleClick(icon.id)}
            onMouseDown={(e) => {
              if (e.button === 0) { // 只有左键才开始拖拽
                startIconDrag(e, icon.id);
              }
            }}
            onContextMenu={(e) => handleIconRightClick(e, icon.id)}
          >
            <div className="desktop-icon-image">
              {typeof icon.thumbnail === 'string' && icon.thumbnail.startsWith('http') ? (
                <img 
                  src={icon.thumbnail} 
                  alt={icon.title}
                  className="desktop-icon-thumbnail"
                />
              ) : (
                <span className="desktop-icon-emoji">{icon.thumbnail}</span>
              )}
            </div>
            <div className="desktop-icon-label">
              {editingTitleId === icon.id ? (
                <input
                  ref={(input) => {
                    if (input && editingTitleId === icon.id) {
                      console.log('🎯 输入框ref回调，准备聚焦:', icon.id);
                      // 只在首次聚焦时设置光标位置
                      if (!input.hasAttribute('data-focused')) {
                        input.setAttribute('data-focused', 'true');
                        setTimeout(() => {
                          console.log('🎯 执行首次聚焦操作:', icon.id);
                          input.focus();
                          // 将光标移动到文本末尾，而不是选中所有文本
                          const length = input.value.length;
                          input.setSelectionRange(length, length);
                        }, 0);
                      }
                    }
                  }}
                  type="text"
                  className="desktop-icon-rename-input"
                  value={editingTitleValue}
                  onChange={(e) => setEditingTitleValue(e.target.value)}
                  onBlur={finishEditingTitle}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      finishEditingTitle();
                    } else if (e.key === 'Escape') {
                      setEditingTitleId(null);
                      setEditingTitleValue('');
                    }
                  }}
                />
              ) : (
                <span className="desktop-icon-title-text">{icon.title}</span>
              )}
            </div>
          </div>
        ))}
        
        {/* 窗口渲染 */}
        {windows
          .filter(window => {
            const isMinimized = minimizedWindows.has(window.id);
            const isHidden = hiddenWindows.has(window.id);
            
            if (isHidden) {
              return false;
            }
            if (isMinimized) {
              return false;
            }
            return true; // 显示非最小化且非隐藏的窗口
          })
          .map(window => (
            <div
              key={window.id}
              className={`canvas-window ${window.type} ${isDragging && dragState.current.windowId === window.id ? 'dragging' : ''} ${focusedWindowId === window.id ? 'focused' : ''}`}
              style={{
                left: window.position?.x || 100,
                top: window.position?.y || 100,
                width: window.size?.width || 400,
                height: window.size?.height || 300,
                zIndex: getWindowZIndex(window.id),
              }}
              onMouseDown={(e) => {
                console.log(`窗口 ${window.id} 当前位置:`, window.position);
                // 点击窗口时设置焦点
                if (e.target === e.currentTarget) {
                  handleWindowFocusLocal(window.id);
                }
              }}
            >
            <div 
              className="window-header"
              onMouseDown={(e) => {
                // 如果点击的是按钮，不要启动拖拽
                if (e.target.closest('.window-controls')) {
                  console.log('点击了窗口控制按钮，不启动拖拽');
                  return;
                }
                startDrag(e, window.id);
              }}
              style={{ cursor: 'move' }}
            >
              {editingTitleId === window.id ? (
                <input
                  type="text"
                  className="window-title-input"
                  value={editingTitleValue}
                  onChange={(e) => setEditingTitleValue(e.target.value)}
                  onBlur={finishEditingTitle}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      finishEditingTitle();
                    } else if (e.key === 'Escape') {
                      cancelEditingTitle();
                    }
                  }}
                  autoFocus
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <span 
                  className="window-title"
                  onDoubleClick={(e) => {
                    e.stopPropagation();
                    startEditingTitle(window.id, window.title);
                  }}
                  title="双击编辑标题"
                >
                  {window.title}
                </span>
              )}
              <div className="window-controls">
                <button 
                  className="minimize-btn"
                  onClick={(e) => {
                    console.log('点击了最小化按钮:', window.id);
                    e.stopPropagation();
                    e.preventDefault();
                    handleWindowMinimizeLocal(window.id);
                  }}
                  title="最小化"
                >
                  ⁻
                </button>
                <button 
                  className="close-btn"
                  onClick={(e) => {
                    console.log('点击了关闭按钮:', window.id);
                    e.stopPropagation();
                    e.preventDefault();
                    handleWindowCloseLocal(window.id);
                  }}
                  title="关闭窗口"
                >
                  ✕
                </button>
              </div>
            </div>
            
            <div
              className="window-content"
              onMouseDown={(e) => {
                // 点击内容区域时设置焦点
                handleWindowFocusLocal(window.id);
                
                // 防止在内容区域按下拖拽
                if (!isResizing && !isDragging) {
                  e.stopPropagation();
                }
              }}
              style={{
                pointerEvents: (isResizing || isDragging) ? 'none' : 'auto'
              }}
            >
              {window.type === 'text' && (
                <TextEditorWithPreview
                  window={window}
                  onContentChange={(content, mode) => handleWindowContentChange(window.id, content, mode)}
                />
              )}
              {window.type === 'image' && (
                <label className="image-placeholder" title={window.content || '点击上传图片'}>
                  {hasRealMediaContent(window) ? (
                    <img
                      src={toMediaUrl(window)}
                      alt="img"
                      style={{ maxWidth: '100%', maxHeight: '100%' }}
                    />
                  ) : (
                    <>
                      🖼️ 图片内容
                      <p>点击上传图片</p>
                    </>
                  )}
                  <input
                    type="file"
                    accept="image/*"
                    style={{ display: 'none' }}
                    onChange={(e) => handleUpload(window.id, 'images', e.target.files)}
                  />
                </label>
              )}
              {window.type === 'video' && (
                <label className="video-placeholder" title={window.content || '点击上传视频'}>
                  {hasRealMediaContent(window) ? (
                    <video
                      controls
                      style={{ width: '100%', height: '100%' }}
                      src={toMediaUrl(window)}
                    />
                  ) : (
                    <>
                      🎥 视频内容
                      <p>点击上传视频</p>
                    </>
                  )}
                  <input
                    type="file"
                    accept="video/*"
                    style={{ display: 'none' }}
                    onChange={(e) => handleUpload(window.id, 'videos', e.target.files)}
                  />
                </label>
              )}
              {window.type === 'audio' && (
                <label className="video-placeholder" title={window.content || '点击上传音频'}>
                  {hasRealMediaContent(window) ? (
                    <audio
                      controls
                      style={{ width: '100%' }}
                      src={toMediaUrl(window)}
                    />
                  ) : (
                    <>
                      🎵 音频内容
                      <p>点击上传音频</p>
                    </>
                  )}
                  <input
                    type="file"
                    accept="audio/*"
                    style={{ display: 'none' }}
                    onChange={(e) => handleUpload(window.id, 'audios', e.target.files)}
                  />
                </label>
              )}
              {window.type === 'pdf' && (
                <label className="pdf-placeholder" title={window.content || '点击上传PDF'}>
                  {(() => {
                    console.log('📄 PDF窗口渲染:', {
                      windowId: window.id,
                      windowContent: window.content,
                      hasContent: !!window.content
                    });
                    
                    if (hasRealMediaContent(window)) {
                      const pdfUrl = toMediaUrl(window);
                      console.log('📄 PDF URL生成:', pdfUrl);
                      
                      return (
                    <iframe
                      title="pdf"
                      style={{ width: '100%', height: '100%', border: 'none' }}
                          src={pdfUrl}
                          onLoad={() => console.log('📄 PDF iframe 加载完成')}
                          onError={(e) => console.error('📄 PDF iframe 加载错误:', e)}
                    ></iframe>
                      );
                    } else {
                      console.log('📄 PDF窗口无内容，显示占位符');
                      return (
                    <>
                      📄 PDF内容
                      <p>点击上传PDF</p>
                    </>
                      );
                    }
                  })()}
                  <input
                    type="file"
                    accept="application/pdf"
                    style={{ display: 'none' }}
                    onChange={(e) => handleUpload(window.id, 'pdfs', e.target.files)}
                  />
                </label>
              )}
            </div>

            <div className="resize-handle" onMouseDown={(e) => startResize(e, window)} />
          </div>
        ))}
        
        {windows.length === 0 && (
          <div 
            className="empty-canvas"
            onContextMenu={handleDesktopRightClick}
            onDragEnter={handleDragEnter}
            onDragLeave={handleDragLeave}
            onDragOver={handleDragOver}
            onDrop={handleDrop}
          >
            <p>展板为空</p>
            <p>点击"创建窗口"开始添加内容</p>
            <p>或拖拽文件到这里创建窗口</p>
          </div>
        )}
      </div>
      
      {/* 缩放期间的全屏覆盖层，防止鼠标穿透 */}
      {isResizing && (
        <div
          className="resize-overlay"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 9999,
            cursor: 'nw-resize',
            pointerEvents: 'all',
            backgroundColor: 'rgba(0, 0, 0, 0.01)' // 几乎透明，但确保能捕获事件
          }}
        />
      )}
      
      {/* 拖拽期间的覆盖层 */}
      {isDragging && (
        <div
          className="drag-overlay"
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            zIndex: 9999,
            cursor: 'move',
            pointerEvents: 'all',
            backgroundColor: 'rgba(0, 0, 0, 0.01)'
          }}
        />
      )}

      {/* 右键菜单 */}
      <ContextMenu 
        visible={contextMenu.visible}
        x={contextMenu.x}
        y={contextMenu.y}
        type={contextMenu.type}
        onAction={(action) => handleContextMenuAction(action, contextMenu.targetIconId)}
      />
    </div>
  );
}

const getWindowIcon = (type) => {
  const typeIcons = {
    'text': '📝',
    'image': '🖼️',
    'video': '🎥',
    'audio': '🎵',
    'pdf': '📄'
  };
  return typeIcons[type] || '🪟';
};

export default BoardCanvas; 