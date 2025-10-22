import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import './BoardCanvas.css';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import * as pdfjsLib from 'pdfjs-dist';
import ChatWindow from './ChatWindow';

// 配置PDF.js
pdfjsLib.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.js`;

// LaTeX 分隔符标准化函数
const normalizeLatexDelimiters = (text) => {
  return text
    .replace(/\\\(/g, '$')
    .replace(/\\\)/g, '$')
    .replace(/\\\[/g, '$$')
    .replace(/\\\]/g, '$$');
};

// 防抖函数
const debounce = (func, wait) => {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
};

// PDF分页组件
function PDFPaginationViewer({ pdfUrl, onClose, boardId, windowId, initialPage }) {
  const [pdfDocument, setPdfDocument] = useState(null);
  const [currentPage, setCurrentPage] = useState(initialPage || 1);
  const [totalPages, setTotalPages] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const canvasRef = useRef(null);
  
  // 缩放和拖拽状态
  const [scale, setScale] = useState(1.5);
  const [panX, setPanX] = useState(0);
  const [panY, setPanY] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });
  const [lastPan, setLastPan] = useState({ x: 0, y: 0 });
  const containerRef = useRef(null);
  
  // 注释功能状态
  const [showAnnotationPanel, setShowAnnotationPanel] = useState(false);
  const [annotationMode, setAnnotationMode] = useState('preview'); // 'preview' 或 'edit'
  const [annotations, setAnnotations] = useState({}); // 存储每页的注释内容
  const [isSavingAnnotation, setIsSavingAnnotation] = useState(false); // 保存状态
  const [annotationFileInfo, setAnnotationFileInfo] = useState({}); // 存储注释文件信息
  
  // LLM功能状态
  const [showLLMMenu, setShowLLMMenu] = useState(false); // 显示LLM菜单
  const [showAnnotationSettings, setShowAnnotationSettings] = useState(false); // 显示注释设置面板
  
  // 批量生成状态
  const [showBatchOutlineModal, setShowBatchOutlineModal] = useState(false); // 显示批量生成大纲模态窗口
  const [showOutlinePanel, setShowOutlinePanel] = useState(false); // 显示大纲侧栏
  const [outlineView, setOutlineView] = useState('list'); // 'list' 或 'detail' - 大纲视图模式
  const [batchOutlineStatus, setBatchOutlineStatus] = useState(''); // 批量生成状态信息
  const [batchOutline, setBatchOutline] = useState(null); // 生成的大纲数据
  const [isBatchGenerating, setIsBatchGenerating] = useState(false); // 是否正在生成
  const [batchSubdivisions, setBatchSubdivisions] = useState(null); // 第二阶段细分数据
  const [selectedSection, setSelectedSection] = useState(null); // 当前选中的分段
  const [batchProgress, setBatchProgress] = useState({ completed: 0, total: 0 }); // 批量处理进度
  const [isStage2, setIsStage2] = useState(false); // 是否是第二阶段
  const [annotationProgress, setAnnotationProgress] = useState({ completed: 0, total: 0, currentPage: null, isGenerating: false }); // 注释生成进度
  const [stage2Completed, setStage2Completed] = useState(false); // 第二阶段是否已完成
  
  // 注释设置状态
  const [annotationSettings, setAnnotationSettings] = useState(() => {
    // 从localStorage加载设置
    const saved = localStorage.getItem('annotationSettings');
    return saved ? JSON.parse(saved) : {
      style: 'detailed', // 默认风格: detailed, simple, academic
      customPrompt: ''
    };
  });
  
  // 预设的注释风格
  const annotationStyles = {
    detailed: {
      name: '详细注释',
      prompt: '请为第{page}页生成详细的注释，包括：\n1. 页面主要内容概要\n2. 重要知识点详解\n3. 需要注意的细节\n4. 相关概念说明\n\n请用Markdown格式输出。'
    },
    simple: {
      name: '简洁注释',
      prompt: '请为第{page}页生成简洁的注释，只包括：\n1. 核心内容概括（1-2句话）\n2. 关键知识点（列表形式）\n\n请用Markdown格式输出。'
    },
    academic: {
      name: '学术注释',
      prompt: '请为第{page}页生成学术风格的注释，包括：\n1. 内容摘要\n2. 主要论点和证据\n3. 方法论说明\n4. 关键术语解释\n\n请用Markdown格式输出。'
    },
    qanda: {
      name: '问答式注释',
      prompt: '请为第{page}页生成问答式注释：\n1. 这页讲了什么？\n2. 核心概念是什么？\n3. 需要记住什么？\n4. 如何应用？\n\n请用Markdown格式输出。'
    }
  };
  
  // 保存注释设置
  const saveAnnotationSettings = (newSettings) => {
    setAnnotationSettings(newSettings);
    localStorage.setItem('annotationSettings', JSON.stringify(newSettings));
  };

  // 加载PDF文档
  useEffect(() => {
    const loadPDF = async () => {
      try {
        setIsLoading(true);
        setError(null);
        
        const loadingTask = pdfjsLib.getDocument(pdfUrl);
        const pdf = await loadingTask.promise;
        
        setPdfDocument(pdf);
        setTotalPages(pdf.numPages);
        
        // 如果有初始页码，跳转到该页，否则默认第1页
        if (initialPage && initialPage >= 1 && initialPage <= pdf.numPages) {
          setCurrentPage(initialPage);
          console.log('PDF加载成功，跳转到第', initialPage, '页');
        } else {
          setCurrentPage(1);
        console.log('PDF加载成功，总页数:', pdf.numPages);
        }
        
        setIsLoading(false);
      } catch (err) {
        console.error('PDF加载失败:', err);
        setError('PDF加载失败: ' + err.message);
        setIsLoading(false);
      }
    };

    if (pdfUrl) {
      loadPDF();
    }
  }, [pdfUrl, initialPage]);

  // 页面切换时加载注释和文件信息
  useEffect(() => {
    if (showAnnotationPanel && boardId && windowId) {
      loadAnnotation(currentPage);
      loadAnnotationFileInfo(currentPage);
    }
  }, [currentPage, showAnnotationPanel, boardId, windowId]);

  // 加载大纲数据
  useEffect(() => {
    const loadOutlineData = async () => {
      if (!boardId || !windowId) return;
      
      try {
        // 尝试加载大纲数据
        const outlineResponse = await fetch(
          `http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/outline-data`
        );
        if (outlineResponse.ok) {
          const outlineData = await outlineResponse.json();
          setBatchOutline(outlineData);
          console.log('加载已有大纲数据:', outlineData);
        }
        
        // 尝试加载细分数据
        const subdivResponse = await fetch(
          `http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/subdivision-data`
        );
        if (subdivResponse.ok) {
          const subdivData = await subdivResponse.json();
          setBatchSubdivisions(subdivData);
          setStage2Completed(true);
          console.log('加载已有细分数据:', subdivData);
        }
      } catch (error) {
        console.log('未找到批量大纲数据（首次使用）');
      }
    };
    
    loadOutlineData();
  }, [boardId, windowId]);

  // 点击外部区域或按ESC键关闭LLM菜单和设置面板
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (showLLMMenu) {
        // 检查点击的元素是否在LLM菜单容器内
        const llmMenuContainer = document.querySelector('[data-llm-menu]');
        if (llmMenuContainer && !llmMenuContainer.contains(event.target)) {
          setShowLLMMenu(false);
        }
      }
      if (showAnnotationSettings) {
        // 检查点击的元素是否在设置面板内
        const settingsPanel = document.querySelector('[data-annotation-settings]');
        if (settingsPanel && !settingsPanel.contains(event.target)) {
          setShowAnnotationSettings(false);
        }
      }
    };

    const handleKeyDown = (event) => {
      if (event.key === 'Escape') {
        if (showLLMMenu) setShowLLMMenu(false);
        if (showAnnotationSettings) setShowAnnotationSettings(false);
      }
    };

    if (showLLMMenu || showAnnotationSettings) {
      // 使用setTimeout确保事件监听器在下一个事件循环中添加
      setTimeout(() => {
        document.addEventListener('mousedown', handleClickOutside);
        document.addEventListener('keydown', handleKeyDown);
      }, 0);
      
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
        document.removeEventListener('keydown', handleKeyDown);
      };
    }
  }, [showLLMMenu, showAnnotationSettings]);

  // 渲染当前页面
  useEffect(() => {
    const renderPage = async () => {
      if (!pdfDocument || !canvasRef.current) return;

      try {
        const page = await pdfDocument.getPage(currentPage);
        const canvas = canvasRef.current;
        const context = canvas.getContext('2d');

        // 使用动态缩放比例
        const viewport = page.getViewport({ scale });
        
        console.log('PDF视口信息:', {
          scale: scale,
          width: viewport.width,
          height: viewport.height,
          originalWidth: page.view[2],
          originalHeight: page.view[3]
        });

        // 设置canvas尺寸
        canvas.height = viewport.height;
        canvas.width = viewport.width;

        // 渲染页面
        const renderContext = {
          canvasContext: context,
          viewport: viewport
        };

        await page.render(renderContext).promise;
        
        // 渲染文本层以支持文字选择
        const textLayer = document.getElementById(`textLayer-${currentPage}`);
        if (textLayer) {
          textLayer.innerHTML = ''; // 清空之前的内容
          
          // 设置文本层容器的精确尺寸
          textLayer.style.width = viewport.width + 'px';
          textLayer.style.height = viewport.height + 'px';
          
          console.log('文本层容器尺寸设置:', {
            textLayerWidth: viewport.width,
            textLayerHeight: viewport.height,
            canvasWidth: canvas.width,
            canvasHeight: canvas.height
          });
          
          try {
            // 获取文本内容
            const textContent = await page.getTextContent();
            console.log('文本内容获取成功，开始创建文本层');
            
            // 手动创建文本层，使用更精确的位置计算
            let debugCount = 0;
            textContent.items.forEach((textItem, index) => {
              if (!textItem.str || textItem.str.trim() === '') return;
              
              const textDiv = document.createElement('span');
              textDiv.textContent = textItem.str;
              textDiv.style.position = 'absolute';
              
              // 使用PDF.js的变换矩阵
              const transform = textItem.transform;
              const fontSize = Math.abs(transform[0]);
              const x = transform[4];
              const y = transform[5];
              
              // PDF.js坐标系：Y轴向上为正，原点在左下角
              // CSS坐标系：Y轴向下为正，原点在左上角
              // 需要考虑缩放比例并翻转Y坐标，调整字体基线
              const scale = viewport.scale;
              const scaledX = x * scale;
              const scaledY = viewport.height - (y * scale) - (fontSize * scale); // 所有坐标都需要缩放
              const scaledFontSize = fontSize * scale;
              
              textDiv.style.left = scaledX + 'px';
              textDiv.style.top = scaledY + 'px';
              textDiv.style.fontSize = scaledFontSize + 'px';
              textDiv.style.fontFamily = textItem.fontName || 'sans-serif';
              // 临时调试：让文本层可见
              textDiv.style.color = 'rgba(255, 0, 0, 0.3)'; // 红色半透明，用于调试
              textDiv.style.cursor = 'text';
              textDiv.style.userSelect = 'text';
              textDiv.style.pointerEvents = 'auto';
              textDiv.style.whiteSpace = 'pre';
              textDiv.style.transformOrigin = '0% 0%';
              textDiv.style.lineHeight = '1';
              textDiv.style.backgroundColor = 'rgba(0, 255, 0, 0.1)'; // 绿色背景，用于调试
              textDiv.style.border = '1px solid blue'; // 蓝色边框，用于调试文本元素位置
              
              // 添加调试信息（只显示前几个）
              if (debugCount < 5) {
                // 获取文本层容器的实际尺寸
                const containerRect = textLayer.getBoundingClientRect();
                console.log(`文本项 ${debugCount}:`, {
                  text: textItem.str,
                  originalX: x,
                  originalY: y,
                  scaledOriginalX: x * scale,
                  scaledOriginalY: y * scale,
                  flippedY: viewport.height - (y * scale),
                  adjustedY: viewport.height - (y * scale) - (fontSize * scale),
                  finalX: scaledX,
                  finalY: scaledY,
                  originalFontSize: fontSize,
                  finalFontSize: scaledFontSize,
                  viewportHeight: viewport.height,
                  viewportWidth: viewport.width,
                  containerWidth: containerRect.width,
                  containerHeight: containerRect.height,
                  scale: scale
                });
                debugCount++;
              }
              
              // 添加悬停效果
              textDiv.addEventListener('mouseenter', () => {
                textDiv.style.backgroundColor = 'rgba(0, 0, 255, 0.1)';
              });
              
              textDiv.addEventListener('mouseleave', () => {
                textDiv.style.backgroundColor = 'transparent';
              });
              
              textLayer.appendChild(textDiv);
            });
            
            console.log(`文本层 ${currentPage} 渲染完成，共 ${textContent.items.length} 个文本项`);
          } catch (textError) {
            console.error('文本层渲染失败:', textError);
          }
        }
        
        console.log(`页面 ${currentPage} 渲染完成`);
      } catch (err) {
        console.error('页面渲染失败:', err);
      }
    };

    renderPage();
  }, [pdfDocument, currentPage, scale]);

  // 缩放函数
  const handleZoomIn = () => {
    setScale(prev => Math.min(prev + 0.2, 3.0));
  };

  const handleZoomOut = () => {
    setScale(prev => Math.max(prev - 0.2, 0.5));
  };

  const handleZoomReset = () => {
    setScale(1.5);
    setPanX(0);
    setPanY(0);
  };

  // 加载注释内容
  const loadAnnotation = async (page) => {
    if (!boardId || !windowId) return;
    
    try {
      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/${page}`);
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setAnnotations(prev => ({
            ...prev,
            [page]: data.content
          }));
        }
      }
    } catch (error) {
      console.error('加载注释失败:', error);
    }
  };

  // 保存注释内容
  const saveAnnotation = async (page, content) => {
    if (!boardId || !windowId) return;
    
    try {
      setIsSavingAnnotation(true);
      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/${page}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ content })
      });
      
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          console.log(`第 ${page} 页注释保存成功`);
        }
      }
    } catch (error) {
      console.error('保存注释失败:', error);
    } finally {
      setIsSavingAnnotation(false);
    }
  };

  // 自动保存注释（防抖）
  const debouncedSaveAnnotation = useCallback(
    debounce((page, content) => {
      saveAnnotation(page, content);
    }, 1000),
    [boardId, windowId]
  );

  // 获取注释文件信息
  const loadAnnotationFileInfo = async (page) => {
    if (!boardId || !windowId) return;
    
    try {
      const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/${page}/info`);
      if (response.ok) {
        const data = await response.json();
        if (data.success) {
          setAnnotationFileInfo(prev => ({
            ...prev,
            [page]: data.file_info
          }));
        }
      }
    } catch (error) {
      console.error('获取注释文件信息失败:', error);
    }
  };

  // 滚轮缩放
  const handleWheel = (e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -0.1 : 0.1;
    setScale(prev => Math.max(0.5, Math.min(3.0, prev + delta)));
  };

  // 拖拽处理
  const handleMouseDown = (e) => {
    if (e.button === 1) { // 中键
      e.preventDefault();
      setIsDragging(true);
      setDragStart({ x: e.clientX, y: e.clientY });
      setLastPan({ x: panX, y: panY });
    }
  };

  const handleMouseMove = (e) => {
    if (isDragging) {
      const deltaX = e.clientX - dragStart.x;
      const deltaY = e.clientY - dragStart.y;
      setPanX(lastPan.x + deltaX);
      setPanY(lastPan.y + deltaY);
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // 上一页
  const goToPreviousPage = () => {
    if (currentPage > 1) {
      setCurrentPage(currentPage - 1);
    }
  };

  // 下一页
  const goToNextPage = () => {
    if (currentPage < totalPages) {
      setCurrentPage(currentPage + 1);
    }
  };

  // 跳转到指定页面
  const goToPage = (pageNumber) => {
    const page = Math.max(1, Math.min(totalPages, parseInt(pageNumber)));
    setCurrentPage(page);
  };

  if (isLoading) {
    return (
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        height: '100%',
        flexDirection: 'column',
        gap: '8px'
      }}>
        <div>📄 正在加载PDF...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'center', 
        height: '100%',
        flexDirection: 'column',
        gap: '8px',
        color: '#ff0000'
      }}>
        <div>❌ {error}</div>
        <button 
          onClick={onClose}
          style={{
            padding: '4px 8px',
            fontSize: '11px',
            backgroundColor: '#c0c0c0',
            border: '2px outset #c0c0c0',
            borderRadius: '0px',
            cursor: 'pointer',
            fontFamily: 'MS Sans Serif, sans-serif'
          }}
        >
          关闭
        </button>
      </div>
    );
  }

  return (
    <div style={{ 
      width: '100%', 
      height: '100%', 
      display: 'flex', 
      flexDirection: 'column',
      backgroundColor: '#ffffff'
    }}>
      {/* 分页工具栏 */}
      <div style={{
        backgroundColor: '#c0c0c0',
        borderBottom: '2px outset #c0c0c0',
        padding: '2px 4px',
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
        height: '24px',
        flexShrink: 0
      }}>
        {/* 上一页按钮 */}
        <button
          onClick={goToPreviousPage}
          disabled={currentPage <= 1}
          style={{
            padding: '1px 8px',
            fontSize: '11px',
            backgroundColor: currentPage <= 1 ? '#a0a0a0' : '#c0c0c0',
            border: '2px outset #c0c0c0',
            borderRadius: '0px',
            cursor: currentPage <= 1 ? 'not-allowed' : 'pointer',
            fontFamily: 'MS Sans Serif, sans-serif',
            height: '20px',
            minWidth: '40px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          ←
        </button>

        {/* 页码显示和输入 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <span style={{ fontSize: '11px', fontFamily: 'MS Sans Serif, sans-serif' }}>
            第
          </span>
          <input
            type="number"
            value={currentPage}
            onChange={(e) => goToPage(e.target.value)}
            min="1"
            max={totalPages}
            style={{
              width: '40px',
              height: '16px',
              fontSize: '11px',
              fontFamily: 'MS Sans Serif, sans-serif',
              border: '2px inset #c0c0c0',
              backgroundColor: '#ffffff',
              textAlign: 'center'
            }}
          />
          <span style={{ fontSize: '11px', fontFamily: 'MS Sans Serif, sans-serif' }}>
            页，共 {totalPages} 页
          </span>
        </div>

        {/* 下一页按钮 */}
        <button
          onClick={goToNextPage}
          disabled={currentPage >= totalPages}
          style={{
            padding: '1px 8px',
            fontSize: '11px',
            backgroundColor: currentPage >= totalPages ? '#a0a0a0' : '#c0c0c0',
            border: '2px outset #c0c0c0',
            borderRadius: '0px',
            cursor: currentPage >= totalPages ? 'not-allowed' : 'pointer',
            fontFamily: 'MS Sans Serif, sans-serif',
            height: '20px',
            minWidth: '40px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center'
          }}
        >
          →
        </button>

        {/* 缩放控制按钮 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '2px', marginLeft: '8px' }}>
          <button
            onClick={handleZoomOut}
            style={{
              padding: '1px 6px',
              fontSize: '11px',
              backgroundColor: '#c0c0c0',
              border: '2px outset #c0c0c0',
              borderRadius: '0px',
              cursor: 'pointer',
              fontFamily: 'MS Sans Serif, sans-serif',
              height: '20px',
              minWidth: '30px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            −
          </button>
          
          <span style={{ 
            fontSize: '11px', 
            fontFamily: 'MS Sans Serif, sans-serif',
            minWidth: '40px',
            textAlign: 'center'
          }}>
            {Math.round(scale * 100)}%
          </span>
          
          <button
            onClick={handleZoomIn}
            style={{
              padding: '1px 6px',
              fontSize: '11px',
              backgroundColor: '#c0c0c0',
              border: '2px outset #c0c0c0',
              borderRadius: '0px',
              cursor: 'pointer',
              fontFamily: 'MS Sans Serif, sans-serif',
              height: '20px',
              minWidth: '30px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            +
          </button>
          
          <button
            onClick={handleZoomReset}
            style={{
              padding: '1px 6px',
              fontSize: '11px',
              backgroundColor: '#c0c0c0',
              border: '2px outset #c0c0c0',
              borderRadius: '0px',
              cursor: 'pointer',
              fontFamily: 'MS Sans Serif, sans-serif',
              height: '20px',
              minWidth: '30px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            重置
          </button>
        </div>

        {/* 大纲按钮 - 只有在批量生成后才显示 */}
        {batchOutline && (
          <button
            onClick={() => {
              setShowOutlinePanel(!showOutlinePanel);
              console.log('大纲面板切换:', !showOutlinePanel);
            }}
            style={{
              padding: '1px 8px',
              fontSize: '11px',
              backgroundColor: showOutlinePanel ? '#a0a0a0' : '#c0c0c0',
              border: '2px outset #c0c0c0',
              borderRadius: '0px',
              cursor: 'pointer',
              fontFamily: 'MS Sans Serif, sans-serif',
              height: '20px',
              minWidth: '50px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              marginLeft: 'auto',
              marginRight: '8px'
            }}
            title={showOutlinePanel ? "隐藏大纲" : "显示大纲"}
          >
            大纲
          </button>
        )}

        {/* 注释按钮 */}
        <button
          onClick={() => {
            setShowAnnotationPanel(!showAnnotationPanel);
            console.log('注释面板切换:', !showAnnotationPanel);
          }}
          style={{
            padding: '1px 8px',
            fontSize: '11px',
            backgroundColor: showAnnotationPanel ? '#a0a0a0' : '#c0c0c0',
            border: '2px outset #c0c0c0',
            borderRadius: '0px',
            cursor: 'pointer',
            fontFamily: 'MS Sans Serif, sans-serif',
            height: '20px',
            minWidth: '50px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginLeft: batchOutline ? '0' : 'auto',
            marginRight: '8px'
          }}
          title={showAnnotationPanel ? "隐藏注释" : "显示注释"}
        >
          📝 注释
        </button>

        {/* 关闭分页模式按钮 */}
        <button
          onClick={onClose}
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
        >
          关闭分页
        </button>
      </div>

      {/* PDF页面内容和注释侧栏 */}
      <div style={{ 
        flex: 1, 
        display: 'flex',
        overflow: 'hidden'
      }}>
        {/* PDF页面内容 */}
        <div 
          ref={containerRef}
          style={{ 
            flex: showAnnotationPanel ? '1' : '1',
            overflow: 'hidden',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            backgroundColor: '#f0f0f0',
            cursor: isDragging ? 'grabbing' : 'grab',
            position: 'relative'
          }}
          onWheel={handleWheel}
          onMouseDown={handleMouseDown}
          onMouseMove={handleMouseMove}
          onMouseUp={handleMouseUp}
          onMouseLeave={handleMouseUp}
        >
        <div style={{ 
          position: 'relative',
          transform: `translate(${panX}px, ${panY}px)`,
          transition: isDragging ? 'none' : 'transform 0.1s ease-out'
        }}>
          <canvas
            ref={canvasRef}
            style={{
              border: '1px solid #808080',
              backgroundColor: '#ffffff',
              boxShadow: '2px 2px 4px rgba(0,0,0,0.3)',
              position: 'relative',
              zIndex: 1
            }}
          />
          {/* 文本层容器 - 用于文字选择 */}
          <div
            id={`textLayer-${currentPage}`}
            className="textLayer"
            style={{
              position: 'absolute',
              top: 0,
              left: 0,
              width: canvasRef.current?.width + 'px' || '100%',
              height: canvasRef.current?.height + 'px' || '100%',
              zIndex: 2,
              pointerEvents: 'auto',
              userSelect: 'text',
              border: '2px solid red' // 临时调试边框
            }}
          />
        </div>
        </div>
        
        {/* 大纲侧栏 */}
        {showOutlinePanel && batchOutline && (
          <div style={{
            width: '320px',
            backgroundColor: '#f0f0f0',
            borderLeft: '2px inset #c0c0c0',
            borderRight: '2px inset #c0c0c0',
            display: 'flex',
            flexDirection: 'column',
            flexShrink: 0,
            overflow: 'hidden'
          }}>
            {/* 大纲侧栏工具栏 */}
            <div style={{
              backgroundColor: '#c0c0c0',
              borderBottom: '2px outset #c0c0c0',
              padding: '4px 8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              fontSize: '11px',
              fontFamily: 'MS Sans Serif, sans-serif',
              fontWeight: 'bold'
            }}>
              <span>文档大纲</span>
              <button
                onClick={() => setShowOutlinePanel(false)}
                style={{
                  backgroundColor: '#c0c0c0',
                  border: '1px outset #c0c0c0',
                  cursor: 'pointer',
                  fontSize: '10px',
                  padding: '0 4px',
                  fontFamily: 'MS Sans Serif, sans-serif'
                }}
              >
                ✕
              </button>
            </div>

            {/* 大纲内容区域 */}
            <div style={{
              flex: 1,
              overflow: 'auto',
              padding: '8px',
              backgroundColor: '#f0f0f0'
            }}>
              {/* 细分内容详情页 */}
              {outlineView === 'detail' && selectedSection !== null && batchSubdivisions && batchSubdivisions.subdivisions && batchSubdivisions.subdivisions[selectedSection] && (
                <div>
                  {/* 返回按钮 */}
                  <button
                    onClick={() => {
                      setOutlineView('list');
                      setSelectedSection(null);
                    }}
                    style={{
                      padding: '4px 12px',
                      marginBottom: '12px',
                      fontSize: '11px',
                      backgroundColor: '#c0c0c0',
                      border: '2px outset #c0c0c0',
                      borderRadius: '0px',
                      cursor: 'pointer',
                      fontFamily: 'MS Sans Serif, sans-serif',
                      fontWeight: 'bold'
                    }}
                    onMouseEnter={(e) => e.target.style.backgroundColor = '#d0d0d0'}
                    onMouseLeave={(e) => e.target.style.backgroundColor = '#c0c0c0'}
                  >
                    ← 返回大纲
                  </button>

                  {/* 注释生成进度条 */}
                  {annotationProgress.total > 0 && (
                    <div style={{
                      marginBottom: '12px',
                      padding: '8px',
                      backgroundColor: '#ffffff',
                      border: '2px inset #c0c0c0'
                    }}>
                      <div style={{
                        fontSize: '10px',
                        marginBottom: '6px',
                        fontFamily: 'MS Sans Serif, sans-serif',
                        color: '#000000'
                      }}>
                        {annotationProgress.isGenerating 
                          ? `正在生成第 ${annotationProgress.currentPage} 页注释... (${annotationProgress.completed}/${annotationProgress.total})`
                          : `注释生成完成 (${annotationProgress.completed}/${annotationProgress.total})`
                        }
                      </div>
                      <div style={{
                        width: '100%',
                        height: '21px',
                        backgroundColor: '#c0c0c0',
                        border: '2px inset #c0c0c0',
                        display: 'flex',
                        gap: '2px',
                        padding: '2px'
                      }}>
                        {Array.from({ length: 25 }).map((_, index) => {
                          const percentage = (annotationProgress.completed / annotationProgress.total) * 100;
                          const squarePercentage = ((index + 1) / 25) * 100;
                          const isActive = squarePercentage <= percentage;
                          
                          return (
                            <div
                              key={index}
                              style={{
                                flex: 1,
                                height: '100%',
                                backgroundColor: isActive ? '#000080' : '#ffffff',
                                border: '1px solid #808080'
                              }}
                            />
                          );
                        })}
                      </div>
                      <div style={{
                        fontSize: '10px',
                        marginTop: '4px',
                        textAlign: 'right',
                        fontFamily: 'MS Sans Serif, sans-serif',
                        color: '#000000'
                      }}>
                        {Math.round((annotationProgress.completed / annotationProgress.total) * 100)}%
                      </div>
                    </div>
                  )}

                  {/* 细分内容详情 */}
                  <div style={{
                    padding: '12px',
                    backgroundColor: '#ffffff',
                    border: '2px inset #c0c0c0'
                  }}>
                    <div style={{
                      fontWeight: 'bold',
                      fontSize: '12px',
                      marginBottom: '12px',
                      color: '#0078d4',
                      fontFamily: 'MS Sans Serif, sans-serif'
                    }}>
                      {batchOutline.outline[selectedSection].section_number || (selectedSection + 1)}. {batchOutline.outline[selectedSection].title || batchOutline.outline[selectedSection].section_title || `章节 ${selectedSection + 1}`}
                    </div>
                    
                    {/* 第二阶段返回的section_summary - 更详细的概括 */}
                    {batchSubdivisions.subdivisions[selectedSection].section_summary && (
                      <div style={{
                        marginBottom: '12px',
                        padding: '8px',
                        backgroundColor: '#e0f0ff',
                        border: '2px inset #c0c0c0'
                      }}>
                        <div style={{
                          fontWeight: 'bold', 
                          marginBottom: '6px',
                          fontSize: '11px',
                          color: '#000000',
                          fontFamily: 'MS Sans Serif, sans-serif'
                        }}>
                          分段概括
                        </div>
                        <div style={{
                          fontSize: '10px',
                          lineHeight: '1.5',
                          whiteSpace: 'pre-wrap',
                          fontFamily: 'MS Sans Serif, sans-serif'
                        }}>
                          {batchSubdivisions.subdivisions[selectedSection].section_summary}
                        </div>
                      </div>
                    )}
                    
                    {/* 原来的summary字段（如果有的话） */}
                    {batchSubdivisions.subdivisions[selectedSection].summary && (
                      <div style={{
                        marginBottom: '12px',
                        padding: '8px',
                        backgroundColor: '#ffffcc',
                        border: '2px inset #c0c0c0'
                      }}>
                        <div style={{
                          fontWeight: 'bold', 
                          marginBottom: '6px',
                          fontSize: '11px',
                          color: '#000000',
                          fontFamily: 'MS Sans Serif, sans-serif'
                        }}>
                          内容概括
                        </div>
                        <div style={{
                          fontSize: '10px',
                          lineHeight: '1.5',
                          whiteSpace: 'pre-wrap',
                          fontFamily: 'MS Sans Serif, sans-serif'
                        }}>
                          {batchSubdivisions.subdivisions[selectedSection].summary}
                        </div>
                      </div>
                    )}
                    
                    {batchSubdivisions.subdivisions[selectedSection].subdivisions && 
                     batchSubdivisions.subdivisions[selectedSection].subdivisions.length > 0 && (
                      <div>
                        <div style={{
                          fontWeight: 'bold',
                          fontSize: '11px',
                          marginBottom: '8px',
                          color: '#000000',
                          fontFamily: 'MS Sans Serif, sans-serif'
                        }}>
                          子分段列表:
                        </div>
                        {batchSubdivisions.subdivisions[selectedSection].subdivisions.map((sub, subIndex) => (
                          <div
                            key={subIndex}
                            style={{
                              padding: '8px',
                              marginBottom: '8px',
                              backgroundColor: '#ffffff',
                              border: '1px solid #d0d0d0',
                              borderLeft: '3px solid #4caf50'
                            }}
                          >
                            <div style={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              marginBottom: '4px'
                            }}>
                              <div style={{
                                fontSize: '11px',
                                fontWeight: 'bold',
                                color: '#000000',
                                fontFamily: 'MS Sans Serif, sans-serif'
                              }}>
                                {sub.title || `子分段 ${subIndex + 1}`}
                              </div>
                              <div style={{
                                fontSize: '10px',
                                color: '#666',
                                fontFamily: 'MS Sans Serif, sans-serif'
                              }}>
                                p.{sub.page_start}-{sub.page_end}
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* 生成注释按键 */}
                    <div style={{
                      marginTop: '16px',
                      padding: '8px',
                      borderTop: '2px inset #c0c0c0',
                      display: 'flex',
                      justifyContent: 'flex-end'
                    }}>
                      <button
                        onClick={async () => {
                          console.log('开始生成当前分段的注释');
                          const section = batchOutline.outline[selectedSection];
                          const totalPages = section.page_end - section.page_start + 1;
                          
                          // 初始化进度
                          setAnnotationProgress({
                            completed: 0,
                            total: totalPages,
                            currentPage: section.page_start,
                            isGenerating: true
                          });
                          
                          try {
                            // 准备提示词模板（与单页注释保持一致）
                            let promptTemplate = '';
                            if (annotationSettings.style === 'custom') {
                              promptTemplate = annotationSettings.customPrompt;
                            } else if (annotationStyles[annotationSettings.style]) {
                              promptTemplate = annotationStyles[annotationSettings.style].prompt;
                            }
                            
                            console.log('发送请求数据:', {
                              section_index: selectedSection,
                              section_data: section,
                              subdivision_data: batchSubdivisions.subdivisions[selectedSection],
                              annotation_style: annotationSettings.style,
                              promptTemplate: promptTemplate
                            });
                            
                            const response = await fetch(
                              `http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/generate-section`,
                              {
                                method: 'POST',
                                headers: {
                                  'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({
                                  section_index: selectedSection,
                                  section_data: section,
                                  subdivision_data: batchSubdivisions.subdivisions[selectedSection],
                                  annotation_style: annotationSettings.style,
                                  promptTemplate: promptTemplate
                                })
                              }
                            );
                            
                            if (!response.ok) {
                              const errorText = await response.text();
                              console.error('API错误响应:', errorText);
                              setAnnotationProgress(prev => ({ ...prev, isGenerating: false }));
                              throw new Error(`生成注释失败: ${response.status} - ${errorText}`);
                            }
                            
                            // 处理流式响应
                            const reader = response.body.getReader();
                            const decoder = new TextDecoder();
                            let buffer = '';
                            
                            while (true) {
                              const {done, value} = await reader.read();
                              if (done) break;
                              
                              buffer += decoder.decode(value, {stream: true});
                              const lines = buffer.split('\n\n');
                              buffer = lines.pop() || '';
                              
                              for (const line of lines) {
                                if (line.startsWith('data: ')) {
                                  const data = JSON.parse(line.slice(6));
                                  
                                  if (data.type === 'status') {
                                    console.log('注释生成状态:', data.message);
                                  } else if (data.type === 'content') {
                                    console.log('LLM输出:', data.content);
                                  } else if (data.type === 'page_done') {
                                    console.log(`第${data.page}页注释完成 (${data.completed}/${data.total})`);
                                    
                                    // 更新进度
                                    setAnnotationProgress({
                                      completed: data.completed,
                                      total: data.total,
                                      currentPage: data.page,
                                      isGenerating: true
                                    });
                                    
                                    // 实时刷新注释显示
                                    if (data.annotation && currentPage === data.page) {
                                      // 如果用户正在查看这一页，立即更新注释内容
                                      setAnnotations(prev => ({
                                        ...prev,
                                        [data.page]: data.annotation
                                      }));
                                      console.log(`✅ 已更新第${data.page}页的注释显示`);
                                    }
                                  } else if (data.type === 'complete') {
                                    console.log('分段注释全部完成:', data);
                                    
                                    // 设置进度为100%并保持
                                    setAnnotationProgress({
                                      completed: data.total_pages,
                                      total: data.total_pages,
                                      currentPage: null,
                                      isGenerating: false
                                    });
                                    
                                    alert(`注释生成完成！共生成 ${data.completed_pages} 页注释`);
                                    
                                    // 生成完成后，如果用户在当前分段的页面范围内，刷新当前页的注释
                                    if (currentPage >= section.page_start && currentPage <= section.page_end) {
                                      // 重新加载当前页的注释
                                      fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/${currentPage}`)
                                        .then(res => res.json())
                                        .then(result => {
                                          if (result.success && result.annotation) {
                                            setAnnotations(prev => ({
                                              ...prev,
                                              [currentPage]: result.annotation
                                            }));
                                          }
                                        })
                                        .catch(err => console.error('刷新注释失败:', err));
                                    }
                                  } else if (data.type === 'error') {
                                    console.error('后端错误:', data.error);
                                    setAnnotationProgress(prev => ({ ...prev, isGenerating: false }));
                                    throw new Error(data.error);
                                  }
                                }
                              }
                            }
                          } catch (error) {
                            console.error('生成注释失败，详细错误:', error);
                            setAnnotationProgress(prev => ({ ...prev, isGenerating: false }));
                            alert('生成注释失败: ' + error.message);
                          }
                        }}
                        style={{
                          padding: '6px 16px',
                          fontSize: '11px',
                          backgroundColor: '#008000',
                          color: '#ffffff',
                          border: '2px outset #008000',
                          borderRadius: '0px',
                          cursor: 'pointer',
                          fontFamily: 'MS Sans Serif, sans-serif',
                          fontWeight: 'bold'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#006000'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#008000'}
                      >
                        生成注释
                      </button>
                    </div>
                  </div>
                </div>
              )}

              {/* 大纲列表视图 */}
              {outlineView === 'list' && (
                <>
                  {/* 第二阶段进度条 - 放在最上面 */}
                  {(isStage2 || stage2Completed) && batchProgress.total > 0 && (
                <div style={{
                  marginBottom: '12px',
                  padding: '8px',
                  backgroundColor: '#c0c0c0',
                  border: '2px inset #c0c0c0',
                  borderRadius: '0px'
                }}>
                  <div style={{
                    fontSize: '11px',
                    fontWeight: 'bold',
                    marginBottom: '6px',
                    color: '#000000',
                    textAlign: 'center'
                  }}>
                    {stage2Completed ? '并行结束' : '并行...'} {batchProgress.completed} / {batchProgress.total}
                  </div>
                  
                  {/* Windows 98风格量子化方格进度条 */}
                  <div style={{
                    width: '100%',
                    height: '30px',
                    backgroundColor: '#c0c0c0',
                    border: '2px inset #c0c0c0',
                    borderRadius: '0px',
                    overflow: 'hidden',
                    position: 'relative',
                    display: 'flex',
                    alignItems: 'center',
                    padding: '1px'
                  }}>
                    {/* 进度条背景 */}
                    <div style={{
                      width: '100%',
                      height: '27px',
                      backgroundColor: '#f0f0f0',
                      border: '1px inset #c0c0c0',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'flex-start',
                      padding: '2px'
                    }}>
                      {/* 量子化方格进度条 */}
                      <div style={{
                        display: 'flex',
                        width: '100%',
                        gap: '2px',
                        alignItems: 'center'
                      }}>
                        {Array.from({ length: 25 }, (_, index) => {
                          const progressPercentage = (batchProgress.completed / batchProgress.total) * 100;
                          const isActive = (index + 1) * 4 <= progressPercentage; // 每格代表4%
                          
                          return (
                            <div
                              key={index}
                              style={{
                                flex: 1,
                                height: '21px',
                                backgroundColor: isActive ? '#000080' : 'transparent',
                                border: '1px solid transparent',
                                borderRadius: '0px',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                position: 'relative',
                                boxSizing: 'border-box'
                              }}
                            >
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* 批量生成所有注释按钮 - 仅在第二阶段完成后显示 */}
              {stage2Completed && batchOutline && batchSubdivisions && (
                <div style={{
                  marginBottom: '12px',
                  padding: '8px',
                  backgroundColor: '#ffffff',
                  border: '2px inset #c0c0c0',
                  display: 'flex',
                  justifyContent: 'center'
                }}>
                  <button
                    onClick={async () => {
                      if (!batchOutline || !batchOutline.outline || !batchSubdivisions || !batchSubdivisions.subdivisions) {
                        alert('大纲或细分数据不完整');
                        return;
                      }

                      const confirmStart = window.confirm(
                        `即将并行生成所有 ${batchOutline.outline.length} 个分段的注释，这可能需要较长时间。确认开始？`
                      );
                      
                      if (!confirmStart) return;

                      console.log('开始批量生成所有分段的注释');

                      // 为每个分段创建生成任务（并行执行）
                      const generatePromises = batchOutline.outline.map(async (section, sectionIndex) => {
                        const subdivision = batchSubdivisions.subdivisions[sectionIndex];
                        if (!subdivision) {
                          console.warn(`分段${sectionIndex}没有细分数据，跳过`);
                          return null;
                        }

                        const totalPages = section.page_end - section.page_start + 1;
                        
                        // 初始化该分段的进度（注意：这里只是示例，真正的进度需要从后端事件更新）
                        console.log(`开始生成分段${sectionIndex}: ${section.title} (${totalPages}页)`);

                        try {
                          // 准备提示词模板
                          let promptTemplate = '';
                          if (annotationSettings.style === 'custom') {
                            promptTemplate = annotationSettings.customPrompt;
                          } else if (annotationStyles[annotationSettings.style]) {
                            promptTemplate = annotationStyles[annotationSettings.style].prompt;
                          }

                          const response = await fetch(
                            `http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/generate-section`,
                            {
                              method: 'POST',
                              headers: {
                                'Content-Type': 'application/json',
                              },
                              body: JSON.stringify({
                                section_index: sectionIndex,
                                section_data: section,
                                subdivision_data: subdivision,
                                annotation_style: annotationSettings.style,
                                promptTemplate: promptTemplate
                              })
                            }
                          );

                          if (!response.ok) {
                            throw new Error(`生成分段${sectionIndex}注释失败`);
                          }

                          // 处理流式响应
                          const reader = response.body.getReader();
                          const decoder = new TextDecoder();
                          let buffer = '';

                          while (true) {
                            const {done, value} = await reader.read();
                            if (done) break;

                            buffer += decoder.decode(value, {stream: true});
                            const lines = buffer.split('\n\n');
                            buffer = lines.pop() || '';

                            for (const line of lines) {
                              if (line.startsWith('data: ')) {
                                const data = JSON.parse(line.slice(6));

                                if (data.type === 'page_done') {
                                  console.log(`[分段${sectionIndex}] 第${data.page}页完成 (${data.completed}/${data.total})`);
                                  
                                  // 实时刷新注释显示
                                  if (data.annotation && currentPage === data.page) {
                                    setAnnotations(prev => ({
                                      ...prev,
                                      [data.page]: data.annotation
                                    }));
                                  }
                                } else if (data.type === 'complete') {
                                  console.log(`[分段${sectionIndex}] 全部完成: ${data.completed_pages}页`);
                                  
                                  // 如果用户在当前分段范围内，刷新当前页
                                  if (currentPage >= section.page_start && currentPage <= section.page_end) {
                                    fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/${currentPage}`)
                                      .then(res => res.json())
                                      .then(result => {
                                        if (result.success && result.annotation) {
                                          setAnnotations(prev => ({
                                            ...prev,
                                            [currentPage]: result.annotation
                                          }));
                                        }
                                      })
                                      .catch(err => console.error('刷新注释失败:', err));
                                  }
                                } else if (data.type === 'error') {
                                  throw new Error(data.error);
                                }
                              }
                            }
                          }

                          return { success: true, sectionIndex };
                        } catch (error) {
                          console.error(`分段${sectionIndex}生成失败:`, error);
                          return { success: false, sectionIndex, error: error.message };
                        }
                      });

                      // 等待所有分段完成
                      console.log(`并行执行${generatePromises.length}个分段生成任务...`);
                      const results = await Promise.all(generatePromises);
                      
                      // 统计结果
                      const successCount = results.filter(r => r && r.success).length;
                      const failCount = results.filter(r => r && !r.success).length;
                      
                      alert(`批量生成完成！\n成功: ${successCount} 个分段\n失败: ${failCount} 个分段`);
                      console.log('批量生成结果:', results);
                    }}
                    style={{
                      padding: '8px 20px',
                      fontSize: '12px',
                      backgroundColor: '#008000',
                      color: '#ffffff',
                      border: '2px outset #008000',
                      borderRadius: '0px',
                      cursor: 'pointer',
                      fontFamily: 'MS Sans Serif, sans-serif',
                      fontWeight: 'bold'
                    }}
                    onMouseEnter={(e) => {
                      e.target.style.backgroundColor = '#009000';
                      e.target.style.borderStyle = 'outset';
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.backgroundColor = '#008000';
                      e.target.style.borderStyle = 'outset';
                    }}
                    onMouseDown={(e) => {
                      e.target.style.borderStyle = 'inset';
                    }}
                    onMouseUp={(e) => {
                      e.target.style.borderStyle = 'outset';
                    }}
                  >
                    批量生成所有注释
                  </button>
                </div>
              )}

              {/* 第一阶段：生成中的流式输出 */}
              {isBatchGenerating && !batchOutline && (
                <div style={{
                  padding: '12px',
                  backgroundColor: '#c0c0c0',
                  border: '2px inset #c0c0c0',
                  fontSize: '11px',
                  fontFamily: 'MS Sans Serif, sans-serif',
                  whiteSpace: 'pre-wrap',
                  minHeight: '100px'
                }}>
                  {batchOutlineStatus}
                </div>
              )}

              {/* 第一阶段：大纲展示 */}
              {batchOutline && batchOutline.outline && (
                <div>
                  {/* 重叠信息提示 */}
                  {batchOutline.page_analysis && batchOutline.page_analysis.statistics.overlapping_pages_count > 0 && (
                    <div style={{
                      padding: '6px 8px',
                      marginBottom: '12px',
                      backgroundColor: '#ffffcc',
                      border: '2px inset #c0c0c0',
                      fontSize: '10px',
                      fontFamily: 'MS Sans Serif, sans-serif',
                      fontWeight: 'normal'
                    }}>
                      检测到 <strong>{batchOutline.page_analysis.statistics.overlapping_pages_count}</strong> 个重叠页面
                      （第 {batchOutline.page_analysis.statistics.multi_annotated_pages.join(', ')} 页），
                      这些页面会被多次注释，后续将自动融合为一个完整注释。
                    </div>
                  )}
                  
                  {/* 大纲章节列表 */}
                  {batchOutline.outline.map((section, index) => {
                    // 检查这个章节是否包含重叠页面
                    const hasOverlap = batchOutline.page_analysis && 
                      batchOutline.page_analysis.statistics.multi_annotated_pages.some(
                        page => page >= section.page_start && page <= section.page_end
                      );
                    
                    // 只有在第二阶段完成后才能点击
                    const isClickable = batchSubdivisions && batchSubdivisions.subdivisions && !isBatchGenerating;
                    const isSelected = selectedSection === index;
                    
                    return (
                      <div
                        key={index}
                        style={{
                          padding: '8px',
                          marginBottom: '8px',
                          backgroundColor: isSelected ? '#e0e0e0' : '#ffffff',
                          border: '1px solid #d0d0d0',
                          borderLeft: hasOverlap ? '3px solid #ff9800' : '3px solid #0078d4',
                          cursor: isClickable ? 'pointer' : 'default',
                          transition: 'background-color 0.2s, box-shadow 0.2s',
                          boxShadow: 'none',
                          opacity: isClickable ? 1 : 0.8
                        }}
                        onMouseEnter={(e) => {
                          if (isClickable) {
                            e.currentTarget.style.backgroundColor = isSelected ? '#d0d0d0' : '#f8f8f8';
                            e.currentTarget.style.boxShadow = '0 2px 4px rgba(0,0,0,0.2)';
                          }
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.backgroundColor = isSelected ? '#e0e0e0' : '#ffffff';
                          e.currentTarget.style.boxShadow = 'none';
                        }}
                        onClick={() => {
                          if (isClickable) {
                            setSelectedSection(index);
                            setOutlineView('detail'); // 切换到详情视图
                            console.log('打开细分详情页:', index);
                          }
                        }}
                      >
                        <div style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          alignItems: 'flex-start',
                          marginBottom: '6px'
                        }}>
                          <div style={{
                            fontWeight: 'bold',
                            fontSize: '11px',
                            flex: 1,
                            color: '#000000',
                            fontFamily: 'MS Sans Serif, sans-serif'
                          }}>
                            {section.section_number || (index + 1)}. {section.title || section.section_title || `章节 ${index + 1}`}
                          </div>
                          <div style={{
                            fontSize: '10px',
                            color: '#666',
                            marginLeft: '8px',
                            whiteSpace: 'nowrap',
                            fontFamily: 'MS Sans Serif, sans-serif'
                          }}>
                            p.{section.page_start}-{section.page_end}
                          </div>
                        </div>
                        
                        {(section.description || section.summary) && (
                          <div style={{
                            fontSize: '10px',
                            color: '#555',
                            lineHeight: '1.4',
                            marginBottom: '6px',
                            fontFamily: 'MS Sans Serif, sans-serif'
                          }}>
                            {(() => {
                              const text = section.description || section.summary;
                              return text.length > 100 ? text.substring(0, 100) + '...' : text;
                            })()}
                          </div>
                        )}
                        
                        {hasOverlap && (
                          <span style={{
                            display: 'inline-block',
                            fontSize: '9px',
                            padding: '2px 4px',
                            backgroundColor: '#fff3e0',
                            border: '1px solid #ffb74d',
                            color: '#e65100',
                            marginTop: '4px',
                            fontFamily: 'MS Sans Serif, sans-serif',
                            fontWeight: 'normal'
                          }} title="此章节包含会被多次注释的页面">
                            ! 含重叠页
                          </span>
                        )}
                      </div>
                    );
                  })}

                  {/* 第二阶段启动按键 */}
                  {!isBatchGenerating && !batchSubdivisions && (
                    <div style={{
                      marginTop: '12px',
                      padding: '8px',
                      display: 'flex',
                      justifyContent: 'flex-end'
                    }}>
                      <button
                        onClick={async () => {
                          console.log('开始第二阶段：细分分段');
                          setIsBatchGenerating(true);
                          setIsStage2(true);
                          setStage2Completed(false);
                          setBatchOutlineStatus('正在并行细分各个分段...');
                          setBatchProgress({ completed: 0, total: batchOutline.outline.length });
                          
                          try {
                            // 调用第二阶段API
                            const response = await fetch(
                              `http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/subdivide`,
                              {
                                method: 'POST',
                                headers: {
                                  'Content-Type': 'application/json',
                                }
                              }
                            );
                            
                            if (!response.ok) {
                              throw new Error('细分处理失败');
                            }
                            
                            // 处理流式响应
                            const reader = response.body.getReader();
                            const decoder = new TextDecoder();
                            let buffer = '';
                            let currentSection = null;
                            
                            while (true) {
                              const {done, value} = await reader.read();
                              if (done) break;
                              
                              buffer += decoder.decode(value, {stream: true});
                              const lines = buffer.split('\n\n');
                              buffer = lines.pop() || '';
                              
                              for (const line of lines) {
                                if (line.startsWith('data: ')) {
                                  const data = JSON.parse(line.slice(6));
                                  
                                  if (data.type === 'status') {
                                    setBatchOutlineStatus(data.message);
                                  } else if (data.type === 'section_start') {
                                    currentSection = data.section;
                                    // 第二阶段不显示详细信息，只记录
                                  } else if (data.type === 'section_content') {
                                    // 第二阶段不显示流式输出内容，避免混乱
                                  } else if (data.type === 'section_done') {
                                    // 更新进度
                                    setBatchProgress({ completed: data.completed, total: data.total });
                                    setBatchOutlineStatus(`正在并行细分各个分段...\n进度: ${data.completed}/${data.total}`);
                                  } else if (data.type === 'complete') {
                                    console.log('所有分段细分完成:', data.data);
                                    // 确保进度条显示为100%完成状态
                                    setBatchProgress(prev => ({ completed: prev.total, total: prev.total }));
                                    setBatchSubdivisions(data.data); // 保存细分数据
                                    setIsBatchGenerating(false);
                                    setStage2Completed(true); // 标记第二阶段完成，但保留进度条显示
                                  } else if (data.type === 'warning') {
                                    setBatchOutlineStatus(prev => prev + `\n警告: ${data.message}`);
                                  } else if (data.type === 'done') {
                                    console.log('细分流程完成');
                                    setIsBatchGenerating(false);
                                  } else if (data.type === 'error') {
                                    console.error('细分错误:', data.error);
                                    setBatchOutlineStatus(prev => prev + `\n错误: ${data.error}`);
                                    setIsBatchGenerating(false);
                                  }
                                }
                              }
                            }
                          } catch (error) {
                            console.error('细分处理失败:', error);
                            setBatchOutlineStatus(prev => prev + `\n细分失败: ${error.message}`);
                            setIsBatchGenerating(false);
                          }
                        }}
                        style={{
                          padding: '6px 16px',
                          fontSize: '11px',
                          backgroundColor: '#0078d4',
                          color: '#ffffff',
                          border: '2px outset #0078d4',
                          borderRadius: '0px',
                          cursor: 'pointer',
                          fontFamily: 'MS Sans Serif, sans-serif',
                          fontWeight: 'bold'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#005a9e'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#0078d4'}
                      >
                        {batchSubdivisions ? '重新细分' : '开始第二阶段'}
                      </button>
                    </div>
                  )}
                </div>
              )}

              {/* 重新细分按键 - 放在底部 */}
              {stage2Completed && batchSubdivisions && batchSubdivisions.subdivisions && (
                <div style={{
                  marginTop: '12px',
                  padding: '8px',
                  display: 'flex',
                  justifyContent: 'flex-end'
                }}>
                  <button
                    onClick={async () => {
                      console.log('重新开始第二阶段：细分分段');
                      setIsBatchGenerating(true);
                      setIsStage2(true);
                      setStage2Completed(false);
                      setSelectedSection(null); // 清空选中
                      setBatchOutlineStatus('正在并行细分各个分段...');
                      setBatchProgress({ completed: 0, total: batchOutline.outline.length });
                      
                      try {
                        // 调用第二阶段API
                        const response = await fetch(
                          `http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/subdivide`,
                          {
                            method: 'POST',
                            headers: {
                              'Content-Type': 'application/json',
                            }
                          }
                        );
                        
                        if (!response.ok) {
                          throw new Error('细分处理失败');
                        }
                        
                        // 处理流式响应
                        const reader = response.body.getReader();
                        const decoder = new TextDecoder();
                        let buffer = '';
                        let currentSection = null;
                        
                        while (true) {
                          const {done, value} = await reader.read();
                          if (done) break;
                          
                          buffer += decoder.decode(value, {stream: true});
                          const lines = buffer.split('\n\n');
                          buffer = lines.pop() || '';
                          
                          for (const line of lines) {
                            if (line.startsWith('data: ')) {
                              const data = JSON.parse(line.slice(6));
                              
                              if (data.type === 'status') {
                                setBatchOutlineStatus(data.message);
                              } else if (data.type === 'section_start') {
                                currentSection = data.section;
                                // 第二阶段不显示详细信息，只记录
                              } else if (data.type === 'section_content') {
                                // 第二阶段不显示流式输出内容，避免混乱
                              } else if (data.type === 'section_done') {
                                // 更新进度
                                setBatchProgress({ completed: data.completed, total: data.total });
                                setBatchOutlineStatus(`正在并行细分各个分段...\n进度: ${data.completed}/${data.total}`);
                              } else if (data.type === 'complete') {
                                console.log('所有分段细分完成:', data.data);
                                // 确保进度条显示为100%完成状态
                                setBatchProgress(prev => ({ completed: prev.total, total: prev.total }));
                                setBatchSubdivisions(data.data); // 保存细分数据
                                setIsBatchGenerating(false);
                                setStage2Completed(true); // 标记第二阶段完成，但保留进度条显示
                              } else if (data.type === 'warning') {
                                setBatchOutlineStatus(prev => prev + `\n警告: ${data.message}`);
                              } else if (data.type === 'done') {
                                console.log('细分流程完成');
                                setIsBatchGenerating(false);
                              } else if (data.type === 'error') {
                                console.error('细分错误:', data.error);
                                setBatchOutlineStatus(prev => prev + `\n错误: ${data.error}`);
                                setIsBatchGenerating(false);
                              }
                            }
                          }
                        }
                      } catch (error) {
                        console.error('细分处理失败:', error);
                        setBatchOutlineStatus(prev => prev + `\n细分失败: ${error.message}`);
                        setIsBatchGenerating(false);
                      }
                    }}
                    style={{
                      padding: '6px 16px',
                      fontSize: '11px',
                      backgroundColor: '#0078d4',
                      color: '#ffffff',
                      border: '2px outset #0078d4',
                      borderRadius: '0px',
                      cursor: 'pointer',
                      fontFamily: 'MS Sans Serif, sans-serif',
                      fontWeight: 'bold'
                    }}
                    onMouseEnter={(e) => e.target.style.backgroundColor = '#005a9e'}
                    onMouseLeave={(e) => e.target.style.backgroundColor = '#0078d4'}
                  >
                    重新细分
                  </button>
                </div>
              )}
                </>
              )}
            </div>
          </div>
        )}
        
        {/* 注释侧栏 */}
        {showAnnotationPanel && (
          <div style={{
            width: '300px',
            backgroundColor: '#f0f0f0',
            borderLeft: '2px inset #c0c0c0',
            display: 'flex',
            flexDirection: 'column',
            flexShrink: 0
          }}>
            {/* 注释侧栏工具栏 */}
            <div style={{
              backgroundColor: '#c0c0c0',
              borderBottom: '2px outset #c0c0c0',
              padding: '4px 8px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              height: '28px',
              flexShrink: 0
            }}>
              <span style={{
                fontSize: '11px',
                fontFamily: 'MS Sans Serif, sans-serif',
                fontWeight: 'bold'
              }}>
                第 {currentPage} 页注释
              </span>
              
              <div style={{ display: 'flex', alignItems: 'center', gap: '4px', position: 'relative' }}>
                {/* 文件信息按钮 */}
                <button
                  style={{
                    padding: '2px 6px',
                    fontSize: '11px',
                    backgroundColor: '#c0c0c0',
                    border: '2px outset #c0c0c0',
                    borderRadius: '0px',
                    cursor: 'pointer',
                    fontFamily: 'MS Sans Serif, sans-serif',
                    height: '20px',
                    minWidth: '24px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                  title={(() => {
                    const fileInfo = annotationFileInfo[currentPage];
                    if (!fileInfo || !fileInfo.exists) {
                      return '暂无注释文件';
                    }
                    return `文件名: ${fileInfo.filename}\n来源: ${fileInfo.source_pdf}\n创建时间: ${fileInfo.created_time}\n修改时间: ${fileInfo.modified_time}\n文件大小: ${fileInfo.size} 字节`;
                  })()}
                >
                  ℹ
                </button>
                
                {/* LLM功能按钮 */}
                <div style={{ position: 'relative' }} data-llm-menu>
                  <button
                    onClick={() => {
                      setShowLLMMenu(!showLLMMenu);
                      console.log('LLM菜单切换:', !showLLMMenu);
                    }}
                    style={{
                      padding: '2px 6px',
                      fontSize: '11px',
                      backgroundColor: showLLMMenu ? '#a0a0a0' : '#c0c0c0',
                      border: '2px outset #c0c0c0',
                      borderRadius: '0px',
                      cursor: 'pointer',
                      fontFamily: 'MS Sans Serif, sans-serif',
                      height: '20px',
                      minWidth: '40px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center'
                    }}
                    title="LLM智能功能"
                  >
                    LLM
                  </button>
                  
                  {/* LLM下拉菜单 */}
                  {showLLMMenu && (
                    <div style={{
                      position: 'absolute',
                      top: '22px',
                      right: '0px',
                      backgroundColor: '#c0c0c0',
                      border: '2px outset #c0c0c0',
                      borderRadius: '0px',
                      zIndex: 1000,
                      minWidth: '120px',
                      boxShadow: '2px 2px 4px rgba(0,0,0,0.3)'
                    }}>
                      <button
                        onClick={async () => {
                          console.log('生成注释功能');
                          setShowLLMMenu(false);
                          setAnnotationMode('preview'); // 切换到预览模式以查看生成的注释
                          
                          try {
                            // 准备提示词模板
                            let promptTemplate = '';
                            if (annotationSettings.style === 'custom') {
                              promptTemplate = annotationSettings.customPrompt;
                            } else if (annotationStyles[annotationSettings.style]) {
                              promptTemplate = annotationStyles[annotationSettings.style].prompt;
                            }
                            
                            console.log('使用注释风格:', annotationSettings.style);
                            console.log('提示词模板:', promptTemplate);
                            
                            // 调用后端API生成注释
                            const response = await fetch(
                              `http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/${currentPage}/generate`,
                              {
                                method: 'POST',
                                headers: {
                                  'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({
                                  promptTemplate: promptTemplate,
                                  style: annotationSettings.style
                                })
                              }
                            );
                            
                            if (!response.ok) {
                              throw new Error('生成注释失败');
                            }
                            
                            // 处理流式响应
                            const reader = response.body.getReader();
                            const decoder = new TextDecoder();
                            let buffer = '';
                            
                            while (true) {
                              const {done, value} = await reader.read();
                              if (done) break;
                              
                              buffer += decoder.decode(value, {stream: true});
                              const lines = buffer.split('\n\n');
                              buffer = lines.pop() || '';
                              
                              for (const line of lines) {
                                if (line.startsWith('data: ')) {
                                  const data = JSON.parse(line.slice(6));
                                  
                                  if (data.type === 'content') {
                                    // 实时更新注释内容
                                    setAnnotations(prev => ({
                                      ...prev,
                                      [currentPage]: (prev[currentPage] || '') + data.content
                                    }));
                                  } else if (data.type === 'notification_added') {
                                    console.log('系统通知已添加到主对话:', data.conversation_id);
                                    // 触发全局事件，通知ChatWindow刷新
                                    const refreshEvent = new CustomEvent('refreshChatConversation', {
                                      detail: { conversationId: data.conversation_id }
                                    });
                                    if (typeof window !== 'undefined') {
                                      window.dispatchEvent(refreshEvent);
                                    }
                                  } else if (data.type === 'done') {
                                    console.log('注释生成完成');
                                    // 重新加载注释以获取完整内容
                                    loadAnnotation(currentPage);
                                  } else if (data.type === 'error') {
                                    console.error('生成注释错误:', data.error);
                                    alert('生成注释失败: ' + data.error);
                                  }
                                }
                              }
                            }
                          } catch (error) {
                            console.error('生成注释失败:', error);
                            alert('生成注释失败: ' + error.message);
                          }
                        }}
                        style={{
                          width: '100%',
                          padding: '4px 8px',
                          fontSize: '11px',
                          backgroundColor: '#c0c0c0',
                          border: 'none',
                          borderBottom: '1px solid #a0a0a0',
                          cursor: 'pointer',
                          fontFamily: 'MS Sans Serif, sans-serif',
                          textAlign: 'left'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#d0d0d0'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#c0c0c0'}
                      >
                        生成注释
                      </button>
                      
                      <button
                        onClick={async () => {
                          console.log('视觉生成功能');
                          setShowLLMMenu(false);
                          setAnnotationMode('preview');
                          
                          try {
                            // 准备提示词模板
                            let promptTemplate = '';
                            if (annotationSettings.style === 'custom') {
                              promptTemplate = annotationSettings.customPrompt;
                            } else if (annotationStyles[annotationSettings.style]) {
                              promptTemplate = annotationStyles[annotationSettings.style].prompt;
                            }
                            
                            console.log('使用视觉生成，注释风格:', annotationSettings.style);
                            
                            // 调用后端API视觉生成注释
                            const response = await fetch(
                              `http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/${currentPage}/generate-visual`,
                              {
                                method: 'POST',
                                headers: {
                                  'Content-Type': 'application/json',
                                },
                                body: JSON.stringify({
                                  promptTemplate: promptTemplate,
                                  style: annotationSettings.style
                                })
                              }
                            );
                            
                            if (!response.ok) {
                              throw new Error('视觉生成注释失败');
                            }
                            
                            // 处理流式响应
                            const reader = response.body.getReader();
                            const decoder = new TextDecoder();
                            let buffer = '';
                            
                            while (true) {
                              const {done, value} = await reader.read();
                              if (done) break;
                              
                              buffer += decoder.decode(value, {stream: true});
                              const lines = buffer.split('\n\n');
                              buffer = lines.pop() || '';
                              
                              for (const line of lines) {
                                if (line.startsWith('data: ')) {
                                  const data = JSON.parse(line.slice(6));
                                  
                                  if (data.type === 'content') {
                                    setAnnotations(prev => ({
                                      ...prev,
                                      [currentPage]: (prev[currentPage] || '') + data.content
                                    }));
                                  } else if (data.type === 'notification_added') {
                                    console.log('系统通知已添加（视觉生成）');
                                    const refreshEvent = new CustomEvent('refreshChatConversation', {
                                      detail: { conversationId: data.conversation_id }
                                    });
                                    if (typeof window !== 'undefined') {
                                      window.dispatchEvent(refreshEvent);
                                    }
                                  } else if (data.type === 'done') {
                                    console.log('视觉生成注释完成');
                                    loadAnnotation(currentPage);
                                  } else if (data.type === 'error') {
                                    console.error('视觉生成错误:', data.error);
                                    alert('视觉生成注释失败: ' + data.error);
                                  }
                                }
                              }
                            }
                          } catch (error) {
                            console.error('视觉生成失败:', error);
                            alert('视觉生成注释失败: ' + error.message);
                          }
                        }}
                        style={{
                          width: '100%',
                          padding: '4px 8px',
                          fontSize: '11px',
                          backgroundColor: '#c0c0c0',
                          border: 'none',
                          borderBottom: '1px solid #a0a0a0',
                          cursor: 'pointer',
                          fontFamily: 'MS Sans Serif, sans-serif',
                          textAlign: 'left'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#d0d0d0'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#c0c0c0'}
                      >
                        👁️ 视觉生成
                      </button>
                      
                      <button
                        onClick={async () => {
                          console.log('批量生成功能');
                          setShowLLMMenu(false);
                          setShowOutlinePanel(true); // 直接打开侧栏，不打开弹窗
                          setBatchOutlineStatus('正在准备...');
                          setBatchOutline(null);
                          setIsBatchGenerating(true);
                          setIsStage2(false);
                          setStage2Completed(false);
                          setBatchProgress({ completed: 0, total: 0 });
                          
                          try {
                            // 调用后端API生成大纲
                            const response = await fetch(
                              `http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/outline`,
                              {
                                method: 'POST',
                                headers: {
                                  'Content-Type': 'application/json',
                                }
                              }
                            );
                            
                            if (!response.ok) {
                              throw new Error('生成批量大纲失败');
                            }
                            
                            // 处理流式响应
                            const reader = response.body.getReader();
                            const decoder = new TextDecoder();
                            let buffer = '';
                            
                            while (true) {
                              const {done, value} = await reader.read();
                              if (done) break;
                              
                              buffer += decoder.decode(value, {stream: true});
                              const lines = buffer.split('\n\n');
                              buffer = lines.pop() || '';
                              
                              for (const line of lines) {
                                if (line.startsWith('data: ')) {
                                  const data = JSON.parse(line.slice(6));
                                  
                                  if (data.type === 'status') {
                                    setBatchOutlineStatus(data.message);
                                  } else if (data.type === 'content') {
                                    // 显示LLM生成的内容
                                    setBatchOutlineStatus(prev => prev + data.content);
                                  } else if (data.type === 'group_content') {
                                    // 显示子模型的流式输出
                                    setBatchOutlineStatus(prev => prev + data.content);
                                  } else if (data.type === 'group_done') {
                                    setBatchOutlineStatus(prev => prev + `\n\n分组${data.group}完成\n`);
                                  } else if (data.type === 'merge_content') {
                                    setBatchOutlineStatus(prev => prev + data.content);
                                  } else if (data.type === 'outline') {
                                    console.log('大纲生成完成:', data.outline);
                                    setBatchOutline(data.outline);
                                    setBatchOutlineStatus('大纲生成完成！');
                                    setIsBatchGenerating(false);
                                  } else if (data.type === 'info') {
                                    console.log('大纲生成信息:', data.message);
                                    setBatchOutlineStatus(prev => prev + '\n' + data.message);
                                  } else if (data.type === 'done') {
                                    console.log('批量生成流程完成');
                                    if (!data.outline) {
                                      setIsBatchGenerating(false);
                                    }
                                  } else if (data.type === 'error') {
                                    console.error('生成大纲错误:', data.error);
                                    setBatchOutlineStatus('错误: ' + data.error);
                                    setIsBatchGenerating(false);
                                  }
                                }
                              }
                            }
                          } catch (error) {
                            console.error('生成批量大纲失败:', error);
                            setBatchOutlineStatus('生成失败: ' + error.message);
                            setIsBatchGenerating(false);
                          }
                        }}
                        style={{
                          width: '100%',
                          padding: '4px 8px',
                          fontSize: '11px',
                          backgroundColor: '#c0c0c0',
                          border: 'none',
                          borderBottom: '1px solid #a0a0a0',
                          cursor: 'pointer',
                          fontFamily: 'MS Sans Serif, sans-serif',
                          textAlign: 'left'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#d0d0d0'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#c0c0c0'}
                      >
                        📚 批量...
                      </button>
                      
                      <button
                        onClick={() => {
                          console.log('打开注释设置');
                          setShowLLMMenu(false);
                          setShowAnnotationSettings(true);
                        }}
                        style={{
                          width: '100%',
                          padding: '4px 8px',
                          fontSize: '11px',
                          backgroundColor: '#c0c0c0',
                          border: 'none',
                          cursor: 'pointer',
                          fontFamily: 'MS Sans Serif, sans-serif',
                          textAlign: 'left'
                        }}
                        onMouseEnter={(e) => e.target.style.backgroundColor = '#d0d0d0'}
                        onMouseLeave={(e) => e.target.style.backgroundColor = '#c0c0c0'}
                      >
                        ⚙️ 注释设置
                      </button>
                    </div>
                  )}
                </div>
                
                {/* 预览/编辑模式切换按钮 */}
                <button
                  onClick={() => {
                    setAnnotationMode(annotationMode === 'preview' ? 'edit' : 'preview');
                    console.log('注释模式切换:', annotationMode === 'preview' ? 'edit' : 'preview');
                  }}
                  style={{
                    padding: '2px 6px',
                    fontSize: '11px',
                    backgroundColor: '#c0c0c0',
                    border: '2px outset #c0c0c0',
                    borderRadius: '0px',
                    cursor: 'pointer',
                    fontFamily: 'MS Sans Serif, sans-serif',
                    height: '20px',
                    minWidth: '24px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}
                  title={annotationMode === 'preview' ? "切换到编辑模式" : "切换到预览模式"}
                >
                  {annotationMode === 'preview' ? '✏️' : '👁️'}
                </button>
              </div>
            </div>
            
            {/* 注释内容区域 */}
            <div style={{
              flex: 1,
              padding: '8px',
              overflow: 'auto'
            }}>
              {annotationMode === 'preview' ? (
                <div style={{
                  fontSize: '12px',
                  fontFamily: 'MS Sans Serif, sans-serif',
                  lineHeight: '1.4',
                  whiteSpace: 'pre-wrap',
                  wordBreak: 'break-word'
                }}>
                  {annotations[currentPage] ? (
                    <ReactMarkdown
                      remarkPlugins={[remarkGfm, remarkMath]}
                      rehypePlugins={[rehypeKatex]}
                      components={{
                        // 自定义样式以匹配Windows 98风格
                        h1: ({children}) => <h1 style={{fontSize: '14px', fontWeight: 'bold', margin: '8px 0 4px 0'}}>{children}</h1>,
                        h2: ({children}) => <h2 style={{fontSize: '13px', fontWeight: 'bold', margin: '6px 0 3px 0'}}>{children}</h2>,
                        h3: ({children}) => <h3 style={{fontSize: '12px', fontWeight: 'bold', margin: '4px 0 2px 0'}}>{children}</h3>,
                        p: ({children}) => <p style={{margin: '2px 0'}}>{children}</p>,
                        code: ({children}) => <code style={{backgroundColor: '#f0f0f0', padding: '1px 2px', fontFamily: 'monospace'}}>{children}</code>,
                        pre: ({children}) => <pre style={{backgroundColor: '#f0f0f0', padding: '4px', margin: '4px 0', overflow: 'auto'}}>{children}</pre>,
                        blockquote: ({children}) => <blockquote style={{borderLeft: '3px solid #c0c0c0', paddingLeft: '8px', margin: '4px 0', fontStyle: 'italic'}}>{children}</blockquote>,
                        ul: ({children}) => <ul style={{margin: '4px 0', paddingLeft: '16px'}}>{children}</ul>,
                        ol: ({children}) => <ol style={{margin: '4px 0', paddingLeft: '16px'}}>{children}</ol>,
                        li: ({children}) => <li style={{margin: '1px 0'}}>{children}</li>,
                        table: ({children}) => <table style={{border: '1px solid #c0c0c0', borderCollapse: 'collapse', margin: '4px 0'}}>{children}</table>,
                        th: ({children}) => <th style={{border: '1px solid #c0c0c0', padding: '2px 4px', backgroundColor: '#e0e0e0'}}>{children}</th>,
                        td: ({children}) => <td style={{border: '1px solid #c0c0c0', padding: '2px 4px'}}>{children}</td>
                      }}
                    >
                      {annotations[currentPage]}
                    </ReactMarkdown>
                  ) : (
                    '暂无注释'
                  )}
                </div>
              ) : (
                <div style={{ position: 'relative', height: '100%' }}>
                  <textarea
                    value={annotations[currentPage] || ''}
                    onChange={(e) => {
                      const newContent = e.target.value;
                      setAnnotations(prev => ({
                        ...prev,
                        [currentPage]: newContent
                      }));
                      // 自动保存（防抖）
                      debouncedSaveAnnotation(currentPage, newContent);
                    }}
                    placeholder="在此输入注释..."
                    style={{
                      width: '100%',
                      height: '100%',
                      border: '2px inset #c0c0c0',
                      backgroundColor: '#ffffff',
                      fontSize: '12px',
                      fontFamily: 'MS Sans Serif, sans-serif',
                      padding: '4px',
                      resize: 'none',
                      outline: 'none'
                    }}
                  />
                  {/* 保存状态指示器 */}
                  {isSavingAnnotation && (
                    <div style={{
                      position: 'absolute',
                      top: '4px',
                      right: '4px',
                      fontSize: '10px',
                      color: '#666',
                      backgroundColor: '#f0f0f0',
                      padding: '2px 4px',
                      border: '1px solid #c0c0c0'
                    }}>
                      保存中...
                    </div>
                  )}
                </div>
              )}
            </div>
            
            {/* 注释设置面板 */}
            {showAnnotationSettings && (
              <div 
                data-annotation-settings
                style={{
                  position: 'absolute',
                  top: '40px',
                  right: '10px',
                  width: '320px',
                  backgroundColor: '#c0c0c0',
                  border: '2px outset #c0c0c0',
                  padding: '8px',
                  fontSize: '11px',
                  fontFamily: 'MS Sans Serif, sans-serif',
                  zIndex: 1001,
                  boxShadow: '2px 2px 4px rgba(0,0,0,0.3)',
                  maxHeight: '500px',
                  overflowY: 'auto'
                }}>
                <div style={{ 
                  fontWeight: 'bold', 
                  marginBottom: '8px', 
                  borderBottom: '1px solid #808080', 
                  paddingBottom: '4px',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}>
                  <span>注释设置</span>
                  <button
                    onClick={() => setShowAnnotationSettings(false)}
                    style={{
                      backgroundColor: '#c0c0c0',
                      border: '1px outset #c0c0c0',
                      cursor: 'pointer',
                      fontSize: '10px',
                      padding: '0 4px'
                    }}
                  >
                    ✕
                  </button>
                </div>
                
                {/* 注释风格选择 */}
                <div style={{ marginBottom: '12px' }}>
                  <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>
                    注释风格:
                  </label>
                  <select
                    value={annotationSettings.style}
                    onChange={(e) => {
                      const newSettings = { ...annotationSettings, style: e.target.value };
                      saveAnnotationSettings(newSettings);
                    }}
                    style={{
                      width: '100%',
                      padding: '2px',
                      fontSize: '11px',
                      fontFamily: 'MS Sans Serif, sans-serif',
                      border: '1px inset #c0c0c0',
                      backgroundColor: '#ffffff'
                    }}
                  >
                    <option value="detailed">详细注释</option>
                    <option value="simple">简洁注释</option>
                    <option value="academic">学术注释</option>
                    <option value="qanda">问答式注释</option>
                    <option value="custom">自定义</option>
                  </select>
                  <div style={{ 
                    fontSize: '10px', 
                    color: '#666', 
                    marginTop: '4px',
                    padding: '4px',
                    backgroundColor: '#f0f0f0',
                    border: '1px solid #d0d0d0'
                  }}>
                    {annotationSettings.style === 'custom' ? 
                      '使用自定义提示词' : 
                      annotationStyles[annotationSettings.style]?.name
                    }
                  </div>
                </div>
                
                {/* 预设风格预览 */}
                {annotationSettings.style !== 'custom' && (
                  <div style={{ marginBottom: '12px' }}>
                    <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>
                      风格说明:
                    </label>
                    <div style={{
                      padding: '6px',
                      backgroundColor: '#ffffff',
                      border: '1px inset #c0c0c0',
                      fontSize: '10px',
                      whiteSpace: 'pre-wrap',
                      maxHeight: '120px',
                      overflowY: 'auto'
                    }}>
                      {annotationStyles[annotationSettings.style]?.prompt}
            </div>
          </div>
        )}
                
                {/* 自定义提示词 */}
                {annotationSettings.style === 'custom' && (
                  <div style={{ marginBottom: '12px' }}>
                    <label style={{ display: 'block', marginBottom: '4px', fontWeight: 'bold' }}>
                      自定义提示词:
                    </label>
                    <textarea
                      value={annotationSettings.customPrompt}
                      onChange={(e) => {
                        const newSettings = { ...annotationSettings, customPrompt: e.target.value };
                        saveAnnotationSettings(newSettings);
                      }}
                      placeholder="输入自定义提示词...\n例如：请为第{page}页生成..."
                      style={{
                        width: '100%',
                        height: '120px',
                        padding: '4px',
                        fontSize: '11px',
                        fontFamily: 'MS Sans Serif, sans-serif',
                        border: '1px inset #c0c0c0',
                        backgroundColor: '#ffffff',
                        resize: 'vertical',
                        boxSizing: 'border-box'
                      }}
                    />
                    <div style={{ 
                      fontSize: '10px', 
                      color: '#666', 
                      marginTop: '2px'
                    }}>
                      提示：使用 {'{page}'} 作为页码占位符
      </div>
    </div>
                )}
                
                {/* 状态提示 */}
                <div style={{ 
                  marginTop: '8px', 
                  padding: '4px', 
                  backgroundColor: '#e6f3ff',
                  border: '1px solid #b0d0f0',
                  fontSize: '10px'
                }}>
                  当前使用: {annotationSettings.style === 'custom' ? '自定义提示词' : annotationStyles[annotationSettings.style]?.name}
                </div>
              </div>
            )}
            
            {/* 批量生成大纲模态窗口 */}
            {showBatchOutlineModal && (
              <div style={{
                position: 'fixed',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(0, 0, 0, 0.5)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                zIndex: 2000
              }}>
                <div style={{
                  backgroundColor: '#bfbfbf',
                  border: '3px outset #f0f0f0',
                  borderRadius: '0px',
                  padding: '8px',
                  width: '80%',
                  maxWidth: '800px',
                  maxHeight: '80%',
                  display: 'flex',
                  flexDirection: 'column',
                  boxShadow: '4px 4px 8px rgba(0,0,0,0.5)',
                  fontFamily: 'MS Sans Serif, sans-serif'
                }}>
                  {/* 标题栏 */}
                  <div style={{
                    backgroundColor: '#000080',
                    color: '#ffffff',
                    padding: '2px 4px',
                    marginBottom: '8px',
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    fontSize: '11px',
                    fontWeight: 'bold'
                  }}>
                    <span>批量注释 - 生成大纲</span>
                    <button
                      onClick={() => {
                        if (!isBatchGenerating || confirm('生成正在进行中，确定要关闭吗？')) {
                          setShowBatchOutlineModal(false);
                        }
                      }}
                      style={{
                        backgroundColor: '#c0c0c0',
                        border: '1px outset #c0c0c0',
                        cursor: 'pointer',
                        fontSize: '10px',
                        padding: '0 4px',
                        fontWeight: 'bold'
                      }}
                    >
                      ✕
                    </button>
                  </div>
                  
                  {/* 内容区域 */}
                  <div style={{
                    flex: 1,
                    display: 'flex',
                    flexDirection: 'column',
                    gap: '8px',
                    overflowY: 'auto',
                    backgroundColor: '#f0f0f0',
                    border: '2px insetrgba(192, 192, 192, 0.64)',
                    padding: '8px'
                  }}>
                    {/* 状态信息 */}
                    {(isBatchGenerating || stage2Completed) && (
                      <div>
                        {/* 第二阶段进度条 */}
                        {(isStage2 || stage2Completed) && batchProgress.total > 0 && (
                          <div style={{
                            padding: '8px',
                            marginBottom: '8px',
                            backgroundColor: '#c0c0c0',
                            border: '2px inset #c0c0c0',
                            borderRadius: '0px'
                          }}>
                            <div style={{
                              fontSize: '11px',
                              fontWeight: 'bold',
                              marginBottom: '6px',
                              color: '#000000',
                              textAlign: 'center'
                            }}>
                              {stage2Completed ? '并行结束' : '并行...'} {batchProgress.completed} / {batchProgress.total}
                            </div>
                            
                            {/* Windows 98风格量子化方格进度条 */}
                            <div style={{
                              width: '100%',
                              height: '30px',
                              backgroundColor: '#c0c0c0',
                              border: '2px inset #c0c0c0',
                              borderRadius: '0px',
                              overflow: 'hidden',
                              position: 'relative',
                              display: 'flex',
                              alignItems: 'center',
                              padding: '1px'
                            }}>
                              {/* 进度条背景 */}
                              <div style={{
                                width: '100%',
                                height: '27px',
                                backgroundColor: '#f0f0f0',
                                border: '1px inset #c0c0c0',
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'flex-start',
                                padding: '2px'
                              }}>
                                {/* 量子化方格进度条 */}
                                <div style={{
                                  display: 'flex',
                                  width: '100%',
                                  gap: '2px',
                                  alignItems: 'center'
                                }}>
                                  {Array.from({ length: 25 }, (_, index) => {
                                    const progressPercentage = (batchProgress.completed / batchProgress.total) * 100;
                                    const isActive = (index + 1) * 4 <= progressPercentage; // 每格代表4%
                                    
                                    return (
                                      <div
                                        key={index}
                                        style={{
                                          flex: 1,
                                          height: '21px',
                                          backgroundColor: isActive ? '#000080' : 'transparent',
                                          border: '1px solid transparent',
                                          borderRadius: '0px',
                                          display: 'flex',
                                          alignItems: 'center',
                                          justifyContent: 'center',
                                          position: 'relative',
                                          boxSizing: 'border-box'
                                        }}
                                      >
    </div>
  );
                                  })}
                                </div>
                              </div>
                            </div>
                          </div>
                        )}
                        
                        {/* 状态文本（第一阶段或其他信息） */}
                        {(!isStage2 && !stage2Completed) && (
                          <div style={{
                            padding: '8px',
                            backgroundColor: '#c0c0c0',
                            border: '1px solid #c0c0c0',
                            fontSize: '11px',
                            whiteSpace: 'pre-wrap'
                          }}>
                            {batchOutlineStatus}
                          </div>
                        )}
                      </div>
                    )}
                    
                    {/* 细分内容展示 */}
                    {selectedSection && (
                      <div style={{
                        padding: '8px',
                        fontSize: '11px'
                      }}>
                        {/* 返回按钮 */}
                        <button
                          onClick={() => setSelectedSection(null)}
                          style={{
                            marginBottom: '12px',
                            padding: '4px 8px',
                            fontSize: '11px',
                            backgroundColor: '#c0c0c0',
                            border: '2px outset #c0c0c0',
                            borderRadius: '0px',
                            cursor: 'pointer',
                            fontFamily: 'MS Sans Serif, sans-serif'
                          }}
                          onMouseEnter={(e) => e.target.style.backgroundColor = '#d0d0d0'}
                          onMouseLeave={(e) => e.target.style.backgroundColor = '#c0c0c0'}
                        >
                          ← 返回大纲
                        </button>
                        
                        <h3 style={{ margin: '0 0 12px 0', fontSize: '13px', fontWeight: 'bold' }}>
                          📖 分段详情：{selectedSection.section_title}
                        </h3>
                        
                        {/* 分段基本信息 */}
                        <div style={{
                          padding: '8px',
                          marginBottom: '12px',
                          backgroundColor: '#e8f4fd',
                          border: '1px solid #b8daff',
                          borderRadius: '2px',
                          fontSize: '10px'
                        }}>
                          <div style={{ marginBottom: '4px' }}>
                            📄 <strong>页码范围：</strong>第{selectedSection.page_start}页 - 第{selectedSection.page_end}页
                          </div>
                        </div>
                        
                        {/* 分段概括 */}
                        <div style={{
                          padding: '8px',
                          marginBottom: '12px',
                          backgroundColor: '#fff8e1',
                          border: '1px solid #ffe082',
                          borderRadius: '2px'
                        }}>
                          <div style={{ 
                            fontWeight: 'bold', 
                            marginBottom: '6px',
                            fontSize: '11px',
                            color: '#f57c00'
                          }}>
                            内容概括
                          </div>
                          <div style={{
                            fontSize: '10px',
                            lineHeight: '1.5',
                            whiteSpace: 'pre-wrap'
                          }}>
                            {selectedSection.section_summary}
                          </div>
                        </div>
                        
                        {/* 细分列表 */}
                        <div style={{
                          fontWeight: 'bold',
                          marginBottom: '8px',
                          fontSize: '11px'
                        }}>
                          🔍 细分内容（共{selectedSection.subdivisions.length}个单元）
                        </div>
                        
                        {selectedSection.subdivisions.map((sub, idx) => (
                          <div
                            key={idx}
                            style={{
                              padding: '8px',
                              marginBottom: '8px',
                              backgroundColor: '#f5f5f5',
                              border: '1px solid #e0e0e0',
                              borderLeft: '3px solid #4caf50',
                              borderRadius: '2px'
                            }}
                          >
                            <div style={{
                              fontWeight: 'bold',
                              marginBottom: '4px',
                              fontSize: '11px',
                              color: '#2e7d32'
                            }}>
                              {sub.subdivision_number}. {sub.title}
                            </div>
                            <div style={{
                              fontSize: '10px',
                              color: '#666'
                            }}>
                              📖 第{sub.page_start}页 - 第{sub.page_end}页
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                    
                    {/* 大纲展示 */}
                    {!selectedSection && batchOutline && batchOutline.outline && (
                      <div style={{
                        padding: '8px',
                        fontSize: '11px'
                      }}>
                        <h3 style={{ margin: '0 0 12px 0', fontSize: '13px', fontWeight: 'bold' }}>
                          文档大纲
                        </h3>
                        
                        {/* 重叠信息提示 */}
                        {batchOutline.page_analysis && batchOutline.page_analysis.statistics.overlapping_pages_count > 0 && (
                          <div style={{
                            padding: '6px 8px',
                            marginBottom: '12px',
                            backgroundColor: '#ffffcc',
                            border: '2px inset #c0c0c0',
                            fontSize: '10px',
                            fontFamily: 'MS Sans Serif, sans-serif',
                            fontWeight: 'normal'
                          }}>
                            检测到 <strong>{batchOutline.page_analysis.statistics.overlapping_pages_count}</strong> 个重叠页面
                            （第 {batchOutline.page_analysis.statistics.multi_annotated_pages.join(', ')} 页），
                            这些页面会被多次注释，后续将自动融合为一个完整注释。
                          </div>
                        )}
                        
                        {batchOutline.outline.map((section, index) => {
                          // 检查这个章节是否包含重叠页面
                          const hasOverlap = batchOutline.page_analysis && 
                            batchOutline.page_analysis.statistics.multi_annotated_pages.some(
                              page => page >= section.page_start && page <= section.page_end
                            );
                          
                          return (
                          <div
                            key={index}
                            style={{
                              padding: '8px',
                              marginBottom: '8px',
                              backgroundColor: '#ffffff',
                              border: '1px solid #d0d0d0',
                              borderLeft: hasOverlap ? '3px solid #ff9800' : '3px solid #0078d4',
                              cursor: 'pointer',
                              transition: 'background-color 0.2s'
                            }}
                            onMouseEnter={(e) => e.currentTarget.style.backgroundColor = '#f8f8f8'}
                            onMouseLeave={(e) => e.currentTarget.style.backgroundColor = '#ffffff'}
                            onClick={() => {
                              console.log('点击章节:', section);
                              // 如果有细分数据，展示该分段的细分内容
                              if (batchSubdivisions && batchSubdivisions.subdivisions) {
                                const subdivision = batchSubdivisions.subdivisions.find(
                                  s => s.section_number === section.section_number
                                );
                                if (subdivision) {
                                  setSelectedSection(subdivision);
                                } else {
                                  alert('该分段暂无细分数据，请先执行第二阶段');
                                }
                              } else {
                                alert('请先执行第二阶段：点击"开始批量生成"按钮');
                              }
                            }}
                          >
                            <div style={{
                              fontWeight: 'bold',
                              marginBottom: '4px',
                              fontSize: '12px',
                              color: hasOverlap ? '#ff9800' : '#0078d4',
                              display: 'flex',
                              alignItems: 'center',
                              gap: '4px'
                            }}>
                              {section.section_number}. {section.title}
                              {hasOverlap && (
                                <span style={{
                                  fontSize: '9px',
                                  backgroundColor: '#fff3e0',
                                  color: '#e65100',
                                  padding: '2px 4px',
                                  borderRadius: '2px',
                                  fontWeight: 'normal'
                                }} title="此章节包含会被多次注释的页面">
                                  ! 含重叠页
                                </span>
                              )}
                            </div>
                            <div style={{
                              fontSize: '10px',
                              color: '#666',
                              marginBottom: '4px'
                            }}>
                              📖 第{section.page_start}页 - 第{section.page_end}页
                            </div>
                            <div style={{
                              fontSize: '10px',
                              lineHeight: '1.4'
                            }}>
                              {section.description}
                            </div>
                          </div>
                        );
                        })}
                      </div>
                    )}
                    
                    {/* 加载完成后的操作按钮 */}
                    {!isBatchGenerating && !selectedSection && batchOutline && (
                      <div style={{
                        padding: '8px',
                        borderTop: '1px solid #d0d0d0',
                        display: 'flex',
                        gap: '8px',
                        justifyContent: 'flex-end'
                      }}>
                        <button
                          onClick={async () => {
                            console.log('开始第二阶段：细分分段');
                            setIsBatchGenerating(true);
                            setIsStage2(true);
                            setStage2Completed(false);
                            setBatchOutlineStatus('正在并行细分各个分段...');
                            setBatchProgress({ completed: 0, total: batchOutline.outline.length });
                            
                            try {
                              // 调用第二阶段API
                              const response = await fetch(
                                `http://localhost:8081/api/boards/${boardId}/windows/${windowId}/annotations/batch/subdivide`,
                                {
                                  method: 'POST',
                                  headers: {
                                    'Content-Type': 'application/json',
                                  }
                                }
                              );
                              
                              if (!response.ok) {
                                throw new Error('细分处理失败');
                              }
                              
                              // 处理流式响应
                              const reader = response.body.getReader();
                              const decoder = new TextDecoder();
                              let buffer = '';
                              let currentSection = null;
                              
                              while (true) {
                                const {done, value} = await reader.read();
                                if (done) break;
                                
                                buffer += decoder.decode(value, {stream: true});
                                const lines = buffer.split('\n\n');
                                buffer = lines.pop() || '';
                                
                                for (const line of lines) {
                                  if (line.startsWith('data: ')) {
                                    const data = JSON.parse(line.slice(6));
                                    
                                    if (data.type === 'status') {
                                      setBatchOutlineStatus(data.message);
                                    } else if (data.type === 'section_start') {
                                      currentSection = data.section;
                                      // 第二阶段不显示详细信息，只记录
                                    } else if (data.type === 'section_content') {
                                      // 第二阶段不显示流式输出内容，避免混乱
                                    } else if (data.type === 'section_done') {
                                      // 更新进度
                                      setBatchProgress({ completed: data.completed, total: data.total });
                                      setBatchOutlineStatus(`正在并行细分各个分段...\n进度: ${data.completed}/${data.total}`);
                                    } else if (data.type === 'complete') {
                                      console.log('所有分段细分完成:', data.data);
                                      // 确保进度条显示为100%完成状态
                                      setBatchProgress(prev => ({ completed: prev.total, total: prev.total }));
                                      setBatchSubdivisions(data.data); // 保存细分数据
                                      setIsBatchGenerating(false);
                                      setStage2Completed(true); // 标记第二阶段完成，但保留进度条显示
                                    } else if (data.type === 'warning') {
                                      setBatchOutlineStatus(prev => prev + `\n警告: ${data.message}`);
                                    } else if (data.type === 'done') {
                                      console.log('细分流程完成');
                                      setIsBatchGenerating(false);
                                    } else if (data.type === 'error') {
                                      console.error('细分错误:', data.error);
                                      setBatchOutlineStatus(prev => prev + `\n错误: ${data.error}`);
                                      setIsBatchGenerating(false);
                                    }
                                  }
                                }
                              }
                            } catch (error) {
                              console.error('细分处理失败:', error);
                              setBatchOutlineStatus(prev => prev + `\n细分失败: ${error.message}`);
                              setIsBatchGenerating(false);
                            }
                          }}
                          style={{
                            padding: '4px 12px',
                            fontSize: '11px',
                            backgroundColor: '#0078d4',
                            color: '#ffffff',
                            border: '2px outset #0078d4',
                            borderRadius: '0px',
                            cursor: 'pointer',
                            fontFamily: 'MS Sans Serif, sans-serif',
                            fontWeight: 'bold'
                          }}
                          onMouseEnter={(e) => e.target.style.backgroundColor = '#005a9e'}
                          onMouseLeave={(e) => e.target.style.backgroundColor = '#0078d4'}
                        >
                          {batchSubdivisions ? '重新细分' : '开始第二阶段'}
                        </button>
                        <button
                          onClick={() => setShowBatchOutlineModal(false)}
                          style={{
                            padding: '4px 12px',
                            fontSize: '11px',
                            backgroundColor: '#c0c0c0',
                            border: '2px outset #c0c0c0',
                            borderRadius: '0px',
                            cursor: 'pointer',
                            fontFamily: 'MS Sans Serif, sans-serif'
                          }}
                          onMouseEnter={(e) => e.target.style.backgroundColor = '#d0d0d0'}
                          onMouseLeave={(e) => e.target.style.backgroundColor = '#c0c0c0'}
                        >
                          关闭
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}
            
          </div>
        )}
      </div>
    </div>
  );
}

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
  
  // 如果有file_path字段，说明已上传
  if (window.file_path) {
    return true;
  }
  
  return false;
};

// toMediaUrl 函数
const toMediaUrl = (windowOrContent, boardId) => {
  console.log('🔗 toMediaUrl 被调用:', { windowOrContent, boardId });
  
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
  
  // 优先使用 content 字段中的绝对路径来提取课程ID（最可靠）
  if (content && typeof content === 'string' && (content.includes('\\') || content.includes('/'))) {
    const pathParts = content.split(/[\\\/]/);
    const filename = pathParts[pathParts.length - 1];
    
    // 从绝对路径中提取课程ID
    const courseIndex = pathParts.findIndex(part => part.startsWith('course-'));
    if (courseIndex !== -1) {
      const courseId = pathParts[courseIndex];
      console.log('🔍 从content绝对路径提取课程ID:', courseId);
      const staticUrl = `http://localhost:8081/static/files/courses/${courseId}/${boardId}/files/${encodeURIComponent(filename)}`;
      console.log('🔗 从content绝对路径生成静态URL:', staticUrl);
      return staticUrl;
    }
  }
  
  // 备用：使用 file_path 生成静态文件URL
  if (filePath && typeof filePath === 'string') {
    let filename;
    let courseId;
    
    if (filePath.startsWith('files/')) {
      // 旧格式：files/filename
      filename = filePath.substring(6); // 移除 "files/" 前缀
      
      // 动态获取courseId - 优先从URL路径中提取
      const currentPath = window.location.pathname;
      console.log('🔍 当前URL路径:', currentPath);
      const courseMatch = currentPath.match(/\/courses\/(course-\d+)/);
      courseId = courseMatch ? courseMatch[1] : 'course-1756987907632'; // 默认值作为备选
      console.log('🔍 提取的课程ID:', courseId);
      
      const staticUrl = `http://localhost:8081/static/files/courses/${courseId}/${boardId}/files/${encodeURIComponent(filename)}`;
      console.log('🔗 从file_path生成静态URL:', staticUrl, 'courseId:', courseId);
      return staticUrl;
    } else if (filePath.includes('\\') || filePath.includes('/')) {
      // 新格式：绝对路径，需要提取文件名和课程ID
      const pathParts = filePath.split(/[\\\/]/);
      filename = pathParts[pathParts.length - 1];
      
      // 优先从路径中提取课程ID
      const courseIndex = pathParts.findIndex(part => part.startsWith('course-'));
      if (courseIndex !== -1) {
        courseId = pathParts[courseIndex];
        console.log('🔍 从文件路径提取课程ID:', courseId);
      } else {
        // 如果路径中没有课程ID，从URL中提取
        const currentPath = window.location.pathname;
        const courseMatch = currentPath.match(/\/courses\/(course-\d+)/);
        courseId = courseMatch ? courseMatch[1] : 'course-1756987907632';
        console.log('🔍 从URL路径提取课程ID:', courseId);
      }
      
      console.log('🔍 从绝对路径提取:', { filename, courseId, filePath });
      const staticUrl = `http://localhost:8081/static/files/courses/${courseId}/${boardId}/files/${encodeURIComponent(filename)}`;
      console.log('🔗 从绝对路径生成静态URL:', staticUrl);
      return staticUrl;
    }
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

// 文档窗口渲染器组件（Word文档等）
function DocumentWindowRenderer({ window: windowData, onUpload, boardId }) {
  const [isPaginationMode, setIsPaginationMode] = useState(false);

  console.log('📄 文档窗口渲染:', {
    windowId: windowData.id,
    windowContent: windowData.content,
    hasContent: !!windowData.content
  });

  if (!hasRealMediaContent(windowData)) {
    console.log('📄 文档窗口无内容，显示占位符');
    return (
      <label className="pdf-placeholder" title="点击上传文档" style={{ flex: 1 }}>
        📄 文档内容
        <p>点击上传Word文档</p>
        <input
          type="file"
          accept=".doc,.docx,.ppt,.pptx,.xls,.xlsx"
          style={{ display: 'none' }}
          onChange={(e) => onUpload(e.target.files)}
        />
      </label>
    );
  }

  const documentUrl = toMediaUrl(windowData, boardId);
  console.log('📄 文档URL生成:', documentUrl);

  // 如果启用分页模式，显示分页组件（转换为PDF后）
  if (isPaginationMode) {
    return (
      <PDFPaginationViewer 
        pdfUrl={documentUrl} 
        onClose={() => setIsPaginationMode(false)}
        boardId={boardId}
        windowId={windowData.id}
      />
    );
  }

  // 默认iframe模式
  return (
    <div className="pdf-container" style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 文档工具栏 */}
      <div style={{
        backgroundColor: '#c0c0c0',
        borderBottom: '2px outset #c0c0c0',
        padding: '2px 4px',
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
        height: '24px',
        flexShrink: 0
      }}>
        <button
          onClick={() => {
            console.log('分页模式按钮被点击');
            setIsPaginationMode(true);
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
          onMouseDown={(e) => { e.target.style.border = '2px inset #c0c0c0'; e.target.style.backgroundColor = '#a0a0a0'; }}
          onMouseUp={(e) => { e.target.style.border = '2px outset #c0c0c0'; e.target.style.backgroundColor = '#c0c0c0'; }}
          onMouseLeave={(e) => { e.target.style.border = '2px outset #c0c0c0'; e.target.style.backgroundColor = '#c0c0c0'; }}
        >
          分页模式
        </button>
      </div>
      
      {/* 文档内容区域 */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <iframe
          title="document"
          style={{ width: '100%', height: '100%', border: 'none' }}
          src={documentUrl}
          onLoad={() => console.log('📄 文档iframe加载完成')}
          onError={(e) => console.error('📄 文档iframe加载错误:', e)}
        ></iframe>
      </div>
    </div>
  );
}

// PDF窗口渲染器组件
function PDFWindowRenderer({ window: windowData, onUpload, boardId }) {
  const [isPaginationMode, setIsPaginationMode] = useState(false);
  const [targetPage, setTargetPage] = useState(null);

  console.log('📄 PDF窗口渲染:', {
    windowId: windowData.id,
    windowContent: windowData.content,
    hasContent: !!windowData.content
  });

  // 监听打开PDF页面事件
  useEffect(() => {
    const handleOpenPDFPageInternal = (event) => {
      const { windowId, page } = event.detail || {};
      
      if (windowId === windowData.id) {
        console.log('📖 PDF窗口收到跳转请求:', { windowId, page });
        setIsPaginationMode(true);
        setTargetPage(page);
      }
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('openPDFPageInternal', handleOpenPDFPageInternal);
    }
    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('openPDFPageInternal', handleOpenPDFPageInternal);
      }
    };
  }, [windowData.id]);

  if (!hasRealMediaContent(windowData)) {
    console.log('📄 PDF窗口无内容，显示占位符');
    return (
      <label className="pdf-placeholder" title="点击上传PDF" style={{ flex: 1 }}>
        📄 PDF内容
        <p>点击上传PDF</p>
        <input
          type="file"
          accept="application/pdf"
          style={{ display: 'none' }}
          onChange={(e) => onUpload(e.target.files)}
        />
      </label>
    );
  }

  const pdfUrl = toMediaUrl(windowData, boardId);
  console.log('📄 PDF URL生成:', pdfUrl);

  // 如果启用分页模式，显示分页组件
  if (isPaginationMode) {
    return (
      <PDFPaginationViewer 
        pdfUrl={pdfUrl} 
        onClose={() => {
          setIsPaginationMode(false);
          setTargetPage(null);
        }}
        boardId={boardId}
        windowId={windowData.id}
        initialPage={targetPage}
      />
    );
  }

  // 默认iframe模式
  return (
    <div className="pdf-container" style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* PDF工具栏 */}
      <div style={{
        backgroundColor: '#c0c0c0',
        borderBottom: '2px outset #c0c0c0',
        padding: '2px 4px',
        display: 'flex',
        alignItems: 'center',
        gap: '4px',
        height: '24px',
        flexShrink: 0
      }}>
        <button
          onClick={() => {
            console.log('分页模式按钮被点击');
            setIsPaginationMode(true);
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
          onMouseDown={(e) => { e.target.style.border = '2px inset #c0c0c0'; e.target.style.backgroundColor = '#a0a0a0'; }}
          onMouseUp={(e) => { e.target.style.border = '2px outset #c0c0c0'; e.target.style.backgroundColor = '#c0c0c0'; }}
          onMouseLeave={(e) => { e.target.style.border = '2px outset #c0c0c0'; e.target.style.backgroundColor = '#c0c0c0'; }}
        >
          分页模式
        </button>
      </div>
      
      {/* PDF内容区域 */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <iframe
          title="pdf"
          style={{ width: '100%', height: '100%', border: 'none' }}
          src={pdfUrl}
          onLoad={() => console.log('📄 PDF iframe 加载完成')}
          onError={(e) => console.error('📄 PDF iframe 加载错误:', e)}
        ></iframe>
      </div>
    </div>
  );
}

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
  
  // 简单的滚动同步状态
  const [isScrollingSyncing, setIsScrollingSyncing] = useState(false);
  const [isUserInteracting, setIsUserInteracting] = useState({ left: false, right: false });

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
    
    // 内容变化时也触发同步到右侧
    if (isTypewriterMode && !isScrollingSyncing && previewRef.current) {
      setIsScrollingSyncing(true);
      const editorLineRatio = getLineBasedScrollRatio(textareaRef.current, true);
      setLineBasedScrollRatio(previewRef.current, editorLineRatio, false);
      
      setTimeout(() => {
        setIsScrollingSyncing(false);
      }, 50);
    }
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

  // 简单的光标事件处理 - 标记用户正在与左侧交互并立即同步
  const handleCursorEvents = () => {
    updateCursorPosition();
    setIsUserInteracting(prev => ({ ...prev, left: true }));
    
    // 立即触发同步到右侧
    if (isTypewriterMode && !isScrollingSyncing && previewRef.current) {
      setIsScrollingSyncing(true);
      const editorLineRatio = getLineBasedScrollRatio(textareaRef.current, true);
      setLineBasedScrollRatio(previewRef.current, editorLineRatio, false);
      
      setTimeout(() => {
        setIsScrollingSyncing(false);
      }, 50);
    }
    
    // 2秒后自动重置交互状态
    setTimeout(() => {
      setIsUserInteracting(prev => ({ ...prev, left: false }));
    }, 2000);
  };

  // 计算基于行数的滚动比例
  const getLineBasedScrollRatio = (element, isEditor = false) => {
    if (!element) return 0;
    
    if (isEditor) {
      // 对于编辑器，基于光标位置计算行数比例
      const text = element.value;
      const cursorPos = element.selectionStart;
      const textBeforeCursor = text.substring(0, cursorPos);
      const currentLine = textBeforeCursor.split('\n').length;
      const totalLines = text.split('\n').length;
      
      return totalLines > 1 ? (currentLine - 1) / (totalLines - 1) : 0;
    } else {
      // 对于预览区域，基于滚动位置估算行数比例
      if (element.scrollHeight <= element.clientHeight) return 0;
      
      // 获取预览区域的行数（通过计算文本内容）
      const previewText = element.textContent || '';
      const previewLines = previewText.split('\n').filter(line => line.trim().length > 0).length;
      
      // 如果预览区域有内容，基于滚动位置和内容行数估算比例
      if (previewLines > 0) {
        const scrollRatio = element.scrollTop / (element.scrollHeight - element.clientHeight);
        return Math.max(0, Math.min(1, scrollRatio));
      }
      
      return 0;
    }
  };

  // 设置基于行数的滚动比例
  const setLineBasedScrollRatio = (element, ratio, isEditor = false) => {
    if (!element) return;
    
    const clampedRatio = Math.max(0, Math.min(1, ratio));
    
    if (isEditor) {
      // 对于编辑器，将行数比例转换为滚动位置
      if (element.scrollHeight <= element.clientHeight) return;
      const maxScroll = element.scrollHeight - element.clientHeight;
      element.scrollTop = maxScroll * clampedRatio;
    } else {
      // 对于预览区域，直接设置滚动位置
      if (element.scrollHeight <= element.clientHeight) return;
      const maxScroll = element.scrollHeight - element.clientHeight;
      element.scrollTop = maxScroll * clampedRatio;
    }
  };

  // 编辑器滚动事件处理 - 基于行数比例同步到预览区域
  const handleEditorScroll = () => {
    if (!isTypewriterMode || isScrollingSyncing || !previewRef.current || !isUserInteracting.left) return;
    
    setIsScrollingSyncing(true);
    const editorLineRatio = getLineBasedScrollRatio(textareaRef.current, true);
    setLineBasedScrollRatio(previewRef.current, editorLineRatio, false);
    
    // 短暂延迟后重置同步标志
    setTimeout(() => {
      setIsScrollingSyncing(false);
    }, 50);
  };

  // 预览区域滚动事件处理 - 基于行数比例同步到编辑器
  const handlePreviewScroll = () => {
    if (!isTypewriterMode || isScrollingSyncing || !textareaRef.current || !isUserInteracting.right) return;
    
    setIsScrollingSyncing(true);
    const previewLineRatio = getLineBasedScrollRatio(previewRef.current, false);
    setLineBasedScrollRatio(textareaRef.current, previewLineRatio, true);
    
    // 短暂延迟后重置同步标志
    setTimeout(() => {
      setIsScrollingSyncing(false);
    }, 50);
  };





  // 简化的 Markdown 组件（移除复杂的坐标同步）
  const markdownComponents = {
    // 可以在这里添加自定义的markdown组件样式
  };

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

      {/* 简化的调试面板 */}
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
          <span>打字机模式: <strong>{isTypewriterMode ? '开启' : '关闭'}</strong></span>
          <span>左侧交互: <strong>{isUserInteracting.left ? '是' : '否'}</strong></span>
          <span>右侧交互: <strong>{isUserInteracting.right ? '是' : '否'}</strong></span>
          <span>左侧行数比例: <strong>{textareaRef.current ? (getLineBasedScrollRatio(textareaRef.current, true) * 100).toFixed(1) + '%' : 'N/A'}</strong></span>
          <span>右侧滚动比例: <strong>{previewRef.current ? (getLineBasedScrollRatio(previewRef.current, false) * 100).toFixed(1) + '%' : 'N/A'}</strong></span>
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
            onClick={() => {
              setIsUserInteracting(prev => ({ ...prev, right: true }));
              
              // 立即触发同步到左侧
              if (isTypewriterMode && !isScrollingSyncing && textareaRef.current) {
                setIsScrollingSyncing(true);
                const previewLineRatio = getLineBasedScrollRatio(previewRef.current, false);
                setLineBasedScrollRatio(textareaRef.current, previewLineRatio, true);
                
                setTimeout(() => {
                  setIsScrollingSyncing(false);
                }, 50);
              }
              
              // 2秒后自动重置交互状态
              setTimeout(() => {
                setIsUserInteracting(prev => ({ ...prev, right: false }));
              }, 2000);
            }}
            onMouseDown={() => {
              setIsUserInteracting(prev => ({ ...prev, right: true }));
            }}
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
              key={`markdown-${localContent.length}`}
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
  
  // 聊天窗口ID常量
  const CHAT_WINDOW_ID = 'chat-window-special';
  
  // 创建聊天窗口对象
  const createChatWindow = () => {
    return {
      id: CHAT_WINDOW_ID,
      type: 'chat',
      title: `💬 AI助手 - ${boardName}`,
      position: { x: 150, y: 100 },
      size: { width: 400, height: 500 },
      content: '',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString()
    };
  };
  
  // 包装setWindows来跟踪调用来源
  const setWindowsWithTrace = (newWindows) => {
    console.log('🔄 setWindows被调用:', {
      新窗口数量: Array.isArray(newWindows) ? newWindows.length : '函数调用',
      调用堆栈: new Error().stack?.split('\n').slice(1, 4).join('\n')
    });
    setWindows(newWindows);
  };
  
  // 调试：监听windows状态变化
  useEffect(() => {
    // 更新ref以便其他地方获取最新状态
    windowsRef.current = windows;
    
    console.log('🔄 Windows状态变化:', {
      数量: windows.length,
      窗口列表: windows.map(w => ({ id: w.id, title: w.title, position: w.position }))
    });
  }, [windows]);
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
  const previousHiddenStateRef = useRef(''); // 记录上次的隐藏状态
  const lastSaveStateRef = useRef({}); // 记录上次保存的窗口状态
  const windowsRef = useRef([]); // 用于获取最新的windows状态
  const deletedIconPositionsRef = useRef([]); // 记录被删除图标的位置，供新图标重用
  
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
    // 首先检查是否有被删除图标的位置可以重用
    if (deletedIconPositionsRef.current.length > 0) {
      const reusedPosition = deletedIconPositionsRef.current.shift(); // 取出第一个被删除的位置
      const gridKey = `${reusedPosition.gridX},${reusedPosition.gridY}`;
      desktopGridRef.current.add(gridKey);
      console.log(`🎯 重用被删除图标的位置: (${reusedPosition.gridX},${reusedPosition.gridY})`);
      return reusedPosition;
    }
    
    // 如果没有可重用的位置，按原来的逻辑查找新位置
    // 获取画布区域的实际尺寸
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
  const saveTimeoutRef = useRef(null);
  const maxZIndexRef = useRef(100);

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
          return toMediaUrl(window, boardId);
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
      case 'document':
        if (hasMediaContent) {
          return '📄'; // 文档有内容时显示文档图标
        }
        return '📄';
      case 'chat':
        return '💬';
      default:
        return '🪟';
    }
  };


  // 获取展板窗口数据的函数 - 移动到useEffect之前避免临时死区问题
  const fetchBoardWindows = useCallback(async () => {
    try {
      console.log('🔄 fetchBoardWindows 开始加载展板窗口数据, boardId:', boardId);
      
      if (!boardId) {
        console.error('❌ boardId 为空，跳过加载');
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
        
        // 简化的窗口加载日志
        console.log(`✅ 成功加载 ${list.length} 个窗口:`);
        list.forEach((w, index) => {
          console.log(`  ${index + 1}. ${w.title} (${w.type}) - 位置: ${w.position?.x},${w.position?.y} 大小: ${w.size?.width}x${w.size?.height} ${w.hidden ? '[隐藏]' : ''}`);
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
        
        // 首先清空网格状态，准备重新分配
        desktopGridRef.current.clear();
        
        // 第一遍：添加所有已保存位置到网格占用状态
        list.forEach(window => {
          const savedPosition = iconPositionsMap[window.id];
          if (savedPosition && savedPosition.gridPosition) {
            const gridKey = `${savedPosition.gridPosition.gridX},${savedPosition.gridPosition.gridY}`;
            desktopGridRef.current.add(gridKey);
            console.log(`📍 恢复已保存位置: ${window.title} at (${savedPosition.gridPosition.gridX},${savedPosition.gridPosition.gridY})`);
          }
        });
        
        // 第二遍：为没有保存位置的窗口分配新位置
        const iconsWithPositions = list.map(window => {
          const savedPosition = iconPositionsMap[window.id];
          
          if (savedPosition && savedPosition.gridPosition) {
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
        
        // 确认网格占用状态
        console.log('📊 网格占用状态:', Array.from(desktopGridRef.current));
        
        // 设置桌面图标
        setDesktopIcons(iconsWithPositions);
        
        // 去重处理：确保没有重复的窗口ID
        const uniqueWindows = [];
        const seenIds = new Set();
        
        for (const window of list) {
          if (!seenIds.has(window.id)) {
            seenIds.add(window.id);
            uniqueWindows.push(window);
          } else {
            console.warn('⚠️ 发现重复的窗口ID，已跳过:', window.id, window.title);
          }
        }
        
        // 设置窗口数据，确保每个窗口都有必需的属性
        const validatedWindows = uniqueWindows.map(window => ({
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
        console.log('🔄 设置窗口状态，窗口数量:', validatedWindows.length);
        setWindowsWithTrace(validatedWindows);
        
        // 延迟验证状态是否正确设置（使用ref获取最新状态）
        setTimeout(() => {
          console.log('⏰ 延迟验证 - 当前windows状态长度:', windowsRef.current.length);
          console.log('⏰ 延迟验证 - 窗口列表:', windowsRef.current.map(w => w.title));
        }, 100);
        
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
      console.error('❌ fetchBoardWindows 获取窗口失败:', error);
      console.error('❌ 错误详情:', error.message);
      console.error('❌ 当前boardId:', boardId);
      // 确保在错误情况下也有基本的空状态
      console.log('❌ 由于fetchBoardWindows错误，重置windows状态为空');
      setWindowsWithTrace([]);
      setDesktopIcons([]);
    }
  }, [boardId, onBatchWindowHide]);

  useEffect(() => {
    if (boardId) {
      console.log('🔄 展板ID变化，开始加载新展板数据:', boardId);
      
      // 先加载新数据，再清理旧状态，避免出现空白期
      const loadNewBoardData = async () => {
        try {
          // 清理交互状态
          forceResetWindowStates();
          cleanupResizeListeners();
          cleanupDragListeners();
          
          // 清空隐藏状态
      if (onClearHiddenWindows) {
        onClearHiddenWindows();
      }
      
          // 重置编辑状态
          setEditingTitleId(null);
      setEditingTitleValue('');
      maxZIndexRef.current = 100;
      
          // 加载新展板数据
          console.log('🔄 开始加载新展板窗口数据');
          await fetchBoardWindows();
          
          console.log('✅ 展板切换完成');
        } catch (error) {
          console.error('❌ 展板切换失败:', error);
          // 发生错误时才清空状态
          console.log('❌ 由于展板切换错误，重置windows状态为空');
          setWindowsWithTrace([]);
          setDesktopIcons([]);
        }
      };
      
      loadNewBoardData();
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
      
      console.log('📡 BoardCanvas收到文件监控事件:', event.detail);
      console.log('⚠️ 文件监控事件可能影响窗口状态！当前窗口数:', windows.length);
      
      switch (type) {
        case 'reload_windows':
          // 重新加载窗口数据和桌面图标 - 使用完整的加载函数确保一致性
          console.log('🔄 文件监控触发：重新加载展板数据');
          console.log('⚠️ 文件监控导致的重新加载可能会重置窗口位置！');
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
    if (typeof window !== 'undefined') {
    window.addEventListener('fileWatcherUpdate', handleFileWatcherUpdate);
    }
    
    // 清理函数
    return () => {
      if (typeof window !== 'undefined') {
      window.removeEventListener('fileWatcherUpdate', handleFileWatcherUpdate);
      }
    };
  }, [boardId, fetchBoardWindows]);

  // 通知App组件窗口变化（过滤掉聊天窗口）
  useEffect(() => {
    const regularWindows = windows.filter(window => window.type !== 'chat');
    console.log('📢 通知App组件窗口变化，常规窗口数量:', regularWindows.length, '总窗口数量:', windows.length);
    if (onWindowsChange) {
      onWindowsChange(regularWindows);
    }
  }, [windows, onWindowsChange]);

  // 同步窗口数据到桌面图标 - 包括所有窗口（显示和隐藏的）
  useEffect(() => {
    // 如果窗口数量为0，清空桌面图标
    if (windows.length === 0) {
      setDesktopIcons([]);
      return;
    }
    
    // 检查是否需要同步（避免频繁触发）
    const windowIds = windows.map(w => w.id).sort().join(',');
    const currentIconIds = desktopIcons.map(i => i.windowId).sort().join(',');
    const hiddenWindowIds = hiddenWindows ? Array.from(hiddenWindows).sort().join(',') : '';
    
    // 如果窗口列表和隐藏状态都没有变化，则跳过
    if (windowIds === currentIconIds && 
        previousHiddenStateRef.current === hiddenWindowIds &&
        desktopIcons.length === windows.length) {
      console.log('🎯 窗口状态无变化，跳过桌面图标同步');
      return;
    }
    
    console.log('🎯 同步窗口数据到桌面图标');
    console.log('🎯 当前窗口数量:', windows.length);
    console.log('🎯 当前桌面图标数量:', desktopIcons.length);
    console.log('🎯 隐藏窗口数量:', hiddenWindows ? hiddenWindows.size : 0);
    
    // 过滤掉聊天窗口，聊天窗口不应该有桌面图标
    const regularWindows = windows.filter(window => window.type !== 'chat');
    
    // 先更新网格占用状态，基于现有图标
    updateGridOccupancy(desktopIcons);
    
    const icons = regularWindows.map(window => {
      // 查找是否已有该图标，保持位置和网格信息
      const existingIcon = desktopIcons.find(icon => icon.id === window.id);
      
      if (existingIcon) {
        console.log(`🎯 保持现有图标位置: ${window.title} (${window.id}) at (${existingIcon.gridPosition?.gridX},${existingIcon.gridPosition?.gridY})`);
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
          isHidden: hiddenWindows ? hiddenWindows.has(window.id) : false
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
          isHidden: hiddenWindows ? hiddenWindows.has(window.id) : false
        };
      }
    });
    
    console.log('🎯 生成的图标数据:', icons.map(i => ({ id: i.id, title: i.title, gridPos: i.gridPosition, isHidden: i.isHidden })));
    
    // 再次更新网格占用状态（包含新图标）
    updateGridOccupancy(icons);
    setDesktopIcons(icons);
    
    // 记录当前状态
    previousHiddenStateRef.current = hiddenWindowIds;
    
    console.log('🎯 桌面图标同步完成');
  }, [windows, hiddenWindows]);

  // 窗口焦点管理
  const handleWindowFocusLocal = async (windowId) => {
    console.log('窗口获得焦点:', windowId);
    
    // 如果有之前的焦点窗口，保存其状态
    if (focusedWindowId && focusedWindowId !== windowId) {
      console.log('保存失去焦点的窗口状态:', focusedWindowId);
      await saveWindowState(focusedWindowId, {});
    }
    
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
        console.log('🔄 开始重命名窗口:', {
          windowId: editingTitleId,
          oldTitle: windowObj.title,
          newTitle: newTitle,
          windowType: windowObj.type
        });
        
        const updatedWindow = { 
          ...windowObj, 
          title: newTitle
        };
        
        console.log('📤 发送重命名请求到后端...');
        const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${editingTitleId}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(updatedWindow),
        });

        console.log('📥 后端响应状态:', response.status);

        if (response.ok) {
          const result = await response.json();
          console.log('📥 后端响应数据:', result);
          
          // 更新本地状态
          setWindows(prevWindows => 
            prevWindows.map(w => 
              w.id === editingTitleId 
                ? { ...w, title: newTitle }
                : w
            )
          );
          
          // 更新桌面图标状态
          setDesktopIcons(prevIcons =>
            prevIcons.map(icon =>
              icon.id === editingTitleId
                ? { ...icon, title: newTitle }
                : icon
            )
          );
          
          console.log('✅ 窗口重命名成功:', newTitle);
          
          // 延迟刷新以确保文件系统操作完成
          setTimeout(() => {
            console.log('🔄 刷新窗口数据以同步文件系统变化');
            fetchBoardWindows();
          }, 1000);
          
        } else {
          const errorText = await response.text();
          console.error('❌ 更新标题失败:', response.status, errorText);
        }
      } else {
        console.log('⚠️ 窗口未找到或标题未变化:', {
          found: !!windowObj,
          oldTitle: windowObj?.title,
          newTitle: newTitle
        });
      }
    } catch (error) {
      console.error('❌ 重命名异常:', error);
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

      // 聊天窗口不需要保存到后端文件系统
      if (window.type === 'chat') {
        console.log('💬 聊天窗口状态不保存到后端，跳过保存');
        return true;
      }

      // 合并更新数据，确保包含所有必要字段
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
          return true;
        } else {
        const errorText = await response.text();
        console.error('❌ 窗口状态保存失败:', response.status, errorText);
          return false;
      }
    } catch (error) {
      console.error('❌ 保存窗口状态异常:', error);
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
    
    // 如果该窗口正在被拖拽或缩放，先停止这些操作
    if (isDragging && dragState.current.windowId === windowId) {
      console.log('⚠️ 窗口正在拖拽中，先停止拖拽');
      dragState.current.active = false;
      setIsDragging(false);
      cleanupDragListeners();
    }
    
    if (isResizing && resizeState.current.windowId === windowId) {
      console.log('⚠️ 窗口正在缩放中，先停止缩放');
      resizeState.current.active = false;
      setIsResizing(false);
      cleanupResizeListeners();
    }
    
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
        // 在删除前记录图标位置，供新图标重用
        const iconToDelete = desktopIcons.find(icon => icon.windowId === windowId);
        if (iconToDelete && iconToDelete.gridPosition) {
          deletedIconPositionsRef.current.push(iconToDelete.gridPosition);
          console.log(`🎯 记录被删除图标的位置: (${iconToDelete.gridPosition.gridX},${iconToDelete.gridPosition.gridY})`);
        }
        
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

  // 强制重置所有窗口交互状态（紧急修复函数）
  const forceResetWindowStates = () => {
    console.log('🔧 强制重置所有窗口交互状态');
    
    // 重置拖拽状态
    if (isDragging) {
      dragState.current.active = false;
      setIsDragging(false);
      cleanupDragListeners();
    }
    
    // 重置缩放状态
    if (isResizing) {
      resizeState.current.active = false;
      setIsResizing(false);
      cleanupResizeListeners();
    }
    
    // 重置样式
    document.body.style.cursor = '';
    document.body.style.userSelect = '';
    
    console.log('✅ 窗口交互状态重置完成');
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
          console.log('✅ 检测到窗口位置变化，准备保存');
          // 延迟保存，防抖机制
          if (saveTimeoutRef.current) {
            clearTimeout(saveTimeoutRef.current);
          }
          
          saveTimeoutRef.current = setTimeout(async () => {
            console.log('准备保存窗口位置:', {
              windowId: target.id,
              position: finalPosition,
            });
            
            // 使用统一的保存函数，确保包含所有状态
            console.log('🔄 开始保存窗口位置...');
            const saveResult = await saveWindowState(target.id, { position: finalPosition });
            console.log('💾 窗口位置保存结果:', saveResult ? '成功' : '失败');
            
            // 验证保存是否真正生效
            if (saveResult) {
              console.log('🔍 保存成功后验证 - 检查后端数据是否更新');
            }
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
          if (saveTimeoutRef.current) {
            clearTimeout(saveTimeoutRef.current);
          }
          
          saveTimeoutRef.current = setTimeout(async () => {
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

  // 页面离开前保存功能已移除
  // 原因：beforeunload 事件会在页面失去焦点时频繁触发，导致不必要的批量保存
  // 现有的事件驱动保存机制已经足够：
  // - 拖拽结束后立即保存位置
  // - 缩放结束后立即保存大小
  // - 窗口失去焦点时保存状态
  // - 文本内容变化时自动保存

  // 定期保存已禁用 - 使用事件驱动的保存机制更高效
  // 现有的保存机制：
  // 1. 拖拽结束后保存位置
  // 2. 缩放结束后保存大小  
  // 3. 窗口失去焦点时保存状态
  // 4. 页面离开前保存所有状态
  // 5. 文本内容变化时自动保存

  // 添加键盘快捷键监听（Ctrl+Shift+R 重置窗口状态，Ctrl+Shift+D 显示调试信息）
  useEffect(() => {
    const handleKeyDown = (e) => {
      // Ctrl+Shift+R 强制重置窗口状态
      if (e.ctrlKey && e.shiftKey && e.key === 'R') {
        e.preventDefault();
        console.log('🎹 检测到快捷键 Ctrl+Shift+R，强制重置窗口状态');
        forceResetWindowStates();
      }
      
      // Ctrl+Shift+S 强制同步所有窗口状态到后端
      if (e.ctrlKey && e.shiftKey && e.key === 'S') {
        e.preventDefault();
        console.log('🔄 强制同步所有窗口状态到后端...');
        
        windowsRef.current.forEach(async (window) => {
          const isHidden = hiddenWindows && hiddenWindows.has(window.id);
          console.log(`💾 强制保存窗口: ${window.title} (隐藏: ${isHidden})`);
          await saveWindowState(window.id, { hidden: isHidden });
        });
      }
      
      // Ctrl+Shift+D 显示调试信息
      if (e.ctrlKey && e.shiftKey && e.key === 'D') {
        e.preventDefault();
        console.log('🔍 当前窗口状态调试信息:');
        console.log(`📊 窗口总数 (state): ${windows.length}`);
        console.log(`📊 窗口总数 (ref): ${windowsRef.current.length}`);
        console.log(`📊 隐藏窗口数: ${hiddenWindows ? hiddenWindows.size : 0}`);
        console.log(`📊 桌面图标数: ${desktopIcons.length}`);
        
        const currentWindows = windowsRef.current.length > 0 ? windowsRef.current : windows;
        
        if (currentWindows.length === 0) {
          console.log('⚠️ 当前没有加载任何窗口');
        } else {
          currentWindows.forEach((window, index) => {
            const isHidden = hiddenWindows && hiddenWindows.has(window.id);
            console.log(`  窗口 ${index + 1}: ${window.title || '无标题'}`);
            console.log(`    ID: ${window.id}`);
            console.log(`    类型: ${window.type}`);
            console.log(`    位置: x:${window.position?.x || '未设置'}, y:${window.position?.y || '未设置'}`);
            console.log(`    大小: w:${window.size?.width || '未设置'}, h:${window.size?.height || '未设置'}`);
            console.log(`    隐藏: ${isHidden}`);
            console.log(`    完整对象:`, window);
          });
        }
        
        // 也显示桌面图标信息
        console.log('🎯 桌面图标信息:');
        desktopIcons.forEach((icon, index) => {
          console.log(`  图标 ${index + 1}: ${icon.title || '无标题'}`);
          console.log(`    ID: ${icon.id}`);
          console.log(`    窗口ID: ${icon.windowId}`);
          console.log(`    位置: x:${icon.position?.x}, y:${icon.position?.y}`);
          console.log(`    隐藏: ${icon.isHidden}`);
        });
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, []);

  // 监听聊天窗口切换事件
  useEffect(() => {
    const handleToggleChatWindow = () => {
      setWindows(prev => {
        const chatWindow = prev.find(w => w.id === CHAT_WINDOW_ID);
        
        if (chatWindow) {
          // 如果聊天窗口存在，检查是否被最小化
          if (minimizedWindows.has(CHAT_WINDOW_ID)) {
            // 如果被最小化，恢复显示
            handleWindowMinimizeLocal(CHAT_WINDOW_ID);
        } else {
            // 如果正在显示，最小化它
            handleWindowMinimizeLocal(CHAT_WINDOW_ID);
          }
          return prev; // 不修改 windows 数组
        } else {
          // 如果聊天窗口不存在，创建它
          const newChatWindow = createChatWindow();
          const newWindows = [...prev, newChatWindow];
          
          // 设置聊天窗口为焦点
          setTimeout(() => {
            handleWindowFocusLocal(CHAT_WINDOW_ID);
          }, 0);
          
          return newWindows;
        }
      });
    };

    if (typeof window !== 'undefined') {
    window.addEventListener('toggleChatWindow', handleToggleChatWindow);
    }
    return () => {
      if (typeof window !== 'undefined') {
      window.removeEventListener('toggleChatWindow', handleToggleChatWindow);
      }
    };
  }, [boardName, minimizedWindows]);

  // 监听打开PDF页面事件
  useEffect(() => {
    const handleOpenPDFPage = (event) => {
      const { windowId, page, filename } = event.detail || {};
      console.log('📖 收到打开PDF页面事件:', { windowId, page, filename });
      
      if (!windowId) return;
      
      // 查找对应的窗口
      const targetWindow = windows.find(w => w.id === windowId);
      
      if (!targetWindow) {
        console.warn('⚠️ 未找到窗口:', windowId);
        return;
      }
      
      console.log('✅ 找到目标窗口:', targetWindow.title);
      
      // 如果窗口被最小化，恢复它
      if (minimizedWindows && minimizedWindows.has(windowId)) {
        console.log('🔄 恢复最小化的窗口');
        handleWindowMinimizeLocal(windowId);
      }
      
      // 如果窗口被隐藏，显示它
      if (hiddenWindows && hiddenWindows.has(windowId)) {
        console.log('🔄 显示隐藏的窗口');
        if (onWindowShow) {
          onWindowShow(windowId);
        }
      }
      
      // 设置窗口为焦点
      setTimeout(() => {
        handleWindowFocusLocal(windowId);
      }, 100);
      
      // 触发PDF窗口打开分页模式并跳转到指定页面
      setTimeout(() => {
        const pdfPageEvent = new CustomEvent('openPDFPageInternal', {
          detail: { windowId, page }
        });
        if (typeof window !== 'undefined') {
          window.dispatchEvent(pdfPageEvent);
        }
      }, 200);
    };

    if (typeof window !== 'undefined') {
      window.addEventListener('openPDFPage', handleOpenPDFPage);
    }
    return () => {
      if (typeof window !== 'undefined') {
        window.removeEventListener('openPDFPage', handleOpenPDFPage);
      }
    };
  }, [windows, minimizedWindows, hiddenWindows, onWindowShow]);


  // 组件卸载时清理事件监听器
  useEffect(() => {
    return () => {
      cleanupResizeListeners();
      cleanupDragListeners();
      // 清理保存定时器
      if (saveTimeoutRef.current) {
        clearTimeout(saveTimeoutRef.current);
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
      {/* 移除顶部标题栏和新建窗口按钮 */}
      
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
                {/* Chat 窗口只显示关闭按钮，关闭时执行最小化 */}
                {window.type !== 'chat' && (
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
                )}
                <button 
                  className="close-btn"
                  onClick={(e) => {
                    console.log('点击了关闭按钮:', window.id);
                    e.stopPropagation();
                    e.preventDefault();
                    // Chat 窗口关闭时执行最小化，其他窗口执行真正的关闭
                    if (window.type === 'chat') {
                      handleWindowMinimizeLocal(window.id);
                    } else {
                    handleWindowCloseLocal(window.id);
                    }
                  }}
                  title={window.type === 'chat' ? "最小化" : "关闭窗口"}
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
              {window.type === 'chat' && (
                <ChatWindow
                  boardId={boardId}
                  boardName={boardName}
                  isVisible={true}
                  onFocus={() => {
                    handleWindowFocusLocal(window.id);
                  }}
                  isFocused={focusedWindowId === window.id}
                  onOpenWindow={(fileName) => {
                    // 根据文件名查找对应的窗口并打开
                    const targetWindow = windows.find(w => 
                      w.title === fileName || 
                      (w.file_path && w.file_path.includes(fileName))
                    );
                    if (targetWindow) {
                      handleIconDoubleClick(targetWindow.id);
                    }
                  }}
                  position={window.position}
                  onPositionChange={(newPosition) => {
                    // 位置变化通过现有的拖拽系统处理
                  }}
                />
              )}
              {window.type === 'image' && (
                <label className="image-placeholder" title={window.content || '点击上传图片'}>
                  {hasRealMediaContent(window) ? (
                    <img
                      src={toMediaUrl(window, boardId)}
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
                      src={toMediaUrl(window, boardId)}
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
                      src={toMediaUrl(window, boardId)}
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
                <PDFWindowRenderer 
                  window={window} 
                  onUpload={(files) => handleUpload(window.id, 'pdfs', files)}
                  boardId={boardId}
                />
              )}
              {window.type === 'document' && (
                <DocumentWindowRenderer 
                  window={window} 
                  onUpload={(files) => handleUpload(window.id, 'documents', files)}
                  boardId={boardId}
                />
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
