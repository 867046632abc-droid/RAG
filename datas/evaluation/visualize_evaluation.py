

import json
import warnings
from pathlib import Path

import matplotlib
import matplotlib.gridspec as gridspec
import matplotlib.pyplot as plt
import numpy as np

warnings.filterwarnings("ignore")

# ── Windows Chinese font support ──────────────────────────────────────────────
matplotlib.rcParams["font.sans-serif"] = [
    "Microsoft YaHei", "SimHei", "Arial Unicode MS", "DejaVu Sans"
]
matplotlib.rcParams["axes.unicode_minus"] = False

# ── Constants ─────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent

METRICS = ["faithfulness", "answer_relevancy", "context_precision", "context_recall"]

METRIC_CN = {
    "faithfulness":      "忠实度",
    "answer_relevancy":  "答案相关性",
    "context_precision": "上下文精度",
    "context_recall":    "上下文召回",
}

METRIC_COLORS = {
    "faithfulness":      "#1976D2",
    "answer_relevancy":  "#F57C00",
    "context_precision": "#388E3C",
    "context_recall":    "#D32F2F",
}

# Ordered run configs: (subfolder, display_label, short_desc)
RUN_CONFIGS = [
    ("第1次结果",                       "R1",         "初始版本"),
    ("第2次结果",                       "R2",         "改进召回"),
    ("第3次结果",                       "R3",         "优化检索"),
    ("第4次结果",                       "R4",         "调参v1"),
    ("第5次结果",                       "R5",         "调参v2"),
    # 第6次 — 无完整结果
    ("第7次结果",                       "R7",         "重构检索"),
    ("第8次结果",                       "R8",         "优化重排"),
    # 第9次 — 无完整结果
    ("第10次结果",                      "R10",        "深度优化"),
    ("第11次结果-显著提升-4o-mini版",   "R11\n4o-mini", "最优4o-mini"),
    ("第13次结果-gpt4o-mini",           "R13\n4o-mini", "最终版本"),
]


# ── Data loading ──────────────────────────────────────────────────────────────

def _parse_summary(data: dict) -> dict:
    """Normalize both old (flat mean) and new (nested dict) summary formats."""
    result = {}
    for m in METRICS:
        if m in data and isinstance(data[m], dict):
            result[m]              = data[m].get("mean")
            result[f"{m}_std"]     = data[m].get("std")
            result[f"{m}_pass_rate"] = data[m].get("pass_rate")
        elif f"{m}_mean" in data:
            result[m]              = data[f"{m}_mean"]
            result[f"{m}_std"]     = None
            result[f"{m}_pass_rate"] = None
        else:
            result[m]              = None
            result[f"{m}_std"]     = None
            result[f"{m}_pass_rate"] = None
    return result


def load_runs(base_dir: Path) -> list[dict]:
    runs = []
    for folder, label, desc in RUN_CONFIGS:
        folder_path = base_dir / folder
        if not folder_path.exists():
            continue
        summary_files = sorted(folder_path.glob("*_summary_*.json"))
        if not summary_files:
            continue
        with open(summary_files[0], encoding="utf-8") as f:
            data = json.load(f)
        run = {"label": label, "desc": desc, "folder": folder}
        run.update(_parse_summary(data))
        runs.append(run)
    return runs


def overall_score(run: dict) -> float:
    vals = [run[m] for m in METRICS if run[m] is not None]
    return float(np.mean(vals)) if vals else float("nan")


# ── Chart 1 — Iterative trend ─────────────────────────────────────────────────

