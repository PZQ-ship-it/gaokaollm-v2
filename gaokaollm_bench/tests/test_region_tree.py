from pathlib import Path

from gaokaollm_bench.data_gen.region_tree import (
    build_coverage_report,
    load_tree,
    normalize_region_name,
    validate_tree,
)


def test_region_tree_artifacts_validate():
    geo_tree = load_tree(Path("gaokaollm_bench/outputs/region_geo_tree.json"))
    urban_tree = load_tree(Path("gaokaollm_bench/outputs/region_urban_tier_tree.json"))

    assert validate_tree(geo_tree, "geo") == []
    assert validate_tree(urban_tree, "urban_tier") == []


def test_normalize_region_name_strips_common_suffixes():
    assert normalize_region_name("浙江省") == "浙江"
    assert normalize_region_name("杭州市") == "杭州"
    assert normalize_region_name("新疆维吾尔自治区") == "新疆"


def test_build_coverage_report_maps_known_city_and_flags_unknown_city():
    geo_tree = load_tree(Path("gaokaollm_bench/outputs/region_geo_tree.json"))
    urban_tree = load_tree(Path("gaokaollm_bench/outputs/region_urban_tier_tree.json"))
    rows = [
        {"province": "浙江", "city": "杭州", "school_count": 5},
        {"province": "浙江", "city": "舟山", "school_count": 1},
    ]

    report = build_coverage_report(rows, geo_tree, urban_tree)

    entries = {entry["city"]: entry for entry in report["entries"]}
    assert entries["杭州"]["geo_node_id"] == "geo:city:hangzhou"
    assert entries["杭州"]["urban_node_id"] == "urban:city:hangzhou"
    assert entries["杭州"]["review_status"] == "reviewed"

    assert entries["舟山"]["geo_node_id"] == "geo:province:zhejiang"
    assert entries["舟山"]["urban_node_id"] is None
    assert entries["舟山"]["review_status"] == "needs_review"
    assert "urban_tier_unmatched" in entries["舟山"]["review_reasons"]


def test_coverage_report_keeps_region_tree_boundary():
    geo_tree = load_tree(Path("gaokaollm_bench/outputs/region_geo_tree.json"))
    urban_tree = load_tree(Path("gaokaollm_bench/outputs/region_urban_tier_tree.json"))
    report = build_coverage_report(
        [{"province": "江苏", "city": "南京", "school_count": 3}],
        geo_tree,
        urban_tree,
    )

    assert report["boundary"]["region_tree_relax_status"] == "data_layer_v0_only"
    assert report["boundary"]["agent_benchmark_status"] == "not_implemented"
