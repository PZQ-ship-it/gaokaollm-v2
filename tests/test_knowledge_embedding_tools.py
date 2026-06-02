import argparse
import json
from pathlib import Path

from scripts import backfill_knowledge_embeddings as backfill
from scripts.audit_knowledge_embeddings import _coverage_row
from scripts.knowledge_embedding_targets import targets_from_trace


def test_targets_from_trace_extracts_candidate_ids_and_titles(tmp_path: Path) -> None:
    trace = {
        "rounds": [
            {
                "latest_tradeoff_pair": {
                    "option_a": {
                        "school_id": 1,
                        "major_id": 2,
                        "major_name": "临床医学",
                    },
                    "option_b": {
                        "school_id": "3",
                        "major_id": None,
                        "major_name": "水产类",
                        "_phi_features": {"major": 1.0},
                    },
                    "delta_phi_b_minus_a": {"major": 0.16666666666666666},
                }
            }
        ]
    }
    path = tmp_path / "trace.json"
    path.write_text(json.dumps(trace, ensure_ascii=False), encoding="utf-8")

    targets = targets_from_trace(path)

    assert targets.school_ids == {1, 3}
    assert targets.major_ids == {2}
    assert targets.major_titles == {"水产类"}


def test_backfill_fetch_docs_builds_targeted_where(monkeypatch) -> None:
    captured = {}

    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def execute(self, query, params):
            captured["query"] = query
            captured["params"] = params

        def fetchall(self):
            return []

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def cursor(self):
            return FakeCursor()

    monkeypatch.setattr(backfill.psycopg, "connect", lambda *args, **kwargs: FakeConn())

    args = argparse.Namespace(
        trace="",
        school_id=["10,20"],
        major_id=["30"],
        major_title=["医学试验班"],
    )
    targets = backfill._targets_from_args(args)
    backfill._fetch_docs(
        limit=5, doc_type="school_intro", targets=targets, linked_only=True
    )

    assert "school_id = ANY" in captured["query"]
    assert "major_id = ANY" in captured["query"]
    assert "title = ANY" in captured["query"]
    assert "(school_id IS NOT NULL OR major_id IS NOT NULL)" in captured["query"]
    assert captured["params"] == [
        "school_intro",
        [10, 20],
        [30],
        ["医学试验班"],
        5,
    ]


def test_coverage_row_reports_ratio() -> None:
    assert _coverage_row(10, 3) == {
        "total": 10,
        "with_embedding": 7,
        "missing_embedding": 3,
        "coverage_ratio": 0.7,
    }
