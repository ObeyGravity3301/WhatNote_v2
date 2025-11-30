
@app.post("/api/boards/{board_id}/windows/{window_id}/annotations/batch/generate-script-section")
async def generate_narrator_script_section(
    board_id: str,
    window_id: str,
    request: Request
):
    """批量生成讲稿：为一个分段的所有页面生成演讲稿"""
    try:
        request_body = await request.json()
        section_index = request_body.get('section_index', 0)
        section_data = request_body.get('section_data')
        subdivision_data = request_body.get('subdivision_data')
        prompt_template = request_body.get('promptTemplate', '')
        
        info(f"开始为分段 {section_index} 批量生成讲稿")
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        target_window = None
        for window in windows:
            if window.get('id') == window_id:
                target_window = window
                break
        
        if not target_window:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        page_start = section_data['page_start']
        page_end = section_data['page_end']
        
        async def generate_stream():
            try:
                yield f"data: {json.dumps({'type': 'status', 'message': f'正在为第 {page_start}-{page_end} 页生成讲稿...'}, ensure_ascii=False)}\n\n"
                
                # 读取该分段所有页面的内容
                pages_content = []
                for page in range(page_start, page_end + 1):
                    page_data = content_manager.get_pdf_page_contents(board_id, window_id, page)
                    if page_data and page_data.get('current'):
                        pages_content.append({
                            'page': page,
                            'content': page_data['current']
                        })
                
                if not pages_content:
                    error_msg = f'未找到分段内容，页码范围: {page_start}-{page_end}'
                    yield f"data: {json.dumps({'type': 'error', 'error': error_msg}, ensure_ascii=False)}\n\n"
                    return
                
                # 构建完整的内容文本
                full_content = ""
                for page_info in pages_content:
                    full_content += f"\n\n=== 第{page_info['page']}页 ===\n{page_info['content']}"
                
                # 获取分段描述
                section_description = ''
                if subdivision_data:
                     section_description = subdivision_data.get('section_summary') or section_data.get('description') or ''

                # 默认讲稿要求
                default_req = "请为每一页撰写一份口语化的演讲稿。\n要求：\n1. 时间控制在 30-60 秒。\n2. 语言自然流畅，适合朗读。\n3. 不要念标题，而是解释核心观点。\n4. 使用第一人称。"
                script_requirement = prompt_template if prompt_template else default_req
                
                prompt = f"""你是一位专业的演讲者。请根据以下PDF分段内容，为每一页撰写演讲稿。

**分段信息**：
- 分段标题: {section_data.get('title', '未命名')}
- 分段描述: {section_description}
- 页码范围: 第{page_start}页 - 第{page_end}页

**分段完整内容**：
{full_content}

**讲稿要求**：
{script_requirement}

**输出格式**（必须严格遵守JSON格式）：
```json
{{
  "scripts": [
    {{
      "page": {page_start},
      "script": "第{page_start}页的演讲稿内容..."
    }},
    {{
      "page": {page_start + 1},
      "script": "第{page_start + 1}页的演讲稿内容..."
    }}
  ]
}}
```
请确保scripts数组包含从{page_start}到{page_end}的所有页面。
直接输出JSON，不要添加任何额外的说明文字。"""
                
                messages = [{
                    "role": "user",
                    "content": prompt,
                    "timestamp": datetime.now().isoformat()
                }]
                
                accumulated_content = ""
                
                # 调用LLM
                async for chunk in llm_service.chat_completion(messages, stream=True):
                    if chunk:
                        accumulated_content += chunk
                
                # 解析结果
                try:
                    content = accumulated_content.strip()
                    if content.startswith('```'):
                        lines = content.split('\n')
                        if lines[0].startswith('```'): lines = lines[1:]
                        if lines[-1].startswith('```'): lines = lines[:-1]
                        content = '\n'.join(lines)
                    
                    result_data = json.loads(content)
                    scripts = result_data.get('scripts', [])
                    
                    for script_item in scripts:
                        page = script_item.get('page')
                        text = script_item.get('script')
                        if page and text:
                            yield f"data: {json.dumps({'type': 'page_done', 'page': page, 'content': text}, ensure_ascii=False)}\n\n"
                    
                    yield f"data: {json.dumps({'type': 'complete', 'total': len(scripts)}, ensure_ascii=False)}\n\n"
                    
                except json.JSONDecodeError as e:
                    error(f"解析讲稿JSON失败: {e}")
                    yield f"data: {json.dumps({'type': 'error', 'error': f'JSON解析失败: {str(e)}'}, ensure_ascii=False)}\n\n"

            except Exception as e:
                error(f"批量生成讲稿失败: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        error(f"批量生成讲稿接口错误: {e}")
        raise HTTPException(status_code=500, detail=str(e))


