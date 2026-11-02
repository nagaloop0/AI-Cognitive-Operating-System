# Evaluation of the local AI features

Run on 2026-11-02 10:36 on an Apple M2 (16 GB), all models local via Ollama.
Reproduce: `venv/bin/python -m scripts.evaluate --models llama3.2:3b qwen2.5:7b`
What changed because of these numbers: [evaluation_history.md](evaluation_history.md)

## 1. Title categories

The category prompt was tuned while looking at the 30 labelled titles, so that score is optimistic.
The 15 held-out titles were written afterwards and never used for tuning: that is the fairer score.

| Model | Tuning set (30) | Held-out set (15) | Time (tuning set) |
| --- | --- | --- | --- |
| llama3.2:3b | 87% (26/30) | 67% (10/15) | 24.5 s |
| qwen2.5:7b | 97% (29/30) | 80% (12/15) | 33.6 s |

Mistakes of llama3.2:3b (tuning set): Work visa requirements - Official guide: expected learning, got work; FastAPI dependency injection - FastAPI docs: expected learning, got work; Testing - FastAPI: expected learning, got work; tasks.py — explore_p: expected work, got learning
Mistakes of qwen2.5:7b (tuning set): Work visa requirements - Official guide: expected learning, got work

Mistakes of llama3.2:3b (held-out set): How to use Python decorators - Real Python: expected learning, got work; Docker networking explained - YouTube: expected learning, got work; PostgreSQL indexes - Official documentation: expected learning, got work; Introduction to statistics - Coursera: expected learning, got work; Booking.com: Hotels in Lisbon: expected other, got fun
Mistakes of qwen2.5:7b (held-out set): Pull request #142: Fix login redirect - GitHub: expected work, got other; Jira - Sprint board: expected work, got other; Introduction to statistics - Coursera: expected learning, got fun

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

Grounding = share of focus areas that reuse at least one word (4+ letters) from that day's window titles.
It only checks that the topics come from the data; it does not check that the insight or suggestion is true.
Those are rated by hand in docs/evaluation_samples.local.md.

| Day | Model | Time | Source | Attempts | Grounding |
| --- | --- | --- | --- | --- | --- |
| 2026-11-02 | llama3.2:3b | 9.8 s | llm | 1 | 100% |
| 2026-11-02 | qwen2.5:7b | 33.6 s | llm | 1 | 100% |
| 2026-10-29 | llama3.2:3b | 18.6 s | llm | 1 | 100% |
| 2026-10-29 | qwen2.5:7b | 57.6 s | llm | 1 | 100% |
| 2026-10-28 | llama3.2:3b | 16.2 s | llm | 1 | 100% |
| 2026-10-28 | qwen2.5:7b | 35.6 s | llm | 1 | 75% |
| 2026-10-22 | llama3.2:3b | 14.3 s | llm | 1 | 75% |
| 2026-10-22 | qwen2.5:7b | 38.5 s | llm | 1 | 100% |
| 2026-10-21 | llama3.2:3b | 11.3 s | llm | 1 | 50% |
| 2026-10-21 | qwen2.5:7b | 24.8 s | llm | 1 | 100% |

- llama3.2:3b: average 14.1 s per summary, average grounding 85%, 5/5 valid on the first try.
- qwen2.5:7b: average 38.0 s per summary, average grounding 95%, 5/5 valid on the first try.

## 4. Cached summary

A summary that was already generated is read from PostgreSQL without calling the model: median 0.4 ms, max 2.5 ms over 20 reads (day 2026-10-29; the HTTP request adds a few ms on top).
