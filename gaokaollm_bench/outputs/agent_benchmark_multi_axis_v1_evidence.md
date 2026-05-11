# multi_axis_v1 ????????????????

???? `multi_axis_v1` ??? summary ????????????? persona?reports?summary ? transcripts??????????????????? LLM?

## 1. ?????????

- ???Benchmark ???? / ????????????? `major_geo_v1 + risk_band_v1`??????????????
- Persona?`gaokaollm_bench/sample_data/iceberg_personas_multi_axis_real_db_30.json`?
- ?????`gaokaollm_bench/outputs/agent_benchmark_multi_axis_v1/`?
- Summary?`gaokaollm_bench/outputs/agent_benchmark_multi_axis_v1_summary.md` ? `summary.json`?
- ?????

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m gaokaollm_bench.tests.manual.agent_benchmark_run --personas gaokaollm_bench/sample_data/iceberg_personas_multi_axis_real_db_30.json --targets app_pareto hard_constraint --max-turns 6 --limit 30 --output-dir gaokaollm_bench/outputs/agent_benchmark_multi_axis_v1 --paper-summary gaokaollm_bench/outputs/agent_benchmark_multi_axis_v1_summary.md --offline-deterministic
```

`multi_axis` persona ? hidden fields ?? `relaxation_axes` ? `axis_flexibilities` ???? required axes??????? simulator/evaluator ????? Agent ??? `implicit_flexibilities`?`volunteer_set` ? `axis_flexibilities`?????????????? PostgreSQL / ??????????

## 2. ??????

| Target | Cases | Completed | Failed | Success | Mean Pareto Gain | Mean Hallucination | Avg Turns |
|---|---:|---:|---:|---:|---:|---:|---:|
| `app_pareto` | 30 | 30 | 0 | 0.533 | 1.133 | 0.029 | 7.67 |
| `hard_constraint` | 30 | 30 | 0 | 0.000 | 0.000 | 0.000 | 13.00 |

???????? `app_pareto` ???? `hard_constraint`???????30 ? case ??? 16 ???????? `major_geo_risk`?????????????????/????????? `chong/wen/bao` ????????????????? benchmark ??????????????

## 3. Profile ?????

| Profile | Required axes | Cases | App success | Axis success summary |
|---|---|---:|---:|---|
| `major_geo_risk` | major_geo + risk_band | 10 | 1 | `major_geo` 10/10; `risk_band` 1/10 |
| `quality_tuition` | major_quality + tuition_value | 10 | 5 | `major_quality` 10/10; `tuition_value` 5/10 |
| `employment_region` | employment_outcome + region_tree | 10 | 10 | `employment_outcome` 10/10; `region_tree` 10/10 |

## 4. ?????

| Case | Profile | Required axes | App success | Baseline success | Turns(app/base) | Hallucination(app/base) | Pareto gain | Axis successes |
|---|---|---|---:|---:|---:|---:|---:|---|
| `multi-axis-major_geo_risk-浙江-592-001` | `major_geo_risk` | major_geo, risk_band | N | N | 13/13 | 0.000/0.000 | 0 | major_geo=Y, risk_band=N |
| `multi-axis-major_geo_risk-浙江-593-002` | `major_geo_risk` | major_geo, risk_band | N | N | 13/13 | 0.250/0.000 | 0 | major_geo=Y, risk_band=N |
| `multi-axis-major_geo_risk-浙江-594-003` | `major_geo_risk` | major_geo, risk_band | N | N | 13/13 | 0.250/0.000 | 0 | major_geo=Y, risk_band=N |
| `multi-axis-major_geo_risk-浙江-595-004` | `major_geo_risk` | major_geo, risk_band | N | N | 13/13 | 0.250/0.000 | 0 | major_geo=Y, risk_band=N |
| `multi-axis-major_geo_risk-浙江-601-005` | `major_geo_risk` | major_geo, risk_band | N | N | 13/13 | 0.000/0.000 | 0 | major_geo=Y, risk_band=N |
| `multi-axis-major_geo_risk-浙江-602-006` | `major_geo_risk` | major_geo, risk_band | N | N | 13/13 | 0.000/0.000 | 0 | major_geo=Y, risk_band=N |
| `multi-axis-major_geo_risk-浙江-603-007` | `major_geo_risk` | major_geo, risk_band | N | N | 13/13 | 0.000/0.000 | 0 | major_geo=Y, risk_band=N |
| `multi-axis-major_geo_risk-浙江-604-008` | `major_geo_risk` | major_geo, risk_band | N | N | 13/13 | 0.000/0.000 | 0 | major_geo=Y, risk_band=N |
| `multi-axis-major_geo_risk-浙江-605-009` | `major_geo_risk` | major_geo, risk_band | Y | N | 3/13 | 0.125/0.000 | 4 | major_geo=Y, risk_band=Y |
| `multi-axis-major_geo_risk-浙江-610-010` | `major_geo_risk` | major_geo, risk_band | N | N | 13/13 | 0.000/0.000 | 0 | major_geo=Y, risk_band=N |
| `multi-axis-quality_tuition-浙江-600-011` | `quality_tuition` | major_quality, tuition_value | N | N | 13/13 | 0.000/0.000 | 0 | major_quality=Y, tuition_value=N |
| `multi-axis-quality_tuition-浙江-601-012` | `quality_tuition` | major_quality, tuition_value | N | N | 13/13 | 0.000/0.000 | 0 | major_quality=Y, tuition_value=N |
| `multi-axis-quality_tuition-浙江-602-013` | `quality_tuition` | major_quality, tuition_value | N | N | 13/13 | 0.000/0.000 | 0 | major_quality=Y, tuition_value=N |
| `multi-axis-quality_tuition-浙江-603-014` | `quality_tuition` | major_quality, tuition_value | Y | N | 3/13 | 0.000/0.000 | 2 | major_quality=Y, tuition_value=Y |
| `multi-axis-quality_tuition-浙江-604-015` | `quality_tuition` | major_quality, tuition_value | Y | N | 3/13 | 0.000/0.000 | 2 | major_quality=Y, tuition_value=Y |
| `multi-axis-quality_tuition-浙江-605-016` | `quality_tuition` | major_quality, tuition_value | Y | N | 3/13 | 0.000/0.000 | 2 | major_quality=Y, tuition_value=Y |
| `multi-axis-quality_tuition-浙江-606-017` | `quality_tuition` | major_quality, tuition_value | Y | N | 3/13 | 0.000/0.000 | 2 | major_quality=Y, tuition_value=Y |
| `multi-axis-quality_tuition-浙江-607-018` | `quality_tuition` | major_quality, tuition_value | Y | N | 3/13 | 0.000/0.000 | 2 | major_quality=Y, tuition_value=Y |
| `multi-axis-quality_tuition-浙江-608-019` | `quality_tuition` | major_quality, tuition_value | N | N | 13/13 | 0.000/0.000 | 0 | major_quality=Y, tuition_value=N |
| `multi-axis-quality_tuition-浙江-609-020` | `quality_tuition` | major_quality, tuition_value | N | N | 13/13 | 0.000/0.000 | 0 | major_quality=Y, tuition_value=N |
| `multi-axis-employment_region-浙江-610-021` | `employment_region` | employment_outcome, region_tree | Y | N | 3/13 | 0.000/0.000 | 2 | employment_outcome=Y, region_tree=Y |
| `multi-axis-employment_region-浙江-612-022` | `employment_region` | employment_outcome, region_tree | Y | N | 3/13 | 0.000/0.000 | 2 | employment_outcome=Y, region_tree=Y |
| `multi-axis-employment_region-浙江-614-023` | `employment_region` | employment_outcome, region_tree | Y | N | 3/13 | 0.000/0.000 | 2 | employment_outcome=Y, region_tree=Y |
| `multi-axis-employment_region-浙江-616-024` | `employment_region` | employment_outcome, region_tree | Y | N | 3/13 | 0.000/0.000 | 2 | employment_outcome=Y, region_tree=Y |
| `multi-axis-employment_region-浙江-618-025` | `employment_region` | employment_outcome, region_tree | Y | N | 3/13 | 0.000/0.000 | 2 | employment_outcome=Y, region_tree=Y |
| `multi-axis-employment_region-浙江-620-026` | `employment_region` | employment_outcome, region_tree | Y | N | 3/13 | 0.000/0.000 | 2 | employment_outcome=Y, region_tree=Y |
| `multi-axis-employment_region-浙江-622-027` | `employment_region` | employment_outcome, region_tree | Y | N | 3/13 | 0.000/0.000 | 2 | employment_outcome=Y, region_tree=Y |
| `multi-axis-employment_region-浙江-624-028` | `employment_region` | employment_outcome, region_tree | Y | N | 3/13 | 0.000/0.000 | 2 | employment_outcome=Y, region_tree=Y |
| `multi-axis-employment_region-浙江-626-029` | `employment_region` | employment_outcome, region_tree | Y | N | 3/13 | 0.000/0.000 | 2 | employment_outcome=Y, region_tree=Y |
| `multi-axis-employment_region-浙江-628-030` | `employment_region` | employment_outcome, region_tree | Y | N | 3/13 | 0.000/0.000 | 2 | employment_outcome=Y, region_tree=Y |

## 5. ????????

?? case ???? `app_pareto` transcript ?????????????????????????????????? deterministic judge ?????????

### multi-axis-major_geo_risk-浙江-592-001

- Profile?`major_geo_risk`?required axes?`major_geo, risk_band`?
- ???app success=N?pareto_gain=0?axis_successes={"major_geo": true, "risk_band": false}?axis_pareto_gains={"major_geo": 1, "risk_band": 0}?
- `major_geo_relax` 西北农林科技大学?陕西/杨凌示范区?资源环境科学?min_score=592?min_rank=61052?tier=4?ranking=57?stage=5?strategy=any_major
- risk_band: transcript ??? `risk_band_relax` ??

### multi-axis-major_geo_risk-浙江-593-002

- Profile?`major_geo_risk`?required axes?`major_geo, risk_band`?
- ???app success=N?pareto_gain=0?axis_successes={"major_geo": true, "risk_band": false}?axis_pareto_gains={"major_geo": 1, "risk_band": 0}?
- `major_geo_relax` 西北农林科技大学?陕西/杨凌示范区?资源环境科学?min_score=592?min_rank=61052?tier=4?ranking=57?stage=5?strategy=any_major
- risk_band: transcript ??? `risk_band_relax` ??

### multi-axis-major_geo_risk-浙江-594-003

- Profile?`major_geo_risk`?required axes?`major_geo, risk_band`?
- ???app success=N?pareto_gain=0?axis_successes={"major_geo": true, "risk_band": false}?axis_pareto_gains={"major_geo": 1, "risk_band": 0}?
- `major_geo_relax` 西北农林科技大学?陕西/杨凌示范区?资源环境科学?min_score=592?min_rank=61052?tier=4?ranking=57?stage=5?strategy=any_major
- risk_band: transcript ??? `risk_band_relax` ??

### multi-axis-major_geo_risk-浙江-595-004

- Profile?`major_geo_risk`?required axes?`major_geo, risk_band`?
- ???app success=N?pareto_gain=0?axis_successes={"major_geo": true, "risk_band": false}?axis_pareto_gains={"major_geo": 1, "risk_band": 0}?
- `major_geo_relax` 西北农林科技大学?陕西/杨凌示范区?资源环境科学?min_score=592?min_rank=61052?tier=4?ranking=57?stage=5?strategy=any_major
- risk_band: transcript ??? `risk_band_relax` ??

### multi-axis-major_geo_risk-浙江-601-005

- Profile?`major_geo_risk`?required axes?`major_geo, risk_band`?
- ???app success=N?pareto_gain=0?axis_successes={"major_geo": true, "risk_band": false}?axis_pareto_gains={"major_geo": 1, "risk_band": 0}?
- `major_geo_relax` 中国矿业大学?江苏/徐州?土木工程?min_score=599?min_rank=52740?tier=4?ranking=53?stage=5?strategy=any_major
- risk_band: transcript ??? `risk_band_relax` ??

### multi-axis-major_geo_risk-浙江-602-006

- Profile?`major_geo_risk`?required axes?`major_geo, risk_band`?
- ???app success=N?pareto_gain=0?axis_successes={"major_geo": true, "risk_band": false}?axis_pareto_gains={"major_geo": 1, "risk_band": 0}?
- `major_geo_relax` 中国矿业大学?江苏/徐州?土木工程?min_score=599?min_rank=52740?tier=4?ranking=53?stage=5?strategy=any_major
- risk_band: transcript ??? `risk_band_relax` ??

### multi-axis-major_geo_risk-浙江-603-007

- Profile?`major_geo_risk`?required axes?`major_geo, risk_band`?
- ???app success=N?pareto_gain=0?axis_successes={"major_geo": true, "risk_band": false}?axis_pareto_gains={"major_geo": 1, "risk_band": 0}?
- `major_geo_relax` 中国矿业大学?江苏/徐州?土木工程?min_score=599?min_rank=52740?tier=4?ranking=53?stage=5?strategy=any_major
- risk_band: transcript ??? `risk_band_relax` ??

### multi-axis-major_geo_risk-浙江-604-008

- Profile?`major_geo_risk`?required axes?`major_geo, risk_band`?
- ???app success=N?pareto_gain=0?axis_successes={"major_geo": true, "risk_band": false}?axis_pareto_gains={"major_geo": 1, "risk_band": 0}?
- `major_geo_relax` 北京中医药大学?北京/朝阳区?护理学?min_score=597?min_rank=55521?tier=3?ranking=115?stage=1?strategy=same_leaf_variants
- risk_band: transcript ??? `risk_band_relax` ??

### multi-axis-major_geo_risk-浙江-605-009

- Profile?`major_geo_risk`?required axes?`major_geo, risk_band`?
- ???app success=Y?pareto_gain=4?axis_successes={"major_geo": true, "risk_band": true}?axis_pareto_gains={"major_geo": 1, "risk_band": 3}?
- `geo_relax` 中国矿业大学?江苏/徐州?土木工程(中外合作办学)(与澳大利亚格里菲斯大学合作办学)?min_score=604?min_rank=49407?tier=4?ranking=53?stage=??strategy=?
- `risk_band_relax` 宁波大学?浙江/宁波市?土木工程?min_score=600?min_rank=47970?tier=3?ranking=87?risk_band=??score_margin=5?rank_gap=1928

### multi-axis-major_geo_risk-浙江-610-010

- Profile?`major_geo_risk`?required axes?`major_geo, risk_band`?
- ???app success=N?pareto_gain=0?axis_successes={"major_geo": true, "risk_band": false}?axis_pareto_gains={"major_geo": 1, "risk_band": 0}?
- `major_geo_relax` 云南大学?云南/昆明市?材料科学与工程?min_score=587?min_rank=66976?tier=3?ranking=64?stage=1?strategy=same_leaf_variants
- risk_band: transcript ??? `risk_band_relax` ??

### multi-axis-quality_tuition-浙江-600-011

- Profile?`quality_tuition`?required axes?`major_quality, tuition_value`?
- ???app success=N?pareto_gain=0?axis_successes={"major_quality": true, "tuition_value": false}?axis_pareto_gains={"major_quality": 1, "tuition_value": 0}?
- `strength_relax` 江西农业大学?江西/南昌市?软件工程?min_score=574?min_rank=80371?tier=2?ranking=237?quality_score=??quality_gain=??rating=?
- tuition_value: transcript ??? `tuition_value_relax` ??

### multi-axis-quality_tuition-浙江-601-012

- Profile?`quality_tuition`?required axes?`major_quality, tuition_value`?
- ???app success=N?pareto_gain=0?axis_successes={"major_quality": true, "tuition_value": false}?axis_pareto_gains={"major_quality": 1, "tuition_value": 0}?
- `strength_relax` 江西农业大学?江西/南昌市?软件工程?min_score=574?min_rank=80371?tier=2?ranking=237?quality_score=??quality_gain=??rating=?
- tuition_value: transcript ??? `tuition_value_relax` ??

### multi-axis-quality_tuition-浙江-602-013

- Profile?`quality_tuition`?required axes?`major_quality, tuition_value`?
- ???app success=N?pareto_gain=0?axis_successes={"major_quality": true, "tuition_value": false}?axis_pareto_gains={"major_quality": 1, "tuition_value": 0}?
- `strength_relax` 江西农业大学?江西/南昌市?软件工程?min_score=574?min_rank=80371?tier=2?ranking=237?quality_score=??quality_gain=??rating=?
- tuition_value: transcript ??? `tuition_value_relax` ??

### multi-axis-quality_tuition-浙江-603-014

- Profile?`quality_tuition`?required axes?`major_quality, tuition_value`?
- ???app success=Y?pareto_gain=2?axis_successes={"major_quality": true, "tuition_value": true}?axis_pareto_gains={"major_quality": 1, "tuition_value": 1}?
- `strength_relax` 西南石油大学?四川/成都市?计算机类(成都校区.含计算机科学与技术、软件工程、物联网工程、数据科学与大数据技术、网络空间安全专业)?min_score=603?min_rank=39583?tier=3?ranking=206?quality_score=??quality_gain=??rating=?
- `tuition_value_relax` 河南大学?河南/开封市?软件工程(开封校区)?min_score=601?min_rank=52015?tier=3?ranking=84?tuition=15000?tuition_delta=9000

### multi-axis-quality_tuition-浙江-604-015

- Profile?`quality_tuition`?required axes?`major_quality, tuition_value`?
- ???app success=Y?pareto_gain=2?axis_successes={"major_quality": true, "tuition_value": true}?axis_pareto_gains={"major_quality": 1, "tuition_value": 1}?
- `strength_relax` 西南石油大学?四川/成都市?计算机类(成都校区.含计算机科学与技术、软件工程、物联网工程、数据科学与大数据技术、网络空间安全专业)?min_score=603?min_rank=39583?tier=3?ranking=206?quality_score=??quality_gain=??rating=?
- `tuition_value_relax` 河南大学?河南/开封市?软件工程(开封校区)?min_score=601?min_rank=52015?tier=3?ranking=84?tuition=15000?tuition_delta=9000

### multi-axis-quality_tuition-浙江-605-016

- Profile?`quality_tuition`?required axes?`major_quality, tuition_value`?
- ???app success=Y?pareto_gain=2?axis_successes={"major_quality": true, "tuition_value": true}?axis_pareto_gains={"major_quality": 1, "tuition_value": 1}?
- `strength_relax` 西南石油大学?四川/成都市?计算机类(成都校区.含计算机科学与技术、软件工程、物联网工程、数据科学与大数据技术、网络空间安全专业)?min_score=603?min_rank=39583?tier=3?ranking=206?quality_score=??quality_gain=??rating=?
- `tuition_value_relax` 河南大学?河南/开封市?软件工程(开封校区)?min_score=601?min_rank=52015?tier=3?ranking=84?tuition=15000?tuition_delta=9000

### multi-axis-quality_tuition-浙江-606-017

- Profile?`quality_tuition`?required axes?`major_quality, tuition_value`?
- ???app success=Y?pareto_gain=2?axis_successes={"major_quality": true, "tuition_value": true}?axis_pareto_gains={"major_quality": 1, "tuition_value": 1}?
- `strength_relax` 西南石油大学?四川/成都市?计算机类(成都校区.含计算机科学与技术、软件工程、物联网工程、数据科学与大数据技术、网络空间安全专业)?min_score=603?min_rank=39583?tier=3?ranking=206?quality_score=??quality_gain=??rating=?
- `tuition_value_relax` 河南大学?河南/开封市?软件工程(开封校区)?min_score=601?min_rank=52015?tier=3?ranking=84?tuition=15000?tuition_delta=9000

### multi-axis-quality_tuition-浙江-607-018

- Profile?`quality_tuition`?required axes?`major_quality, tuition_value`?
- ???app success=Y?pareto_gain=2?axis_successes={"major_quality": true, "tuition_value": true}?axis_pareto_gains={"major_quality": 1, "tuition_value": 1}?
- `strength_relax` 上海海洋大学?上海/浦东新区?计算机类(含计算机科学与技术、软件工程、空间信息与数字技术、数据科学与大数据技术专业)?min_score=607?min_rank=35912?tier=3?ranking=206?quality_score=??quality_gain=??rating=?
- `tuition_value_relax` 河南大学?河南/开封市?软件工程(开封校区)?min_score=601?min_rank=52015?tier=3?ranking=84?tuition=15000?tuition_delta=9000

### multi-axis-quality_tuition-浙江-608-019

- Profile?`quality_tuition`?required axes?`major_quality, tuition_value`?
- ???app success=N?pareto_gain=0?axis_successes={"major_quality": true, "tuition_value": false}?axis_pareto_gains={"major_quality": 1, "tuition_value": 0}?
- `strength_relax` 东北农业大学?黑龙江/哈尔滨市?计算机类(含计算机科学与技术、软件工程、物联网工程、人工智能专业)?min_score=608?min_rank=34937?tier=3?ranking=130?quality_score=??quality_gain=??rating=?
- tuition_value: transcript ??? `tuition_value_relax` ??

### multi-axis-quality_tuition-浙江-609-020

- Profile?`quality_tuition`?required axes?`major_quality, tuition_value`?
- ???app success=N?pareto_gain=0?axis_successes={"major_quality": true, "tuition_value": false}?axis_pareto_gains={"major_quality": 1, "tuition_value": 0}?
- `strength_relax` 东北农业大学?黑龙江/哈尔滨市?计算机类(含计算机科学与技术、软件工程、物联网工程、人工智能专业)?min_score=608?min_rank=34937?tier=3?ranking=130?quality_score=??quality_gain=??rating=?
- tuition_value: transcript ??? `tuition_value_relax` ??

### multi-axis-employment_region-浙江-610-021

- Profile?`employment_region`?required axes?`employment_outcome, region_tree`?
- ???app success=Y?pareto_gain=2?axis_successes={"employment_outcome": true, "region_tree": true}?axis_pareto_gains={"employment_outcome": 1, "region_tree": 1}?
- `employment_outcome_relax` 郑州大学?河南/郑州市?工业设计?min_score=606?min_rank=45348?tier=3?ranking=49?outcome_score=100.0?outcome_gain=49.0?employment_rank=4?top_industry=互联网/电子商务?salary=["面议 ","50000以上 ","4500-5999 "] [66%,16%,16%]
- `region_tree_relax` 宁波大学?浙江/宁波市?机械类(含机械设计制造及其自动化、车辆工程、工业工程专业)?min_score=600?min_rank=42609?tier=3?ranking=87?strategy=geo_block_relax?region=杭州->宁波?tree_confidence=0.95

### multi-axis-employment_region-浙江-612-022

- Profile?`employment_region`?required axes?`employment_outcome, region_tree`?
- ???app success=Y?pareto_gain=2?axis_successes={"employment_outcome": true, "region_tree": true}?axis_pareto_gains={"employment_outcome": 1, "region_tree": 1}?
- `employment_outcome_relax` 郑州大学?河南/郑州市?工业设计?min_score=606?min_rank=45348?tier=3?ranking=49?outcome_score=100.0?outcome_gain=49.0?employment_rank=4?top_industry=互联网/电子商务?salary=["面议 ","50000以上 ","4500-5999 "] [66%,16%,16%]
- `region_tree_relax` 宁波大学?浙江/宁波市?机械类(含机械设计制造及其自动化、车辆工程、工业工程专业)?min_score=600?min_rank=42609?tier=3?ranking=87?strategy=geo_block_relax?region=杭州->宁波?tree_confidence=0.95

### multi-axis-employment_region-浙江-614-023

- Profile?`employment_region`?required axes?`employment_outcome, region_tree`?
- ???app success=Y?pareto_gain=2?axis_successes={"employment_outcome": true, "region_tree": true}?axis_pareto_gains={"employment_outcome": 1, "region_tree": 1}?
- `employment_outcome_relax` 郑州大学?河南/郑州市?工业设计?min_score=606?min_rank=45348?tier=3?ranking=49?outcome_score=100.0?outcome_gain=49.0?employment_rank=4?top_industry=互联网/电子商务?salary=["面议 ","50000以上 ","4500-5999 "] [66%,16%,16%]
- `region_tree_relax` 宁波大学?浙江/宁波市?机械设计制造及其自动化?min_score=614?min_rank=37017?tier=3?ranking=87?strategy=geo_block_relax?region=杭州->宁波?tree_confidence=0.95

### multi-axis-employment_region-浙江-616-024

- Profile?`employment_region`?required axes?`employment_outcome, region_tree`?
- ???app success=Y?pareto_gain=2?axis_successes={"employment_outcome": true, "region_tree": true}?axis_pareto_gains={"employment_outcome": 1, "region_tree": 1}?
- `employment_outcome_relax` 西南交通大学?四川/成都市?工业设计?min_score=615?min_rank=36544?tier=3?ranking=39?outcome_score=100.0?outcome_gain=49.0?employment_rank=4?top_industry=互联网/电子商务?salary=["面议 ","50000以上 ","4500-5999 "] [66%,16%,16%]
- `region_tree_relax` 宁波大学?浙江/宁波市?机械设计制造及其自动化?min_score=615?min_rank=37690?tier=3?ranking=87?strategy=geo_block_relax?region=杭州->宁波?tree_confidence=0.95

### multi-axis-employment_region-浙江-618-025

- Profile?`employment_region`?required axes?`employment_outcome, region_tree`?
- ???app success=Y?pareto_gain=2?axis_successes={"employment_outcome": true, "region_tree": true}?axis_pareto_gains={"employment_outcome": 1, "region_tree": 1}?
- `employment_outcome_relax` 西南交通大学?四川/成都市?工业设计?min_score=615?min_rank=36544?tier=3?ranking=39?outcome_score=100.0?outcome_gain=49.0?employment_rank=4?top_industry=互联网/电子商务?salary=["面议 ","50000以上 ","4500-5999 "] [66%,16%,16%]
- `region_tree_relax` 宁波大学?浙江/宁波市?机械类(含机械设计制造及其自动化,车辆工程,工业工程专业)?min_score=617?min_rank=36476?tier=3?ranking=87?strategy=geo_block_relax?region=杭州->宁波?tree_confidence=0.95

### multi-axis-employment_region-浙江-620-026

- Profile?`employment_region`?required axes?`employment_outcome, region_tree`?
- ???app success=Y?pareto_gain=2?axis_successes={"employment_outcome": true, "region_tree": true}?axis_pareto_gains={"employment_outcome": 1, "region_tree": 1}?
- `employment_outcome_relax` 西南交通大学?四川/成都市?工业设计?min_score=615?min_rank=36544?tier=3?ranking=39?outcome_score=100.0?outcome_gain=49.0?employment_rank=4?top_industry=互联网/电子商务?salary=["面议 ","50000以上 ","4500-5999 "] [66%,16%,16%]
- `region_tree_relax` 宁波大学?浙江/宁波市?机械类(含机械设计制造及其自动化,车辆工程,工业工程专业)?min_score=617?min_rank=36476?tier=3?ranking=87?strategy=geo_block_relax?region=杭州->宁波?tree_confidence=0.95

### multi-axis-employment_region-浙江-622-027

- Profile?`employment_region`?required axes?`employment_outcome, region_tree`?
- ???app success=Y?pareto_gain=2?axis_successes={"employment_outcome": true, "region_tree": true}?axis_pareto_gains={"employment_outcome": 1, "region_tree": 1}?
- `employment_outcome_relax` 西南交通大学?四川/成都市?工业设计?min_score=615?min_rank=36544?tier=3?ranking=39?outcome_score=100.0?outcome_gain=49.0?employment_rank=4?top_industry=互联网/电子商务?salary=["面议 ","50000以上 ","4500-5999 "] [66%,16%,16%]
- `region_tree_relax` 宁波大学?浙江/宁波市?机械类(含机械设计制造及其自动化,车辆工程,工业工程专业)?min_score=617?min_rank=36476?tier=3?ranking=87?strategy=geo_block_relax?region=杭州->宁波?tree_confidence=0.95

### multi-axis-employment_region-浙江-624-028

- Profile?`employment_region`?required axes?`employment_outcome, region_tree`?
- ???app success=Y?pareto_gain=2?axis_successes={"employment_outcome": true, "region_tree": true}?axis_pareto_gains={"employment_outcome": 1, "region_tree": 1}?
- `employment_outcome_relax` 西南交通大学?四川/成都市?工业设计?min_score=615?min_rank=36544?tier=3?ranking=39?outcome_score=100.0?outcome_gain=49.0?employment_rank=4?top_industry=互联网/电子商务?salary=["面议 ","50000以上 ","4500-5999 "] [66%,16%,16%]
- `region_tree_relax` 宁波大学?浙江/宁波市?机械类(含机械设计制造及其自动化,车辆工程,工业工程专业)?min_score=617?min_rank=36476?tier=3?ranking=87?strategy=geo_block_relax?region=杭州->宁波?tree_confidence=0.95

### multi-axis-employment_region-浙江-626-029

- Profile?`employment_region`?required axes?`employment_outcome, region_tree`?
- ???app success=Y?pareto_gain=2?axis_successes={"employment_outcome": true, "region_tree": true}?axis_pareto_gains={"employment_outcome": 1, "region_tree": 1}?
- `employment_outcome_relax` 西南交通大学?四川/成都市?工业设计?min_score=615?min_rank=36544?tier=3?ranking=39?outcome_score=100.0?outcome_gain=49.0?employment_rank=4?top_industry=互联网/电子商务?salary=["面议 ","50000以上 ","4500-5999 "] [66%,16%,16%]
- `region_tree_relax` 宁波大学?浙江/宁波市?机械类(含机械设计制造及其自动化,车辆工程,工业工程专业)?min_score=617?min_rank=36476?tier=3?ranking=87?strategy=geo_block_relax?region=杭州->宁波?tree_confidence=0.95

### multi-axis-employment_region-浙江-628-030

- Profile?`employment_region`?required axes?`employment_outcome, region_tree`?
- ???app success=Y?pareto_gain=2?axis_successes={"employment_outcome": true, "region_tree": true}?axis_pareto_gains={"employment_outcome": 1, "region_tree": 1}?
- `employment_outcome_relax` 西南交通大学?四川/成都市?工业设计?min_score=615?min_rank=36544?tier=3?ranking=39?outcome_score=100.0?outcome_gain=49.0?employment_rank=4?top_industry=互联网/电子商务?salary=["面议 ","50000以上 ","4500-5999 "] [66%,16%,16%]
- `region_tree_relax` 宁波大学?浙江/宁波市?机械类(含机械设计制造及其自动化,车辆工程,工业工程专业)?min_score=617?min_rank=36476?tier=3?ranking=87?strategy=geo_block_relax?region=杭州->宁波?tree_confidence=0.95

## 6. Baseline ?????

`hard_constraint` baseline ?????????????????????????????? Pareto negotiation???? 30 ? case ? baseline ???? `0.000`???????????

`multi_axis_v1` ?????????????????????? required axes???????????`axis_successes` ??????????? `elicitation_success` ?????

???????? `multi_axis_v1` ?? Benchmark ??????????????? sandbox/evaluator ??????????????????????????????????? `major_geo_v1 + risk_band_v1` ??????
