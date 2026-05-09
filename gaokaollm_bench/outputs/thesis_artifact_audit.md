# Thesis Artifact Audit

- Created at: `2026-05-10T02:15:33`
- Experiments: `major_geo_v1, risk_band_v1`
- Overall: `PASS`

## Global Checks

| Check | Status | Detail |
|---|---|---|
| `required_global_docs_exist` | PASS | required README and thesis docs exist |
| `hidden_persona_leakage_boundary_documented` | PASS | docs state Agent does not read hidden persona fields |
| `recorded_pytest_result_present` | PASS | thesis docs record: 79 passed, 9 skipped, 1 warning |

## 论文叙事文档审计

| Check | Status | Detail |
|---|---|---|
| `core_docs_cover_dual_experiment_terms` | PASS | all thesis narrative docs mention major_geo/risk_band experiments and relaxation capabilities |
| `v1_v2_plan_positions_versions_correctly` | PASS | v1/v2 plan frames v1 as prototype and v2 as final contribution |
| `dynamic_relaxation_overview_matches_current_scope` | PASS | dynamic overview marks risk_band_relax implemented and keeps city/tuition/employment/strength as future work |
| `narrative_docs_keep_hidden_persona_boundary` | PASS | narrative docs state Agent does not read hidden persona fields |

## Experiment: `major_geo_v1`

- Experiment dir: `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1`
- Opportunity field: `major_geo_relax`
- Overall: `PASS`

### Checks

| Check | Status | Detail |
|---|---|---|
| `required_artifacts_exist` | PASS | experiment evidence, report, and summary artifacts exist |
| `app_pareto_metrics_match_summary_claim` | PASS | metrics match expected thesis claim |
| `hard_constraint_metrics_match_summary_claim` | PASS | metrics match expected thesis claim |
| `case_coverage_and_outcomes` | PASS | app rows=10, app success=9, app failure=1, baseline success=0, same case ids=True |
| `transcripts_exist` | PASS | all report transcript paths resolve |
| `successful_app_cases_have_major_geo_relax_evidence` | PASS | all successful app_pareto cases expose major_geo_relax or recommended_schools |
| `baseline_has_no_major_geo_relax` | PASS | hard_constraint transcripts do not expose major_geo_relax |
| `known_failure_case_documented` | PASS | real-db-set-浙江-569-009 is explicitly documented as the non-success case |

### Metrics

| Target | Cases | Success | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|
| `app_pareto` | 10 | 9 | 0.900 | 0.900 | 0.000 | 5.20 |
| `hard_constraint` | 10 | 0 | 0.000 | 0.000 | 0.000 | 7.00 |

### Case Coverage

| Case | app_pareto | App Turns | App Gain | App Halluc. | hard_constraint | Baseline Turns |
|---|---|---:|---:|---:|---|---:|
| `real-db-set-浙江-542-001` | true | 5 | 1 | 0.000 | false | 7 |
| `real-db-set-浙江-544-002` | true | 5 | 1 | 0.000 | false | 7 |
| `real-db-set-浙江-546-003` | true | 5 | 1 | 0.000 | false | 7 |
| `real-db-set-浙江-547-004` | true | 5 | 1 | 0.000 | false | 7 |
| `real-db-set-浙江-549-005` | true | 5 | 1 | 0.000 | false | 7 |
| `real-db-set-浙江-550-006` | true | 5 | 1 | 0.000 | false | 7 |
| `real-db-set-浙江-557-007` | true | 5 | 1 | 0.000 | false | 7 |
| `real-db-set-浙江-568-008` | true | 5 | 1 | 0.000 | false | 7 |
| `real-db-set-浙江-569-009` | false | 7 | 0 | 0.000 | false | 7 |
| `real-db-set-浙江-575-010` | true | 5 | 1 | 0.000 | false | 7 |

## Experiment: `risk_band_v1`

- Experiment dir: `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1`
- Opportunity field: `risk_band_relax`
- Overall: `PASS`

### Checks

| Check | Status | Detail |
|---|---|---|
| `required_artifacts_exist` | PASS | experiment evidence, report, and summary artifacts exist |
| `app_pareto_metrics_match_summary_claim` | PASS | metrics match expected thesis claim |
| `hard_constraint_metrics_match_summary_claim` | PASS | metrics match expected thesis claim |
| `case_coverage_and_outcomes` | PASS | app rows=10, app success=10, app failure=0, baseline success=0, same case ids=True |
| `transcripts_exist` | PASS | all report transcript paths resolve |
| `successful_app_cases_have_risk_band_relax_evidence` | PASS | all successful app_pareto cases expose risk_band_relax or recommended_schools |
| `successful_app_cases_have_min_risk_band_relax_candidates` | PASS | all successful app_pareto cases expose at least 3 risk_band_relax candidates |
| `baseline_has_no_risk_band_relax` | PASS | hard_constraint transcripts do not expose risk_band_relax |

### Metrics

