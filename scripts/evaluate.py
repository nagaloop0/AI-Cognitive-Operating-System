"""
Evaluation of the AI features on this Mac (needs Ollama running and the models pulled).

1. Categories: accuracy of each model on a labelled set of 30 window titles.
2. Task grouping: pairwise precision / recall / F1 of embedding clusters at several similarity thresholds.
3. Daily summaries: on your most recent real days, per model: time, valid-JSON attempts, and grounding
   (share of focus areas that use words from the day's window titles).

Results (numbers only) -> docs/evaluation.md, safe to commit.
Summary texts for rating by hand -> docs/evaluation_samples.local.md (git-ignored: contains your titles).

Run: venv/bin/python -m scripts.evaluate --models llama3.2:3b qwen2.5:7b
"""
import argparse
import json
import re
import time
from datetime import date, datetime
from itertools import combinations
from pathlib import Path

import numpy as np
from sqlalchemy import func

from backend.categories import BATCH_SIZE, classify_titles
from backend.database import SessionLocal
from backend.digest import build_day_digest
from backend.llm_client import LLMClient
from backend.models import AppActivity
from backend.settings import load_settings
from backend.summary import generate_summary
from backend.tasks import DOCUMENT_PREFIX, cluster, title_text
from backend.timeutil import as_utc, local_tz

ROOT = Path(__file__).resolve().parent.parent
LABELLED = ROOT / "scripts" / "eval_data" / "labelled_titles.json"
RESULTS = ROOT / "docs" / "evaluation.md"
SAMPLES = ROOT / "docs" / "evaluation_samples.local.md"
THRESHOLDS = [0.60, 0.65, 0.70, 0.75, 0.80, 0.85, 0.90]
WORD = re.compile(r"[a-z0-9_]{4,}")


def evaluate_categories(model: str, items: list[dict]) -> dict:
    llm = LLMClient(model=model)
    pairs = [(item["app"], item["title"]) for item in items]
    predicted: dict[int, str] = {}
    start = time.perf_counter()
    for offset in range(0, len(pairs), BATCH_SIZE):
        labels = classify_titles(llm, pairs[offset:offset + BATCH_SIZE])
        predicted.update({offset + i: category for i, category in labels.items()})
    seconds = time.perf_counter() - start
    correct = sum(predicted.get(i) == item["category"] for i, item in enumerate(items))
    mistakes = [f'{item["title"]}: expected {item["category"]}, got {predicted.get(i, "nothing")}'
                for i, item in enumerate(items) if predicted.get(i) != item["category"]]
    return {"model": model, "accuracy": correct / len(items), "correct": correct, "total": len(items),
            "seconds": seconds, "mistakes": mistakes}


def evaluate_grouping(items: list[dict]) -> list[dict]:
    llm = LLMClient()
    vectors = np.array(llm.embed([DOCUMENT_PREFIX + title_text(i["title"]) for i in items]))
    truth = {(a, b) for a, b in combinations(range(len(items)), 2) if items[a]["task"] == items[b]["task"]}
    rows = []
    for threshold in THRESHOLDS:
        groups = cluster(vectors, threshold)
        predicted = {tuple(sorted(pair)) for group in groups for pair in combinations(group, 2)}
        tp = len(predicted & truth)
        precision = tp / len(predicted) if predicted else 0.0
        recall = tp / len(truth) if truth else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        rows.append({"threshold": threshold, "groups": len(groups), "precision": precision, "recall": recall, "f1": f1})
    return rows


def recent_days(db, limit: int) -> list[date]:
    starts = [as_utc(row[0]).astimezone(local_tz()).date()
              for row in db.query(func.min(AppActivity.start_time)).group_by(func.date(AppActivity.start_time))]
    return sorted(set(starts), reverse=True)[:limit]


def grounding(focus_areas: list[str], digest_text: str) -> float:
    """Share of focus areas that contain at least one word (4+ letters) from the day's report."""
    source_words = set(WORD.findall(digest_text.casefold()))
    if not focus_areas:
        return 0.0
    grounded = sum(bool(set(WORD.findall(area.casefold())) & source_words) for area in focus_areas)
    return grounded / len(focus_areas)


