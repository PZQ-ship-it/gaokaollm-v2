-- Gaokao recommendation system base schema.
-- Target database: PostgreSQL with pgvector.

BEGIN;

CREATE EXTENSION IF NOT EXISTS vector;

CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$;

CREATE TABLE IF NOT EXISTS schools (
  id bigserial PRIMARY KEY,
  name text NOT NULL,
  normalized_name text,
  old_name text,
  province text,
  city text,
  district text,
  school_type text,
  ownership text,
  education_level text,
  affiliation text,
  is_985 boolean,
  is_211 boolean,
  is_double_first_class boolean,
  is_strong_base boolean,
  ranking integer,
  master_count integer,
  doctor_count integer,
  national_key_subject_count integer,
  source_file text,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT schools_normalized_name_province_uk UNIQUE (normalized_name, province)
);

DROP TRIGGER IF EXISTS schools_set_updated_at ON schools;

CREATE TRIGGER schools_set_updated_at
BEFORE UPDATE ON schools
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS school_codes (
  id bigserial PRIMARY KEY,
  school_id bigint REFERENCES schools(id) ON DELETE CASCADE,
  code text NOT NULL,
  code_type text NOT NULL,
  province text,
  year integer,
  source_file text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT school_codes_code_type_year_uk UNIQUE (code, code_type, year, province)
);

CREATE TABLE IF NOT EXISTS majors (
  id bigserial PRIMARY KEY,
  major_code text,
  name text NOT NULL,
  normalized_name text,
  discipline_category text,
  major_category text,
  degree text,
  duration text,
  level text,
  subject_suggestion text,
  intro text,
  what_to_learn text,
  career_direction text,
  salary_text text,
  source_file text,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT majors_major_code_level_uk UNIQUE (major_code, level)
);

CREATE UNIQUE INDEX IF NOT EXISTS majors_normalized_name_level_uk
ON majors (normalized_name, level)
WHERE major_code IS NULL;

DROP TRIGGER IF EXISTS majors_set_updated_at ON majors;

CREATE TRIGGER majors_set_updated_at
BEFORE UPDATE ON majors
FOR EACH ROW
EXECUTE FUNCTION set_updated_at();

