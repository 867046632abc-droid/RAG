import os
import time
import uuid
import requests

from llm_models.all_llm import sora_client, KLING_ACCESS_KEY, KLING_SECRET_KEY
from multimodal_RAG.video_state import VideoGraphState
from utils.log_utils import log

_MAX_PROMPT_LEN = 300

# 默认保存到项目 datas/videos/ 目录
_DEFAULT_SAVE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "datas", "videos"
)


def _build_prompt(generation: str) -> str:
    summary = generation[:_MAX_PROMPT_LEN].strip()
    return f"根据以下半导体技术内容，生成一段简洁的科普解释动画：{summary}"


def _save_binary(content, save_dir: str) -> str:
    """将二进制内容写入本地 mp4 文件，返回绝对路径。"""
    os.makedirs(save_dir, exist_ok=True)
    filepath = os.path.join(save_dir, f"video_{uuid.uuid4().hex[:8]}.mp4")
    with open(filepath, "wb") as f:
        # SDK 返回 HttpxBinaryResponseContent，支持 .read() 或直接迭代
        f.write(content.read() if hasattr(content, "read") else bytes(content))
    log.info(f"视频已保存: {filepath}")
    return filepath


# ---------- Sora (openai SDK v2) ----------

def _generate_with_sora(prompt: str, save_dir: str) -> str:
    """
    调用 OpenAI Sora v2 生成视频并保存到本地，返回本地文件路径。
    模型: sora-2 | seconds: '4'/'8'/'12' | size: '1280x720' 等
    """
    log.info("提交 Sora 视频任务（含轮询，通常需要数分钟）...")
    video = sora_client.videos.create_and_poll(
        prompt=prompt,
        model="sora-2",
        seconds="8",
        size="1280x720",
    )
    log.info(f"Sora 任务完成，video_id={video.id}")
    content = sora_client.videos.download_content(video.id)
    return _save_binary(content, save_dir)


# ---------- Kling ----------

def _kling_jwt() -> str:
    try:
        import jwt
    except ImportError:
        raise ImportError("调用 Kling 需要 PyJWT：pip install PyJWT")

    payload = {
        "iss": KLING_ACCESS_KEY,
        "exp": int(time.time()) + 1800,
        "nbf": int(time.time()) - 5,
    }
    return jwt.encode(payload, KLING_SECRET_KEY, algorithm="HS256")


def _generate_with_kling(prompt: str, save_dir: str, max_wait: int = 300) -> str:
    """
    调用 Kling text2video，轮询等待任务完成，下载并保存到本地，返回文件路径。
    """
    if not KLING_ACCESS_KEY or not KLING_SECRET_KEY:
        raise ValueError("Kling 密钥未配置，请在 .env 中添加 KLING_ACCESS_KEY / KLING_SECRET_KEY")

    def _headers():
        return {"Authorization": f"Bearer {_kling_jwt()}", "Content-Type": "application/json"}

    resp = requests.post(
        "https://api.klingai.com/v1/videos/text2video",
        headers=_headers(),
        json={"model": "kling-v1", "prompt": prompt, "duration": "5", "aspect_ratio": "16:9"},
        timeout=30,
    )
    resp.raise_for_status()
    task_id = resp.json()["data"]["task_id"]
    log.info(f"Kling 任务已提交，task_id={task_id}")

    deadline = time.time() + max_wait
    while time.time() < deadline:
        time.sleep(10)
        check = requests.get(
            f"https://api.klingai.com/v1/videos/text2video/{task_id}",
            headers=_headers(), timeout=30,
        )
        check.raise_for_status()
        data = check.json()["data"]
        status = data["task_status"]
        log.info(f"Kling 任务状态: {status}")
        if status == "succeed":
            url = data["task_result"]["videos"][0]["url"]
            # 下载到本地
            os.makedirs(save_dir, exist_ok=True)
            filepath = os.path.join(save_dir, f"video_{uuid.uuid4().hex[:8]}.mp4")
            dl = requests.get(url, timeout=120, stream=True)
            dl.raise_for_status()
            with open(filepath, "wb") as f:
                for chunk in dl.iter_content(chunk_size=8192):
                    f.write(chunk)
            log.info(f"Kling 视频已保存: {filepath}")
            return filepath
        if status == "failed":
            raise RuntimeError(f"Kling 生成失败: {data.get('task_status_msg', '')}")

    raise TimeoutError(f"Kling 生成超时（{max_wait}s）")


# ---------- 节点入口 ----------

def video_generate(state: VideoGraphState) -> dict:
    """视频生成节点：将 RAG 回答转为短视频并保存到本地。"""
    generation = state.get("generation", "")
    provider = state.get("video_provider", "sora")
    save_dir = state.get("video_save_dir") or _DEFAULT_SAVE_DIR

    if not generation:
        log.warning("video_generate: generation 为空，跳过")
        return {"video_path": ""}

    prompt = _build_prompt(generation)
    log.info(f"---开始视频生成，provider={provider}，保存目录={save_dir}---")

    try:
        if provider == "sora":
            local_path = _generate_with_sora(prompt, save_dir)
        elif provider == "kling":
            local_path = _generate_with_kling(prompt, save_dir)
        else:
            raise ValueError(f"不支持的 provider: {provider}，可选: sora / kling")

        return {"video_path": local_path}

    except Exception as e:
        log.error(f"视频生成失败: {e}")
        return {"video_path": f"ERROR: {e}"}
