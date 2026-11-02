# Evaluation history: what was measured, what changed

Each row is one change made because of a measurement. Latest numbers: [evaluation.md](evaluation.md).

| Date | Area | Measured before | Change | Measured after |
| --- | --- | --- | --- | --- |
| 2026-11-02 | Summary prompt | Headlines like "Activity Report for Thursday"; focus areas were app names ("Used Notes") | Rules moved into JSON-schema field descriptions; examples taken from an unrelated day (the 3B model copied a matching example word for word) | Focus areas are real topics from titles (`ai-project.md`, `style.css`); grounding 100% on 5 real days |
| 2026-11-02 | RAG answers | Model invented "worked on it Wednesday in Chrome" when no source passed the 60 s filter | Sources from 10 s with honest seconds; "No window titles match the question" stated in the context; similarity cut-off 0.55 to 0.60 | "Did I go to the gym yesterday?" answers "I can't find that in your history." |
| 2026-11-02 | Categories prompt (llama3.2:3b) | 70% (21/30): tutorials and docs labelled "fun", job search "communication" | Explicit rules: docs, Wikipedia, tutorials = learning; job search = work; decide by topic, not app | 87% (26/30) |
| 2026-11-02 | Categories schema | qwen2.5:7b 0%: it answered `{"labels": []}`, which the schema allowed | `minItems` = `maxItems` = batch size in the JSON schema | qwen2.5:7b 90% (27/30) |
| 2026-11-02 | Task grouping | Pairwise F1 0.18 (best threshold 0.80) with "App: title" embedded; every browser tab looked alike | Embed the title only; threshold 0.70 | F1 0.28 |
| 2026-11-02 | Labelled set | Some test titles contained personal details | Replaced with neutral titles (resume.pdf, cover_letter.docx, "Work visa requirements") and re-ran everything | Categories: llama3.2:3b 87% (26/30), qwen2.5:7b 97% (29/30); grouping F1 0.28 unchanged; summaries 5/5 valid (llama 8.6 s, qwen 22.0 s) |
| 2026-11-02 | Held-out test set | Category scores were measured only on the 30 titles the prompt was tuned on | Added 15 new titles never used for tuning; also measured the cached-summary time | Held-out: llama3.2:3b 67% (10/15), qwen2.5:7b 80% (12/15), vs 87% / 97% on the tuning set: the prompt partly fits the tuning titles. llama mostly labels tutorials and docs as work. Cached summary: median 0.4 ms (database read) |

## Decisions

- **Default model stays llama3.2:3b for summaries.** qwen2.5:7b takes about 2.5 to 2.7 times longer per summary
  (latest run 38.0 s vs 14.1 s; earlier 22.0 s vs 8.6 s, timings vary with machine load). For categories qwen is only
  about 1.4 times slower (33.6 s vs 24.5 s for 30 titles). Switch with `LLM_MODEL` in `.env`.
- **Categories: qwen is the better choice (open).** On the held-out set qwen scores 80% vs 67% for llama, and labels
  are made once per title and cached, so speed matters little. A separate category model setting is not built yet.
- **One vector per title.** nomic-embed-text with its `clustering:` prefix reached F1 0.32 vs 0.28, but needs a second
  vector per title, because search must use `search_document:`. Not worth double storage yet.

## Known limits

- Task grouping by title similarity is weak for tasks whose titles share no words (job search = CV + LinkedIn ad +
  visa page + cover letter). Next step: let the LLM merge groups using the day's context.
- Category accuracy on unseen titles is clearly lower than on the tuning set (llama 67% vs 87%); the 15-title
  held-out set is small, so treat these numbers as rough.
- Grounding only checks that focus areas reuse words from window titles, not that the insight is true.
