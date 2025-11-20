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
from config import DATA_DIR
from services.todo_state_manager import TodoStateManager
from tools import tool_registry
from tools.todo_tools import TodoTracker, register_todo_tools

class LLMService:
    """LLM API调用服务"""
    
    def __init__(self, api_config_manager, content_manager=None, conversation_manager=None, todo_state_manager: Optional[TodoStateManager] = None):
        self.api_config_manager = api_config_manager
        self.content_manager = content_manager
        self.conversation_manager = conversation_manager
        self.todo_state_manager = todo_state_manager or TodoStateManager(DATA_DIR, conversation_manager)
        
        # 确保待办工具已注册（绑定共享状态管理器）
        register_todo_tools(tool_registry, state_manager=self.todo_state_manager)
    
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
                        
                        content_array.append({
                            'type': 'text',
                            'text': f"[文件内容: {file_info.get('name', 'unknown')}]\n{text_content}"
                        })
                    except UnicodeDecodeError:
                        # 尝试其他编码
                        try:
                            text_content = file_data.decode('gbk')
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
    
    async def chat_completion(self, messages: List[Dict], stream: bool = True, override_model: str = None) -> AsyncGenerator[str, None]:
        """
        调用LLM API进行对话补全
        
        Args:
            messages: 对话消息列表，支持多模态内容（文本+文件）
            stream: 是否使用流式响应
            override_model: 临时覆盖使用的模型（用于视觉任务等特殊场景）
            
        Yields:
            str: 流式响应的文本片段
        """
        try:
            # 获取当前API配置
            current_provider = self.api_config_manager.get_current_provider()
            provider_config = self.api_config_manager.get_current_config().copy()  # 复制避免修改原配置
            
            # 如果指定了 override_model，临时覆盖
            if override_model:
                info(f"[LLM] 临时使用模型: {override_model} (原模型: {provider_config.get('model')})")
                provider_config['model'] = override_model
            
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
    
    async def chat_with_tools(
        self,
        messages: List[Dict],
        max_iterations: int = 25,
        board_id: Optional[str] = None,
        conversation_id: Optional[str] = None
    ) -> AsyncGenerator[Dict, None]:
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
            # 创建/获取 TodoTracker 实例（每个会话一个）
            if board_id and conversation_id and self.todo_state_manager:
                todo_tracker = self.todo_state_manager.get_tracker(board_id, conversation_id)
            else:
                todo_tracker = TodoTracker()

            def log_todo_status(stage: str):
                if todo_tracker.has_todos():
                    status = todo_tracker.get_status()
                    remaining_titles = [
                        item.get('task')
                        for item in status.get('items', [])
                        if not item.get('completed')
                    ]
                    info(
                        f"[LLM Tools][Todo] {stage}: {status['completed_count']}/{status['total']} 完成，剩余 {status['remaining_count']} 项 -> {remaining_titles}"
                    )
                else:
                    info(f"[LLM Tools][Todo] {stage}: 当前无待办列表")

            def persist_todo_state(reason: str = "状态更新"):
                if board_id and conversation_id and self.todo_state_manager:
                    self.todo_state_manager.save_tracker(board_id, conversation_id, todo_tracker, reason)
                    log_todo_status(f"{reason}（已持久化）")
                else:
                    log_todo_status(f"{reason}（未持久化，缺少对话信息）")

            # 如果已有状态，首次进入时同步给前端
            if board_id and conversation_id and self.todo_state_manager:
                initial_status = todo_tracker.get_status()
                if initial_status and initial_status.get("has_todos"):
                    log_todo_status("载入持久化状态后")
                    yield {
                        "type": "todo_status",
                        "content": initial_status
                    }
                persist_todo_state("请求开始时同步")
            
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
                
                # ⭐ 真正的流式处理：边接收边判断类型
                accumulated_message = {
                    'role': 'assistant',
                    'content': '',
                    'tool_calls': []
                }
                finish_reason = None
                tool_calls_buffer = {}
                text_buffer = ""
                is_outputting_text = False  # 标记是否正在输出文本
                
                # 调用LLM（流式）
                url = f"{provider_config['baseUrl']}/chat/completions"
                headers = {
                    'Authorization': f"Bearer {provider_config['apiKey']}",
                    'Content-Type': 'application/json'
                }
                
                payload = {
                    'model': provider_config['model'],
                    'messages': processed_messages,
                    'stream': True,
                    'temperature': 0.7
                }
                
                if tools_definitions and len(tools_definitions) > 0:
                    payload['tools'] = tools_definitions
                
                info(f"[LLM Tools] 开始流式接收 LLM 响应...")
                
                import aiohttp
                # ⭐ 设置超时（总共120秒，读取超时60秒）
                timeout = aiohttp.ClientTimeout(total=120, sock_read=60)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, headers=headers, json=payload) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            yield {"type": "error", "content": f"❌ API错误: {error_text}"}
                            return
                        
                        chunk_count = 0
                        async for line in response.content:
                            line_str = line.decode('utf-8').strip()
                            if not line_str or not line_str.startswith('data: '):
                                continue
                            
                            data = line_str[6:]
                            if data == '[DONE]':
                                info(f"[LLM Tools] 流式接收完成，共 {chunk_count} 个chunk")
                                break
                            
                            chunk_count += 1
                            if chunk_count % 10 == 0:
                                info(f"[LLM Tools] 已接收 {chunk_count} 个chunk")
                            
                            try:
                                chunk = json.loads(data)
                                if 'choices' not in chunk or not chunk['choices']:
                                    continue
                                
                                choice = chunk['choices'][0]
                                delta = choice.get('delta', {})
                                chunk_finish_reason = choice.get('finish_reason')
                                
                                # 🔍 检测内容类型并处理
                                if 'content' in delta and delta['content']:
                                    # 📝 文本内容 → 立即流式输出
                                    content_chunk = delta['content']
                                    accumulated_message['content'] += content_chunk
                                    
                                    if not is_outputting_text:
                                        # 第一次输出文本
                                        is_outputting_text = True
                                        info(f"[LLM Tools] 开始流式输出文本")
                                        yield {"type": "text_start", "content": ""}
                                    
                                    # 立即发送文本块（真正的流式）
                                    yield {"type": "text_chunk", "content": content_chunk}
                                
                                elif 'tool_calls' in delta:
                                    # 🔧 工具调用 → 累积到 buffer
                                    for tool_call_delta in delta['tool_calls']:
                                        idx = tool_call_delta.get('index', 0)
                                        
                                        if idx not in tool_calls_buffer:
                                            tool_calls_buffer[idx] = {
                                                'id': '',
                                                'type': 'function',
                                                'function': {'name': '', 'arguments': ''}
                                            }
                                        
                                        if 'id' in tool_call_delta:
                                            tool_calls_buffer[idx]['id'] = tool_call_delta['id']
                                        
                                        if 'function' in tool_call_delta:
                                            func = tool_call_delta['function']
                                            if 'name' in func and func['name']:
                                                tool_calls_buffer[idx]['function']['name'] += func['name']
                                            if 'arguments' in func and func['arguments']:
                                                tool_calls_buffer[idx]['function']['arguments'] += func['arguments']
                                
                                # 更新 finish_reason
                                if chunk_finish_reason:
                                    finish_reason = chunk_finish_reason
                                    
                            except json.JSONDecodeError:
                                continue
                
                # 文本输出完成
                if is_outputting_text:
                    yield {"type": "text_complete", "content": ""}
                
                # 构建完整消息
                if tool_calls_buffer:
                    accumulated_message['tool_calls'] = [
                        tool_calls_buffer[i] for i in sorted(tool_calls_buffer.keys())
                    ]
                
                message = accumulated_message
                
                # 检查是否有工具调用
                if finish_reason == 'tool_calls' and message.get('tool_calls'):
                    tool_calls = message['tool_calls']
                    info(f"[LLM Tools] 检测到 {len(tool_calls)} 个工具调用")
                    
                    # 按照您的要求：截断，只处理第一个工具调用
                    tool_call = tool_calls[0]
                    function_name = tool_call['function']['name']
                    arguments_str = tool_call['function']['arguments']
                    
                    # ⭐ 清理 arguments 字符串（移除可能的额外内容）
                    arguments_str = arguments_str.strip()
                    
                    # 尝试找到完整的 JSON 对象
                    try:
                        # 尝试直接解析
                        function_args = json.loads(arguments_str)
                    except json.JSONDecodeError as e:
                        # JSON 解析失败，尝试修复
                        error(f"[LLM Tools] JSON解析失败: {e}")
                        error(f"[LLM Tools] 原始 arguments: {repr(arguments_str)}")
                        
                        # 尝试提取第一个完整的 JSON 对象
                        brace_count = 0
                        json_end = -1
                        for i, char in enumerate(arguments_str):
                            if char == '{':
                                brace_count += 1
                            elif char == '}':
                                brace_count -= 1
                                if brace_count == 0:
                                    json_end = i + 1
                                    break
                        
                        if json_end > 0:
                            clean_json = arguments_str[:json_end]
                            info(f"[LLM Tools] 尝试使用截断的 JSON: {repr(clean_json)}")
                            try:
                                function_args = json.loads(clean_json)
                            except:
                                yield {
                                    "type": "error",
                                    "content": f"❌ 工具参数解析失败:\n```\n{arguments_str}\n```"
                                }
                                continue
                        else:
                            yield {
                                "type": "error",
                                "content": f"❌ 工具参数格式错误:\n```\n{arguments_str}\n```"
                            }
                            continue
                    
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
                    
                    tool_context = {
                        "todo_tracker": todo_tracker,
                        "board_id": board_id,
                        "conversation_id": conversation_id
                    }
                    result = await tool_executor.execute_tool_call(tool_call_obj, context=tool_context)

                    tool_success = result.status.value == "success"
                    try:
                        parsed_arguments = json.loads(function_args) if isinstance(function_args, str) else function_args
                    except json.JSONDecodeError:
                        parsed_arguments = {}

                    debug_payload = result.data if tool_success else {"error": result.error}
                    try:
                        payload_preview = json.dumps(debug_payload, ensure_ascii=False)
                    except TypeError:
                        payload_preview = str(debug_payload)
                    if len(payload_preview) > 500:
                        payload_preview = payload_preview[:500] + "...(truncated)"

                    info(
                        f"[LLM Tools] 工具执行{'成功' if tool_success else '失败'}: {function_name} | 参数: {parsed_arguments} | 结果: {payload_preview}"
                    )

                    window_related_tools = {
                        'create_window',
                        'update_window',
                        'edit_window',
                        'delete_window',
                        'move_window',
                        'read_window'
                    }
                    if function_name in window_related_tools:
                        window_id = debug_payload.get('window_id') if isinstance(debug_payload, dict) else None
                        if not window_id and isinstance(parsed_arguments, dict):
                            window_id = parsed_arguments.get('window_id')
                        board_for_log = None
                        if isinstance(debug_payload, dict):
                            board_for_log = debug_payload.get('board_id')
                        if not board_for_log and isinstance(parsed_arguments, dict):
                            board_for_log = parsed_arguments.get('board_id')
                        info(
                            f"[LLM Tools][Window] 操作 {function_name} -> board_id={board_for_log}, window_id={window_id}, success={tool_success}"
                        )
                    
                    yield {
                        "type": "tool_result",
                        "content": f"✅ 工具执行完成: {function_name}",
                        "tool_name": function_name,
                        "tool_result": result.data if tool_success else {"error": result.error}
                    }
                    
                    # ⭐ 如果执行了 todo 相关工具，立即发送 todo 状态更新
                    if function_name in [
                        'create_todo_list',
                        'complete_todo_item',
                        'add_todo_item',
                        'skip_todo_item',
                        'get_todo_status'
                    ]:
                        log_todo_status("执行待办工具后")
                        yield {
                            "type": "todo_status",
                            "content": todo_tracker.get_status()
                        }
                        persist_todo_state("执行待办工具后")
                    
                    # ⭐ 如果调用了 pause_execution 工具，立即暂停执行
                    if function_name == 'pause_execution':
                        pause_reason = result.data.get('reason', '') if result.status.value == "success" else ""
                        remaining = todo_tracker.get_status()['remaining_count'] if todo_tracker.has_todos() else 0
                        
                        info(f"[LLM Tools] 模型调用 pause_execution 工具，暂停执行。原因: {pause_reason}")
                        
                        # 发送 todo 状态给前端（如果有）
                        if todo_tracker.has_todos():
                            log_todo_status("pause_execution 调用时")
                            yield {
                                "type": "todo_status",
                                "content": todo_tracker.get_status()
                            }
                            persist_todo_state("pause_execution 后")
                        
                        # 将工具调用和结果添加到对话历史
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
                        
                        # ⭐ 将暂停原因作为模型的文本回复发送，让前端显示在对话中
                        pause_text = ""
                        if pause_reason:
                            pause_text = pause_reason
                        else:
                            pause_text = "执行已暂停"
                        
                        if remaining > 0:
                            pause_text += f"\n\n还有 {remaining} 项待办未完成，可以稍后继续。"
                        
                        # 先发送 text_start，确保工具调用状态更新为"已完成"
                        yield {
                            "type": "text_start",
                            "content": ""
                        }
                        
                        # 发送文本内容，让前端将其作为模型的自然回复显示
                        yield {
                            "type": "text_chunk",
                            "content": pause_text
                        }
                        
                        # 发送暂停提示（作为系统信息）
                        yield {
                            "type": "info",
                            "content": "⏸️ 执行已暂停"
                        }

                        persist_todo_state("pause_execution 完成后")
                        
                        # 暂停执行，结束对话
                        return
                    
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
                    # 没有工具调用，只有文本输出
                    content = message.get('content', '')
                    info(f"[LLM Tools] LLM 回复 (finish_reason={finish_reason}): {len(content)} 字符")
                    
                    # ⭐ 文本已经在流式循环中输出了，这里只需处理历史
                    if content:
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
                                status = todo_tracker.get_status()
                                log_todo_status("所有待办项完成")
                                yield {
                                    "type": "todo_status",
                                    "content": status
                                }
                                persist_todo_state("所有待办项完成")
                                info(f"[LLM Tools] 所有待办项已完成，结束对话")
                                return
                            else:
                                # 还有未完成的待办项，结束当前对话，让用户决定是否继续
                                status = todo_tracker.get_status()
                                remaining = status['remaining_count']
                                info(f"[LLM Tools] 还有 {remaining} 项待办未完成，结束本轮对话，等待用户下一步指令")
                                log_todo_status("主动停止但仍有待办")
                                # 发送 todo 状态给前端
                                yield {
                                    "type": "todo_status",
                                    "content": status
                                }
                                
                                # 告知用户还有待办项未完成，可稍后继续
                                message = f"⏹️ 对话已结束，还有 {remaining} 项待办未完成。如需继续，请重新发送指令或让助手调用 pause_execution 后再继续。"
                                yield {
                                    "type": "info",
                                    "content": message
                                }

                                persist_todo_state("主动停止但仍有待办")
                                
                                return
                        else:
                            # 没有创建待办列表，按原逻辑结束
                            persist_todo_state("无待办时结束对话")
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
                'stream': True,  # ⭐ 改为流式
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
                    
                    # ⭐ 流式处理响应
                    accumulated_response = {
                        'choices': [{
                            'message': {
                                'role': 'assistant',
                                'content': '',
                                'tool_calls': []
                            },
                            'finish_reason': None
                        }]
                    }
                    
                    tool_calls_buffer = {}  # 累积工具调用 {index: {id, type, function: {name, arguments}}}
                    
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        if not line_str or not line_str.startswith('data: '):
                            continue
                        
                        data = line_str[6:]
                        if data == '[DONE]':
                            break
                        
                        try:
                            chunk = json.loads(data)
                            if 'choices' not in chunk or not chunk['choices']:
                                continue
                            
                            choice = chunk['choices'][0]
                            delta = choice.get('delta', {})
                            finish_reason = choice.get('finish_reason')
                            
                            # 累积 content
                            if 'content' in delta and delta['content']:
                                accumulated_response['choices'][0]['message']['content'] += delta['content']
                            
                            # 累积 tool_calls
                            if 'tool_calls' in delta:
                                for tool_call_delta in delta['tool_calls']:
                                    idx = tool_call_delta.get('index', 0)
                                    
                                    if idx not in tool_calls_buffer:
                                        tool_calls_buffer[idx] = {
                                            'id': tool_call_delta.get('id', ''),
                                            'type': tool_call_delta.get('type', 'function'),
                                            'function': {
                                                'name': '',
                                                'arguments': ''
                                            }
                                        }
                                    
                                    if 'id' in tool_call_delta:
                                        tool_calls_buffer[idx]['id'] = tool_call_delta['id']
                                    
                                    if 'function' in tool_call_delta:
                                        func_delta = tool_call_delta['function']
                                        if 'name' in func_delta:
                                            tool_calls_buffer[idx]['function']['name'] += func_delta['name']
                                        if 'arguments' in func_delta:
                                            tool_calls_buffer[idx]['function']['arguments'] += func_delta['arguments']
                            
                            # 更新 finish_reason
                            if finish_reason:
                                accumulated_response['choices'][0]['finish_reason'] = finish_reason
                                
                        except json.JSONDecodeError:
                            continue
                    
                    # 将累积的 tool_calls 添加到响应
                    if tool_calls_buffer:
                        accumulated_response['choices'][0]['message']['tool_calls'] = [
                            tool_calls_buffer[i] for i in sorted(tool_calls_buffer.keys())
                        ]
                    
                    return accumulated_response
                    
        except Exception as e:
            import traceback
            error(f"[LLM Tools] API调用异常: {e}")
            error(f"[LLM Tools] 详细错误: {traceback.format_exc()}")
            return None
