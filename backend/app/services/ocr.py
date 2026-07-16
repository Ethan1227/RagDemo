"""证据 OCR 识别服务（PaddleOCR，中文）。

- 懒加载单例：首次调用才初始化并下载模型，避免导入期开销；测试全程 mock
- 图片(png/jpg/jpeg/bmp)：直接 OCR
- PDF：先用 pypdf 提取文本层；文本过少（扫描件）则用 pypdfium2 渲染页面转图片再 OCR
- txt：直接解码
- 同步 SDK 包装到线程池；失败显式抛错
"""
from __future__ import annotations

import asyncio
import io
import threading
from pathlib import Path

from loguru import logger

IMAGE_TYPES = {"png", "jpg", "jpeg", "bmp"}
# PDF 文本层少于该字符数，判定为扫描件走 OCR
_SCANNED_PDF_THRESHOLD = 50
# 扫描件 PDF 渲染 OCR 的最大页数（防止超大文件耗时过长）
_MAX_PDF_OCR_PAGES = 20

_ocr_engine = None
_lock = threading.Lock()


def detect_evidence_type(filename: str) -> str:
    """返回 image/pdf/txt，不支持则抛 ValueError。"""
    suffix = Path(filename).suffix.lower().lstrip(".")
    if suffix in IMAGE_TYPES:
        return "image"
    if suffix == "pdf":
        return "pdf"
    if suffix == "txt":
        return "txt"
    raise ValueError(f"不支持的证据类型：.{suffix}（支持 png/jpg/jpeg/bmp/pdf/txt）")


def _get_engine():
    """懒加载 PaddleOCR 引擎（中文，关闭方向/矫正以提速）。"""
    global _ocr_engine
    if _ocr_engine is None:
        with _lock:
            if _ocr_engine is None:
                from paddleocr import PaddleOCR

                # enable_mkldnn=False 规避 paddle 3.x OneDNN 在部分 CPU 上的
                # ConvertPirAttribute2RuntimeAttribute 未实现错误
                _ocr_engine = PaddleOCR(
                    lang="ch",
                    enable_mkldnn=False,
                    use_doc_orientation_classify=False,
                    use_doc_unwarping=False,
                    use_textline_orientation=False,
                )
                logger.info("PaddleOCR 引擎初始化完成（lang=ch）")
    return _ocr_engine


def _ocr_image_array(image_array) -> str:
    """对单张图片 ndarray 执行 OCR，返回按行拼接的文本。"""
    engine = _get_engine()
    result = engine.predict(image_array)
    lines: list[str] = []
    for page in result or []:
        # PaddleOCR 3.x：结果对象含 rec_texts 字段
        texts = page.get("rec_texts") if hasattr(page, "get") else None
        if texts:
            lines.extend(texts)
    return "\n".join(lines)


def _bytes_to_array(data: bytes):
    import numpy as np
    from PIL import Image

    image = Image.open(io.BytesIO(data)).convert("RGB")
    return np.array(image)


def _recognize_sync(filename: str, data: bytes) -> str:
    file_type = detect_evidence_type(filename)

    if file_type == "txt":
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return data.decode("gbk", errors="replace")

    if file_type == "image":
        return _ocr_image_array(_bytes_to_array(data))

    # PDF：优先文本层
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    if len(text.strip()) >= _SCANNED_PDF_THRESHOLD:
        return text

    # 扫描件：渲染页面为图片再 OCR
    logger.info("PDF 文本层过少，按扫描件渲染 OCR：{}", filename)
    import numpy as np
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(data)
    ocr_pages: list[str] = []
    for i in range(min(len(pdf), _MAX_PDF_OCR_PAGES)):
        bitmap = pdf[i].render(scale=2.0)
        pil_image = bitmap.to_pil().convert("RGB")
        ocr_pages.append(_ocr_image_array(np.array(pil_image)))
    return "\n".join(ocr_pages)


async def recognize(filename: str, data: bytes) -> str:
    """识别证据文本（异步包装）。"""
    text = await asyncio.to_thread(_recognize_sync, filename, data)
    logger.debug("OCR 完成：{}，{} 字符", filename, len(text))
    return text