| Target | Cases | Success | Elicitation Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|
| `app_pareto` | 10 | 10 | 1.000 | 3.000 | 0.000 | 5.00 |
| `hard_constraint` | 10 | 0 | 0.000 | 0.000 | 0.000 | 15.00 |

### Case Coverage

| Case | app_pareto | App Turns | App Gain | App Halluc. | hard_constraint | Baseline Turns |
|---|---|---:|---:|---:|---|---:|
| `real-db-set-浙江-592-001` | true | 5 | 3 | 0.000 | false | 15 |
| `real-db-set-浙江-593-002` | true | 5 | 3 | 0.000 | false | 15 |
| `real-db-set-浙江-594-003` | true | 5 | 3 | 0.000 | false | 15 |
| `real-db-set-浙江-595-004` | true | 5 | 3 | 0.000 | false | 15 |
| `real-db-set-浙江-601-005` | true | 5 | 3 | 0.000 | false | 15 |
| `real-db-set-浙江-602-006` | true | 5 | 3 | 0.000 | false | 15 |
| `real-db-set-浙江-603-007` | true | 5 | 3 | 0.000 | false | 15 |
| `real-db-set-浙江-604-008` | true | 5 | 3 | 0.000 | false | 15 |
| `real-db-set-浙江-605-009` | true | 5 | 3 | 0.000 | false | 15 |
| `real-db-set-浙江-606-010` | true | 5 | 3 | 0.000 | false | 15 |

## SHA256

