"""
Semantic task grouping with embeddings.

1. Every unique window title becomes a vector (Ollama `nomic-embed-text`, 768 numbers).
2. Titles whose vectors are close (cosine similarity >= threshold) are linked; each connected group is one task.
3. The local model gives each multi-title task a short name ("Pattern engine work").

Vectors live in PostgreSQL (pgvector), so nearest-neighbour search runs inside the database;
the SQLite test database falls back to numpy for the same maths.
"""
import logging
from collections import defaultdict
from datetime import date

import numpy as np
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy.orm import Session

from backend.digest import load_segments
from backend.llm_client import LLMResponseError
from backend.models import EMBEDDING_DIMENSIONS, AppActivity, Task, TitleEmbedding
from backend.privacy import PRIVATE_TITLE, redact
from backend.timeutil import local_day_bounds

logger = logging.getLogger("tasks")

# nomic-embed-text is trained with these prefixes: stored texts are "documents", questions are "queries"
DOCUMENT_PREFIX = "search_document: "
QUERY_PREFIX = "search_query: "
SIMILARITY_THRESHOLD = 0.70     # best F1 on the labelled set (scripts/evaluate.py, docs/evaluation.md)
EMBED_BATCH_SIZE = 32
MAX_NAMED_TASKS = 40            # model naming calls per regrouping; the rest get a rule-based name


class TaskTime(BaseModel):
    task_id: int
    name: str
    minutes: int
    titles: list[str]


class _TaskName(BaseModel):
    name: str = Field(min_length=2, max_length=60, description="2 to 5 words naming the shared piece of work")


def title_text(window_title: str) -> str:
    """Only the title is embedded: with "Google Chrome: ..." in front, every browser tab looked alike
    (evaluation: F1 0.18 with the app name, 0.28 without)."""
    return redact(window_title)


def embed_new_titles(db: Session, llm, limit: int = 500) -> int:
    """Embeds titles that have no vector yet. Private and empty titles are never embedded."""
    known = {(r.app_name, r.window_title) for r in db.query(TitleEmbedding.app_name, TitleEmbedding.window_title)}
    pairs = {
        (app, title)
        for app, title in db.query(AppActivity.app_name, AppActivity.window_title).distinct()
        if app and title and title != PRIVATE_TITLE and (app, title) not in known
    }
    todo = sorted(pairs)[:limit]
    for i in range(0, len(todo), EMBED_BATCH_SIZE):
        batch = todo[i:i + EMBED_BATCH_SIZE]
        vectors = llm.embed([DOCUMENT_PREFIX + title_text(title) for _, title in batch])
        if vectors and len(vectors[0]) != EMBEDDING_DIMENSIONS:
            raise LLMResponseError(
                f"The embedding model returns {len(vectors[0])} numbers per title, but the database stores "
                f"{EMBEDDING_DIMENSIONS} (EMBED_DIMENSIONS in .env). Use the matching model or update both.")
        db.add_all(TitleEmbedding(app_name=app, window_title=title, embedding=list(vector))
                   for (app, title), vector in zip(batch, vectors))
        db.commit()
    return len(todo)


def cosine_similarity_matrix(vectors: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    unit = vectors / np.where(norms == 0, 1, norms)
    return unit @ unit.T


def cluster(vectors: np.ndarray, threshold: float = SIMILARITY_THRESHOLD) -> list[list[int]]:
    """Connected components of the "similar enough" graph (union-find). Returns lists of row indexes."""
    parent = list(range(len(vectors)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    if len(vectors) > 1:
        similar = cosine_similarity_matrix(vectors) >= threshold
        rows, cols = np.nonzero(np.triu(similar, k=1))
        for a, b in zip(rows.tolist(), cols.tolist()):
            parent[find(a)] = find(b)

    groups: dict[int, list[int]] = defaultdict(list)
    for i in range(len(vectors)):
        groups[find(i)].append(i)
    return sorted(groups.values(), key=len, reverse=True)


def regroup_tasks(db: Session, llm, threshold: float = SIMILARITY_THRESHOLD) -> int:
    """Rebuilds all tasks from the stored vectors. Returns the number of tasks."""
    rows = db.query(TitleEmbedding).order_by(TitleEmbedding.id).all()
    if not rows:
        return 0
    groups = cluster(np.array([np.asarray(r.embedding, dtype=float) for r in rows]), threshold)

    for row in rows:
        row.task_id = None
    db.query(Task).delete()
    db.flush()

    named = 0
    for group in groups:
        members = [rows[i] for i in group]
        name = None
        if len(members) > 1 and named < MAX_NAMED_TASKS:
            name = _ask_name(llm, members)
            named += 1
        task = Task(name=name or _fallback_name(members))
        db.add(task)
        db.flush()
        for member in members:
            member.task_id = task.id
    db.commit()
    return len(groups)


def _ask_name(llm, members: list[TitleEmbedding]) -> str | None:
    listing = "\n".join(f"- [{m.app_name}] {title_text(m.window_title)}" for m in members[:8])
    messages = [
        {"role": "system", "content": "These window titles belong to one piece of work. "
                                      "Name that work in 2 to 5 words, using project or topic names from the titles."},
        {"role": "user", "content": listing},
    ]
    try:
        return _TaskName.model_validate(llm.chat(messages, json_schema=_TaskName.model_json_schema())).name
    except (LLMResponseError, ValidationError) as e:
        logger.info("Task name falls back to a rule: %s", e)
        return None


def _fallback_name(members: list[TitleEmbedding]) -> str:
    return redact(members[0].window_title, max_chars=40) or members[0].app_name


def similar_titles(db: Session, vector: list[float], k: int = 8) -> list[tuple[TitleEmbedding, float]]:
    """The k stored titles closest to `vector`, with their cosine similarity (1 = same direction)."""
    if db.get_bind().dialect.name == "postgresql":
        distance = TitleEmbedding.embedding.cosine_distance(vector)
        return [(row, 1 - dist) for row, dist in db.query(TitleEmbedding, distance).order_by(distance).limit(k)]

    rows = db.query(TitleEmbedding).all()
    if not rows:
        return []
    matrix = np.array([np.asarray(r.embedding, dtype=float) for r in rows])
    query = np.asarray(vector, dtype=float)
    scores = (matrix @ query) / (np.linalg.norm(matrix, axis=1) * (np.linalg.norm(query) or 1) + 1e-12)
    best = np.argsort(-scores)[:k]
    return [(rows[i], float(scores[i])) for i in best]


def task_minutes(db: Session, day: date) -> list[TaskTime]:
    """Time per task on a local day, most time first."""
    start, end = local_day_bounds(day)
    links = {(r.app_name, r.window_title): r.task_id for r in db.query(TitleEmbedding) if r.task_id}
    names = {t.id: t.name for t in db.query(Task)}
    seconds: dict[int, float] = defaultdict(float)
    titles: dict[int, set[str]] = defaultdict(set)
    for seg in load_segments(db, start, end):
        task_id = links.get((seg.app_name, seg.title))
        if task_id:
            seconds[task_id] += seg.seconds
            titles[task_id].add(redact(seg.title))
    result = [TaskTime(task_id=t, name=names[t], minutes=round(s / 60), titles=sorted(titles[t])[:5])
              for t, s in seconds.items() if t in names]
    return sorted((r for r in result if r.minutes > 0), key=lambda r: r.minutes, reverse=True)
