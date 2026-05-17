from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import psycopg


ROOT = Path(__file__).resolve().parents[1]
DB_DSN = "host=127.0.0.1 port=55432 user=postgres dbname=gaokao_recommendation"


def norm_text(value: Any) -> str | None:
    if value is None or pd.isna(value):
        return None
    text = str(value).strip()
    if text in {"", "-", "--", "nan", "NaN", "None"}:
        return None
    return text


def norm_name(value: Any) -> str | None:
    text = norm_text(value)
    if not text:
        return None
    return re.sub(r"\s+", "", text)


def norm_major_name(value: Any) -> str | None:
    text = norm_name(value)
    if not text:
        return None
    candidates = [text]
    stripped = re.split(r"[（(]", text, maxsplit=1)[0].strip()
    if stripped and stripped != text:
        candidates.append(stripped)
    normalized = []
    for item in candidates:
        for suffix in ("专业",):
            if item.endswith(suffix):
                item = item[: -len(suffix)]
        if item and item not in normalized:
            normalized.append(item)
    return normalized[-1] if normalized else text


def resolve_major_id(major_map: dict[str, int], value: Any) -> int | None:
    keys = [norm_name(value), norm_major_name(value)]
    for key in keys:
        if key and key in major_map:
            return major_map[key]
    return None


def to_int(value: Any) -> int | None:
    text = norm_text(value)
    if not text:
        return None
    text = text.replace(",", "")
    match = re.search(r"-?\d+", text)
    return int(match.group(0)) if match else None


def extract_year(value: Any) -> int | None:
    text = norm_text(value)
    if not text:
        return None
    match = re.search(r"(20\d{2})", text)
    return int(match.group(1)) if match else None


def to_decimal(value: Any) -> Decimal | None:
    text = norm_text(value)
    if not text:
        return None
    text = text.replace(",", "")
    match = re.search(r"-?\d+(?:\.\d+)?", text)
    if not match:
        return None
    try:
        return Decimal(match.group(0))
    except InvalidOperation:
        return None


