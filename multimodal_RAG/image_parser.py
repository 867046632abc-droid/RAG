import base64
from pathlib import Path
from typing import List

from langchain_core.documents import Document

from llm_models.all_llm import sora_client
from utils.log_utils import log

_MIME = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "gif": "gif", "webp": "webp", "bmp": "jpeg"}

_DESCRIBE_PROMPT = (
    "请详细描述这张图片的内容，重点说明其中涉及的技术结构、器件示意图、"
    "工艺流程、数据图表或参数信息，使用中文回答，不少于100字。"
)


class ImageParser:
    """将图片文件通过 GPT-4o vision 转为文字 Document，供写入 Milvus。"""

    def _encode(self, image_path: str) -> tuple[str, str]:
        ext = Path(image_path).suffix.lower().lstrip(".")
        mime = _MIME.get(ext, "jpeg")
        with open(image_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("utf-8")
        return b64, mime

    def _describe(self, image_path: str) -> str:
        b64, mime = self._encode(image_path)
        resp = sora_client.chat.completions.create(
            model="gpt-4o",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image_url", "image_url": {"url": f"data:image/{mime};base64,{b64}"}},
                    {"type": "text", "text": _DESCRIBE_PROMPT},
                ],
            }],
            max_tokens=1000,
        )
        return resp.choices[0].message.content.strip()

    def parse_image(self, image_path: str) -> List[Document]:
        """解析单张图片，返回含 vision 描述的 Document 列表。"""
        image_path = str(image_path)
        filename = Path(image_path).name
        log.info(f"[ImageParser] 正在描述图片: {filename}")

        description = self._describe(image_path)
        log.info(f"[ImageParser] 描述完成，字符数={len(description)}")

        return [Document(
            page_content=description,
            metadata={
                "category": "Image",
                "source": image_path,
                "filename": filename,
                "filetype": Path(image_path).suffix.lower(),
                "title": f"图片: {filename}",
                "category_depth": 0,
            },
        )]

    def parse_images(self, image_paths: List[str]) -> List[Document]:
        docs = []
        for p in image_paths:
            try:
                docs.extend(self.parse_image(p))
            except Exception as e:
                log.error(f"[ImageParser] 图片解析失败 {p}: {e}")
        return docs


if __name__ == "__main__":
    parser = ImageParser()
    docs = parser.parse_image(r"C:\path\to\your\image.png")
    for d in docs:
        print(d.metadata)
        print(d.page_content[:200])
