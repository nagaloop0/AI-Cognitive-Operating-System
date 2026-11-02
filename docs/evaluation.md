# Evaluation of the local AI features

Run on 2026-11-02 09:58 on an Apple M2 (16 GB), all models local via Ollama.
Reproduce: `venv/bin/python -m scripts.evaluate --models llama3.2:3b qwen2.5:7b`
What changed because of these numbers: [evaluation_history.md](evaluation_history.md)

## 1. Title categories (30 labelled titles)

| Model | Accuracy | Correct | Time |
| --- | --- | --- | --- |
| llama3.2:3b | 87% | 26/30 | 23.3 s |
| qwen2.5:7b | 97% | 29/30 | 33.3 s |

Mistakes of llama3.2:3b: Work visa requirements - Official guide: expected learning, got work; FastAPI dependency injection - FastAPI docs: expected learning, got work; Testing - FastAPI: expected learning, got work; tasks.py — explore_p: expected work, got learning
Mistakes of qwen2.5:7b: Work visa requirements - Official guide: expected learning, got work

## 2. Task grouping with embeddings (nomic-embed-text, pairwise scores)

| Similarity threshold | Groups | Precision | Recall | F1 |
| --- | --- | --- | --- | --- |
| 0.60 | 2 | 6% | 100% | 0.12 |
| 0.65 | 11 | 8% | 50% | 0.13 |
| 0.70 | 20 | 24% | 35% | 0.28 |
| 0.75 | 24 | 19% | 12% | 0.14 |
| 0.80 | 24 | 19% | 12% | 0.14 |
| 0.85 | 27 | 25% | 4% | 0.07 |
| 0.90 | 29 | 100% | 4% | 0.07 |

Best F1 at threshold 0.70 (12 true tasks in the labelled set).

## 3. Daily summaries on real days

Grounding = share of focus areas that use words from that day's window titles.

| Day | Model | Time | Source | Attempts | Grounding |
| --- | --- | --- | --- | --- | --- |
| 2026-11-02 | llama3.2:3b | 6.0 s | llm | 1 | 75% |
| 2026-11-02 | qwen2.5:7b | 17.2 s | llm | 1 | 100% |
| 2026-10-29 | llama3.2:3b | 8.6 s | llm | 1 | 100% |
| 2026-10-29 | qwen2.5:7b | 22.7 s | llm | 1 | 100% |
| 2026-10-28 | llama3.2:3b | 7.1 s | llm | 1 | 100% |
| 2026-10-28 | qwen2.5:7b | 20.4 s | llm | 1 | 75% |
| 2026-10-22 | llama3.2:3b | 13.2 s | llm | 1 | 75% |
| 2026-10-22 | qwen2.5:7b | 27.8 s | llm | 1 | 100% |
| 2026-10-21 | llama3.2:3b | 8.2 s | llm | 1 | 100% |
| 2026-10-21 | qwen2.5:7b | 21.9 s | llm | 1 | 100% |

- llama3.2:3b: average 8.6 s per summary, average grounding 90%, 5/5 valid on the first try.
- qwen2.5:7b: average 22.0 s per summary, average grounding 95%, 5/5 valid on the first try.
