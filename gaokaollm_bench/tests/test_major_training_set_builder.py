import json
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import pytest

from gaokaollm_bench.data_gen import major_training_set_builder as builder


@pytest.fixture
def workspace_tmp() -> Iterator[Path]:
    path = Path("gaokaollm_bench/outputs/test_tmp") / f"major_training_set_builder_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path)


def test_default_training_tree_is_clean_observed_tree():
    assert builder.DEFAULT_TREE_PATH == Path("gaokaollm_bench/sample_data/major_tree_observed_full.json")
    assert "auto_assigned" not in str(builder.DEFAULT_TREE_PATH)


def test_training_builder_refuses_auto_assigned_tree_by_default(workspace_tmp, monkeypatch):
    tree_path = workspace_tmp / "major_tree_observed_auto_assigned_full.json"
    output_path = workspace_tmp / "train.jsonl"
    tree_path.write_text(json.dumps({"nodes": {}}, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "major_training_set_builder",
            "--tree-path",
            str(tree_path),
            "--output",
            str(output_path),
        ],
    )

    with pytest.raises(SystemExit) as exc_info:
        builder.main()

    assert "Refusing to build rule-labeled training data" in str(exc_info.value)
    assert not output_path.exists()


def test_training_builder_preserves_clean_tree_labels(workspace_tmp, monkeypatch):
    chinese_major = "\u4e2d\u6587(\u5357\u6821\u533a)"
    tcm_major = "\u4e2d\u533b\u5b66"
    tree_path = workspace_tmp / "major_tree_observed_full.json"
    output_path = workspace_tmp / "train.jsonl"
    tree = {
        "nodes": {
            "root": {
                "id": "root",
                "label": "root",
                "parent": None,
                "level": 0,
                "include_keywords": [],
                "exclude_keywords": [],
                "observed_names": [],
            },
            "language_group": {
                "id": "language_group",
                "label": "\u8bed\u8a00\u6587\u5b66\u5927\u7c7b",
                "parent": "root",
                "level": 1,
                "include_keywords": [],
                "exclude_keywords": [],
                "observed_names": [],
            },
            "chinese_language": {
                "id": "chinese_language",
                "label": "\u4e2d\u56fd\u8bed\u8a00\u6587\u5b66\u7c7b",
                "parent": "language_group",
                "level": 2,
                "include_keywords": ["\u4e2d\u6587"],
                "exclude_keywords": [],
                "observed_names": [chinese_major],
            },
            "medical_tcm": {
                "id": "medical_tcm",
                "label": "\u4e2d\u533b\u4e2d\u836f\u4e34\u5e8a\u7c7b",
                "parent": "root",
                "level": 2,
                "include_keywords": ["\u4e2d\u533b"],
                "exclude_keywords": [],
                "observed_names": [tcm_major],
            },
        }
    }
    tree_path.write_text(json.dumps(tree, ensure_ascii=False), encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "major_training_set_builder",
            "--tree-path",
            str(tree_path),
            "--output",
            str(output_path),
        ],
    )

    builder.main()

    rows = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]
    chinese_rows = [row for row in rows if row["text"] == chinese_major]
    assert chinese_rows
    assert {row["leaf_id"] for row in chinese_rows} == {"chinese_language"}
    assert not any(row["text"] == chinese_major and row["leaf_id"] == "medical_tcm" for row in rows)
