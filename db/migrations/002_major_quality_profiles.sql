-- School-major quality normalization layer.
--
-- This migration keeps the existing school_major_strengths table intact and
-- builds reusable, auditable tables for major-quality negotiation experiments.

CREATE TABLE IF NOT EXISTS discipline_major_mappings (
  id bigserial PRIMARY KEY,
  discipline_name text NOT NULL,
  major_id bigint NOT NULL REFERENCES majors(id) ON DELETE CASCADE,
  major_name text,
  mapping_rule text NOT NULL,
  confidence numeric NOT NULL DEFAULT 0.8,
  source_file text,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT discipline_major_mappings_uk
    UNIQUE (discipline_name, major_id, mapping_rule)
);

CREATE TABLE IF NOT EXISTS school_major_quality_signals (
  id bigserial PRIMARY KEY,
  school_id bigint NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  major_id bigint NOT NULL REFERENCES majors(id) ON DELETE CASCADE,
  major_name text,
  source_type text NOT NULL,
  source_record_id bigint REFERENCES school_major_strengths(id) ON DELETE SET NULL,
  discipline_name text,
  rank integer,
  rating text,
  level text,
  score numeric,
  vote_count integer,
  signal_score numeric NOT NULL,
  evidence_label text,
  mapping_rule text,
  source_file text,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT school_major_quality_signals_source_type_ck
    CHECK (source_type IN (
      'major_ranking',
      'discipline_evaluation',
      'featured_major',
      'key_major',
      'satisfaction'
    ))
);

CREATE TABLE IF NOT EXISTS school_major_quality_profiles (
  id bigserial PRIMARY KEY,
  school_id bigint NOT NULL REFERENCES schools(id) ON DELETE CASCADE,
  major_id bigint NOT NULL REFERENCES majors(id) ON DELETE CASCADE,
  major_name text,
  quality_score numeric NOT NULL,
  quality_tier text NOT NULL,
  best_major_rank integer,
  best_rating text,
  has_key_major boolean NOT NULL DEFAULT false,
  has_featured_major boolean NOT NULL DEFAULT false,
  satisfaction_score numeric,
  vote_count integer,
  evidence_sources jsonb NOT NULL DEFAULT '[]'::jsonb,
  raw jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT school_major_quality_profiles_uk UNIQUE (school_id, major_id)
);

CREATE INDEX IF NOT EXISTS discipline_major_mappings_major_idx
ON discipline_major_mappings (major_id);

CREATE INDEX IF NOT EXISTS school_major_quality_signals_school_major_idx
ON school_major_quality_signals (school_id, major_id);

CREATE INDEX IF NOT EXISTS school_major_quality_signals_source_idx
ON school_major_quality_signals (source_type);

CREATE INDEX IF NOT EXISTS school_major_quality_profiles_major_score_idx
ON school_major_quality_profiles (major_id, quality_score DESC);

CREATE INDEX IF NOT EXISTS school_major_quality_profiles_school_idx
ON school_major_quality_profiles (school_id);

COMMENT ON TABLE discipline_major_mappings IS
  'Deterministic mapping from discipline-evaluation names to canonical majors.';
COMMENT ON TABLE school_major_quality_signals IS
  'Normalized school-major quality evidence from rankings, evaluations, key/featured majors, and satisfaction.';
COMMENT ON TABLE school_major_quality_profiles IS
  'Aggregated school-major quality profiles used by major_quality_relax.';
