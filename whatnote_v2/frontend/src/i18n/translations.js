/**
 * 多语言字典
 * 结构：{ key: { default: { lang: value }, themeName: { lang: value } } }
 */
const translations = {
  // 通用词汇
  "start": {
    "default": {
      "zh-CN": "开始",
      "en-US": "Start",
      "ja-JP": "スタート"
    }
  },
  "create_course": {
    "default": {
      "zh-CN": "新建课程",
      "en-US": "New Course",
      "ja-JP": "新しいコース"
    }
  },
  "create_board": {
    "default": {
      "zh-CN": "新建展板",
      "en-US": "New Board",
      "ja-JP": "新しいボード"
    }
  },
  "recycle_bin": {
    "default": {
      "zh-CN": "回收站",
      "en-US": "Recycle Bin",
      "ja-JP": "ごみ箱"
    },
    "mac": {
      "zh-CN": "废纸篓",
      "en-US": "Trash",
      "ja-JP": "ゴミ箱"
    }
  },
  "console": {
    "default": {
      "zh-CN": "工具控制台",
      "en-US": "Console",
      "ja-JP": "コンソール"
    }
  },
  "rename": {
    "default": {
      "zh-CN": "重命名",
      "en-US": "Rename",
      "ja-JP": "名前を変更"
    }
  },
  "delete": {
    "default": {
      "zh-CN": "删除",
      "en-US": "Delete",
      "ja-JP": "削除"
    }
  },
  "open_in_explorer": {
    "default": {
      "zh-CN": "在资源管理器中打开",
      "en-US": "Open in File Explorer",
      "ja-JP": "エクスプローラーで開く"
    },
    "mac": {
      "zh-CN": "在访达中显示",
      "en-US": "Reveal in Finder",
      "ja-JP": "Finderで表示"
    }
  },
  "properties": {
    "default": {
      "zh-CN": "属性(P)",
      "en-US": "Properties(P)",
      "ja-JP": "プロパティ(P)"
    }
  },
  "empty_trash": {
    "default": {
      "zh-CN": "清空回收站",
      "en-US": "Empty Recycle Bin",
      "ja-JP": "ごみ箱を空にする"
    }
  },
  "view": {
    "default": {
      "zh-CN": "查看(V) ▼",
      "en-US": "View(V) ▼",
      "ja-JP": "表示(V) ▼"
    }
  },
  "sort_name": {
    "default": {
      "zh-CN": "名称",
      "en-US": "Name",
      "ja-JP": "名前"
    }
  },
  "sort_created": {
    "default": {
      "zh-CN": "创建时间",
      "en-US": "Created Time",
      "ja-JP": "作成日時"
    }
  },
  "sort_deleted": {
    "default": {
      "zh-CN": "删除时间",
      "en-US": "Deleted Time",
      "ja-JP": "削除日時"
    }
  },
  "sort_type": {
    "default": {
      "zh-CN": "类型",
      "en-US": "Type",
      "ja-JP": "種類"
    }
  },
  "sort_asc": {
    "default": {
      "zh-CN": "正序",
      "en-US": "Ascending",
      "ja-JP": "昇順"
    }
  },
  "sort_desc": {
    "default": {
      "zh-CN": "倒序",
      "en-US": "Descending",
      "ja-JP": "降順"
    }
  },
  "ok": {
    "default": {
      "zh-CN": "确定",
      "en-US": "OK",
      "ja-JP": "OK"
    }
  },
  "cancel": {
    "default": {
      "zh-CN": "取消",
      "en-US": "Cancel",
      "ja-JP": "キャンセル"
    }
  },
  "personalization": {
    "default": {
      "zh-CN": "个性化",
      "en-US": "Personalization",
      "ja-JP": "個人設定"
    }
  },
  "language": {
    "default": {
      "zh-CN": "语言",
      "en-US": "Language",
      "ja-JP": "言語"
    }
  },
  "select_language": {
    "default": {
      "zh-CN": "选择软件显示语言。",
      "en-US": "Select software display language.",
      "ja-JP": "ソフトウェアの表示言語を選択してください。"
    }
  },
  "confirm_delete_title": {
    "default": {
      "zh-CN": "永久删除确认",
      "en-US": "Permanent Delete Confirmation",
      "ja-JP": "永久削除の確認"
    }
  },
  "confirm_delete_msg": {
    "default": {
      "zh-CN": "确定要永久删除这个文件吗？此操作无法撤销！",
      "en-US": "Are you sure you want to permanently delete this file? This action cannot be undone!",
      "ja-JP": "このファイルを永久に削除してもよろしいですか？この操作は取り消せません！"
    }
  },
  "confirm_empty_trash_title": {
    "default": {
      "zh-CN": "清空回收站",
      "en-US": "Empty Recycle Bin",
      "ja-JP": "ごみ箱を空にする"
    }
  },
  "confirm_empty_trash_msg": {
    "default": {
      "zh-CN": "确定要清空回收站吗？此操作将永久删除所有文件，无法撤销！",
      "en-US": "Are you sure you want to empty the recycle bin? This will permanently delete all files and cannot be undone!",
      "ja-JP": "ごみ箱を空にしてもよろしいですか？すべてのファイルが永久に削除され、取り消すことはできません！"
    }
  },
  // 个性化面板相关
  "loading": {
    "default": {
      "zh-CN": "加载中...",
      "en-US": "Loading...",
      "ja-JP": "読み込み中..."
    }
  },
  "loading_personalization": {
    "default": {
      "zh-CN": "正在加载个性化设置，请稍候。",
      "en-US": "Loading personalization settings, please wait.",
      "ja-JP": "個人設定を読み込んでいます。しばらくお待ちください。"
    }
  },
  "theme_style": {
    "default": {
      "zh-CN": "主题风格",
      "en-US": "Theme Style",
      "ja-JP": "テーマスタイル"
    }
  },
  "theme_win98": {
    "default": {
      "zh-CN": "Windows 98 （别的没做）",
      "en-US": "Windows 98 (Others not implemented)",
      "ja-JP": "Windows 98 （他は未実装）"
    }
  },
  "default_wallpaper": {
    "default": {
      "zh-CN": "全局默认壁纸",
      "en-US": "Global Default Wallpaper",
      "ja-JP": "グローバルデフォルト壁紙"
    }
  },
  "default_wallpaper_desc": {
    "default": {
      "zh-CN": "将会应用到所有展板，除非某个展板单独指定了壁纸。",
      "en-US": "Will be applied to all boards unless a board has its own wallpaper.",
      "ja-JP": "すべてのボードに適用されます。ボードが独自の壁紙を指定している場合を除きます。"
    }
  },
  "display_mode": {
    "default": {
      "zh-CN": "显示模式：",
      "en-US": "Display Mode:",
      "ja-JP": "表示モード："
    }
  },
  "wallpaper_preview": {
    "default": {
      "zh-CN": "默认壁纸预览",
      "en-US": "Default Wallpaper Preview",
      "ja-JP": "デフォルト壁紙プレビュー"
    }
  },
  "no_default_wallpaper": {
    "default": {
      "zh-CN": "暂未设置默认壁纸",
      "en-US": "No default wallpaper set",
      "ja-JP": "デフォルト壁紙が設定されていません"
    }
  },
  "filename": {
    "default": {
      "zh-CN": "文件名：",
      "en-US": "Filename:",
      "ja-JP": "ファイル名："
    }
  },
  "upload_time": {
    "default": {
      "zh-CN": "上传时间：",
      "en-US": "Upload Time:",
      "ja-JP": "アップロード日時："
    }
  },
  "unnamed": {
    "default": {
      "zh-CN": "未命名",
      "en-US": "Unnamed",
      "ja-JP": "無題"
    }
  },
  "uploading": {
    "default": {
      "zh-CN": "正在上传...",
      "en-US": "Uploading...",
      "ja-JP": "アップロード中..."
    }
  },
  "change_default_wallpaper": {
    "default": {
      "zh-CN": "更换默认壁纸...",
      "en-US": "Change Default Wallpaper...",
      "ja-JP": "デフォルト壁紙を変更..."
    }
  },
  "board_wallpaper": {
    "default": {
      "zh-CN": "展板专属壁纸",
      "en-US": "Board Wallpaper",
      "ja-JP": "ボード専用壁紙"
    }
  },
  "current_board": {
    "default": {
      "zh-CN": "当前展板：",
      "en-US": "Current Board:",
      "ja-JP": "現在のボード："
    }
  },
  "board_wallpaper_desc": {
    "default": {
      "zh-CN": "上传多个壁纸后，可在下方快速切换。未选择时将使用全局默认壁纸。",
      "en-US": "After uploading multiple wallpapers, you can quickly switch below. If none is selected, the global default wallpaper will be used.",
      "ja-JP": "複数の壁紙をアップロード後、下で素早く切り替えできます。選択されていない場合は、グローバルデフォルト壁紙が使用されます。"
    }
  },
  "no_board_wallpaper": {
    "default": {
      "zh-CN": "暂未上传展板专属壁纸。",
      "en-US": "No board wallpaper uploaded yet.",
      "ja-JP": "ボード専用壁紙はまだアップロードされていません。"
    }
  },
  "wallpaper": {
    "default": {
      "zh-CN": "壁纸",
      "en-US": "Wallpaper",
      "ja-JP": "壁紙"
    }
  },
  "unnamed_wallpaper": {
    "default": {
      "zh-CN": "未命名壁纸",
      "en-US": "Unnamed Wallpaper",
      "ja-JP": "無題の壁紙"
    }
  },
  "in_use": {
    "default": {
      "zh-CN": "正在使用",
      "en-US": "In Use",
      "ja-JP": "使用中"
    }
  },
  "set_as_current": {
    "default": {
      "zh-CN": "设为当前壁纸",
      "en-US": "Set as Current Wallpaper",
      "ja-JP": "現在の壁紙に設定"
    }
  },
  "upload_board_wallpaper": {
    "default": {
      "zh-CN": "上传展板壁纸...",
      "en-US": "Upload Board Wallpaper...",
      "ja-JP": "ボード壁紙をアップロード..."
    }
  },
  "restore_default_wallpaper": {
    "default": {
      "zh-CN": "恢复默认壁纸",
      "en-US": "Restore Default Wallpaper",
      "ja-JP": "デフォルト壁紙に戻す"
    }
  },
  "current_using_solid": {
    "default": {
      "zh-CN": "当前使用：纯色桌面 (Win98 默认蓝)",
      "en-US": "Currently Using: Solid Color Desktop (Win98 Default Blue)",
      "ja-JP": "現在使用中：単色デスクトップ（Win98デフォルトブルー）"
    }
  },
  "current_using_board": {
    "default": {
      "zh-CN": "当前使用：展板自定义壁纸",
      "en-US": "Currently Using: Board Custom Wallpaper",
      "ja-JP": "現在使用中：ボードカスタム壁紙"
    }
  },
  "current_using_default": {
    "default": {
      "zh-CN": "当前使用：全局默认壁纸",
      "en-US": "Currently Using: Global Default Wallpaper",
      "ja-JP": "現在使用中：グローバルデフォルト壁紙"
    }
  },
  "wallpaper_mode_updated": {
    "default": {
      "zh-CN": "壁纸显示模式已更新。",
      "en-US": "Wallpaper display mode updated.",
      "ja-JP": "壁紙表示モードが更新されました。"
    }
  },
  "updating_display_mode": {
    "default": {
      "zh-CN": "正在更新默认壁纸显示模式...",
      "en-US": "Updating default wallpaper display mode...",
      "ja-JP": "デフォルト壁紙表示モードを更新中..."
    }
  },
  "default_display_mode_updated": {
    "default": {
      "zh-CN": "默认壁纸显示模式已更新。",
      "en-US": "Default wallpaper display mode updated.",
      "ja-JP": "デフォルト壁紙表示モードが更新されました。"
    }
  },
  "uploading_default_wallpaper": {
    "default": {
      "zh-CN": "正在上传默认壁纸...",
      "en-US": "Uploading default wallpaper...",
      "ja-JP": "デフォルト壁紙をアップロード中..."
    }
  },
  "default_wallpaper_updated": {
    "default": {
      "zh-CN": "默认壁纸已更新，所有展板将使用新壁纸。",
      "en-US": "Default wallpaper updated. All boards will use the new wallpaper.",
      "ja-JP": "デフォルト壁紙が更新されました。すべてのボードが新しい壁紙を使用します。"
    }
  },
  "uploading_board_wallpaper": {
    "default": {
      "zh-CN": "正在上传展板壁纸...",
      "en-US": "Uploading board wallpaper...",
      "ja-JP": "ボード壁紙をアップロード中..."
    }
  },
  "board_wallpaper_applied": {
    "default": {
      "zh-CN": "展板壁纸上传并已应用。",
      "en-US": "Board wallpaper uploaded and applied.",
      "ja-JP": "ボード壁紙がアップロードされ、適用されました。"
    }
  },
  "board_wallpaper_uploaded": {
    "default": {
      "zh-CN": "展板壁纸上传成功，请从列表中手动选择。",
      "en-US": "Board wallpaper uploaded successfully. Please select manually from the list.",
      "ja-JP": "ボード壁紙が正常にアップロードされました。リストから手動で選択してください。"
    }
  },
  "board_wallpaper_applied_msg": {
    "default": {
      "zh-CN": "已应用展板专属壁纸。",
      "en-US": "Board custom wallpaper applied.",
      "ja-JP": "ボード専用壁紙が適用されました。"
    }
  },
  "restored_default_wallpaper": {
    "default": {
      "zh-CN": "已恢复使用全局默认壁纸。",
      "en-US": "Restored to global default wallpaper.",
      "ja-JP": "グローバルデフォルト壁紙に戻しました。"
    }
  },
  "personalization_settings": {
    "default": {
      "zh-CN": "个性化设置",
      "en-US": "Personalization Settings",
      "ja-JP": "個人設定"
    }
  },
  "failed_to_load_personalization": {
    "default": {
      "zh-CN": "获取个性化设置失败",
      "en-US": "Failed to load personalization settings",
      "ja-JP": "個人設定の読み込みに失敗しました"
    }
  },
  "new_project": {
    "default": {
      "zh-CN": "新建项目",
      "en-US": "New Project",
      "ja-JP": "新しいプロジェクト"
    }
  },
  "new_web_window": {
    "default": {
      "zh-CN": "新建 Web 应用窗口",
      "en-US": "New Web App Window",
      "ja-JP": "新しいWebアプリウィンドウ"
    }
  },
  "open_console": {
    "default": {
      "zh-CN": "打开控制台",
      "en-US": "Open Console",
      "ja-JP": "コンソールを開く"
    }
  },
  "plugin_manager": {
    "default": {
      "zh-CN": "插件管理器",
      "en-US": "Plugin Manager",
      "ja-JP": "プラグインマネージャー"
    }
  },
  "calendar_planner": {
    "default": {
      "zh-CN": "日历与计划",
      "en-US": "Calendar & Planner",
      "ja-JP": "カレンダーとプランナー"
    }
  },
  "message_center": {
    "default": {
      "zh-CN": "消息中心",
      "en-US": "Message Center",
      "ja-JP": "メッセージセンター"
    }
  },
  "window_type_text": {
    "default": {
      "zh-CN": "文本",
      "en-US": "Text",
      "ja-JP": "テキスト"
    }
  },
  "window_type_web": {
    "default": {
      "zh-CN": "网页",
      "en-US": "Web",
      "ja-JP": "Web"
    }
  },
  "window_type_image": {
    "default": {
      "zh-CN": "图片",
      "en-US": "Image",
      "ja-JP": "画像"
    }
  },
  "window_type_video": {
    "default": {
      "zh-CN": "视频",
      "en-US": "Video",
      "ja-JP": "動画"
    }
  },
  "window_type_audio": {
    "default": {
      "zh-CN": "音频",
      "en-US": "Audio",
      "ja-JP": "オーディオ"
    }
  },
  "window_type_pdf": {
    "default": {
      "zh-CN": "PDF",
      "en-US": "PDF",
      "ja-JP": "PDF"
    }
  },
  "window_type_default": {
    "default": {
      "zh-CN": "窗口",
      "en-US": "Window",
      "ja-JP": "ウィンドウ"
    }
  },
  "new_window": {
    "default": {
      "zh-CN": "新建",
      "en-US": "New",
      "ja-JP": "新規"
    }
  },
  "unnamed_course": {
    "default": {
      "zh-CN": "未命名课程",
      "en-US": "Unnamed Course",
      "ja-JP": "無題のコース"
    }
  },
  "unnamed_board": {
    "default": {
      "zh-CN": "未命名展板",
      "en-US": "Unnamed Board",
      "ja-JP": "無題のボード"
    }
  },
  "no_courses": {
    "default": {
      "zh-CN": "暂无课程",
      "en-US": "No courses",
      "ja-JP": "コースがありません"
    }
  },
  "no_boards": {
    "default": {
      "zh-CN": "暂无展板",
      "en-US": "No boards",
      "ja-JP": "ボードがありません"
    }
  },
  "course_name_placeholder": {
    "default": {
      "zh-CN": "课程名称",
      "en-US": "Course Name",
      "ja-JP": "コース名"
    }
  },
  "board_name_placeholder": {
    "default": {
      "zh-CN": "展板名称",
      "en-US": "Board Name",
      "ja-JP": "ボード名"
    }
  },
  "ai_assistant": {
    "default": {
      "zh-CN": "LLM助手",
      "en-US": "Assistant",
      "ja-JP": "助手"
    }
  },
  "ai_assistant_chat": {
    "default": {
      "zh-CN": "LLM助手",
      "en-US": "LLM Assistant",
      "ja-JP": "LLMアシスタント"
    }
  },
  "message": {
    "default": {
      "zh-CN": "消息",
      "en-US": "Alerts",
      "ja-JP": "通知"
    }
  },
  "connected": {
    "default": {
      "zh-CN": "已连接",
      "en-US": "Connected",
      "ja-JP": "接続済み"
    }
  },
  "disconnected": {
    "default": {
      "zh-CN": "未连接",
      "en-US": "Disconnected",
      "ja-JP": "未接続"
    }
  },
  "chat_settings": {
    "default": {
      "zh-CN": "设置",
      "en-US": "Settings",
      "ja-JP": "設定"
    }
  },
  "chat_llm_api_settings": {
    "default": {
      "zh-CN": "LLM API 设置",
      "en-US": "LLM API Settings",
      "ja-JP": "LLM API設定"
    }
  },
  "chat_select_file": {
    "default": {
      "zh-CN": "文件",
      "en-US": "File",
      "ja-JP": "ファイル"
    }
  },
  "chat_select_file_title": {
    "default": {
      "zh-CN": "选择文件发送",
      "en-US": "Select File to Send",
      "ja-JP": "送信するファイルを選択"
    }
  },
  "chat_todo": {
    "default": {
      "zh-CN": "Todo",
      "en-US": "Todo",
      "ja-JP": "Todo"
    }
  },
  "chat_todo_title": {
    "default": {
      "zh-CN": "显示/隐藏任务列表",
      "en-US": "Show/Hide Todo List",
      "ja-JP": "タスクリストの表示/非表示"
    }
  },
  "chat_tools": {
    "default": {
      "zh-CN": "工具",
      "en-US": "Tools",
      "ja-JP": "ツール"
    }
  },
  "chat_tools_enabled": {
    "default": {
      "zh-CN": "工具调用已启用（AI 可以创建窗口、查询任务等）",
      "en-US": "Tool calling enabled (AI can create windows, query tasks, etc.)",
      "ja-JP": "ツール呼び出しが有効（AIがウィンドウを作成、タスクをクエリなど可能）"
    }
  },
  "chat_tools_disabled": {
    "default": {
      "zh-CN": "工具调用已禁用",
      "en-US": "Tool calling disabled",
      "ja-JP": "ツール呼び出しが無効"
    }
  },
  "chat_scroll_bottom": {
    "default": {
      "zh-CN": "底部",
      "en-US": "Bottom",
      "ja-JP": "下部"
    }
  },
  "chat_scroll_bottom_title": {
    "default": {
      "zh-CN": "滚动到最底部",
      "en-US": "Scroll to Bottom",
      "ja-JP": "最下部にスクロール"
    }
  },
  "chat_clear": {
    "default": {
      "zh-CN": "清空",
      "en-US": "Clear",
      "ja-JP": "クリア"
    }
  },
  "chat_clear_title": {
    "default": {
      "zh-CN": "清空聊天记录",
      "en-US": "Clear Chat History",
      "ja-JP": "チャット履歴をクリア"
    }
  },
  "chat_input_placeholder": {
    "default": {
      "zh-CN": "输入消息... (Enter发送，Shift+Enter换行)",
      "en-US": "Type a message... (Enter to send, Shift+Enter for new line)",
      "ja-JP": "メッセージを入力... (Enterで送信、Shift+Enterで改行)"
    }
  },
  "chat_task_progress": {
    "default": {
      "zh-CN": "任务进度 ({completed}/{total})",
      "en-US": "Task Progress ({completed}/{total})",
      "ja-JP": "タスク進捗 ({completed}/{total})"
    }
  },
  "chat_all_tasks_completed": {
    "default": {
      "zh-CN": "所有任务已完成",
      "en-US": "All tasks completed",
      "ja-JP": "すべてのタスクが完了しました"
    }
  },
  "chat_task_progress_summary": {
    "default": {
      "zh-CN": "进度：已完成 {completed}/{total}，剩余 {remaining}",
      "en-US": "Progress: {completed}/{total} completed, {remaining} remaining",
      "ja-JP": "進捗：{completed}/{total} 完了、残り {remaining}"
    }
  },
  "chat_task_completed": {
    "default": {
      "zh-CN": "✓ 完成",
      "en-US": "✓ Completed",
      "ja-JP": "✓ 完了"
    }
  },
  "chat_no_tasks": {
    "default": {
      "zh-CN": "暂无任务项",
      "en-US": "No task items",
      "ja-JP": "タスク項目はありません"
    }
  },
  "chat_task_note": {
    "default": {
      "zh-CN": "备注",
      "en-US": "Note",
      "ja-JP": "備考"
    }
  },
  "chat_task_skipped": {
    "default": {
      "zh-CN": "跳过",
      "en-US": "Skipped",
      "ja-JP": "スキップ"
    }
  },
  "chat_stop_generation": {
    "default": {
      "zh-CN": "停止生成",
      "en-US": "Stop Generation",
      "ja-JP": "生成を停止"
    }
  },
  "chat_send_message": {
    "default": {
      "zh-CN": "发送消息",
      "en-US": "Send Message",
      "ja-JP": "メッセージを送信"
    }
  },
  "chat_no_messages": {
    "default": {
      "zh-CN": "暂无消息",
      "en-US": "No messages",
      "ja-JP": "メッセージはありません"
    }
  },
  "chat_clear_all": {
    "default": {
      "zh-CN": "清空所有消息",
      "en-US": "Clear all messages",
      "ja-JP": "すべてのメッセージをクリア"
    }
  },
  "chat_no_files_in_board": {
    "default": {
      "zh-CN": "展板中暂无文件",
      "en-US": "No files in board",
      "ja-JP": "ボード内にファイルはありません"
    }
  },
  "calendar_weekday_0": {
    "default": {
      "zh-CN": "日",
      "en-US": "Sun",
      "ja-JP": "日"
    }
  },
  "calendar_weekday_1": {
    "default": {
      "zh-CN": "一",
      "en-US": "Mon",
      "ja-JP": "月"
    }
  },
  "calendar_weekday_2": {
    "default": {
      "zh-CN": "二",
      "en-US": "Tue",
      "ja-JP": "火"
    }
  },
  "calendar_weekday_3": {
    "default": {
      "zh-CN": "三",
      "en-US": "Wed",
      "ja-JP": "水"
    }
  },
  "calendar_weekday_4": {
    "default": {
      "zh-CN": "四",
      "en-US": "Thu",
      "ja-JP": "木"
    }
  },
  "calendar_weekday_5": {
    "default": {
      "zh-CN": "五",
      "en-US": "Fri",
      "ja-JP": "金"
    }
  },
  "calendar_weekday_6": {
    "default": {
      "zh-CN": "六",
      "en-US": "Sat",
      "ja-JP": "土"
    }
  },
  "calendar_prev_month": {
    "default": {
      "zh-CN": "上一月",
      "en-US": "Previous Month",
      "ja-JP": "前月"
    }
  },
  "calendar_next_month": {
    "default": {
      "zh-CN": "下一月",
      "en-US": "Next Month",
      "ja-JP": "次月"
    }
  },
  "calendar_subtitle": {
    "default": {
      "zh-CN": "快速查看当月安排",
      "en-US": "Quick view of this month's schedule",
      "ja-JP": "今月のスケジュールを簡単に表示"
    }
  },
  "calendar_back_to_today": {
    "default": {
      "zh-CN": "回到今天",
      "en-US": "Back to Today",
      "ja-JP": "今日に戻る"
    }
  },
  "calendar_footer_label": {
    "default": {
      "zh-CN": "选中日期将在右侧展示，计划功能稍后补充",
      "en-US": "Selected date will be shown on the right, planning features coming soon",
      "ja-JP": "選択した日付は右側に表示されます。計画機能は後ほど追加予定"
    }
  },
  "calendar_weekday_full_0": {
    "default": {
      "zh-CN": "星期日",
      "en-US": "Sunday",
      "ja-JP": "日曜日"
    }
  },
  "calendar_weekday_full_1": {
    "default": {
      "zh-CN": "星期一",
      "en-US": "Monday",
      "ja-JP": "月曜日"
    }
  },
  "calendar_weekday_full_2": {
    "default": {
      "zh-CN": "星期二",
      "en-US": "Tuesday",
      "ja-JP": "火曜日"
    }
  },
  "calendar_weekday_full_3": {
    "default": {
      "zh-CN": "星期三",
      "en-US": "Wednesday",
      "ja-JP": "水曜日"
    }
  },
  "calendar_weekday_full_4": {
    "default": {
      "zh-CN": "星期四",
      "en-US": "Thursday",
      "ja-JP": "木曜日"
    }
  },
  "calendar_weekday_full_5": {
    "default": {
      "zh-CN": "星期五",
      "en-US": "Friday",
      "ja-JP": "金曜日"
    }
  },
  "calendar_weekday_full_6": {
    "default": {
      "zh-CN": "星期六",
      "en-US": "Saturday",
      "ja-JP": "土曜日"
    }
  },
  "calendar_weekday_prefix": {
    "default": {
      "zh-CN": "星期",
      "en-US": "",
      "ja-JP": ""
    }
  },
  "planner_new_task_placeholder": {
    "default": {
      "zh-CN": "新增待办名称",
      "en-US": "New task name",
      "ja-JP": "新しいタスク名"
    }
  },
  "planner_add_task": {
    "default": {
      "zh-CN": "添加待办",
      "en-US": "Add Task",
      "ja-JP": "タスクを追加"
    }
  },
  "planner_no_tasks": {
    "default": {
      "zh-CN": "暂未添加待办",
      "en-US": "No tasks yet",
      "ja-JP": "タスクがまだありません"
    }
  },
  "planner_no_tasks_desc": {
    "default": {
      "zh-CN": "使用上方输入框添加新的计划事项，支持精确到分钟的开始时间。",
      "en-US": "Use the input box above to add new tasks, with start time accurate to the minute.",
      "ja-JP": "上記の入力ボックスを使用して新しいタスクを追加します。開始時刻は分単位で指定できます。"
    }
  },
  "planner_no_tasks_desc2": {
    "default": {
      "zh-CN": "勾选事项即可标记完成，完成后的待办会自动移动到列表底部。",
      "en-US": "Check items to mark as complete. Completed tasks will automatically move to the bottom of the list.",
      "ja-JP": "項目にチェックを入れると完了としてマークされます。完了したタスクは自動的にリストの下部に移動します。"
    }
  },
  "date_format_year": {
    "default": {
      "zh-CN": "年",
      "en-US": "",
      "ja-JP": "年"
    }
  },
  "date_format_month": {
    "default": {
      "zh-CN": "月",
      "en-US": "",
      "ja-JP": "月"
    }
  },
  "date_format_day": {
    "default": {
      "zh-CN": "日",
      "en-US": "",
      "ja-JP": "日"
    }
  },
  "text_upload": {
    "default": {
      "zh-CN": "上传...",
      "en-US": "Upload...",
      "ja-JP": "アップロード..."
    }
  },
  "text_edit_mode": {
    "default": {
      "zh-CN": "编辑模式",
      "en-US": "Edit Mode",
      "ja-JP": "編集モード"
    }
  },
  "text_marp_preview": {
    "default": {
      "zh-CN": "Marp 预览",
      "en-US": "Marp Preview",
      "ja-JP": "Marp プレビュー"
    }
  },
  "text_marp_previewing": {
    "default": {
      "zh-CN": "Marp 预览中",
      "en-US": "Marp Previewing",
      "ja-JP": "Marp プレビュー中"
    }
  },
  "text_marp_preview_title": {
    "default": {
      "zh-CN": "Marp 幻灯片相关功能",
      "en-US": "Marp Slide Features",
      "ja-JP": "Marp スライド関連機能"
    }
  },
  "text_switch_to_marp": {
    "default": {
      "zh-CN": "切换到 Marp 预览",
      "en-US": "Switch to Marp Preview",
      "ja-JP": "Marp プレビューに切り替え"
    }
  },
  "text_switch_to_markdown": {
    "default": {
      "zh-CN": "切换回 Markdown 预览",
      "en-US": "Switch Back to Markdown Preview",
      "ja-JP": "Markdown プレビューに戻す"
    }
  },
  "text_select_theme": {
    "default": {
      "zh-CN": "选择主题（当前：",
      "en-US": "Select Theme (Current: ",
      "ja-JP": "テーマを選択（現在："
    }
  },
  "text_marp_guide": {
    "default": {
      "zh-CN": "Marp 使用说明",
      "en-US": "Marp Usage Guide",
      "ja-JP": "Marp 使用説明"
    }
  },
  "text_or_input_url": {
    "default": {
      "zh-CN": "或输入网址:",
      "en-US": "Or Enter URL:",
      "ja-JP": "またはURLを入力："
    }
  },
  "text_url_placeholder": {
    "default": {
      "zh-CN": "例如 https://example.com",
      "en-US": "e.g. https://example.com",
      "ja-JP": "例: https://example.com"
    }
  },
  "text_open_webpage": {
    "default": {
      "zh-CN": "打开网页",
      "en-US": "Open Webpage",
      "ja-JP": "ウェブページを開く"
    }
  },
  "text_open_webpage_title": {
    "default": {
      "zh-CN": "将当前文本窗口转换为网页窗口",
      "en-US": "Convert current text window to webpage window",
      "ja-JP": "現在のテキストウィンドウをウェブページウィンドウに変換"
    }
  },
  "text_export": {
    "default": {
      "zh-CN": "导出",
      "en-US": "Export",
      "ja-JP": "エクスポート"
    }
  },
  "text_exporting": {
    "default": {
      "zh-CN": "导出中...",
      "en-US": "Exporting...",
      "ja-JP": "エクスポート中..."
    }
  },
  "text_export_markdown_pdf": {
    "default": {
      "zh-CN": "导出 Markdown PDF",
      "en-US": "Export Markdown PDF",
      "ja-JP": "Markdown PDFをエクスポート"
    }
  },
  "text_export_marp_pdf": {
    "default": {
      "zh-CN": "导出 Marp PDF",
      "en-US": "Export Marp PDF",
      "ja-JP": "Marp PDFをエクスポート"
    }
  },
  "text_export_marp_ppt": {
    "default": {
      "zh-CN": "导出 Marp PPT",
      "en-US": "Export Marp PPT",
      "ja-JP": "Marp PPTをエクスポート"
    }
  },
  "text_markdown_placeholder": {
    "default": {
      "zh-CN": "在这里输入 Markdown 内容...",
      "en-US": "Enter Markdown content here...",
      "ja-JP": "ここにMarkdownコンテンツを入力..."
    }
  },
  "text_empty_content": {
    "default": {
      "zh-CN": "内容为空或尚未渲染",
      "en-US": "Content is empty or not yet rendered",
      "ja-JP": "コンテンツが空またはまだレンダリングされていません"
    }
  },
  "text_loading_marp": {
    "default": {
      "zh-CN": "正在加载 Marp 组件...",
      "en-US": "Loading Marp component...",
      "ja-JP": "Marpコンポーネントを読み込み中..."
    }
  },
  "text_marp_guide_desc": {
    "default": {
      "zh-CN": "Marp 能将 Markdown 转换成幻灯片。开启预览会自动插入需要的 front-matter（`marp: true`、`theme: ...`），也可以手动编辑。",
      "en-US": "Marp converts Markdown into slides. Enabling preview will automatically insert the required front-matter (`marp: true`, `theme: ...`), or you can edit it manually.",
      "ja-JP": "MarpはMarkdownをスライドに変換します。プレビューを有効にすると、必要なfront-matter（`marp: true`、`theme: ...`）が自動的に挿入されます。手動で編集することもできます。"
    }
  },
  "text_marp_guide_item1": {
    "default": {
      "zh-CN": "使用 `---` 分隔每一页。",
      "en-US": "Use `---` to separate each page.",
      "ja-JP": "`---`を使用して各ページを区切ります。"
    }
  },
  "text_marp_guide_item2": {
    "default": {
      "zh-CN": "在 front-matter 中设置 `theme:` 即可指定主题。",
      "en-US": "Set `theme:` in the front-matter to specify a theme.",
      "ja-JP": "front-matterで`theme:`を設定するとテーマを指定できます。"
    }
  },
  "text_marp_guide_item3": {
    "default": {
      "zh-CN": "导出按钮可生成 PDF / PPT。导出前用预览检查样式。",
      "en-US": "Export buttons can generate PDF / PPT. Check the style with preview before exporting.",
      "ja-JP": "エクスポートボタンでPDF / PPTを生成できます。エクスポート前にプレビューでスタイルを確認してください。"
    }
  },
  "text_marp_frontmatter_detected": {
    "default": {
      "zh-CN": "已检测到 marp front-matter。",
      "en-US": "Marp front-matter detected.",
      "ja-JP": "marp front-matterが検出されました。"
    }
  },
  "text_marp_frontmatter_not_detected": {
    "default": {
      "zh-CN": "尚未检测到 marp front-matter，切换到预览后会自动添加。",
      "en-US": "Marp front-matter not detected yet. It will be automatically added when switching to preview.",
      "ja-JP": "marp front-matterがまだ検出されていません。プレビューに切り替えると自動的に追加されます。"
    }
  },
  "text_marp_custom_theme": {
    "default": {
      "zh-CN": "当前正在使用自定义主题：",
      "en-US": "Currently using custom theme: ",
      "ja-JP": "現在、カスタムテーマを使用中："
    }
  },
  "text_export_no_markdown": {
    "default": {
      "zh-CN": "当前没有可导出的 Markdown 内容。",
      "en-US": "No Markdown content available for export.",
      "ja-JP": "エクスポート可能なMarkdownコンテンツがありません。"
    }
  },
  "text_export_no_content": {
    "default": {
      "zh-CN": "当前没有可导出的内容。",
      "en-US": "No content available for export.",
      "ja-JP": "エクスポート可能なコンテンツがありません。"
    }
  },
  "text_export_markdown_pdf_error": {
    "default": {
      "zh-CN": "导出 Markdown PDF 失败：",
      "en-US": "Failed to export Markdown PDF: ",
      "ja-JP": "Markdown PDFのエクスポートに失敗しました："
    }
  },
  "text_export_marp_pdf_error": {
    "default": {
      "zh-CN": "导出 Marp PDF 失败：",
      "en-US": "Failed to export Marp PDF: ",
      "ja-JP": "Marp PDFのエクスポートに失敗しました："
    }
  },
  "text_export_marp_ppt_error": {
    "default": {
      "zh-CN": "导出 Marp PPT 失败：",
      "en-US": "Failed to export Marp PPT: ",
      "ja-JP": "Marp PPTのエクスポートに失敗しました："
    }
  },
  "text_export_marp_empty_error": {
    "default": {
      "zh-CN": "当前内容为空，无法导出 Marp 幻灯片",
      "en-US": "Content is empty, cannot export Marp slides",
      "ja-JP": "コンテンツが空です。Marpスライドをエクスポートできません"
    }
  },
  "text_export_marp_no_slides_error": {
    "default": {
      "zh-CN": "未找到可导出的 Marp 幻灯片。",
      "en-US": "No exportable Marp slides found.",
      "ja-JP": "エクスポート可能なMarpスライドが見つかりませんでした。"
    }
  },
  "text_unknown_error": {
    "default": {
      "zh-CN": "未知错误",
      "en-US": "Unknown error",
      "ja-JP": "不明なエラー"
    }
  },
  "web_address_label": {
    "default": {
      "zh-CN": "地址:",
      "en-US": "Address:",
      "ja-JP": "アドレス："
    }
  },
  "image_text_extract": {
    "default": {
      "zh-CN": "文字提取",
      "en-US": "Text Extraction",
      "ja-JP": "文字抽出"
    }
  },
  "image_image_translate": {
    "default": {
      "zh-CN": "图片翻译",
      "en-US": "Image Translation",
      "ja-JP": "画像翻訳"
    }
  },
  "image_extracting": {
    "default": {
      "zh-CN": "提取中...",
      "en-US": "Extracting...",
      "ja-JP": "抽出中..."
    }
  },
  "image_upload_first": {
    "default": {
      "zh-CN": "请先上传图片",
      "en-US": "Please upload image first",
      "ja-JP": "まず画像をアップロードしてください"
    }
  },
  "image_requires_valid_content": {
    "default": {
      "zh-CN": "需要有效的图片内容",
      "en-US": "requires valid image content",
      "ja-JP": "有効な画像コンテンツが必要です"
    }
  },
  "image_re_extracting": {
    "default": {
      "zh-CN": "正在重新提取文字...",
      "en-US": "Re-extracting text...",
      "ja-JP": "テキストを再抽出中..."
    }
  },
  "image_please_wait": {
    "default": {
      "zh-CN": "请稍候，这可能需要几秒钟",
      "en-US": "Please wait, this may take a few seconds",
      "ja-JP": "お待ちください。数秒かかる場合があります"
    }
  },
  "image_extract_success": {
    "default": {
      "zh-CN": "文字提取成功",
      "en-US": "Text extraction successful",
      "ja-JP": "文字抽出成功"
    }
  },
  "image_click_to_view": {
    "default": {
      "zh-CN": "点击查看结果",
      "en-US": "Click to view results",
      "ja-JP": "結果を表示するにはクリック"
    }
  },
  "image_extract_failed": {
    "default": {
      "zh-CN": "提取失败",
      "en-US": "Extraction failed",
      "ja-JP": "抽出に失敗しました"
    }
  },
  "image_translating": {
    "default": {
      "zh-CN": "正在翻译...",
      "en-US": "Translating...",
      "ja-JP": "翻訳中..."
    }
  },
  "image_translate_success": {
    "default": {
      "zh-CN": "图片翻译成功",
      "en-US": "Image translation successful",
      "ja-JP": "画像翻訳成功"
    }
  },
  "image_translate_failed": {
    "default": {
      "zh-CN": "图片翻译失败",
      "en-US": "Image translation failed",
      "ja-JP": "画像翻訳に失敗しました"
    }
  },
  "image_translate_applied": {
    "default": {
      "zh-CN": "翻译层已应用到图片",
      "en-US": "Translation layer applied to image",
      "ja-JP": "翻訳レイヤーが画像に適用されました"
    }
  },
  "image_action_triggered": {
    "default": {
      "zh-CN": "已触发",
      "en-US": "Triggered",
      "ja-JP": "トリガーされました"
    }
  },
  "image_check_ai_assistant": {
    "default": {
      "zh-CN": "请在AI助手或相关工具中查看执行状态",
      "en-US": "Please check execution status in AI Assistant or related tools",
      "ja-JP": "AIアシスタントまたは関連ツールで実行状況を確認してください"
    }
  },
  "web_new_tab": {
    "default": {
      "zh-CN": "新标签页",
      "en-US": "New Tab",
      "ja-JP": "新しいタブ"
    }
  },
  "web_placeholder_instruction": {
    "default": {
      "zh-CN": "在上方输入框填写 URL，点击\"前往\"访问网页",
      "en-US": "Enter URL in the input box above and click 'Go' to visit the webpage",
      "ja-JP": "上の入力ボックスにURLを入力し、「移動」をクリックしてウェブページにアクセス"
    }
  },
  "web_url_placeholder_full": {
    "default": {
      "zh-CN": "输入网页链接，例如 https://example.com",
      "en-US": "Enter webpage URL, e.g. https://example.com",
      "ja-JP": "ウェブページのURLを入力してください。例: https://example.com"
    }
  },
  "text_url_placeholder_simple": {
    "default": {
      "zh-CN": "例: https://example.com",
      "en-US": "e.g. https://example.com",
      "ja-JP": "例: https://example.com"
    }
  },
  "new_web_app_window": {
    "default": {
      "zh-CN": "新建 Web 应用窗口",
      "en-US": "New Web App Window",
      "ja-JP": "新しいWebアプリウィンドウ"
    }
  },
  "shortcut_settings": {
    "default": {
      "zh-CN": "快捷键设置...",
      "en-US": "Shortcut Settings...",
      "ja-JP": "ショートカット設定..."
    }
  },
  // PDF Viewer
  "pdf_pagination_mode": {
    "default": {
      "zh-CN": "分页模式",
      "en-US": "Pagination Mode",
      "ja-JP": "ページ表示モード"
    }
  },
  "pdf_placeholder_title": {
    "default": {
      "zh-CN": "📄 PDF内容",
      "en-US": "📄 PDF Content",
      "ja-JP": "📄 PDFコンテンツ"
    }
  },
  "pdf_placeholder_desc": {
    "default": {
      "zh-CN": "点击上传PDF",
      "en-US": "Click to upload PDF",
      "ja-JP": "クリックしてPDFをアップロード"
    }
  },
  "pdf_page_prefix": {
    "default": {
      "zh-CN": "第",
      "en-US": "Page",
      "ja-JP": "第"
    }
  },
  "pdf_page_suffix": {
    "default": {
      "zh-CN": "页，共 {total} 页",
      "en-US": "of {total}",
      "ja-JP": " / {total} 頁"
    }
  },
  "pdf_zoom_reset": {
    "default": {
      "zh-CN": "重置",
      "en-US": "Reset",
      "ja-JP": "リセット"
    }
  },
  "pdf_extract_progress": {
    "default": {
      "zh-CN": "正在提取: {current} / {total} 页",
      "en-US": "Extracting: {current} / {total} pages",
      "ja-JP": "抽出中: {current} / {total} 頁"
    }
  },
  "pdf_extract_select_pages": {
    "default": {
      "zh-CN": "页面选择:",
      "en-US": "Select Pages:",
      "ja-JP": "頁選択:"
    }
  },
  "pdf_extract_selected_count": {
    "default": {
      "zh-CN": "选择中: {count} 页",
      "en-US": "Selected: {count} pages",
      "ja-JP": "選択中: {count} 頁"
    }
  },
  "pdf_extract_start_btn": {
    "default": {
      "zh-CN": "抽出开始 ({count} 页)",
      "en-US": "Start Extraction ({count} pages)",
      "ja-JP": "抽出開始 ({count} 頁)"
    }
  },
  "pdf_extract_complete": {
    "default": {
      "zh-CN": "✅ 页面内容提取完成",
      "en-US": "✅ Page extraction complete",
      "ja-JP": "✅ 頁内容の抽出完了"
    }
  },
  "pdf_extract_complete_errors": {
    "default": {
      "zh-CN": "⚠️ 页面内容提取完成（部分错误）",
      "en-US": "✅ Page extraction complete (with errors)",
      "ja-JP": "⚠️ 頁内容の抽出完了（一部エラー）"
    }
  },
  "pdf_extract_compare_title": {
    "default": {
      "zh-CN": "📄 第 {page} 页提取结果对比",
      "en-US": "📄 Comparison for Page {page}",
      "ja-JP": "📄 {page} 頁の抽出結果比較"
    }
  },
  "pdf_extract_load_fail": {
    "default": {
      "zh-CN": "无法读取该页面的提取内容",
      "en-US": "Failed to load extraction for this page",
      "ja-JP": "この頁の抽出内容を読み込めません"
    }
  },
  "pdf_extract_no_content": {
    "default": {
      "zh-CN": "该页面暂无保存的提取内容",
      "en-US": "No saved extraction for this page",
      "ja-JP": "この頁に保存された抽出内容はありません"
    }
  },
  "pdf_outline": {
    "default": {
      "zh-CN": "大纲",
      "en-US": "Outline",
      "ja-JP": "アウトライン"
    }
  },
  "pdf_hide_outline": {
    "default": {
      "zh-CN": "隐藏大纲",
      "en-US": "Hide Outline",
      "ja-JP": "アウトラインを隠す"
    }
  },
  "pdf_show_outline": {
    "default": {
      "zh-CN": "显示大纲",
      "en-US": "Show Outline",
      "ja-JP": "アウトラインを表示"
    }
  },
  "pdf_annotations": {
    "default": {
      "zh-CN": "📝 注释",
      "en-US": "📝 Annotations",
      "ja-JP": "📝 注釈"
    }
  },
  "pdf_hide_annotations": {
    "default": {
      "zh-CN": "隐藏注释",
      "en-US": "Hide Annotations",
      "ja-JP": "注釈を隠す"
    }
  },
  "pdf_show_annotations": {
    "default": {
      "zh-CN": "显示注释",
      "en-US": "Show Annotations",
      "ja-JP": "注釈を表示"
    }
  },
  "pdf_search": {
    "default": {
      "zh-CN": "搜索",
      "en-US": "Search",
      "ja-JP": "検索"
    }
  },
  "pdf_hide_search": {
    "default": {
      "zh-CN": "隐藏搜索",
      "en-US": "Hide Search",
      "ja-JP": "検索を隠す"
    }
  },
  "pdf_semantic_search": {
    "default": {
      "zh-CN": "语义搜索",
      "en-US": "Semantic Search",
      "ja-JP": "セマンティック検索"
    }
  },
  "pdf_extract": {
    "default": {
      "zh-CN": "提取",
      "en-US": "Extract",
      "ja-JP": "抽出"
    }
  },
  "pdf_hide_extract": {
    "default": {
      "zh-CN": "隐藏提取面板",
      "en-US": "Hide Extraction",
      "ja-JP": "抽出パネルを隠す"
    }
  },
  "pdf_show_extract": {
    "default": {
      "zh-CN": "提取页面内容",
      "en-US": "Extract Page Content",
      "ja-JP": "ページ内容を抽出"
    }
  },
  "pdf_close_pagination": {
    "default": {
      "zh-CN": "关闭分页",
      "en-US": "Close Pagination",
      "ja-JP": "ページ表示を閉じる"
    }
  },
  "pdf_page_translate": {
    "default": {
      "zh-CN": "页面翻译",
      "en-US": "Page Translate",
      "ja-JP": "ページ翻訳"
    }
  },
  "pdf_translating": {
    "default": {
      "zh-CN": "正在翻译页面...",
      "en-US": "Translating page...",
      "ja-JP": "ページを翻訳中..."
    }
  },
  "pdf_show_original": {
    "default": {
      "zh-CN": "显示原文",
      "en-US": "Show Original",
      "ja-JP": "原文を表示"
    }
  },
  "pdf_page_translate_success": {
    "default": {
      "zh-CN": "页面翻译完成",
      "en-US": "Page translation complete",
      "ja-JP": "ページ翻訳完了"
    }
  },
  "pdf_translate_applied": {
    "default": {
      "zh-CN": "翻译层已覆盖到当前页",
      "en-US": "Translation layer applied to current page",
      "ja-JP": "翻訳レイヤーが現在のページに適用されました"
    }
  },
  "pdf_translate_failed": {
    "default": {
      "zh-CN": "翻译失败",
      "en-US": "Translation failed",
      "ja-JP": "翻訳に失敗しました"
    }
  },
  "pdf_search_placeholder": {
    "default": {
      "zh-CN": "描述你想找的内容...",
      "en-US": "Describe what you're looking for...",
      "ja-JP": "探したい内容を入力..."
    }
  },
  "pdf_searching": {
    "default": {
      "zh-CN": "搜索中...",
      "en-US": "Searching...",
      "ja-JP": "検索中..."
    }
  },
  "pdf_search_btn": {
    "default": {
      "zh-CN": "搜索",
      "en-US": "Search",
      "ja-JP": "検索"
    }
  },
  "pdf_close_search": {
    "default": {
      "zh-CN": "关闭",
      "en-US": "Close",
      "ja-JP": "閉じる"
    }
  },
  "pdf_search_results_for": {
    "default": {
      "zh-CN": "搜索: \"{query}\"",
      "en-US": "Search: \"{query}\"",
      "ja-JP": "検索: \"{query}\""
    }
  },
  "pdf_back_to_history": {
    "default": {
      "zh-CN": "返回历史",
      "en-US": "Back to History",
      "ja-JP": "履歴に戻る"
    }
  },
  "pdf_no_results": {
    "default": {
      "zh-CN": "未找到相关内容",
      "en-US": "No relevant content found",
      "ja-JP": "関連する内容は見つかりませんでした"
    }
  },
  "pdf_search_history": {
    "default": {
      "zh-CN": "搜索历史",
      "en-US": "Search History",
      "ja-JP": "検索履歴"
    }
  },
  "pdf_results_count": {
    "default": {
      "zh-CN": "{count} 个结果",
      "en-US": "{count} results",
      "ja-JP": "{count} 件の結果"
    }
  },
  "pdf_extract_title": {
    "default": {
      "zh-CN": "提取页面内容",
      "en-US": "Extract Page Content",
      "ja-JP": "ページ内容の抽出"
    }
  },
  "pdf_select_pages": {
    "default": {
      "zh-CN": "选择页面:",
      "en-US": "Select Pages:",
      "ja-JP": "ページ選択:"
    }
  },
  "pdf_select_all": {
    "default": {
      "zh-CN": "全选",
      "en-US": "Select All",
      "ja-JP": "すべて選択"
    }
  },
  "pdf_select_invert": {
    "default": {
      "zh-CN": "反选",
      "en-US": "Invert Selection",
      "ja-JP": "選択反転"
    }
  },
  "pdf_select_unextracted": {
    "default": {
      "zh-CN": "未提取",
      "en-US": "Unextracted",
      "ja-JP": "未抽出"
    }
  },
  "pdf_select_clear": {
    "default": {
      "zh-CN": "清空",
      "en-US": "Clear",
      "ja-JP": "クリア"
    }
  },
  "pdf_selected_count": {
    "default": {
      "zh-CN": "已选: {count} 页",
      "en-US": "Selected: {count} pages",
      "ja-JP": "選択中: {count} ページ"
    }
  },
  "pdf_start_extract": {
    "default": {
      "zh-CN": "开始提取 ({count}页)",
      "en-US": "Start Extracting ({count} pages)",
      "ja-JP": "抽出開始 ({count} ページ)"
    }
  },
  "pdf_extract_progress": {
    "default": {
      "zh-CN": "正在提取: {current} / {total} 页",
      "en-US": "Extracting: {current} / {total} pages",
      "ja-JP": "抽出中: {current} / {total} ページ"
    }
  },
  "pdf_extracting": {
    "default": {
      "zh-CN": "提取中...",
      "en-US": "Extracting...",
      "ja-JP": "抽出中..."
    }
  },
  "pdf_extract_success": {
    "default": {
      "zh-CN": "✅ 页面提取完成",
      "en-US": "✅ Page extraction complete",
      "ja-JP": "✅ ページの抽出が完了しました"
    }
  },
  "pdf_extract_partial": {
    "default": {
      "zh-CN": "⚠️ 页面提取完成(含错误)",
      "en-US": "⚠️ Page extraction complete (with errors)",
      "ja-JP": "⚠️ ページの抽出が完了しました（エラーあり）"
    }
  },
  "pdf_extract_fail": {
    "default": {
      "zh-CN": "❌ 提取失败",
      "en-US": "❌ Extraction failed",
      "ja-JP": "❌ 抽出に失敗しました"
    }
  },
  "pdf_rate_limit": {
    "default": {
      "zh-CN": "❌ 限流 (429)",
      "en-US": "❌ Rate Limit (429)",
      "ja-JP": "❌ 速度制限 (429)"
    }
  },
  "pdf_network_error": {
    "default": {
      "zh-CN": "❌ 网络错误",
      "en-US": "❌ Network Error",
      "ja-JP": "❌ ネットワークエラー"
    }
  },
  "pdf_generic_error": {
    "default": {
      "zh-CN": "❌ 出错",
      "en-US": "❌ Error",
      "ja-JP": "❌ エラー"
    }
  },
  "not_rendered": {
    "default": {
      "zh-CN": "未渲染",
      "en-US": "Not Rendered",
      "ja-JP": "未レンダリング"
    }
  },
  "pdf_extracted": {
    "default": {
      "zh-CN": "已提取",
      "en-US": "Extracted",
      "ja-JP": "抽出済み"
    }
  },
  "char_unit": {
    "default": {
      "zh-CN": "字",
      "en-US": " chars",
      "ja-JP": "文字"
    }
  },
  "tip": {
    "default": {
      "zh-CN": "提示",
      "en-US": "Tip",
      "ja-JP": "ヒント"
    }
  },
  "error": {
    "default": {
      "zh-CN": "错误",
      "en-US": "Error",
      "ja-JP": "エラー"
    }
  },
  "on": {
    "default": {
      "zh-CN": "开启",
      "en-US": "On",
      "ja-JP": "オン"
    }
  },
  "off": {
    "default": {
      "zh-CN": "关闭",
      "en-US": "Off",
      "ja-JP": "オフ"
    }
  },
  "typewriter_mode": {
    "default": {
      "zh-CN": "打字机模式",
      "en-US": "Typewriter Mode",
      "ja-JP": "タイプライターモード"
    }
  },
  "failed_to_load_extracted_content": {
    "default": {
      "zh-CN": "无法加载该页面的提取内容",
      "en-US": "Failed to load extracted content for this page",
      "ja-JP": "このページの抽出内容を読み込めませんでした"
    }
  },
  "no_saved_extracted_content": {
    "default": {
      "zh-CN": "该页面没有已保存的提取内容",
      "en-US": "No saved extracted content for this page",
      "ja-JP": "このページには保存された抽出内容がありません"
    }
  },
  "pdf_note_style_detailed": {
    "default": {
      "zh-CN": "详细笔记",
      "en-US": "Detailed Notes",
      "ja-JP": "詳細ノート"
    }
  },
  "pdf_note_style_concise": {
    "default": {
      "zh-CN": "简洁摘要",
      "en-US": "Concise Summary",
      "ja-JP": "簡潔な要約"
    }
  },
  "pdf_note_style_academic": {
    "default": {
      "zh-CN": "学术综述",
      "en-US": "Academic Review",
      "ja-JP": "学術レビュー"
    }
  },
  "pdf_note_style_outline": {
    "default": {
      "zh-CN": "大纲式笔记",
      "en-US": "Outline Notes",
      "ja-JP": "アウトライン形式"
    }
  },
  "pdf_anno_style_detailed": {
    "default": {
      "zh-CN": "详细注释",
      "en-US": "Detailed Annotations",
      "ja-JP": "詳細注釈"
    }
  },
  "pdf_anno_style_simple": {
    "default": {
      "zh-CN": "简洁注释",
      "en-US": "Simple Annotations",
      "ja-JP": "簡潔な注釈"
    }
  },
  "pdf_anno_style_academic": {
    "default": {
      "zh-CN": "学术注释",
      "en-US": "Academic Annotations",
      "ja-JP": "学術的注釈"
    }
  },
  "pdf_anno_style_qanda": {
    "default": {
      "zh-CN": "问答式注释",
      "en-US": "Q&A Annotations",
      "ja-JP": "Q&A形式"
    }
  },
  "pdf_sidebar_anno_title": {
    "default": {
      "zh-CN": "第 {page} 页注释",
      "en-US": "Page {page} Annotations",
      "ja-JP": "{page} 頁注釈"
    }
  },
  "pdf_sidebar_anno_info_tooltip": {
    "default": {
      "zh-CN": "注释文件信息",
      "en-US": "Annotation File Info",
      "ja-JP": "注釈情報"
    }
  },
  "pdf_sidebar_anno_info_empty": {
    "default": {
      "zh-CN": "暂无注释文件",
      "en-US": "No annotation file",
      "ja-JP": "注釈なし"
    }
  },
  "pdf_sidebar_anno_info_details": {
    "default": {
      "zh-CN": "文件名: {filename}\n来源: {source}\n创建时间: {created}\n修改时间: {modified}\n文件大小: {size} 字节",
      "en-US": "Filename: {filename}\nSource: {source}\nCreated: {created}\nModified: {modified}\nSize: {size} bytes",
      "ja-JP": "ファイル名: {filename}\nソース: {source}\n作成: {created}\n更新: {modified}\nサイズ: {size} バイト"
    }
  },
  "pdf_sidebar_anno_llm_tooltip": {
    "default": {
      "zh-CN": "LLM智能功能",
      "en-US": "LLM Intelligent Features",
      "ja-JP": "LLM機能"
    }
  },
  "pdf_sidebar_anno_gen_btn": {
    "default": {
      "zh-CN": "生成注释",
      "en-US": "Generate Annotations",
      "ja-JP": "注釈生成"
    }
  },
  "pdf_sidebar_anno_visual_btn": {
    "default": {
      "zh-CN": "视觉生成",
      "en-US": "Visual Generation",
      "ja-JP": "視覚生成"
    }
  },
  "pdf_sidebar_anno_summary_btn": {
    "default": {
      "zh-CN": "生成全文档笔记",
      "en-US": "Generate Full Doc Notes",
      "ja-JP": "全文ノート生成"
    }
  },
  "pdf_sidebar_anno_outline_btn": {
    "default": {
      "zh-CN": "生成大纲",
      "en-US": "Generate Outline",
      "ja-JP": "大綱生成"
    }
  },
  "pdf_sidebar_anno_one_click_btn": {
    "default": {
      "zh-CN": "逐页注释",
      "en-US": "Page-by-Page Annotations",
      "ja-JP": "逐次注釈"
    }
  },
  "pdf_sidebar_anno_one_click_title": {
    "default": {
      "zh-CN": "逐页注释提示",
      "en-US": "Page-by-Page Annotations Info",
      "ja-JP": "逐次注釈ヒント"
    }
  },
  "pdf_sidebar_anno_one_click_msg": {
    "default": {
      "zh-CN": "检测到文档共约 {pages} 页。\n\n逐页注释功能将自动执行以下操作：\n  1. 生成文档大纲\n  2. 细分各个分段\n  3. 为所有页面生成注释\n\n此操作将消耗大量 Token 和时间。\n估算耗时：{min} - {max} 分钟\n\n是否继续？",
      "en-US": "Detected approximately {pages} pages.\n\nPage-by-page annotations will automatically:\n  1. Generate document outline\n  2. Subdivide sections\n  3. Generate annotations for all pages\n\nThis operation consumes significant tokens and time.\nEstimated time: {min} - {max} minutes\n\nContinue?",
      "ja-JP": "ドキュメントは約 {pages} 頁です。\n\n逐次注釈機能は以下の操作を自動実行します：\n  1. ドキュメント大綱の生成\n  2. セクションの細分化\n  3. 全頁の注釈生成\n\n大量のトークンと時間を消費します。\n推定時間：{min} - {max} 分\n\n続行しますか？"
    }
  },
  "pdf_sidebar_anno_one_click_done": {
    "default": {
      "zh-CN": "✓ 逐页注释完成",
      "en-US": "✓ Page-by-Page Annotations Complete",
      "ja-JP": "✓ 逐次注釈完了"
    }
  },
  "pdf_sidebar_anno_one_click_done_merge_fail": {
    "default": {
      "zh-CN": "⚠ 逐页注释完成（融合失败）",
      "en-US": "⚠ Page-by-Page Annotations Complete (Merge Failed)",
      "ja-JP": "⚠ 逐次注釈完了（マージ失敗）"
    }
  },
  "pdf_sidebar_anno_one_click_fail": {
    "default": {
      "zh-CN": "✗ 逐页注释失败",
      "en-US": "✗ Page-by-Page Annotations Failed",
      "ja-JP": "✗ 逐次注釈失敗"
    }
  },
  "pdf_sidebar_anno_batch_count": {
    "default": {
      "zh-CN": "共生成 {count} 页注释",
      "en-US": "Generated {count} page annotations",
      "ja-JP": "合計 {count} 頁の注釈を生成"
    }
  },
  "pdf_sidebar_anno_batch_btn": {
    "default": {
      "zh-CN": "批量生成所有分段注释",
      "en-US": "Batch Generate All Section Annotations",
      "ja-JP": "全セクション注釈を一括生成"
    }
  },
  "pdf_outline_generating": {
    "default": {
      "zh-CN": "正在生成大纲...",
      "en-US": "Generating outline...",
      "ja-JP": "大綱を生成中..."
    }
  },
  "pdf_outline_subdividing": {
    "default": {
      "zh-CN": "正在细分分段...",
      "en-US": "Subdividing sections...",
      "ja-JP": "セクション細分化中..."
    }
  },
  "pdf_outline_title": {
    "default": {
      "zh-CN": "文档大纲",
      "en-US": "Document Outline",
      "ja-JP": "ドキュメント大綱"
    }
  },
  "pdf_outline_view_list": {
    "default": {
      "zh-CN": "列表视图",
      "en-US": "List View",
      "ja-JP": "一覧表示"
    }
  },
  "pdf_outline_view_mindmap": {
    "default": {
      "zh-CN": "思维导图视图",
      "en-US": "Mind Map View",
      "ja-JP": "マインドマップ"
    }
  },
  "pdf_outline_back": {
    "default": {
      "zh-CN": "返回大纲",
      "en-US": "Back to Outline",
      "ja-JP": "大綱に戻る"
    }
  },
  "pdf_outline_mindmap_hint_title": {
    "default": {
      "zh-CN": "操作提示：",
      "en-US": "Interaction Tips:",
      "ja-JP": "操作ヒント："
    }
  },
  "pdf_outline_mindmap_hint_click": {
    "default": {
      "zh-CN": "点击节点跳转到对应页面",
      "en-US": "Click node to jump to page",
      "ja-JP": "クリックで頁に移動"
    }
  },
  "pdf_outline_mindmap_hint_zoom": {
    "default": {
      "zh-CN": "滚轮缩放，中键拖拽移动画布",
      "en-US": "Scroll to zoom, middle-click drag to pan",
      "ja-JP": "スクロールで拡大縮小、中ボタンで移動"
    }
  },
  "pdf_outline_mindmap_legend": {
    "default": {
      "zh-CN": "🔵文件 🟢分段 🟣细分 ⚪页码",
      "en-US": "🔵File 🟢Section 🟣Subdiv ⚪Page",
      "ja-JP": "🔵ファイル 🟢セクション 🟣細分 ⚪頁"
    }
  },
  // PDF Narrator Plugin
  "narrator_btn": {
    "default": {
      "zh-CN": "讲解",
      "en-US": "Narrator",
      "ja-JP": "解説"
    }
  },
  "narrator_btn_title": {
    "default": {
      "zh-CN": "打开智能讲解控制台",
      "en-US": "Open Narrator Console",
      "ja-JP": "スマート解説コンソールを開く"
    }
  },
  "narrator_settings": {
    "default": {
      "zh-CN": "设置",
      "en-US": "Settings",
      "ja-JP": "設定"
    }
  },
  "narrator_back": {
    "default": {
      "zh-CN": "返回",
      "en-US": "Back",
      "ja-JP": "戻る"
    }
  },
  "narrator_prompt_label": {
    "default": {
      "zh-CN": "讲稿生成提示词 (Prompt)",
      "en-US": "Script Generation Prompt",
      "ja-JP": "講稿生成プロンプト"
    }
  },
  "narrator_reference_label": {
    "default": {
      "zh-CN": "参考音色 (Reference)",
      "en-US": "Reference Voice",
      "ja-JP": "参考音声"
    }
  },
  "lang_zh": {
    "default": {
      "zh-CN": "中文",
      "en-US": "Chinese",
      "ja-JP": "中国語"
    }
  },
  "lang_en": {
    "default": {
      "zh-CN": "英文",
      "en-US": "English",
      "ja-JP": "英語"
    }
  },
  "lang_ja": {
    "default": {
      "zh-CN": "日语",
      "en-US": "Japanese",
      "ja-JP": "日本語"
    }
  },
  "narrator_upload_ref": {
    "default": {
      "zh-CN": "上传参考音频",
      "en-US": "Upload Reference Audio",
      "ja-JP": "参考音声をアップロード"
    }
  },
  "narrator_change_ref": {
    "default": {
      "zh-CN": "更换参考音频",
      "en-US": "Change Reference Audio",
      "ja-JP": "参考音声を変更"
    }
  },
  "narrator_ref_text_placeholder": {
    "default": {
      "zh-CN": "输入参考音频的文字内容...",
      "en-US": "Enter the text content of the reference audio...",
      "ja-JP": "参考音声のテキスト内容を入力してください..."
    }
  },
  "narrator_model_label": {
    "default": {
      "zh-CN": "模型 (Model)",
      "en-US": "Model",
      "ja-JP": "モデル"
    }
  },
  "narrator_output_lang": {
    "default": {
      "zh-CN": "输出:",
      "en-US": "Output:",
      "ja-JP": "出力:"
    }
  },
  "narrator_mixed_zh": {
    "default": {
      "zh-CN": "中英混合",
      "en-US": "Mixed CH/EN",
      "ja-JP": "中英混合"
    }
  },
  "narrator_pure_en": {
    "default": {
      "zh-CN": "纯英文",
      "en-US": "Pure English",
      "ja-JP": "英語のみ"
    }
  },
  "narrator_mixed_ja": {
    "default": {
      "zh-CN": "日英混合",
      "en-US": "Mixed JA/EN",
      "ja-JP": "日英混合"
    }
  },
  "narrator_auto_lang": {
    "default": {
      "zh-CN": "自动",
      "en-US": "Auto",
      "ja-JP": "自動"
    }
  },
  "narrator_refresh_models": {
    "default": {
      "zh-CN": "刷新模型",
      "en-US": "Refresh Models",
      "ja-JP": "モデルを更新"
    }
  },
  "narrator_save_settings": {
    "default": {
      "zh-CN": "保存设置",
      "en-US": "Save Settings",
      "ja-JP": "設定を保存"
    }
  },
  "narrator_script_page": {
    "default": {
      "zh-CN": "第 {page} 页讲稿",
      "en-US": "Page {page} Script",
      "ja-JP": "{page} 頁の原稿"
    }
  },
  "narrator_back_to_player": {
    "default": {
      "zh-CN": "返回播放器",
      "en-US": "Back to Player",
      "ja-JP": "戻る"
    }
  },
  "narrator_edit_placeholder": {
    "default": {
      "zh-CN": "在此处输入或修改讲稿...",
      "en-US": "Enter or edit script here...",
      "ja-JP": "ここに原稿を入力..."
    }
  },
  "narrator_saving": {
    "default": {
      "zh-CN": "正在自动保存...",
      "en-US": "Auto-saving...",
      "ja-JP": "保存中..."
    }
  },
  "narrator_saved": {
    "default": {
      "zh-CN": "已保存",
      "en-US": "Saved",
      "ja-JP": "保存済"
    }
  },
  "narrator_click_to_play": {
    "default": {
      "zh-CN": "点击播放",
      "en-US": "Click to Play",
      "ja-JP": "クリックで再生"
    }
  },
  "narrator_no_audio": {
    "default": {
      "zh-CN": "暂无语音",
      "en-US": "No Audio",
      "ja-JP": "音声なし"
    }
  },
  "narrator_hide_subtitles": {
    "default": {
      "zh-CN": "隐藏字幕",
      "en-US": "Hide Subtitles",
      "ja-JP": "字幕を隠す"
    }
  },
  "narrator_show_subtitles": {
    "default": {
      "zh-CN": "字幕",
      "en-US": "Subtitles",
      "ja-JP": "字幕"
    }
  },
  "narrator_gen_script": {
    "default": {
      "zh-CN": "生成本页讲稿",
      "en-US": "Generate Page Script",
      "ja-JP": "本頁の原稿生成"
    }
  },
  "narrator_gen_audio": {
    "default": {
      "zh-CN": "生成本页语音",
      "en-US": "Generate Page Audio",
      "ja-JP": "本頁の音声生成"
    }
  },
  "narrator_batch_script": {
    "default": {
      "zh-CN": "生成全部讲稿",
      "en-US": "Batch Scripts",
      "ja-JP": "全頁の原稿を一括生成"
    }
  },
  "narrator_batch_audio": {
    "default": {
      "zh-CN": "生成全部语音",
      "en-US": "Batch Audio",
      "ja-JP": "全頁の音声を一括生成"
    }
  },
  "narrator_missing_script": {
    "default": {
      "zh-CN": "补全未生成讲稿",
      "en-US": "Fill Missing Scripts",
      "ja-JP": "未生成の原稿を補完"
    }
  },
  "narrator_missing_audio": {
    "default": {
      "zh-CN": "补全未生成语音",
      "en-US": "Fill Missing Audio",
      "ja-JP": "未生成の音声を補完"
    }
  },
  "narrator_prev_page": {
    "default": {
      "zh-CN": "上一页",
      "en-US": "Prev Page",
      "ja-JP": "前頁"
    }
  },
  "narrator_next_page": {
    "default": {
      "zh-CN": "下一页",
      "en-US": "Next Page",
      "ja-JP": "次頁"
    }
  },
  "narrator_mode_label": {
    "default": {
      "zh-CN": "模式:",
      "en-US": "Mode:",
      "ja-JP": "モード:"
    }
  },
  "narrator_mode_page_once": {
    "default": {
      "zh-CN": "➡️ 单页",
      "en-US": "➡️ Single Page",
      "ja-JP": "➡️ 単一頁"
    }
  },
  "narrator_mode_page_loop": {
    "default": {
      "zh-CN": "🔂 单页循环",
      "en-US": "🔂 Page Loop",
      "ja-JP": "🔂 頁ループ"
    }
  },
  "narrator_mode_doc_once": {
    "default": {
      "zh-CN": "⏩ 全文",
      "en-US": "⏩ Full Doc",
      "ja-JP": "⏩ 全文"
    }
  },
  "narrator_mode_doc_loop": {
    "default": {
      "zh-CN": "🔁 全文循环",
      "en-US": "🔁 Doc Loop",
      "ja-JP": "🔁 全文ループ"
    }
  },
  "narrator_edit": {
    "default": {
      "zh-CN": "编辑",
      "en-US": "Edit",
      "ja-JP": "編集"
    }
  },
  "narrator_close": {
    "default": {
      "zh-CN": "关闭",
      "en-US": "Close",
      "ja-JP": "閉じる"
    }
  },
  "narrator_skip_section": {
    "default": {
      "zh-CN": "跳过重复分段 {index}...",
      "en-US": "Skipping duplicate section {index}...",
      "ja-JP": "重複セクション {index} をスキップ..."
    }
  },
  "narrator_skip_completed_section": {
    "default": {
      "zh-CN": "跳过已完成分段 {title}...",
      "en-US": "Skipping completed section {title}...",
      "ja-JP": "完了セクション {title} をスキップ..."
    }
  },
  "narrator_play_pause": {
    "default": {
      "zh-CN": "播放/暂停",
      "en-US": "Play/Pause",
      "ja-JP": "再生/停止"
    }
  },
  "narrator_batch_start_script": {
    "default": {
      "zh-CN": "开始{prefix}生成讲稿...",
      "en-US": "Starting to {prefix} scripts...",
      "ja-JP": "{prefix}原稿生成を開始..."
    }
  },
  "narrator_batch_start_audio": {
    "default": {
      "zh-CN": "开始{prefix}合成语音...",
      "en-US": "Starting to {prefix} audio...",
      "ja-JP": "{prefix}音声合成を開始..."
    }
  },
  "narrator_batch_prefix_batch": {
    "default": {
      "zh-CN": "批量",
      "en-US": "batch",
      "ja-JP": "一括"
    }
  },
  "narrator_batch_prefix_fill": {
    "default": {
      "zh-CN": "补全",
      "en-US": "fill",
      "ja-JP": "補完"
    }
  },
  "narrator_preparing": {
    "default": {
      "zh-CN": "准备中...",
      "en-US": "Preparing...",
      "ja-JP": "準備中..."
    }
  },
  "narrator_analyzing_outline": {
    "default": {
      "zh-CN": "未找到文档结构，正在执行大纲分析 (1/2)...",
      "en-US": "No structure found, analyzing outline (1/2)...",
      "ja-JP": "構成が見つかりません。大綱分析中 (1/2)..."
    }
  },
  "narrator_subdividing": {
    "default": {
      "zh-CN": "正在细分文档结构 (2/2)...",
      "en-US": "Subdividing structure (2/2)...",
      "ja-JP": "構成を細分化中 (2/2)..."
    }
  },
  "narrator_generating": {
    "default": {
      "zh-CN": "正在生成: {title} [{range}] (并行处理中)...",
      "en-US": "Generating: {title} [{range}] (Parallel)...",
      "ja-JP": "生成中: {title} [{range}] (並列処理中)..."
    }
  },
  "narrator_batch_complete": {
    "default": {
      "zh-CN": "生成完成",
      "en-US": "Generation Complete",
      "ja-JP": "生成完了"
    }
  },
  "narrator_batch_missing": {
    "default": {
      "zh-CN": "完成，但缺失第 {pages} 页",
      "en-US": "Complete, but missing pages {pages}",
      "ja-JP": "完了（{pages} 頁が未生成）"
    }
  },
  "narrator_synthesizing": {
    "default": {
      "zh-CN": "正在合成第 {page} 页语音...",
      "en-US": "Synthesizing page {page} audio...",
      "ja-JP": "{page} 頁の音声を合成中..."
    }
  },
  "narrator_skipping": {
    "default": {
      "zh-CN": "跳过已存在的第 {page} 页...",
      "en-US": "Skipping existing page {page}...",
      "ja-JP": "既存の {page} 頁をスキップ..."
    }
  },
  "narrator_generating_script_status": {
    "default": {
      "zh-CN": "正在生成讲稿...",
      "en-US": "Generating script...",
      "ja-JP": "原稿生成中..."
    }
  },
  "narrator_gen_error": {
    "default": {
      "zh-CN": "生成出错: {error}",
      "en-US": "Generation error: {error}",
      "ja-JP": "生成エラー: {error}"
    }
  },
  "narrator_no_audio_alert": {
    "default": {
      "zh-CN": "当前页没有语音，无法开始演示",
      "en-US": "No audio for current page, cannot start presentation",
      "ja-JP": "音声がないため、再生できません"
    }
  },
  "narrator_status_alert": {
    "default": {
      "zh-CN": "TTS 服务状态: {status}\n{error}",
      "en-US": "TTS Service Status: {status}\n{error}",
      "ja-JP": "TTS 状態: {status}\n{error}"
    }
  },
  "narrator_conn_error": {
    "default": {
      "zh-CN": "无法连接到后端服务",
      "en-US": "Cannot connect to backend service",
      "ja-JP": "接続エラー"
    }
  },
  "narrator_upload_fail": {
    "default": {
      "zh-CN": "上传失败: {error}",
      "en-US": "Upload failed: {error}",
      "ja-JP": "アップロード失敗: {error}"
    }
  },
  "narrator_upload_error": {
    "default": {
      "zh-CN": "上传出错: {error}",
      "en-US": "Upload error: {error}",
      "ja-JP": "アップロードエラー: {error}"
    }
  },
  "narrator_gen_fail_alert": {
    "default": {
      "zh-CN": "语音生成失败: {error}",
      "en-US": "Audio generation failed: {error}",
      "ja-JP": "音声生成失敗: {error}"
    }
  },
  "narrator_switch_fail": {
    "default": {
      "zh-CN": "切换模型失败，请检查后端连接",
      "en-US": "Failed to switch model, check backend connection",
      "ja-JP": "模型切替失敗"
    }
  },
  "narrator_script_short": {
    "default": {
      "zh-CN": "文",
      "en-US": "Script",
      "ja-JP": "文"
    }
  },
  "narrator_audio_short": {
    "default": {
      "zh-CN": "音",
      "en-US": "Audio",
      "ja-JP": "音"
    }
  },
  "narrator_batch_script_short": {
    "default": {
      "zh-CN": "批量文",
      "en-US": "Batch Script",
      "ja-JP": "一括文"
    }
  },
  "narrator_batch_audio_short": {
    "default": {
      "zh-CN": "批量音",
      "en-US": "Batch Audio",
      "ja-JP": "一括音"
    }
  },
  "narrator_fill_short": {
    "default": {
      "zh-CN": "补全",
      "en-US": "Fill",
      "ja-JP": "補完"
    }
  },
  "shortcut_settings": {
    "default": {
      "zh-CN": "快捷键设置...",
      "en-US": "Shortcut Settings...",
      "ja-JP": "ショートカット設定..."
    }
  },
  "pdf_summary_prompt_detailed": {
    "default": {
      "zh-CN": "你是一位专业的学术和文档分析助手。请仔细阅读以下PDF文档的全部内容，生成一份详尽的、结构清晰的**全文档阅读笔记**。\n\n**笔记生成要求**：\n1. **核心观点提炼**：首先用简练的语言概括文档的核心主旨（Executive Summary）。\n2. **结构化内容梳理**：按照文档的逻辑结构（章节或主题），详细记录关键信息、重要数据、论点和结论。请保留足够的细节，不要只是列大纲。\n3. **重要概念解析**：解释文档中出现的关键术语和概念。\n4. **总结与启示**：总结文档的价值，并给出你的阅读心得或批判性思考。\n5. **格式要求**：使用标准Markdown格式，利用多级标题、列表、加粗等使笔记易于阅读。",
      "en-US": "You are a professional academic and document analysis assistant. Please read the full content of the following PDF document carefully and generate a detailed and clearly structured **full-document reading note**.\n\n**Note Generation Requirements**:\n1. **Core Viewpoint Extraction**: First, summarize the core theme of the document in concise language (Executive Summary).\n2. **Structured Content Review**: Record key information, important data, arguments, and conclusions in detail according to the document's logical structure (chapters or themes). Please keep enough details, don't just list an outline.\n3. **Important Concept Analysis**: Explain key terms and concepts appearing in the document.\n4. **Summary and Insights**: Summarize the value of the document and give your reading reflections or critical thinking.\n5. **Formatting Requirements**: Use standard Markdown format, utilizing multi-level headings, lists, bolding, etc., to make the notes easy to read.",
      "ja-JP": "専門的な学術およびドキュメント分析アシスタントとして、以下のPDFドキュメントの全内容を注意深く読み、詳細で構造の明確な**全文読解ノート**を作成してください。\n\n**ノート作成要件**：\n1. **核心概念の抽出**：ドキュメントの核心を簡潔な言葉で概説してください（エグゼクティブサマリー）。\n2. **構造的な内容整理**：ドキュメントの論理構造（章またはテーマ）に従い、主要な情報、重要なデータ、論点、結論を詳細に記録してください。アウトラインだけでなく、十分な詳細を含めてください。\n3. **重要用語の解析**：ドキュメントに登場する主要な用語や概念を解説してください。\n4. **要約と考察**：ドキュメントの价值をまとめ、あなたの読書感想や批判的思考を述べてください。\n5. **書式要件**：標準的なMarkdown形式を使用し、多階層の見出し、リスト、太字などを活用して読みやすくしてください。"
    }
  },
  "pdf_summary_prompt_concise": {
    "default": {
      "zh-CN": "请阅读文档内容，生成一份**简洁的摘要笔记**。\n\n**要求**：\n1. 提炼核心论点，忽略次要细节。\n2. 使用要点列表（Bullet points）形式呈现。\n3. 控制篇幅，专注于“文档讲了什么”和“主要结论是什么”。\n4. 适合快速浏览。",
      "en-US": "Please read the document content and generate a **concise summary note**.\n\n**Requirements**:\n1. Extract core arguments and ignore secondary details.\n2. Present in bullet point format.\n3. Control length, focusing on 'what the document says' and 'what the main conclusion is'.\n4. Suitable for quick scanning.",
      "ja-JP": "ドキュメントの内容を読み、**簡潔な要約ノート**を作成してください。\n\n**要件**：\n1. 核心となる論点を抽出し、細かな詳細は省略してください。\n2. 箇条書き（ブレットポイント）形式で提示してください。\n3. ドキュメントの内容と主要な結論に焦点を当て、分量を抑えてください。\n4. 素早い閲覧に適した形式にしてください。"
    }
  },
  "pdf_summary_prompt_academic": {
    "default": {
      "zh-CN": "请以**学术综述**的风格撰写这份文档的笔记。\n\n**要求**：\n1. **背景与问题**：文档研究了什么问题？背景是什么？\n2. **方法与论证**：作者使用了什么方法或论据？\n3. **主要发现**：得出了什么结论？\n4. **学术价值**：该文档在相关领域的贡献是什么？\n5. **引用与术语**：准确引用文中的专业术语。",
      "en-US": "Please write a note for this document in the style of an **academic review**.\n\n**Requirements**:\n1. **Background and Problem**: What problem does the document research? What is the background?\n2. **Method and Argument**: What methods or arguments did the author use?\n3. **Main Findings**: What conclusions were reached?\n4. **Academic Value**: What is the contribution of this document to related fields?\n5. **Citations and Terminology**: Accurately cite professional terms in the text.",
      "ja-JP": "**学術的レビュー**のスタイルでこのドキュメントのノートを作成してください。\n\n**要件**：\n1. **背景と課題**：ドキュメントは何を研究していますか？背景は何ですか？\n2. **手法と立証**：著者はどのような手法や論拠を使用しましたか？\n3. **主な発見**：どのような結論が得られましたか？\n4. **学術的価値**：関連分野におけるこのドキュメントの貢献は何ですか？\n5. **引用と用語**：文中の専門用語を正確に引用してください。"
    }
  },
  "pdf_summary_prompt_outline": {
    "default": {
      "zh-CN": "请为这份文档生成一份**大纲式笔记**。\n\n**要求**：\n1. 严格遵循文档的目录结构。\n2. 在每个层级下，用简短的句子概括该部分的内容。\n3. 重点展示文档的逻辑框架和层次关系。\n4. 适合梳理文档结构。",
      "en-US": "Please generate an **outline-style note** for this document.\n\n**Requirements**:\n1. Strictly follow the document's table of contents structure.\n2. Summarize the content of each section with short sentences under each level.\n3. Focus on showing the document's logical framework and hierarchical relationships.\n4. Suitable for organizing document structure.",
      "ja-JP": "このドキュメントの**アウトライン形式ノート**を作成してください。\n\n**要件**：\n1. ドキュメントの目次構造に厳密に従ってください。\n2. 各階層で、そのセクションの内容を短い文章で概説してください。\n3. ドキュメントの論理的な枠組みと階層関係を重点的に示してください。\n4. 構成の整理に適した形式にしてください。"
    }
  },
  "pdf_anno_prompt_detailed": {
    "default": {
      "zh-CN": "请为第{page}页生成详细的注释，包括：\n1. 页面主要内容概要\n2. 重要知识点详解\n3. 需要注意的细节\n4. 相关概念说明\n\n请用Markdown格式输出。",
      "en-US": "Please generate a detailed annotation for page {page}, including:\n1. Summary of main content\n2. Detailed explanation of important knowledge points\n3. Details to note\n4. Explanation of related concepts\n\nPlease output in Markdown format.",
      "ja-JP": "{page} 頁の詳細な注釈を作成してください。内容は以下を含みます：\n1. 主要な内容の概要\n2. 重要な知識点の詳細解説\n3. 注意すべき詳細事項\n4. 関連概念の説明\n\nMarkdown形式で出力してください。"
    }
  },
  "pdf_anno_prompt_simple": {
    "default": {
      "zh-CN": "请为第{page}页生成简洁的注释，只包括：\n1. 核心内容概括（1-2句话）\n2. 关键知识点（列表形式）\n\n请用Markdown格式输出。",
      "en-US": "Please generate a concise annotation for page {page}, including only:\n1. Core content summary (1-2 sentences)\n2. Key knowledge points (list format)\n\nPlease output in Markdown format.",
      "ja-JP": "{page} 頁の簡潔な注釈を作成してください。内容は以下のみとします：\n1. 核心内容の概説（1〜2文）\n2. 主要な知識点（リスト形式）\n\nMarkdown形式で出力してください。"
    }
  },
  "pdf_anno_prompt_academic": {
    "default": {
      "zh-CN": "请为第{page}页生成学术风格的注释，包括：\n1. 内容摘要\n2. 主要论点和证据\n3. 方法论说明\n4. 关键术语解释\n\n请用Markdown格式输出。",
      "en-US": "Please generate an academic-style annotation for page {page}, including:\n1. Content summary\n2. Main arguments and evidence\n3. Methodological explanation\n4. Explanation of key terms\n\nPlease output in Markdown format.",
      "ja-JP": "{page} 頁の学術的スタイルの注釈を作成してください。内容は以下を含みます：\n1. 内容の要約\n2. 主要な論点と根拠\n3. 手法の説明\n4. 主要用語の解説\n\nMarkdown形式で出力してください。"
    }
  },
  "pdf_anno_prompt_qanda": {
    "default": {
      "zh-CN": "请为第{page}页生成问答式注释：\n1. 这页讲了什么？\n2. 核心概念是什么？\n3. 需要记住什么？\n4. 如何应用？\n\n请用Markdown格式输出。",
      "en-US": "Please generate a Q&A style annotation for page {page}:\n1. What does this page say?\n2. What are the core concepts?\n3. What needs to be remembered?\n4. How to apply it?\n\nPlease output in Markdown format.",
      "ja-JP": "{page} 頁のQ&A形式の注釈を作成してください：\n1. この頁は何について述べていますか？\n2. 核心となる概念は何ですか？\n3. 何を覚える必要がありますか？\n4. どのように応用できますか？\n\nMarkdown形式で出力してください。"
    }
  },
  "toast_success": {
    "default": {
      "zh-CN": "操作成功",
      "en-US": "Success",
      "ja-JP": "成功"
    }
  },
  "toast_error": {
    "default": {
      "zh-CN": "操作失败",
      "en-US": "Failed",
      "ja-JP": "失敗"
    }
  },
  "toast_info": {
    "default": {
      "zh-CN": "提示",
      "en-US": "Info",
      "ja-JP": "情報"
    }
  },
  "delete_course_title": {
    "default": {
      "zh-CN": "删除课程",
      "en-US": "Delete Course",
      "ja-JP": "コース削除"
    }
  },
  "delete_board_title": {
    "default": {
      "zh-CN": "删除展板",
      "en-US": "Delete Board",
      "ja-JP": "ボード削除"
    }
  },
  "delete_course_confirm": {
    "default": {
      "zh-CN": "确定要删除课程 \"{name}\" 吗？这会删除该课程下的所有展板和文件！",
      "en-US": "Are you sure you want to delete course \"{name}\"? This will delete all boards and files under this course!",
      "ja-JP": "コース \"{name}\" を削除してもよろしいですか？このコース内のすべてのボードとファイルが削除されます。"
    }
  },
  "delete_board_confirm": {
    "default": {
      "zh-CN": "确定要删除展板 \"{name}\" 吗？",
      "en-US": "Are you sure you want to delete board \"{name}\"?",
      "ja-JP": "ボード \"{name}\" を削除してもよろしいですか？"
    }
  },
  "delete_success": {
    "default": {
      "zh-CN": "删除成功",
      "en-US": "Deleted successfully",
      "ja-JP": "削除しました"
    }
  },
  "delete_fail": {
    "default": {
      "zh-CN": "删除失败",
      "en-US": "Deletion failed",
      "ja-JP": "削除に失敗しました"
    }
  },
  "network_error": {
    "default": {
      "zh-CN": "操作失败，请检查网络",
      "en-US": "Action failed, please check network",
      "ja-JP": "ネットワークを確認してください"
    }
  },
  "byte_unit": {
    "default": {
      "zh-CN": "字节",
      "en-US": "Bytes",
      "ja-JP": "バイト"
    }
  },
  "pdf_note_style_detailed": {
    "default": {
      "zh-CN": "详细笔记",
      "en-US": "Detailed Note",
      "ja-JP": "詳細ノート"
    }
  },
  "pdf_note_style_concise": {
    "default": {
      "zh-CN": "简洁摘要",
      "en-US": "Concise Summary",
      "ja-JP": "簡潔な要約"
    }
  },
  "pdf_note_style_academic": {
    "default": {
      "zh-CN": "学术风格",
      "en-US": "Academic Style",
      "ja-JP": "学術的スタイル"
    }
  },
  "pdf_note_style_outline": {
    "default": {
      "zh-CN": "大纲结构",
      "en-US": "Outline Structure",
      "ja-JP": "アウトライン構造"
    }
  },
  "pdf_summary_generating": {
    "default": {
      "zh-CN": "正在生成笔记...",
      "en-US": "Generating notes...",
      "ja-JP": "ノート生成中..."
    }
  },
  "pdf_summary_analyzing_part": {
    "default": {
      "zh-CN": "正在分析第 {part} 部分...",
      "en-US": "Analyzing part {part}...",
      "ja-JP": "第 {part} 部分を分析中..."
    }
  },
  "pdf_summary_merging": {
    "default": {
      "zh-CN": "所有分组分析完成，正在整合成总笔记...",
      "en-US": "All parts analyzed, merging into final note...",
      "ja-JP": "全セクションの分析が完了しました。最終ノートに統合中..."
    }
  },
  "pdf_summary_small_file": {
    "default": {
      "zh-CN": "文件较小，直接生成笔记中...",
      "en-US": "Small file, generating note directly...",
      "ja-JP": "ファイルが小さいため、直接ノートを生成しています..."
    }
  },
  "pdf_summary_large_file": {
    "default": {
      "zh-CN": "文件较大，使用分组分析策略...",
      "en-US": "Large file, using grouped analysis strategy...",
      "ja-JP": "ファイルが大きいため、グループ化分析戦略を使用しています..."
    }
  },
  "pdf_summary_split_groups": {
    "default": {
      "zh-CN": "分为 {count} 组进行逐个分析...",
      "en-US": "Split into {count} groups for analysis...",
      "ja-JP": "{count} グループに分割して分析しています..."
    }
  },
  "pdf_summary_start_btn": {
    "default": {
      "zh-CN": "开始生成",
      "en-US": "Start Generating",
      "ja-JP": "生成開始"
    }
  },
  "pdf_summary_click_to_start": {
    "default": {
      "zh-CN": "点击“生成全文档笔记”开始生成",
      "en-US": "Click 'Generate Full-document Note' to start",
      "ja-JP": "「全文ノートを生成」をクリックして開始します"
    }
  },
  "pdf_summary_title": {
    "default": {
      "zh-CN": "全文档笔记",
      "en-US": "Full-document Note",
      "ja-JP": "全文ノート"
    }
  },
  "pdf_summary_settings": {
    "default": {
      "zh-CN": "全文档笔记生成设置",
      "en-US": "Full-document Note Settings",
      "ja-JP": "全文ノート生成設定"
    }
  },
  "pdf_summary_refresh": {
    "default": {
      "zh-CN": "刷新笔记内容",
      "en-US": "Refresh Note Content",
      "ja-JP": "ノート内容を更新"
    }
  },
  "pdf_summary_complete_msg": {
    "default": {
      "zh-CN": "✅ 全文档笔记生成完成",
      "en-US": "✅ Full-document note generation complete",
      "ja-JP": "✅ 全文ノートの生成が完了しました"
    }
  },
  "pdf_summary_complete_details": {
    "default": {
      "zh-CN": "已保存并加载",
      "en-US": "Saved and loaded",
      "ja-JP": "保存して読み込みました"
    }
  },
  "pdf_summary_reload_success": {
    "default": {
      "zh-CN": "全文档笔记已重新加载",
      "en-US": "Full-document note reloaded",
      "ja-JP": "全文ノートを再読み込みしました"
    }
  },
  "pdf_summary_preparing": {
    "default": {
      "zh-CN": "准备开始...",
      "en-US": "Preparing to start...",
      "ja-JP": "準備中..."
    }
  },
  "pdf_summary_complete": {
    "default": {
      "zh-CN": "生成完成",
      "en-US": "Generation complete",
      "ja-JP": "生成完了"
    }
  },
  "pdf_summary_failed": {
    "default": {
      "zh-CN": "生成失败: {error}",
      "en-US": "Generation failed: {error}",
      "ja-JP": "生成失敗: {error}"
    }
  },
  "pdf_summary_error": {
    "default": {
      "zh-CN": "错误: {error}",
      "en-US": "Error: {error}",
      "ja-JP": "エラー: {error}"
    }
  },
  "pdf_summary_no_content": {
    "default": {
      "zh-CN": "未找到笔记内容",
      "en-US": "No note content found",
      "ja-JP": "ノートの内容が見つかりません"
    }
  },
  "pdf_summary_style_label": {
    "default": {
      "zh-CN": "笔记风格:",
      "en-US": "Note Style:",
      "ja-JP": "ノートスタイル:"
    }
  },
  "pdf_summary_custom_option": {
    "default": {
      "zh-CN": "自定义...",
      "en-US": "Custom...",
      "ja-JP": "カスタム..."
    }
  },
  "pdf_summary_custom_prompt_label": {
    "default": {
      "zh-CN": "自定义提示词:",
      "en-US": "Custom Prompt:",
      "ja-JP": "カスタムプロンプト:"
    }
  },
  "pdf_summary_custom_prompt_placeholder": {
    "default": {
      "zh-CN": "请输入提示词模板...",
      "en-US": "Please enter prompt template...",
      "ja-JP": "プロンプトテンプレートを入力してください..."
    }
  },
  "pdf_summary_prompt_detailed": {
    "default": {
      "zh-CN": "你是一位专业的学术和文档分析助手。请仔细阅读以下PDF文档的全部内容，生成一份详尽的、结构清晰的**全文档阅读笔记**。\n\n**笔记生成要求**：\n1. **核心观点提炼**：首先用简练的语言概括文档的核心主旨（Executive Summary）。\n2. **结构化内容梳理**：按照文档的逻辑结构（章节或主题），详细记录关键信息、重要数据、论点和结论。请保留足够的细节，不要只是列大纲，另外，需要在重点或者细节位置提供页码，以(page XXX)的形式提供。\n3. **重要概念解析**：解释文档中出现的关键术语和概念。\n4. **总结与启示**：总结文档的价值，并给出你的阅读心得或批判性思考。\n5. **格式要求**：使用标准Markdown格式，利用多级标题、列表、加粗等使笔记易于阅读。\n\n请直接输出Markdown格式的笔记内容，不要截断，务必完整输出。",
      "en-US": "You are a professional academic and document analysis assistant. Please carefully read the entire content of the following PDF document and generate a detailed and clearly structured **full-document reading note**.\n\n**Note Generation Requirements**:\n1. **Core Insight Extraction**: First, summarize the core theme of the document in concise language (Executive Summary).\n2. **Structured Content Review**: According to the logical structure of the document (chapters or topics), record key information, important data, arguments, and conclusions in detail. Please retain enough detail, not just an outline. In addition, provide page numbers at key points or details in the format (page XXX).\n3. **Key Concept Analysis**: Explain key terms and concepts appearing in the document.\n4. **Summary & Inspiration**: Summarize the value of the document and give your reading insights or critical thinking.\n5. **Formatting Requirements**: Use standard Markdown format, utilizing multi-level headings, lists, bolding, etc., to make the notes easy to read.\n\nPlease output the note content directly in Markdown format. Do not truncate; ensure full output.",
      "ja-JP": "あなたは専門的な学術・ドキュメント分析アシスタントです。以下のPDFドキュメントの全内容を注意深く読み、詳細で構造の明確な**全文読書ノート**を生成してください。\n\n**ノート生成要件**:\n1. **核心概念の抽出**: まず、簡潔な言葉でドキュメントの核心的な主題を要約してください（エグゼクティブサマリー）。\n2. **構造化された内容の整理**: ドキュメントの論理構造（章またはトピック）に従って、主要な情報、重要なデータ、論点、結論を詳細に記録してください。十分な詳細を保持し、単なるアウトラインにならないようにしてください。また、重点や詳細箇所には (page XXX) の形式でページ番号を提供してください。\n3. **重要概念の解析**: ドキュメントに登場する主要な用語や概念を説明してください。\n4. **まとめと示唆**: ドキュメントの価値を要約し、読書後の感想や批判的思考を述べてください。\n5. **フォーマット要件**: 標準的なMarkdown形式を使用し、多段階の見出し、リスト、太字などを活用して読みやすいノートにしてください。\n\nノートの内容をMarkdown形式で直接出力してください。途中で中断せず、必ず最後まで出力してください。"
    }
  },
  "pdf_summary_prompt_concise": {
    "default": {
      "zh-CN": "请阅读文档内容，生成一份**简洁的摘要笔记**。\n\n**要求**：\n1. 提炼核心论点，忽略次要细节。\n2. 使用要点列表（Bullet points）形式呈现。\n3. 控制篇幅，专注于“文档讲了什么”和“主要结论是什么”。\n4. 适合快速浏览。",
      "en-US": "Please read the document content and generate a **concise summary note**.\n\n**Requirements**:\n1. Extract core arguments and ignore secondary details.\n2. Present in bullet point format.\n3. Control the length, focusing on 'what the document is about' and 'what the main conclusions are'.\n4. Suitable for quick browsing.",
      "ja-JP": "ドキュメントの内容を読み、**簡潔な要約ノート**を生成してください。\n\n**要件**:\n1. 核心的な論点を抽出し、些細な詳細は無視してください。\n2. 箇条書き（ブレットポイント）形式で提示してください。\n3. 分量を抑え、「ドキュメントが何を伝えているか」と「主要な結論は何か」に集中してください。\n4. 素早い閲覧に適した形式にしてください。"
    }
  },
  "pdf_summary_prompt_academic": {
    "default": {
      "zh-CN": "请以**学术综述**的风格撰写这份文档的笔记。\n\n**要求**：\n1. **背景与问题**：文档研究了什么问题？背景是什么？\n2. **方法与论证**：作者使用了什么方法或论据？\n3. **主要发现**：得出了什么结论？\n4. **学术价值**：该文档在相关领域的贡献是什么？\n5. **引用与术语**：准确引用文中的专业术语。",
      "en-US": "Please write the notes for this document in the style of an **academic review**.\n\n**Requirements**:\n1. **Background & Problem**: What problem does the document research? What is the background?\n2. **Methods & Arguments**: What methods or arguments did the author use?\n3. **Key Findings**: What conclusions were reached?\n4. **Academic Value**: What is the contribution of this document to the relevant field?\n5. **Citations & Terminology**: Accurately cite professional terms in the text.",
      "ja-JP": "**学術的レビュー**のスタイルでこのドキュメントのノートを作成してください。\n\n**要件**:\n1. **背景と問題**: ドキュメントは何の問題を研究していますか？背景は何ですか？\n2. **手法と論証**: 著者はどのような手法や論拠を使用しましたか？\n3. **主要な発見**: どのような結論が得られましたか？\n4. **学術的価値**: このドキュメントの関連分野への貢献は何ですか？\n5. **引用と用語**: 文中の専門用語を正確に引用してください。"
    }
  },
  "pdf_summary_prompt_outline": {
    "default": {
      "zh-CN": "请为这份文档生成一份**大纲式笔记**。\n\n**要求**：\n1. 严格遵循文档的目录结构。\n2. 在每个层级下，用简短的句子概括该部分的内容。\n3. 重点展示文档的逻辑框架和层次关系。\n4. 适合梳理文档结构。",
      "en-US": "Please generate an **outline-style note** for this document.\n\n**Requirements**:\n1. Strictly follow the document's table of contents structure.\n2. Summarize the content of each section with brief sentences at each level.\n3. Focus on showing the logical framework and hierarchical relationship of the document.\n4. Suitable for organizing document structure.",
      "ja-JP": "このドキュメントの**アウトライン形式のノート**を生成してください。\n\n**要件**:\n1. ドキュメントの目次構造に厳密に従ってください。\n2. 各階層の下で、そのセクションの内容を短い文章で要約してください。\n3. ドキュメントの論理的な枠組みと階層関係を重点的に示してください。\n4. ドキュメント構造の整理に適した形式にしてください。"
    }
  },
  "pdf_summary_prompt_custom": {
    "default": {
      "zh-CN": "以下是用户定义的自定义笔记风格要求，请遵循此要求生成笔记：\n\n{custom_prompt}",
      "en-US": "The following is the user-defined custom note style requirement. Please follow this requirement to generate notes:\n\n{custom_prompt}",
      "ja-JP": "以下はユーザー定義のカスタムノートスタイル要件です。この要件に従ってノートを生成してください：\n\n{custom_prompt}"
    }
  },
  "open_folder_fail": {
    "default": {
      "zh-CN": "无法打开文件夹",
      "en-US": "Failed to open folder",
      "ja-JP": "フォルダを開けません"
    }
  },
  "hotkey_next_window": {
    "default": {
      "zh-CN": "切换到下一个窗口",
      "en-US": "Switch to next window",
      "ja-JP": "次のウィンドウ"
    }
  },
  "hotkey_prev_window": {
    "default": {
      "zh-CN": "切换到上一个窗口",
      "en-US": "Switch to previous window",
      "ja-JP": "前のウィンドウ"
    }
  },
  "marp_theme_default_name": {
    "default": {
      "zh-CN": "Default 经典",
      "en-US": "Default Classic",
      "ja-JP": "標準"
    }
  },
  "marp_theme_default_desc": {
    "default": {
      "zh-CN": "Marp 默认浅色主题，适合大多数场景。",
      "en-US": "Marp default light theme, suitable for most scenarios.",
      "ja-JP": "標準的な明るいテーマです。"
    }
  },
  "marp_theme_gaia_desc": {
    "default": {
      "zh-CN": "大字号、视觉冲击更强的展示主题。",
      "en-US": "Large font, visually impactful presentation theme.",
      "ja-JP": "文字が大きく、視覚効果の高いテーマです。"
    }
  },
  "marp_theme_uncover_desc": {
    "default": {
      "zh-CN": "暗色背景，适合舞台演示的主题。",
      "en-US": "Dark background, suitable for stage presentations.",
      "ja-JP": "暗い背景のプレゼンテーション用テーマです。"
    }
  },
  "pdf_load_fail": {
    "default": {
      "zh-CN": "PDF加载失败",
      "en-US": "PDF Load Failed",
      "ja-JP": "PDF読み込み失敗"
    }
  }
};

export default translations;

