from __future__ import annotations

import argparse
import json
import logging
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langgraph.errors import GraphRecursionError
from llm_models.all_llm import llm
from llm_models.embeddings_model import openai_embedding
from pydantic import BaseModel, Field

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CASE_COUNT = 10
MAX_WORKERS = 4
SPACE_PATTERN = re.compile(r"\s+")
METRIC_COLUMNS = ("faithfulness", "answer_relevancy", "context_precision", "context_recall")
BADCASE_THRESHOLD = 0.6
BADCASE_MAX_ROWS = 8
RESULT_DIR_PATTERN = re.compile(r"^第(\d+)次结果$")
RUN_STATUS_FILENAME = "run_status.json"
PARTIAL_SAMPLES_FILENAME = "graph2_ragas_samples_partial.json"
FIXED_CASES_FILENAME = "fixed_ragas_cases.json"

# ---------------------------------------------------------------------------
# 人工标注测试集（gold answer，来源于 datas/md 下的真实文档内容）
# ---------------------------------------------------------------------------
MANUAL_TEST_CASES: list[dict[str, Any]] = [
    {
        "question": "高介电常数金属栅技术（HKMG）如何降低晶体管的漏电流？",
        "reference": (
            "HKMG通过使用铪氧化物（HfO₂）等介电常数可达25以上的高介电常数材料，"
            "在减小栅极物理厚度的同时提高栅极对沟道的电场控制能力，从而有效降低漏电流。"
            "传统低介电常数材料在尺寸缩小到纳米级时因电场穿透效应漏电流会显著增加，"
            "而高介电常数材料的使用可解决这一问题。"
        ),
        "reference_contexts": [
            "传统低介电常数材料在尺寸缩小到纳米级时，因电场穿透效应而言，漏电流会显著增加。"
            "而高介电常数材料的使用可以减小栅极的物理厚度，提高栅极对通道的电场控制能力，从而降低漏电流。"
        ],
    },
    {
        "question": "等离子体处理中，氧等离子体如何去除半导体表面的有机污染物？",
        "reference": (
            "氧等离子体通过O₂→2O·解离产生活性氧原子，在200-400℃的反应温度下"
            "氧化分解半导体表面的有机污染物（如光刻胶残留、油脂等），实现表面清洁。"
        ),
        "reference_contexts": [
            "等离子体处理能有效去除半导体表面的有机污染物（光刻胶残留、油脂等）和金属杂质。"
            "典型工艺：氧等离子体(Oxygen Plasma)：通过O₂→2O·解离产生的活性氧原子氧化分解有机物（反应温度200-400℃）"
        ],
    },
    {
        "question": "在等离子体刻蚀中，实现高深宽比结构精确加工的关键工艺因素有哪些？",
        "reference": (
            "实现高深宽比结构精确加工的关键因素包括：选择合适的刻蚀气体（如F2、Cl2、N2）、"
            "合理控制刻蚀时间和能量密度以避免过蚀刻、选择具有高蚀刻选择性的掩膜材料，"
            "以及采用反应离子刻蚀（RIE）或深反应离子刻蚀（DRIE）等先进设备和技术，"
            "通过调整等离子体功率、气体流量及温度等参数获得最佳刻蚀效果。"
        ),
        "reference_contexts": [
            "首先，选择合适的刻蚀气体非常重要。常用的刻蚀气体包括氟气（F2）、氯气（Cl2）以及氮气（N2），"
            "这些气体的物理化学性质直接影响蚀刻速率和选择性。其次，控制刻蚀时间和能量密度是实现高深宽比结构的关键。"
            "例如，较长的刻蚀时间可能导致较大的蚀刻深度，而适当的能量密度则能合理控制刻蚀速率，避免出现过蚀刻现象。"
            "此外，掩膜材料的选择也至关重要，能有效提供蚀刻选择性，以确保在高深宽比结构中掩膜不被损伤。"
            "采用先进的刻蚀设备和技术，例如反应离子刻蚀（RIE）或深反应离子刻蚀（DRIE），"
            "可以有效提高深宽比结构的刻蚀精度和一致性。"
        ],
    },
    {
        "question": "定向自组装（DSA）技术中，高χ值嵌段共聚物相比普通嵌段共聚物有什么优势？",
        "reference": (
            "高χ值嵌段共聚物（High-χ BCP）因两种嵌段的不相容性更强，可实现更小的自然周期尺寸（L0）。"
            "例如使用聚苯乙烯-b-聚二甲基硅氧烷（PS-b-PDMS）可达到5nm以下周期，"
            "而传统PS-b-PMMA体系难以达到这一水平，从而突破传统光刻技术的分辨率限制。"
        ),
        "reference_contexts": [
            "开发高χ（chi）值嵌段共聚物（High-χ BCP），其中χ值表征两种嵌段的不相容性。"
            "高χ材料（如PS-b-PMMA的改进型）可实现更小的L0，"
            "例如使用聚苯乙烯-b-聚二甲基硅氧烷（PS-b-PDMS）可达到5nm以下周期"
        ],
    },
    {
        "question": "自对准双重曝光（SADP）相比LELE双重曝光技术有哪些核心优势？",
        "reference": (
            "SADP相比LELE的核心优势在于：规避了掩模对准误差（LELE需要优于3nm的对准精度）；"
            "图形尺寸由间隔层沉积厚度控制，可达更高的均匀性；"
            "且特别适用于规则阵列结构，例如FinFET鳍片的成形工艺。"
        ),
        "reference_contexts": [
            "SADP通过化学沉积和刻蚀工艺实现图形倍增，相较于LELE，SADP的优势在于："
            "规避了掩模对准误差；图形尺寸由沉积厚度控制，可达更高均匀性；"
            "适用于规则阵列结构（如FinFET的鳍片成形）"
        ],
    },
    {
        "question": "MOCVD技术在GaN HEMT器件制造中的具体应用是什么？",
        "reference": (
            "MOCVD在SiC衬底上制备AlGaN/GaN异质结，形成的二维电子气（2DEG）浓度可达1×10¹³ cm⁻²，"
            "从而制造适用于5G射频功放的GaN高电子迁移率晶体管（HEMT）器件。"
        ),
        "reference_contexts": [
            "GaN HEMT：在SiC衬底上制备AlGaN/GaN异质结，"
            "二维电子气（2DEG）浓度可达1×10¹³ cm⁻²，适用于5G射频功放。"
        ],
    },
    {
        "question": "16nm FinFET与28nm平面工艺相比，在功耗和漏电流方面有哪些具体改善？",
        "reference": (
            "16nm FinFET比28nm平面工艺动态功耗降低约40%；"
            "由于短沟道效应导致的漏致势垒降低（DIBL）被抑制，关断状态漏电流降低10倍以上。"
            "这得益于FinFET栅极三面包裹沟道结构对沟道的更强静电控制。"
        ),
        "reference_contexts": [
            "更低的阈值电压（Vth）：因沟道控制增强，可在保持相同关断电流（Ioff）的情况下降低工作电压（Vdd）。"
            "实测数据显示，16nm FinFET比28nm平面工艺动态功耗降低约40%。"
            "泄漏电流抑制：短沟道效应导致的漏致势垒降低（DIBL）被抑制，关断状态漏电流降低10倍以上。"
        ],
    },
    {
        "question": "晶圆级封装（WLP）在制造成本上相比传统封装有哪些优势？",
        "reference": (
            "对于I/O数量在200以下的芯片，WLP单颗封装成本可比传统封装低30-40%；"
            "采用批量加工模式使设备利用率提高3-5倍；"
            "同时省略了基板和框架等材料，物料清单（BOM）成本降低约25%。"
        ),
        "reference_contexts": [
            "WLP采用批量加工模式，在晶圆级同时完成数百至数千个芯片的封装，设备利用率提高3-5倍。"
            "统计数据显示，对于I/O数量在200以下的芯片，WLP的单颗封装成本可比传统封装低30-40%。"
            "此外，WLP省略了基板(Substrate)和框架(Lead Frame)等材料，物料清单(BOM, Bill of Materials)成本降低约25%。"
        ],
    },
    {
        "question": "EUV光刻胶在7nm以下制程中面临哪些主要技术挑战？",
        "reference": (
            "EUV光刻胶面临三类主要挑战：①光子-材料相互作用控制，需精确调控二次电子散射路径、"
            "酸扩散长度和反应猝灭效率；②材料组分优化，包括新型聚合物骨架设计、"
            "Sn/Hf等金属含量（5-20wt%）平衡及显影兼容性；③工艺集成障碍，"
            "要求刻蚀选择比>85%、随机缺陷密度<0.1/cm²、套刻精度<3nm时胶厚均匀性<1nm。"
        ),
        "reference_contexts": [
            "EUV光刻胶的化学反应主要由二次电子触发，而非直接光化学反应。每个EUV光子平均产生约5个二次电子，"
            "这些电子的能量分布（0-80eV）和扩散距离（2-20nm）直接影响图形精度。研发需精确调控："
            "电子散射路径（Electron Scattering Path）、酸扩散长度（Acid Diffusion Length）、反应猝灭效率（Quenching Efficiency）。"
            "在7nm以下节点，EUV光刻胶面临多重工艺匹配问题：刻蚀转移损失：要求>85%的选择比（Selectivity）以维持图形完整性；"
            "缺陷控制：需将随机缺陷（Stochastic Defects）密度控制在<0.1/cm²；"
            "多重曝光对齐：套刻精度（Overlay）要求<3nm时对胶厚均匀性（<1nm变异）提出苛求。"
        ],
    },
    {
        "question": "全环绕栅极晶体管（GAAFET）相比FinFET在静电控制方面有哪些具体改善？",
        "reference": (
            "GAAFET通过栅极从四个方向完全包围沟道，相比FinFET的三面包裹结构，"
            "亚阈值摆幅（Subthreshold Swing）改善约15-20%，"
            "漏致势垒降低（DIBL）效应降低50%以上，"
            "关态泄漏电流（Ioff）可降低1-2个数量级。"
        ),
        "reference_contexts": [
            "GAAFET通过四面包裹的栅极结构，显著增强了栅极对沟道的静电控制能力。具体表现为："
            "亚阈值摆幅（Subthreshold Swing）改善约15-20%；"
            "漏致势垒降低（DIBL）效应降低50%以上；"
            "关态泄漏电流（Ioff）可降低1-2个数量级。"
        ],
    },
]


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class QAPair(BaseModel):
    question: str = Field(..., description="Question answerable from context")
    reference: str = Field(..., description="Accurate reference answer")


