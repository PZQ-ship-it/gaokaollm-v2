import json
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
import torch

from gaokaollm_bench.data_gen import major_probe_train as train
from gaokaollm_bench.data_gen.major_probe_predict import _load_probe


@pytest.fixture
def workspace_tmp() -> Iterator[Path]:
    path = Path("gaokaollm_bench/outputs/test_tmp") / f"major_probe_opt_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path)


def test_best_checkpoint_tiebreak_prefers_accuracy_then_loss_then_earlier_epoch():
    best = {
        "epoch": 5,
        "val_macro_f1": 0.7,
        "val_accuracy": 0.8,
        "val_loss": 1.0,
    }
    higher_acc = {
        "epoch": 8,
        "val_macro_f1": 0.7,
        "val_accuracy": 0.81,
        "val_loss": 1.2,
    }
    lower_loss = {
        "epoch": 8,
        "val_macro_f1": 0.7,
        "val_accuracy": 0.8,
        "val_loss": 0.9,
    }
    later_same = {
        "epoch": 8,
        "val_macro_f1": 0.7,
        "val_accuracy": 0.8,
        "val_loss": 1.0,
    }

    best_key = train._best_key(best, "val_macro_f1")

    assert train._metric_is_better(higher_acc, selection_metric="val_macro_f1", best_key=best_key)
    assert train._metric_is_better(lower_loss, selection_metric="val_macro_f1", best_key=best_key)
    assert not train._metric_is_better(later_same, selection_metric="val_macro_f1", best_key=best_key)


def test_class_weight_modes_are_finite_for_missing_classes():
    y = np.asarray([0, 0, 0, 1], dtype=np.int64)

    balanced = train._class_weights(y, num_classes=3, mode="balanced")
    sqrt_balanced = train._class_weights(y, num_classes=3, mode="sqrt_balanced")

    assert balanced is not None
    assert sqrt_balanced is not None
    assert torch.isfinite(balanced).all()
    assert torch.isfinite(sqrt_balanced).all()
    assert balanced[1] > balanced[0]
    assert balanced[2] == 1.0


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def test_train_mlp_checkpoint_can_be_loaded_by_predict(workspace_tmp, monkeypatch):
    rows = [
        {"text": "alpha one", "normalized_text": "alpha one", "leaf_id": "a"},
        {"text": "alpha two", "normalized_text": "alpha two", "leaf_id": "a"},
        {"text": "beta one", "normalized_text": "beta one", "leaf_id": "b"},
        {"text": "beta two", "normalized_text": "beta two", "leaf_id": "b"},
    ]
    train_path = workspace_tmp / "train.jsonl"
    val_path = workspace_tmp / "val.jsonl"
    output_dir = workspace_tmp / "probe"
    tree_path = workspace_tmp / "tree.json"
    embeddings_path = workspace_tmp / "embeddings.npz"
    _write_jsonl(train_path, rows)
    _write_jsonl(val_path, rows)
    np.savez(
        embeddings_path,
        texts=np.asarray([row["normalized_text"] for row in rows], dtype=object),
        embeddings=np.asarray(
            [
                [1.0, 0.0, 0.0, 0.0],
                [0.9, 0.1, 0.0, 0.0],
                [0.0, 1.0, 0.0, 0.0],
                [0.1, 0.9, 0.0, 0.0],
            ],
            dtype=np.float32,
        ),
    )
    tree_path.write_text(
        json.dumps(
            {
                "nodes": {
                    "a": {"id": "a", "label": "A"},
                    "b": {"id": "b", "label": "B"},
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "major_probe_train",
            "--input-jsonl",
            str(train_path),
            "--val-jsonl",
            str(val_path),
            "--embeddings",
            str(embeddings_path),
            "--output-dir",
            str(output_dir),
            "--epochs",
            "3",
            "--model-kind",
            "mlp",
            "--hidden-dim",
            "8",
            "--dropout",
            "0.0",
            "--selection-metric",
            "val_macro_f1",
        ],
    )

    train.main()
    model, inv_label_map, nodes = _load_probe(
        probe_path=output_dir / "best_probe.pt",
        label_map_path=output_dir / "label_map.json",
        major_tree_path=tree_path,
    )
    metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))

    assert isinstance(model, torch.nn.Sequential)
    assert set(inv_label_map.values()) == {"a", "b"}
    assert nodes["a"]["label"] == "A"
    assert metrics["model_config"]["model_kind"] == "mlp"
    assert metrics["best_val_macro_f1"] is not None


def test_early_stopping_records_status(workspace_tmp, monkeypatch):
    rows = [
        {"text": "alpha one", "normalized_text": "alpha one", "leaf_id": "a"},
        {"text": "alpha two", "normalized_text": "alpha two", "leaf_id": "a"},
        {"text": "beta one", "normalized_text": "beta one", "leaf_id": "b"},
        {"text": "beta two", "normalized_text": "beta two", "leaf_id": "b"},
    ]
    train_path = workspace_tmp / "train.jsonl"
    val_path = workspace_tmp / "val.jsonl"
    output_dir = workspace_tmp / "probe"
    embeddings_path = workspace_tmp / "embeddings.npz"
    _write_jsonl(train_path, rows)
    _write_jsonl(val_path, rows)
    np.savez(
        embeddings_path,
        texts=np.asarray([row["normalized_text"] for row in rows], dtype=object),
        embeddings=np.ones((len(rows), 4), dtype=np.float32),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "major_probe_train",
            "--input-jsonl",
            str(train_path),
            "--val-jsonl",
            str(val_path),
            "--embeddings",
            str(embeddings_path),
            "--output-dir",
            str(output_dir),
            "--epochs",
            "12",
            "--lr",
            "0",
            "--early-stopping-patience",
            "2",
            "--selection-metric",
            "val_macro_f1",
        ],
    )

    train.main()
    metrics = json.loads((output_dir / "metrics.json").read_text(encoding="utf-8"))

    assert metrics["stopped_early"] is True
    assert metrics["epochs_completed"] < 12
