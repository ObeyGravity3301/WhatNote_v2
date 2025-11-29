/**
 * TTS (Text-to-Speech) 语音生成插件示例
 * 演示如何集成大型 AI 模型文件（如 gpt-sovit）
 * 
 * 模型文件存储方案：
 * 1. 本地存储：放在 public/models/ 目录（不会被 webpack 打包，运行时加载）
 * 2. 外部 CDN：从远程 URL 加载模型文件
 * 3. 后端服务：通过后端 API 提供模型服务（推荐）
 */

import React, { useState, useCallback, useRef } from 'react';

const TTSPlugin = {
  id: 'tts-plugin',
  name: '语音生成',
  type: 'toolbar-feature',
  targetWindowTypes: ['text'],
  version: '1.0.0',
  description: '使用 gpt-sovit 模型进行文本转语音',
  enabledByDefault: true,
  icon: '🔊',
  
  // 插件配置：模型文件路径
  modelConfig: {
    // 方案1: 本地模型文件（放在 public/models/ 目录）
    localModelPath: '/models/gpt-sovit/model.onnx',
    localConfigPath: '/models/gpt-sovit/config.json',
    
    // 方案2: 远程模型文件
    remoteModelUrl: 'https://your-cdn.com/models/gpt-sovit/model.onnx',
    
    // 方案3: 后端 API（推荐，避免前端加载大文件）
    apiEndpoint: 'http://localhost:8081/api/tts/generate',
    
    // 使用的方案
    useBackend: true, // 推荐使用后端 API
  },
  
  renderToolbarButton: (props) => {
    return function TTSButton() {
      const { content = '', windowId } = props;
      const [isGenerating, setIsGenerating] = useState(false);
      const [audioUrl, setAudioUrl] = useState(null);
      const audioRef = useRef(null);
      
      // 生成语音
      const handleGenerateSpeech = useCallback(async () => {
        if (!content.trim()) {
          alert('请先输入文本内容');
          return;
        }
        
        setIsGenerating(true);
        setAudioUrl(null);
        
        try {
          if (TTSPlugin.modelConfig.useBackend) {
            // 方案3: 使用后端 API（推荐）
            const response = await fetch(TTSPlugin.modelConfig.apiEndpoint, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({
                text: content,
                model: 'gpt-sovit',
                voice: 'default'
              })
            });
            
            if (!response.ok) {
              throw new Error(`后端服务错误: ${response.statusText}`);
            }
            
            const blob = await response.blob();
            const url = URL.createObjectURL(blob);
            setAudioUrl(url);
          } else {
            // 方案1/2: 前端加载模型（需要 onnxruntime-web）
            // 注意：这需要安装 onnxruntime-web 包
            // npm install onnxruntime-web
            
            // 这里只是示例，实际实现需要加载模型并推理
            console.warn('[TTS插件] 前端模型加载需要 onnxruntime-web，建议使用后端 API');
            alert('前端模型加载功能需要额外配置，建议使用后端 API 方案');
            setIsGenerating(false);
            return;
          }
        } catch (error) {
          console.error('[TTS插件] 生成语音失败:', error);
          alert(`生成语音失败: ${error.message}`);
        } finally {
          setIsGenerating(false);
        }
      }, [content]);
      
      // 清理音频 URL
      const handleCleanup = useCallback(() => {
        if (audioUrl) {
          URL.revokeObjectURL(audioUrl);
          setAudioUrl(null);
        }
      }, [audioUrl]);
      
      return (
        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
          <button
            onClick={handleGenerateSpeech}
            disabled={isGenerating || !content.trim()}
            style={{
              padding: '2px 8px',
              fontSize: '11px',
              fontFamily: 'MS Sans Serif, sans-serif',
              backgroundColor: isGenerating ? '#a0a0a0' : '#c0c0c0',
              border: '2px outset #c0c0c0',
              cursor: isGenerating ? 'wait' : 'pointer',
              minWidth: '60px',
              display: 'flex',
              alignItems: 'center',
              gap: '4px'
            }}
            onMouseDown={(e) => {
              if (!isGenerating) {
                e.currentTarget.style.border = '2px inset #c0c0c0';
                e.currentTarget.style.backgroundColor = '#a0a0a0';
              }
            }}
            onMouseUp={(e) => {
              if (!isGenerating) {
                e.currentTarget.style.border = '2px outset #c0c0c0';
                e.currentTarget.style.backgroundColor = '#c0c0c0';
              }
            }}
            onMouseLeave={(e) => {
              if (!isGenerating) {
                e.currentTarget.style.border = '2px outset #c0c0c0';
                e.currentTarget.style.backgroundColor = '#c0c0c0';
              }
            }}
          >
            <span>{isGenerating ? '生成中...' : '🔊 语音'}</span>
          </button>
          
          {audioUrl && (
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <audio
                ref={audioRef}
                src={audioUrl}
                controls
                style={{
                  height: '20px',
                  fontSize: '10px'
                }}
              />
              <button
                onClick={handleCleanup}
                style={{
                  padding: '1px 4px',
                  fontSize: '9px',
                  backgroundColor: '#c0c0c0',
                  border: '1px outset #c0c0c0',
                  cursor: 'pointer'
                }}
              >
                ✕
              </button>
            </div>
          )}
        </div>
      );
    };
  },
  
  // 生命周期钩子：启用时初始化
  onEnable: (context) => {
    console.log('[TTS插件] 已启用');
    // 可以在这里预加载模型（如果使用前端方案）
    // 或者检查后端服务是否可用
  },
  
  // 生命周期钩子：禁用时清理
  onDisable: (context) => {
    console.log('[TTS插件] 已禁用');
    // 清理资源
  }
};

export default TTSPlugin;