class BadcaseAnalysisResult(BaseModel):
    badcase_reason: str = Field(..., description="Root-cause analysis of bad cases")
    improvement_suggestion: str = Field(..., description="Concrete, actionable improvement suggestions for the RAG system")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, payload: Any) -> None:
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def _load_fixed_test_cases() -> list[dict[str, Any]]:
    cases_path = Path(__file__).resolve().parents[1] / "datas" / "evaluation" / FIXED_CASES_FILENAME
    if not cases_path.exists():
        raise FileNotFoundError(f"Fixed test cases file not found: {cases_path}")

    with cases_path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if not isinstance(payload, list) or not payload:
        raise ValueError(f"Invalid fixed test cases file: {cases_path}")

    required_keys = {"question", "reference", "reference_contexts"}
    for i, item in enumerate(payload):
        if not isinstance(item, dict):
            raise ValueError(f"Case #{i} is not an object in {cases_path}")
        missing = required_keys - set(item.keys())
        if missing:
            raise ValueError(f"Case #{i} missing keys {sorted(missing)} in {cases_path}")
        if not isinstance(item["reference_contexts"], list):
            raise ValueError(f"Case #{i} reference_contexts must be a list in {cases_path}")
    return payload


def _update_run_status(output_dir: Path, stage: str, **kwargs: Any) -> None:
    status = {"stage": stage, "updated_at": datetime.now().isoformat(timespec="seconds")}
    status.update(kwargs)
    _write_json(output_dir / RUN_STATUS_FILENAME, status)


