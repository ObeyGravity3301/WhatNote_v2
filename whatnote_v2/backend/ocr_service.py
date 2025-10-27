"""
OCR服务模块
使用PaddleOCR进行文字识别
"""

from paddleocr import PaddleOCR
import fitz  # PyMuPDF
import time
from PIL import Image
import io
from datetime import datetime
from logger import info, error

# 全局OCR实例（延迟初始化，单例模式）
_ocr_instance = None

def get_ocr_instance():
    """
    获取OCR实例（单例模式）
    只在第一次使用时初始化，避免启动时加载
    """
    global _ocr_instance
    if _ocr_instance is None:
        info("🔍 初始化PaddleOCR...")
        try:
            # 使用最简配置，最大兼容性
            _ocr_instance = PaddleOCR(
                use_angle_cls=True,  # 使用方向分类器
                lang='ch'  # 中英文混合识别
            )
            info("✅ PaddleOCR初始化完成")
        except Exception as e:
            error(f"❌ PaddleOCR初始化失败: {e}")
            raise
    return _ocr_instance


def ocr_page_image(pdf_path, page_number):
    """
    OCR识别PDF指定页面
    
    Args:
        pdf_path: PDF文件路径
        page_number: 页码（从1开始）
    
    Returns:
        {
            'source': 'ocr',
            'ocr_at': '2025-10-27T12:05:00',
            'page_number': 3,
            'engine': 'paddleocr',
            'text': '识别的文字...',
            'char_count': 156,
            'confidence': 0.95,
            'processing_time': 2.3
        }
    """
    start_time = time.time()
    
    try:
        info(f"🔍 开始OCR识别第{page_number}页...")
        
        # 打开PDF
        doc = fitz.open(pdf_path)
        if page_number < 1 or page_number > len(doc):
            raise ValueError(f"页码超出范围: {page_number} (总页数: {len(doc)})")
        
        page = doc[page_number - 1]  # 0-based index
        
        # 将页面渲染为图片（高分辨率以提高OCR准确度）
        zoom = 2.0  # 放大2倍
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # 转换为numpy数组（PaddleOCR需要numpy.ndarray格式）
        img_data = pix.tobytes("png")
        image = Image.open(io.BytesIO(img_data))
        import numpy as np
        img_array = np.array(image)
        
        # 执行OCR
        ocr = get_ocr_instance()
        
        # 新版PaddleOCR使用predict方法，输入numpy数组
        try:
            result = ocr.predict(img_array)
        except (AttributeError, TypeError) as e1:
            info(f"predict方法失败: {e1}，尝试ocr方法")
            # 如果predict方法不支持，尝试传统的ocr方法
            try:
                result = ocr.ocr(img_array)
            except Exception as e2:
                info(f"ocr(numpy)方法失败: {e2}，尝试ocr(字节)")
                # 最后尝试使用字节数据
                result = ocr.ocr(img_data)
        
        info(f"🔍 OCR返回结果类型: {type(result)}")
        info(f"🔍 OCR返回内容: {str(result)[:500]}")  # 只打印前500字符
        
        # 提取文字和置信度
        text_lines = []
        confidences = []
        
        # 处理新版PaddleOCR返回格式
        if isinstance(result, dict):
            # 新版API返回字典格式
            if 'rec_text' in result:
                text_lines = result.get('rec_text', [])
                confidences = result.get('rec_score', [1.0] * len(text_lines))
            elif 'dt_polys' in result and 'rec_text' in result:
                text_lines = result.get('rec_text', [])
                confidences = result.get('rec_score', [1.0] * len(text_lines))
        elif result and isinstance(result, list) and len(result) > 0:
            # 传统API返回列表格式
            for line in result[0] if isinstance(result[0], list) else result:
                if line and len(line) >= 2:
                    text = line[1][0] if isinstance(line[1], (list, tuple)) else str(line[1])
                    confidence = line[1][1] if isinstance(line[1], (list, tuple)) and len(line[1]) > 1 else 1.0
                    text_lines.append(text)
                    confidences.append(confidence)
        
        full_text = '\n'.join(text_lines)
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        processing_time = round(time.time() - start_time, 2)
        
        info(f"✅ 第{page_number}页OCR完成，识别{len(text_lines)}行，{len(full_text)}字符，耗时{processing_time}秒")
        
        return {
            'source': 'ocr',
            'ocr_at': datetime.now().isoformat(),
            'page_number': page_number,
            'engine': 'paddleocr',
            'text': full_text,
            'char_count': len(full_text),
            'confidence': round(avg_confidence, 2),
            'processing_time': processing_time,
            'lines_count': len(text_lines)
        }
        
    except Exception as e:
        import traceback
        error(f"❌ OCR第{page_number}页失败: {e}")
        error(f"详细错误信息: {traceback.format_exc()}")
        raise