def plot_trend(ax, runs: list[dict]) -> None:
    x = np.arange(len(runs))
    x_labels = [r["label"].replace("\n", "\n") for r in runs]

    for m in METRICS:
        y = [r[m] if r[m] is not None else np.nan for r in runs]
        ax.plot(x, y, marker="o", linewidth=2.2, markersize=6,
                color=METRIC_COLORS[m], label=METRIC_CN[m], zorder=3)

    # Composite score line
    scores = [overall_score(r) for r in runs]
    ax.plot(x, scores, marker="D", linewidth=1.5, markersize=5,
            color="#7B1FA2", linestyle="--", label="综合均分", alpha=0.7, zorder=2)

    best_idx = int(np.nanargmax(scores))
    ax.annotate(
        f"  综合最优\n  {scores[best_idx]:.3f}",
        xy=(best_idx, scores[best_idx]),
        xytext=(best_idx + 0.3, scores[best_idx] - 0.06),
        fontsize=7.5, color="#7B1FA2",
        arrowprops=dict(arrowstyle="->", color="#7B1FA2", lw=1),
    )

    ax.set_xticks(x)
    ax.set_xticklabels(x_labels, fontsize=8)
    ax.set_ylim(0.55, 1.08)
    ax.set_ylabel("评分", fontsize=10)
    ax.set_title("各轮次评估指标迭代趋势", fontsize=12, fontweight="bold", pad=10)
    ax.legend(loc="lower right", fontsize=7.5, framealpha=0.8, ncol=3)
    ax.grid(True, alpha=0.3, linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)


# ── Chart 2 — Radar ───────────────────────────────────────────────────────────

def plot_radar(ax, runs: list[dict]) -> None:
    # Pick last 4 runs with full data
    complete = [r for r in runs if all(r[m] is not None for m in METRICS)]
    selected = complete[-4:]

    N = len(METRICS)
    angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
    angles += angles[:1]
    cn_labels = [METRIC_CN[m] for m in METRICS]

    palette = ["#1976D2", "#D32F2F", "#388E3C", "#F57C00"]

    for i, run in enumerate(selected):
        vals = [run[m] for m in METRICS]
        vals += vals[:1]
        label_str = run["label"].replace("\n", " ")
        ax.plot(angles, vals, "o-", linewidth=2, color=palette[i],
                label=label_str, markersize=5)
        ax.fill(angles, vals, alpha=0.12, color=palette[i])

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(cn_labels, fontsize=9)
    ax.set_ylim(0.6, 1.0)
    ax.set_yticks([0.65, 0.75, 0.85, 0.95, 1.0])
    ax.set_yticklabels(["0.65", "0.75", "0.85", "0.95", "1.00"], fontsize=6.5)
    ax.set_title("最终配置多维性能对比", fontsize=12, fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.45, 1.18), fontsize=8)
    ax.grid(True, alpha=0.4)


# ── Chart 3 — Model comparison (gpt-5.4 vs gpt-4o-mini) ─────────────────────

_MODEL_CONFIGS = {
    "gpt-4o-mini": [
        "第11次结果-显著提升-4o-mini版",
        "第13次结果-gpt4o-mini",
    ],
    "gpt-5.4": [
        "第11次结果-gpt5.4",
        "第12次结果-gpt5.4",
    ],
}

_MODEL_COLORS = {
    "gpt-4o-mini": "#1976D2",
    "gpt-5.4":     "#D32F2F",
}


def _load_model_runs(base_dir: Path) -> dict[str, list[dict]]:
    result = {}
    for model, folders in _MODEL_CONFIGS.items():
        runs = []
        for folder in folders:
            p = base_dir / folder
            if not p.exists():
                continue
            files = sorted(p.glob("*_summary_*.json"))
            if not files:
                continue
            with open(files[0], encoding="utf-8") as f:
                data = json.load(f)
            run = {"label": folder, "model": model}
            run.update(_parse_summary(data))
            runs.append(run)
        result[model] = runs
    return result


