import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from langchain_core.messages import HumanMessage
from langgraph.types import Command

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_QUERY = (
    "我是浙江考生，分数600，选科物理、化学、生物，想读医学相关专业，"
    "只看江浙沪的学校，预算每年5500元以内。"
)
DEFAULT_REPLIES = [
    "ACCEPT",
    "REJECT",
    "HESITATE",
    "REJECT",
    "HESITATE",
]
NON_BUDGET_OPPORTUNITIES = {
    "major_geo_relax",
    "major_quality_relax",
    "employment_outcome_relax",
    "region_tree_relax",
    "risk_band_relax",
    "strength_relax",
    "geo_relax",
    "city_relax",
    "major_relax",
}
RELAXABLE_DIMENSIONS = {"geo", "major", "tuition", "risk"}
REVERSE_COST_DIMENSIONS = {"school", "quality"}
PROBE_SEQUENCE = (
    ("tuition_value_relax", "school"),
    ("major_geo_relax", "school"),
    ("risk_band_relax", "school"),
    ("region_tree_relax", "quality"),
    ("major_quality_relax", "quality"),
)
DEFAULT_CONSTRAINTS = {
    "score": 600,
    "province": "\u6d59\u6c5f",
    "target_provinces": ["\u6c5f\u82cf", "\u6d59\u6c5f", "\u4e0a\u6d77"],
    "major": "\u533b\u5b66",
    "budget": 5500,
    "selected_subjects": ["\u7269\u7406", "\u5316\u5b66", "\u751f\u7269"],
}