| File | SHA256 |
|---|---|
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\reports\app_pareto.jsonl` | `7f4a92f93c27646933381ab70210f4094ed4b7a51f8d8b99cbde821733e06210` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\reports\hard_constraint.jsonl` | `7f483f56ddb4dcf5a914378fe067d5044afebe4740e7626ecc36e5854c3a1598` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\summary.json` | `4da3a647b2e5ac2ccd314c44feaa540d2a2739320452d1cf00133886ff432240` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\app_pareto\transcript_real-db-set-浙江-542-001.json` | `47f6b983014ea814d371f715d4783b1f70323e2dc58c1b137039666dbdc935a6` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\app_pareto\transcript_real-db-set-浙江-544-002.json` | `5bf18d155fcea3d3b2588a9f7695e939f2d092b5306955b1752fe30eb127fe6d` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\app_pareto\transcript_real-db-set-浙江-546-003.json` | `6985fd8aafb8017d97b41a3c5f650c9d7ce7165771849876793ddbf7f3572de3` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\app_pareto\transcript_real-db-set-浙江-547-004.json` | `0925441e995d9e3040e3ad125cd1c185af3e9c210e2a2f3b1cadf417bfe5e455` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\app_pareto\transcript_real-db-set-浙江-549-005.json` | `00257c8d33ca4770d1749bfcc33c6c6914187a0ed2911d211382bdc124a358b6` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\app_pareto\transcript_real-db-set-浙江-550-006.json` | `14ddfffc2610b978f87fcc54788cf52e860791d0847f25ec2a7f7bede7010208` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\app_pareto\transcript_real-db-set-浙江-557-007.json` | `ae999957e691fe4ea46712ad910401020b3f093c6206a5a0c90cccd7978129ad` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\app_pareto\transcript_real-db-set-浙江-568-008.json` | `3b08d82c644263709eb76ab2b858f7ec6fe5bfc4cd6689d4564e6bce76615d54` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\app_pareto\transcript_real-db-set-浙江-569-009.json` | `c0c21917314e3b9603df5161ac3e5b58fa5841c3b033123308650bd8740d85df` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\app_pareto\transcript_real-db-set-浙江-575-010.json` | `c2cda29316e0f2d56411cc731bbc9bec9ea46175d39fa954d7b3b1c9b9d7c6c7` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-542-001.json` | `f4c4497d27402695e131d7a902d5cc755cd4cffdf8c7e208cb2fa39a048d97c7` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-544-002.json` | `be89905bca1a66f2d52bb449befd6b5426f6910c3086c707ebb920498d29561b` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-546-003.json` | `e6c419dea177d4cb8d0095c7d2a0a55c42746dd00efa73ed8b4ae2799569010d` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-547-004.json` | `1485d838deec0262a3fb69c34d81dd3a3c5d076ee11c4d477b9cbed16a749ac4` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-549-005.json` | `8460ddcdaf6ac9dabf2c3f47544ccddbc2653828d86a27157ef105d1804d7933` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-550-006.json` | `a3eda3d31a90c420490a2b6bbaa7df5b2e68af68c876ce881e19766ee0a5c38c` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-557-007.json` | `0d53fec61c00d3817626875504e4a62b8ef9ba4970155d17baeb9bd7b8a8428f` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-568-008.json` | `1e43d488e31a17752efdacfe1ee973485e4504bd0c0fc58a9c9dac4fbb57d90e` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-569-009.json` | `807679cee5177accd2539e90db2147cbdfab7bb32998a6507024ae64cc70c796` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-575-010.json` | `02c447989804025d2d74fd1e886eadbc3cda7d5990fe92883effbb7106f71381` |
| `gaokaollm_bench\outputs\agent_benchmark_major_geo_v1_evidence.md` | `49eed89cc4c5ec5f1368c3e1f27acaa849cbd7e3e7224ce7371481e428631a60` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\reports\app_pareto.jsonl` | `b80aaf3cb0c9f2043b6aee693077eeed973110a777df04550a6ba95d58b2888b` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\reports\hard_constraint.jsonl` | `bc749e1fa68b8d8327437aff07ae2321a677d53656d2066f59d60e429f3407cc` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\summary.json` | `7ff1ea82b463bca21c6cec94798196713a743459a457182ea0be1a3a678976db` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\app_pareto\transcript_real-db-set-浙江-592-001.json` | `bfcd8e89c003fe7caea1ee196760783c96859f7562681ad0071bcd912157cc03` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\app_pareto\transcript_real-db-set-浙江-593-002.json` | `b02388af47330a202b9e5c7254c33acf888fbd3bf140d267b3fffb54086908a2` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\app_pareto\transcript_real-db-set-浙江-594-003.json` | `77cb3a3e7ec199845a63fefb6b82eece5017828c5e5606343cc039f8537c36cc` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\app_pareto\transcript_real-db-set-浙江-595-004.json` | `9e04fa7ad1eb9ce973bb3c4ee2bf6aeaa406a408c31f30a0dfcffce9354d4b2b` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\app_pareto\transcript_real-db-set-浙江-601-005.json` | `a51233614da0e0f22befc02ddf553ab918e5d8ecce29acc7179d2106de2ca422` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\app_pareto\transcript_real-db-set-浙江-602-006.json` | `c39bbe210549639df40cf6ef27c135e21a91098f2ce5c693ef33f20c84f7ab7f` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\app_pareto\transcript_real-db-set-浙江-603-007.json` | `964d4c0e065ee6f32d3be417134ce2a7341c3bee2dfc878986f235239ae01979` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\app_pareto\transcript_real-db-set-浙江-604-008.json` | `3925d37aedc6df9443c53195a621455bce8ac86b50737e4574bfc0f17b8cfba9` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\app_pareto\transcript_real-db-set-浙江-605-009.json` | `7c76f02f438c27ccfaa3df5c9db264c5149b2593a1060665d5a5a9fb1c185980` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\app_pareto\transcript_real-db-set-浙江-606-010.json` | `4fd7348bc49775b6c7a38f08fb71ae376ab80b7c574de174c87c38e7ce3c2295` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-592-001.json` | `fe5241ace3401beda0102a0aeff6171efc76e225ceedd19cad5ab1d4b1c91069` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-593-002.json` | `197293009d04320b2125b460390b1eac1398c1f03831415dcb13cd39500b45a8` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-594-003.json` | `7d59f9367be66bedb04ac3c4e66d17cd807fd62da0b00dd8c2b394af8392be7b` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-595-004.json` | `dcd4fd131e5d02b32d9367f50b2371b8dc38a65aa3bb290e4b06697628a666aa` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-601-005.json` | `72a813e6132a4f1ed6acba7f90bff71d1a416d1bf6b96fe01b9ec3055bc5e32a` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-602-006.json` | `e9052aaadcbfd1d4e0c014d9c0a2244526b4fb46e87a0afb6141f712b7610a4f` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-603-007.json` | `f8cddfbbde226ccc63c96160020e07739ecbc817ae24f7f069d9dbbfa6d37568` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-604-008.json` | `662f6c0e0641fe02f5e783bef2db0e6ca272032f4cea66e51721efc6463faa2b` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-605-009.json` | `5869ac2064cea7dab95a6e83d46e0ae18a52897fe0cf7dcedc3630ea78842de6` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1\transcripts\hard_constraint\transcript_real-db-set-浙江-606-010.json` | `444af5c120e1ed6961e620fe8add0a8d699ff23a1c9605ca1df2a17ed7b4d4ed` |
| `gaokaollm_bench\outputs\agent_benchmark_risk_band_v1_evidence.md` | `7346693bf69c052cb5ce8b33c26f92d37d8537262159420407f0d8445c812342` |
| `gaokaollm_bench\outputs\thesis_agent_benchmark_contribution.md` | `924a469da5a00ba21072ae563ed48a970549f96906449b9ba9a1ab3cd0682ab5` |
| `gaokaollm_bench\outputs\thesis_method_experiment_chapters.md` | `02449b18c5e86b71755dd4e73ff6a8a9ac03572139544dfba58e33c31a4b2254` |
| `gaokaollm_bench\outputs\thesis_v1_v2_integration_plan.md` | `d2a3a8812a7ca0f872ae9db404983a3f57e3aef63dbf19371cd481ac281e0b03` |
| `gaokaollm_bench\放宽与跃迁.md` | `c5c4ff65bfa9276ff3ad3f9e9bd47f0415e020cb2f6861fa13093b9030ad4a04` |
