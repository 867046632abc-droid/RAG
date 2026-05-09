import base64
import os
import subprocess
import tempfile
from pathlib import Path
from typing import List

from langchain_core.documents import Document

from llm_models.all_llm import sora_client
from utils.log_utils import log

_FRAME_PROMPT = (
    "这是视频第 {ts} 秒处的画面，请描述画面中的技术内容，"
    "重点关注器件结构、工艺步骤、数据图表、文字信息等，使用中文回答。"
)


class VideoParser:
    """
    将视频文件解析为文字 Document 列表，供写入 Milvus。
    两路并行：
      1. 音频轨 → Whisper 转录（需要系统安装 ffmpeg）
      2. 关键帧 → GPT-4o vision 描述（每 frame_interval_sec 秒取一帧）
    依赖：pip install opencv-python  （ffmpeg 需系统级安装）
    """

    def __init__(self, frame_interval_sec: int = 30):
        self.frame_interval_sec = frame_interval_sec

    # ── 音频转录 ──────────────────────────────────────────

    def _extract_audio(self, video_path: str) -> str:
        """用 ffmpeg 从视频中提取音频，返回临时 mp3 路径。"""
        tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
        tmp.close()
        subprocess.run(
            ["ffmpeg", "-y", "-i", video_path, "-q:a", "0", "-map", "a", tmp.name],
            check=True, capture_output=True,
        )
        return tmp.name

    def _transcribe(self, audio_path: str) -> str:
        with open(audio_path, "rb") as f:
            result = sora_client.audio.transcriptions.create(
                model="whisper-1", file=f, language="zh"
            )
        return result.text.strip()

    # ── 关键帧描述 ────────────────────────────────────────

    def _extract_frames(self, video_path: str) -> List[tuple]:
        """每隔 frame_interval_sec 秒提取一帧，返回 [(timestamp_sec, base64_jpg), ...]。"""
        try:
            import cv2
        except ImportError:
            raise ImportError("视频帧提取需要 OpenCV：pip install opencv-python")

        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        interval = max(1, int(fps * self.frame_interval_sec))

        frames, idx = [], 0
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            if idx % interval == 0:
                ts = int(idx / fps)
                _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
                b64 = base64.b64encode(buf).decode("utf-8")
                frames.append((ts, b64))
            idx += 1
        cap.release()
        return frames

    def _describe_frame(self, b64: str, timestamp: int) -> str:
        resp = sora_client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                    {"type": "text", "text": _FRAME_PROMPT.format(ts=timestamp)},
                ],
            }],
            max_tokens=500,
        )
        return resp.choices[0].message.content.strip()

    # ── 主入口 ────────────────────────────────────────────

    def parse_video(self, video_path: str) -> List[Document]:
        """解析单个视频文件，返回 Document 列表。"""
        video_path = str(video_path)
        filename = Path(video_path).name
        docs = []
        base_meta = {
            "source": video_path,
            "filename": filename,
            "filetype": Path(video_path).suffix.lower(),
            "category_depth": 0,
        }

        # 1. 音频转录
        try:
            log.info(f"[VideoParser] 提取音频: {filename}")
            audio_path = self._extract_audio(video_path)
            transcript = self._transcribe(audio_path)
            os.unlink(audio_path)
            if transcript:
                docs.append(Document(
                    page_content=f"【视频音频转录】\n{transcript}",
                    metadata={**base_meta, "category": "VideoTranscript",
                               "title": f"音频转录: {filename}"},
                ))
                log.info(f"[VideoParser] 转录完成，字符数={len(transcript)}")
        except Exception as e:
            log.warning(f"[VideoParser] 音频转录跳过: {e}")

        # 2. 关键帧描述
        try:
            log.info(f"[VideoParser] 提取关键帧（每{self.frame_interval_sec}s一帧）: {filename}")
            frames = self._extract_frames(video_path)
            log.info(f"[VideoParser] 共提取 {len(frames)} 帧")
            for ts, b64 in frames:
                try:
                    desc = self._describe_frame(b64, ts)
                    docs.append(Document(
                        page_content=f"【视频画面 {ts}s】\n{desc}",
                        metadata={**base_meta, "category": "VideoFrame",
                                   "title": f"视频帧 {ts}s: {filename}"},
                    ))
                except Exception as e:
                    log.warning(f"[VideoParser] 帧描述失败 t={ts}s: {e}")
        except Exception as e:
            log.warning(f"[VideoParser] 帧提取跳过: {e}")

        log.info(f"[VideoParser] {filename} 共生成 {len(docs)} 个 Document")
        return docs

    def parse_videos(self, video_paths: List[str]) -> List[Document]:
        docs = []
        for p in video_paths:
            try:
                docs.extend(self.parse_video(p))
            except Exception as e:
                log.error(f"[VideoParser] 视频解析失败 {p}: {e}")
        return docs


if __name__ == "__main__":
    parser = VideoParser(frame_interval_sec=30)
    docs = parser.parse_video(r"C:\path\to\your\video.mp4")
    for d in docs:
        print(d.metadata["category"], d.metadata["title"])
        print(d.page_content[:200])
        print("---")
