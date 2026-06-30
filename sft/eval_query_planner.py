#!/usr/bin/env python3
"""Evaluate query planner baselines before/after LoRA training.

Modes:
- raw_query: no model; wraps the user question as a minimal query_plan.
- endpoint: calls an OpenAI-compatible chat endpoint for base or LoRA models.

This script evaluates JSON/schema quality. Retrieval hit@k can be added later by
using each predicted primary/secondary query against Milvus.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
import urllib.error
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any

ALLOWED_INTENTS = {
    "definition",
    "mechanism",
    "comparison",
    "application",
    "parameter",
    "challenge",
    "process",
    "advantage",
}

EVAL_INSTRUCTION = (
    "你是半导体 RAG 系统的 query planner。请把用户问题改写为适合向量库和 BM25 "
    "混合检索的 JSON 查询计划。只输出严格 JSON，不要 markdown，不要解释。JSON 必须包含 "
    "primary_query, secondary_queries, must_keep_terms, intent, answer_aspects。"
)


def load_env_fallback(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def extract_json_object(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start < 0 or end <= start:
            return None
        try:
            parsed = json.loads(cleaned[start : end + 1])
        except json.JSONDecodeError:
            return None
    return parsed if isinstance(parsed, dict) else None


def validate_plan(plan: Any) -> tuple[bool, str | None]:
    if not isinstance(plan, dict):
        return False, "not_object"
    if not isinstance(plan.get("primary_query"), str) or not plan["primary_query"].strip():
        return False, "missing_primary_query"
    if not isinstance(plan.get("secondary_queries"), list) or not all(isinstance(x, str) and x.strip() for x in plan["secondary_queries"]):
        return False, "bad_secondary_queries"
    if not isinstance(plan.get("must_keep_terms"), list) or not any(isinstance(x, str) and x.strip() for x in plan["must_keep_terms"]):
        return False, "bad_must_keep_terms"
    if plan.get("intent") not in ALLOWED_INTENTS:
        return False, "bad_intent"
    if not isinstance(plan.get("answer_aspects"), list) or not any(isinstance(x, str) and x.strip() for x in plan["answer_aspects"]):
        return False, "bad_answer_aspects"
    return True, None


def call_endpoint(base_url: str, api_key: str, model: str, question: str, timeout: float, temperature: float) -> str:
    url = base_url.rstrip("/") + "/chat/completions"
    payload = json.dumps(
        {
            "model": model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": EVAL_INSTRUCTION},
                {"role": "user", "content": question},
            ],
        },
        ensure_ascii=False,
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"HTTP {exc.code}: {error_body[:500]}") from exc
    parsed = json.loads(body)
    return parsed["choices"][0]["message"].get("content") or ""


def raw_query_plan(question: str) -> dict[str, Any]:
    return {
        "primary_query": question,
        "secondary_queries": [],
        "must_keep_terms": [],
        "intent": "definition",
        "answer_aspects": [],
    }


def load_eval_rows(path: Path, limit: int | None) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data[:limit] if limit else data
    result = []
    for row in rows:
        if "input" in row:
            result.append({"question": row["input"], "gold_output": row.get("output")})
        elif "user_question" in row:
            result.append({"question": row["user_question"], "gold_output": json.dumps(row.get("query_plan", {}), ensure_ascii=False)})
    return result


def build_parser() -> argparse.ArgumentParser:
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["raw_query", "endpoint"], required=True)
    parser.add_argument("--input", type=Path, default=root / "dataset" / "valid_alpaca.json")
    parser.add_argument("--output", type=Path, default=root / "eval_results" / "eval.json")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--model", default=os.getenv("EVAL_MODEL", "Qwen/Qwen2.5-0.5B-Instruct"))
    parser.add_argument("--base-url", default=os.getenv("EVAL_BASE_URL", "http://127.0.0.1:8000/v1"))
    parser.add_argument("--api-key-env", default=os.getenv("EVAL_API_KEY_ENV", "EVAL_API_KEY"))
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    return parser


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    load_env_fallback(root / ".env")
    load_env_fallback(Path(__file__).resolve().parent / ".env")

    args = build_parser().parse_args()
    rows = load_eval_rows(args.input, args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)

    api_key = os.getenv(args.api_key_env, "EMPTY")
    results: list[dict[str, Any]] = []
    counters: Counter[str] = Counter()

    for idx, row in enumerate(rows):
        question = row["question"]
        error = None
        raw_text = ""
        if args.mode == "raw_query":
            plan = raw_query_plan(question)
            raw_text = json.dumps(plan, ensure_ascii=False)
        else:
            try:
                raw_text = call_endpoint(args.base_url, api_key, args.model, question, args.timeout, args.temperature)
                plan = extract_json_object(raw_text)
            except Exception as exc:
                plan = None
                error = repr(exc)

        ok, reason = validate_plan(plan)
        counters["total"] += 1
        counters["schema_pass" if ok else "schema_fail"] += 1
        if reason:
            counters[reason] += 1
        if plan is not None:
            counters["json_parse_pass"] += 1
        else:
            counters["json_parse_fail"] += 1

        results.append(
            {
                "index": idx,
                "question": question,
                "prediction_text": raw_text,
                "prediction_plan": plan,
                "schema_pass": ok,
                "failure_reason": reason,
                "error": error,
                "gold_output": row.get("gold_output"),
            }
        )
        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    total = max(1, counters["total"])
    summary = {
        "mode": args.mode,
        "model": args.model,
        "input": str(args.input),
        "total": counters["total"],
        "json_parse_rate": counters["json_parse_pass"] / total,
        "schema_pass_rate": counters["schema_pass"] / total,
        "counters": dict(counters),
    }
    args.output.write_text(json.dumps({"summary": summary, "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
