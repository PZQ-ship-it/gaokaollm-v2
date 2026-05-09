CREATE TABLE schools (
    id integer PRIMARY KEY,
    name text NOT NULL,
    province text NOT NULL,
    city text,
    is_985 boolean NOT NULL DEFAULT false,
    is_211 boolean NOT NULL DEFAULT false,
    is_double_first_class boolean NOT NULL DEFAULT false,
    education_level text NOT NULL DEFAULT '本科',
    ranking integer
);

CREATE TABLE subject_requirements (
    raw_requirement text PRIMARY KEY,
    requirement_type text NOT NULL,
    normalized_subjects text[] NOT NULL DEFAULT '{}'
);

CREATE TABLE admission_scores (
    id integer PRIMARY KEY,
    year integer NOT NULL,
    school_id integer NOT NULL REFERENCES schools(id),
    major_id integer,
    major_code text,
    major_name_raw text NOT NULL,
    subject_requirement text,
    requirement_normalized text[],
    min_score integer,
    min_rank integer
);

CREATE TABLE admission_plans (
    id integer PRIMARY KEY,
    school_id integer NOT NULL REFERENCES schools(id),
    year integer NOT NULL,
    major_id integer,
    major_code text,
    major_name_raw text NOT NULL,
    tuition integer
);

INSERT INTO subject_requirements (raw_requirement, requirement_type, normalized_subjects)
VALUES
    ('不限', 'none', '{}'),
    ('物理、化学(2科必选)', 'all_required', ARRAY['物理','化学']),
    ('物理、化学、生物(3科必选)', 'all_required', ARRAY['物理','化学','生物']);

INSERT INTO schools
    (id, name, province, city, is_985, is_211, is_double_first_class, education_level, ranking)
VALUES
    (1, '丽水学院', '浙江', '丽水市', false, false, false, '本科', 500),
    (206, '东北农业大学', '黑龙江', '哈尔滨市', false, true, true, '本科', 120),
    (61, '西南交通大学', '四川', '成都市', false, true, true, '本科', 80),
    (133, '广西大学', '广西', '南宁市', false, true, true, '本科', 110),
    (282, '天津中医药大学', '天津', '静海区', false, false, true, '本科', 180);

INSERT INTO admission_scores
    (id, year, school_id, major_id, major_code, major_name_raw, subject_requirement, requirement_normalized, min_score, min_rank)
VALUES
    (1, 2025, 1, 1001, 'LS001', '临床医学', '物理、化学、生物(3科必选)', ARRAY['物理','化学','生物'], 542, 120000),
    (2, 2025, 206, 371, 'DBNY001', '动物科学', '不限', '{}', 541, 123189),
    (3, 2024, 61, 6101, 'XNJT001', '城市设计', '不限', '{}', 492, 178059),
    (4, 2024, 61, 6102, 'XNJT002', '建筑类', '不限', '{}', 492, 178059),
    (5, 2024, 133, 469, 'GX001', '公共事业管理', '不限', '{}', 542, 120100),
    (6, 2024, 282, 2821, 'TJTCM001', '医学技术类', '物理、化学(2科必选)', ARRAY['物理','化学'], 492, 178059);

INSERT INTO admission_plans
    (id, school_id, year, major_id, major_code, major_name_raw, tuition)
VALUES
    (1, 1, 2025, 1001, 'LS001', '临床医学', 6325),
    (2, 206, 2025, 371, 'DBNY001', '动物科学', 3000),
    (3, 61, 2024, 6101, 'XNJT001', '城市设计', 6600),
    (4, 61, 2024, 6102, 'XNJT002', '建筑类', 6600),
    (5, 133, 2024, 469, 'GX001', '公共事业管理', 5950),
    (6, 282, 2024, 2821, 'TJTCM001', '医学技术类', 5800);