def _load_corpus_for_qa(max_chunks: int = 200) -> list[Document]:
    """Load markdown paragraphs as source material for QA pair generation only."""
    md_dir = Path(__file__).resolve().parents[1] / "datas" / "md"
    docs: list[Document] = []
    for path in sorted(md_dir.glob("*.md")):
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for para in re.split(r"\n\s*\n+", text.replace("\r\n", "\n")):
            para = SPACE_PATTERN.sub(" ", para.strip())
            if 120 <= len(para) <= 1400:
                docs.append(Document(page_content=para, metadata={"source": str(path)}))
            if len(docs) >= max_chunks:
                return docs
    return docs


def _extract_contexts(documents: Any) -> list[str]:
    if documents is None:
        return []
    items = documents if isinstance(documents, list) else [documents]
    contexts: list[str] = []
    for item in items:
        if hasattr(item, "page_content"):
            text = item.page_content
        elif isinstance(item, dict):
            text = item.get("page_content", "")
        else:
            text = str(item)
        text = (text or "").strip()
        if text:
            contexts.append(text)
    return contexts


# ---------------------------------------------------------------------------
# Test case & sample generation
# ---------------------------------------------------------------------------

def build_test_cases(docs: list[Document], case_count: int = CASE_COUNT) -> list[dict[str, Any]]:
    prompt = ChatPromptTemplate.from_template(
        "You will get one technical context.\n"
        "Generate one precise QA pair only from the context.\n"
        "Question should be specific and single-focus.\n"
        "Answer must be accurate and concise.\n\n"
        "Context:\n{context}"
    )
    qa_chain = prompt | llm.with_structured_output(QAPair)

    cases: list[dict[str, Any]] = []
    seen_questions: set[str] = set()

    for doc in docs:
        if len(cases) >= case_count:
            break
        context = doc.page_content
        try:
            qa = qa_chain.invoke({"context": context[:1800]})
            question = qa.question.strip()
            reference = qa.reference.strip()
        except Exception:
            continue

        if not question or not reference or question in seen_questions:
            continue
        seen_questions.add(question)
        cases.append({"question": question, "reference": reference, "reference_contexts": [context]})

    if len(cases) < case_count:
        raise RuntimeError(f"Only built {len(cases)} cases, less than required {case_count}.")
    return cases


