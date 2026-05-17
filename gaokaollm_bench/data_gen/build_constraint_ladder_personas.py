"""Build a small constraint-ladder diagnostic persona set from real DB personas."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from gaokaollm_bench.schemas import IcebergPersona


SAMPLE_DATA_DIR = Path("gaokaollm_bench/sample_data")
DEFAULT_OUTPUT = SAMPLE_DATA_DIR / "iceberg_personas_constraint_ladder_real_db_9.json"
SUBJECTS = ["物理", "化学", "生物"]


@dataclass(frozen=True)
class LadderSpec:
    case_id: str
    source_file: str
    source_case_id: str
    school_name: str
    major_name: str
    constraint_count: int
    diagnostic_level: str
    relax_axis: str
    benefit_axis: str
    explicit_red_lines: dict[str, str]
    initial_utterance: str
    trigger_condition: str
    compromise: str


SPECS = [
    LadderSpec(
        case_id="constraint-ladder-1c-geo-001",
        source_file="iceberg_personas_major_hierarchy_real_db_10.json",
        source_case_id="real-db-set-浙江-542-001",
        school_name="东北农业大学",
        major_name="动物科学",
        constraint_count=1,
        diagnostic_level="1-constrain",
        relax_axis="geo",
        benefit_axis="school_tier",
        explicit_red_lines={"geo": "只想留在浙江，不主动看省外学校"},
        initial_utterance="我542分，选考物理化学生物，只想留在浙江，专业先不死守。",
        trigger_condition=(
            "只要看到一个省外真实可达的211/双一流候选，且包含学校名、专业名、最低分"
            "和位次证据，就愿意考虑出省。"
        ),
        compromise="可以为了从普通本科跃迁到211/双一流而放宽地域。",
    ),
    LadderSpec(
        case_id="constraint-ladder-1c-major-002",
        source_file="iceberg_personas_major_hierarchy_threshold3_real_db_10.json",
        source_case_id="real-db-set-浙江-560-002",
        school_name="石河子大学",
        major_name="预防医学",
        constraint_count=1,
        diagnostic_level="1-constrain",
        relax_axis="major",
        benefit_axis="school_tier",
        explicit_red_lines={"major": "只想读临床医学，其他医学相关专业先不看"},
        initial_utterance="我560分，选考物理化学生物，只想读临床医学，其他专业先别推荐。",
        trigger_condition=(
            "只要看到一个医学相关、真实可达且学校层次明显更高的候选，"
            "并给出最低分和位次证据，就愿意放宽到相近医学专业。"
        ),
        compromise="可以为了211/双一流层次，把临床医学放宽到预防医学等相近医学专业。",
    ),
    LadderSpec(
        case_id="constraint-ladder-1c-risk-003",
        source_file="iceberg_personas_risk_band_real_db_10.json",
        source_case_id="real-db-set-浙江-606-010",
        school_name="宁波大学",
        major_name="临床医学",
        constraint_count=1,
        diagnostic_level="1-constrain",
        relax_axis="risk",
        benefit_axis="school_tier",
        explicit_red_lines={"risk": "只想稳妥，不想冲刺压线学校"},
        initial_utterance="我606分，选考物理化学生物，只想稳妥一点，临床医学不要冲太危险。",
        trigger_condition=(
            "只要看到一个同省同专业、真实可达且层次更高的候选，"
            "并明确说明最低分、位次和风险层级，就愿意接受轻微冲刺。"
        ),
        compromise="可以为了双一流临床医学接受一个分数贴边但证据清楚的候选。",
    ),
    LadderSpec(
        case_id="constraint-ladder-2c-geo-major-004",
        source_file="iceberg_personas_region_tree_real_db_10.json",
        source_case_id="real-db-set-浙江-618-005",
        school_name="湖南师范大学",
        major_name="临床医学",
        constraint_count=2,
        diagnostic_level="2-constrain",
        relax_axis="geo",
        benefit_axis="school_tier",
        explicit_red_lines={
            "geo": "优先只看杭州或浙江附近",
            "major": "临床医学优先，不想换专业",
        },
        initial_utterance="我618分，选考物理化学生物，想读临床医学，优先只看杭州或浙江附近。",
        trigger_condition=(
            "只要看到一个临床医学不变、真实可达且学校层次更高的省外候选，"
            "并给出最低分和位次证据，就愿意放宽地域。"
        ),
        compromise="可以为了211/双一流临床医学放宽城市和省份。",
    ),
    LadderSpec(
        case_id="constraint-ladder-2c-major-risk-005",
        source_file="iceberg_personas_major_hierarchy_threshold3_real_db_10.json",
        source_case_id="real-db-set-浙江-580-006",
        school_name="成都中医药大学",
        major_name="康复治疗学",
        constraint_count=2,
        diagnostic_level="2-constrain",
        relax_axis="major",
        benefit_axis="school_tier",
        explicit_red_lines={
            "major": "只想读临床医学，其他医学相关专业先不看",
            "risk": "希望分数余量明显，不想压线",
        },
        initial_utterance="我580分，选考物理化学生物，只想读临床医学，而且希望分数余量稳一点。",
        trigger_condition=(
            "只要看到一个医学相关、分数余量充足且学校层次更高的真实候选，"
            "并给出学校名、专业名、最低分和位次证据，就愿意放宽专业小类。"
        ),
        compromise="可以为了稳妥的双一流医学相关机会，把临床医学放宽到康复治疗学。",
    ),
    LadderSpec(
        case_id="constraint-ladder-2c-geo-tuition-006",
        source_file="iceberg_personas_major_hierarchy_real_db_10.json",
        source_case_id="real-db-set-浙江-550-006",
        school_name="东北农业大学",
        major_name="生物科学",
        constraint_count=2,
        diagnostic_level="2-constrain",
        relax_axis="geo",
        benefit_axis="school_tier",
        explicit_red_lines={
            "geo": "只想留在浙江",
            "tuition": "学费最好保持普通公办水平",
        },
        initial_utterance="我550分，选考物理化学生物，只想留在浙江，学费最好保持普通公办水平。",
        trigger_condition=(
            "只要看到一个省外公办双一流候选，分数真实可达，并给出最低分和位次证据，"
            "就愿意先放宽地域。"
        ),
        compromise="可以为了公办双一流层次放宽地域，但不接受明显高收费项目。",
    ),
    LadderSpec(
        case_id="constraint-ladder-3c-geo-major-risk-007",
        source_file="iceberg_personas_region_tree_real_db_10.json",
        source_case_id="real-db-set-浙江-622-007",
        school_name="湖南师范大学",
        major_name="临床医学",
        constraint_count=3,
        diagnostic_level="3-constrain",
        relax_axis="geo",
        benefit_axis="school_tier",
        explicit_red_lines={
            "geo": "优先只看杭州或浙江附近",
            "major": "临床医学优先",
            "risk": "不要没有分数证据的压线推荐",
        },
        initial_utterance=(
            "我622分，选考物理化学生物，想读临床医学，优先只看杭州或浙江附近，"
            "没有分数证据的压线推荐先别给。"
        ),
        trigger_condition=(
            "只要看到一个临床医学不变、真实可达、最低分证据清楚的211/双一流候选，"
            "就愿意放宽地域。"
        ),
        compromise="可以为了211/双一流临床医学放宽地域，但必须保留分数证据。",
    ),
    LadderSpec(
        case_id="constraint-ladder-3c-geo-major-tuition-008",
        source_file="iceberg_personas_major_hierarchy_threshold3_real_db_10.json",
        source_case_id="real-db-set-浙江-600-010",
        school_name="南京中医药大学",
        major_name="康复治疗学",
        constraint_count=3,
        diagnostic_level="3-constrain",
        relax_axis="major",
        benefit_axis="school_tier",
        explicit_red_lines={
            "geo": "优先留在浙江或江浙沪",
            "major": "只想读临床医学",
            "tuition": "不考虑明显高收费项目",
        },
        initial_utterance=(
            "我600分，选考物理化学生物，优先留在浙江或江浙沪，只想读临床医学，"
            "明显高收费项目先别推荐。"
        ),
        trigger_condition=(
            "只要看到一个江浙沪范围内、公办双一流、医学相关且真实可达的候选，"
            "并给出最低分和位次证据，就愿意放宽专业小类。"
        ),
        compromise="可以为了双一流医学相关机会，把临床医学放宽到康复治疗学。",
    ),
    LadderSpec(
        case_id="constraint-ladder-3c-school-major-geo-009",
        source_file="iceberg_personas_major_any_real_db_10.json",
        source_case_id="real-db-set-浙江-660-007",
        school_name="浙江大学医学院",
        major_name="预防医学",
        constraint_count=3,
        diagnostic_level="3-constrain",
        relax_axis="major",
        benefit_axis="school_tier",
        explicit_red_lines={
            "school": "学校层次必须是985",
            "major": "只想读临床医学",
            "geo": "最好留在浙江",
        },
        initial_utterance="我660分，选考物理化学生物，学校层次必须是985，最好留在浙江，只想读临床医学。",
        trigger_condition=(
            "只要看到一个浙江省内985医学类候选，真实可达且给出最低分和位次证据，"
            "就愿意把临床医学放宽到预防医学。"
        ),
        compromise="可以为了浙江省内985医学平台，把临床医学放宽到预防医学。",
    ),
]


def _load_items(source_file: str) -> list[dict[str, Any]]:
    path = SAMPLE_DATA_DIR / source_file
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("items", [])
    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a list or items list")
    return data


def _source_persona(spec: LadderSpec) -> dict[str, Any]:
    for item in _load_items(spec.source_file):
        if item.get("case_id") == spec.source_case_id:
            return item
    raise ValueError(f"source case not found: {spec.source_file} {spec.source_case_id}")


def _source_volunteer(source: dict[str, Any], spec: LadderSpec) -> dict[str, Any]:
    volunteers = (source.get("implicit_flexibilities") or {}).get("volunteer_set") or []
    for row in volunteers:
        if (
            row.get("school_name") == spec.school_name
            and row.get("major_name") == spec.major_name
        ):
            copied = dict(row)
            copied["source_persona_file"] = spec.source_file
            copied["source_case_id"] = spec.source_case_id
            return copied
    raise ValueError(
        f"volunteer not found: {spec.source_file} {spec.source_case_id} "
        f"{spec.school_name} {spec.major_name}"
    )


def build_persona(spec: LadderSpec) -> IcebergPersona:
    source = _source_persona(spec)
    source_bg = source.get("background") or {}
    volunteer = _source_volunteer(source, spec)
    score = int(source_bg["score"])
    baseline_tier = int(source_bg.get("baseline_tier") or 0)
    target_tier = int(volunteer.get("tier") or baseline_tier)
    tier_delta = max(0, target_tier - baseline_tier)
    background = {
        "score": score,
        "province": "浙江",
        "subjects": SUBJECTS,
        "preferred_major": spec.major_name,
        "baseline_school": source_bg.get("baseline_school"),
        "baseline_tier": baseline_tier,
        "baseline_label": source_bg.get("baseline_label"),
        "constraint_count": spec.constraint_count,
        "diagnostic_level": spec.diagnostic_level,
        "relax_axis": spec.relax_axis,
        "benefit_axis": spec.benefit_axis,
        "trigger_evidence_count": 1,
        "source_persona_file": spec.source_file,
        "source_case_id": spec.source_case_id,
        "target_tier_delta": tier_delta,
    }
    flex = {
        "trigger_type": "single_verified_option",
        "constraint_relaxed": spec.relax_axis,
        "trigger_condition": spec.trigger_condition,
        "volunteer_set": [volunteer],
        "minimum_required_volunteers": 1,
        "representative_schools": [spec.school_name],
        "tier_labels": [volunteer.get("tier_label")],
        "benefit_axis": spec.benefit_axis,
        "compromise": spec.compromise,
    }
    milestones = {
        "reject_generic_advice": True,
        "reject_unverified_option": True,
        "require_single_verified_option": True,
        "require_school_major_score_evidence": True,
        "require_option_advantage": True,
        "accept_after_verified_option": [spec.school_name],
    }
    return IcebergPersona(
        case_id=spec.case_id,
        background=background,
        explicit_red_lines=spec.explicit_red_lines,
        implicit_flexibilities=flex,
        initial_utterance=spec.initial_utterance,
        process_milestones=milestones,
    )


def build_dataset() -> list[IcebergPersona]:
    personas = [build_persona(spec) for spec in SPECS]
    if len(personas) != 9:
        raise AssertionError(f"expected 9 personas, got {len(personas)}")
    counts = {item.background["constraint_count"] for item in personas}
    if counts != {1, 2, 3}:
        raise AssertionError(f"unexpected constraint counts: {counts}")
    return personas


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    args = parser.parse_args()
    personas = build_dataset()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            [persona.model_dump() for persona in personas], ensure_ascii=False, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(personas)} personas to {output}")
    for persona in personas:
        bg = persona.background
        print(
            f"{persona.case_id}: {bg['diagnostic_level']} "
            f"relax={bg['relax_axis']} benefit={bg['benefit_axis']}"
        )


if __name__ == "__main__":
    main()
