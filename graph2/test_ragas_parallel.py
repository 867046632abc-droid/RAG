"""
Benchmark: serial vs parallel build_samples in ragas_eval.py

Mock out run_graph2_once with a configurable sleep to simulate LLM API latency,
then measure wall-clock time and verify result correctness.

Run from project root:
    python -m graph2.test_ragas_parallel
"""
from __future__ import annotations

import sys
import threading
import time
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Minimal stubs so ragas_eval imports without real LLM / LangGraph packages
# ---------------------------------------------------------------------------

_stub_modules = {
    "graph2.generate_node2": MagicMock(),
    "graph2.grade_answer_chain": MagicMock(),
    "graph2.grade_documents_node": MagicMock(),
    "graph2.grade_hallucinations_chain": MagicMock(),
    "graph2.query_route_chain": MagicMock(),
    "graph2.transform_query_node": MagicMock(),
    "graph2.web_search_node": MagicMock(),
    "langchain_core.documents": MagicMock(),
    "langchain_core.prompts": MagicMock(),
    "langgraph.constants": MagicMock(END="__end__", START="__start__"),
    "langgraph.errors": MagicMock(),
    "langgraph.graph": MagicMock(),
    "llm_models.all_llm": MagicMock(),
    "llm_models.embeddings_model": MagicMock(),
    "pydantic": MagicMock(),
}
for mod_name, stub in _stub_modules.items():
    sys.modules.setdefault(mod_name, stub)

# Provide Document as a simple namedtuple-like class
import types
lc_doc_mod = types.ModuleType("langchain_core.documents")


class Document:
    def __init__(self, page_content: str = "", metadata: dict | None = None):
        self.page_content = page_content
        self.metadata = metadata or {}


lc_doc_mod.Document = Document
sys.modules["langchain_core.documents"] = lc_doc_mod

import importlib
import graph2.ragas_eval as ragas_eval  # noqa: E402  (import after stubs)

# ---------------------------------------------------------------------------
# Shared test helpers
# ---------------------------------------------------------------------------

SIMULATED_LATENCY = 0.5   # seconds per case (simulates an API round-trip)
TEST_CASE_COUNT = 8        # how many cases to benchmark


def _make_fake_test_cases(n: int) -> list[dict[str, Any]]:
    return [
        {
            "question": f"What is concept #{i}?",
            "reference": f"Answer #{i}",
            "reference_contexts": [f"Context #{i}"],
        }
        for i in range(n)
    ]


def _fake_run_graph2_once(question: str) -> tuple[str, list[str]]:
    """Simulate a slow LLM call."""
    time.sleep(SIMULATED_LATENCY)
    return f"Answer for: {question}", [f"ctx: {question}"]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestBuildSamplesParallel(unittest.TestCase):

    def _run_build_samples(self, max_workers: int) -> tuple[list[dict], float]:
        fake_corpus = ragas_eval._IndexedCorpus(
            docs=[Document(page_content=f"doc {i}") for i in range(TEST_CASE_COUNT)],
            token_sets=[{f"doc", str(i)} for i in range(TEST_CASE_COUNT)],
        )
        test_cases = _make_fake_test_cases(TEST_CASE_COUNT)

        original_count = ragas_eval.CASE_COUNT
        ragas_eval.CASE_COUNT = TEST_CASE_COUNT

        with (
            patch.object(ragas_eval, "_ensure_corpus", return_value=fake_corpus),
            patch.object(ragas_eval, "build_test_cases", return_value=test_cases),
            patch.object(ragas_eval, "run_graph2_once", side_effect=_fake_run_graph2_once),
        ):
            t0 = time.perf_counter()
            samples = ragas_eval.build_samples(output_dir=None, max_workers=max_workers)
            elapsed = time.perf_counter() - t0

        ragas_eval.CASE_COUNT = original_count
        return samples, elapsed

    # ------------------------------------------------------------------
    def test_serial_baseline(self):
        """Workers=1 behaves like the old serial loop."""
        samples, elapsed = self._run_build_samples(max_workers=1)
        self.assertEqual(len(samples), TEST_CASE_COUNT)
        expected_min = SIMULATED_LATENCY * TEST_CASE_COUNT
        self.assertGreaterEqual(elapsed, expected_min * 0.9,
            f"Serial run too fast ({elapsed:.2f}s < {expected_min:.2f}s)")
        print(f"\n[serial  ] elapsed={elapsed:.2f}s  expected>={expected_min:.2f}s  OK")

    def test_parallel_speedup(self):
        """Workers=4 should finish noticeably faster than serial."""
        _, serial_elapsed = self._run_build_samples(max_workers=1)
        samples, parallel_elapsed = self._run_build_samples(max_workers=4)

        speedup = serial_elapsed / parallel_elapsed
        print(
            f"\n[parallel] elapsed={parallel_elapsed:.2f}s  "
            f"serial={serial_elapsed:.2f}s  speedup={speedup:.2f}x"
        )
        self.assertEqual(len(samples), TEST_CASE_COUNT)
        self.assertGreater(speedup, 1.8,
            f"Expected >1.8x speedup, got {speedup:.2f}x")

    def test_result_order_preserved(self):
        """Output list must be in the same order as test_cases (not completion order)."""
        samples, _ = self._run_build_samples(max_workers=4)
        for i, sample in enumerate(samples):
            self.assertIn(str(i), sample["user_input"],
                f"Sample #{i} out of order: {sample['user_input']!r}")

    def test_no_missing_samples(self):
        """Every test case must produce exactly one sample."""
        samples, _ = self._run_build_samples(max_workers=4)
        self.assertEqual(len(samples), TEST_CASE_COUNT)
        for sample in samples:
            self.assertIn("user_input", sample)
            self.assertIn("response", sample)
            self.assertIn("retrieved_contexts", sample)
            self.assertIn("reference", sample)

    def test_thread_safety_no_duplicates(self):
        """Run twice concurrently; neither run should produce duplicate questions."""
        results: list[list[dict]] = [[], []]
        errors: list[Exception] = []

        def _run(slot: int):
            try:
                samples, _ = self._run_build_samples(max_workers=4)
                results[slot] = samples
            except Exception as exc:
                errors.append(exc)

        t1 = threading.Thread(target=_run, args=(0,))
        t2 = threading.Thread(target=_run, args=(1,))
        t1.start(); t2.start()
        t1.join(); t2.join()

        self.assertFalse(errors, f"Thread errors: {errors}")
        for slot, samples in enumerate(results):
            questions = [s["user_input"] for s in samples]
            self.assertEqual(len(questions), len(set(questions)),
                f"Slot {slot} has duplicate questions")


