"""批判节点：在 graph2 的两条评判链基础上，输出 high/medium/low 三级置信度。

置信度规则
----------
high   : 幻觉检测=yes 且 答案有效=yes（完全基于文档且有效回答）
medium : 幻觉检测=yes 但 答案有效=no（基于文档但回答不完整/偏题）
low    : 幻觉检测=no（存在文档以外的内容，触发重试或兜底）
"""
from graph2.grade_answer_chain import answer_grader_chain
from graph2.grade_hallucinations_chain import hallucination_grader_chain
from utils.log_utils import log


def critic_check(state: dict) -> dict:
    """批判 Agent：对专家输出做幻觉检测 + 答案有效性检测，输出置信度。"""
    question = state["question"]
    documents = state["documents"]
    expert_output = state.get("expert_output", "")

    if not expert_output.strip():
        log.info("---[批判 Agent] 专家输出为空，置信度=low---")
        return {"confidence": "low"}

    # ── 幻觉检测 ─────────────────────────────────────────────────────────────
    log.info("---[批判 Agent] 幻觉检测中---")
    hall_score = hallucination_grader_chain.invoke({
        "documents": documents,
        "generation": expert_output,
    })
    grounded = hall_score.binary_score == "yes"
    log.info("---[批判 Agent] 幻觉检测结果：%s（grounded=%s）---",
             hall_score.binary_score, grounded)

    if not grounded:
        log.info("---[批判 Agent] 检测到幻觉，置信度=low，触发重试---")
        return {"confidence": "low"}

    # ── 答案有效性检测 ────────────────────────────────────────────────────────
    log.info("---[批判 Agent] 答案有效性检测中---")
    ans_score = answer_grader_chain.invoke({
        "question": question,
        "generation": expert_output,
    })
    useful = ans_score.binary_score == "yes"
    log.info("---[批判 Agent] 答案有效性：%s（useful=%s）---",
             ans_score.binary_score, useful)

    confidence = "high" if useful else "medium"
    log.info("---[批判 Agent] 最终置信度=%s---", confidence)
    return {"confidence": confidence}