CREATE TABLE IF NOT EXISTS admission_plans (
  id bigserial PRIMARY KEY,
  year integer NOT NULL,
  student_province text NOT NULL DEFAULT '浙江',
  batch text,
  batch_detail text,
  subject_type text,
  school_id bigint REFERENCES schools(id) ON DELETE SET NULL,
  school_code text,
  school_name_raw text,
  major_id bigint REFERENCES majors(id) ON DELETE SET NULL,
  major_code text,
  major_name_raw text,
  major_direction text,
  major_remark text,
  major_level text,
  education_system text,
  tuition numeric,
  plan_count integer,
  subject_requirement text,
  requirement_normalized text[],
  ownership text,
  source_file text,
  source_sheet text,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS admission_scores (
  id bigserial PRIMARY KEY,
  year integer NOT NULL,
  student_province text NOT NULL DEFAULT '浙江',
  batch text,
  subject_type text,
  school_id bigint REFERENCES schools(id) ON DELETE SET NULL,
  school_code text,
  school_name_raw text,
  major_id bigint REFERENCES majors(id) ON DELETE SET NULL,
  major_code text,
  major_name_raw text,
  major_remark text,
  subject_requirement text,
  requirement_normalized text[],
  plan_count integer,
  enrolled_count integer,
  min_score numeric,
  min_rank integer,
  avg_score numeric,
  max_score numeric,
  score_diff numeric,
  source_file text,
  source_sheet text,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS school_admission_scores (
  id bigserial PRIMARY KEY,
  year integer NOT NULL,
  student_province text NOT NULL DEFAULT '浙江',
  batch text,
  subject_type text,
  school_id bigint REFERENCES schools(id) ON DELETE SET NULL,
  school_code text,
  school_name_raw text,
  enrolled_count integer,
  min_score numeric,
  min_rank integer,
  avg_score numeric,
  max_score numeric,
  score_diff numeric,
  batch_line numeric,
  source_file text,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS score_rank_segments (
  id bigserial PRIMARY KEY,
  province text NOT NULL,
  year integer NOT NULL,
  subject_type text NOT NULL,
  level text,
  score_min integer,
  score_max integer,
  rank_min integer,
  rank_max integer,
  same_score_count integer,
  source_file text,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS batch_lines (
  id bigserial PRIMARY KEY,
  province text NOT NULL,
  year integer NOT NULL,
  batch text,
  subject_type text,
  batch_type text,
  control_score numeric,
  pressure_score numeric,
  score_range text,
  remark text,
  source_file text,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS subject_requirements (
  id bigserial PRIMARY KEY,
  raw_requirement text NOT NULL,
  normalized_subjects text[],
  requirement_type text NOT NULL DEFAULT 'unknown',
  description text,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT subject_requirements_type_ck
    CHECK (requirement_type IN ('none', 'all_required', 'any_required', 'unknown')),
  CONSTRAINT subject_requirements_raw_uk UNIQUE (raw_requirement)
);

CREATE TABLE IF NOT EXISTS school_major_strengths (
  id bigserial PRIMARY KEY,
  school_id bigint REFERENCES schools(id) ON DELETE CASCADE,
  major_id bigint REFERENCES majors(id) ON DELETE SET NULL,
  discipline_name text,
  source_type text NOT NULL,
  rank integer,
  rating text,
  level text,
  score numeric,
  vote_count integer,
  description text,
  source_file text,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT school_major_strengths_source_type_ck
    CHECK (source_type IN (
      'major_ranking',
      'key_major',
      'featured_major',
      'discipline_evaluation',
      'satisfaction'
    ))
);

CREATE TABLE IF NOT EXISTS major_employment_profiles (
  id bigserial PRIMARY KEY,
  major_id bigint REFERENCES majors(id) ON DELETE SET NULL,
  major_name_raw text,
  employment_rank text,
  employment_rank_desc text,
  top_city text,
  top_industry text,
  industry_distribution jsonb,
  city_distribution jsonb,
  job_distribution jsonb,
  salary_distribution jsonb,
  salary_history jsonb,
  source_file text,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS special_admission_programs (
  id bigserial PRIMARY KEY,
  year integer,
  student_province text,
  program_type text NOT NULL,
  school_id bigint REFERENCES schools(id) ON DELETE SET NULL,
  school_name_raw text,
  major_id bigint REFERENCES majors(id) ON DELETE SET NULL,
  major_name_raw text,
  batch text,
  subject_type text,
  subject_requirement text,
  other_requirement text,
  plan_count integer,
  min_score numeric,
  min_rank integer,
  admission_score numeric,
  interview_score numeric,
  source_file text,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS student_profiles (
  id bigserial PRIMARY KEY,
  name text,
  province text NOT NULL DEFAULT '浙江',
  exam_year integer,
  score numeric,
  rank integer,
  selected_subjects text[],
  preferred_provinces text[],
  preferred_cities text[],
  preferred_school_types text[],
  preferred_majors text[],
  avoid_majors text[],
  tuition_max numeric,
  risk_preference text NOT NULL DEFAULT 'balanced',
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT student_profiles_risk_preference_ck
    CHECK (risk_preference IN ('conservative', 'balanced', 'aggressive'))
);

CREATE TABLE IF NOT EXISTS recommendation_results (
  id bigserial PRIMARY KEY,
  student_profile_id bigint REFERENCES student_profiles(id) ON DELETE CASCADE,
  plan_id bigint REFERENCES admission_plans(id) ON DELETE SET NULL,
  school_id bigint REFERENCES schools(id) ON DELETE SET NULL,
  major_id bigint REFERENCES majors(id) ON DELETE SET NULL,
  risk_level text,
  probability_score numeric,
  rank_gap integer,
  score_gap numeric,
  fit_score numeric,
  explanation text,
  evidence jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT recommendation_results_risk_level_ck
    CHECK (risk_level IS NULL OR risk_level IN ('冲', '稳', '保', '垫'))
);

CREATE TABLE IF NOT EXISTS knowledge_documents (
  id bigserial PRIMARY KEY,
  doc_type text NOT NULL,
  title text,
  content text NOT NULL,
  school_id bigint REFERENCES schools(id) ON DELETE SET NULL,
  major_id bigint REFERENCES majors(id) ON DELETE SET NULL,
  year integer,
  source_file text,
  source_sheet text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  embedding vector(1536),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT knowledge_documents_doc_type_ck
    CHECK (doc_type IN (
      'school_intro',
      'major_intro',
      'admission_rule',
      'career_info',
      'term_explanation',
      'special_program',
      'other'
    ))
);

CREATE INDEX IF NOT EXISTS school_codes_code_type_year_idx
ON school_codes (code, code_type, year);

CREATE INDEX IF NOT EXISTS school_codes_school_id_idx
ON school_codes (school_id);

CREATE INDEX IF NOT EXISTS schools_name_idx
ON schools (name);

CREATE INDEX IF NOT EXISTS majors_name_idx
ON majors (name);

CREATE INDEX IF NOT EXISTS admission_plans_year_province_batch_idx
ON admission_plans (year, student_province, batch);

CREATE INDEX IF NOT EXISTS admission_plans_school_year_idx
ON admission_plans (school_id, year);

CREATE INDEX IF NOT EXISTS admission_plans_major_year_idx
ON admission_plans (major_id, year);

CREATE INDEX IF NOT EXISTS admission_plans_requirement_gin_idx
ON admission_plans USING gin (requirement_normalized);

CREATE INDEX IF NOT EXISTS admission_scores_year_province_rank_idx
ON admission_scores (year, student_province, min_rank);

CREATE INDEX IF NOT EXISTS admission_scores_school_year_idx
ON admission_scores (year, school_id);

CREATE INDEX IF NOT EXISTS admission_scores_major_year_idx
ON admission_scores (year, major_id);

CREATE INDEX IF NOT EXISTS admission_scores_school_code_major_code_year_idx
ON admission_scores (school_code, major_code, year);

CREATE INDEX IF NOT EXISTS admission_scores_requirement_gin_idx
ON admission_scores USING gin (requirement_normalized);

CREATE INDEX IF NOT EXISTS school_admission_scores_year_province_rank_idx
ON school_admission_scores (year, student_province, min_rank);

CREATE INDEX IF NOT EXISTS school_admission_scores_school_year_idx
ON school_admission_scores (school_id, year);

CREATE INDEX IF NOT EXISTS score_rank_segments_score_idx
ON score_rank_segments (province, year, subject_type, score_min, score_max);

CREATE INDEX IF NOT EXISTS score_rank_segments_rank_idx
ON score_rank_segments (province, year, subject_type, rank_min, rank_max);

CREATE INDEX IF NOT EXISTS batch_lines_lookup_idx
ON batch_lines (province, year, subject_type, batch);

CREATE INDEX IF NOT EXISTS subject_requirements_subjects_gin_idx
ON subject_requirements USING gin (normalized_subjects);

CREATE INDEX IF NOT EXISTS school_major_strengths_school_major_idx
ON school_major_strengths (school_id, major_id);

CREATE INDEX IF NOT EXISTS school_major_strengths_source_rating_idx
ON school_major_strengths (source_type, rating);

CREATE INDEX IF NOT EXISTS school_major_strengths_major_rank_idx
ON school_major_strengths (major_id, rank);

CREATE INDEX IF NOT EXISTS major_employment_profiles_major_id_idx
ON major_employment_profiles (major_id);

CREATE INDEX IF NOT EXISTS special_admission_programs_program_year_idx
ON special_admission_programs (program_type, year);

CREATE INDEX IF NOT EXISTS special_admission_programs_school_idx
ON special_admission_programs (school_id);

CREATE INDEX IF NOT EXISTS student_profiles_exam_year_province_idx
ON student_profiles (exam_year, province);

CREATE INDEX IF NOT EXISTS recommendation_results_student_created_idx
ON recommendation_results (student_profile_id, created_at DESC);

CREATE INDEX IF NOT EXISTS knowledge_documents_doc_type_idx
ON knowledge_documents (doc_type);

CREATE INDEX IF NOT EXISTS knowledge_documents_school_id_idx
ON knowledge_documents (school_id);

CREATE INDEX IF NOT EXISTS knowledge_documents_major_id_idx
ON knowledge_documents (major_id);

CREATE INDEX IF NOT EXISTS knowledge_documents_embedding_hnsw_idx
ON knowledge_documents
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

COMMENT ON TABLE schools IS 'Canonical school dimension table.';
COMMENT ON TABLE school_codes IS 'School code mapping across admission, MOE, source files, and years.';
COMMENT ON TABLE majors IS 'Canonical major dimension table.';
COMMENT ON TABLE admission_plans IS 'Yearly Zhejiang admission plan facts, one row per school-major-batch plan.';
COMMENT ON TABLE admission_scores IS 'Major-level admission score and rank facts.';
COMMENT ON TABLE school_admission_scores IS 'School-level admission score and rank facts.';
COMMENT ON TABLE score_rank_segments IS 'Score-to-rank segment table, also known as one-score-one-rank.';
COMMENT ON TABLE batch_lines IS 'Batch control score lines.';
COMMENT ON TABLE subject_requirements IS 'Normalized elective subject requirements.';
COMMENT ON TABLE school_major_strengths IS 'School-major quality signals from rankings, key majors, evaluations, and satisfaction.';
COMMENT ON TABLE major_employment_profiles IS 'Major employment, salary, industry, city, and career profiles.';
COMMENT ON TABLE special_admission_programs IS 'Strong base, police/military, tuition-free teacher, and special program admissions.';
COMMENT ON TABLE student_profiles IS 'Student input profile for recommendation runs.';
COMMENT ON TABLE recommendation_results IS 'Persisted recommendation candidates and explanations.';
COMMENT ON TABLE knowledge_documents IS 'RAG and semantic explanation documents with pgvector embeddings.';

COMMIT;
