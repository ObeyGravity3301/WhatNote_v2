
@app.post("/api/boards/{board_id}/windows/{window_id}/image/extract")
async def extract_image_content(board_id: str, window_id: str):
    """提取图片窗口的文字内容"""
    try:
        info(f"🚀 开始提取图片内容: window_id={window_id}")
        
        # 获取窗口信息
        windows = content_manager.get_board_windows(board_id)
        window_data = None
        for window in windows:
            if window.get('id') == window_id:
                window_data = window
                break
        
        if not window_data:
            raise HTTPException(status_code=404, detail="窗口不存在")
        
        # 确定图片路径
        image_path_str = window_data.get('content', '')
        if not image_path_str:
            # 尝试从 file_path 获取
            image_path_str = window_data.get('file_path', '')
            
        if not image_path_str:
             raise HTTPException(status_code=400, detail="窗口没有图片内容")

        # 处理路径
        image_path = Path(image_path_str)
        if not image_path.is_absolute():
             # 1. 尝试直接拼接 DATA_DIR
             path1 = Path(DATA_DIR) / image_path_str
             if path1.exists():
                 image_path = path1
             else:
                 # 2. 尝试作为 board_dir 下的文件
                 # 这里的 board_dir 假设为 DATA_DIR / board_id (兼容旧结构) 或 DATA_DIR / "courses" / ... / board_id
                 # 简单遍历查找
                 found = False
                 for root, dirs, files in os.walk(DATA_DIR):
                     if image_path_str in files:
                         image_path = Path(root) / image_path_str
                         found = True
                         break
                     # 也可以检查相对路径
                     possible = Path(root) / image_path_str
                     if possible.exists() and possible.is_file():
                         image_path = possible
                         found = True
                         break
                 
                 if not found:
                     # 最后的尝试：URL解码
                     if "/static/files/" in image_path_str:
                         try:
                             import urllib.parse
                             rel_path = urllib.parse.unquote(image_path_str.split("/static/files/")[1])
                             path2 = Path(DATA_DIR) / rel_path
                             if path2.exists():
                                 image_path = path2
                         except:
                             pass

        if not image_path.exists():
             raise HTTPException(status_code=404, detail=f"图片文件不存在: {image_path_str}")

        info(f"处理图片: {image_path}")

        # 读取图片并转base64
        import base64
        with open(image_path, 'rb') as f:
            img_bytes = f.read()
        img_base64 = base64.b64encode(img_bytes).decode('utf-8')
        
        # 构造 Prompt
        messages = [
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """你正在分析一张图片。请完成以下两个独立任务：

**任务1：文本提取（OCR）**
- 识别并提取图片中的**所有文字内容**。
- 保持原有的层次结构和格式。
- 使用Markdown格式（# 标题、- 列表等）。
- 如果没有文字，返回空字符串。

**任务2：图片内容描述**
- 详细描述图片展示的具体内容。
- 如果是图表，描述图表类型、数据趋势等。
- 如果没有明显内容，返回空字符串。

**输出格式（必须是纯JSON）：**
```json
{
  "text_extraction": "文字内容（Markdown）",
  "visual_description": "图片描述"
}
```
只返回JSON，不要markdown代码块标记。"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{img_base64}"
                        }
                    }
                ]
            }
        ]

        # 调用LLM
        current_config = llm_service.get_config()
        current_provider = current_config.get('provider', 'qwen')
        
        vision_model_map = {
            'qwen': 'qwen-vl-plus',
            'openai': 'gpt-4o',
            'anthropic': 'claude-3-5-sonnet-20241022',
            'gemini': 'gemini-1.5-pro'
        }
        use_model = vision_model_map.get(current_provider, 'qwen-vl-plus')

        accumulated_content = ""
        async for chunk in llm_service.chat_completion(messages, stream=False, override_model=use_model):
            accumulated_content += chunk
        
        info(f"✅ 图片内容提取完成: {len(accumulated_content)} 字")

        # 解析 JSON
        text_content = ""
        image_content = ""
        try:
            json_content = accumulated_content.strip()
            if json_content.startswith("```json"):
                json_content = json_content[7:]
            if json_content.startswith("```"):
                json_content = json_content[3:]
            if json_content.endswith("```"):
                json_content = json_content[:-3]
            json_content = json_content.strip()
            
            import json
            parsed = json.loads(json_content)
            text_content = parsed.get("text_extraction", "")
            image_content = parsed.get("visual_description", "")
        except Exception as e:
            info(f"JSON解析失败，返回原始内容: {e}")
            text_content = accumulated_content
            image_content = "（解析失败）"

        # 保存结果
        save_dir = image_path.parent
        if not save_dir.exists():
             save_dir = Path(DATA_DIR) / "files"
             save_dir.mkdir(parents=True, exist_ok=True)
             
        image_stem = image_path.stem
        md_filename = f"{image_stem}_extracted.md"
        md_path = save_dir / md_filename
        
        final_content = f"# 图片提取内容: {image_path.name}\n\n## 文本提取\n\n{text_content}\n\n## 图片描述\n\n{image_content}"
        
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(final_content)
            
        info(f"💾 内容已保存到: {md_path}")
        
        return {
            'success': True,
            'text_content': text_content,
            'image_content': image_content,
            'saved_path': str(md_path)
        }

    except Exception as e:
        error(f"图片提取失败: {e}")
        import traceback
        error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))