def run_graph2_once(question: str, graph=None) -> tuple[str, list[str]]:
    """Run the real graph2 pipeline (Milvus hybrid retrieval + CRAG) for one question."""
    if graph is None:
        from graph2.graph_2 import get_graph
        graph = get_graph()
    try:
        final_state = graph.invoke({"question": question}, config={"recursion_limit": 60})
    except GraphRecursionError:
        final_state = {}
    answer = (final_state.get("generation") or "").strip()
    contexts = _extract_contexts(final_state.get("documents"))
    return answer, contexts


def build_samples(
    output_dir: Path | None = None,
    max_workers: int = MAX_WORKERS,
    graph=None,
) -> list[dict[str, Any]]:
    test_cases = _load_fixed_test_cases()
    total_cases = len(test_cases)
    samples: list[dict[str, Any] | None] = [None] * total_cases
    completed_count = 0
    status_lock = threading.Lock()

    if output_dir is not None:
        _update_run_status(
            output_dir, "building_samples",
            total_cases=total_cases, completed_cases=0, max_workers=max_workers,
        )

    def _process(idx: int, case: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        answer, contexts = run_graph2_once(case["question"], graph=graph)
        return idx, {
            "user_input": case["question"],
            "response": answer,
            "retrieved_contexts": contexts,
            "reference": case["reference"],
            "reference_contexts": case["reference_contexts"],
        }

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_process, idx, case): idx for idx, case in enumerate(test_cases)}
        for future in as_completed(futures):
            idx, sample = future.result()
            samples[idx] = sample
            with status_lock:
                completed_count += 1
                done = completed_count
                if output_dir is not None:
                    _write_json(output_dir / PARTIAL_SAMPLES_FILENAME, [s for s in samples if s is not None])
                    _update_run_status(
                        output_dir, "building_samples",
                        total_cases=total_cases, completed_cases=done, max_workers=max_workers,
                    )
            logger.info("[build_samples] completed %d/%d", done, total_cases)

    return [s for s in samples if s is not None]


