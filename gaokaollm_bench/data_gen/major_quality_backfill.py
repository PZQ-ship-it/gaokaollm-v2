"""Build normalized school-major quality profiles from imported raw signals."""

from __future__ import annotations

import argparse
import json
import os
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg


DEFAULT_DATABASE_URL = "postgresql://postgres@127.0.0.1:55432/gaokao_recommendation"
SCHEMA_SQL = Path("db/migrations/002_major_quality_profiles.sql")
MAJOR_NAME_KEYS = ("专业名称", "专业")
FEATURED_FLAGS = ("国家重点", "国家品牌", "省部重点", "校级优势", "国家特色")
RATING_SCORES = {
    "A+": 100,
    "A": 95,
    "A-": 90,
    "B+": 85,
    "B": 80,
    "B-": 75,
    "C+": 70,
    "C": 65,
    "C-": 60,
}


@dataclass(frozen=True)
class MajorRef:
    major_id: int
    name: str
    major_category: str | None
    discipline_category: str | None
    level: str | None


def clean_major_name(value: Any) -> str | None:
    """Normalize major names from source files for exact catalog matching."""

    if value is None:
        return None
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return None
    for suffix in ("专业", "(专业)", "（专业）"):
        if text.endswith(suffix):
            text = text[: -len(suffix)].strip()
    return text or None


def rating_score(value: Any) -> int | None:
    if value is None:
        return None
    text = str(value).strip().upper().replace(" ", "")
    return RATING_SCORES.get(text)


