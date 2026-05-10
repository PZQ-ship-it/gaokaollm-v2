# Region Tree v1 HITL Coverage Report

本报告验收地域树 HITL 审校包与 v1 数据层覆盖改进，不表示 `region_tree_relax` 已进入 Agent 或 Benchmark 实验。

## Boundary

- 当前主实验仍是 `major_geo_v1 + risk_band_v1`。
- 当前六组实验结果不包含地域树实验。
- `region_tree_relax` 尚未实现，不得把本报告写成 Pareto gain。
- 不能只凭 `schools.city` 包装城市收益。
- 未来 Agent 仍不能读取 `implicit_flexibilities` 或 `volunteer_set`。

## v0 / v1 Coverage Comparison

| Metric | v0 | v1 | Delta |
|---|---:|---:|---:|
| `total_city_pairs` | 414 | 414 | 0 |
| `total_schools` | 3219 | 3219 | 0 |
| `province_count` | 35 | 35 | 0 |
| `province_mapped_count` | 29 | 31 | 2 |
| `geo_city_pair_mapped_count` | 395 | 412 | 17 |
| `geo_city_pair_high_confidence_count` | 12 | 63 | 51 |
| `urban_city_pair_mapped_count` | 72 | 123 | 51 |
| `urban_city_pair_high_confidence_count` | 71 | 122 | 51 |
| `review_queue_count` | 404 | 353 | -51 |

## Review Batch

- Review packet rows: 404
- Rule-seeded v1 reviewed rows: 50
- Review source: `rule_seed_v1_top_priority_rows`
- 这些条目是 v1 seed，不等同于最终人工审校完成；后续可以在 CSV/JSONL 中人工修改后再次回填。

## Reviewed Seed Rows

| Rank | Province | City | Schools | Geo action | Urban action | Reasons |
|---:|---|---|---:|---|---|---|
| 1 | 内蒙古 | 呼和浩特市 | 25 | accept_suggested_geo | accept_suggested_urban | geo_province_or_city_unmatched;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 2 | 香港 | 香港 | 11 | accept_suggested_geo | accept_suggested_urban | geo_province_or_city_unmatched;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 3 | 内蒙古 | 包头市 | 7 | accept_suggested_geo | accept_suggested_urban | geo_province_or_city_unmatched;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 4 | 澳门 | 澳门 | 6 | accept_suggested_geo | accept_suggested_urban | geo_province_or_city_unmatched;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 5 | 内蒙古 | 赤峰市 | 5 | accept_suggested_geo | accept_suggested_urban | geo_province_or_city_unmatched;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 6 | 内蒙古 | 鄂尔多斯市 | 5 | accept_suggested_geo | accept_suggested_urban | geo_province_or_city_unmatched;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 7 | 西藏 | 拉萨市 | 5 | accept_suggested_geo | accept_suggested_urban | geo_province_or_city_unmatched;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 8 | 内蒙古 | 呼伦贝尔市 | 4 | accept_suggested_geo | accept_suggested_urban | geo_province_or_city_unmatched;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 9 | 内蒙古 | 乌兰察布市 | 3 | accept_suggested_geo | accept_suggested_urban | geo_province_or_city_unmatched;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 10 | 内蒙古 | 通辽市 | 3 | accept_suggested_geo | accept_suggested_urban | geo_province_or_city_unmatched;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 11 | 内蒙古 | 巴彦淖尔市 | 2 | accept_suggested_geo | accept_suggested_urban | geo_province_or_city_unmatched;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 12 | 内蒙古 | 乌海市 | 1 | accept_suggested_geo | accept_suggested_urban | geo_province_or_city_unmatched;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 13 | 内蒙古 | 兴安盟 | 1 | accept_suggested_geo | accept_suggested_urban | geo_province_or_city_unmatched;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 14 | 内蒙古 | 呼伦贝尔市满洲里市 | 1 | accept_suggested_geo | accept_suggested_urban | geo_province_or_city_unmatched;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 15 | 内蒙古 | 锡林郭勒盟 | 1 | accept_suggested_geo | accept_suggested_urban | geo_province_or_city_unmatched;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 16 | 内蒙古 | 阿拉善盟 | 1 | accept_suggested_geo | accept_suggested_urban | geo_province_or_city_unmatched;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 18 | 西藏 | 林芝市 | 1 | accept_suggested_geo | accept_suggested_urban | geo_province_or_city_unmatched;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 20 | 陕西 | 西安市 | 92 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 21 | 河南 | 郑州市 | 82 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 22 | 江西 | 南昌市 | 64 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 23 | 湖南 | 长沙市 | 63 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 24 | 黑龙江 | 哈尔滨市 | 60 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 25 | 云南 | 昆明市 | 57 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 26 | 河北 | 石家庄 | 57 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 27 | 山西 | 太原市 | 53 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 28 | 吉林 | 长春市 | 49 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 29 | 辽宁 | 沈阳市 | 47 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 30 | 贵州 | 贵阳市 | 44 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 31 | 山东 | 济南市 | 42 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 32 | 广西 | 南宁市 | 42 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 33 | 甘肃 | 兰州市 | 39 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 34 | 福建 | 福州市 | 39 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 35 | 辽宁 | 大连市 | 32 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 36 | 山东 | 青岛市 | 28 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 37 | 新疆 | 乌鲁木齐市 | 27 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 38 | 山东 | 烟台市 | 21 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 39 | 广西 | 桂林市 | 20 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 40 | 福建 | 泉州市 | 20 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 41 | 河北 | 保定市 | 19 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 42 | 宁夏 | 银川市 | 17 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 43 | 山东 | 潍坊市 | 17 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 44 | 湖南 | 湘潭市 | 17 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 45 | 福建 | 厦门市 | 17 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 46 | 河北 | 廊坊市 | 16 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 47 | 江苏 | 徐州 | 14 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 48 | 江苏 | 无锡 | 14 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 49 | 四川 | 绵阳市 | 13 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 50 | 河北 | 唐山市 | 13 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 51 | 海南 | 海口市 | 13 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |
| 52 | 安徽 | 芜湖市 | 12 | accept_suggested_geo | accept_suggested_urban | geo_city_not_explicitly_mapped;low_confidence_or_missing_mapping;urban_tier_unmatched |

