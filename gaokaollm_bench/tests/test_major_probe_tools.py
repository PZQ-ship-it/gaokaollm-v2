import json
import shutil
from collections.abc import Iterator
from pathlib import Path
from uuid import uuid4

import numpy as np
import pytest
import torch

from gaokaollm_bench.data_gen.major_probe_predict import _load_probe
from gaokaollm_bench.data_gen.major_probe_train import build_probe_model
from gaokaollm_bench.chains.json_repair import (
    direct_response_format,
    repair_major_payload,
)
from gaokaollm_bench.data_gen.major_training_set_builder import (
    _filter_ambiguous_rows,
    _iter_rows,
    detect_ambiguous_compound_major,
)
from gaokaollm_bench.tests.manual.major_probe_architecture_trials import (
    build_trial_matrix,
)
from gaokaollm_bench.tests.manual.major_probe_error_analysis import analyze
from gaokaollm_bench.tests.manual.major_probe_frkan_trials import (
    build_trial_matrix as build_frkan_trial_matrix,
)
from gaokaollm_bench.tests.manual.major_probe_promote import _metric_gate


@pytest.fixture
def workspace_tmp() -> Iterator[Path]:
    path = Path("gaokaollm_bench/outputs/test_tmp") / f"major_probe_tools_{uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path)


def _toy_tree() -> dict:
    return {
        "nodes": {
            "econ_group": {
                "id": "econ_group",
                "label": "经管类",
                "parent": None,
                "level": 1,
                "include_keywords": [],
                "exclude_keywords": [],
                "observed_names": [],
            },
            "computer_group": {
                "id": "computer_group",
                "label": "计算机类",
                "parent": None,
                "level": 1,
                "include_keywords": [],
                "exclude_keywords": [],
                "observed_names": [],
            },
            "business_management": {
                "id": "business_management",
                "label": "工商管理类",
                "parent": "econ_group",
                "level": 2,
                "include_keywords": ["工商管理", "市场营销"],
                "exclude_keywords": [],
                "observed_names": [
                    "工商管理类(含工商管理、市场营销、大数据管理方向专业)"
                ],
            },
            "data_ai": {
                "id": "data_ai",
                "label": "数据与人工智能类",
                "parent": "computer_group",
                "level": 2,
                "include_keywords": ["大数据", "人工智能"],
                "exclude_keywords": [],
                "observed_names": ["数据科学与大数据技术"],
            },
        }
    }


def test_ambiguity_detector_flags_cross_parent_compound_major():
    detection = detect_ambiguous_compound_major(
        "工商管理类(含工商管理、市场营销、大数据管理方向专业)",
        "business_management",
        _toy_tree(),
    )

    assert detection["is_ambiguous"] is True
    assert "computer_group" in detection["cross_parent_ids"]


def test_filter_ambiguous_rows_keeps_tree_unchanged():
    tree = _toy_tree()
    rows = list(_iter_rows(tree))
    kept, audit = _filter_ambiguous_rows(rows, tree=tree)

    assert audit
    assert any(row["leaf_id"] == "business_management" for row in audit)
    assert tree["nodes"]["business_management"]["observed_names"]
    assert len(kept) < len(rows)


def test_metric_gate_requires_dual_improvement(workspace_tmp):
    candidate = workspace_tmp / "candidate"
    candidate.mkdir()
    (candidate / "metrics.json").write_text(
        json.dumps(
            {
                "best_val_macro_f1": 0.8,
                "best_val_accuracy": 0.7,
            }
        ),
        encoding="utf-8",
    )

    gate = _metric_gate(candidate, min_macro_f1=0.75, min_accuracy=0.77)

    assert gate["passes"] is False
    assert gate["macro_f1"] == 0.8


@pytest.mark.parametrize(
    "model_kind", ["linear", "mlp", "deep_mlp", "residual_mlp", "fr_kan"]
)
def test_build_probe_model_supports_architectures(model_kind):
    model = build_probe_model(
        input_dim=4,
        output_dim=3,
        model_kind=model_kind,
        hidden_dim=5,
        dropout=0.1,
        num_hidden_layers=2,
        activation="gelu",
        fourier_grid_size=3,
    )

    with torch.no_grad():
        logits = model(torch.ones(2, 4))

    assert tuple(logits.shape) == (2, 3)