def _iter_rows(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    if isinstance(value, dict):
        rows: list[dict[str, Any]] = []
        for nested in value.values():
            rows.extend(_iter_rows(nested))
        return rows
    return []


def _log(args: argparse.Namespace, message: str) -> None:
    if args.verbose:
        print(f"[demo-trace] {message}", flush=True)


def _interrupt_payload(snapshot: Any) -> dict[str, Any]:
    for task in getattr(snapshot, "tasks", None) or []:
        for interrupt in getattr(task, "interrupts", None) or []:
            value = getattr(interrupt, "value", None)
            if isinstance(value, dict):
                payload = dict(value)
                if payload.get("text"):
                    payload["text"] = str(payload["text"])
                return payload
            elif value:
                return {"text": str(value)}
    values = getattr(snapshot, "values", {}) or {}
    question = values.get("latest_agent_probe_question")
    if not question:
        return {}
    return {
        "text": str(question),
        "latest_tradeoff_pair": values.get("latest_tradeoff_pair"),
        "latest_pareto_diff": values.get("latest_pareto_diff"),
        "latest_question_kind": values.get("latest_question_kind"),
        "latest_question_source": values.get("latest_question_source"),
        "latest_probe_target_dimension": values.get("latest_probe_target_dimension"),
    }


def _interrupt_question(snapshot: Any) -> str | None:
    payload = _interrupt_payload(snapshot)
    text = payload.get("text")
    return str(text) if text else None


def _latest_ai_message_text(values: dict[str, Any]) -> str:
    messages = values.get("messages") or []
    for message in reversed(messages):
        content = getattr(message, "content", None)
        if content:
            return str(content)
    return ""


def _current_probe(values: dict[str, Any]) -> str:
    plan = values.get("probe_plan") or []
    if not plan or not isinstance(plan[0], dict):
        return ""
    first = plan[0]
    probe = str(first.get("probe") or first.get("probe_name") or "")
    return probe.removeprefix("probe_")


def _opportunity_counts(values: dict[str, Any]) -> dict[str, int]:
    opportunities = values.get("pareto_opportunities") or {}
    if not isinstance(opportunities, dict):
        return {}
    return {key: len(_iter_rows(value)) for key, value in opportunities.items()}


def _bucket_counts(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    return {
        str(bucket): len(rows) if isinstance(rows, list) else len(_iter_rows(rows))
        for bucket, rows in value.items()
    }


def _final_recommendation_count(values: dict[str, Any]) -> int:
    explicit = values.get("final_recommendation_count")
    try:
        count = int(explicit)
    except (TypeError, ValueError):
        count = 0
    if count > 0:
        return count
    return sum(_bucket_counts(values.get("final_recommendation_matrix")).values())


def _candidate_preview(values: dict[str, Any], key: str) -> list[dict[str, Any]]:
    opportunities = values.get("pareto_opportunities") or {}
    rows = _iter_rows(opportunities.get(key)) if isinstance(opportunities, dict) else []
    preview: list[dict[str, Any]] = []
    for row in rows[:3]:
        preview.append(
            {
                "school_name": row.get("school_name") or row.get("school"),
                "school_province": row.get("school_province") or row.get("province"),
                "major_name": row.get("major_name") or row.get("major"),
                "tuition": row.get("tuition"),
                "ranking": row.get("ranking"),
                "tier": row.get("tier"),
                "geo_relax_level": row.get("geo_relax_level"),
                "major_relax_level": row.get("major_relax_level"),
                "major_similarity_score": row.get("major_similarity_score"),
                "major_similarity_label": row.get("major_similarity_label"),
                "risk_bucket": row.get("risk_bucket") or row.get("risk_level"),
                "semantic_score": row.get("semantic_score"),
                "semantic_score_source": row.get("semantic_score_source"),
                "_implicit_utility": row.get("_implicit_utility"),
                "_semantic_score": row.get("_semantic_score"),
                "_lexicographic_tier": row.get("_lexicographic_tier"),
                "_phi_features": row.get("_phi_features"),
            }
        )
    return preview


def _all_opportunity_rows(values: dict[str, Any]) -> list[dict[str, Any]]:
    opportunities = values.get("pareto_opportunities") or {}
    if not isinstance(opportunities, dict):
        return []
    rows: list[dict[str, Any]] = []
    for key, nested in opportunities.items():
        for row in _iter_rows(nested):
            enriched = dict(row)
            enriched.setdefault("_opportunity_key", str(key))
            rows.append(enriched)
    return rows


def _anchor_rows(values: dict[str, Any]) -> list[dict[str, Any]]:
    opportunities = values.get("pareto_opportunities") or {}
    global_rows = (
        _iter_rows(opportunities.get("global_baseline"))
        if isinstance(opportunities, dict)
        else []
    )
    accepted_rows = [
        row
        for row in _iter_rows(values.get("candidates") or [])
        if row.get("_accepted_relaxation")
    ]
    return [
        *accepted_rows,
        *global_rows,
        *_iter_rows(values.get("baseline_results") or []),
    ]


def _benefit_dimensions(
    opportunity_key: str,
    target_dimension: str,
    cost_dimensions: tuple[str, ...],
) -> tuple[str, ...]:
    preferred: list[str] = []
    if target_dimension in {"school", "quality"}:
        preferred.append(target_dimension)
    elif target_dimension in {"major", "risk"}:
        preferred.append(target_dimension)
    probe_benefits = {
        "major_geo_relax": ("school", "quality", "risk"),
        "geo_relax": ("school", "quality", "major", "risk"),
        "city_relax": ("school", "quality", "major", "risk"),
        "region_tree_relax": ("school", "quality", "major", "risk"),
        "major_relax": ("school", "quality", "geo", "risk"),
        "tuition_value_relax": ("school", "quality", "major", "risk"),
        "risk_band_relax": ("school", "quality", "major"),
        "major_quality_relax": ("quality", "school", "risk"),
        "employment_outcome_relax": ("quality", "school", "major"),
        "strength_relax": ("school", "quality", "major", "risk"),
    }
    preferred.extend(probe_benefits.get(opportunity_key, ()))
    preferred.extend(("school", "quality", "major", "risk", "geo"))
    result: list[str] = []
    for dimension in preferred:
        if dimension not in cost_dimensions and dimension not in result:
            result.append(dimension)
    return tuple(result)


def _cost_dimensions(opportunity_key: str, target_dimension: str) -> tuple[str, ...]:
    probe_costs = {
        "major_geo_relax": ("geo", "major"),
        "geo_relax": ("geo",),
        "city_relax": ("geo",),
        "region_tree_relax": ("geo",),
        "major_relax": ("major",),
        "tuition_value_relax": ("tuition",),
        "risk_band_relax": ("risk",),
        "major_quality_relax": ("major", "geo", "tuition"),
        "employment_outcome_relax": ("major", "geo"),
        "strength_relax": ("geo", "major", "tuition", "risk"),
    }
    if opportunity_key in probe_costs:
        return probe_costs[opportunity_key]
    if target_dimension in RELAXABLE_DIMENSIONS:
        return (target_dimension,)
    return tuple(RELAXABLE_DIMENSIONS)


def _available_cost_dimensions(
    values: dict[str, Any],
    opportunity_key: str,
    target_dimension: str,
) -> tuple[str, ...]:
    costs = _cost_dimensions(opportunity_key, target_dimension)
    blocked = {
        str(item)
        for item in (values.get("factual_blocked_dimensions") or [])
        if str(item) in RELAXABLE_DIMENSIONS
    }
    filtered = tuple(item for item in costs if item not in blocked)
    return filtered or costs


def _selector_audit_for_values(values: dict[str, Any]) -> dict[str, Any]:
    from app.graphs.nodes.negotiator import select_constrained_tradeoff_pair

    key = _current_probe(values)
    focused = _candidate_preview(values, key)
    raw_focused = []
    opportunities = values.get("pareto_opportunities") or {}
    if isinstance(opportunities, dict):
        for row in _iter_rows(opportunities.get(key)):
            enriched = dict(row)
            enriched.setdefault("_opportunity_key", key)
            raw_focused.append(enriched)
    anchors = _anchor_rows(values)
    all_rows = _all_opportunity_rows(values)
    target = str(values.get("ucb_target_dimension") or "")
    costs = _available_cost_dimensions(values, key, target)
    benefits = _benefit_dimensions(key, target, costs)
    option_a, option_b, delta, cost, benefit = select_constrained_tradeoff_pair(
        [*anchors, *raw_focused, *all_rows],
        cost_dimensions=costs,
        benefit_dimensions=benefits,
        challenger_rows=raw_focused,
        anchor_rows=anchors or all_rows,
        previous_delta_phi=values.get("latest_pareto_diff"),
    )
    return {
        "current_probe": key,
        "focused_candidate_count": len(focused),
        "option_a": {
            "school_name": option_a.get("school_name"),
            "major_name": option_a.get("major_name"),
            "_opportunity_key": option_a.get("_opportunity_key"),
        }
        if option_a
        else {},
        "option_b": {
            "school_name": option_b.get("school_name"),
            "major_name": option_b.get("major_name"),
            "_opportunity_key": option_b.get("_opportunity_key"),
        }
        if option_b
        else {},
        "delta": delta,
        "cost": cost,
        "benefit": benefit,
    }


def _synthetic_candidate(
    school_name: str,
    major_name: str,
    utility: float,
    features: dict[str, float],
    *,
    opportunity_key: str = "",
    province: str = "",
    tuition: int | None = None,
) -> dict[str, Any]:
    return {
        "school_name": school_name,
        "school_province": province,
        "major_name": major_name,
        "tuition": tuition,
        "ranking": 80,
        "quality_score": features.get("quality", 0.5),
        "min_rank": 52000,
        "risk_level": "match",
        "_implicit_utility": utility,
        "_opportunity_key": opportunity_key,
        "_phi_features": {
            "school": 0.5,
            "major": 1.0,
            "tuition": 1.0,
            "quality": 0.5,
            "geo": 1.0,
            "risk": 0.5,
            **features,
        },
    }


def _fetch_query_sync_with_timeout(
    query: str,
    *params: Any,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    import psycopg
    from psycopg.rows import dict_row

    from app.core.db_pg import get_database_url

    connect_timeout = max(1, int(min(timeout_seconds, 10)))
    statement_timeout_ms = max(1000, int(timeout_seconds * 1000))
    with psycopg.connect(
        get_database_url(),
        row_factory=dict_row,
        connect_timeout=connect_timeout,
        options=f"-c statement_timeout={statement_timeout_ms}",
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            rows = cur.fetchall()
            return [dict(row) for row in rows]


async def _fetch_query_with_timeout(
    query: str,
    *params: Any,
    timeout_seconds: float,
) -> list[dict[str, Any]]:
    return await asyncio.to_thread(
        _fetch_query_sync_with_timeout,
        query,
        *params,
        timeout_seconds=timeout_seconds,
    )


async def _preflight_snapshot(args: argparse.Namespace) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "database_url_configured": bool(os.environ.get("DATABASE_URL")),
        "openai_timeout": os.environ.get("OPENAI_TIMEOUT"),
        "openai_structured_timeout": os.environ.get("OPENAI_STRUCTURED_TIMEOUT"),
        "openai_reasoning_timeout": os.environ.get("OPENAI_REASONING_TIMEOUT"),
        "offline_deterministic": bool(args.offline_deterministic),
    }
    try:
        rows = await _fetch_query_with_timeout(
            "select 1 as ok",
            timeout_seconds=args.db_query_timeout_seconds,
        )
        snapshot["database_ready"] = bool(rows and rows[0].get("ok") == 1)
    except Exception as exc:
        snapshot["database_ready"] = False
        snapshot["database_error_type"] = type(exc).__name__
        snapshot["database_error"] = str(exc)[:240]
    return snapshot


async def _drain(
    app: Any,
    payload: Any,
    config: dict[str, Any],
    *,
    timeout_seconds: float | None = None,
) -> None:
    async def _consume() -> None:
        async for _event in app.astream(payload, config=config):
            pass

    if timeout_seconds is None or timeout_seconds <= 0:
        await _consume()
        return
    await asyncio.wait_for(_consume(), timeout=timeout_seconds)


def _round_record(
    turn: int,
    values: dict[str, Any],
    question: str,
    reply: str,
    *,
    interrupt_meta: dict[str, Any] | None = None,
    turn_latency_seconds: float | None = None,
) -> dict[str, Any]:
    meta = interrupt_meta or {}
    probe = _current_probe(values)
    counts = _opportunity_counts(values)
    return {
        "turn": turn,
        "turn_latency_seconds": turn_latency_seconds,
        "current_probe": probe,
        "ucb_target_dimension": values.get("ucb_target_dimension"),
        "latest_question_kind": values.get("latest_question_kind")
        or meta.get("latest_question_kind"),
        "latest_question_source": values.get("latest_question_source")
        or meta.get("latest_question_source"),
        "latest_probe_target_dimension": values.get("latest_probe_target_dimension")
        or meta.get("latest_probe_target_dimension"),
        "latest_tradeoff_pair": values.get("latest_tradeoff_pair")
        or meta.get("latest_tradeoff_pair"),
        "opportunity_rankings": values.get("opportunity_rankings"),
        "opportunity_counts": counts,
        "planner_source": values.get("planner_source"),
        "full_context_query_preview": str(values.get("full_context_query") or "")[:240],
        "full_context_embedding_model": values.get("full_context_embedding_model"),
        "full_context_embedding_present": bool(values.get("full_context_embedding")),
        "lexicographic_epsilon": values.get("lexicographic_epsilon"),
        "factual_blocked_dimensions": values.get("factual_blocked_dimensions") or [],
        "navigation_intent": values.get("navigation_intent"),
        "focused_candidates": _candidate_preview(values, probe),
        "selector_audit": _selector_audit_for_values(values),
        "question": question,
        "simulated_reply": reply,
        "latest_pareto_diff": values.get("latest_pareto_diff")
        or meta.get("latest_pareto_diff"),
    }


def analyze_rounds(rounds: list[dict[str, Any]]) -> dict[str, Any]:
    failures: list[str] = []
    tried_costs = [
        str(
            row.get("latest_probe_target_dimension")
            or ((row.get("selector_audit") or {}).get("cost"))
            or ""
        )
        for row in rounds
        if row.get("latest_question_kind") == "tradeoff"
        or ((row.get("selector_audit") or {}).get("cost"))
    ]
    non_budget_counts = (
        {
            key: max(
                int((row.get("opportunity_counts") or {}).get(key) or 0)
                for row in rounds
            )
            for key in NON_BUDGET_OPPORTUNITIES
        }
        if rounds
        else {}
    )
    non_budget_seen = any(count > 0 for count in non_budget_counts.values())

    for row in rounds:
        cost = str(
            row.get("latest_probe_target_dimension")
            or ((row.get("selector_audit") or {}).get("cost"))
            or ""
        )
        probe = str(row.get("current_probe") or "")
        selector = row.get("selector_audit") or {}
        selected_probe = str(
            ((selector.get("option_b") or {}).get("_opportunity_key") or "")
        )
        focused_count = int(selector.get("focused_candidate_count") or 0)
        if cost in REVERSE_COST_DIMENSIONS:
            failures.append(
                f"turn {row['turn']}: reverse relaxation cost dimension {cost}"
            )
        if (
            row.get("latest_question_kind") == "tradeoff"
            or ((row.get("selector_audit") or {}).get("cost"))
        ) and cost not in RELAXABLE_DIMENSIONS:
            failures.append(
                f"turn {row['turn']}: tradeoff cost dimension is not relaxable: {cost}"
            )
        question = str(row.get("question") or "")
        if "牺牲/放宽 学校层次" in question or "牺牲/放宽 学科与培养质量" in question:
            failures.append(f"turn {row['turn']}: question asks reverse relaxation")
        if probe in NON_BUDGET_OPPORTUNITIES and cost == "tuition":
            failures.append(f"turn {row['turn']}: non-budget probe used tuition cost")
        if probe in NON_BUDGET_OPPORTUNITIES and focused_count <= 0:
            failures.append(
                f"turn {row['turn']}: current probe has no focused candidates"
            )
        if (
            probe == "risk_band_relax"
            and row.get("latest_question_kind") == "tradeoff"
            and cost
            and cost != "risk"
        ):
            failures.append(
                f"turn {row['turn']}: risk probe used non-risk cost dimension {cost}"
            )
        if (
            probe == "risk_band_relax"
            and row.get("latest_question_kind") == "no_significant_tradeoff"
            and cost
            and cost != "risk"
        ):
            failures.append(
                f"turn {row['turn']}: risk no-significant probe reported non-risk dimension {cost}"
            )
        if probe == "risk_band_relax" and not cost:
            question = str(row.get("question") or "")
            no_significant = any(
                token in question
                for token in (
                    "没有看到",
                    "不足以形成",
                    "未发现",
                    "换个维度",
                    "换一个维度",
                    "直接查看最终",
                    "最终推荐",
                )
            )
            if not no_significant and not any(
                token in question for token in ("风险", "冲", "稳", "保", "录取弹性")
            ):
                failures.append(
                    f"turn {row['turn']}: risk probe produced no risk tradeoff"
                )
        if (
            probe in NON_BUDGET_OPPORTUNITIES
            and selected_probe
            and selected_probe != probe
        ):
            failures.append(
                f"turn {row['turn']}: selector chose {selected_probe} while current probe is {probe}"
            )
        for index, candidate in enumerate(row.get("focused_candidates") or [], start=1):
            features = candidate.get("_phi_features")
            if probe == "major_geo_relax" and isinstance(features, dict):
                try:
                    geo = float(features.get("geo", 1.0))
                    major = float(features.get("major", 1.0))
                except (TypeError, ValueError):
                    geo = 1.0
                    major = 1.0
                if geo >= 1.0 and major >= 1.0:
                    failures.append(
                        f"turn {row['turn']}: major_geo focused candidate {index} has no geo/major penalty"
                    )

    if (
        len(rounds) >= 2
        and non_budget_seen
        and tried_costs
        and set(tried_costs) <= {"tuition"}
    ):
        failures.append(
            "non-budget opportunities exist, but all tradeoff turns used tuition"
        )
    distinct_non_budget_costs = {
        cost for cost in tried_costs if cost in {"geo", "major", "risk"}
    }
    if len(rounds) >= 3 and non_budget_seen and not distinct_non_budget_costs:
        failures.append(
            "multi-turn trace never tried a non-budget relaxation dimension"
        )
    repeated_non_budget = [
        cost
        for cost in ("geo", "major", "risk")
        if sum(1 for item in tried_costs if item == cost) >= 3
    ]
    if len(tried_costs) >= 4 and repeated_non_budget and len(set(tried_costs)) <= 2:
        failures.append(
            "multi-turn trace repeats one non-budget dimension without exploring another axis: "
            + ",".join(repeated_non_budget)
        )

    return {
        "status": "failed" if failures else "ok",
        "failures": failures,
        "tried_cost_dimensions": tried_costs,
        "non_budget_opportunity_counts": non_budget_counts,
    }


def _simulated_opportunities() -> dict[str, Any]:
    baseline = [
        _synthetic_candidate(
            "浙江中医药大学",
            "药学",
            1.0,
            {
                "school": 0.55,
                "major": 0.95,
                "tuition": 1.0,
                "quality": 0.55,
                "geo": 1.0,
                "risk": 0.72,
            },
            opportunity_key="global_baseline",
            province="浙江",
            tuition=5300,
        ),
        _synthetic_candidate(
            "南京医科大学",
            "康复治疗学",
            0.96,
            {
                "school": 0.62,
                "major": 0.90,
                "tuition": 1.0,
                "quality": 0.64,
                "geo": 1.0,
                "risk": 0.62,
            },
            opportunity_key="global_baseline",
            province="江苏",
            tuition=5500,
        ),
    ]
    tuition = [
        _synthetic_candidate(
            "江苏大学",
            "临床医学",
            1.35,
            {
                "school": 0.68,
                "major": 1.0,
                "tuition": 0.42,
                "quality": 0.66,
                "geo": 1.0,
                "risk": 0.66,
            },
            opportunity_key="tuition_value_relax",
            province="江苏",
            tuition=7480,
        )
    ]
    major_geo = [
        {
            **_synthetic_candidate(
                "北京体育大学",
                "运动康复",
                1.05,
                {
                    "school": 0.82,
                    "major": 0.68,
                    "tuition": 1.0,
                    "quality": 0.78,
                    "geo": 0.55,
                    "risk": 0.70,
                },
                opportunity_key="major_geo_relax",
                province="北京",
                tuition=5000,
            ),
            "geo_relax_level": 1,
            "major_relax_level": 2,
        },
        {
            **_synthetic_candidate(
                "河南大学",
                "公共卫生与预防医学",
                1.02,
                {
                    "school": 0.76,
                    "major": 0.72,
                    "tuition": 1.0,
                    "quality": 0.74,
                    "geo": 0.58,
                    "risk": 0.68,
                },
                opportunity_key="major_geo_relax",
                province="河南",
                tuition=5060,
            ),
            "geo_relax_level": 1,
            "major_relax_level": 1,
        },
    ]
    risk = [
        {
            **_synthetic_candidate(
                "浙江大学医学院",
                "预防医学",
                0.98,
                {
                    "school": 0.95,
                    "major": 0.92,
                    "tuition": 0.90,
                    "quality": 0.92,
                    "geo": 1.0,
                    "risk": 0.25,
                },
                opportunity_key="risk_band_relax",
                province="浙江",
                tuition=6000,
            ),
            "risk_level": "reach",
            "risk_relax_level": 1,
            "min_rank": 43000,
        }
    ]
    region = [
        {
            **_synthetic_candidate(
                "安徽医科大学",
                "医学影像学",
                1.01,
                {
                    "school": 0.72,
                    "major": 0.88,
                    "tuition": 1.0,
                    "quality": 0.70,
                    "geo": 0.72,
                    "risk": 0.66,
                },
                opportunity_key="region_tree_relax",
                province="安徽",
                tuition=5500,
            ),
            "geo_relax_level": 1,
        }
    ]
    quality = [
        {
            **_synthetic_candidate(
                "中国药科大学",
                "药物制剂",
                1.04,
                {
                    "school": 0.84,
                    "major": 0.78,
                    "tuition": 0.92,
                    "quality": 0.90,
                    "geo": 1.0,
                    "risk": 0.58,
                },
                opportunity_key="major_quality_relax",
                province="江苏",
                tuition=6380,
            ),
            "major_relax_level": 1,
        }
    ]
    return {
        "global_baseline": {"match": baseline[:1], "safety": baseline[1:]},
        "tuition_value_relax": tuition,
        "major_geo_relax": major_geo,
        "risk_band_relax": risk,
        "region_tree_relax": region,
        "major_quality_relax": quality,
    }


async def run_probe_audit(args: argparse.Namespace) -> dict[str, Any]:
    from app.flows.probers import run_all_probes
    from app.graphs.nodes.negotiator import select_constrained_tradeoff_pair

    user_state = {
        "constraints": DEFAULT_CONSTRAINTS,
        "accepted_relaxations": [{"dimension": "tuition", "accepted_budget": 6000}],
    }

    async def audit_db(query: str, *params: Any) -> list[dict[str, Any]]:
        return await _fetch_query_with_timeout(
            query,
            *params,
            timeout_seconds=args.db_query_timeout_seconds,
        )

    try:
        opportunities = await asyncio.wait_for(
            run_all_probes(DEFAULT_CONSTRAINTS, db=audit_db, user_state=user_state),
            timeout=args.turn_timeout_seconds,
        )
    except asyncio.TimeoutError:
        return {
            "thread_id": args.thread_id or f"probe-audit-{int(time.time())}",
            "mode": "probe_audit",
            "constraints": DEFAULT_CONSTRAINTS,
            "opportunity_counts": {},
            "major_geo_preview": [],
            "selected_pair": {},
            "analysis": {
                "status": "failed",
                "failures": [
                    f"probe audit timed out after {args.turn_timeout_seconds} seconds"
                ],
            },
        }
    except Exception as exc:
        return {
            "thread_id": args.thread_id or f"probe-audit-{int(time.time())}",
            "mode": "probe_audit",
            "constraints": DEFAULT_CONSTRAINTS,
            "opportunity_counts": {},
            "major_geo_preview": [],
            "selected_pair": {},
            "analysis": {
                "status": "failed",
                "failures": [
                    f"probe audit failed before candidate analysis: {type(exc).__name__}: {exc}"
                ],
            },
        }
    major_geo_rows = _iter_rows(opportunities.get("major_geo_relax"))
    tuition_rows = _iter_rows(opportunities.get("tuition_value_relax"))
    anchors = [
        {
            "school_name": "Accepted Budget Anchor",
            "major_name": "Medical Anchor",
            "_implicit_utility": 1.0,
            "_phi_features": {
                "school": 0.5,
                "major": 1.0,
                "tuition": 0.65,
                "quality": 0.5,
                "geo": 1.0,
                "risk": 0.5,
            },
        }
    ]
    option_a, option_b, delta, cost, benefit = select_constrained_tradeoff_pair(
        [*anchors, *tuition_rows, *major_geo_rows],
        cost_dimensions=("geo", "major"),
        benefit_dimensions=("school", "quality", "risk"),
        challenger_rows=major_geo_rows,
        anchor_rows=anchors,
    )
    failures: list[str] = []
    if not major_geo_rows:
        failures.append("major_geo_relax returned no non-budget candidates")
    if option_b and option_b in tuition_rows:
        failures.append("selector chose stale tuition candidate")
    if cost in REVERSE_COST_DIMENSIONS:
        failures.append(f"selector used reverse cost dimension {cost}")
    if option_b and cost not in {"geo", "major"}:
        failures.append(f"selector did not use non-budget cost dimension: {cost}")
    for index, row in enumerate(major_geo_rows[:3], start=1):
        features = row.get("_phi_features") if isinstance(row, dict) else {}
        if isinstance(features, dict) and (
            float(features.get("geo", 1.0)) >= 1.0
            and float(features.get("major", 1.0)) >= 1.0
        ):
            failures.append(f"major_geo row {index} has no geo/major penalty")

    return {
        "thread_id": args.thread_id or f"probe-audit-{int(time.time())}",
        "mode": "probe_audit",
        "constraints": DEFAULT_CONSTRAINTS,
        "opportunity_counts": {
            key: len(_iter_rows(value)) for key, value in opportunities.items()
        },
        "major_geo_preview": _candidate_preview(
            {"pareto_opportunities": {"major_geo_relax": major_geo_rows}},
            "major_geo_relax",
        ),
        "selected_pair": {
            "option_a": {
                "school_name": option_a.get("school_name"),
                "major_name": option_a.get("major_name"),
            }
            if option_a
            else {},
            "option_b": {
                "school_name": option_b.get("school_name"),
                "major_name": option_b.get("major_name"),
                "_opportunity_key": option_b.get("_opportunity_key"),
            }
            if option_b
            else {},
            "delta": delta,
            "cost": cost,
            "benefit": benefit,
        },
        "analysis": {
            "status": "failed" if failures else "ok",
            "failures": failures,
        },
    }


async def run_selector_audit(args: argparse.Namespace) -> dict[str, Any]:
    from app.graphs.nodes.negotiator import select_constrained_tradeoff_pair

    anchor = _synthetic_candidate(
        "当前预算内医学候选",
        "医学相关专业",
        1.0,
        {"school": 0.50, "major": 1.0, "tuition": 0.70, "quality": 0.50, "geo": 1.0},
        opportunity_key="global_baseline",
        province="浙江",
        tuition=5500,
    )
    stale_budget = _synthetic_candidate(
        "上一轮预算放宽候选",
        "医学相关专业",
        1.5,
        {"school": 0.58, "major": 1.0, "tuition": 0.45, "quality": 0.55, "geo": 1.0},
        opportunity_key="tuition_value_relax",
        province="江苏",
        tuition=7480,
    )
    major_geo = _synthetic_candidate(
        "全国范围更强候选",
        "公共卫生与预防医学",
        0.95,
        {"school": 0.82, "major": 0.65, "tuition": 1.0, "quality": 0.75, "geo": 0.65},
        opportunity_key="major_geo_relax",
        province="北京",
        tuition=5000,
    )
    option_a, option_b, delta, cost, benefit = select_constrained_tradeoff_pair(
        [anchor, stale_budget, major_geo],
        cost_dimensions=("geo", "major"),
        benefit_dimensions=("school", "quality", "risk"),
        challenger_rows=[major_geo],
        anchor_rows=[anchor, stale_budget],
    )
    failures: list[str] = []
    if option_b.get("_opportunity_key") != "major_geo_relax":
        failures.append("selector did not prioritize the current non-budget probe")
    if cost in REVERSE_COST_DIMENSIONS:
        failures.append(f"selector used reverse cost dimension {cost}")
    if cost not in {"geo", "major"}:
        failures.append(
            f"selector did not use geo/major as the relaxation cost: {cost}"
        )
    if benefit not in {"school", "quality", "risk"}:
        failures.append(f"selector used unexpected benefit dimension: {benefit}")
    if delta.get(str(cost), 0.0) >= 0:
        failures.append("selected pair does not actually relax the chosen cost")
    if delta.get(str(benefit), 0.0) <= 0:
        failures.append("selected pair does not gain on the chosen benefit")

    return {
        "thread_id": args.thread_id or f"selector-audit-{int(time.time())}",
        "mode": "selector_audit",
        "constraints": DEFAULT_CONSTRAINTS,
        "opportunity_counts": {
            "global_baseline": 1,
            "tuition_value_relax": 1,
            "major_geo_relax": 1,
        },
        "selected_pair": {
            "option_a": {
                "school_name": option_a.get("school_name"),
                "major_name": option_a.get("major_name"),
                "_opportunity_key": option_a.get("_opportunity_key"),
            },
            "option_b": {
                "school_name": option_b.get("school_name"),
                "major_name": option_b.get("major_name"),
                "_opportunity_key": option_b.get("_opportunity_key"),
            },
            "delta": delta,
            "cost": cost,
            "benefit": benefit,
        },
        "analysis": {
            "status": "failed" if failures else "ok",
            "failures": failures,
        },
    }


async def run_trace(args: argparse.Namespace) -> dict[str, Any]:
    from app.graphs.workflow import build_graph

    if args.offline_deterministic:
        os.environ["GAOKAOLLM_OFFLINE_DETERMINISTIC"] = "1"
    trace_id = args.thread_id or f"demo-trace-{int(time.time())}"
    preflight = await _preflight_snapshot(args)
    _log(args, "building graph")
    try:
        app = build_graph()
    except Exception as exc:
        return {
            "thread_id": trace_id,
            "query": args.query,
            "offline_deterministic": bool(args.offline_deterministic),
            "preflight": preflight,
            "rounds": [],
            "analysis": {
                "status": "failed",
                "failures": [f"graph build failed: {type(exc).__name__}: {exc}"],
            },
            "errors": [
                {
                    "turn": 0,
                    "error": str(exc)[:1000],
                    "error_type": type(exc).__name__,
                }
            ],
            "final_question_kind": None,
            "final_probe_plan": None,
            "final_recommendation_count": 0,
            "final_recommendation_bucket_counts": {},
            "final_recommendation_highlight_counts": {},
            "final_recommendation_matrix": {},
            "final_recommendation_highlights": {},
            "final_weights": None,
            "final_variance": None,
            "final_reply": "",
        }
    _log(args, "graph ready")
    config = {"configurable": {"thread_id": trace_id}}
    replies = args.reply or DEFAULT_REPLIES
    payload: Any = {"messages": [HumanMessage(content=args.query)]}
    rounds: list[dict[str, Any]] = []

    errors: list[dict[str, Any]] = []

    for turn in range(1, args.max_turns + 1):
        turn_started = time.perf_counter()
        _log(args, f"turn {turn} start")
        try:
            _log(args, f"turn {turn} entering stream")
            await _drain(
                app,
                payload,
                config,
                timeout_seconds=args.turn_timeout_seconds,
            )
            _log(args, f"turn {turn} stream drained")
        except asyncio.TimeoutError:
            _log(args, f"turn {turn} timeout")
            errors.append(
                {
                    "turn": turn,
                    "error": "timeout",
                    "error_type": "TimeoutError",
                    "timeout_seconds": args.turn_timeout_seconds,
                    "latency_seconds": round(time.perf_counter() - turn_started, 3),
                }
            )
            break
        except Exception as exc:
            _log(args, f"turn {turn} error: {type(exc).__name__}: {exc}")
            errors.append(
                {
                    "turn": turn,
                    "error": str(exc)[:1000],
                    "error_type": type(exc).__name__,
                    "latency_seconds": round(time.perf_counter() - turn_started, 3),
                }
            )
            break
        snapshot = app.get_state(config)
        _log(args, f"turn {turn} snapshot read")
        values = dict(getattr(snapshot, "values", {}) or {})
        interrupt_meta = _interrupt_payload(snapshot)
        question = str(interrupt_meta.get("text") or "")
        if not question:
            _log(args, f"turn {turn} no interrupt")
            break
        reply = replies[min(turn - 1, len(replies) - 1)]
        rounds.append(
            _round_record(
                turn,
                values,
                question,
                reply,
                interrupt_meta=interrupt_meta,
                turn_latency_seconds=round(time.perf_counter() - turn_started, 3),
            )
        )
        _log(args, f"turn {turn} interrupt captured")
        payload = Command(resume=reply)

    if errors:
        _log(args, "skip final state after error")
        final_values: dict[str, Any] = {}
    else:
        _log(args, "reading final state")
        final_values = dict(app.get_state(config).values or {})
    report = {
        "thread_id": trace_id,
        "query": args.query,
        "offline_deterministic": bool(args.offline_deterministic),
        "preflight": preflight,
        "rounds": rounds,
        "analysis": analyze_rounds(rounds),
        "errors": errors,
        "final_question_kind": final_values.get("latest_question_kind"),
        "final_probe_plan": final_values.get("probe_plan"),
        "final_recommendation_count": _final_recommendation_count(final_values),
        "final_recommendation_bucket_counts": _bucket_counts(
            final_values.get("final_recommendation_matrix")
        ),
        "final_recommendation_highlight_counts": _bucket_counts(
            final_values.get("final_recommendation_highlights")
        ),
        "final_recommendation_matrix": final_values.get("final_recommendation_matrix")
        or {},
        "final_recommendation_highlights": final_values.get(
            "final_recommendation_highlights"
        )
        or {},
        "final_weights": final_values.get("implicit_weights"),
        "final_variance": final_values.get("weight_variance"),
        "final_reply": _latest_ai_message_text(final_values),
    }
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run an automated frontend demo trace."
    )
    parser.add_argument("--query", default=DEFAULT_QUERY)
    parser.add_argument("--max-turns", type=int, default=5)
    parser.add_argument("--thread-id", default="")
    parser.add_argument("--reply", action="append", help="Simulated reply per turn.")
    parser.add_argument("--output", default="")
    parser.add_argument("--offline-deterministic", action="store_true")
    parser.add_argument("--turn-timeout-seconds", type=float, default=45.0)
    parser.add_argument("--db-query-timeout-seconds", type=float, default=8.0)
    parser.add_argument("--no-fail", action="store_true")
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument(
        "--mode",
        choices=("graph", "probe-audit", "selector-audit"),
        default="graph",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.mode == "selector-audit":
        report = asyncio.run(run_selector_audit(args))
    elif args.mode == "probe-audit":
        report = asyncio.run(run_probe_audit(args))
    else:
        report = asyncio.run(run_trace(args))
    output_path = (
        Path(args.output)
        if args.output
        else ROOT / "outputs" / "demo_trace" / f"{report['thread_id']}.json"
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    analysis = report["analysis"]
    if report.get("errors"):
        analysis = {
            **analysis,
            "status": "failed",
            "failures": [
                *analysis.get("failures", []),
                *[
                    f"turn {item.get('turn')}: {item.get('error')}"
                    for item in report.get("errors", [])
                ],
            ],
        }
        report["analysis"] = analysis
        output_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2, default=str),
            encoding="utf-8",
        )
    print(
        json.dumps(
            {"output": str(output_path), **analysis}, ensure_ascii=False, indent=2
        )
    )
    if analysis.get("status") != "ok" and not args.no_fail:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
