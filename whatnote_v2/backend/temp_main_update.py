@app.post("/api/boards/{board_id}/windows/{window_id}/annotations/batch/summary-note")
async def generate_batch_summary_note(
    board_id: str,
    window_id: str,
    request: Request
):
    """生成PDF全文档阅读笔记（使用Split-Merge策略）"""
    try:
        # 获取请求体参数
        body = await request.json()
        summary_style = body.get('summary_style', 'detailed')
        custom_prompt = body.get('custom_prompt', '')
        
        info(f"生成全文档阅读笔记: board_id={board_id}, window_id={window_id}, style={summary_style}")
        
        # 预设Prompt模板
        SUMMARY_PROMPTS = {
            'detailed': """你是一位专业的学术和文档分析助手。请仔细阅读以下PDF文档的全部内容，生成一份详尽的、结构清晰的**全文档阅读笔记**。

**笔记生成要求**：
1. **核心观点提炼**：首先用简练的语言概括文档的核心主旨（Executive Summary）。
2. **结构化内容梳理**：按照文档的逻辑结构（章节或主题），详细记录关键信息、重要数据、论点和结论。请保留足够的细节，不要只是列大纲，另外，需要在重点或者细节位置提供页码，以(page XXX)的形式提供。
3. **重要概念解析**：解释文档中出现的关键术语和概念。
4. **总结与启示**：总结文档的价值，并给出你的阅读心得或批判性思考。
5. **格式要求**：使用标准Markdown格式，利用多级标题、列表、加粗等使笔记易于阅读。

请直接输出Markdown格式的笔记内容。""",
            'concise': """请阅读文档内容，生成一份**简洁的摘要笔记**。

**要求**：
1. 提炼核心论点，忽略次要细节。
2. 使用要点列表（Bullet points）形式呈现。
3. 控制篇幅，专注于“文档讲了什么”和“主要结论是什么”。
4. 适合快速浏览。""",
            'academic': """请以**学术综述**的风格撰写这份文档的笔记。

**要求**：
1. **背景与问题**：文档研究了什么问题？背景是什么？
2. **方法与论证**：作者使用了什么方法或论据？
3. **主要发现**：得出了什么结论？
4. **学术价值**：该文档在相关领域的贡献是什么？
5. **引用与术语**：准确引用文中的专业术语。""",
            'outline': """请为这份文档生成一份**大纲式笔记**。

**要求**：
1. 严格遵循文档的目录结构。
2. 在每个层级下，用简短的句子概括该部分的内容。
3. 重点展示文档的逻辑框架和层次关系。
4. 适合梳理文档结构。"""
        }
        
        # 确定Prompt模板
        base_prompt_template = custom_prompt if summary_style == 'custom' else SUMMARY_PROMPTS.get(summary_style, SUMMARY_PROMPTS['detailed'])
        
        # 配置参数
        SMALL_FILE_THRESHOLD = 30000  # 小文件阈值（字符数）
        PAGES_PER_GROUP = 10  # 大文件分组时每组页数
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        target_window = None
        for window in windows:
            if window.get('id') == window_id:
                target_window = window
                break
        
        if not target_window:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        if target_window.get('type') != 'pdf':
            raise HTTPException(status_code=400, detail="只有PDF文件支持批量注释功能")
        
        pdf_filename = target_window.get('title', 'unknown')
        info(f"开始分析PDF文件: {pdf_filename}")
        
        # 读取PDF所有页面内容
        all_pages_content = []
        total_chars = 0
        page_num = 1
        
        while True:
            page_content = content_manager.get_pdf_page_contents(board_id, window_id, page_num)
            if not page_content.get('current'):
                break
            
            page_text = page_content['current']
            all_pages_content.append({
                'page': page_num,
                'content': page_text,
                'length': len(page_text)
            })
            total_chars += len(page_text)
            page_num += 1
        
        total_pages = len(all_pages_content)
        info(f"PDF总页数: {total_pages}, 总字符数: {total_chars}")
        
        if total_pages == 0:
            raise HTTPException(status_code=400, detail="PDF文件无内容")
        
        # 创建或获取总笔记对话记录
        summary_conv_id = f"summary-note-{window_id}"
        conversation = conversation_manager.get_conversation(board_id, summary_conv_id, page=None, limit=None)
        if not conversation:
            conversation = conversation_manager.create_conversation(
                board_id,
                title=f"全文档笔记 - {pdf_filename}"
            )
            conversations_dir = conversation_manager.get_board_conversations_dir(board_id)
            old_file = conversations_dir / f"{conversation['id']}.json"
            new_file = conversations_dir / f"{summary_conv_id}.json"
            if old_file.exists():
                old_file.rename(new_file)
            conversation['id'] = summary_conv_id
        
        # 准备SSE流式响应
        async def generate_summary_stream():
            try:
                # 判断使用哪种方法
                if total_chars <= SMALL_FILE_THRESHOLD:
                    # 方法1：小文件，直接发送全部内容
                    info(f"使用直接方法（文件较小）: {total_chars} 字符")
                    yield f"data: {json.dumps({'type': 'status', 'message': '文件较小，直接生成笔记中...'}, ensure_ascii=False)}\n\n"
                    
                    # 构建完整文本
                    full_text = "\n\n".join([
                        f"=== 第{p['page']}页 ===\n{p['content']}"
                        for p in all_pages_content
                    ])
                    
                    # 构建最终提示词
                    prompt = f"""{base_prompt_template}

**文档信息**：
- 文件名: {pdf_filename}
- 总页数: {total_pages}

**文档内容**：
{full_text}"""
                    
                    # 发送给LLM
                    user_message = {
                        "role": "user",
                        "content": prompt,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": {
                            "action": "generate_batch_summary_note",
                            "pdf_filename": pdf_filename,
                            "window_id": window_id,
                            "total_pages": total_pages,
                            "total_chars": total_chars,
                            "method": "direct",
                            "style": summary_style
                        }
                    }
                    
                    messages = [user_message]
                    accumulated_content = ""
                    
                    async for chunk in llm_service.chat_completion(messages, stream=True):
                        if chunk:
                            accumulated_content += chunk
                            yield f"data: {json.dumps({'type': 'content', 'content': chunk}, ensure_ascii=False)}\n\n"
                    
                    # 保存助手消息
                    assistant_message = {
                        "role": "assistant",
                        "content": accumulated_content,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": {
                            "action": "generate_batch_summary_note",
                            "method": "direct",
                            "total_pages": total_pages,
                            "total_chars": total_chars
                        }
                    }
                    
                    conversation_manager.add_message(board_id, summary_conv_id, user_message)
                    conversation_manager.add_message(board_id, summary_conv_id, assistant_message)
                    
                    # 保存总笔记到文件（小文件模式）
                    try:
                        pdf_file_path = Path(target_window.get('content'))
                        if not pdf_file_path.is_absolute():
                            board_dir = None
                            for course_dir in content_manager.file_manager.courses_dir.iterdir():
                                if course_dir.is_dir():
                                    potential_board_dir = course_dir / board_id
                                    if potential_board_dir.exists():
                                        board_dir = potential_board_dir
                                        break
                            
                            if board_dir:
                                pdf_file_path = board_dir / pdf_file_path
                        
                        if pdf_file_path and pdf_file_path.exists():
                            pdf_name = pdf_file_path.stem
                            pages_dir = pdf_file_path.parent / "pages" / pdf_name
                            pages_dir.mkdir(parents=True, exist_ok=True)
                            
                            summary_file_path = pages_dir / "summary_note.md"
                            
                            with open(summary_file_path, 'w', encoding='utf-8') as f:
                                f.write(accumulated_content)
                            
                            info(f"✅ 全文档笔记已保存至: {summary_file_path}")
                            yield f"data: {json.dumps({'type': 'saved', 'path': str(summary_file_path)}, ensure_ascii=False)}\n\n"
                        else:
                            error(f"无法保存笔记文件，PDF路径不存在: {pdf_file_path}")
                    except Exception as e:
                        error(f"保存笔记文件失败: {e}")

                    yield f"data: {json.dumps({'type': 'complete', 'content': accumulated_content}, ensure_ascii=False)}\n\n"
                    
                else:
                    # 方法2：大文件，Split-Merge策略
                    info(f"使用Split-Merge方法（文件较大）: {total_chars} 字符")
                    yield f"data: {json.dumps({'type': 'status', 'message': '文件较大，使用分组分析策略...'}, ensure_ascii=False)}\n\n"
                    
                    # 分割页面
                    groups = []
                    for i in range(0, total_pages, PAGES_PER_GROUP):
                        group_pages = all_pages_content[i:i+PAGES_PER_GROUP]
                        groups.append({
                            'group_number': len(groups) + 1,
                            'pages': group_pages,
                            'page_start': group_pages[0]['page'],
                            'page_end': group_pages[-1]['page']
                        })
                    
                    info(f"分为{len(groups)}组进行分析")
                    yield f"data: {json.dumps({'type': 'status', 'message': f'分为{len(groups)}组进行逐个分析...'}, ensure_ascii=False)}\n\n"
                    
                    # 对每组进行分析（生成局部笔记）
                    group_notes = []
                    for group in groups:
                        group_num = group['group_number']
                        page_start = group['page_start']
                        page_end = group['page_end']
                        status_message = f'正在分析第{group_num}组 (第{page_start}-{page_end}页)...'
                        yield f"data: {json.dumps({'type': 'status', 'message': status_message}, ensure_ascii=False)}\n\n"
                        
                        # 构建组文本
                        group_text = "\n\n".join([
                            f"=== 第{p['page']}页 ===\n{p['content']}"
                            for p in group['pages']
                        ])
                        
                        # 构建子模型提示词 - 局部笔记（简化版Prompt，主要用于提取信息）
                        sub_prompt = f"""你是一位专业的文档分析助手。请分析以下PDF文档片段的内容，生成一份**局部阅读笔记**。

**文档信息**：
- 文件名: {pdf_filename}
- 分析范围: 第{group['page_start']}-{group['page_end']}页（共{total_pages}页）
- 组号: {group_num}/{len(groups)}

**文档片段内容**：
{group_text}

**任务要求**：
1. 仔细阅读该片段，提取其中的关键信息、主要论点和重要数据。
2. **不要生成大纲**，而是生成内容详实的笔记段落。
3. 如果片段包含完整的章节，请明确章节标题。
4. 标记出该部分中最重要的概念。
5. 保持客观、准确。

请输出Markdown格式的笔记内容。"""
                        
                        # 创建子对话记录
                        sub_conv_id = f"summary-note-{window_id}-part{group_num}"
                        sub_conversation = conversation_manager.get_conversation(board_id, sub_conv_id, page=None, limit=None)
                        if not sub_conversation:
                            sub_conversation = conversation_manager.create_conversation(
                                board_id,
                                title=f"全文档笔记-分组{group_num} - {pdf_filename}"
                            )
                            conversations_dir = conversation_manager.get_board_conversations_dir(board_id)
                            old_file = conversations_dir / f"{sub_conversation['id']}.json"
                            new_file = conversations_dir / f"{sub_conv_id}.json"
                            if old_file.exists():
                                old_file.rename(new_file)
                            sub_conversation['id'] = sub_conv_id
                        
                        # 发送给子模型
                        sub_user_message = {
                            "role": "user",
                            "content": sub_prompt,
                            "timestamp": datetime.now().isoformat(),
                            "metadata": {
                                "action": "generate_batch_summary_note_sub",
                                "pdf_filename": pdf_filename,
                                "window_id": window_id,
                                "group_number": group_num,
                                "page_start": group['page_start'],
                                "page_end": group['page_end'],
                                "method": "split"
                            }
                        }
                        
                        sub_messages = [sub_user_message]
                        sub_accumulated_content = ""
                        
                        async for chunk in llm_service.chat_completion(sub_messages, stream=True):
                            if chunk:
                                sub_accumulated_content += chunk
                                yield f"data: {json.dumps({'type': 'group_content', 'group': group_num, 'content': chunk}, ensure_ascii=False)}\n\n"
                        
                        # 保存子模型消息
                        sub_assistant_message = {
                            "role": "assistant",
                            "content": sub_accumulated_content,
                            "timestamp": datetime.now().isoformat(),
                            "metadata": {
                                "action": "generate_batch_summary_note_sub",
                                "group_number": group_num,
                                "method": "split"
                            }
                        }
                        
                        conversation_manager.add_message(board_id, sub_conv_id, sub_user_message)
                        conversation_manager.add_message(board_id, sub_conv_id, sub_assistant_message)
                        
                        group_notes.append({
                            'group_number': group_num,
                            'content': sub_accumulated_content
                        })
                        yield f"data: {json.dumps({'type': 'group_done', 'group': group_num}, ensure_ascii=False)}\n\n"
                    
                    # 汇总所有分组笔记
                    yield f"data: {json.dumps({'type': 'status', 'message': '所有分组分析完成，正在整合成总笔记...'}, ensure_ascii=False)}\n\n"
                    
                    # 构建汇总提示词 - Merge
                    groups_summary = "\n\n".join([
                        f"=== 第{g['group_number']}部分笔记 ===\n{g['content']}"
                        for g in group_notes
                    ])
                    
                    merge_prompt = f"""{base_prompt_template}

**文档信息**：
- 文件名: {pdf_filename}
- 总页数: {total_pages}

**各部分局部笔记（原始素材）**：
{groups_summary}

**特别指示**：
以上内容是基于文档分段生成的局部笔记。请根据你的笔记风格要求，将这些素材整合成一份完整的、连贯的全文档笔记。确保整合后的内容流畅，不要有明显的拼接痕迹。"""
                    
                    # 发送给LLM进行汇总
                    merge_user_message = {
                        "role": "user",
                        "content": merge_prompt,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": {
                            "action": "generate_batch_summary_note_merge",
                            "pdf_filename": pdf_filename,
                            "window_id": window_id,
                            "total_pages": total_pages,
                            "total_groups": len(groups),
                            "method": "split_merge",
                            "style": summary_style
                        }
                    }
                    
                    merge_messages = [merge_user_message]
                    merge_accumulated_content = ""
                    
                    async for chunk in llm_service.chat_completion(merge_messages, stream=True):
                        if chunk:
                            merge_accumulated_content += chunk
                            yield f"data: {json.dumps({'type': 'merge_content', 'content': chunk}, ensure_ascii=False)}\n\n"
                    
                    # 保存汇总消息
                    merge_assistant_message = {
                        "role": "assistant",
                        "content": merge_accumulated_content,
                        "timestamp": datetime.now().isoformat(),
                        "metadata": {
                            "action": "generate_batch_summary_note_merge",
                            "method": "split_merge",
                            "total_pages": total_pages,
                            "total_groups": len(groups)
                        }
                    }
                    
                    conversation_manager.add_message(board_id, summary_conv_id, merge_user_message)
                    conversation_manager.add_message(board_id, summary_conv_id, merge_assistant_message)

                    # 保存总笔记到文件
                    try:
                        pdf_file_path = Path(target_window.get('content'))
                        if not pdf_file_path.is_absolute():
                            board_dir = None
                            for course_dir in content_manager.file_manager.courses_dir.iterdir():
                                if course_dir.is_dir():
                                    potential_board_dir = course_dir / board_id
                                    if potential_board_dir.exists():
                                        board_dir = potential_board_dir
                                        break
                            
                            if board_dir:
                                pdf_file_path = board_dir / pdf_file_path
                        
                        if pdf_file_path and pdf_file_path.exists():
                            pdf_name = pdf_file_path.stem
                            pages_dir = pdf_file_path.parent / "pages" / pdf_name
                            pages_dir.mkdir(parents=True, exist_ok=True)
                            
                            summary_file_path = pages_dir / "summary_note.md"
                            
                            with open(summary_file_path, 'w', encoding='utf-8') as f:
                                f.write(merge_accumulated_content)
                            
                            info(f"✅ 全文档笔记已保存至: {summary_file_path}")
                            yield f"data: {json.dumps({'type': 'saved', 'path': str(summary_file_path)}, ensure_ascii=False)}\n\n"
                        else:
                            error(f"无法保存笔记文件，PDF路径不存在: {pdf_file_path}")
                            yield f"data: {json.dumps({'type': 'error', 'error': '无法保存笔记文件，PDF路径无效'}, ensure_ascii=False)}\n\n"

                    except Exception as e:
                        error(f"保存笔记文件失败: {e}")
                        yield f"data: {json.dumps({'type': 'error', 'error': f'保存文件失败: {str(e)}'}, ensure_ascii=False)}\n\n"
                    
                    yield f"data: {json.dumps({'type': 'complete', 'content': merge_accumulated_content}, ensure_ascii=False)}\n\n"
                    
            except Exception as e:
                error(f"生成全文档笔记失败: {e}")
                yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
        
        return StreamingResponse(
            generate_summary_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        error(f"生成全文档笔记失败: {e}")
        raise HTTPException(status_code=500, detail=f"生成全文档笔记失败: {str(e)}")





