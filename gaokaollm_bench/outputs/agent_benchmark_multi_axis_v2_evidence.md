# multi_axis_v2 轴一致性 Benchmark 压力测试逐例证据

## 实验定位

`multi_axis_v2` 是多轴隐藏妥协压力测试的修正版，目标是修正 v1 中部分画像轴不一致的问题。它不替代主实验，也不改变七组单轴/单类实验事实表；它专门检查同一用户同时存在两个隐藏妥协轴时，证据谈判 Agent 是否能同时组织两类证据。

- Persona: `gaokaollm_bench/sample_data/iceberg_personas_multi_axis_coherent_real_db_30.json`
- Output: `gaokaollm_bench/outputs/agent_benchmark_multi_axis_v2/`
- Summary: `gaokaollm_bench/outputs/agent_benchmark_multi_axis_v2_summary.md`
- Hidden fields `implicit_flexibilities`、`volunteer_set`、`axis_flexibilities` 仅用于模拟器和评测器，Agent 不读取。

## 聚合指标核对

| Target | Cases | Success | Mean Pareto gain | Mean hallucination | Avg turns |
|---|---:|---:|---:|---:|---:|
| app_pareto | 30 | 0.367 | 1.133 | 0.005 | 9.33 |
| hard_constraint | 30 | 0.000 | 0.000 | 0.008 | 13.00 |

## Profile 结果

| Profile | Cases | Success | Mean gain | Axis success summary |
|---|---:|---:|---:|---|
| `major_geo_risk` 专业-地域放宽 + 风险组合 | 10 | 6 | 2.400 | major_geo 8/10, risk_band 7/10 |
| `quality_tuition` 专业质量 + 学费预算 | 10 | 5 | 1.000 | major_quality 10/10, tuition_value 5/10 |
| `employment_region` 就业结果 + 地域层级证据 | 10 | 0 | 0.000 | employment_outcome 10/10 |

## 逐例结果

