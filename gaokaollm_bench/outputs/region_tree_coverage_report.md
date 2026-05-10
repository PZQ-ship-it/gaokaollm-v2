# Region Tree v0 Coverage Report

本报告只验收地域树数据层覆盖情况，不表示 `region_tree_relax` 已进入 Agent 或 Benchmark 实验。

## Summary

| Metric | Value |
|---|---:|
| `total_city_pairs` | 414 |
| `total_schools` | 3219 |
| `province_count` | 35 |
| `province_mapped_count` | 29 |
| `geo_city_pair_mapped_count` | 395 |
| `geo_city_pair_high_confidence_count` | 12 |
| `urban_city_pair_mapped_count` | 72 |
| `urban_city_pair_high_confidence_count` | 71 |
| `review_queue_count` | 404 |

## Boundary

- 当前产物是 `region_geo_tree` 与 `region_urban_tier_tree` 的 v0 数据层。
- `region_tree_relax` 尚未实现，不进入当前六组实验结果表。
- 不能只凭 `schools.city` 包装城市收益或 Pareto gain。
- 未来 Agent 仍不能读取 `implicit_flexibilities` 或 `volunteer_set`。

## Review Queue

| Province | City | Schools | Geo node | Geo conf. | Urban node | Urban conf. | Reasons |
|---|---|---:|---|---:|---|---:|---|
| 上海 | 嘉定区 | 4 | geo:province:shanghai | 0.600 | urban:city:shanghai | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 奉贤区 | 6 | geo:province:shanghai | 0.600 | urban:city:shanghai | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 宝山区 | 6 | geo:province:shanghai | 0.600 | urban:city:shanghai | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 徐汇区 | 9 | geo:province:shanghai | 0.600 | urban:city:shanghai | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 普陀区 | 1 | geo:province:shanghai | 0.600 | urban:city:shanghai | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 杨浦区 | 11 | geo:province:shanghai | 0.600 | urban:city:shanghai | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 松江区 | 7 | geo:province:shanghai | 0.600 | urban:city:shanghai | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 浦东新区 | 21 | geo:province:shanghai | 0.600 | urban:city:shanghai | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 虹口区 | 3 | geo:province:shanghai | 0.600 | urban:city:shanghai | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 金山区 | 2 | geo:province:shanghai | 0.600 | urban:city:shanghai | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 长宁区 | 1 | geo:province:shanghai | 0.600 | urban:city:shanghai | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 闵行区 | 2 | geo:province:shanghai | 0.600 | urban:city:shanghai | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 青浦区 | 1 | geo:province:shanghai | 0.600 | urban:city:shanghai | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 静安区 | 3 | geo:province:shanghai | 0.600 | urban:city:shanghai | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 上海 | 黄浦区 | 1 | geo:province:shanghai | 0.600 | urban:city:shanghai | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 云南 | 临沧市 | 1 | geo:province:yunnan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 丽江市 | 3 | geo:province:yunnan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 保山市 | 2 | geo:province:yunnan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 大理白族自治州 | 4 | geo:province:yunnan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 德宏傣族景颇族自治州 | 2 | geo:province:yunnan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 文山壮族苗族自治州 | 2 | geo:province:yunnan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 昆明市 | 57 | geo:province:yunnan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 昭通市 | 2 | geo:province:yunnan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 普洱市 | 2 | geo:province:yunnan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 曲靖市 | 4 | geo:province:yunnan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 楚雄彝族自治州 | 3 | geo:province:yunnan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 玉溪市 | 3 | geo:province:yunnan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 红河哈尼族彝族自治州 | 3 | geo:province:yunnan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 红河州蒙自市 | 1 | geo:province:yunnan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 云南 | 西双版纳傣族自治州 | 1 | geo:province:yunnan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 内蒙古 | 乌兰察布市 | 3 | - | 0.000 | - | 0.000 | geo_province_or_city_unmatched, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 内蒙古 | 乌海市 | 1 | - | 0.000 | - | 0.000 | geo_province_or_city_unmatched, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 内蒙古 | 兴安盟 | 1 | - | 0.000 | - | 0.000 | geo_province_or_city_unmatched, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 内蒙古 | 包头市 | 7 | - | 0.000 | - | 0.000 | geo_province_or_city_unmatched, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 内蒙古 | 呼伦贝尔市 | 4 | - | 0.000 | - | 0.000 | geo_province_or_city_unmatched, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 内蒙古 | 呼伦贝尔市满洲里市 | 1 | - | 0.000 | - | 0.000 | geo_province_or_city_unmatched, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 内蒙古 | 呼和浩特市 | 25 | - | 0.000 | - | 0.000 | geo_province_or_city_unmatched, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 内蒙古 | 巴彦淖尔市 | 2 | - | 0.000 | - | 0.000 | geo_province_or_city_unmatched, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 内蒙古 | 赤峰市 | 5 | - | 0.000 | - | 0.000 | geo_province_or_city_unmatched, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 内蒙古 | 通辽市 | 3 | - | 0.000 | - | 0.000 | geo_province_or_city_unmatched, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 内蒙古 | 鄂尔多斯市 | 5 | - | 0.000 | - | 0.000 | geo_province_or_city_unmatched, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 内蒙古 | 锡林郭勒盟 | 1 | - | 0.000 | - | 0.000 | geo_province_or_city_unmatched, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 内蒙古 | 阿拉善盟 | 1 | - | 0.000 | - | 0.000 | geo_province_or_city_unmatched, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 北京 | 东城区 | 3 | geo:province:beijing | 0.600 | urban:city:beijing | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 丰台区 | 8 | geo:province:beijing | 0.600 | urban:city:beijing | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 大兴区 | 8 | geo:province:beijing | 0.600 | urban:city:beijing | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 密云区 | 1 | geo:province:beijing | 0.600 | urban:city:beijing | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 延庆区 | 2 | geo:province:beijing | 0.600 | urban:city:beijing | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 怀柔区 | 4 | geo:province:beijing | 0.600 | urban:city:beijing | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 房山区 | 5 | geo:province:beijing | 0.600 | urban:city:beijing | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 昌平区 | 14 | geo:province:beijing | 0.600 | urban:city:beijing | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 朝阳区 | 19 | geo:province:beijing | 0.600 | urban:city:beijing | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 海淀区 | 39 | geo:province:beijing | 0.600 | urban:city:beijing | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 石景山区 | 4 | geo:province:beijing | 0.600 | urban:city:beijing | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 西城区 | 3 | geo:province:beijing | 0.600 | urban:city:beijing | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 通州区 | 10 | geo:province:beijing | 0.600 | urban:city:beijing | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 北京 | 顺义区 | 2 | geo:province:beijing | 0.600 | urban:city:beijing | 0.950 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 吉林 | 吉林市 | 9 | geo:province:jilin | 1.000 | - | 0.000 | low_confidence_or_missing_mapping, urban_tier_unmatched |
| 吉林 | 四平市 | 4 | geo:province:jilin | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 吉林 | 延边朝鲜族自治州 | 3 | geo:province:jilin | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 吉林 | 松原市 | 1 | geo:province:jilin | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 吉林 | 梅河口市 | 1 | geo:province:jilin | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 吉林 | 白城市 | 3 | geo:province:jilin | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 吉林 | 白山市 | 1 | geo:province:jilin | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 吉林 | 辽源市 | 1 | geo:province:jilin | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 吉林 | 通化市 | 2 | geo:province:jilin | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 吉林 | 长春市 | 49 | geo:province:jilin | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 乐山市 | 3 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 内江市 | 4 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 凉山彝族自治州 | 3 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 南充市 | 5 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 宜宾 | 1 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 宜宾市 | 4 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 巴中市 | 1 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 广元市 | 3 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 广安市 | 1 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 德阳市 | 10 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 攀枝花 | 2 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 攀枝花市 | 1 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 泸州市 | 7 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 甘孜藏族自治州 | 2 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 眉山市 | 5 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 绵阳市 | 13 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 自贡市 | 3 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 资阳市 | 3 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 达州市 | 3 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 遂宁市 | 1 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 阆中市 | 1 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 阿坝藏族羌族自治州 | 2 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 四川 | 雅安市 | 2 | geo:province:sichuan | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 天津 | 东丽区 | 3 | geo:province:tianjin | 0.600 | urban:city:tianjin | 0.850 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 北辰区 | 8 | geo:province:tianjin | 0.600 | urban:city:tianjin | 0.850 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 南开区 | 2 | geo:province:tianjin | 0.600 | urban:city:tianjin | 0.850 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 和平区 | 1 | geo:province:tianjin | 0.600 | urban:city:tianjin | 0.850 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 宝坻区 | 2 | geo:province:tianjin | 0.600 | urban:city:tianjin | 0.850 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 武清区 | 1 | geo:province:tianjin | 0.600 | urban:city:tianjin | 0.850 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 河东区 | 9 | geo:province:tianjin | 0.600 | urban:city:tianjin | 0.850 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 河北区 | 3 | geo:province:tianjin | 0.600 | urban:city:tianjin | 0.850 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 河西区 | 5 | geo:province:tianjin | 0.600 | urban:city:tianjin | 0.850 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 津南区 | 8 | geo:province:tianjin | 0.600 | urban:city:tianjin | 0.850 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 滨海新区 | 8 | geo:province:tianjin | 0.600 | urban:city:tianjin | 0.850 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 蓟县 | 2 | geo:province:tianjin | 0.600 | urban:city:tianjin | 0.850 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 西青区 | 12 | geo:province:tianjin | 0.600 | urban:city:tianjin | 0.850 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 天津 | 静海区 | 6 | geo:province:tianjin | 0.600 | urban:city:tianjin | 0.850 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping |
| 宁夏 | 吴忠市 | 1 | geo:province:ningxia | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 宁夏 | 固原市 | 1 | geo:province:ningxia | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 宁夏 | 石嘴山市 | 2 | geo:province:ningxia | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 宁夏 | 银川市 | 17 | geo:province:ningxia | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 安徽 | 亳州市 | 2 | geo:province:anhui | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 安徽 | 六安市 | 5 | geo:province:anhui | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 安徽 | 安庆市 | 5 | geo:province:anhui | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 安徽 | 宣城市 | 2 | geo:province:anhui | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 安徽 | 宿州市 | 4 | geo:province:anhui | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 安徽 | 池州市 | 3 | geo:province:anhui | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 安徽 | 淮北市 | 5 | geo:province:anhui | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 安徽 | 淮南市 | 5 | geo:province:anhui | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 安徽 | 滁州市 | 4 | geo:province:anhui | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 安徽 | 芜湖市 | 12 | geo:province:anhui | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 安徽 | 蚌埠市 | 7 | geo:province:anhui | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 安徽 | 铜陵市 | 3 | geo:province:anhui | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 安徽 | 阜阳市 | 8 | geo:province:anhui | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 安徽 | 马鞍山市 | 6 | geo:province:anhui | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 安徽 | 黄山市 | 3 | geo:province:anhui | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 东营市 | 5 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 临沂市 | 5 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 威海市 | 9 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 德州市 | 4 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 日照市 | 4 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 枣庄市 | 3 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 泰安市 | 10 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 济南市 | 42 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 济宁市 | 6 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 淄博市 | 6 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 滨州市 | 3 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 潍坊市 | 17 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 烟台市 | 21 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 聊城市 | 4 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 荣成市 | 1 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 莱芜市 | 1 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 菏泽市 | 5 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 青岛市 | 28 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山东 | 高密市 | 1 | geo:province:shandong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山西 | 临汾市 | 6 | geo:province:shanxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山西 | 吕梁市 | 2 | geo:province:shanxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山西 | 大同市 | 4 | geo:province:shanxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山西 | 太原市 | 53 | geo:province:shanxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山西 | 忻州市 | 2 | geo:province:shanxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山西 | 晋中市 | 12 | geo:province:shanxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山西 | 晋城市 | 1 | geo:province:shanxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山西 | 朔州市 | 3 | geo:province:shanxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山西 | 运城市 | 7 | geo:province:shanxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山西 | 长治市 | 6 | geo:province:shanxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 山西 | 阳泉市 | 3 | geo:province:shanxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 东莞市 | 8 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 中山市 | 3 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 云浮市 | 2 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 佛山市 | 6 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 惠州市 | 5 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 揭阳市 | 2 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 梅州市 | 2 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 汕头市 | 5 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 汕尾市 | 1 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 江门市 | 5 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 河源市 | 1 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 清远市 | 3 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 湛江市 | 7 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 潮州市 | 2 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 珠海市 | 9 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 肇庆市 | 7 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 茂名市 | 5 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 阳江市 | 1 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广东 | 韶关市 | 2 | geo:province:guangdong | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广西 | 北海市 | 4 | geo:province:guangxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广西 | 南宁市 | 42 | geo:province:guangxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广西 | 崇左市 | 7 | geo:province:guangxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广西 | 来宾市 | 2 | geo:province:guangxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广西 | 柳州市 | 7 | geo:province:guangxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广西 | 桂林市 | 20 | geo:province:guangxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广西 | 梧州市 | 3 | geo:province:guangxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广西 | 河池市 | 2 | geo:province:guangxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广西 | 玉林市 | 2 | geo:province:guangxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广西 | 百色市 | 4 | geo:province:guangxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广西 | 贵港市 | 1 | geo:province:guangxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广西 | 贺州市 | 1 | geo:province:guangxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广西 | 钦州市 | 3 | geo:province:guangxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 广西 | 防城港市 | 1 | geo:province:guangxi | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 新疆 | 乌鲁木齐市 | 27 | geo:province:xinjiang | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 新疆 | 伊犁哈萨克自治州 | 3 | geo:province:xinjiang | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 新疆 | 克孜勒苏柯尔克孜自治州 | 1 | geo:province:xinjiang | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 新疆 | 克拉玛依市 | 3 | geo:province:xinjiang | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 新疆 | 博尔塔拉蒙古自治州 | 1 | geo:province:xinjiang | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 新疆 | 吐鲁番市 | 1 | geo:province:xinjiang | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 新疆 | 和田地区 | 3 | geo:province:xinjiang | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 新疆 | 哈密地区 | 1 | geo:province:xinjiang | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 新疆 | 喀什地区 | 2 | geo:province:xinjiang | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 新疆 | 图木舒克市 | 1 | geo:province:xinjiang | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 新疆 | 塔城地区 | 1 | geo:province:xinjiang | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 新疆 | 巴音郭楞蒙古自治州 | 3 | geo:province:xinjiang | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 新疆 | 昌吉回族自治州 | 3 | geo:province:xinjiang | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |
| 新疆 | 直辖县级市 | 2 | geo:province:xinjiang | 0.600 | - | 0.000 | geo_city_not_explicitly_mapped, low_confidence_or_missing_mapping, urban_tier_unmatched |

## Human Review Suggestions

1. 优先审校 `urban_tier_unmatched` 城市，确认是否需要加入城市层级树。
2. 对 `fallback_to_province_for_unlisted_city` 的地理挂载补充城市或都市圈节点。
3. 城市层级应保留 `source`、`mapping_rule`、`confidence` 和 `review_status`，避免把主观城市偏好伪装成事实收益。
