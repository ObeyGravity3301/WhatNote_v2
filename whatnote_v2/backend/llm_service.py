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
    
    def __init__(self, api_config_manager, content_manager=None):
        self.api_config_manager = api_config_manager
        self.content_manager = content_manager
    
    def _extract_pdf_with_pypdf(self, file_path: str, file_info: Dict, content_array: List, pdf_reader=None) -> None:
        """使用PyPDF直接提取PDF文本（回退方案）"""
        try:
            if pdf_reader is None:
                pdf_reader = pypdf.PdfReader(file_path)
            
            text_content = ""
            
            # 提取所有页面的文本
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                page_text = page.extract_text()
                if page_text.strip():
                    text_content += f"--- 第 {page_num + 1} 页 ---\n{page_text}\n\n"
            
            if text_content.strip():
                # 清理文本格式
                text_content = text_content.replace('\n\n\n', '\n\n')
                text_content = text_content.replace('  ', ' ')
                
                # 限制文本长度
                max_chars = 50000
                original_length = len(text_content)
                if original_length > max_chars:
                    total_pages = len(pdf_reader.pages)
                    estimated_page = int((max_chars / original_length) * total_pages)
                    text_content = text_content[:max_chars] + f"\n\n... (内容已截断，完整文档共{total_pages}页，已发送约前{estimated_page}页)"
                    info(f"PDF文本过长，已截断: 原始{original_length}字符 -> {max_chars}字符")
                
                content_array.append({
                    'type': 'text',
                    'text': f"[PDF文件内容: {file_info.get('name', 'unknown')} - 共{len(pdf_reader.pages)}页]\n\n{text_content}"
                })
                info(f"PDF文本提取成功（PyPDF），总页数: {len(pdf_reader.pages)}, 文本长度: {len(text_content)} 字符")
            else:
                content_array.append({
                    'type': 'text',
                    'text': f"[PDF文件: {file_info.get('name', 'unknown')} - 无法提取文本内容]"
                })
        except Exception as e:
            info(f"PyPDF提取失败: {e}")
            content_array.append({
                'type': 'text',
                'text': f"[PDF文件: {file_info.get('name', 'unknown')} - 提取失败: {str(e)}]"
            })
    
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
        
        info(f"开始处理文件: {len(message['files'])} 个文件")
        
        processed_message = message.copy()
        
        # 为通义千问VL，直接将文件内容添加到content数组中
        content_array = []
        
        # 如果有原始文本内容，先添加文本
        if 'content' in message and message['content']:
            content_array.append({
                'type': 'text',
                'text': message['content']
            })
        
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
                    # 图片文件：直接添加到content数组中
                    info(f"处理图片文件: {file_info.get('name', 'unknown')} - MIME类型: {mime_type} - 大小: {len(file_data)} bytes")
                    
                    # 检查文件大小，如果太大则压缩或跳过
                    if len(file_data) > 20 * 1024 * 1024:  # 20MB限制
                        info(f"图片文件过大，跳过: {file_info.get('name', 'unknown')}")
                        content_array.append({
                            'type': 'text',
                            'text': f"[图片文件: {file_info.get('name', 'unknown')} - 文件过大，无法发送]"
                        })
                    else:
                        # 使用base64格式
                        base64_data = base64.b64encode(file_data).decode('utf-8')
                        info(f"Base64数据长度: {len(base64_data)} 字符")
                        
                        content_array.append({
                            'type': 'image_url',
                            'image_url': {
                                'url': f"data:{mime_type};base64,{base64_data}"
                            }
                        })
                        info(f"图片处理完成: {file_info.get('name', 'unknown')}")
                elif file_info.get('type') == 'pdfs':
                    # PDF文件：使用版本管理系统读取内容（新方法：基于PDF路径）
                    info(f"📄 [AI助手] 处理PDF文件: {file_info.get('name', 'unknown')}")
                    
                    # 尝试使用版本管理系统读取内容（不再需要board_id和window_id！）
                    if self.content_manager:
                        try:
                            info(f"📖 [AI助手] 使用版本管理系统读取PDF内容（基于路径）")
                            
                            # 获取PDF总页数
                            pdf_reader = pypdf.PdfReader(file_path)
                            total_pages = len(pdf_reader.pages)
                            
                            # 获取PDF文件名
                            pdf_file = Path(file_path)
                            pdf_name = pdf_file.stem
                            
                            # 构建pages目录
                            pages_dir = pdf_file.parent / "pages" / pdf_name
                            
                            text_content = ""
                            used_versions = []  # 记录使用的版本
                                
                            # 读取所有页面内容（使用新的版本管理方法）
                            for page_num in range(1, total_pages + 1):
                                # 获取该页使用的版本（新方法：直接从PDF路径）
                                version = self.content_manager.get_page_version_from_pdf(file_path, page_num)
                                used_versions.append(f"{page_num}:{version.upper()}")
                                
                                # 根据版本读取对应的文件
                                if version == 'llm':
                                    content_file = pages_dir / f"{pdf_name}_page_{page_num:03d}_llm.md"
                                else:
                                    content_file = pages_dir / f"{pdf_name}_page_{page_num:03d}.md"
                                
                                if content_file.exists():
                                    with open(content_file, 'r', encoding='utf-8') as f:
                                        page_content = f.read()
                                        text_content += f"--- 第 {page_num} 页 ---\n{page_content}\n\n"
                                        info(f"📄 [文件读取] 第{page_num}页 ({version.upper()}) → {content_file.name}")
                            
                            info(f"✅ [AI助手] 版本管理读取成功: {', '.join(used_versions)}")
                            
                            if text_content.strip():
                                # 清理文本格式
                                text_content = text_content.replace('\n\n\n', '\n\n')
                                text_content = text_content.replace('  ', ' ')
                                
                                # 限制文本长度
                                max_chars = 50000
                                original_length = len(text_content)
                                if original_length > max_chars:
                                    estimated_page = int((max_chars / original_length) * total_pages)
                                    text_content = text_content[:max_chars] + f"\n\n... (内容已截断，完整文档共{total_pages}页，已发送约前{estimated_page}页)"
                                    info(f"PDF文本过长，已截断: 原始{original_length}字符 -> {max_chars}字符")
                                
                                content_array.append({
                                    'type': 'text',
                                    'text': f"[PDF文件内容: {file_info.get('name', 'unknown')} - 共{total_pages}页]\n\n{text_content}"
                                })
                                info(f"✅ [AI助手] PDF内容发送成功，总页数: {total_pages}, 文本长度: {len(text_content)} 字符")
                            else:
                                # 回退：使用PyPDF直接提取
                                info(f"⚠️ [AI助手] 版本管理未找到内容，回退到PyPDF直接提取")
                                self._extract_pdf_with_pypdf(file_path, file_info, content_array, pdf_reader)
                        
                        except Exception as e:
                            info(f"❌ [AI助手] 版本管理读取失败: {e}，回退到PyPDF")
                            # 回退：使用PyPDF直接提取
                            try:
                                pdf_reader = pypdf.PdfReader(file_path)
                                self._extract_pdf_with_pypdf(file_path, file_info, content_array, pdf_reader)
                            except Exception as e2:
                                info(f"❌ [AI助手] PyPDF提取也失败: {e2}")
                                content_array.append({
                                    'type': 'text',
                                    'text': f"[PDF文件: {file_info.get('name', 'unknown')} - 处理失败: {str(e2)}]"
                                })
                    else:
                        # 没有content_manager，使用PyPDF直接提取
                        info(f"⚠️ [AI助手] 无content_manager，使用PyPDF直接提取")
                        try:
                            pdf_reader = pypdf.PdfReader(file_path)
                            self._extract_pdf_with_pypdf(file_path, file_info, content_array, pdf_reader)
                        except Exception as e:
                            info(f"❌ [AI助手] PDF处理失败: {e}")
                            content_array.append({
                                'type': 'text',
                                'text': f"[PDF文件: {file_info.get('name', 'unknown')} - 处理失败: {str(e)}]"
                            })
                elif file_info.get('type') == 'audios':
                    # 音频文件：转换为base64发送给LLM
                    if len(file_data) > 20 * 1024 * 1024:  # 20MB限制
                        content_array.append({
                            'type': 'text',
                            'text': f"[音频文件: {file_info.get('name', 'unknown')} - 文件过大，无法发送]"
                        })
                    else:
                        base64_data = base64.b64encode(file_data).decode('utf-8')
                        content_array.append({
                            'type': 'image_url',
                            'image_url': {
                                'url': f"data:{mime_type};base64,{base64_data}"
                            }
                        })
                elif file_info.get('type') == 'videos':
                    # 视频文件：转换为base64发送给LLM
                    if len(file_data) > 20 * 1024 * 1024:  # 20MB限制
                        content_array.append({
                            'type': 'text',
                            'text': f"[视频文件: {file_info.get('name', 'unknown')} - 文件过大，无法发送]"
                        })
                    else:
                        base64_data = base64.b64encode(file_data).decode('utf-8')
                        content_array.append({
                            'type': 'image_url',
                            'image_url': {
                                'url': f"data:{mime_type};base64,{base64_data}"
                            }
                        })
                else:
                    # 其他文件类型：尝试读取文本内容，如果失败则发送base64
                    try:
                        text_content = file_data.decode('utf-8')
                        # 限制文本长度，避免发送过长的内容
                        if len(text_content) > 5000:
                            text_content = text_content[:5000] + "\n... (内容已截断)"
                        
                        content_array.append({
                            'type': 'text',
                            'text': f"[文件内容: {file_info.get('name', 'unknown')}]\n{text_content}"
                        })
                    except UnicodeDecodeError:
                        # 尝试其他编码
                        try:
                            text_content = file_data.decode('gbk')
                            if len(text_content) > 5000:
                                text_content = text_content[:5000] + "\n... (内容已截断)"
                            content_array.append({
                                'type': 'text',
                                'text': f"[文件内容: {file_info.get('name', 'unknown')}]\n{text_content}"
                            })
                        except UnicodeDecodeError:
                            # 如果无法解码为文本，则发送base64给LLM
                            if len(file_data) > 20 * 1024 * 1024:  # 20MB限制
                                content_array.append({
                                    'type': 'text',
                                    'text': f"[二进制文件: {file_info.get('name', 'unknown')} - 文件过大，无法发送]"
                                })
                            else:
                                base64_data = base64.b64encode(file_data).decode('utf-8')
                                content_array.append({
                                    'type': 'image_url',
                                    'image_url': {
                                        'url': f"data:{mime_type};base64,{base64_data}"
                                    }
                                })
                
                info(f"处理文件成功: {file_info.get('name', 'unknown')}")
                
            except Exception as e:
                error(f"处理文件失败: {e}")
                content_array.append({
                    'type': 'text',
                    'text': f"[文件处理失败: {file_info.get('name', 'unknown')} - 错误: {str(e)[:100]}]"
                })
        
        # 将文件内容添加到消息中
        info(f"文件处理完成，content_array长度: {len(content_array)}")
        if content_array:
            # 直接设置content为数组格式
            processed_message['content'] = content_array
            
            # 记录文件处理统计
            info(f"成功处理 {len(content_array)} 个内容项，准备发送给多模态LLM")
            info(f"最终消息content类型: {type(processed_message.get('content'))}")
            if isinstance(processed_message.get('content'), list):
                info(f"最终消息content数组长度: {len(processed_message['content'])}")
                for i, item in enumerate(processed_message['content']):
                    info(f"  content[{i}]: type={item.get('type')}, 内容={str(item)[:100]}...")
        else:
            info("没有文件需要处理")
        
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
            info(f"=== 开始处理 {len(messages)} 条消息 ===")
            processed_messages = []
            for i, message in enumerate(messages):
                info(f"--- 处理消息 {i} ---")
                info(f"角色: {message.get('role')}")
                info(f"内容: {message.get('content', '')[:100]}...")
                
                # 调试信息：检查消息是否包含文件
                if 'files' in message and message['files']:
                    info(f"发现文件信息: {len(message['files'])} 个文件")
                    for file_info in message['files']:
                        info(f"文件: {file_info.get('name', 'unknown')} - 类型: {file_info.get('type', 'unknown')}")
                else:
                    info("消息中没有文件信息")
                
                processed_message = self._process_message_files(message)
                
                # 检查处理后的消息是否包含文件内容
                if isinstance(processed_message.get('content'), list):
                    has_file_content = any(item.get('type') in ['image_url', 'image'] for item in processed_message['content'])
                    if has_file_content:
                        info(f"处理后消息包含文件内容，content数组长度: {len(processed_message['content'])}")
                        for j, item in enumerate(processed_message['content']):
                            if item.get('type') == 'image_url':
                                info(f"  图片 {j}: {item['image_url']['url'][:50]}...")
                    else:
                        info("处理后消息不包含文件内容")
                else:
                    info("处理后消息content不是数组")
                
                processed_messages.append(processed_message)
            
            info(f"=== 处理完成，准备发送给 {current_provider} API ===")
            
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
            # 不设置超时，允许长文档处理
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
            # 不设置超时，允许长文档处理
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
            # 不设置超时，允许长文档处理
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
            # 不设置超时，允许长文档处理
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
    
    async def chat_with_tools(self, messages: List[Dict], max_iterations: int = 25) -> AsyncGenerator[Dict, None]:
        """
        支持工具调用的对话方法
        
        Args:
            messages: 对话消息列表
            max_iterations: 最大工具调用轮数，防止死循环
            
        Yields:
            Dict: 包含响应类型和内容的字典
                {
                    "type": "text" | "tool_call" | "tool_result" | "final",
                    "content": "...",
                    "tool_name": "...",  # type=tool_call时提供
                    "tool_result": {...}  # type=tool_result时提供
                }
        """
        try:
            # 创建 TodoTracker 实例（每个对话一个）
            from tools.todo_tools import TodoTracker, register_todo_tools
            from tools import tool_registry
            
            todo_tracker = TodoTracker()
            register_todo_tools(tool_registry, todo_tracker)
            
            # 获取API配置
            current_provider = self.api_config_manager.get_current_provider()
            provider_config = self.api_config_manager.get_current_config()
            
            if not provider_config or not provider_config.get('apiKey'):
                yield {
                    "type": "error",
                    "content": f"❌ 错误：{current_provider} API未配置"
                }
                return
            
            # 获取可用工具
            tools_definitions = tool_registry.get_all_tools()
            
            info(f"[LLM Tools] 开始工具调用对话，可用工具: {len(tools_definitions)} 个")
            
            # 处理消息中的文件
            processed_messages = []
            for msg in messages:
                processed_msg = self._process_message_files(msg)
                processed_messages.append(processed_msg)
            
            # 工具调用循环
            for iteration in range(max_iterations):
                info(f"[LLM Tools] 第 {iteration + 1} 轮对话")
                
                # 调用LLM（带工具定义）
                response_data = await self._call_llm_with_tools(
                    provider_config, 
                    current_provider,
                    processed_messages,  # 使用处理过的消息
                    tools_definitions
                )
                
                if not response_data:
                    yield {"type": "error", "content": "❌ LLM调用失败"}
                    return
                
                message = response_data['choices'][0]['message']
                finish_reason = response_data['choices'][0].get('finish_reason')
                
                # 检查是否有工具调用
                if finish_reason == 'tool_calls' and message.get('tool_calls'):
                    tool_calls = message['tool_calls']
                    info(f"[LLM Tools] 检测到 {len(tool_calls)} 个工具调用")
                    
                    # 按照您的要求：截断，只处理第一个工具调用
                    tool_call = tool_calls[0]
                    function_name = tool_call['function']['name']
                    function_args = json.loads(tool_call['function']['arguments'])
                    
                    yield {
                        "type": "tool_call",
                        "content": f"🔧 正在调用工具: {function_name}",
                        "tool_name": function_name,
                        "arguments": function_args
                    }
                    
                    # 执行工具
                    from tools import tool_executor
                    from tools.schemas import ToolCall
                    
                    tool_call_obj = ToolCall(
                        id=tool_call['id'],
                        type="function",
                        function={
                            "name": function_name,
                            "arguments": function_args
                        }
                    )
                    
                    result = await tool_executor.execute_tool_call(tool_call_obj, context={})
                    
                    yield {
                        "type": "tool_result",
                        "content": f"✅ 工具执行完成: {function_name}",
                        "tool_name": function_name,
                        "tool_result": result.data if result.status.value == "success" else {"error": result.error}
                    }
                    
                    # 将LLM的消息和工具结果添加到对话历史
                    processed_messages.append({
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [tool_call]
                    })
                    
                    processed_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call['id'],
                        "name": function_name,
                        "content": json.dumps(result.data if result.status.value == "success" else {"error": result.error}, ensure_ascii=False)
                    })
                    
                    # 继续下一轮
                    continue
                    
                else:
                    # 没有工具调用，检查是否有文本输出
                    content = message.get('content', '')
                    info(f"[LLM Tools] LLM 回复 (finish_reason={finish_reason}): {len(content)} 字符")
                    
                    if content:
                        # 有文本内容，流式输出
                        info(f"[LLM Tools] 输出文本")
                        
                        # 先发送一个标记，表示开始文本输出
                        yield {
                            "type": "text_start",
                            "content": ""
                        }
                        
                        # 流式输出内容（模拟打字效果）
                        chunk_size = 10  # 每次输出的字符数
                        for i in range(0, len(content), chunk_size):
                            chunk = content[i:i+chunk_size]
                            yield {
                                "type": "text_chunk",
                                "content": chunk
                            }
                            # 小延迟以确保流式效果
                            await asyncio.sleep(0.01)
                        
                        # 发送完成标记
                        yield {
                            "type": "text_complete",
                            "content": ""
                        }
                        
                        # 将文本添加到对话历史
                        processed_messages.append({
                            "role": "assistant",
                            "content": content
                        })
                    
                    # 🎯 关键：检查 todo 状态决定是否继续
                    if finish_reason == 'stop':
                        # LLM 主动停止
                        
                        if todo_tracker.has_todos():
                            # 有待办列表，检查是否全部完成
                            if todo_tracker.is_all_completed():
                                info(f"[LLM Tools] 所有待办项已完成，结束对话")
                                return
                            else:
                                # 还有未完成的待办项
                                remaining = todo_tracker.get_status()['remaining_count']
                                info(f"[LLM Tools] 还有 {remaining} 项待办未完成，继续下一轮")
                                
                                # 发送 todo 状态给前端
                                yield {
                                    "type": "todo_status",
                                    "content": todo_tracker.get_status()
                                }
                                
                                continue
                        else:
                            # 没有创建待办列表，按原逻辑结束
                            info(f"[LLM Tools] 无待办列表，LLM 停止，结束对话")
                            return
                    else:
                        # finish_reason 不是 'stop'，继续下一轮
                        info(f"[LLM Tools] finish_reason={finish_reason}，继续下一轮")
                        continue
            
            # 达到最大迭代次数
            yield {
                "type": "warning",
                "content": f"⚠️ 已达到最大工具调用次数 ({max_iterations})，停止执行"
            }
            
        except Exception as e:
            error(f"[LLM Tools] 工具调用失败: {e}")
            yield {
                "type": "error",
                "content": f"❌ 工具调用失败: {str(e)}"
            }
    
    async def _call_llm_with_tools(self, config: Dict, provider: str, messages: List[Dict], tools: List[Dict]) -> Optional[Dict]:
        """
        调用LLM API（带工具定义）
        
        Returns:
            Dict: API响应数据，或 None 如果失败
        """
        try:
            url = f"{config['baseUrl']}/chat/completions"
            headers = {
                'Authorization': f"Bearer {config['apiKey']}",
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': config['model'],
                'messages': messages,
                'stream': False,  # 工具调用不使用流式
                'temperature': 0.7
            }
            
            # 只在有工具时才添加 tools 参数（避免空数组错误）
            if tools and len(tools) > 0:
                payload['tools'] = tools
            
            info(f"[LLM Tools] 调用 {provider} API，工具数: {len(tools)}")
            info(f"[LLM Tools] Payload: {json.dumps({'model': payload['model'], 'tools_count': len(tools), 'messages_count': len(payload['messages'])}, ensure_ascii=False)}")
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        error(f"[LLM Tools] API错误 ({response.status}): {error_text}")
                        return None
                    
                    return await response.json()
                    
        except Exception as e:
            import traceback
            error(f"[LLM Tools] API调用异常: {e}")
            error(f"[LLM Tools] 详细错误: {traceback.format_exc()}")
            return None
