#!/usr/bin/env python3
"""Generate query-planner SFT data from semiconductor markdown chunks using Seed2.0.

This script intentionally does not contain API keys. Set SEED_API_KEY in the
runtime environment before running non-dry-run generation.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import random
import re
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass

try:
    from dotenv import load_dotenv
except ImportError:  # python-dotenv is optional for this script.
    load_dotenv = None
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Iterable

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

TRAINING_INSTRUCTION = (
    "你是半导体 RAG 系统的 query planner。请把用户问题改写为适合向量库和 BM25 "
    "混合检索的 JSON 查询计划。必须保留专业术语、数值、缩写、材料名、工艺名和比较对象。"
)

SYSTEM_PROMPT = """你是一个用于半导体技术 RAG 系统的 query planner 数据生成专家。

你的任务：
根据给定的参考文档片段，生成适合训练小模型的 query rewrite 样本。
样本目标不是回答问题，而是把用户问题改写为更适合 Milvus 混合检索（向量检索 + BM25）的查询计划。

必须遵守：
1. 只基于给定文档片段生成问题和查询计划，不得引入外部事实。
2. 用户问题要自然，像真实用户会问的问题。
3. 查询计划必须保留关键术语、英文缩写、材料名、工艺名、数值、单位、比较对象。
4. primary_query 应适合直接送入向量数据库和 BM25 检索。
5. secondary_queries 应覆盖同义词、英文表达、缩写/全称、数值条件、机制词。
6. 不要在 query 里直接写完整答案；query 只能用于检索。
7. output 必须是严格 JSON 数组，不要 markdown，不要解释。
8. 如果文档片段信息不足以生成高质量样本，返回空数组。
9. 只生成半导体技术领域样本，不要生成 web_search、闲聊、时事、价格行情类负样本。

输出格式：
返回 JSON 数组，每个元素必须包含：
- user_question: 用户原始问题
- query_plan:
  - primary_query: string
  - secondary_queries: string[]
  - must_keep_terms: string[]
  - intent: one of ["definition", "mechanism", "comparison", "application", "parameter", "challenge", "process", "advantage"]
  - answer_aspects: string[]
- quality_reason: 简短说明为什么该查询计划有助于检索
- source_terms: 从文档中抽取的关键术语
"""

USER_PROMPT_TEMPLATE = """参考文档片段：
<<<
{chunk_text}
>>>