@pytest.mark.parametrize(
    ("kwargs", "message"),
    [
        ({"num_hidden_layers": 0}, "num-hidden-layers"),
        ({"dropout": 1.0}, "dropout"),
        ({"activation": "swish"}, "Unsupported activation"),
        ({"model_kind": "fr_kan", "fourier_grid_size": 0}, "fourier-grid-size"),
    ],
)
def test_build_probe_model_rejects_invalid_architecture_params(kwargs, message):
    params = {
        "input_dim": 4,
        "output_dim": 3,
        "model_kind": "deep_mlp",
        "hidden_dim": 5,
        "dropout": 0.1,
        "num_hidden_layers": 2,
        "activation": "gelu",
        "fourier_grid_size": 3,
    }
    params.update(kwargs)

    with pytest.raises(ValueError, match=message):
        build_probe_model(**params)


def test_complex_probe_checkpoint_loads_via_prediction_loader(workspace_tmp):
    label_map_path = workspace_tmp / "label_map.json"
    label_map_path.write_text(json.dumps({"a": 0, "b": 1}), encoding="utf-8")
    tree_path = workspace_tmp / "tree.json"
    tree_path.write_text(
        json.dumps(
            {
                "nodes": {
                    "a": {"id": "a", "label": "A"},
                    "b": {"id": "b", "label": "B"},
                }
            }
        ),
        encoding="utf-8",
    )
    model_config = {
        "input_dim": 2,
        "output_dim": 2,
        "model_kind": "residual_mlp",
        "hidden_dim": 4,
        "dropout": 0.1,
        "num_hidden_layers": 2,
        "activation": "gelu",
    }
    model = build_probe_model(**model_config)
    probe_path = workspace_tmp / "probe.pt"
    torch.save(
        {
            "state_dict": {
                key: value.detach().clone() for key, value in model.state_dict().items()
            },
            "model_config": model_config,
        },
        probe_path,
    )

    loaded_model, inv_label_map, nodes = _load_probe(
        probe_path=probe_path,
        label_map_path=label_map_path,
        major_tree_path=tree_path,
    )

    with torch.no_grad():
        logits = loaded_model(torch.ones(1, 2))

    assert tuple(logits.shape) == (1, 2)
    assert inv_label_map[0] == "a"
    assert nodes["b"]["label"] == "B"


def test_frkan_checkpoint_loads_via_prediction_loader(workspace_tmp):
    label_map_path = workspace_tmp / "label_map.json"
    label_map_path.write_text(json.dumps({"a": 0, "b": 1}), encoding="utf-8")
    tree_path = workspace_tmp / "tree.json"
    tree_path.write_text(
        json.dumps(
            {
                "nodes": {
                    "a": {"id": "a", "label": "A"},
                    "b": {"id": "b", "label": "B"},
                }
            }
        ),
        encoding="utf-8",
    )
    model_config = {
        "input_dim": 2,
        "output_dim": 2,
        "model_kind": "fr_kan",
        "hidden_dim": 4,
        "dropout": 0.1,
        "num_hidden_layers": 1,
        "activation": "relu",
        "fourier_grid_size": 3,
    }
    model = build_probe_model(**model_config)
    probe_path = workspace_tmp / "frkan_probe.pt"
    torch.save(
        {
            "state_dict": {
                key: value.detach().clone() for key, value in model.state_dict().items()
            },
            "model_config": model_config,
        },
        probe_path,
    )

    loaded_model, _, _ = _load_probe(
        probe_path=probe_path,
        label_map_path=label_map_path,
        major_tree_path=tree_path,
    )

    with torch.no_grad():
        logits = loaded_model(torch.ones(1, 2))

    assert tuple(logits.shape) == (1, 2)


def test_direct_llm_repair_rejects_unknown_label():
    label_options = [
        {"label": "computer_science", "label_name": "计算机科学类"},
        {"label": "vocational_cloud", "label_name": "云计算技术应用类"},
    ]

    repaired = repair_major_payload(
        {"major_name": ": ", "selected_label": ": "},
        major_name="云计算技术应用",
        label_options=label_options,
    )

    assert repaired["schema_valid"] is False
    assert repaired["label_valid"] is False
    assert repaired["selected_label"] == ": "


def test_direct_llm_repair_maps_label_name_to_label():
    label_options = [
        {"label": "computer_science", "label_name": "计算机科学类"},
        {"label": "vocational_cloud", "label_name": "云计算技术应用类"},
    ]

    repaired = repair_major_payload(
        {"major_name": "云计算技术应用", "selected_label": "云计算技术应用类"},
        major_name="云计算技术应用",
        label_options=label_options,
    )

    assert repaired["schema_valid"] is True
    assert repaired["label_valid"] is True
    assert repaired["selected_label"] == "vocational_cloud"
    assert "mapped_label_name_to_label" in repaired["repair_notes"]


