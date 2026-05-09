import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import gradio as gr
from openai import OpenAI

from graph2.graph_2 import get_graph
from utils.env_utils import OPENAI_API_KEY

graph = get_graph()
_whisper_client = OpenAI(api_key=OPENAI_API_KEY)


def transcribe(audio_path: str) -> str:
    """用 Whisper API 将录音文件转为文字。"""
    if not audio_path:
        return ""
    with open(audio_path, "rb") as f:
        result = _whisper_client.audio.transcriptions.create(
            model="whisper-1",
            file=f,
            language="zh",
        )
    return result.text


def run_graph(question: str):
    if not question.strip():
        return "", "请输入问题"

    logs = []
    final_answer = ""

    inputs = {"question": question}
    for output in graph.stream(inputs):
        for node_name, node_value in output.items():
            logs.append(f"[节点] {node_name}")
            if isinstance(node_value, dict):
                gen = node_value.get("generation")
                if gen:
                    final_answer = gen
                    logs.append(f"  生成回答: {gen[:100]}{'...' if len(gen) > 100 else ''}")
                docs = node_value.get("documents")
                if docs:
                    logs.append(f"  检索文档数: {len(docs)}")
            logs.append("---")

    return final_answer, "\n".join(logs)


def handle_audio(audio_path: str):
    """录音结束后：转文字 → 填入输入框 → 自动提交。"""
    question = transcribe(audio_path)
    if not question:
        return "", "", "转录失败，请重试"
    answer, logs = run_graph(question)
    return question, answer, logs


with gr.Blocks(title="RAG半导体知识库问答系统") as demo:
    gr.Markdown("# RAG半导体知识库问答系统")
    gr.Markdown("基于 LangGraph 的自适应 RAG，支持向量库检索 + Web 搜索，含幻觉检测。支持语音提问。")

    with gr.Row():
        with gr.Column(scale=2):
            question_input = gr.Textbox(
                label="输入问题（可直接输入，也可用语音）",
                placeholder="请输入你的问题，或点击下方麦克风录音...",
                lines=3,
            )
            audio_input = gr.Audio(
                sources=["microphone"],
                type="filepath",
                label="语音提问（录音结束后自动识别并提交）",
            )
            submit_btn = gr.Button("提交", variant="primary")
            answer_output = gr.Textbox(label="最终回答", lines=8, interactive=False)

        with gr.Column(scale=1):
            log_output = gr.Textbox(label="执行过程", lines=20, interactive=False)

    # 文字提交
    submit_btn.click(fn=run_graph, inputs=question_input, outputs=[answer_output, log_output])
    question_input.submit(fn=run_graph, inputs=question_input, outputs=[answer_output, log_output])

    # 语音提交：录音结束 → 转文字填入输入框 → 自动触发问答
    audio_input.stop_recording(
        fn=handle_audio,
        inputs=audio_input,
        outputs=[question_input, answer_output, log_output],
    )

if __name__ == "__main__":
    demo.launch(server_name="127.0.0.1", server_port=7860)