| Case | Profile | App success | Baseline success | Turns | Hallucination | Gain | Axis successes |
|---|---|---:|---:|---:|---:|---:|---|
| `multi-axis-v2-major_geo_risk-浙江-592-001` | `major_geo_risk` | True | False | 3 | 0.000 | 4 | major_geo=true, risk_band=true |
| `multi-axis-v2-major_geo_risk-浙江-600-002` | `major_geo_risk` | True | False | 3 | 0.000 | 4 | major_geo=true, risk_band=true |
| `multi-axis-v2-major_geo_risk-浙江-610-003` | `major_geo_risk` | False | False | 13 | 0.000 | 0 | major_geo=false, risk_band=true |
| `multi-axis-v2-major_geo_risk-浙江-620-004` | `major_geo_risk` | False | False | 13 | 0.000 | 0 | major_geo=false, risk_band=false |
| `multi-axis-v2-major_geo_risk-浙江-630-005` | `major_geo_risk` | True | False | 3 | 0.143 | 4 | major_geo=true, risk_band=true |
| `multi-axis-v2-major_geo_risk-浙江-594-006` | `major_geo_risk` | False | False | 13 | 0.000 | 0 | major_geo=true, risk_band=false |
| `multi-axis-v2-major_geo_risk-浙江-600-007` | `major_geo_risk` | True | False | 3 | 0.000 | 4 | major_geo=true, risk_band=true |
| `multi-axis-v2-major_geo_risk-浙江-610-008` | `major_geo_risk` | False | False | 13 | 0.000 | 0 | major_geo=true, risk_band=false |
| `multi-axis-v2-major_geo_risk-浙江-580-009` | `major_geo_risk` | True | False | 3 | 0.000 | 4 | major_geo=true, risk_band=true |
| `multi-axis-v2-major_geo_risk-浙江-590-010` | `major_geo_risk` | True | False | 3 | 0.000 | 4 | major_geo=true, risk_band=true |
| `multi-axis-v2-quality_tuition-浙江-600-011` | `quality_tuition` | False | False | 13 | 0.000 | 0 | major_quality=true, tuition_value=false |
| `multi-axis-v2-quality_tuition-浙江-601-012` | `quality_tuition` | False | False | 13 | 0.000 | 0 | major_quality=true, tuition_value=false |
| `multi-axis-v2-quality_tuition-浙江-602-013` | `quality_tuition` | False | False | 13 | 0.000 | 0 | major_quality=true, tuition_value=false |
| `multi-axis-v2-quality_tuition-浙江-603-014` | `quality_tuition` | True | False | 3 | 0.000 | 2 | major_quality=true, tuition_value=true |
| `multi-axis-v2-quality_tuition-浙江-604-015` | `quality_tuition` | True | False | 3 | 0.000 | 2 | major_quality=true, tuition_value=true |
| `multi-axis-v2-quality_tuition-浙江-605-016` | `quality_tuition` | True | False | 3 | 0.000 | 2 | major_quality=true, tuition_value=true |
| `multi-axis-v2-quality_tuition-浙江-606-017` | `quality_tuition` | True | False | 3 | 0.000 | 2 | major_quality=true, tuition_value=true |
| `multi-axis-v2-quality_tuition-浙江-607-018` | `quality_tuition` | True | False | 3 | 0.000 | 2 | major_quality=true, tuition_value=true |
| `multi-axis-v2-quality_tuition-浙江-608-019` | `quality_tuition` | False | False | 13 | 0.000 | 0 | major_quality=true, tuition_value=false |
| `multi-axis-v2-quality_tuition-浙江-610-020` | `quality_tuition` | False | False | 13 | 0.000 | 0 | major_quality=true, tuition_value=false |
| `multi-axis-v2-employment_region-浙江-520-021` | `employment_region` | False | False | 13 | 0.000 | 0 | employment_outcome=true, region_tree=false |
| `multi-axis-v2-employment_region-浙江-522-022` | `employment_region` | False | False | 13 | 0.000 | 0 | employment_outcome=true, region_tree=false |
| `multi-axis-v2-employment_region-浙江-524-023` | `employment_region` | False | False | 13 | 0.000 | 0 | employment_outcome=true, region_tree=false |
| `multi-axis-v2-employment_region-浙江-526-024` | `employment_region` | False | False | 13 | 0.000 | 0 | employment_outcome=true, region_tree=false |
| `multi-axis-v2-employment_region-浙江-528-025` | `employment_region` | False | False | 13 | 0.000 | 0 | employment_outcome=true, region_tree=false |
| `multi-axis-v2-employment_region-浙江-530-026` | `employment_region` | False | False | 13 | 0.000 | 0 | employment_outcome=true, region_tree=false |
| `multi-axis-v2-employment_region-浙江-532-027` | `employment_region` | False | False | 13 | 0.000 | 0 | employment_outcome=true, region_tree=false |
| `multi-axis-v2-employment_region-浙江-534-028` | `employment_region` | False | False | 13 | 0.000 | 0 | employment_outcome=true, region_tree=false |
| `multi-axis-v2-employment_region-浙江-536-029` | `employment_region` | False | False | 13 | 0.000 | 0 | employment_outcome=true, region_tree=false |
| `multi-axis-v2-employment_region-浙江-538-030` | `employment_region` | False | False | 13 | 0.000 | 0 | employment_outcome=true, region_tree=false |

## 轴级候选证据

