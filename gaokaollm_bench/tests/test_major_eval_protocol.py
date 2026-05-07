from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest

from gaokaollm_bench.data_gen.major_eval_protocol import (
    assert_complete_embedding_coverage,
    assert_no_group_overlap,
    embedding_coverage,
    grouped_train_val_split,
    low_sample_macro_f1,
    parent_metrics,
    summarize_persona_recommendations,
)


@pytest.fixture
def workspace_tmp() -> Iterator[Path]:
    path = Path("gaokaollm_bench/outputs/test_tmp") / f"major_eval_protocol_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path)


def test_grouped_split_prevents_normalized_text_leakage():
    rows = [
        {"text": "A1", "normalized_text": "same-a", "leaf_id": "a"},
        {"text": "A1 campus", "normalized_text": "same-a", "leaf_id": "a"},
        {"text": "A2", "normalized_text": "a2", "leaf_id": "a"},
        {"text": "B1", "normalized_text": "b1", "leaf_id": "b"},
        {"text": "B2", "normalized_text": "b2", "leaf_id": "b"},
    ]

    train_rows, val_rows, stats = grouped_train_val_split(rows, val_ratio=0.5, seed=1)

    assert stats["overlap_count"] == 0
    assert_no_group_overlap(train_rows, val_rows)


def test_grouped_split_rejects_conflicting_labels():
    rows = [
        {"text": "X", "normalized_text": "x", "leaf_id": "a"},
        {"text": "X duplicate", "normalized_text": "x", "leaf_id": "b"},
    ]

    with pytest.raises(ValueError, match="conflicting labels"):
        grouped_train_val_split(rows)


def test_embedding_coverage_reports_missing_texts(workspace_tmp):
    rows = [
        {"text": "alpha", "normalized_text": "alpha", "leaf_id": "a"},
        {"text": "beta", "normalized_text": "beta", "leaf_id": "b"},
    ]
    embeddings_path = workspace_tmp / "embeddings.npz"
    np.savez(
        embeddings_path,
        texts=np.asarray(["alpha"], dtype=object),
        embeddings=np.asarray([[1.0, 0.0]], dtype=np.float32),
    )

    coverage = embedding_coverage(rows, embeddings_path)

    assert coverage["missing_count"] == 1
    assert coverage["missing_examples"] == ["beta"]
    with pytest.raises(ValueError, match="incomplete"):
        assert_complete_embedding_coverage(rows, embeddings_path)


def test_parent_metrics_and_low_sample_macro_f1():
    tree = {
        "nodes": {
            "root_a": {"id": "root_a", "label": "A", "parent": None},
            "root_b": {"id": "root_b", "label": "B", "parent": None},
            "a1": {"id": "a1", "label": "A1", "parent": "root_a"},
            "a2": {"id": "a2", "label": "A2", "parent": "root_a"},
            "b1": {"id": "b1", "label": "B1", "parent": "root_b"},
        }
    }
    samples = [
        {"gold_label": "a1", "pred_label": "a2"},
        {"gold_label": "b1", "pred_label": "a1"},
    ]
    report = {
        "a1": {"support": 1, "f1-score": 0.5},
        "a2": {"support": 8, "f1-score": 0.9},
        "accuracy": 0.5,
        "macro avg": {"f1-score": 0.7},
        "weighted avg": {"f1-score": 0.8},
    }

    parent = parent_metrics(samples, tree)
    low_sample = low_sample_macro_f1(report, max_support=5)

    assert parent["parent_accuracy"] == 0.5
    assert parent["parent_confusion_pairs"][0]["gold_parent"] == "root_b"
    assert low_sample["label_count"] == 1
    assert low_sample["macro_f1"] == 0.5


def test_persona_recommendation_summary_counts_stage5():
    personas = [
        {
            "background": {"relaxation_stage": 4, "stage_attempts": [{"stage": 4, "failure_reason": None}]},
            "implicit_flexibilities": {
                "volunteer_set": [
                    {"school_name": "A"},
                    {"school_name": "B"},
                ]
            },
        },
        {
            "background": {"relaxation_stage": 5, "stage_attempts": [{"stage": 4, "failure_reason": "below_threshold"}]},
            "implicit_flexibilities": {"volunteer_set": [{"school_name": "A"}]},
        },
    ]

    summary = summarize_persona_recommendations(personas)

    assert summary["stage_distribution"] == {"4": 1, "5": 1}
    assert summary["stage5_rate"] == 0.5
    assert summary["avg_unique_school_count"] == 1.5
