#!/usr/bin/env python3
"""
调试文件名生成问题
"""

from pathlib import Path

def debug_filename_generation():
    print("=== 调试文件名生成 ===\n")
    
    # 模拟上传API的逻辑
    filename = "upload_fix_test.png"
    print(f"原始文件名: {filename}")
    
    # 获取原文件名（不含扩展名）作为新的基础名称
    original_basename = Path(filename).stem
    file_extension = Path(filename).suffix
    
    print(f"原始基础名: {original_basename}")
    print(f"文件扩展名: {file_extension}")
    
    # 模拟_sanitize_filename
    def _sanitize_filename(filename: str) -> str:
        """清理文件名中的非法字符"""
        import re
        # 移除或替换非法字符
        sanitized = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 移除前后空格和点
        sanitized = sanitized.strip(' .')
        return sanitized
    
    safe_basename = _sanitize_filename(original_basename)
    print(f"安全基础名: {safe_basename}")
    
    # 模拟_generate_unique_filename
    def _generate_unique_filename(files_dir: Path, base_name: str, extension: str) -> str:
        """生成唯一的文件名"""
        # 清理文件名中的非法字符
        safe_name = _sanitize_filename(base_name)
        print(f"  _generate_unique_filename 输入:")
        print(f"    base_name: {base_name}")
        print(f"    extension: {extension}")
        print(f"    safe_name: {safe_name}")
        
        # 检查文件是否存在，如果存在则添加编号
        file_name = f"{safe_name}{extension}"
        print(f"    生成的文件名: {file_name}")
        
        if not (files_dir / file_name).exists():
            return file_name
        
        # 添加编号直到找到唯一名称
        counter = 1
        while True:
            file_name = f"{safe_name}({counter}){extension}"
            print(f"    尝试文件名: {file_name}")
            if not (files_dir / file_name).exists():
                return file_name
            counter += 1
    
    # 模拟目标目录
    target_dir = Path("whatnote_v2/backend/whatnote_data/courses/course-1756987907632/board-1756987954946/files")
    
    print(f"\n目标目录: {target_dir}")
    print(f"目录存在: {target_dir.exists()}")
    
    if target_dir.exists():
        print("目录中的文件:")
        for file_path in target_dir.iterdir():
            if file_path.is_file():
                print(f"  {file_path.name}")
    
    # 生成唯一文件名
    print(f"\n调用 _generate_unique_filename:")
    new_filename = _generate_unique_filename(target_dir, safe_basename, file_extension)
    print(f"最终生成的文件名: {new_filename}")
    
    # 检查为什么会产生.png.jpg
    print(f"\n分析.png.jpg问题:")
    if new_filename.endswith('.png.jpg'):
        print("❌ 发现重复扩展名问题!")
        print("可能的原因:")
        print("1. base_name包含了扩展名")
        print("2. extension被错误处理")
        print("3. 某个地方添加了额外的扩展名")
    else:
        print("✅ 文件名生成正确")

if __name__ == "__main__":
    debug_filename_generation()