# ---------------------------------------------------------------------------
# Standalone benchmark report (not a unittest)
# ---------------------------------------------------------------------------

def run_benchmark():
    print("=" * 60)
    print("  ragas_eval.build_samples  parallel benchmark")
    print(f"  cases={TEST_CASE_COUNT}  simulated_latency={SIMULATED_LATENCY}s/case")
    print("=" * 60)

    fake_corpus = ragas_eval._IndexedCorpus(
        docs=[Document(page_content=f"doc {i}") for i in range(TEST_CASE_COUNT)],
        token_sets=[{"doc", str(i)} for i in range(TEST_CASE_COUNT)],
    )
    test_cases = _make_fake_test_cases(TEST_CASE_COUNT)
    original_count = ragas_eval.CASE_COUNT
    ragas_eval.CASE_COUNT = TEST_CASE_COUNT

    results_table: list[tuple[int, float, float]] = []

    for workers in (1, 2, 4, 8):
        with (
            patch.object(ragas_eval, "_ensure_corpus", return_value=fake_corpus),
            patch.object(ragas_eval, "build_test_cases", return_value=test_cases),
            patch.object(ragas_eval, "run_graph2_once", side_effect=_fake_run_graph2_once),
        ):
            t0 = time.perf_counter()
            samples = ragas_eval.build_samples(output_dir=None, max_workers=workers)
            elapsed = time.perf_counter() - t0

        ideal = (SIMULATED_LATENCY * TEST_CASE_COUNT) / workers
        results_table.append((workers, elapsed, ideal))
        assert len(samples) == TEST_CASE_COUNT

    ragas_eval.CASE_COUNT = original_count

    serial_elapsed = results_table[0][1]
    print(f"\n{'workers':>8}  {'elapsed(s)':>12}  {'ideal(s)':>10}  {'speedup':>9}  {'efficiency':>10}")
    print("-" * 60)
    for workers, elapsed, ideal in results_table:
        speedup = serial_elapsed / elapsed
        efficiency = speedup / workers * 100
        print(f"{workers:>8}  {elapsed:>12.2f}  {ideal:>10.2f}  {speedup:>9.2f}x  {efficiency:>9.1f}%")

    print("\nNotes:")
    print("  ideal   = total_latency / workers  (perfect linear scaling)")
    print("  speedup = serial_elapsed / this_elapsed")
    print("  efficiency = speedup / workers * 100%")
    print("\n[OK] All samples produced correctly in all configurations.")


if __name__ == "__main__":
    run_benchmark()
    print("\n" + "=" * 60)
    print("  Running unittest suite")
    print("=" * 60 + "\n")
    unittest.main(argv=[__file__, "-v"], exit=False)