# ---------------------------------------------------------------------------
# RAGAS evaluation
# ---------------------------------------------------------------------------

def evaluate_with_ragas(samples: list[dict[str, Any]]):
    from ragas import evaluate
    from ragas.dataset_schema import EvaluationDataset, SingleTurnSample
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

    dataset = EvaluationDataset(
        samples=[
            SingleTurnSample(
                user_input=item["user_input"],
                response=item["response"],
                retrieved_contexts=item["retrieved_contexts"],
                reference=item["reference"],
                reference_contexts=item["reference_contexts"],
            )
            for item in samples
        ]
    )
    result = evaluate(
        dataset=dataset,
        metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
        llm=LangchainLLMWrapper(llm),
        embeddings=LangchainEmbeddingsWrapper(openai_embedding),
    )
    return result.to_pandas()


# ---------------------------------------------------------------------------
# Badcase analysis — feeds CSV rows to LLM, writes last two rows
# ---------------------------------------------------------------------------

def _build_badcase_rows(df, threshold: float = BADCASE_THRESHOLD, top_n: int = BADCASE_MAX_ROWS) -> list[dict[str, Any]]:
    import pandas as pd

    score_columns = [col for col in METRIC_COLUMNS if col in df.columns]
    if not score_columns:
        return []

    work_df = df.copy()
    for col in score_columns:
        work_df[col] = pd.to_numeric(work_df[col], errors="coerce")
    work_df["__min_score__"] = work_df[score_columns].min(axis=1, skipna=True)

    bad_df = work_df[(work_df["__min_score__"] < threshold) | work_df["__min_score__"].isna()]
    if bad_df.empty:
        bad_df = work_df.nsmallest(min(len(work_df), top_n), "__min_score__")
    bad_df = bad_df.head(top_n)

    rows: list[dict[str, Any]] = []
    for _, row in bad_df.iterrows():
        rows.append({
            "question": str(row.get("user_input", "")),
            "response": str(row.get("response", ""))[:260],
            "reference": str(row.get("reference", ""))[:220],
            "retrieved_contexts": str(row.get("retrieved_contexts", ""))[:320],
            "faithfulness": row.get("faithfulness"),
            "answer_relevancy": row.get("answer_relevancy"),
            "context_precision": row.get("context_precision"),
            "context_recall": row.get("context_recall"),
        })
    return rows


def _fallback_badcase_analysis(df) -> tuple[str, str]:
    import pandas as pd

    score_columns = [col for col in METRIC_COLUMNS if col in df.columns]
    if not score_columns:
        return (
            "Missing RAGAS metric columns, cannot locate badcase reasons.",
            "Ensure CSV contains faithfulness, answer_relevancy, context_precision, context_recall.",
        )
    numeric_df = df[score_columns].apply(pd.to_numeric, errors="coerce")
    weakest = numeric_df.mean().sort_values().index[0]
    reason = (
        f"Most badcases show low {weakest}. Likely causes: retrieval-question misalignment or "
        "incomplete answer coverage."
    )
    suggestion = (
        "Improve retrieval recall and reranking quality; enforce grounding on retrieved context."
    )
    return reason, suggestion


