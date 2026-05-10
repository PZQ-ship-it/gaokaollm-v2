-- Normalized major-level employment outcome profiles for employment_outcome_relax.

CREATE TABLE IF NOT EXISTS major_employment_outcome_profiles (
  id bigserial PRIMARY KEY,
  major_id bigint NOT NULL REFERENCES majors(id) ON DELETE CASCADE,
  major_name text NOT NULL,
  employment_rank integer,
  employment_rank_desc text,
  top_city text,
  top_industry text,
  industry_distribution jsonb NOT NULL DEFAULT '{}'::jsonb,
  city_distribution jsonb NOT NULL DEFAULT '{}'::jsonb,
  job_distribution jsonb NOT NULL DEFAULT '{}'::jsonb,
  salary_distribution jsonb NOT NULL DEFAULT '{}'::jsonb,
  salary_history jsonb NOT NULL DEFAULT '{}'::jsonb,
  outcome_score numeric NOT NULL,
  outcome_tier text NOT NULL,
  evidence_sources jsonb NOT NULL DEFAULT '[]'::jsonb,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT major_employment_outcome_profiles_uk UNIQUE (major_id)
);

CREATE INDEX IF NOT EXISTS major_employment_outcome_profiles_score_idx
ON major_employment_outcome_profiles (outcome_score DESC, employment_rank ASC NULLS LAST);

CREATE INDEX IF NOT EXISTS major_employment_outcome_profiles_major_idx
ON major_employment_outcome_profiles (major_id);

COMMENT ON TABLE major_employment_outcome_profiles IS
  'Normalized major-level employment outcome evidence used by employment_outcome_relax.';
