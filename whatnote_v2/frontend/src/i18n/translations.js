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
  }
};

export default translations;

