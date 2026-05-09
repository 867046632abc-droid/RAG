"""
多模态内容写入 Milvus 的统一入口。

支持的文件类型：
  图片：.jpg .jpeg .png .gif .webp .bmp
  视频：.mp4 .avi .mov .mkv .flv .wmv

用法示例：
  ingest = MultimodalIngest()

  # 写入单张图片
  ingest.ingest_image("path/to/image.png")

  # 写入单个视频（每30秒取一帧，可调整）
  ingest.ingest_video("path/to/video.mp4", frame_interval_sec=30)

  # 批量扫描目录，自动按扩展名分发
  ingest.ingest_directory("path/to/media_folder")
"""

from pathlib import Path
from typing import List

from documents.milvus_db import MilvusVectorSave
from multimodal_RAG.image_parser import ImageParser
from multimodal_RAG.video_parser import VideoParser
from utils.log_utils import log

_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}
_VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv"}


class MultimodalIngest:
    """将图片/视频解析为 Document 并写入已有 Milvus collection。"""

    def __init__(self, frame_interval_sec: int = 30):
        self._milvus = MilvusVectorSave()
        self._milvus.create_connection()
        self._image_parser = ImageParser()
        self._video_parser = VideoParser(frame_interval_sec=frame_interval_sec)

    def _write(self, docs):
        if not docs:
            log.warning("无可写入的 Document，跳过。")
            return
        self._milvus.add_documents(docs)
        log.info(f"成功写入 {len(docs)} 个 Document 到 Milvus。")

    def ingest_image(self, image_path: str):
        """解析单张图片并写入 Milvus。"""
        docs = self._image_parser.parse_image(image_path)
        self._write(docs)

    def ingest_images(self, image_paths: List[str]):
        """批量解析图片并写入 Milvus。"""
        docs = self._image_parser.parse_images(image_paths)
        self._write(docs)

    def ingest_video(self, video_path: str, frame_interval_sec: int = None):
        """解析单个视频（音频转录 + 关键帧描述）并写入 Milvus。"""
        if frame_interval_sec is not None:
            self._video_parser.frame_interval_sec = frame_interval_sec
        docs = self._video_parser.parse_video(video_path)
        self._write(docs)

    def ingest_videos(self, video_paths: List[str]):
        """批量解析视频并写入 Milvus。"""
        docs = self._video_parser.parse_videos(video_paths)
        self._write(docs)

    def ingest_directory(self, dir_path: str):
        """
        扫描目录，按扩展名自动分发到图片/视频 parser，统一写入 Milvus。
        不递归子目录。
        """
        dir_path = Path(dir_path)
        images, videos = [], []
        for f in dir_path.iterdir():
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            if ext in _IMAGE_EXTS:
                images.append(str(f))
            elif ext in _VIDEO_EXTS:
                videos.append(str(f))

        log.info(f"目录扫描完成：{len(images)} 张图片，{len(videos)} 个视频")

        docs = []
        if images:
            docs.extend(self._image_parser.parse_images(images))
        if videos:
            docs.extend(self._video_parser.parse_videos(videos))

        self._write(docs)


if __name__ == "__main__":
    ingest = MultimodalIngest(frame_interval_sec=30)

    # 单张图片
    # ingest.ingest_image(r"C:\path\to\image.png")

    # 单个视频
    # ingest.ingest_video(r"C:\path\to\video.mp4")

    # 扫描整个目录
    ingest.ingest_directory(r"C:\Users\20661\Desktop\myproject\RAG_PROJECT\RAG_PROJECT\datas\image_input")
