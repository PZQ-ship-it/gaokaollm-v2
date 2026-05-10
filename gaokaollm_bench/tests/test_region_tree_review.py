import json
import tempfile
from pathlib import Path

from gaokaollm_bench.data_gen.region_tree import build_coverage_report, load_tree
from gaokaollm_bench.data_gen.region_tree_review import (
    apply_seed_reviews,
    build_review_packet,
    build_v1_report,
    read_review_packet,
)


def _sample_report():
    geo_tree = load_tree(Path("gaokaollm_bench/outputs/region_geo_tree.json"))
    urban_tree = load_tree(Path("gaokaollm_bench/outputs/region_urban_tier_tree.json"))
    rows = [
        {"province": "浙江", "city": "杭州", "school_count": 8},
        {"province": "浙江", "city": "舟山", "school_count": 3},
        {"province": "内蒙古", "city": "呼和浩特", "school_count": 6},
    ]
    return build_coverage_report(rows, geo_tree, urban_tree), geo_tree, urban_tree


def test_review_packet_keeps_unmatched_and_low_confidence_items():
    report, _, _ = _sample_report()

    packet = build_review_packet(report)

    cities = [row["city"] for row in packet]
    assert "舟山" in cities
    assert "呼和浩特" in cities
    assert cities[0] == "呼和浩特"
    assert packet[0]["priority_score"] > packet[1]["priority_score"]
    assert packet[0]["suggested_geo_parent_id"] == "geo:north_china"
    assert packet[0]["suggested_urban_parent_id"] == "urban:tier:strong_capital"
    assert packet[0]["reviewer_geo_action"] == ""


def test_apply_seed_reviews_adds_reviewed_nodes_and_preserves_schema():
    report, geo_tree, urban_tree = _sample_report()
    packet = build_review_packet(report)

    geo_v1, urban_v1, reviewed_rows = apply_seed_reviews(
        packet=packet,
        geo_tree=geo_tree,
        urban_tree=urban_tree,
        top_n=2,
    )

    geo_nodes = {node["node_id"]: node for node in geo_v1["nodes"]}
    urban_nodes = {node["node_id"]: node for node in urban_v1["nodes"]}
    assert len(reviewed_rows) == 2
    assert reviewed_rows[0]["reviewer_geo_action"] == "accept_suggested_geo"
    assert reviewed_rows[0]["reviewer_confidence"] == "0.82"
    assert reviewed_rows[0]["suggested_geo_node_id"] in geo_nodes
    assert reviewed_rows[0]["suggested_urban_node_id"] in urban_nodes
    assert geo_nodes[reviewed_rows[0]["suggested_geo_node_id"]]["review_status"] == (
        "reviewed"
    )
    assert (
        urban_nodes[reviewed_rows[0]["suggested_urban_node_id"]]["mapping_rule"]
        == "rule_seed_v1_urban_tier_attachment"
    )


def test_v1_report_compares_review_queue_delta():
    report, geo_tree, urban_tree = _sample_report()
    packet = build_review_packet(report)
    geo_v1, urban_v1, reviewed_rows = apply_seed_reviews(
        packet=packet,
        geo_tree=geo_tree,
        urban_tree=urban_tree,
        top_n=2,
    )

    v1_report = build_v1_report(
        v0_report=report,
        geo_v1=geo_v1,
        urban_v1=urban_v1,
        reviewed_rows=reviewed_rows,
    )

    assert v1_report["summary"]["v0"]["review_queue_count"] == 2
    assert v1_report["summary"]["v1"]["review_queue_count"] == 0
    assert v1_report["summary"]["delta"]["review_queue_count"] == -2
    assert v1_report["boundary"]["region_tree_relax_status"] == "not_implemented"


def test_reviewed_packet_can_be_read_and_applied():
    report, geo_tree, urban_tree = _sample_report()
    packet = build_review_packet(report)
    manual_row = dict(packet[0])
    manual_row["reviewer_geo_action"] = "accept_suggested_geo"
    manual_row["reviewer_urban_action"] = "accept_suggested_urban"
    manual_row["reviewer_note"] = "manual fixture review"
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as tmpdir:
        packet_path = Path(tmpdir) / "reviewed.jsonl"
        packet_path.write_text(
            json.dumps(manual_row, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )

        reviewed_packet = read_review_packet(packet_path)
        _, _, reviewed_rows = apply_seed_reviews(
            packet=reviewed_packet,
            geo_tree=geo_tree,
            urban_tree=urban_tree,
            require_reviewer_action=True,
        )

    assert len(reviewed_rows) == 1
    assert reviewed_rows[0]["reviewer_note"] == "manual fixture review"