## Remaining Review Queue Sample

| Province | City | Schools | Geo node | Urban node | Reasons |
|---|---|---:|---|---|---|
| 上海 | 嘉定区 | 4 | geo:province:shanghai | urban:city:shanghai | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 奉贤区 | 6 | geo:province:shanghai | urban:city:shanghai | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 宝山区 | 6 | geo:province:shanghai | urban:city:shanghai | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 徐汇区 | 9 | geo:province:shanghai | urban:city:shanghai | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 普陀区 | 1 | geo:province:shanghai | urban:city:shanghai | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 杨浦区 | 11 | geo:province:shanghai | urban:city:shanghai | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 松江区 | 7 | geo:province:shanghai | urban:city:shanghai | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 浦东新区 | 21 | geo:province:shanghai | urban:city:shanghai | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 虹口区 | 3 | geo:province:shanghai | urban:city:shanghai | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 金山区 | 2 | geo:province:shanghai | urban:city:shanghai | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 长宁区 | 1 | geo:province:shanghai | urban:city:shanghai | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 闵行区 | 2 | geo:province:shanghai | urban:city:shanghai | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 青浦区 | 1 | geo:province:shanghai | urban:city:shanghai | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 静安区 | 3 | geo:province:shanghai | urban:city:shanghai | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 黄浦区 | 1 | geo:province:shanghai | urban:city:shanghai | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 云南 | 临沧市 | 1 | geo:province:yunnan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 丽江市 | 3 | geo:province:yunnan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 保山市 | 2 | geo:province:yunnan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 大理白族自治州 | 4 | geo:province:yunnan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 德宏傣族景颇族自治州 | 2 | geo:province:yunnan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 文山壮族苗族自治州 | 2 | geo:province:yunnan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 昭通市 | 2 | geo:province:yunnan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 普洱市 | 2 | geo:province:yunnan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 曲靖市 | 4 | geo:province:yunnan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 楚雄彝族自治州 | 3 | geo:province:yunnan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 玉溪市 | 3 | geo:province:yunnan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 红河哈尼族彝族自治州 | 3 | geo:province:yunnan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 红河州蒙自市 | 1 | geo:province:yunnan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 西双版纳傣族自治州 | 1 | geo:province:yunnan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 北京 | 东城区 | 3 | geo:province:beijing | urban:city:beijing | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 丰台区 | 8 | geo:province:beijing | urban:city:beijing | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 大兴区 | 8 | geo:province:beijing | urban:city:beijing | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 密云区 | 1 | geo:province:beijing | urban:city:beijing | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 延庆区 | 2 | geo:province:beijing | urban:city:beijing | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 怀柔区 | 4 | geo:province:beijing | urban:city:beijing | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 房山区 | 5 | geo:province:beijing | urban:city:beijing | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 昌平区 | 14 | geo:province:beijing | urban:city:beijing | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 朝阳区 | 19 | geo:province:beijing | urban:city:beijing | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 海淀区 | 39 | geo:province:beijing | urban:city:beijing | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 石景山区 | 4 | geo:province:beijing | urban:city:beijing | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 西城区 | 3 | geo:province:beijing | urban:city:beijing | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 通州区 | 10 | geo:province:beijing | urban:city:beijing | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 顺义区 | 2 | geo:province:beijing | urban:city:beijing | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 吉林 | 吉林市 | 9 | geo:province:jilin | - | low_confidence_or_missing_mapping, urban_tier_unmatched |
| 吉林 | 四平市 | 4 | geo:province:jilin | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 吉林 | 延边朝鲜族自治州 | 3 | geo:province:jilin | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 吉林 | 松原市 | 1 | geo:province:jilin | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 吉林 | 梅河口市 | 1 | geo:province:jilin | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 吉林 | 白城市 | 3 | geo:province:jilin | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 吉林 | 白山市 | 1 | geo:province:jilin | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 吉林 | 辽源市 | 1 | geo:province:jilin | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 吉林 | 通化市 | 2 | geo:province:jilin | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 乐山市 | 3 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 内江市 | 4 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 凉山彝族自治州 | 3 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 南充市 | 5 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 宜宾 | 1 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 宜宾市 | 4 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 巴中市 | 1 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 广元市 | 3 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 广安市 | 1 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 德阳市 | 10 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 攀枝花 | 2 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 攀枝花市 | 1 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 泸州市 | 7 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 甘孜藏族自治州 | 2 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 眉山市 | 5 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 自贡市 | 3 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 资阳市 | 3 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 达州市 | 3 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 遂宁市 | 1 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 阆中市 | 1 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 阿坝藏族羌族自治州 | 2 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 雅安市 | 2 | geo:province:sichuan | - | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 天津 | 东丽区 | 3 | geo:province:tianjin | urban:city:tianjin | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 北辰区 | 8 | geo:province:tianjin | urban:city:tianjin | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 南开区 | 2 | geo:province:tianjin | urban:city:tianjin | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 和平区 | 1 | geo:province:tianjin | urban:city:tianjin | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 宝坻区 | 2 | geo:province:tianjin | urban:city:tianjin | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 武清区 | 1 | geo:province:tianjin | urban:city:tianjin | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