def quality_tier(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 80:
        return "B"
    if score >= 70:
        return "C"
    return "D"


def major_rank_score(rank: Any, rating: Any = None) -> float:
    try:
        rank_int = int(float(rank))
    except (TypeError, ValueError):
        rank_int = 999
    score = max(45.0, 106.0 - float(rank_int))
    grade = rating_score(rating)
    if grade is not None:
        score = max(score, float(grade))
    return min(100.0, score)


def discipline_score(rating: Any, confidence: float) -> float:
    grade = rating_score(rating)
    if grade is None:
        return 55.0 * confidence
    return round(float(grade) * confidence, 3)


def key_major_score(level: Any, description: Any = None) -> float:
    text = f"{level or ''} {description or ''}"
    if "国家" in text or "国家级" in text:
        return 88.0
    if "省" in text or "部" in text:
        return 76.0
    return 68.0


def featured_major_score(raw: dict[str, Any]) -> float:
    for key in ("国家重点", "国家品牌", "国家特色"):
        if str(raw.get(key) or "").strip() == "是":
            return 84.0
    for key in ("省部重点", "校级优势"):
        if str(raw.get(key) or "").strip() == "是":
            return 74.0
    return 66.0


def satisfaction_signal_score(score: Any) -> float | None:
    try:
        value = float(score)
    except (TypeError, ValueError):
        return None
    return round(min(80.0, max(50.0, 50.0 + (value - 3.0) * 15.0)), 3)


def evidence_label(
    *,
    source_type: str,
    rank: Any = None,
    rating: Any = None,
    level: Any = None,
    score: Any = None,
    vote_count: Any = None,
) -> str:
    if source_type == "major_ranking":
        return f"专业排名 {rank}, 评级 {rating}".strip()
    if source_type == "discipline_evaluation":
        return f"第四轮学科评估 {rating}".strip()
    if source_type == "featured_major":
        return "特色专业"
    if source_type == "key_major":
        return f"重点专业 {level}".strip()
    if source_type == "satisfaction":
        return f"专业满意度 {score}, 投票 {vote_count}".strip()
    return source_type


def _raw_major_name(raw: dict[str, Any]) -> str | None:
    for key in MAJOR_NAME_KEYS:
        major = clean_major_name(raw.get(key))
        if major:
            return major
    return None


def _load_schema(conn: psycopg.Connection[Any]) -> None:
    sql = SCHEMA_SQL.read_text(encoding="utf-8")
    with conn.cursor() as cur:
        cur.execute(sql)
    conn.commit()


def _load_majors(
    conn: psycopg.Connection[Any],
) -> tuple[dict[int, MajorRef], dict[str, int]]:
    refs: dict[int, MajorRef] = {}
    by_name: dict[str, int] = {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, major_category, discipline_category, level
            FROM majors
            WHERE name IS NOT NULL
            """
        )
        for (
            major_id,
            name,
            major_category,
            discipline_category,
            level,
        ) in cur.fetchall():
            ref = MajorRef(
                major_id=int(major_id),
                name=str(name),
                major_category=major_category,
                discipline_category=discipline_category,
                level=level,
            )
            refs[ref.major_id] = ref
            by_name.setdefault(ref.name, ref.major_id)
    return refs, by_name


def _build_discipline_mappings(
    conn: psycopg.Connection[Any],
    majors: dict[int, MajorRef],
) -> dict[str, list[tuple[MajorRef, str, float]]]:
    disciplines: dict[str, dict[str, Any]] = {}
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT discipline_name, source_file
            FROM school_major_strengths
            WHERE source_type = 'discipline_evaluation'
              AND discipline_name IS NOT NULL
            """
        )
        for discipline_name, source_file in cur.fetchall():
            disciplines[str(discipline_name)] = {"source_file": source_file}

    mapping_rows: list[tuple[Any, ...]] = []
    by_discipline: dict[str, list[tuple[MajorRef, str, float]]] = defaultdict(list)
    seen: set[tuple[str, int, str]] = set()
    for discipline_name, meta in disciplines.items():
        for ref in majors.values():
            candidates = [
                (ref.name, "exact_major_name", 1.0),
                (ref.major_category, "major_category", 0.85),
                (ref.discipline_category, "discipline_category", 0.65),
            ]
            for value, rule, confidence in candidates:
                if value != discipline_name:
                    continue
                key = (discipline_name, ref.major_id, rule)
                if key in seen:
                    continue
                seen.add(key)
                by_discipline[discipline_name].append((ref, rule, confidence))
                mapping_rows.append(
                    (
                        discipline_name,
                        ref.major_id,
                        ref.name,
                        rule,
                        Decimal(str(confidence)),
                        meta.get("source_file"),
                        json.dumps(
                            {"discipline_name": discipline_name}, ensure_ascii=False
                        ),
                    )
                )

    with conn.cursor() as cur:
        cur.execute("DELETE FROM discipline_major_mappings")
        cur.executemany(
            """
            INSERT INTO discipline_major_mappings (
                discipline_name, major_id, major_name, mapping_rule, confidence,
                source_file, raw
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
            ON CONFLICT (discipline_name, major_id, mapping_rule) DO UPDATE SET
                confidence = EXCLUDED.confidence,
                source_file = EXCLUDED.source_file,
                raw = EXCLUDED.raw
            """,
            mapping_rows,
        )
    conn.commit()
    return by_discipline


def _append_signal(
    rows: list[tuple[Any, ...]],
    *,
    sms_id: int,
    school_id: int | None,
    ref: MajorRef | None,
    source_type: str,
    discipline_name: str | None,
    rank: Any,
    rating: Any,
    level: Any,
    score: Any,
    vote_count: Any,
    signal_score: float | None,
    label: str,
    mapping_rule: str | None,
    source_file: str | None,
    raw: dict[str, Any],
) -> None:
    if school_id is None or ref is None or signal_score is None:
        return
    rows.append(
        (
            school_id,
            ref.major_id,
            ref.name,
            source_type,
            sms_id,
            discipline_name,
            int(float(rank)) if rank is not None else None,
            str(rating).strip() if rating is not None else None,
            str(level).strip() if level is not None else None,
            Decimal(str(score)) if score is not None else None,
            int(float(vote_count)) if vote_count is not None else None,
            Decimal(str(round(signal_score, 3))),
            label,
            mapping_rule,
            source_file,
            json.dumps(raw, ensure_ascii=False, default=str),
        )
    )


def _rebuild_signals(
    conn: psycopg.Connection[Any],
    majors: dict[int, MajorRef],
    majors_by_name: dict[str, int],
    discipline_mappings: dict[str, list[tuple[MajorRef, str, float]]],
) -> int:
    rows: list[tuple[Any, ...]] = []
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                id, school_id, major_id, discipline_name, source_type, rank,
                rating, level, score, vote_count, description, source_file, raw
            FROM school_major_strengths
            WHERE school_id IS NOT NULL
            """
        )
        for (
            sms_id,
            school_id,
            major_id,
            discipline_name,
            source_type,
            rank,
            rating,
            level,
            score,
            vote_count,
            description,
            source_file,
            raw,
        ) in cur.fetchall():
            raw = raw or {}
            source_type = str(source_type)
            ref: MajorRef | None = None
            if major_id is not None:
                ref = majors.get(int(major_id))
            if ref is None:
                major_name = _raw_major_name(raw)
                if major_name:
                    mapped_id = majors_by_name.get(major_name)
                    ref = majors.get(mapped_id) if mapped_id is not None else None

            if source_type == "major_ranking":
                _append_signal(
                    rows,
                    sms_id=int(sms_id),
                    school_id=int(school_id),
                    ref=ref,
                    source_type=source_type,
                    discipline_name=discipline_name,
                    rank=rank,
                    rating=rating,
                    level=level,
                    score=None,
                    vote_count=None,
                    signal_score=major_rank_score(rank, rating),
                    label=evidence_label(
                        source_type=source_type,
                        rank=rank,
                        rating=rating,
                    ),
                    mapping_rule="raw_major_name_suffix",
                    source_file=source_file,
                    raw=raw,
                )
            elif source_type == "discipline_evaluation":
                for mapped_ref, rule, confidence in discipline_mappings.get(
                    str(discipline_name or ""),
                    [],
                ):
                    _append_signal(
                        rows,
                        sms_id=int(sms_id),
                        school_id=int(school_id),
                        ref=mapped_ref,
                        source_type=source_type,
                        discipline_name=discipline_name,
                        rank=None,
                        rating=rating,
                        level=level,
                        score=None,
                        vote_count=None,
                        signal_score=discipline_score(rating, confidence),
                        label=evidence_label(source_type=source_type, rating=rating),
                        mapping_rule=rule,
                        source_file=source_file,
                        raw=raw,
                    )
            elif source_type == "featured_major":
                _append_signal(
                    rows,
                    sms_id=int(sms_id),
                    school_id=int(school_id),
                    ref=ref,
                    source_type=source_type,
                    discipline_name=discipline_name,
                    rank=None,
                    rating=rating,
                    level=level,
                    score=None,
                    vote_count=None,
                    signal_score=featured_major_score(raw),
                    label=evidence_label(source_type=source_type),
                    mapping_rule="major_id_or_raw_major_name",
                    source_file=source_file,
                    raw=raw,
                )
            elif source_type == "key_major":
                _append_signal(
                    rows,
                    sms_id=int(sms_id),
                    school_id=int(school_id),
                    ref=ref,
                    source_type=source_type,
                    discipline_name=discipline_name,
                    rank=None,
                    rating=rating,
                    level=level,
                    score=None,
                    vote_count=None,
                    signal_score=key_major_score(level, description),
                    label=evidence_label(source_type=source_type, level=level),
                    mapping_rule="major_id_or_raw_major_name",
                    source_file=source_file,
                    raw=raw,
                )
            elif source_type == "satisfaction":
                _append_signal(
                    rows,
                    sms_id=int(sms_id),
                    school_id=int(school_id),
                    ref=ref,
                    source_type=source_type,
                    discipline_name=discipline_name,
                    rank=None,
                    rating=rating,
                    level=level,
                    score=score,
                    vote_count=vote_count,
                    signal_score=satisfaction_signal_score(score),
                    label=evidence_label(
                        source_type=source_type,
                        score=score,
                        vote_count=vote_count,
                    ),
                    mapping_rule="major_id_or_raw_major_name",
                    source_file=source_file,
                    raw=raw,
                )

    with conn.cursor() as cur:
        cur.execute("DELETE FROM school_major_quality_signals")
        cur.executemany(
            """
            INSERT INTO school_major_quality_signals (
                school_id, major_id, major_name, source_type, source_record_id,
                discipline_name, rank, rating, level, score, vote_count,
                signal_score, evidence_label, mapping_rule, source_file, raw
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb
            )
            """,
            rows,
        )
    conn.commit()
    return len(rows)


def _rebuild_profiles(conn: psycopg.Connection[Any]) -> int:
    grouped: dict[tuple[int, int], list[dict[str, Any]]] = defaultdict(list)
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT
                school_id, major_id, major_name, source_type, rank, rating, level,
                score, vote_count, signal_score, evidence_label, mapping_rule,
                source_file
            FROM school_major_quality_signals
            ORDER BY school_id, major_id, signal_score DESC, source_type
            """
        )
        cols = [desc.name for desc in cur.description]
        for record in cur.fetchall():
            row = dict(zip(cols, record, strict=True))
            grouped[(int(row["school_id"]), int(row["major_id"]))].append(row)

    profile_rows: list[tuple[Any, ...]] = []
    for (school_id, major_id), signals in grouped.items():
        max_score = max(float(row["signal_score"]) for row in signals)
        has_key = any(row["source_type"] == "key_major" for row in signals)
        has_featured = any(row["source_type"] == "featured_major" for row in signals)
        best_major_rank = min(
            [
                int(row["rank"])
                for row in signals
                if row["source_type"] == "major_ranking" and row.get("rank") is not None
            ],
            default=None,
        )
        best_rating = None
        best_rating_score = -1
        for row in signals:
            grade = rating_score(row.get("rating"))
            if grade is not None and grade > best_rating_score:
                best_rating_score = grade
                best_rating = row.get("rating")
        satisfaction_rows = [
            row for row in signals if row["source_type"] == "satisfaction"
        ]
        satisfaction_score = (
            max(
                float(row["score"])
                for row in satisfaction_rows
                if row.get("score") is not None
            )
            if satisfaction_rows
            else None
        )
        vote_count = (
            sum(
                int(row["vote_count"])
                for row in satisfaction_rows
                if row.get("vote_count") is not None
            )
            or None
        )
        bonus = (5.0 if has_key else 0.0) + (4.0 if has_featured else 0.0)
        quality_score = min(100.0, round(max_score + bonus, 3))
        evidence_sources = [
            {
                "source_type": row["source_type"],
                "rank": row.get("rank"),
                "rating": row.get("rating"),
                "level": row.get("level"),
                "score": float(row["score"]) if row.get("score") is not None else None,
                "signal_score": float(row["signal_score"]),
                "evidence_label": row.get("evidence_label"),
                "mapping_rule": row.get("mapping_rule"),
                "source_file": row.get("source_file"),
            }
            for row in signals[:6]
        ]
        raw = {
            "signal_count": len(signals),
            "source_types": sorted({row["source_type"] for row in signals}),
        }
        profile_rows.append(
            (
                school_id,
                major_id,
                signals[0]["major_name"],
                Decimal(str(quality_score)),
                quality_tier(quality_score),
                best_major_rank,
                best_rating,
                has_key,
                has_featured,
                Decimal(str(satisfaction_score))
                if satisfaction_score is not None
                else None,
                vote_count,
                json.dumps(evidence_sources, ensure_ascii=False, default=str),
                json.dumps(raw, ensure_ascii=False, default=str),
            )
        )

    with conn.cursor() as cur:
        cur.execute("DELETE FROM school_major_quality_profiles")
        cur.executemany(
            """
            INSERT INTO school_major_quality_profiles (
                school_id, major_id, major_name, quality_score, quality_tier,
                best_major_rank, best_rating, has_key_major, has_featured_major,
                satisfaction_score, vote_count, evidence_sources, raw
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb
            )
            ON CONFLICT (school_id, major_id) DO UPDATE SET
                major_name = EXCLUDED.major_name,
                quality_score = EXCLUDED.quality_score,
                quality_tier = EXCLUDED.quality_tier,
                best_major_rank = EXCLUDED.best_major_rank,
                best_rating = EXCLUDED.best_rating,
                has_key_major = EXCLUDED.has_key_major,
                has_featured_major = EXCLUDED.has_featured_major,
                satisfaction_score = EXCLUDED.satisfaction_score,
                vote_count = EXCLUDED.vote_count,
                evidence_sources = EXCLUDED.evidence_sources,
                raw = EXCLUDED.raw
            """,
            profile_rows,
        )
    conn.commit()
    return len(profile_rows)


def rebuild_major_quality_profiles(
    database_url: str | None = None,
    *,
    ensure_schema: bool = True,
) -> dict[str, int]:
    conninfo = database_url or os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL
    with psycopg.connect(conninfo) as conn:
        if ensure_schema:
            _load_schema(conn)
        majors, majors_by_name = _load_majors(conn)
        discipline_mappings = _build_discipline_mappings(conn, majors)
        signal_count = _rebuild_signals(
            conn, majors, majors_by_name, discipline_mappings
        )
        profile_count = _rebuild_profiles(conn)
        mapping_count = sum(len(items) for items in discipline_mappings.values())
    return {
        "discipline_major_mappings": mapping_count,
        "school_major_quality_signals": signal_count,
        "school_major_quality_profiles": profile_count,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Rebuild school-major quality normalization tables."
    )
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
    )
    args = parser.parse_args()
    result = rebuild_major_quality_profiles(args.database_url)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
