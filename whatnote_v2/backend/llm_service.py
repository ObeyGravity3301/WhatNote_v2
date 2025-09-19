"""
LLM API服务模块
支持多个服务商的API调用
"""

import aiohttp
import json
import asyncio
from typing import Dict, List, Optional, AsyncGenerator
from logger import info, error

class LLMService:
    """LLM API调用服务"""
    
    def __init__(self, api_config_manager):
        self.api_config_manager = api_config_manager
    
    async def chat_completion(self, messages: List[Dict], stream: bool = True) -> AsyncGenerator[str, None]:
        """
        调用LLM API进行对话补全
        
        Args:
            messages: 对话消息列表
            stream: 是否使用流式响应
            
        Yields:
            str: 流式响应的文本片段
        """
        try:
            # 获取当前API配置
            current_provider = self.api_config_manager.get_current_provider()
            provider_config = self.api_config_manager.get_current_config()
            
            if not provider_config or not provider_config.get('apiKey'):
                yield f"❌ 错误：{current_provider} API未配置或密钥为空"
                return
            
            info(f"使用 {current_provider} API 进行对话")
            
            # 根据服务商调用对应的API
            if current_provider == 'openai':
                async for chunk in self._call_openai_api(provider_config, messages, stream):
                    yield chunk
            elif current_provider == 'anthropic':
                async for chunk in self._call_anthropic_api(provider_config, messages, stream):
                    yield chunk
            elif current_provider == 'gemini':
                async for chunk in self._call_gemini_api(provider_config, messages, stream):
                    yield chunk
            elif current_provider == 'qwen':
                async for chunk in self._call_qwen_api(provider_config, messages, stream):
                    yield chunk
            else:
                yield f"❌ 错误：不支持的服务商 {current_provider}"
                
        except Exception as e:
            error(f"LLM API调用失败: {e}")
            yield f"❌ API调用失败: {str(e)}"
    
    async def _call_openai_api(self, config: Dict, messages: List[Dict], stream: bool) -> AsyncGenerator[str, None]:
        """调用OpenAI API"""
        url = f"{config['baseUrl']}/chat/completions"
        headers = {
            'Authorization': f"Bearer {config['apiKey']}",
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': config['model'],
            'messages': messages,
            'stream': stream,
            'temperature': 0.7
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        yield f"❌ OpenAI API错误 ({response.status}): {error_text}"
                        return
                    
                    if stream:
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data: '):
                                data = line[6:]  # 移除 'data: ' 前缀
                                if data == '[DONE]':
                                    break
                                try:
                                    chunk_data = json.loads(data)
                                    if 'choices' in chunk_data and chunk_data['choices']:
                                        delta = chunk_data['choices'][0].get('delta', {})
                                        content = delta.get('content', '')
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    continue
                    else:
                        response_data = await response.json()
                        if 'choices' in response_data and response_data['choices']:
                            content = response_data['choices'][0]['message']['content']
                            yield content
                            
        except Exception as e:
            yield f"❌ OpenAI API调用异常: {str(e)}"
    
    async def _call_anthropic_api(self, config: Dict, messages: List[Dict], stream: bool) -> AsyncGenerator[str, None]:
        """调用Anthropic API"""
        url = f"{config['baseUrl']}/v1/messages"
        headers = {
            'x-api-key': config['apiKey'],
            'Content-Type': 'application/json',
            'anthropic-version': '2023-06-01'
        }
        
        # 转换消息格式（Anthropic格式稍有不同）
        anthropic_messages = []
        for msg in messages:
            if msg['role'] == 'system':
                continue  # Claude 3.5的system消息需要特殊处理
            anthropic_messages.append({
                'role': msg['role'],
                'content': msg['content']
            })
        
        payload = {
            'model': config['model'],
            'messages': anthropic_messages,
            'max_tokens': 4000,
            'stream': stream
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        yield f"❌ Anthropic API错误 ({response.status}): {error_text}"
                        return
                    
                    if stream:
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data: '):
                                data = line[6:]
                                if data == '[DONE]':
                                    break
                                try:
                                    chunk_data = json.loads(data)
                                    if chunk_data.get('type') == 'content_block_delta':
                                        content = chunk_data.get('delta', {}).get('text', '')
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    continue
                    else:
                        response_data = await response.json()
                        if 'content' in response_data and response_data['content']:
                            content = response_data['content'][0]['text']
                            yield content
                            
        except Exception as e:
            yield f"❌ Anthropic API调用异常: {str(e)}"
    
    async def _call_gemini_api(self, config: Dict, messages: List[Dict], stream: bool) -> AsyncGenerator[str, None]:
        """调用Gemini API"""
        url = f"{config['baseUrl']}/models/{config['model']}:generateContent"
        if stream:
            url += "?alt=sse"
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        # 转换消息格式为Gemini格式
        contents = []
        for msg in messages:
            if msg['role'] == 'system':
                continue  # Gemini的system消息需要特殊处理
            role = 'user' if msg['role'] == 'user' else 'model'
            contents.append({
                'role': role,
                'parts': [{'text': msg['content']}]
            })
        
        payload = {
            'contents': contents,
            'generationConfig': {
                'temperature': 0.7,
                'maxOutputTokens': 4000
            }
        }
        
        # 添加API密钥到URL
        url += f"&key={config['apiKey']}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        yield f"❌ Gemini API错误 ({response.status}): {error_text}"
                        return
                    
                    if stream:
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data: '):
                                data = line[6:]
                                try:
                                    chunk_data = json.loads(data)
                                    if 'candidates' in chunk_data:
                                        for candidate in chunk_data['candidates']:
                                            if 'content' in candidate and 'parts' in candidate['content']:
                                                for part in candidate['content']['parts']:
                                                    if 'text' in part:
                                                        yield part['text']
                                except json.JSONDecodeError:
                                    continue
                    else:
                        response_data = await response.json()
                        if 'candidates' in response_data:
                            for candidate in response_data['candidates']:
                                if 'content' in candidate and 'parts' in candidate['content']:
                                    for part in candidate['content']['parts']:
                                        if 'text' in part:
                                            yield part['text']
                            
        except Exception as e:
            yield f"❌ Gemini API调用异常: {str(e)}"
    
    async def _call_qwen_api(self, config: Dict, messages: List[Dict], stream: bool) -> AsyncGenerator[str, None]:
        """调用通义千问API（OpenAI兼容模式）"""
        url = f"{config['baseUrl']}/chat/completions"
        headers = {
            'Authorization': f"Bearer {config['apiKey']}",
            'Content-Type': 'application/json'
        }
        
        payload = {
            'model': config['model'],
            'messages': messages,
            'stream': stream,
            'temperature': 0.7,
            'max_tokens': 4000
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        yield f"❌ 通义千问API错误 ({response.status}): {error_text}"
                        return
                    
                    if stream:
                        async for line in response.content:
                            line = line.decode('utf-8').strip()
                            if line.startswith('data: '):
                                data = line[6:]  # 移除 'data: ' 前缀
                                if data == '[DONE]':
                                    break
                                try:
                                    chunk_data = json.loads(data)
                                    if 'choices' in chunk_data and chunk_data['choices']:
                                        delta = chunk_data['choices'][0].get('delta', {})
                                        content = delta.get('content', '')
                                        if content:
                                            yield content
                                except json.JSONDecodeError:
                                    continue
                    else:
                        response_data = await response.json()
                        if 'choices' in response_data and response_data['choices']:
                            content = response_data['choices'][0]['message']['content']
                            yield content
                            
        except Exception as e:
            yield f"❌ 通义千问API调用异常: {str(e)}"
