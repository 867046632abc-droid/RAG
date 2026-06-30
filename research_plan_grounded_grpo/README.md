# Grounded RAG Tool-Use Post-Training Research Plan

本文件夹是一套论文导向的 LLM post-training 研究方案，面向已有 `RAG_PROJECT` baseline，而不是从零搭建 demo。

项目核心方向：

- 可靠工具调用
- grounded RAG QA
- 引用忠实性
- 拒答校准
- H20 单卡或少量 H20 可执行的 SFT/DPO/GRPO 后训练

建议论文暂定题目：

> Evidence-Grounded GRPO for Reliable Tool-Using RAG Question Answering with Faithful Citations and Calibrated Refusal

核心 claim：

> 在固定 RAG 工具环境中，使用多目标、可验证、证据约束的 GRPO reward，可以比仅 SFT 或 SFT+DPO 更有效降低 hallucination 和无依据引用，同时通过 refusal calibration reward 抑制 citation reward 带来的过度拒答。

文件结构：

| 文件 | 内容 |
| --- | --- |
| [00_research_overview.md](00_research_overview.md) | 研究总览、核心假设、最小可发表版本 |
| [01_research_questions_and_innovations.md](01_research_questions_and_innovations.md) | 研究问题与创新点 |
| [02_technical_route_h20.md](02_technical_route_h20.md) | H20 资源下的模型、LoRA、框架和训练路线 |
| [03_data_design.md](03_data_design.md) | 数据构造、划分、防泄漏和泛化评估 |
| [04_grpo_design.md](04_grpo_design.md) | GRPO rollout、reward、group sampling 和 reward hacking 防控 |
| [05_experiments_and_metrics.md](05_experiments_and_metrics.md) | 实验矩阵、指标、评测器分工 |
| [06_paper_outline.md](06_paper_outline.md) | 论文大纲、图表、核心叙事 |
| [07_roadmap_and_deliverables.md](07_roadmap_and_deliverables.md) | 10 周计划、风险、pivot 和最终产出 |

外部技术参考：

- Hugging Face TRL GRPOTrainer documentation: https://huggingface.co/docs/trl/main/en/grpo_trainer
- Qwen3 model collection: https://huggingface.co/collections/Qwen/qwen3-67dd247413f0e2e4f653967f
- Qwen2.5 model collection: https://huggingface.co/collections/Qwen/qwen25-66e81a666513e518adb90d9e