def clean_raw(row: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in row.items():
        if value is None or pd.isna(value):
            out[str(key)] = None
        elif isinstance(value, (int, float, str, bool)):
            out[str(key)] = value
        else:
            out[str(key)] = str(value)
    return out


def normalize_subjects(value: Any) -> list[str] | None:
    text = norm_text(value)
    if not text:
        return None
    if any(word in text for word in ["不限", "不提科目要求", "无"]):
        return []
    mapping = {
        "物": "物理",
        "物理": "物理",
        "化": "化学",
        "化学": "化学",
        "生": "生物",
        "生物": "生物",
        "政": "政治",
        "政治": "政治",
        "思想政治": "政治",
        "史": "历史",
        "历史": "历史",
        "地": "地理",
        "地理": "地理",
        "技": "技术",
        "技术": "技术",
    }
    found: list[str] = []
    for key, subject in mapping.items():
        if key in text and subject not in found:
            found.append(subject)
    return found or None


def file_by_name_contains(*parts: str) -> Path:
    candidates = []
    for path in ROOT.rglob("*"):
        if path.is_file() and all(part in path.name for part in parts):
            candidates.append(path)
    if not candidates:
        raise FileNotFoundError(parts)
    candidates.sort(key=lambda p: (len(p.parts), len(p.name), str(p)))
    return candidates[0]


def read_excel(path: Path, sheet_name: str | int = 0) -> pd.DataFrame:
    return pd.read_excel(path, sheet_name=sheet_name, dtype=object)


def rows(df: pd.DataFrame) -> Iterable[dict[str, Any]]:
    df = df.dropna(how="all")
    for row in df.to_dict("records"):
        yield row


def execute_many(
    conn: psycopg.Connection, sql: str, data: list[tuple[Any, ...]], label: str
) -> None:
    if not data:
        print(f"{label}: 0")
        return
    with conn.cursor() as cur:
        cur.executemany(sql, data)
    print(f"{label}: {len(data)}")


def reset_tables(conn: psycopg.Connection) -> None:
    tables = [
        "recommendation_results",
        "student_profiles",
        "knowledge_documents",
        "special_admission_programs",
        "major_employment_profiles",
        "school_major_strengths",
        "subject_requirements",
        "batch_lines",
        "score_rank_segments",
        "school_admission_scores",
        "admission_scores",
        "admission_plans",
        "school_codes",
        "majors",
        "schools",
    ]
    with conn.cursor() as cur:
        cur.execute("TRUNCATE TABLE " + ", ".join(tables) + " RESTART IDENTITY CASCADE")


def load_schools(conn: psycopg.Connection) -> None:
    path = file_by_name_contains("院校基础信息")
    df = read_excel(path)
    data = []
    for row in rows(df):
        name = norm_text(row.get("学校名称"))
        if not name:
            continue
        data.append(
            (
                name,
                norm_name(name),
                norm_text(row.get("新院校名称")),
                norm_text(row.get("所在省")),
                norm_text(row.get("城市")),
                norm_text(row.get("类型")),
                norm_text(row.get("隶属单位")),
                norm_text(row.get("公私性质")),
                norm_text(row.get("本科/专科")),
                norm_text(row.get("是否985")) is not None,
                norm_text(row.get("是否211")) is not None,
                norm_text(row.get("一流大学")) is not None,
                to_int(row.get("排名")),
                str(path.relative_to(ROOT)),
                json.dumps(clean_raw(row), ensure_ascii=False),
            )
        )
    sql = """
        INSERT INTO schools (
            name, normalized_name, old_name, province, city, school_type,
            affiliation, ownership, education_level, is_985, is_211,
            is_double_first_class, ranking, source_file, raw
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (normalized_name, province) DO UPDATE SET
            name = EXCLUDED.name,
            old_name = EXCLUDED.old_name,
            city = EXCLUDED.city,
            school_type = EXCLUDED.school_type,
            affiliation = EXCLUDED.affiliation,
            ownership = EXCLUDED.ownership,
            education_level = EXCLUDED.education_level,
            is_985 = EXCLUDED.is_985,
            is_211 = EXCLUDED.is_211,
            is_double_first_class = EXCLUDED.is_double_first_class,
            ranking = EXCLUDED.ranking,
            source_file = EXCLUDED.source_file,
            raw = EXCLUDED.raw
    """
    execute_many(conn, sql, data, "schools")


def load_majors(conn: psycopg.Connection) -> None:
    data = []
    for path in [
        file_by_name_contains("大学专业基础信息"),
        file_by_name_contains("专业基本介绍"),
        file_by_name_contains("2023本科专业目录"),
    ]:
        df = read_excel(path)
        for row in rows(df):
            name = norm_text(
                row.get("三级专业名称") or row.get("专业名称") or row.get("专业名")
            )
            if not name:
                continue
            code = norm_text(
                row.get("三级专业代码") or row.get("专业代码") or row.get("专业码")
            )
            data.append(
                (
                    code,
                    name,
                    norm_name(name),
                    norm_text(
                        row.get("一级专业名称")
                        or row.get("学科门类")
                        or row.get("门类")
                    ),
                    norm_text(row.get("二级专业名称") or row.get("专业类")),
                    norm_text(row.get("授予学位") or row.get("学位")),
                    norm_text(row.get("修业年限") or row.get("学制")),
                    norm_text(row.get("类型") or row.get("层次")),
                    norm_text(row.get("选考（学科）建议") or row.get("指引必选")),
                    norm_text(row.get("专业描述") or row.get("专业是什么")),
                    norm_text(row.get("专业学什么")),
                    norm_text(row.get("就业方向")),
                    str(path.relative_to(ROOT)),
                    json.dumps(clean_raw(row), ensure_ascii=False),
                )
            )
    sql = """
        INSERT INTO majors (
            major_code, name, normalized_name, discipline_category, major_category,
            degree, duration, level, subject_suggestion, intro, what_to_learn,
            career_direction, source_file, raw
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        ON CONFLICT (major_code, level) DO UPDATE SET
            name = EXCLUDED.name,
            normalized_name = EXCLUDED.normalized_name,
            discipline_category = COALESCE(EXCLUDED.discipline_category, majors.discipline_category),
            major_category = COALESCE(EXCLUDED.major_category, majors.major_category),
            degree = COALESCE(EXCLUDED.degree, majors.degree),
            duration = COALESCE(EXCLUDED.duration, majors.duration),
            subject_suggestion = COALESCE(EXCLUDED.subject_suggestion, majors.subject_suggestion),
            intro = COALESCE(EXCLUDED.intro, majors.intro),
            what_to_learn = COALESCE(EXCLUDED.what_to_learn, majors.what_to_learn),
            career_direction = COALESCE(EXCLUDED.career_direction, majors.career_direction),
            source_file = EXCLUDED.source_file,
            raw = EXCLUDED.raw
    """
    # Avoid NULL major_code conflict ambiguity by giving uncoded majors a synthetic code.
    fixed = []
    seen = set()
    for item in data:
        item = list(item)
        if not item[0]:
            item[0] = f"NAME:{item[2]}:{item[7] or ''}"
        key = (item[0], item[7])
        if key in seen:
            continue
        seen.add(key)
        fixed.append(tuple(item))
    execute_many(conn, sql, fixed, "majors")


def fetch_maps(conn: psycopg.Connection) -> tuple[dict[str, int], dict[str, int]]:
    school_map: dict[str, int] = {}
    major_map: dict[str, int] = {}
    with conn.cursor() as cur:
        cur.execute("SELECT id, normalized_name FROM schools")
        for school_id, name in cur.fetchall():
            if name:
                school_map[name] = school_id
        cur.execute("SELECT id, normalized_name FROM majors")
        for major_id, name in cur.fetchall():
            if name and name not in major_map:
                major_map[name] = major_id
    return school_map, major_map


def load_score_rank_segments(conn: psycopg.Connection) -> None:
    data = []
    for path in [
        file_by_name_contains("2017-2024", "一分一段"),
        file_by_name_contains("一分一段2025"),
    ]:
        xl = pd.ExcelFile(path)
        for sheet in xl.sheet_names:
            df = read_excel(path, sheet)
            for row in rows(df):
                province = norm_text(row.get("省份")) or sheet
                year = to_int(row.get("年份"))
                subject = norm_text(row.get("科目"))
                if not year or not subject:
                    continue
                data.append(
                    (
                        province,
                        year,
                        subject,
                        norm_text(row.get("层次")),
                        to_int(row.get("最小分数")),
                        to_int(row.get("最大分数")),
                        to_int(row.get("最高位次")),
                        to_int(row.get("最低位次")),
                        to_int(row.get("同分人数")),
                        str(path.relative_to(ROOT)),
                    )
                )
    sql = """
        INSERT INTO score_rank_segments (
            province, year, subject_type, level, score_min, score_max,
            rank_min, rank_max, same_score_count, source_file
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    execute_many(conn, sql, data, "score_rank_segments")


def load_batch_lines(conn: psycopg.Connection) -> None:
    path = file_by_name_contains("2021-2024", "批次线")
    df = read_excel(path)
    data = []
    for row in rows(df):
        province = norm_text(row.get("省市"))
        year = to_int(row.get("年份"))
        if not province or not year:
            continue
        data.append(
            (
                province,
                year,
                norm_text(row.get("批次/段")),
                norm_text(row.get("科目")),
                norm_text(row.get("批次类型")),
                to_decimal(row.get("控制分数线")),
                to_decimal(row.get("压分线")),
                norm_text(row.get("压线分区间")),
                norm_text(row.get("remark")),
                str(path.relative_to(ROOT)),
                json.dumps(clean_raw(row), ensure_ascii=False),
            )
        )
    sql = """
        INSERT INTO batch_lines (
            province, year, batch, subject_type, batch_type, control_score,
            pressure_score, score_range, remark, source_file, raw
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
    """
    execute_many(conn, sql, data, "batch_lines")


def load_school_scores(conn: psycopg.Connection, school_map: dict[str, int]) -> None:
    path = file_by_name_contains("院校分数")
    xl = pd.ExcelFile(path)
    data = []
    for sheet in xl.sheet_names:
        df = read_excel(path, sheet)
        for row in rows(df):
            year = to_int(row.get("年份")) or to_int(sheet)
            school = norm_text(row.get("学校") or row.get("院校名称"))
            if not year or not school:
                continue
            data.append(
                (
                    year,
                    "浙江",
                    norm_text(row.get("批次")),
                    norm_text(row.get("科目") or row.get("考生类别")),
                    school_map.get(norm_name(school) or ""),
                    norm_text(row.get("招生代码") or row.get("院校代码")),
                    school,
                    to_int(row.get("录取人数")),
                    to_decimal(row.get("最低分")),
                    to_int(row.get("最低分位次")),
                    to_decimal(row.get("平均分")),
                    to_decimal(row.get("最高分")),
                    to_decimal(row.get("最低分线差") or row.get("线差")),
                    str(path.relative_to(ROOT)),
                    json.dumps(clean_raw(row), ensure_ascii=False),
                )
            )
    sql = """
        INSERT INTO school_admission_scores (
            year, student_province, batch, subject_type, school_id, school_code,
            school_name_raw, enrolled_count, min_score, min_rank, avg_score,
            max_score, score_diff, source_file, raw
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
    """
    execute_many(conn, sql, data, "school_admission_scores")


def load_plans(
    conn: psycopg.Connection, school_map: dict[str, int], major_map: dict[str, int]
) -> None:
    plan_files = [
        file_by_name_contains("2025", "招生计划0621"),
        file_by_name_contains("2025", "招生计划0723"),
        file_by_name_contains("2024", "招生计划"),
        ROOT / "近三年报志愿数据" / "浙江-2022-招生计划.xlsx",
        ROOT / "近三年报志愿数据" / "Z浙江-2021计划.xlsx",
    ]
    data = []
    codes = []
    for path in plan_files:
        if not path.exists():
            continue
        xl = pd.ExcelFile(path)
        for sheet in xl.sheet_names:
            df = read_excel(path, sheet)
            for row in rows(df):
                year = to_int(row.get("年份")) or extract_year(path.name)
                school = norm_text(
                    row.get("院校名称") or row.get("学校名称") or row.get("学校")
                )
                major = norm_text(
                    row.get("专业名称") or row.get("专业") or row.get("专业方向")
                )
                if not year or not school or not major:
                    continue
                school_id = school_map.get(norm_name(school) or "")
                major_id = resolve_major_id(major_map, major)
                school_code = norm_text(
                    row.get("院校代码") or row.get("院校代号") or row.get("招生代码")
                )
                req = norm_text(
                    row.get("选科要求")
                    or row.get("选考科目")
                    or row.get("科目要求")
                    or row.get("报考要求")
                )
                data.append(
                    (
                        year,
                        norm_text(row.get("生源地") or row.get("省份")) or "浙江",
                        norm_text(row.get("批次")),
                        norm_text(row.get("批次详情") or row.get("类型")),
                        norm_text(row.get("科类")),
                        school_id,
                        school_code,
                        school,
                        major_id,
                        norm_text(row.get("专业代码") or row.get("专业代号")),
                        major,
                        norm_text(row.get("专业方向")),
                        norm_text(row.get("专业备注") or row.get("专业简注")),
                        norm_text(row.get("专业层次") or row.get("层次")),
                        norm_text(row.get("学制") or row.get("学年")),
                        to_decimal(row.get("学费")),
                        to_int(row.get("计划人数") or row.get("招生计划人数")),
                        req,
                        normalize_subjects(req),
                        norm_text(row.get("办学性质")),
                        str(path.relative_to(ROOT)),
                        sheet,
                        json.dumps(clean_raw(row), ensure_ascii=False),
                    )
                )
                if school_id and school_code:
                    codes.append(
                        (
                            school_id,
                            school_code,
                            "zhejiang_admission_code",
                            "浙江",
                            year,
                            str(path.relative_to(ROOT)),
                        )
                    )
    sql = """
        INSERT INTO admission_plans (
            year, student_province, batch, batch_detail, subject_type, school_id,
            school_code, school_name_raw, major_id, major_code, major_name_raw,
            major_direction, major_remark, major_level, education_system, tuition,
            plan_count, subject_requirement, requirement_normalized, ownership,
            source_file, source_sheet, raw
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
    """
    execute_many(conn, sql, data, "admission_plans")
    code_sql = """
        INSERT INTO school_codes (school_id, code, code_type, province, year, source_file)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (code, code_type, year, province) DO NOTHING
    """
    execute_many(conn, code_sql, list(dict.fromkeys(codes)), "school_codes")


def load_admission_scores(
    conn: psycopg.Connection, school_map: dict[str, int], major_map: dict[str, int]
) -> None:
    score_files = [
        file_by_name_contains("浙江25专业分"),
        file_by_name_contains("专业分数", "2024"),
        ROOT / "近三年报志愿数据" / "Z浙江-专业分数-2023(1).xlsx",
        ROOT / "浙江-2023-专业分数0531本专(1).xlsx",
        ROOT / "近三年报志愿数据" / "浙江-2022-专业分数.xlsx",
        ROOT / "近三年报志愿数据" / "浙江2021专业分数.xlsx",
    ]
    data = []
    for path in score_files:
        if not path.exists():
            continue
        xl = pd.ExcelFile(path)
        for sheet in xl.sheet_names:
            df = read_excel(path, sheet)
            for row in rows(df):
                year = to_int(row.get("年份") or row.get("招生年份")) or extract_year(
                    path.name
                )
                school = norm_text(
                    row.get("学校名称") or row.get("学校") or row.get("院校名称")
                )
                major = norm_text(row.get("专业名称") or row.get("专业"))
                if not year or not school or not major:
                    continue
                req = norm_text(
                    row.get("选科要求") or row.get("选考科目") or row.get("科目要求")
                )
                data.append(
                    (
                        year,
                        norm_text(row.get("生源地") or row.get("招生地区")) or "浙江",
                        norm_text(row.get("批次") or row.get("录取批次")),
                        norm_text(
                            row.get("科类") or row.get("科目") or row.get("考生类别")
                        ),
                        school_map.get(norm_name(school) or ""),
                        norm_text(row.get("院校代码") or row.get("招生代码")),
                        school,
                        resolve_major_id(major_map, major),
                        norm_text(row.get("专业代码") or row.get("专业组")),
                        major,
                        norm_text(row.get("专业备注") or row.get("备注")),
                        req,
                        normalize_subjects(req),
                        to_int(row.get("计划人数") or row.get("招生人数")),
                        to_int(row.get("录取人数") or row.get("实际招生人数")),
                        to_decimal(row.get("最低分")),
                        to_int(row.get("最低位次") or row.get("最低分位次")),
                        to_decimal(row.get("平均分")),
                        to_decimal(row.get("最高分")),
                        to_decimal(row.get("最低分线差") or row.get("线差")),
                        str(path.relative_to(ROOT)),
                        sheet,
                        json.dumps(clean_raw(row), ensure_ascii=False),
                    )
                )
    sql = """
        INSERT INTO admission_scores (
            year, student_province, batch, subject_type, school_id, school_code,
            school_name_raw, major_id, major_code, major_name_raw, major_remark,
            subject_requirement, requirement_normalized, plan_count, enrolled_count,
            min_score, min_rank, avg_score, max_score, score_diff, source_file,
            source_sheet, raw
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
    """
    execute_many(conn, sql, data, "admission_scores")


def load_supporting_data(
    conn: psycopg.Connection, school_map: dict[str, int], major_map: dict[str, int]
) -> None:
    employment_path = file_by_name_contains("专业就业信息")
    df = read_excel(employment_path)
    employment = []
    for row in rows(df):
        major = norm_text(row.get("学科三类"))
        if not major:
            continue
        employment.append(
            (
                resolve_major_id(major_map, major),
                major,
                norm_text(row.get("就业概况-名次")),
                norm_text(row.get("就业概况-名次-描述")),
                norm_text(row.get("就业最多地区")),
                norm_text(row.get("就业最多行业")),
                json.dumps(
                    clean_raw(
                        {
                            "items": row.get("就业行业分布"),
                            "ratios": row.get("就业行业分布比例"),
                        }
                    ),
                    ensure_ascii=False,
                ),
                json.dumps(
                    clean_raw(
                        {
                            "items": row.get("就业地区分布"),
                            "ratios": row.get("就业地区分布比例"),
                        }
                    ),
                    ensure_ascii=False,
                ),
                json.dumps(
                    clean_raw(
                        {"items": row.get("工资情况"), "ratios": row.get("工资比例")}
                    ),
                    ensure_ascii=False,
                ),
                str(employment_path.relative_to(ROOT)),
                json.dumps(clean_raw(row), ensure_ascii=False),
            )
        )
    execute_many(
        conn,
        """
        INSERT INTO major_employment_profiles (
            major_id, major_name_raw, employment_rank, employment_rank_desc, top_city,
            top_industry, industry_distribution, city_distribution, salary_distribution,
            source_file, raw
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s::jsonb)
        """,
        employment,
        "major_employment_profiles",
    )

    strength_rows = []
    for path, source_type in [
        (file_by_name_contains("专业排名信息"), "major_ranking"),
        (file_by_name_contains("专业满意度"), "satisfaction"),
        (file_by_name_contains("全国第四轮学科评估"), "discipline_evaluation"),
        (file_by_name_contains("特色专业"), "featured_major"),
        (file_by_name_contains("重点专业"), "key_major"),
    ]:
        df = read_excel(path)
        for row in rows(df):
            school = norm_text(
                row.get("学校名称")
                or row.get("院校名称")
                or row.get("院校")
                or row.get("学校")
            )
            major = norm_text(row.get("专业名称") or row.get("专业"))
            discipline = norm_text(row.get("专业类") or row.get("学科门类"))
            if not school:
                continue
            strength_rows.append(
                (
                    school_map.get(norm_name(school) or ""),
                    resolve_major_id(major_map, major) if major else None,
                    discipline,
                    source_type,
                    to_int(row.get("排名")),
                    norm_text(row.get("评级") or row.get("评估结果")),
                    norm_text(row.get("professionType") or row.get("层次")),
                    to_decimal(row.get("综合满意度")),
                    to_int(row.get("综合满意度投票人数")),
                    norm_text(
                        row.get("国家重点") or row.get("国家特色") or row.get("国家级")
                    ),
                    str(path.relative_to(ROOT)),
                    json.dumps(clean_raw(row), ensure_ascii=False),
                )
            )
    execute_many(
        conn,
        """
        INSERT INTO school_major_strengths (
            school_id, major_id, discipline_name, source_type, rank, rating,
            level, score, vote_count, description, source_file, raw
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        """,
        strength_rows,
        "school_major_strengths",
    )


def load_subject_requirements(conn: psycopg.Connection) -> None:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT DISTINCT subject_requirement
            FROM admission_plans
            WHERE subject_requirement IS NOT NULL
            UNION
            SELECT DISTINCT subject_requirement
            FROM admission_scores
            WHERE subject_requirement IS NOT NULL
            """
        )
        values = [row[0] for row in cur.fetchall()]
    data = []
    for raw in values:
        subjects = normalize_subjects(raw)
        if subjects == []:
            req_type = "none"
        elif subjects:
            req_type = (
                "all_required"
                if any(token in raw for token in ["+", "均须", "且", ",", "，"])
                else "any_required"
            )
        else:
            req_type = "unknown"
        data.append((raw, subjects, req_type, raw))
    execute_many(
        conn,
        """
        INSERT INTO subject_requirements (
            raw_requirement, normalized_subjects, requirement_type, description
        )
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (raw_requirement) DO UPDATE SET
            normalized_subjects = EXCLUDED.normalized_subjects,
            requirement_type = EXCLUDED.requirement_type,
            description = EXCLUDED.description
        """,
        data,
        "subject_requirements",
    )


def load_special_admission_programs(
    conn: psycopg.Connection, school_map: dict[str, int], major_map: dict[str, int]
) -> None:
    path = file_by_name_contains("强基", "军警")
    xl = pd.ExcelFile(path)
    data = []
    program_type_map = {
        "强基分数": "强基",
        "公安警校分数": "公安警校",
        "公费师范生数据": "公费师范",
        "军校面试分": "军校",
        "25三大专项数据": "三大专项",
    }
    for sheet in xl.sheet_names:
        df = read_excel(path, sheet)
        program_type = program_type_map.get(sheet, sheet)
        for row in rows(df):
            school = norm_text(row.get("院校名称") or row.get("学校名称"))
            major = norm_text(row.get("专业名称") or row.get("专业"))
            if not school:
                continue
            data.append(
                (
                    extract_year(path.name) or 2025,
                    norm_text(row.get("生源地") or row.get("省份")) or "浙江",
                    program_type,
                    school_map.get(norm_name(school) or ""),
                    school,
                    resolve_major_id(major_map, major) if major else None,
                    major,
                    norm_text(row.get("批次")),
                    norm_text(row.get("科类")),
                    norm_text(row.get("选科要求")),
                    norm_text(row.get("其他要求")),
                    to_int(row.get("计划人数")),
                    to_decimal(row.get("最低分")),
                    to_int(row.get("最低位次")),
                    to_decimal(row.get("录取分")),
                    to_decimal(row.get("面试分") or row.get("入围分")),
                    str(path.relative_to(ROOT)),
                    json.dumps(clean_raw(row), ensure_ascii=False),
                )
            )
    execute_many(
        conn,
        """
        INSERT INTO special_admission_programs (
            year, student_province, program_type, school_id, school_name_raw,
            major_id, major_name_raw, batch, subject_type, subject_requirement,
            other_requirement, plan_count, min_score, min_rank, admission_score,
            interview_score, source_file, raw
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
        """,
        data,
        "special_admission_programs",
    )


def load_knowledge_documents(
    conn: psycopg.Connection, school_map: dict[str, int], major_map: dict[str, int]
) -> None:
    docs = []
    for path, doc_type, title_col, content_cols in [
        (
            file_by_name_contains("院校基本简介"),
            "school_intro",
            "院校名称",
            ["院校名称", "省份", "城市", "隶属于", "国家重点学科", "硕士点", "博士点"],
        ),
        (
            file_by_name_contains("院校专业简介"),
            "school_intro",
            "院校名称",
            ["院校名称", "类别", "专业名称（*代表国家特色专业）"],
        ),
        (
            file_by_name_contains("专业基本介绍"),
            "major_intro",
            "专业名称",
            ["专业名称", "专业是什么", "专业学什么"],
        ),
    ]:
        df = read_excel(path)
        for row in rows(df):
            title = norm_text(row.get(title_col))
            if not title:
                continue
            parts = [norm_text(row.get(col)) for col in content_cols]
            content = "\n".join(part for part in parts if part)
            if not content:
                continue
            docs.append(
                (
                    doc_type,
                    title,
                    content,
                    school_map.get(norm_name(title) or "")
                    if doc_type == "school_intro"
                    else None,
                    major_map.get(norm_name(title) or "")
                    if doc_type == "major_intro"
                    else None,
                    str(path.relative_to(ROOT)),
                    json.dumps(clean_raw(row), ensure_ascii=False),
                )
            )
    execute_many(
        conn,
        """
        INSERT INTO knowledge_documents (
            doc_type, title, content, school_id, major_id, source_file, metadata
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
        """,
        docs,
        "knowledge_documents",
    )


def main() -> None:
    with psycopg.connect(DB_DSN, autocommit=False) as conn:
        print("reset tables")
        reset_tables(conn)
        load_schools(conn)
        load_majors(conn)
        school_map, major_map = fetch_maps(conn)
        print(f"school_map: {len(school_map)}, major_map: {len(major_map)}")
        load_score_rank_segments(conn)
        load_batch_lines(conn)
        load_school_scores(conn, school_map)
        load_plans(conn, school_map, major_map)
        load_admission_scores(conn, school_map, major_map)
        load_supporting_data(conn, school_map, major_map)
        load_subject_requirements(conn)
        load_special_admission_programs(conn, school_map, major_map)
        load_knowledge_documents(conn, school_map, major_map)
        conn.commit()


if __name__ == "__main__":
    main()
