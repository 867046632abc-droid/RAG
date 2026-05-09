
"""
从 PDF 文件中批量提取嵌入图片，保存到指定目录。

用法：
  extractor = PdfImageExtractor(output_dir="datas/image_input", min_size=100)
  extractor.extract_pdf("path/to/file.pdf")       # 单个 PDF
  extractor.extract_directory("path/to/pdf_dir")  # 目录下所有 PDF
"""

import hashlib
import os
from pathlib import Path
from typing import List

from utils.log_utils import log

# 最小边长（像素），过滤掉 logo、分隔线等无意义小图
_DEFAULT_MIN_SIZE = 100


class PdfImageExtractor:
    """从 PDF 中提取嵌入图片并保存为 PNG/JPEG。需要：pip install PyMuPDF"""

    def __init__(self, output_dir: str = None, min_size: int = _DEFAULT_MIN_SIZE):
        if output_dir is None:
            output_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                "datas", "image_input",
            )
        self.output_dir = output_dir
        self.min_size = min_size
        self._seen_hashes: set = set()   # 跨 PDF 去重

    def _get_fitz(self):
        try:
            import fitz
            return fitz
        except ImportError:
            raise ImportError("PDF 图片提取需要 PyMuPDF：pip install PyMuPDF")

    def extract_pdf(self, pdf_path: str) -> List[str]:
        """
        提取单个 PDF 的所有嵌入图片。
        返回保存成功的图片路径列表。
        """
        fitz = self._get_fitz()
        pdf_path = str(pdf_path)
        pdf_name = Path(pdf_path).stem
        save_dir = os.path.join(self.output_dir, pdf_name)
        os.makedirs(save_dir, exist_ok=True)

        doc = fitz.open(pdf_path)
        saved, skipped_size, skipped_dup = 0, 0, 0
        saved_paths = []

        log.info(f"[PdfImageExtractor] 开始提取: {Path(pdf_path).name}（共 {len(doc)} 页）")

        for page_num, page in enumerate(doc, start=1):
            images = page.get_images(full=True)
            for img_idx, img_info in enumerate(images):
                xref = img_info[0]
                try:
                    base_image = doc.extract_image(xref)
                except Exception:
                    continue

                width  = base_image.get("width", 0)
                height = base_image.get("height", 0)

                # 过滤过小的图
                if width < self.min_size or height < self.min_size:
                    skipped_size += 1
                    continue

                img_bytes = base_image["image"]

                # 去重（跨页面、跨 PDF）
                img_hash = hashlib.md5(img_bytes).hexdigest()
                if img_hash in self._seen_hashes:
                    skipped_dup += 1
                    continue
                self._seen_hashes.add(img_hash)

                ext = base_image.get("ext", "png")
                filename = f"p{page_num:03d}_img{img_idx:02d}_{img_hash[:6]}.{ext}"
                filepath = os.path.join(save_dir, filename)

                with open(filepath, "wb") as f:
                    f.write(img_bytes)

                saved_paths.append(filepath)
                saved += 1

        doc.close()
        log.info(
            f"[PdfImageExtractor] {Path(pdf_path).name} 完成 → "
            f"保存 {saved} 张，跳过(太小) {skipped_size}，跳过(重复) {skipped_dup}"
        )
        return saved_paths

    def extract_directory(self, pdf_dir: str) -> List[str]:
        """扫描目录下所有 PDF，依次提取图片。"""
        pdf_dir = Path(pdf_dir)
        pdfs = list({p.resolve() for p in pdf_dir.glob("*") if p.suffix.lower() == ".pdf"})
        if not pdfs:
            log.warning(f"[PdfImageExtractor] 目录中未找到 PDF 文件: {pdf_dir}")
            return []

        log.info(f"[PdfImageExtractor] 共找到 {len(pdfs)} 个 PDF")
        all_paths = []
        for pdf in pdfs:
            paths = self.extract_pdf(str(pdf))
            all_paths.extend(paths)

        log.info(f"[PdfImageExtractor] 全部完成，共提取 {len(all_paths)} 张图片，保存至: {self.output_dir}")
        return all_paths


if __name__ == "__main__":
    extractor = PdfImageExtractor(
        output_dir=r"C:\Users\20661\Desktop\myproject\RAG_PROJECT\RAG_PROJECT\datas\image_input",
        min_size=100,   # 过滤掉小于 100×100 像素的图
    )

    # 单个 PDF
    # extractor.extract_pdf(r"C:\path\to\your.pdf")

    # 整个目录的 PDF
    # extractor.extract_directory(r"C:\path\to\pdf_folder")

    # 先用项目内已有的 PDF 测试一下
    extractor.extract_pdf(
        r"C:\Users\20661\Desktop\myproject\RAG_PROJECT\RAG_PROJECT\datas\layout-parser-paper.pdf"
    )
