#!/usr/bin/env python3
"""
创建默认占位文件模板
"""

from pathlib import Path

def create_template_files():
    templates_dir = Path("whatnote_v2/backend/templates")
    templates_dir.mkdir(exist_ok=True)
    
    # 创建最小的有效JPEG文件 (1x1像素，白色)
    jpeg_data = (
        b'\xFF\xD8\xFF\xE0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00'
        b'\xFF\xDB\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08'
        b'\n\x0C\x14\r\x0C\x0B\x0B\x0C\x19\x12\x13\x0F\x14\x1D\x1A\x1F\x1E'
        b'\x1D\x1A\x1C\x1C $.\' \",#\x1C\x1C(7),01444\x1F\'9=82<.342'
        b'\xFF\xC0\x00\x11\x08\x00\x01\x00\x01\x01\x01\x11\x00\x02\x11\x01'
        b'\x03\x11\x01\xFF\xC4\x00\x14\x00\x01\x00\x00\x00\x00\x00\x00\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x08\xFF\xC4\x00\x14\x10\x01\x00'
        b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'
        b'\xFF\xDA\x00\x0C\x03\x01\x00\x02\x11\x03\x11\x00\x3F\x00\xAA\xFF\xD9'
    )
    
    # 创建图片模板
    with open(templates_dir / "新建图片.jpg", "wb") as f:
        f.write(jpeg_data)
    print("创建了图片模板: 新建图片.jpg")
    
    # 创建最小的有效PNG文件 (1x1像素，透明)
    png_data = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01'
        b'\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01'
        b'\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    
    with open(templates_dir / "新建图片.png", "wb") as f:
        f.write(png_data)
    print("创建了PNG模板: 新建图片.png")
    
    # 创建文本模板
    with open(templates_dir / "新建文本.txt", "w", encoding="utf-8") as f:
        f.write("# 新建文本文档\n\n在此输入您的内容...")
    print("创建了文本模板: 新建文本.txt")
    
    # 创建视频占位文件（空文件，实际使用时会被替换）
    with open(templates_dir / "新建视频.mp4", "wb") as f:
        f.write(b"")  # 空文件，作为占位符
    print("创建了视频模板: 新建视频.mp4")
    
    # 创建音频占位文件
    with open(templates_dir / "新建音频.mp3", "wb") as f:
        f.write(b"")  # 空文件，作为占位符
    print("创建了音频模板: 新建音频.mp3")
    
    # 创建PDF占位文件
    with open(templates_dir / "新建文档.pdf", "wb") as f:
        f.write(b"")  # 空文件，作为占位符
    print("创建了PDF模板: 新建文档.pdf")
    
    print(f"\n所有模板文件已创建在: {templates_dir}")

if __name__ == "__main__":
    create_template_files()