请基于这个参考文档片段生成 {num_samples} 条高质量样本。"""


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    source_file: str
    text: str


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_env_fallback(path: Path) -> None:
    """Load simple KEY=value env files when python-dotenv is unavailable."""
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


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def normalize_for_dedupe(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"\s+", "", text)
    text = re.sub(r"[，。！？、；：,.!?;:\-—_（）()\[\]{}《》<>\"'`]+", "", text)
    return text


def read_markdown(path: Path) -> str:
    text = path.read_text(encoding="utf-8", errors="ignore")
    text = re.sub(r"```.*?```", " ", text, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[[^\]]+\]\([^)]*\)", lambda m: m.group(0).split("]", 1)[0].lstrip("["), text)
    text = re.sub(r"^\s{0,3}#{1,6}\s*", "", text, flags=re.M)
    text = re.sub(r"^\s*[-*_]{3,}\s*$", " ", text, flags=re.M)
    return text


def split_paragraphs(text: str) -> list[str]:
    paragraphs = [normalize_space(p) for p in re.split(r"\n\s*\n+", text)]
    return [p for p in paragraphs if len(p) >= 20]


def chunk_text(text: str, chunk_size: int, overlap: int, min_chars: int) -> list[str]:
    paragraphs = split_paragraphs(text)
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        if not current:
            current = paragraph
            continue

        if len(current) + 1 + len(paragraph) <= chunk_size:
            current = f"{current}\n{paragraph}"
        else:
            if len(current) >= min_chars:
                chunks.append(current)
            tail = current[-overlap:] if overlap > 0 else ""
            current = f"{tail}\n{paragraph}" if tail else paragraph

    if len(current) >= min_chars:
        chunks.append(current)

    return chunks


def iter_chunks(md_dir: Path, chunk_size: int, overlap: int, min_chars: int) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(md_dir.glob("*.md")):
        text = read_markdown(path)
        for idx, part in enumerate(chunk_text(text, chunk_size, overlap, min_chars)):
            source_file = path.name
            chunk_id = f"{source_file}::{idx:04d}"
            chunks.append(Chunk(chunk_id=chunk_id, source_file=source_file, text=part))
    return chunks


def load_seen_keys(raw_path: Path) -> set[str]:
    seen: set[str] = set()
    if not raw_path.exists():
        return seen
    with raw_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                continue
            q = item.get("user_question", "")
            primary = item.get("query_plan", {}).get("primary_query", "")
            if q or primary:
                seen.add(sample_key(q, primary))
    return seen


def load_existing_alpaca(raw_path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    if not raw_path.exists():
        return rows
    with raw_path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                raw = json.loads(line)
            except json.JSONDecodeError:
                continue
            rows.append(to_alpaca(raw))
    return rows


def sample_key(user_question: str, primary_query: str) -> str:
    normalized = normalize_for_dedupe(user_question) + "||" + normalize_for_dedupe(primary_query)
    return hashlib.sha1(normalized.encode("utf-8")).hexdigest()


def build_user_prompt(chunk: Chunk, num_samples: int) -> str:
    return USER_PROMPT_TEMPLATE.format(chunk_text=chunk.text, num_samples=num_samples)


class SeedHTTPClient:
    """Tiny OpenAI-compatible chat completions client using only stdlib."""

    def __init__(self, api_key: str, base_url: str, timeout: float):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def complete(self, model: str, messages: list[dict[str, str]], temperature: float) -> str:
        url = f"{self.base_url}/chat/completions"
        payload = json.dumps(
            {"model": model, "messages": messages, "temperature": temperature},
            ensure_ascii=False,
        ).encode("utf-8")
        request = urllib.request.Request(
            url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Seed HTTP {exc.code}: {error_body[:500]}") from exc
        parsed = json.loads(body)
        return parsed["choices"][0]["message"].get("content") or ""


def get_openai_client(api_key: str, base_url: str, timeout: float):
    try:
        from openai import OpenAI
    except ImportError:
        return SeedHTTPClient(api_key=api_key, base_url=base_url, timeout=timeout)
    return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)


def call_seed(client: Any, model: str, chunk: Chunk, num_samples: int, temperature: float) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_prompt(chunk, num_samples)},
    ]
    if hasattr(client, "complete"):
        return client.complete(model=model, messages=messages, temperature=temperature)
    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        messages=messages,
    )
    return response.choices[0].message.content or ""


def extract_json_array(text: str) -> list[Any]:
    cleaned = text.strip()
    cleaned = re.sub(r"^```(?:json)?", "", cleaned).strip()
    cleaned = re.sub(r"```$", "", cleaned).strip()

    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(cleaned[start : end + 1])

    if isinstance(parsed, dict) and isinstance(parsed.get("samples"), list):
        parsed = parsed["samples"]
    if not isinstance(parsed, list):
        raise ValueError("Seed response is not a JSON array")
    return parsed


def as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        if isinstance(item, str):
            item = normalize_space(item)
            if item:
                result.append(item)
    return result


def validate_and_normalize_sample(sample: Any, chunk: Chunk) -> tuple[dict[str, Any] | None, str | None]:
    if not isinstance(sample, dict):
        return None, "sample_not_object"

    user_question = normalize_space(str(sample.get("user_question", "")))
    query_plan = sample.get("query_plan")
    if not user_question or not isinstance(query_plan, dict):
        return None, "missing_question_or_plan"

    primary_query = normalize_space(str(query_plan.get("primary_query", "")))
    secondary_queries = as_string_list(query_plan.get("secondary_queries"))
    must_keep_terms = as_string_list(query_plan.get("must_keep_terms"))
    answer_aspects = as_string_list(query_plan.get("answer_aspects"))
    intent = normalize_space(str(query_plan.get("intent", "")))

    if intent not in ALLOWED_INTENTS:
        return None, "invalid_intent"
    if not primary_query or len(primary_query) > 220:
        return None, "bad_primary_query"
    if len(secondary_queries) < 1 or len(secondary_queries) > 5:
        return None, "bad_secondary_queries"
    if len(must_keep_terms) < 2:
        return None, "too_few_must_keep_terms"
    if len(answer_aspects) < 1:
        return None, "missing_answer_aspects"

    searchable_text = f"{chunk.text} {user_question} {primary_query}".lower()
    matched_terms = [term for term in must_keep_terms if term.lower() in searchable_text]
    if len(matched_terms) < 2:
        return None, "must_keep_terms_not_grounded"

    normalized = {
        "source_file": chunk.source_file,
        "chunk_id": chunk.chunk_id,
        "chunk_text": chunk.text,
        "user_question": user_question,
        "query_plan": {
            "primary_query": primary_query,
            "secondary_queries": secondary_queries,
            "must_keep_terms": must_keep_terms,
            "intent": intent,
            "answer_aspects": answer_aspects,
        },
        "quality_reason": normalize_space(str(sample.get("quality_reason", ""))),
        "source_terms": as_string_list(sample.get("source_terms")),
    }
    return normalized, None


def to_alpaca(raw: dict[str, Any]) -> dict[str, str]:
    output = json.dumps(raw["query_plan"], ensure_ascii=False, separators=(",", ":"))
    return {
        "instruction": TRAINING_INSTRUCTION,
        "input": raw["user_question"],
        "output": output,
    }


def append_jsonl(path: Path, item: dict[str, Any]) -> None:
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")


def write_json(path: Path, item: Any) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(item, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def build_parser() -> argparse.ArgumentParser:
    root = project_root()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--md-dir", type=Path, default=root / "datas" / "md")
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent / "results")
    parser.add_argument("--target-samples", type=int, default=1000)
    parser.add_argument("--samples-per-chunk", type=int, default=3)
    parser.add_argument("--chunk-size", type=int, default=1200)
    parser.add_argument("--chunk-overlap", type=int, default=150)
    parser.add_argument("--min-chunk-chars", type=int, default=350)
    parser.add_argument("--max-chunks", type=int, default=None)
    parser.add_argument("--shuffle", action="store_true", help="Shuffle chunks before generation.")
    parser.add_argument("--seed", type=int, default=20260630)
    parser.add_argument("--dry-run", action="store_true", help="Only preview chunking; do not call Seed.")
    parser.add_argument("--resume", action="store_true", help="Continue from existing raw_seed_candidates.jsonl.")
    parser.add_argument("--model", default=os.getenv("SEED_MODEL", "doubao-seed-2-0-pro-260215"))
    parser.add_argument("--base-url", default=os.getenv("SEED_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"))
    parser.add_argument("--api-key-env", default=os.getenv("SEED_API_KEY_ENV", "ARK_API_KEY"))
    parser.add_argument("--temperature", type=float, default=0.3)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--save-every", type=int, default=20)
    parser.add_argument("--workers", type=int, default=1, help="Concurrent Seed API requests.")
    parser.add_argument("--max-failed-chunks", type=int, default=50, help="Abort after this many failed chunks to avoid wasting API calls.")
    return parser


def process_chunk_with_seed(
    client: Any,
    model: str,
    chunk: Chunk,
    samples_per_chunk: int,
    temperature: float,
) -> tuple[Chunk, list[Any] | None, str | None]:
    try:
        content = call_seed(
            client=client,
            model=model,
            chunk=chunk,
            num_samples=samples_per_chunk,
            temperature=temperature,
        )
        return chunk, extract_json_array(content), None
    except Exception as exc:  # Preserve failure context and keep generation moving.
        return chunk, None, repr(exc)



def main() -> int:
    env_paths = [project_root() / ".env", Path(__file__).resolve().parent / ".env"]
    if load_dotenv is not None:
        for env_path in env_paths:
            load_dotenv(env_path, override=False)
    else:
        for env_path in env_paths:
            load_env_fallback(env_path)

    args = build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    chunks = iter_chunks(args.md_dir, args.chunk_size, args.chunk_overlap, args.min_chunk_chars)
    if args.shuffle:
        random.seed(args.seed)
        random.shuffle(chunks)
    if args.max_chunks is not None:
        chunks = chunks[: args.max_chunks]

    print(f"[sft] md_dir={args.md_dir}")
    print(f"[sft] chunks={len(chunks)} chunk_size={args.chunk_size} overlap={args.chunk_overlap}")
    if chunks[:1]:
        print(f"[sft] first_chunk={chunks[0].chunk_id} chars={len(chunks[0].text)}")

    raw_path = args.output_dir / "raw_seed_candidates.jsonl"
    alpaca_path = args.output_dir / "llamafactory_alpaca.json"
    failed_path = args.output_dir / "failed_chunks.jsonl"
    summary_path = args.output_dir / "run_summary.json"

    if args.dry_run:
        preview = [asdict(chunk) | {"chars": len(chunk.text), "text": chunk.text[:500]} for chunk in chunks[:10]]
        write_json(args.output_dir / "dry_run_chunks_preview.json", preview)
        print(f"[sft] dry run wrote {args.output_dir / 'dry_run_chunks_preview.json'}")
        return 0

    api_key = os.getenv(args.api_key_env) or os.getenv("SEED_API_KEY") or os.getenv("ARK_API_KEY")
    if not api_key:
        print(
            f"[sft] missing API key env: {args.api_key_env}; also checked SEED_API_KEY and ARK_API_KEY",
            file=sys.stderr,
        )
        return 2

    if not args.resume:
        for path in (raw_path, alpaca_path, failed_path, summary_path):
            if path.exists():
                path.unlink()

    seen = load_seen_keys(raw_path) if args.resume else set()
    alpaca_rows = load_existing_alpaca(raw_path) if args.resume else []

    client = get_openai_client(api_key=api_key, base_url=args.base_url, timeout=args.timeout)
    counters: dict[str, int] = {
        "chunks_total": len(chunks),
        "chunks_attempted": 0,
        "seed_items": 0,
        "accepted": len(alpaca_rows),
        "duplicates": 0,
        "failed_chunks": 0,
    }
    reject_reasons: dict[str, int] = {}

    def handle_items(chunk: Chunk, items: list[Any]) -> None:
        counters["seed_items"] += len(items)
        for item in items:
            if counters["accepted"] >= args.target_samples:
                break
            normalized, reason = validate_and_normalize_sample(item, chunk)
            if normalized is None:
                assert reason is not None
                reject_reasons[reason] = reject_reasons.get(reason, 0) + 1
                continue

            key = sample_key(
                normalized["user_question"],
                normalized["query_plan"]["primary_query"],
            )
            if key in seen:
                counters["duplicates"] += 1
                continue
            seen.add(key)

            append_jsonl(raw_path, normalized)
            alpaca_rows.append(to_alpaca(normalized))
            counters["accepted"] += 1

    def handle_failure(chunk: Chunk, error: str) -> None:
        counters["failed_chunks"] += 1
        append_jsonl(
            failed_path,
            {
                "chunk_id": chunk.chunk_id,
                "source_file": chunk.source_file,
                "error": error,
            },
        )
        print(f"[sft] failed chunk={chunk.chunk_id}: {error}")

    if args.workers <= 1:
        for chunk in chunks:
            if counters["accepted"] >= args.target_samples:
                break

            counters["chunks_attempted"] += 1
            chunk, items, error = process_chunk_with_seed(
                client=client,
                model=args.model,
                chunk=chunk,
                samples_per_chunk=args.samples_per_chunk,
                temperature=args.temperature,
            )
            if error is not None:
                handle_failure(chunk, error)
                if counters["failed_chunks"] >= args.max_failed_chunks:
                    print(f"[sft] abort: failed_chunks reached {args.max_failed_chunks}")
                    break
                continue

            assert items is not None
            handle_items(chunk, items)

            if counters["chunks_attempted"] % args.save_every == 0:
                write_json(alpaca_path, alpaca_rows)
                write_json(summary_path, {"args": vars(args) | {"md_dir": str(args.md_dir), "output_dir": str(args.output_dir)}, "counters": counters, "reject_reasons": reject_reasons})
                print(f"[sft] accepted={counters['accepted']} attempted_chunks={counters['chunks_attempted']}")

            if args.sleep_seconds > 0:
                time.sleep(args.sleep_seconds)
    else:
        chunk_iter = iter(chunks)
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            inflight: dict[Any, Chunk] = {}

            def submit_next() -> bool:
                if counters["accepted"] >= args.target_samples:
                    return False
                try:
                    next_chunk = next(chunk_iter)
                except StopIteration:
                    return False
                counters["chunks_attempted"] += 1
                future = executor.submit(
                    process_chunk_with_seed,
                    client,
                    args.model,
                    next_chunk,
                    args.samples_per_chunk,
                    args.temperature,
                )
                inflight[future] = next_chunk
                return True

            while len(inflight) < args.workers and submit_next():
                pass

            while inflight and counters["accepted"] < args.target_samples:
                for future in as_completed(list(inflight.keys())):
                    inflight.pop(future, None)
                    chunk, items, error = future.result()
                    if error is not None:
                        handle_failure(chunk, error)
                        if counters["failed_chunks"] >= args.max_failed_chunks:
                            print(f"[sft] abort: failed_chunks reached {args.max_failed_chunks}")
                            inflight.clear()
                            break
                    else:
                        assert items is not None
                        handle_items(chunk, items)

                    if counters["chunks_attempted"] % args.save_every == 0 or counters["accepted"] >= args.target_samples:
                        write_json(alpaca_path, alpaca_rows)
                        write_json(summary_path, {"args": vars(args) | {"md_dir": str(args.md_dir), "output_dir": str(args.output_dir)}, "counters": counters, "reject_reasons": reject_reasons})
                        print(f"[sft] accepted={counters['accepted']} attempted_chunks={counters['chunks_attempted']}")

                    while len(inflight) < args.workers and counters["failed_chunks"] < args.max_failed_chunks and submit_next():
                        if args.sleep_seconds > 0:
                            time.sleep(args.sleep_seconds)
                    break

    write_json(alpaca_path, alpaca_rows)
    write_json(summary_path, {"args": vars(args) | {"md_dir": str(args.md_dir), "output_dir": str(args.output_dir)}, "counters": counters, "reject_reasons": reject_reasons})
    print(f"[sft] done accepted={counters['accepted']} raw={raw_path} alpaca={alpaca_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