def _analyze_badcase_df(df) -> tuple[str, str]:
    """Feed worst-case rows to LLM and return (badcase_reason, improvement_suggestion)."""
    badcase_rows = _build_badcase_rows(df)
    if not badcase_rows:
        return _fallback_badcase_analysis(df)

    prompt = ChatPromptTemplate.from_template(
        "You are a RAG evaluation analyst. Below is a JSON list of badcase rows from a RAG system evaluation.\n"
        "Each row contains RAGAS metric scores (faithfulness, answer_relevancy, context_precision, "
        "context_recall) along with the question, model response, reference answer, and retrieved contexts.\n\n"
        "Badcase rows (JSON):\n{badcases_json}\n\n"
        "Based solely on the data above, provide:\n"
        "1) badcase_reason: Identify the direct failure patterns and root causes (2-4 sentences). "
        "Point out which metrics are lowest and explain why.\n"
        "2) improvement_suggestion: Give concrete, actionable technical improvements for the RAG pipeline "
        "(2-4 sentences). Be specific about retrieval, reranking, generation, or prompt strategies.\n"
        "Keep both fields concise — they will be written into CSV cells.\n"
        "请用中文回答。"
    )
    chain = prompt | llm.with_structured_output(BadcaseAnalysisResult)

    try:
        result = chain.invoke({"badcases_json": json.dumps(badcase_rows, ensure_ascii=False)})
        reason = SPACE_PATTERN.sub(" ", result.badcase_reason or "").strip()
        suggestion = SPACE_PATTERN.sub(" ", result.improvement_suggestion or "").strip()
        if not reason or not suggestion:
            return _fallback_badcase_analysis(df)
        return reason, suggestion
    except Exception:
        return _fallback_badcase_analysis(df)


def _append_badcase_analysis_rows(detail_path: Path) -> None:
    """Read the evaluation CSV, call LLM for analysis, append two summary rows."""
    import pandas as pd

    df = pd.read_csv(detail_path, encoding="utf-8-sig")
    if df.empty:
        return

    badcase_reason, improvement_suggestion = _analyze_badcase_df(df)
    columns = list(df.columns)

    reason_row = {col: "" for col in columns}
    suggestion_row = {col: "" for col in columns}

    if "user_input" in columns:
        reason_row["user_input"] = "[BADCASE_REASON]"
        suggestion_row["user_input"] = "[IMPROVEMENT_SUGGESTION]"
    if "response" in columns:
        reason_row["response"] = badcase_reason
        suggestion_row["response"] = improvement_suggestion
    if "reference" in columns:
        reason_row["reference"] = "badcase原因分析"
        suggestion_row["reference"] = "系统优化建议"
    if "retrieved_contexts" in columns:
        reason_row["retrieved_contexts"] = "[]"
        suggestion_row["retrieved_contexts"] = "[]"

    df = pd.concat([df, pd.DataFrame([reason_row, suggestion_row], columns=columns)], ignore_index=True)
    df.to_csv(detail_path, index=False, encoding="utf-8-sig")


# ---------------------------------------------------------------------------
# Output management
# ---------------------------------------------------------------------------

_RESULT_DIR_PATTERN_LOOSE = re.compile(r"^第(\d+)次结果")


def _create_next_result_dir(suffix: str = "") -> Path:
    evaluation_dir = Path(__file__).resolve().parents[1] / "datas" / "evaluation"
    evaluation_dir.mkdir(parents=True, exist_ok=True)

    max_round = 0
    for child in evaluation_dir.iterdir():
        if not child.is_dir():
            continue
        m = _RESULT_DIR_PATTERN_LOOSE.match(child.name)
        if m:
            max_round = max(max_round, int(m.group(1)))

    next_round = max_round + 1
    tag = f"-{suffix}" if suffix else ""
    while True:
        result_dir = evaluation_dir / f"第{next_round}次结果{tag}"
        try:
            result_dir.mkdir(parents=False, exist_ok=False)
            return result_dir
        except FileExistsError:
            next_round += 1