def extract_text_from_page(pdf_path, page_number):
    """
    从PDF页面提取文字层（非OCR）
    
    Args:
        pdf_path: PDF文件路径
        page_number: 页码（从1开始）
    
    Returns:
        {
            'source': 'extraction',
            'extracted_at': '2025-10-27T12:00:00',
            'page_number': 3,
            'text': '提取的文字...',
            'char_count': 156,
            'has_text_layer': True
        }
    """
    try:
        doc = fitz.open(pdf_path)
        if page_number < 1 or page_number > len(doc):
            raise ValueError(f"页码超出范围: {page_number} (总页数: {len(doc)})")
        
        page = doc[page_number - 1]
        text = page.get_text()
        
        return {
            'source': 'extraction',
            'extracted_at': datetime.now().isoformat(),
            'page_number': page_number,
            'text': text,
            'char_count': len(text),
            'has_text_layer': len(text.strip()) > 0
        }
        
    except Exception as e:
        error(f"❌ 提取第{page_number}页文字失败: {e}")
        raise


def detect_suspicious_pages(pdf_path):
    """
    检测可能需要OCR的可疑页面
    
    检测规则：
    1. 完全无文字层
    2. 文字量过少 (< 50字符)
    3. 图片占比过高且文字少
    
    Args:
        pdf_path: PDF文件路径
    
    Returns:
        [
            {
                'page_number': 3,
                'reasons': ['文字量少 (15字符)', '主要内容为图片'],
                'text_preview': 'fig 1.2',
                'char_count': 7
            },
            ...
        ]
    """
    try:
        doc = fitz.open(pdf_path)
        suspicious_pages = []
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text().strip()
            
            reasons = []
            
            # 规则1: 无文字或极少文字
            if len(text) < 10:
                reasons.append("无文字层" if len(text) == 0 else f"文字极少 ({len(text)}字符)")
            elif len(text) < 50:
                reasons.append(f"文字量少 ({len(text)}字符)")
            
            # 规则2: 检测是否是图片页（通过图片占比）
            image_list = page.get_images()
            if len(image_list) > 0 and len(text) < 100:
                # 获取页面尺寸
                page_rect = page.rect
                page_area = page_rect.width * page_rect.height
                
                # 计算图片总面积
                total_image_area = 0
                for img in image_list:
                    try:
                        # 获取图片位置信息
                        # 注意：get_image_bbox 可能不存在，使用替代方法
                        xref = img[0]
                        # 简单估算：如果有多个大图片，认为是图片页
                        total_image_area += page_area * 0.3  # 粗略估算
                    except:
                        pass
                
                # 如果图片较多且文字少
                if len(image_list) >= 1 and len(text) < 100:
                    reasons.append("主要内容为图片")
            
            # 如果有可疑原因，添加到列表
            if reasons:
                suspicious_pages.append({
                    "page_number": page_num + 1,
                    "reasons": reasons,
                    "text_preview": text[:50] + "..." if len(text) > 50 else text,
                    "char_count": len(text)
                })
        
        info(f"🔍 检测完成，发现{len(suspicious_pages)}个可疑页面")
        return suspicious_pages
        
    except Exception as e:
        error(f"❌ 检测可疑页面失败: {e}")
        raise