def evaluate_summaries(models: list[str], days_limit: int) -> tuple[list[dict], list[str]]:
    db = SessionLocal()
    rows, samples = [], []
    try:
        private_apps = load_settings(db).private_apps
        for day in recent_days(db, days_limit):
            digest = build_day_digest(db, day, private_apps)
            if digest.is_empty:
                continue
            text = digest.to_prompt_text()
            for model in models:
                start = time.perf_counter()
                result = generate_summary(digest, LLMClient(model=model))
                seconds = time.perf_counter() - start
                rows.append({"day": day.isoformat(), "model": model, "seconds": seconds, "source": result.source,
                             "attempts": result.attempts, "grounding": grounding(result.focus_areas, text)})
                samples.append(f"### {day} · {model} · {seconds:.1f} s\n\n**{result.headline}**\n\n"
                               f"- Focus: {', '.join(result.focus_areas)}\n- Insight: {result.insight}\n"
                               f"- Suggestion: {result.suggestion}\n\nYour rating (1-5) accuracy: _ usefulness: _\n")
    finally:
        db.close()
    return rows, samples


def write_report(categories: list[dict], grouping: list[dict], summaries: list[dict]) -> None:
    best = max(grouping, key=lambda r: r["f1"])
    lines = [
        "# Evaluation of the local AI features",
        "",
        f"Run on {datetime.now():%Y-%m-%d %H:%M} on an Apple M2 (16 GB), all models local via Ollama.",
        "Reproduce: `venv/bin/python -m scripts.evaluate --models llama3.2:3b qwen2.5:7b`",
        "What changed because of these numbers: [evaluation_history.md](evaluation_history.md)",
        "",
        "## 1. Title categories (30 labelled titles)",
        "",
        "| Model | Accuracy | Correct | Time |",
        "| --- | --- | --- | --- |",
        *[f"| {c['model']} | {c['accuracy']:.0%} | {c['correct']}/{c['total']} | {c['seconds']:.1f} s |" for c in categories],
        "",
        *[f"Mistakes of {c['model']}: " + ("; ".join(c["mistakes"]) or "none") for c in categories],
        "",
        "## 2. Task grouping with embeddings (nomic-embed-text, pairwise scores)",
        "",
        "| Similarity threshold | Groups | Precision | Recall | F1 |",
        "| --- | --- | --- | --- | --- |",
        *[f"| {g['threshold']:.2f} | {g['groups']} | {g['precision']:.0%} | {g['recall']:.0%} | {g['f1']:.2f} |" for g in grouping],
        "",
        f"Best F1 at threshold {best['threshold']:.2f} (12 true tasks in the labelled set).",
        "",
        "## 3. Daily summaries on real days",
        "",
        "Grounding = share of focus areas that use words from that day's window titles.",
        "",
        "| Day | Model | Time | Source | Attempts | Grounding |",
        "| --- | --- | --- | --- | --- | --- |",
        *[f"| {s['day']} | {s['model']} | {s['seconds']:.1f} s | {s['source']} | {s['attempts']} | {s['grounding']:.0%} |"
          for s in summaries],
        "",
    ]
    for model in sorted({s["model"] for s in summaries}):
        mine = [s for s in summaries if s["model"] == model]
        lines.append(f"- {model}: average {np.mean([s['seconds'] for s in mine]):.1f} s per summary, "
                     f"average grounding {np.mean([s['grounding'] for s in mine]):.0%}, "
                     f"{sum(s['attempts'] == 1 and s['source'] == 'llm' for s in mine)}/{len(mine)} valid on the first try.")
    RESULTS.parent.mkdir(exist_ok=True)
    RESULTS.write_text("\n".join(lines) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--models", nargs="+", default=["llama3.2:3b"])
    parser.add_argument("--days", type=int, default=5)
    args = parser.parse_args()

    items = json.loads(LABELLED.read_text())
    print("1/3 categories ...")
    categories = [evaluate_categories(m, items) for m in args.models]
    print("2/3 task grouping ...")
    grouping = evaluate_grouping(items)
    print("3/3 daily summaries ...")
    summaries, samples = evaluate_summaries(args.models, args.days)

    write_report(categories, grouping, summaries)
    SAMPLES.write_text("# Summary samples to rate by hand (local only)\n\n" + "\n".join(samples))
    print(RESULTS.read_text())
    print(f"Samples to rate: {SAMPLES}")


if __name__ == "__main__":
    main()
