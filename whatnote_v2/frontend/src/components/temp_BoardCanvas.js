function ImageWindowRenderer({ window: windowData, onUpload, boardId, addMessage, openMessageCenter }) {
  const hasContent = hasRealMediaContent(windowData);
  const imageUrl = hasContent ? toMediaUrl(windowData, boardId) : null;
  
  // 新增状态
  const [isExtracting, setIsExtracting] = useState(false);
  const [extractResult, setExtractResult] = useState(null);
  const [showResult, setShowResult] = useState(false);

  const triggerImageAction = async (action) => {
    const actionLabels = {
      'text-extract': '文字提取',
      'image-translate': '图片翻译'
    };

    if (!hasContent) {
      if (addMessage) {
        addMessage('请先上传图片', `${actionLabels[action]}需要有效的图片内容`, 'warning', windowData.id);
      }
      return;
    }

    if (action === 'text-extract') {
        setIsExtracting(true);
        try {
            if (addMessage) {
                addMessage('正在提取文字...', '请稍候，这可能需要几秒钟', 'info', windowData.id);
            }
            
            const response = await fetch(`http://localhost:8081/api/boards/${boardId}/windows/${windowData.id}/image/extract`, {
                method: 'POST'
            });
            
            if (!response.ok) {
                throw new Error(await response.text());
            }
            
            const data = await response.json();
            setExtractResult(data);
            setShowResult(true);
            
            if (addMessage) {
                addMessage('✅ 文字提取成功', '点击查看结果', 'success', windowData.id);
            }
            
            if (openMessageCenter) {
                openMessageCenter();
            }
        } catch (error) {
            console.error('提取失败:', error);
            if (addMessage) {
                addMessage('❌ 提取失败', error.message || '未知错误', 'error', windowData.id);
            }
        } finally {
            setIsExtracting(false);
        }
        return;
    }

    if (typeof window !== 'undefined') {
      const event = new CustomEvent('imageWindowAction', {
        detail: {
          windowId: windowData.id,
          action,
          imageUrl,
          boardId
        }
      });
      window.dispatchEvent(event);
    }

    if (addMessage) {
      addMessage(`已触发${actionLabels[action]}`, '请在AI助手或相关工具中查看执行状态', 'info', windowData.id);
    }

    if (openMessageCenter) {
      openMessageCenter();
    }
  };

  const toolbarButtonStyle = {
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
  };

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', position: 'relative' }}>
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
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <button
            style={{...toolbarButtonStyle, cursor: isExtracting ? 'wait' : 'pointer'}}
            onClick={() => !isExtracting && triggerImageAction('text-extract')}
            onMouseDown={(e) => { if(!isExtracting) { e.currentTarget.style.border = '2px inset #c0c0c0'; e.currentTarget.style.backgroundColor = '#a0a0a0'; } }}
            onMouseUp={(e) => { if(!isExtracting) { e.currentTarget.style.border = '2px outset #c0c0c0'; e.currentTarget.style.backgroundColor = '#c0c0c0'; } }}
            onMouseLeave={(e) => { if(!isExtracting) { e.currentTarget.style.border = '2px outset #c0c0c0'; e.currentTarget.style.backgroundColor = '#c0c0c0'; } }}
            disabled={isExtracting}
          >
            {isExtracting ? '提取中...' : '文字提取'}
          </button>
          <button
            style={toolbarButtonStyle}
            onClick={() => triggerImageAction('image-translate')}
            onMouseDown={(e) => { e.currentTarget.style.border = '2px inset #c0c0c0'; e.currentTarget.style.backgroundColor = '#a0a0a0'; }}
            onMouseUp={(e) => { e.currentTarget.style.border = '2px outset #c0c0c0'; e.currentTarget.style.backgroundColor = '#c0c0c0'; }}
            onMouseLeave={(e) => { e.currentTarget.style.border = '2px outset #c0c0c0'; e.currentTarget.style.backgroundColor = '#c0c0c0'; }}
          >
            图片翻译
          </button>
        </div>
      </div>
      <div style={{ flex: 1, display: 'flex', position: 'relative' }}>
        <label className="image-placeholder" title={windowData.content || '点击上传图片'} style={{ width: '100%', height: '100%' }}>
          {hasContent ? (
            <img
              src={imageUrl}
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
            onChange={(e) => {
              const files = e.target.files;
              if (onUpload) {
                onUpload(files);
              }
              e.target.value = '';
            }}
          />
        </label>

        {/* 提取结果覆盖层 */}
        {showResult && extractResult && (
            <div style={{
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                backgroundColor: 'rgba(255, 255, 255, 0.95)',
                display: 'flex',
                flexDirection: 'column',
                zIndex: 10,
                padding: '4px'
            }}>
                <div style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '4px',
                    borderBottom: '2px solid #808080',
                    marginBottom: '4px',
                    backgroundColor: '#c0c0c0'
                }}>
                    <span style={{ fontWeight: 'bold', fontSize: '11px', fontFamily: 'MS Sans Serif, sans-serif' }}>提取结果</span>
                    <button 
                        onClick={() => setShowResult(false)}
                        style={{
                            fontSize: '10px',
                            cursor: 'pointer',
                            border: '1px outset #ffffff',
                            padding: '0px 4px',
                            backgroundColor: '#c0c0c0'
                        }}
                    >
                        ×
                    </button>
                </div>
                
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px', overflow: 'hidden' }}>
                    {/* 文本内容 */}
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', border: '1px inset #ffffff', backgroundColor: '#ffffff' }}>
                        <div style={{ padding: '2px 4px', backgroundColor: '#e0e0e0', fontSize: '10px', fontWeight: 'bold' }}>
                            📝 文本内容
                        </div>
                        <div style={{ flex: 1, overflow: 'auto', padding: '4px', fontSize: '11px', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                            {extractResult.text_content || '(无文本内容)'}
                        </div>
                    </div>
                    
                    {/* 图片描述 */}
                    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', border: '1px inset #ffffff', backgroundColor: '#ffffff' }}>
                        <div style={{ padding: '2px 4px', backgroundColor: '#e0e0e0', fontSize: '10px', fontWeight: 'bold' }}>
                            🖼️ 图片描述
                        </div>
                        <div style={{ flex: 1, overflow: 'auto', padding: '4px', fontSize: '11px', fontFamily: 'monospace', whiteSpace: 'pre-wrap' }}>
                            {extractResult.image_content || '(无图片描述)'}
                        </div>
                    </div>
                </div>
                
                <div style={{ marginTop: '4px', fontSize: '10px', color: '#666', textAlign: 'center' }}>
                    已自动保存至: {extractResult.saved_path ? extractResult.saved_path.split('/').pop() : 'files/'}
                </div>
            </div>
        )}
      </div>
    </div>
  );
}












