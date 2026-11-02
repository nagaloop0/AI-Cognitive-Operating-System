"""
Tests for semantic task grouping (embeddings) and "Ask your history" (RAG).
FakeLLM returns hand-made vectors, so which titles are "similar" is known in advance.
"""
from datetime import date, timedelta

import numpy as np
import pytest

from backend.ask import answer_question, resolve_days
from backend.llm_client import LLMResponseError
from backend.models import Task, TitleEmbedding
from backend.tasks import DOCUMENT_PREFIX, QUERY_PREFIX, cluster, embed_new_titles, regroup_tasks, \
    similar_titles, task_minutes
from backend.timeutil import local_day_bounds, local_today
from conftest import FakeLLM, add_activity, padded

YESTERDAY = local_today() - timedelta(days=1)


def add(db, app, title, hour, minutes=30, day=YESTERDAY):
    start, _ = local_day_bounds(day)
    add_activity(db, app, title, start + timedelta(hours=hour), minutes)


def llm_with_vectors(*answers):
    llm = FakeLLM(*answers)
    llm.vectors = {
        DOCUMENT_PREFIX + "pattern_engine.py — explore_p": [1.0, 0.1, 0.0],
        DOCUMENT_PREFIX + "test_pattern_engine.py — explore_p": [0.95, 0.15, 0.0],
        DOCUMENT_PREFIX + "resume.pdf": [0.0, 1.0, 0.1],
        QUERY_PREFIX + "When did I work on the pattern engine?": [1.0, 0.12, 0.0],
    }
    return llm


def project_day(db):
    add(db, "Code", "pattern_engine.py — explore_p", 9, 60)
    add(db, "Code", "test_pattern_engine.py — explore_p", 10, 30)
    add(db, "Google Chrome", "resume.pdf", 11, 20)
    add(db, "WhatsApp", "(private)", 12, 10)


# ---- clustering ----------------------------------------------------------------------------------

def test_cluster_links_similar_vectors_only():
    vectors = np.array([[1, 0], [0.98, 0.05], [0, 1]], dtype=float)

    assert cluster(vectors, threshold=0.9) == [[0, 1], [2]]


def test_wrong_vector_size_gives_a_clear_error(db):
    project_day(db)
    llm = llm_with_vectors()
    llm.embed = lambda texts: [[0.1, 0.2]] * len(texts)

    with pytest.raises(LLMResponseError, match="EMBED_DIMENSIONS"):
        embed_new_titles(db, llm)


def test_cluster_with_one_vector():
    assert cluster(np.array([[1.0, 0.0]])) == [[0]]


# ---- embeddings and tasks ------------------------------------------------------------------------

def test_titles_are_embedded_once_and_private_titles_never(db):
    project_day(db)
    llm = llm_with_vectors()

    assert embed_new_titles(db, llm) == 3
    assert embed_new_titles(db, llm) == 0
    assert db.query(TitleEmbedding).filter_by(app_name="WhatsApp").count() == 0


def test_similar_titles_become_one_named_task(db):
    project_day(db)
    llm = llm_with_vectors({"name": "Pattern engine work"})
    embed_new_titles(db, llm)

    assert regroup_tasks(db, llm) == 2

    tasks = task_minutes(db, YESTERDAY)
    assert [(t.name, t.minutes) for t in tasks] == [("Pattern engine work", 90), ("resume.pdf", 20)]


def test_regrouping_replaces_old_tasks(db):
    project_day(db)
    llm = llm_with_vectors({"name": "Pattern engine work"}, {"name": "Pattern engine"})
    embed_new_titles(db, llm)

    regroup_tasks(db, llm)
    regroup_tasks(db, llm)

    assert db.query(Task).count() == 2


def test_similar_titles_ranks_by_cosine_similarity(db):
    project_day(db)
    embed_new_titles(db, llm_with_vectors())

    best, score = similar_titles(db, padded([1.0, 0.1, 0.0]), k=1)[0]

    assert best.window_title == "pattern_engine.py — explore_p"
    assert score > 0.99


# ---- ask your history ----------------------------------------------------------------------------

def test_resolve_days():
    monday = date(2026, 11, 2)  # a Monday

    assert resolve_days("what did I do yesterday?", monday) == [date(2026, 11, 1)]
    assert resolve_days("and on Friday", monday) == [date(2026, 10, 30)]
    assert resolve_days("what about today, monday", monday) == [monday]
    assert resolve_days("last monday please", monday) == [date(2026, 10, 26)]
    assert resolve_days("on 2026-10-29", monday) == [date(2026, 10, 29)]
    assert len(resolve_days("what did I work on?", monday)) == 7


def test_answer_uses_day_reports_and_related_titles(db):
    project_day(db)
    llm = llm_with_vectors("You worked on the pattern engine yesterday for 1 h 30 min.")
    embed_new_titles(db, llm)

    result = answer_question(db, llm, "When did I work on the pattern engine?")

    prompt = llm.calls[-1]["messages"][1]["content"]
    assert "pattern_engine.py — explore_p | 1 h" in prompt
    assert "resume.pdf |" not in prompt.split("Window titles related")[1]
    assert result.answer.startswith("You worked on the pattern engine")
    assert {s.window_title for s in result.sources} == {"pattern_engine.py — explore_p",
                                                         "test_pattern_engine.py — explore_p"}


def test_answer_without_embeddings_still_uses_day_reports(db):
    project_day(db)
    llm = FakeLLM("You worked in Code yesterday.")

    result = answer_question(db, llm, "What did I do yesterday?")

    assert result.sources == []
    assert result.days == [YESTERDAY]
    assert "No additional window titles matched the question by meaning; answer from the day reports above." in llm.calls[-1]["messages"][1]["content"]