| Case | Required axes | Axis hit | Representative evidence from hidden set |
|---|---|---|---|
| `multi-axis-v2-major_geo_risk-浙江-592-001` | major_geo, risk_band | {"major_geo": true, "risk_band": true} | major_geo: 海军军医大学; 护理学(护师)(只招普通高中应届毕业生.政治面貌要求为共青团员或中共党员.要求高考成绩不低于特殊类型招生控制线); min_score=589; min_rank=54060<br>risk_band: 杭州师范大学; 临床医学; min_score=590; min_rank=63187; risk_level=chong |
| `multi-axis-v2-major_geo_risk-浙江-600-002` | major_geo, risk_band | {"major_geo": true, "risk_band": true} | major_geo: 中国矿业大学; 土木工程; min_score=599; min_rank=52740<br>risk_band: 杭州医学院; 临床医学; min_score=591; min_rank=62029; risk_level=chong |
| `multi-axis-v2-major_geo_risk-浙江-610-003` | major_geo, risk_band | {"major_geo": false, "risk_band": true} | major_geo: 厦门大学; 化学工程与工艺(厦门大学马来西亚分校招生专业)(马来西亚分校.全英文授课,要求高考外语成绩不低于120分.人学第一年期间达到录取专业要求的雅思等成绩后开始学位课程学习.学费:2.8万林吉特/学年,办学地点在马来西亚雪兰莪州雪邦沙叻丁宜); min_score=603; min_rank=39583<br>risk_band: 宁波大学; 临床医学; min_score=610; min_rank=40934; risk_level=chong |
| `multi-axis-v2-major_geo_risk-浙江-620-004` | major_geo, risk_band | {"major_geo": false, "risk_band": false} | major_geo: 厦门大学; 软件工程(厦门大学马来西亚分校招生专业)(马来西亚分校.全英文授课,要求高考外语成绩不低于120分.入学第一年期间达到录取专业要求的雅思等成绩后开始学位课程学习.学费:2.7万林吉特/学年,办学地点在马来西亚雪兰莪州1雪邦沙叻丁宜); min_score=618; min_rank=26327<br>risk_band: 温州医科大学; 临床医学(中外合作办学)(要求高考外语成绩不低于120分); min_score=615; min_rank=28836; risk_level=chong |
| `multi-axis-v2-major_geo_risk-浙江-630-005` | major_geo, risk_band | {"major_geo": true, "risk_band": true} | major_geo: 哈尔滨工业大学(威海); 船舶与海洋工程(中外合作办学)(威海校区); min_score=629; min_rank=18297<br>risk_band: 温州医科大学; 临床医学; min_score=627; min_rank=25442; risk_level=chong |
| `multi-axis-v2-major_geo_risk-浙江-594-006` | major_geo, risk_band | {"major_geo": true, "risk_band": false} | major_geo: 海军军医大学; 护理学(护师)(只招普通高中应届毕业生.政治面貌要求为共青团员或中共党员.要求高考成绩不低于特殊类型招生控制线); min_score=589; min_rank=54060<br>risk_band: 浙江中医药大学; 临床医学; min_score=594; min_rank=58239; risk_level=chong |
| `multi-axis-v2-major_geo_risk-浙江-600-007` | major_geo, risk_band | {"major_geo": true, "risk_band": true} | major_geo: 中国矿业大学; 土木工程; min_score=599; min_rank=52740<br>risk_band: 浙江中医药大学; 临床医学; min_score=594; min_rank=58239; risk_level=chong |
| `multi-axis-v2-major_geo_risk-浙江-610-008` | major_geo, risk_band | {"major_geo": true, "risk_band": false} | major_geo: 厦门大学; 化学工程与工艺(厦门大学马来西亚分校招生专业)(马来西亚分校.全英文授课,要求高考外语成绩不低于120分.人学第一年期间达到录取专业要求的雅思等成绩后开始学位课程学习.学费:2.8万林吉特/学年,办学地点在马来西亚雪兰莪州雪邦沙叻丁宜); min_score=603; min_rank=39583<br>risk_band: 杭州师范大学; 临床医学; min_score=602; min_rank=46132; risk_level=chong |
| `multi-axis-v2-major_geo_risk-浙江-580-009` | major_geo, risk_band | {"major_geo": true, "risk_band": true} | major_geo: 西南交通大学; 城市设计(成都东部(国际)校区正式启用前,过渡办学地点在成都犀浦校区); min_score=492; min_rank=178059<br>risk_band: 浙江师范大学; 环境科学与工程; min_score=579; min_rank=76210; risk_level=chong |
| `multi-axis-v2-major_geo_risk-浙江-590-010` | major_geo, risk_band | {"major_geo": true, "risk_band": true} | major_geo: 海军军医大学; 护理学(护师)(只招普通高中应届毕业生.政治面貌要求为共青团员或中共党员.要求高考成绩不低于特殊类型招生控制线); min_score=589; min_rank=54060<br>risk_band: 宁波大学; 旅游管理(中外合作办学)(中法合作)(植物园校区.符合条件者第四学年可选赴法国昂热大学留学,可获中法双文凭,法方不另收学费); min_score=587; min_rank=56283; risk_level=chong |
| `multi-axis-v2-quality_tuition-浙江-600-011` | major_quality, tuition_value | {"major_quality": true, "tuition_value": false} | major_quality: 重庆邮电大学; 软件工程; min_score=600; min_rank=51826; quality_score=97.0; quality_gain=16.0<br>tuition_value: 河南大学; 软件工程; min_score=599; min_rank=52808; tuition=15000; tuition_delta=9000 |
| `multi-axis-v2-quality_tuition-浙江-601-012` | major_quality, tuition_value | {"major_quality": true, "tuition_value": false} | major_quality: 重庆邮电大学; 软件工程; min_score=600; min_rank=51826; quality_score=97.0; quality_gain=16.0<br>tuition_value: 河南大学; 软件工程; min_score=599; min_rank=52808; tuition=15000; tuition_delta=9000 |
| `multi-axis-v2-quality_tuition-浙江-602-013` | major_quality, tuition_value | {"major_quality": true, "tuition_value": false} | major_quality: 重庆邮电大学; 软件工程; min_score=600; min_rank=51826; quality_score=97.0; quality_gain=16.0<br>tuition_value: 河南大学; 软件工程; min_score=599; min_rank=52808; tuition=15000; tuition_delta=9000 |
| `multi-axis-v2-quality_tuition-浙江-603-014` | major_quality, tuition_value | {"major_quality": true, "tuition_value": true} | major_quality: 重庆邮电大学; 软件工程; min_score=600; min_rank=51826; quality_score=97.0; quality_gain=16.0<br>tuition_value: 河南大学; 软件工程; min_score=599; min_rank=52808; tuition=15000; tuition_delta=9000 |
| `multi-axis-v2-quality_tuition-浙江-604-015` | major_quality, tuition_value | {"major_quality": true, "tuition_value": true} | major_quality: 重庆邮电大学; 软件工程; min_score=600; min_rank=51826; quality_score=97.0; quality_gain=16.0<br>tuition_value: 河南大学; 软件工程; min_score=599; min_rank=52808; tuition=15000; tuition_delta=9000 |
| `multi-axis-v2-quality_tuition-浙江-605-016` | major_quality, tuition_value | {"major_quality": true, "tuition_value": true} | major_quality: 重庆邮电大学; 软件工程; min_score=600; min_rank=51826; quality_score=97.0; quality_gain=16.0<br>tuition_value: 河南大学; 软件工程; min_score=599; min_rank=52808; tuition=15000; tuition_delta=9000 |
| `multi-axis-v2-quality_tuition-浙江-606-017` | major_quality, tuition_value | {"major_quality": true, "tuition_value": true} | major_quality: 重庆邮电大学; 软件工程; min_score=600; min_rank=51826; quality_score=97.0; quality_gain=16.0<br>tuition_value: 河南大学; 软件工程; min_score=599; min_rank=52808; tuition=15000; tuition_delta=9000 |
| `multi-axis-v2-quality_tuition-浙江-607-018` | major_quality, tuition_value | {"major_quality": true, "tuition_value": true} | major_quality: 重庆邮电大学; 软件工程; min_score=600; min_rank=51826; quality_score=97.0; quality_gain=16.0<br>tuition_value: 河南大学; 软件工程; min_score=599; min_rank=52808; tuition=15000; tuition_delta=9000 |
| `multi-axis-v2-quality_tuition-浙江-608-019` | major_quality, tuition_value | {"major_quality": true, "tuition_value": false} | major_quality: 重庆邮电大学; 软件工程; min_score=600; min_rank=51826; quality_score=97.0; quality_gain=16.0<br>tuition_value: 河南大学; 软件工程; min_score=599; min_rank=52808; tuition=15000; tuition_delta=9000 |
| `multi-axis-v2-quality_tuition-浙江-610-020` | major_quality, tuition_value | {"major_quality": true, "tuition_value": false} | major_quality: 重庆邮电大学; 软件工程; min_score=600; min_rank=51826; quality_score=97.0; quality_gain=16.0<br>tuition_value: 河南大学; 软件工程; min_score=599; min_rank=52808; tuition=15000; tuition_delta=9000 |
| `multi-axis-v2-employment_region-浙江-520-021` | employment_outcome, region_tree | {"employment_outcome": true, "region_tree": false} | employment_outcome: 广西师范大学; 工业设计; min_score=513; min_rank=156857; outcome_score=100.0; outcome_gain=49.0<br>region_tree: 西南交通大学; 城市设计(成都东部(国际)校区正式启用前,过渡办学地点在成都犀浦校区); min_score=492; min_rank=178059; region_relax_strategy=urban_tier_relax; target_region_name=成都 |
| `multi-axis-v2-employment_region-浙江-522-022` | employment_outcome, region_tree | {"employment_outcome": true, "region_tree": false} | employment_outcome: 广西师范大学; 工业设计; min_score=513; min_rank=156857; outcome_score=100.0; outcome_gain=49.0<br>region_tree: 西南交通大学; 城市设计(成都东部(国际)校区正式启用前,过渡办学地点在成都犀浦校区); min_score=492; min_rank=178059; region_relax_strategy=urban_tier_relax; target_region_name=成都 |
| `multi-axis-v2-employment_region-浙江-524-023` | employment_outcome, region_tree | {"employment_outcome": true, "region_tree": false} | employment_outcome: 广西师范大学; 工业设计; min_score=513; min_rank=156857; outcome_score=100.0; outcome_gain=49.0<br>region_tree: 西南交通大学; 城市设计(成都东部(国际)校区正式启用前,过渡办学地点在成都犀浦校区); min_score=492; min_rank=178059; region_relax_strategy=urban_tier_relax; target_region_name=成都 |
| `multi-axis-v2-employment_region-浙江-526-024` | employment_outcome, region_tree | {"employment_outcome": true, "region_tree": false} | employment_outcome: 广西师范大学; 工业设计; min_score=513; min_rank=156857; outcome_score=100.0; outcome_gain=49.0<br>region_tree: 西南交通大学; 城市设计(成都东部(国际)校区正式启用前,过渡办学地点在成都犀浦校区); min_score=492; min_rank=178059; region_relax_strategy=urban_tier_relax; target_region_name=成都 |
| `multi-axis-v2-employment_region-浙江-528-025` | employment_outcome, region_tree | {"employment_outcome": true, "region_tree": false} | employment_outcome: 广西师范大学; 工业设计; min_score=513; min_rank=156857; outcome_score=100.0; outcome_gain=49.0<br>region_tree: 西南交通大学; 城市设计(成都东部(国际)校区正式启用前,过渡办学地点在成都犀浦校区); min_score=492; min_rank=178059; region_relax_strategy=urban_tier_relax; target_region_name=成都 |
| `multi-axis-v2-employment_region-浙江-530-026` | employment_outcome, region_tree | {"employment_outcome": true, "region_tree": false} | employment_outcome: 广西师范大学; 工业设计; min_score=513; min_rank=156857; outcome_score=100.0; outcome_gain=49.0<br>region_tree: 西南交通大学; 城市设计(成都东部(国际)校区正式启用前,过渡办学地点在成都犀浦校区); min_score=492; min_rank=178059; region_relax_strategy=urban_tier_relax; target_region_name=成都 |
| `multi-axis-v2-employment_region-浙江-532-027` | employment_outcome, region_tree | {"employment_outcome": true, "region_tree": false} | employment_outcome: 广西师范大学; 工业设计; min_score=513; min_rank=156857; outcome_score=100.0; outcome_gain=49.0<br>region_tree: 西南交通大学; 城市设计(成都东部(国际)校区正式启用前,过渡办学地点在成都犀浦校区); min_score=492; min_rank=178059; region_relax_strategy=urban_tier_relax; target_region_name=成都 |
| `multi-axis-v2-employment_region-浙江-534-028` | employment_outcome, region_tree | {"employment_outcome": true, "region_tree": false} | employment_outcome: 广西师范大学; 工业设计; min_score=513; min_rank=156857; outcome_score=100.0; outcome_gain=49.0<br>region_tree: 西南交通大学; 城市设计(成都东部(国际)校区正式启用前,过渡办学地点在成都犀浦校区); min_score=492; min_rank=178059; region_relax_strategy=urban_tier_relax; target_region_name=成都 |
| `multi-axis-v2-employment_region-浙江-536-029` | employment_outcome, region_tree | {"employment_outcome": true, "region_tree": false} | employment_outcome: 广西师范大学; 工业设计; min_score=513; min_rank=156857; outcome_score=100.0; outcome_gain=49.0<br>region_tree: 西南交通大学; 城市设计(成都东部(国际)校区正式启用前,过渡办学地点在成都犀浦校区); min_score=492; min_rank=178059; region_relax_strategy=urban_tier_relax; target_region_name=成都 |
| `multi-axis-v2-employment_region-浙江-538-030` | employment_outcome, region_tree | {"employment_outcome": true, "region_tree": false} | employment_outcome: 广西师范大学; 工业设计; min_score=513; min_rank=156857; outcome_score=100.0; outcome_gain=49.0<br>region_tree: 西南交通大学; 城市设计(成都东部(国际)校区正式启用前,过渡办学地点在成都犀浦校区); min_score=492; min_rank=178059; region_relax_strategy=urban_tier_relax; target_region_name=成都 |

## 论文可引用结论

v2 修正后，Benchmark 构造不再依赖无关单轴样本拼接，而是记录 `multi_axis_version=v2` 与 `coherence_checks`。结果显示 app_pareto 仍显著高于硬约束基线，但就业-地域组合和部分质量-学费组合暴露出多轴证据编排瓶颈；这说明压力测试用于发现组合能力上限，而不是替代主实验结论。