def save_outputs(samples: list[dict[str, Any]], df, output_dir: Path | None = None) -> dict[str, Path]:
    import pandas as pd

    if output_dir is None:
        output_dir = _create_next_result_dir()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    cases_path = output_dir / f"graph2_ragas_testcases_{timestamp}.json"
    detail_path = output_dir / f"graph2_ragas_detail_{timestamp}.csv"
    summary_path = output_dir / f"graph2_ragas_summary_{timestamp}.json"
    cases_only_path = output_dir / f"graph2_ragas_cases_only_{timestamp}.json"

    _write_json(cases_path, samples)
    _write_json(cases_only_path, [
        {"question": s["user_input"], "reference": s["reference"],
         "reference_contexts": s.get("reference_contexts", [])}
        for s in samples
    ])

    df.to_csv(detail_path, index=False, encoding="utf-8-sig")
    _append_badcase_analysis_rows(detail_path)

    summary: dict[str, Any] = {"sample_count": int(len(df))}
    for col in METRIC_COLUMNS:
        if col not in df.columns:
            continue
        series = pd.to_numeric(df[col], errors="coerce")
        summary[col] = {
            "mean": round(float(series.mean()), 4),
            "std": round(float(series.std()), 4),
            "min": round(float(series.min()), 4),
            "max": round(float(series.max()), 4),
            "pass_rate": round(float((series >= BADCASE_THRESHOLD).mean()), 4),
        }
    _write_json(summary_path, summary)

    partial = output_dir / PARTIAL_SAMPLES_FILENAME
    if partial.exists():
        partial.unlink()

    return {
        "result_dir": output_dir,
        "cases": cases_path,
        "cases_only": cases_only_path,
        "detail": detail_path,
        "summary": summary_path,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    global CASE_COUNT, MAX_WORKERS, BADCASE_THRESHOLD

    parser = argparse.ArgumentParser(description="RAGAS evaluation for graph2 RAG pipeline")
    parser.add_argument("--case-count", type=int, default=CASE_COUNT)
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--threshold", type=float, default=BADCASE_THRESHOLD)
    parser.add_argument(
        "--mode",
        choices=["original", "replace", "coexist"],
        default="original",
        help="Pipeline variant: original / replace (reranker replaces grader) / coexist (reranker + grader)",
    )
    args = parser.parse_args()
    CASE_COUNT = args.case_count
    MAX_WORKERS = args.workers
    BADCASE_THRESHOLD = args.threshold

    if args.mode == "replace":
        from graph2.graph_2_replace import get_graph
        graph = get_graph()
        dir_suffix = "reranker-replace"
    elif args.mode == "coexist":
        from graph2.graph_2_coexist import get_graph
        graph = get_graph()
        dir_suffix = "reranker-coexist"
    else:
        from graph2.graph_2 import get_graph
        graph = get_graph()
        dir_suffix = ""

    output_dir = _create_next_result_dir(suffix=dir_suffix)
    logger.info("mode=%s  result_dir: %s", args.mode, output_dir)
    _update_run_status(output_dir, "started", workers=MAX_WORKERS, mode=args.mode)

    wall_start = time.perf_counter()
    paths: dict[str, Path] = {}
    build_elapsed = eval_elapsed = 0.0
    try:
        t0 = time.perf_counter()
        samples = build_samples(output_dir=output_dir, max_workers=MAX_WORKERS, graph=graph)
        build_elapsed = time.perf_counter() - t0
        logger.info("[build_samples] finished in %.1fs", build_elapsed)

        _update_run_status(output_dir, "evaluating_ragas", sample_count=len(samples))
        logger.info("[evaluate_with_ragas] started")
        t1 = time.perf_counter()
        df = evaluate_with_ragas(samples)
        eval_elapsed = time.perf_counter() - t1
        logger.info("[evaluate_with_ragas] finished in %.1fs", eval_elapsed)

        _update_run_status(output_dir, "saving_outputs", sample_count=len(samples))
        paths = save_outputs(samples, df, output_dir=output_dir)

        total_elapsed = time.perf_counter() - wall_start
        _update_run_status(
            output_dir, "completed",
            sample_count=len(samples),
            build_samples_seconds=round(build_elapsed, 2),
            evaluate_ragas_seconds=round(eval_elapsed, 2),
            total_seconds=round(total_elapsed, 2),
            outputs={k: str(v) for k, v in paths.items()},
        )
    except Exception as exc:
        _update_run_status(output_dir, "failed", error=repr(exc))
        raise

    total_elapsed = time.perf_counter() - wall_start
    logger.info("RAGAS evaluation finished. Total: %.1fs (build=%.1fs, eval=%.1fs)",
                total_elapsed, build_elapsed, eval_elapsed)
    for key, value in paths.items():
        logger.info("  %s: %s", key, value)


if __name__ == "__main__":
    main()