def plot_model_comparison(ax, base_dir: Path) -> None:
    model_runs = _load_model_runs(base_dir)

    x = np.arange(len(METRICS))
    width = 0.32
    offsets = {"gpt-4o-mini": -width / 2 - 0.04, "gpt-5.4": width / 2 + 0.04}

    y_bottom = 0.6
    all_means: dict[str, list[float]] = {}
    for model, runs in model_runs.items():
        if not runs:
            continue
        color = _MODEL_COLORS[model]

        means = []
        for m in METRICS:
            vals = [r[m] for r in runs if r[m] is not None]
            means.append(float(np.mean(vals)) if vals else 0.0)
        all_means[model] = means

        bars = ax.bar(
            x + offsets[model], means, width,
            color=color, alpha=0.85, label=model, zorder=3,
        )

        # Value labels centered inside the visible portion of each bar (white text)
        for bar, mean in zip(bars, means):
            label_y = y_bottom + (mean - y_bottom) / 2
            ax.text(
                bar.get_x() + bar.get_width() / 2, label_y,
                f"{mean:.3f}",
                ha="center", va="center",
                fontsize=9, color="white", fontweight="bold",
            )

    # Delta annotations above the taller bar for each metric
    mini_means  = all_means.get("gpt-4o-mini", [])
    gpt54_means = all_means.get("gpt-5.4", [])
    if mini_means and gpt54_means:
        for j in range(len(METRICS)):
            delta = mini_means[j] - gpt54_means[j]
            sign  = "▲" if delta > 0 else "▼"
            color = "#1976D2" if delta > 0 else "#D32F2F"
            top_y = max(mini_means[j], gpt54_means[j])
            ax.text(x[j], top_y + 0.016,
                    f"{sign}{abs(delta):.3f}",
                    ha="center", va="bottom",
                    fontsize=9, color=color, fontweight="bold")

    ax.axhline(y=0.8, color="#888888", linestyle="--", alpha=0.5, linewidth=1.2, zorder=0)
    ax.text(len(METRICS) - 0.5, 0.805, "0.80 基准线",
            fontsize=7.5, color="#888888", ha="right")

    ax.set_xticks(x)
    ax.set_xticklabels([METRIC_CN[m] for m in METRICS], fontsize=11)
    ax.set_ylim(y_bottom, 1.12)
    ax.set_ylabel("评分均值", fontsize=10)
    ax.set_title("模型选型对比：gpt-5.4 vs gpt-4o-mini",
                 fontsize=12, fontweight="bold", pad=10)
    ax.legend(fontsize=10, loc="upper left", framealpha=0.85)
    ax.grid(True, alpha=0.3, axis="y", linestyle="--")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)



# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    runs = load_runs(BASE_DIR)
    if not runs:
        print("No evaluation summaries found.")
        return
    print(f"Loaded {len(runs)} valid evaluation runs.")

    output_dir = BASE_DIR / "figures"
    output_dir.mkdir(exist_ok=True)

    fig = plt.figure(figsize=(18, 12), facecolor="white")
    fig.suptitle(
        "RAG System Evaluation Dashboard\n"
        "知识图谱增强检索系统 · RAGAS 多轮评估报告",
        fontsize=15, fontweight="bold", y=0.995,
    )

    gs = gridspec.GridSpec(2, 1, figure=fig, hspace=0.50)
    ax1 = fig.add_subplot(gs[0])
    ax3 = fig.add_subplot(gs[1])

    plot_trend(ax1, runs)
    plot_model_comparison(ax3, BASE_DIR)


    # Footer — best run summary
    best = max(runs, key=overall_score)
    footer = (
        f"综合最优: {best['desc']}  |  "
        + "  |  ".join(
            f"{METRIC_CN[m]}: {best[m]:.4f}" for m in METRICS if best[m] is not None
        )
        + f"  |  综合均分: {overall_score(best):.4f}"
    )
    fig.text(
        0.5, 0.003, footer, ha="center", fontsize=8.5, color="#444444",
        bbox=dict(boxstyle="round,pad=0.35", facecolor="#F5F5F5", alpha=0.9),
    )

    out_path = output_dir / "rag_evaluation_dashboard.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor="white")
    print(f"Dashboard saved → {out_path}")
    plt.show()


if __name__ == "__main__":
    main()