def test_direct_llm_repair_treats_null_as_invalid_by_default():
    label_options = [{"label": "computer_science", "label_name": "计算机科学类"}]

    strict = repair_major_payload(
        {"major_name": "云计算技术应用", "selected_label": None},
        major_name="云计算技术应用",
        label_options=label_options,
    )
    diagnostic = repair_major_payload(
        {"major_name": "云计算技术应用", "selected_label": None},
        major_name="云计算技术应用",
        label_options=label_options,
        allow_null=True,
    )

    assert strict["schema_valid"] is False
    assert strict["label_valid"] is False
    assert diagnostic["schema_valid"] is True
    assert diagnostic["label_valid"] is False


def test_direct_llm_schema_uses_label_enum():
    label_options = [
        {"label": "computer_science", "label_name": "计算机科学类"},
        {"label": "vocational_cloud", "label_name": "云计算技术应用类"},
    ]

    schema = direct_response_format(label_options)
    selected = schema["json_schema"]["schema"]["properties"]["selected_label"]

    assert selected["enum"] == ["computer_science", "vocational_cloud"]


def test_architecture_trial_matrix_has_expected_small_scale():
    args = type(
        "Args",
        (),
        {
            "seed": [],
            "lr": 0.001,
            "weight_decay": 0.0001,
            "batch_size": 64,
        },
    )()

    runs = build_trial_matrix(args)

    assert len(runs) == 18
    assert {run.seed for run in runs} == {42, 43, 44}
    assert any(run.architecture.model_kind == "deep_mlp" for run in runs)
    assert any(run.architecture.model_kind == "residual_mlp" for run in runs)


def test_frkan_trial_matrix_has_expected_dual_protocol_scale():
    args = type(
        "Args",
        (),
        {
            "seed": [],
            "weight_decay": 0.0001,
            "batch_size": 64,
        },
    )()

    runs = build_frkan_trial_matrix(args)

    assert len(runs) == 15
    assert {run.seed for run in runs} == {42, 43, 44}
    assert {run.config.protocol for run in runs} == {"fair_probe", "paper_suggested"}
    assert any(
        run.config.model_kind == "fr_kan" and run.config.fourier_grid_size == 5
        for run in runs
    )


def test_error_analysis_outputs_topk_and_confusion(workspace_tmp):
    rows = [
        {
            "text": "alpha",
            "normalized_text": "alpha",
            "leaf_id": "a",
            "source": "observed_names",
        },
        {
            "text": "beta",
            "normalized_text": "beta",
            "leaf_id": "b",
            "source": "observed_names",
        },
    ]
    input_path = workspace_tmp / "val.jsonl"
    with input_path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    embeddings_path = workspace_tmp / "embeddings.npz"
    np.savez(
        embeddings_path,
        texts=np.asarray(["alpha", "beta"], dtype=object),
        embeddings=np.asarray([[1.0, 0.0], [0.0, 1.0]], dtype=np.float32),
    )
    label_map_path = workspace_tmp / "label_map.json"
    label_map_path.write_text(json.dumps({"a": 0, "b": 1}), encoding="utf-8")
    tree_path = workspace_tmp / "tree.json"
    tree_path.write_text(
        json.dumps(
            {
                "nodes": {
                    "a": {"id": "a", "label": "A", "parent": None, "level": 2},
                    "b": {"id": "b", "label": "B", "parent": None, "level": 2},
                }
            }
        ),
        encoding="utf-8",
    )
    model = torch.nn.Linear(2, 2)
    with torch.no_grad():
        model.weight.copy_(torch.eye(2))
        model.bias.zero_()
    probe_path = workspace_tmp / "probe.pt"
    torch.save(
        {
            "state_dict": {
                key: value.detach().clone() for key, value in model.state_dict().items()
            },
            "model_config": {
                "input_dim": 2,
                "output_dim": 2,
                "model_kind": "linear",
                "hidden_dim": 2,
                "dropout": 0.0,
            },
        },
        probe_path,
    )

    args = type(
        "Args",
        (),
        {
            "input_jsonl": str(input_path),
            "embeddings": str(embeddings_path),
            "probe": str(probe_path),
            "label_map": str(label_map_path),
            "major_tree": str(tree_path),
            "output_dir": str(workspace_tmp / "analysis"),
            "label_field": "leaf_id",
            "text_field": "normalized_text",
            "top_k": 2,
        },
    )()

    result = analyze(args)

    assert result["summary"]["topk_accuracy"] == 1.0
    assert result["per_sample"][0]["predictions"]
    assert "a" in result["confusion"]
