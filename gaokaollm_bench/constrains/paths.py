"""Common default paths used by data builders and manual experiments."""

from __future__ import annotations

from pathlib import Path


PACKAGE_ROOT = Path("gaokaollm_bench")
OUTPUTS_DIR = PACKAGE_ROOT / "outputs"
SAMPLE_DATA_DIR = PACKAGE_ROOT / "sample_data"

MAJOR_TRAINING_DIR = OUTPUTS_DIR / "major_training"
MAJOR_TRAINING_SPLITS_DIR = MAJOR_TRAINING_DIR / "splits"
MAJOR_TRAINING_PROBE_DIR = OUTPUTS_DIR / "major_training_probe"
MAJOR_PROBE_CLASSIFICATION_ABLATION_DIR = (
    OUTPUTS_DIR / "major_probe_classification_ablation"
)
MAJOR_PROBE_ARCHITECTURE_TRIALS_DIR = OUTPUTS_DIR / "major_probe_architecture_trials"
MAJOR_PROBE_FRKAN_TRIALS_DIR = OUTPUTS_DIR / "major_probe_frkan_trials"
MAJOR_VAL_BENCHMARK_DIR = OUTPUTS_DIR / "major_val_benchmark"

MAJOR_TRAIN_JSONL = MAJOR_TRAINING_DIR / "train.jsonl"
MAJOR_VAL_JSONL = MAJOR_TRAINING_SPLITS_DIR / "val.jsonl"
MAJOR_EMBEDDINGS = MAJOR_TRAINING_DIR / "embeddings.npz"
MAJOR_RAW_TRAIN_ONLY_JSONL = (
    MAJOR_PROBE_CLASSIFICATION_ABLATION_DIR / "data" / "raw_train_only.jsonl"
)
MAJOR_EMBEDDINGS_UNION_VAL_FILLED = (
    MAJOR_TRAINING_DIR / "embeddings_union_val_filled.npz"
)
MAJOR_DEFAULT_PROBE = MAJOR_TRAINING_PROBE_DIR / "best_probe.pt"
MAJOR_DEFAULT_LABEL_MAP = MAJOR_TRAINING_PROBE_DIR / "label_map.json"
MAJOR_ABLATION_BEST_PROBE = (
    MAJOR_PROBE_CLASSIFICATION_ABLATION_DIR
    / "raw_mlp_h256_sqrt_balanced_s42"
    / "best_probe.pt"
)
MAJOR_ABLATION_BEST_LABEL_MAP = (
    MAJOR_PROBE_CLASSIFICATION_ABLATION_DIR
    / "raw_mlp_h256_sqrt_balanced_s42"
    / "label_map.json"
)

MAJOR_OBSERVED_TREE = SAMPLE_DATA_DIR / "major_tree_observed_full.json"
MAJOR_FINAL_TREE = OUTPUTS_DIR / "major_tree_final_reviewed.json"
MAJOR_FINAL_TREE_AUDIT = OUTPUTS_DIR / "major_tree_final_reviewed_audit.json"
MAJOR_REVIEW_CANDIDATES = OUTPUTS_DIR / "major_probe_review_candidates.json"
MAJOR_REVIEW_CANDIDATES_REVIEWED = (
    OUTPUTS_DIR / "major_probe_review_candidates_llm_reviewed.json"
)

DEFAULT_PERSONA_OUTPUT = SAMPLE_DATA_DIR / "iceberg_personas_real_db.json"
