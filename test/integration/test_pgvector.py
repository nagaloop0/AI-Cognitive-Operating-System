"""
Integration tests on real PostgreSQL + pgvector (the SQLite tests cannot reach this code path).
They use the pg_db fixture from test/conftest.py: a separate *_test database, emptied before and after
each test, with the real engine and SessionLocal replaced by tripwires.

Run: TEST_DATABASE_URL=postgresql+psycopg2://<user>@localhost/cognitive_os_test \
     venv/bin/python -m pytest -m postgres -v
"""
from datetime import timedelta

import numpy as np
import pytest
from sqlalchemy import text

from backend.models import EMBEDDING_DIMENSIONS, Task, TitleEmbedding
from backend.tasks import cosine_similarity_matrix, regroup_tasks, similar_titles, task_minutes
from backend.timeutil import local_day_bounds, local_today
from conftest import FakeLLM, add_activity, padded

pytestmark = pytest.mark.postgres

YESTERDAY = local_today() - timedelta(days=1)


def store(db, title, vector, app="Code"):
    db.add(TitleEmbedding(app_name=app, window_title=title, embedding=padded(vector)))
    db.commit()


def test_init_db_enables_pgvector_and_creates_tables(pg_db):
    extension = pg_db.execute(text("SELECT extname FROM pg_extension WHERE extname = 'vector'")).scalar()
    column_type = pg_db.execute(text(
        "SELECT format_type(atttypid, atttypmod) FROM pg_attribute "
        "WHERE attrelid = 'title_embedding'::regclass AND attname = 'embedding'")).scalar()

    assert extension == "vector"
    assert column_type == f"vector({EMBEDDING_DIMENSIONS})"


def test_embedding_round_trip_keeps_all_numbers(pg_db):
    store(pg_db, "digest.py", [0.25, -0.5, 1.0])

    stored = pg_db.query(TitleEmbedding).one().embedding

    assert len(stored) == EMBEDDING_DIMENSIONS
    assert list(stored[:3]) == [0.25, -0.5, 1.0]


def test_similar_titles_ranks_by_pgvector_cosine_distance(pg_db):
    store(pg_db, "pattern_engine.py", [1.0, 0.1, 0.0])
    store(pg_db, "test_pattern_engine.py", [0.9, 0.3, 0.0])
    store(pg_db, "resume.pdf", [0.0, 1.0, 0.2], app="Preview")

    results = similar_titles(pg_db, padded([1.0, 0.0, 0.0]), k=3)

    assert [row.window_title for row, _ in results] == ["pattern_engine.py", "test_pattern_engine.py", "resume.pdf"]
    assert results[0][1] > results[1][1] > results[2][1]


def test_pgvector_scores_match_the_numpy_formula(pg_db):
    vectors = {"a.py": [1.0, 2.0, 0.5], "b.py": [-0.3, 1.0, 2.0], "c.py": [0.7, -1.2, 0.4]}
    for title, vector in vectors.items():
        store(pg_db, title, vector)
    query = [0.5, 1.0, -0.2]

    from_postgres = {row.window_title: score for row, score in similar_titles(pg_db, padded(query), k=3)}

    matrix = np.array([padded(query)] + [padded(v) for v in vectors.values()])
    from_numpy = dict(zip(vectors, cosine_similarity_matrix(matrix)[0, 1:]))
    for title in vectors:
        assert from_postgres[title] == pytest.approx(from_numpy[title], abs=1e-6)


def test_task_grouping_and_minutes_on_postgres(pg_db):
    start, _ = local_day_bounds(YESTERDAY)
    add_activity(pg_db, "Code", "pattern_engine.py", start + timedelta(hours=9), 60)
    add_activity(pg_db, "Code", "test_pattern_engine.py", start + timedelta(hours=10), 30)
    add_activity(pg_db, "Preview", "resume.pdf", start + timedelta(hours=11), 20)
    store(pg_db, "pattern_engine.py", [1.0, 0.1, 0.0])
    store(pg_db, "test_pattern_engine.py", [0.95, 0.15, 0.0])
    store(pg_db, "resume.pdf", [0.0, 1.0, 0.1], app="Preview")

    assert regroup_tasks(pg_db, FakeLLM({"name": "Pattern engine work"})) == 2

    assert [(t.name, t.minutes) for t in task_minutes(pg_db, YESTERDAY)] == [
        ("Pattern engine work", 90), ("resume.pdf", 20)]


def test_deleting_tasks_keeps_embeddings(pg_db):
    store(pg_db, "a.py", [1.0, 0.0, 0.0])
    regroup_tasks(pg_db, FakeLLM())
    assert pg_db.query(TitleEmbedding).one().task_id is not None

    pg_db.query(Task).delete()
    pg_db.commit()
    pg_db.expire_all()

    assert pg_db.query(TitleEmbedding).one().task_id is None  # ON DELETE SET NULL


def test_real_database_cannot_be_used_during_integration_tests(pg_db):
    import backend.database as database
    from backend.database import init_db

    with pytest.raises(AssertionError, match="must not use backend.database.SessionLocal"):
        database.SessionLocal()
    with pytest.raises(AssertionError, match="must not use backend.database.engine"):
        init_db()  # no argument = the default engine
