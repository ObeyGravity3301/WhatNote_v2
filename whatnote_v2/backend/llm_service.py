"""
LLM API服务模块
支持多个服务商的API调用
"""

import aiohttp
import json
import asyncio
import base64
import mimetypes
from pathlib import Path
from typing import Dict, List, Optional, AsyncGenerator
from logger import info, error
import pypdf

class LLMService:
    """LLM API调用服务"""
    
    def __init__(self, api_config_manager):
        self.api_config_manager = api_config_manager
    
    def _process_message_files(self, message: Dict) -> Dict:
        """
        处理消息中的文件，将文件内容转换为LLM可理解的格式
        
        Args:
            message: 包含files字段的消息
            
        Returns:
            Dict: 处理后的消息，包含文件内容
        """
        if 'files' not in message or not message['files']:
            info("消息中没有文件信息，直接返回原消息")
            return message
        
        info(f"原始消息格式: role={message.get('role')}, content类型={type(message.get('content'))}, files数量={len(message.get('files', []))}")
        
        info(f"开始处理文件: {len(message['files'])} 个文件")
        
        processed_message = message.copy()
        file_contents = []
        
        for file_info in message['files']:
            try:
                file_path = Path(file_info.get('path', ''))
                info(f"处理文件: {file_info.get('name', 'unknown')} - 路径: {file_path} - 类型: {file_info.get('type', 'unknown')}")
                
                if not file_path.exists():
                    info(f"文件不存在: {file_path}")
                    continue
                
                # 读取文件内容
                with open(file_path, 'rb') as f:
                    file_data = f.read()
                
                # 获取MIME类型
                mime_type, _ = mimetypes.guess_type(str(file_path))
                if not mime_type:
                    mime_type = 'application/octet-stream'
                
                # 根据文件类型处理 - 直接发送文件本身给多模态LLM
                info(f"文件类型判断: {file_info.get('type')} - 文件大小: {len(file_data)} bytes")
                
                if file_info.get('type') == 'images':
                    # 图片文件：转换为base64发送给LLM
                    info(f"处理图片文件: {file_info.get('name', 'unknown')} - MIME类型: {mime_type} - 大小: {len(file_data)} bytes")
                    
                    # 检查文件大小，如果太大则压缩或跳过
                    if len(file_data) > 20 * 1024 * 1024:  # 20MB限制
                        info(f"图片文件过大，跳过: {file_info.get('name', 'unknown')}")
                        file_contents.append({
                            'type': 'text',
                            'text': f"[图片文件: {file_info.get('name', 'unknown')} - 文件过大，无法发送]"
                        })
                    else:
                        base64_data = base64.b64encode(file_data).decode('utf-8')
                        info(f"图片base64编码成功，长度: {len(base64_data)} 字符")
                        
                        # 详细调试信息：验证数据真实性
                        info(f"原始文件数据前20字节: {file_data[:20].hex()}")
                        info(f"Base64前50字符: {base64_data[:50]}")
                        info(f"Base64后50字符: {base64_data[-50:]}")
                        
                        # 验证base64解码
                        try:
                            decoded_data = base64.b64decode(base64_data)
                            info(f"Base64解码验证: 原始长度={len(file_data)}, 解码长度={len(decoded_data)}, 匹配={decoded_data == file_data}")
                        except Exception as e:
                            info(f"Base64解码验证失败: {e}")
                        
                        # 通义千问支持的图片格式
                        file_contents.append({
                            'type': 'image_url',
                            'image_url': {
                                'url': f"data:{mime_type};base64,{base64_data}"
                            }
                        })
                        info(f"通义千问图片格式: type=image_url, url=data:{mime_type};base64,{base64_data[:50]}...")
                        info(f"图片处理完成: {file_info.get('name', 'unknown')}")
                elif file_info.get('type') == 'pdfs':
                    # PDF文件：提取文本内容发送给LLM
                    info(f"处理PDF文件: {file_info.get('name', 'unknown')} - 大小: {len(file_data)} bytes")
                    
                    try:
                        with open(file_path, 'rb') as pdf_file:
                            pdf_reader = pypdf.PdfReader(pdf_file)
                            text_content = ""
                            
                            # 提取所有页面的文本，并添加页面分隔符
                            for page_num in range(len(pdf_reader.pages)):
                                page = pdf_reader.pages[page_num]
                                page_text = page.extract_text()
                                if page_text.strip():
                                    text_content += f"--- 第 {page_num + 1} 页 ---\n{page_text}\n\n"
                            
                            if text_content.strip():
                                # 清理文本格式
                                text_content = text_content.replace('\n\n\n', '\n\n')  # 移除多余空行
                                text_content = text_content.replace('  ', ' ')  # 移除多余空格
                                
                                # 限制文本长度，避免发送过长的内容
                                if len(text_content) > 8000:
                                    text_content = text_content[:8000] + "\n\n... (内容已截断，共提取前8000字符)"
                                
                                file_contents.append({
                                    'type': 'text',
                                    'text': f"[PDF文件内容: {file_info.get('name', 'unknown')}]\n\n{text_content}"
                                })
                                info(f"PDF文本提取成功，长度: {len(text_content)} 字符")
                            else:
                                file_contents.append({
                                    'type': 'text',
                                    'text': f"[PDF文件: {file_info.get('name', 'unknown')} - 无法提取文本内容，可能是扫描版PDF]"
                                })
                    except Exception as e:
                        info(f"PDF处理失败: {e}")
                        file_contents.append({
                            'type': 'text',
                            'text': f"[PDF文件: {file_info.get('name', 'unknown')} - 处理失败: {str(e)}]"
                        })
                elif file_info.get('type') == 'audios':
                    # 音频文件：发送文件信息
                    file_contents.append({
                        'type': 'text',
                        'text': f"[音频文件: {file_info.get('name', 'unknown')} - 大小: {(len(file_data)/1024):.1f}KB]"
                    })
                elif file_info.get('type') == 'videos':
                    # 视频文件：发送文件信息
                    file_contents.append({
                        'type': 'text',
                        'text': f"[视频文件: {file_info.get('name', 'unknown')} - 大小: {(len(file_data)/1024):.1f}KB]"
                    })
                else:
                    # 其他文件类型：尝试读取文本内容
                    try:
                        text_content = file_data.decode('utf-8')
                        # 清理文本格式
                        text_content = text_content.replace('\r\n', '\n').replace('\r', '\n')  # 统一换行符
                        text_content = text_content.replace('\n\n\n', '\n\n')  # 移除多余空行
                        
                        # 限制文本长度，避免发送过长的内容
                        if len(text_content) > 6000:
                            text_content = text_content[:6000] + "\n\n... (内容已截断，共提取前6000字符)"
                        
                        file_contents.append({
                            'type': 'text',
                            'text': f"[文件内容: {file_info.get('name', 'unknown')}]\n\n{text_content}"
                        })
                        info(f"文本文件提取成功，长度: {len(text_content)} 字符")
                    except UnicodeDecodeError:
                        # 尝试其他编码
                        try:
                            text_content = file_data.decode('gbk')
                            # 清理文本格式
                            text_content = text_content.replace('\r\n', '\n').replace('\r', '\n')
                            text_content = text_content.replace('\n\n\n', '\n\n')
                            
                            if len(text_content) > 6000:
                                text_content = text_content[:6000] + "\n\n... (内容已截断，共提取前6000字符)"
                            
                            file_contents.append({
                                'type': 'text',
                                'text': f"[文件内容: {file_info.get('name', 'unknown')}]\n\n{text_content}"
                            })
                            info(f"文本文件提取成功(GBK编码)，长度: {len(text_content)} 字符")
                        except UnicodeDecodeError:
                            # 如果无法解码为文本，则发送文件信息
                            file_contents.append({
                                'type': 'text',
                                'text': f"[二进制文件: {file_info.get('name', 'unknown')} - 大小: {(len(file_data)/1024):.1f}KB - 无法提取文本内容]"
                            })
                
                info(f"处理文件成功: {file_info.get('name', 'unknown')}")
                
            except Exception as e:
                error(f"处理文件失败: {e}")
                file_contents.append({
                    'type': 'text',
                    'text': f"[文件处理失败: {file_info.get('name', 'unknown')} - 错误: {str(e)[:100]}]"
                })
        
        # 将文件内容添加到消息中
        if file_contents:
            # 对于支持多模态的API，将文件内容添加到消息中
            if 'content' in processed_message:
                # 如果原消息有文本内容，保留文本内容
                processed_message['content'] = [
                    {'type': 'text', 'text': processed_message['content']}
                ] + file_contents
            else:
                processed_message['content'] = file_contents
            
            # 记录文件处理统计
            info(f"成功处理 {len(file_contents)} 个文件，准备发送给多模态LLM")
            info(f"文件内容预览: {[f['type'] + ':' + f.get('text', f.get('image_url', {}).get('url', ''))[:100] + '...' for f in file_contents]}")
            
            # 详细记录每个文件的内容
            for i, file_content in enumerate(file_contents):
                if file_content['type'] == 'text':
                    info(f"文件内容 {i+1}: {file_content['text'][:200]}...")
                elif file_content['type'] == 'image_url':
                    info(f"图片内容 {i+1}: {file_content['image_url']['url'][:100]}...")
        else:
            info("没有文件需要处理")
        
        # 最终调试信息
        info(f"处理后消息格式: role={processed_message.get('role')}, content类型={type(processed_message.get('content'))}")
        if isinstance(processed_message.get('content'), list):
            info(f"content数组长度: {len(processed_message['content'])}")
            for i, item in enumerate(processed_message['content']):
                info(f"  content[{i}]: type={item.get('type')}, 内容={str(item)[:150]}...")
        
        return processed_message
    
    async def chat_completion(self, messages: List[Dict], stream: bool = True) -> AsyncGenerator[str, None]:
        """
        调用LLM API进行对话补全
        
        Args:
            messages: 对话消息列表，支持多模态内容（文本+文件）
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
            
            # 处理消息中的文件内容
            processed_messages = []
            for message in messages:
                # 调试信息：检查消息是否包含文件
                if 'files' in message and message['files']:
                    info(f"发现文件信息: {len(message['files'])} 个文件")
                    for file_info in message['files']:
                        info(f"文件: {file_info.get('name', 'unknown')} - 类型: {file_info.get('type', 'unknown')}")
                else:
                    info("消息中没有文件信息")
                
                processed_message = self._process_message_files(message)
                processed_messages.append(processed_message)
            
            # 根据服务商调用对应的API
            if current_provider == 'openai':
                async for chunk in self._call_openai_api(provider_config, processed_messages, stream):
                    yield chunk
            elif current_provider == 'anthropic':
                async for chunk in self._call_anthropic_api(provider_config, processed_messages, stream):
                    yield chunk
            elif current_provider == 'gemini':
                async for chunk in self._call_gemini_api(provider_config, processed_messages, stream):
                    yield chunk
            elif current_provider == 'qwen':
                async for chunk in self._call_qwen_api(provider_config, processed_messages, stream):
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
            
            # 处理多模态内容
            parts = []
            if isinstance(msg.get('content'), list):
                # 多模态内容（包含文件和文本）
                for content_item in msg['content']:
                    if content_item.get('type') == 'text':
                        parts.append({'text': content_item['text']})
                    elif content_item.get('type') == 'image_url':
                        # 处理图片
                        parts.append({
                            'inline_data': {
                                'mime_type': content_item['image_url']['url'].split(';')[0].split(':')[1],
                                'data': content_item['image_url']['url'].split(',')[1]
                            }
                        })
            else:
                # 纯文本内容
                parts.append({'text': msg['content']})
            
            contents.append({
                'role': role,
                'parts': parts
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
        
        # 调试：记录发送给通义千问的消息格式
        info(f"发送给通义千问的消息数量: {len(messages)}")
        for i, msg in enumerate(messages):
            if 'content' in msg and isinstance(msg['content'], list):
                info(f"消息 {i} 内容项数量: {len(msg['content'])}")
                for j, content in enumerate(msg['content']):
                    if content.get('type') == 'image_url':
                        info(f"  图片内容 {j}: {content['image_url']['url'][:100]}...")
                    elif content.get('type') == 'text':
                        info(f"  文本内容 {j}: {content['text'][:100]}...")
        
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
