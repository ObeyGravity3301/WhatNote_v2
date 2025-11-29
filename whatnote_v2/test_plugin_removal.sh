#!/bin/bash

# 插件移除测试脚本
# 用于测试移除插件文件后系统是否正常工作

PLUGINS_DIR="frontend/src/plugins/core"
BACKUP_DIR="frontend/src/plugins/core.backup"
TEST_RESULTS="test_plugin_removal_results.txt"

echo "========================================="
echo "插件移除测试脚本"
echo "========================================="
echo ""

# 创建备份目录
if [ ! -d "$BACKUP_DIR" ]; then
    echo "📦 创建备份目录..."
    mkdir -p "$BACKUP_DIR"
fi

# 备份插件文件
echo "📦 备份插件文件..."
cp -r "$PLUGINS_DIR"/* "$BACKUP_DIR/" 2>/dev/null || echo "⚠️  备份目录已存在或文件不存在"

# 列出可用的插件文件
echo ""
echo "可用的插件文件:"
ls -1 "$PLUGINS_DIR"/*.js 2>/dev/null | while read file; do
    basename "$file"
done

echo ""
echo "请选择要测试的场景:"
echo "1) 移除字数统计插件 (word-count-plugin.js)"
echo "2) 移除便签窗口插件 (sticky-note-plugin.js)"
echo "3) 移除所有插件"
echo "4) 恢复所有插件"
echo "5) 切换到测试模式（使用动态 import，支持运行时加载）"
echo "6) 切换回生产模式（使用静态 import）"
echo "7) 退出"
echo ""
read -p "请输入选项 (1-7): " choice

case $choice in
    1)
        echo ""
        echo "🧪 测试场景: 移除字数统计插件"
        if [ -f "$PLUGINS_DIR/word-count-plugin.js" ]; then
            mv "$PLUGINS_DIR/word-count-plugin.js" "$BACKUP_DIR/word-count-plugin.js.backup"
            echo "✅ 已移除 word-count-plugin.js"
            echo ""
            echo "📝 请测试以下功能:"
            echo "   - 应用是否能正常启动"
            echo "   - 文本编辑器工具栏是否正常显示（不应有字数统计按钮）"
            echo "   - 插件管理器是否正常显示（字数统计插件应显示为未加载）"
            echo "   - 其他功能是否正常工作"
            echo ""
            echo "测试完成后，运行此脚本选择选项 4 恢复插件"
        else
            echo "⚠️  文件不存在或已被移除"
        fi
        ;;
    2)
        echo ""
        echo "🧪 测试场景: 移除便签窗口插件"
        if [ -f "$PLUGINS_DIR/sticky-note-plugin.js" ]; then
            mv "$PLUGINS_DIR/sticky-note-plugin.js" "$BACKUP_DIR/sticky-note-plugin.js.backup"
            echo "✅ 已移除 sticky-note-plugin.js"
            echo ""
            echo "📝 请测试以下功能:"
            echo "   - 应用是否能正常启动"
            echo "   - 桌面右键菜单是否正常（不应有创建便签选项）"
            echo "   - 插件管理器是否正常显示（便签插件应显示为未加载）"
            echo "   - 其他功能是否正常工作"
            echo ""
            echo "测试完成后，运行此脚本选择选项 4 恢复插件"
        else
            echo "⚠️  文件不存在或已被移除"
        fi
        ;;
    3)
        echo ""
        echo "🧪 测试场景: 移除所有插件"
        if [ -d "$PLUGINS_DIR" ]; then
            for file in "$PLUGINS_DIR"/*.js; do
                if [ -f "$file" ]; then
                    mv "$file" "$BACKUP_DIR/$(basename "$file").backup"
                    echo "✅ 已移除 $(basename "$file")"
                fi
            done
            echo ""
            echo "📝 请测试以下功能:"
            echo "   - 应用是否能正常启动"
            echo "   - 插件管理器是否正常显示（应显示没有插件或插件未加载）"
            echo "   - 其他核心功能是否正常工作"
            echo ""
            echo "测试完成后，运行此脚本选择选项 4 恢复插件"
        else
            echo "⚠️  插件目录不存在"
        fi
        ;;
    4)
        echo ""
        echo "🔄 恢复所有插件..."
        if [ -d "$BACKUP_DIR" ]; then
            for file in "$BACKUP_DIR"/*.backup; do
                if [ -f "$file" ]; then
                    original_name=$(basename "$file" .backup)
                    mv "$file" "$PLUGINS_DIR/$original_name"
                    echo "✅ 已恢复 $original_name"
                fi
            done
            echo ""
            echo "✅ 所有插件已恢复"
            echo "📝 请重新启动应用以加载插件"
        else
            echo "⚠️  备份目录不存在，无法恢复"
        fi
        ;;
    5)
        echo ""
        echo "🧪 切换到测试模式..."
        PLUGINS_INDEX="frontend/src/plugins/index.js"
        PLUGINS_INDEX_PROD="frontend/src/plugins/index.prod.js"
        PLUGINS_INDEX_TEST="frontend/src/plugins/index.test.js"
        
        if [ -f "$PLUGINS_INDEX_TEST" ]; then
            if [ -f "$PLUGINS_INDEX" ] && [ ! -f "$PLUGINS_INDEX_PROD" ]; then
                mv "$PLUGINS_INDEX" "$PLUGINS_INDEX_PROD"
                echo "✅ 已备份生产版本为 index.prod.js"
            fi
            cp "$PLUGINS_INDEX_TEST" "$PLUGINS_INDEX"
            echo "✅ 已切换到测试模式（动态 import）"
            echo "📝 现在可以移除插件文件进行测试，构建不会失败"
            echo "⚠️  注意：需要修改 BoardCanvas.js 中的 initializePlugins() 调用为 await initializePlugins()"
        else
            echo "❌ 测试版本文件不存在: $PLUGINS_INDEX_TEST"
        fi
        ;;
    6)
        echo ""
        echo "🔄 切换回生产模式..."
        PLUGINS_INDEX="frontend/src/plugins/index.js"
        PLUGINS_INDEX_PROD="frontend/src/plugins/index.prod.js"
        
        if [ -f "$PLUGINS_INDEX_PROD" ]; then
            mv "$PLUGINS_INDEX_PROD" "$PLUGINS_INDEX"
            echo "✅ 已恢复生产模式（静态 import）"
        else
            echo "⚠️  生产版本文件不存在，无法恢复"
        fi
        ;;
    7)
        echo "退出"
        exit 0
        ;;
    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

echo ""
echo "========================================="
echo "测试完成"
echo "========================================="

