# 动态决策考量可行性矩阵与实验路线图

本文档用于补充 `gaokaollm_bench/放宽与跃迁.md`：它不继续扩展审计，不新增实验结论，也不改 Agent 或 benchmark 代码，而是把高考志愿场景中的动态决策考量重新分层。目标是回答三个问题：

1. 哪些用户偏好已经被当前 Agent+Benchmark 闭环验证。
2. 哪些偏好由当前 PostgreSQL 快照强支撑，适合成为下一项实验。
3. 哪些偏好虽然真实存在，但当前缺少可核验证据，不能直接写成已可评测 Pareto 放宽。

## 1. 分类框架

高考志愿咨询中的“放宽”不应被理解成无条件劝用户降低要求。更稳妥的分类方式是把决策变量拆成四层：

| 层级 | 定义 | 当前处理原则 | 例子 |
|---|---|---|---|
| 硬约束 | 不应被 Agent 主动突破的事实或资格条件 | 默认不放宽，只用于过滤候选 | 分数、位次、选科、批次、学历层次 |
| 可谈判偏好 | 用户可能因证据充分而改变的初始偏好 | 可生成冰山画像并做多轮谈判 | 专业、地域、风险、预算、学科实力、就业导向 |
| 证据维度 | 判断放宽是否带来收益的可核验数据 | 必须来自 PostgreSQL 或明确产物 | 最低分、最低位次、学校 tier/ranking、风险层级、学费、就业画像、学科实力、多年稳定性 |
| 谈判动作 | Agent 在对话中可以采取的操作 | 必须留下 transcript 证据 | 约束放宽、替代专业、组合重排、证据校准、追问澄清 |

因此，论文中不宜把“用户可能关心的因素”直接等同于“已实现的动态放宽能力”。只有当某个因素同时满足以下条件时，才适合作为 Agent+Benchmark 实验：有真实数据、能构造 baseline-vs-relaxed gap、能在对话中表达成证据、能被 deterministic judge 或 LLM judge 验证。

## 2. 当前实验证明

当前已经形成三条闭环，其中前两条是论文主实验，第三条是扩展实验。

| 实验 | 决策考量 | Agent 能力 | 结果口径 | 论文定位 |
|---|---|---|---|---|
| `major_geo_v1` | 专业与地域联合放宽 | `major_geo_relax` | `app_pareto 0.900 / 0.900 / 0.000 / 5.20` vs `hard_constraint 0.000 / 0.000 / 0.000 / 7.00` | 主实验 |
| `risk_band_v1` | 风险偏好与冲稳保组合 | `risk_band_relax` | `app_pareto 1.000 / 3.000 / 0.000 / 5.00` vs `hard_constraint 0.000 / 0.000 / 0.000 / 15.00` | 主实验 |
| `school_strength_v1` | 学科/学校实力证据放宽 | `strength_relax` | `app_pareto 1.000 / 15.000 / 0.000 / 5.00` vs `hard_constraint 0.000 / 0.000 / 0.000 / 11.00` | 扩展实验 |

这三组结果说明，Pareto gain 不只来自学校层次提升。`risk_band_relax` 证明“志愿组合质量”也可以成为收益，`strength_relax` 证明“证据更强的学校/学科实力”也可以成为收益。但它们都依赖可审计证据，而不是泛泛劝说。

## 3. 可行性矩阵

| 状态 | 决策考量 | 数据支撑 | 是否适合做 benchmark | 推荐处理 |
|---|---|---|---|---|
| 已闭环 | 专业+地域联合放宽 | `admission_scores`、`schools`、专业树、学校 tier/ranking | 是 | 保持为主实验，不再无限扩样前先写清失败样本 |
| 已闭环 | 风险偏好放宽 | `admission_scores.min_score`、`min_rank`、`score_rank_segments` | 是 | 保持为主实验，后续可升级概率化风险模型 |
| 已闭环 | 学科实力放宽 | `school_major_strengths`、`admission_scores`、`schools` | 是 | 作为扩展实验，后续补专业级映射 |
| 可直接开发 | 学费/预算性价比放宽 | `admission_plans.tuition` 覆盖高，且可与录取分表 join | 是 | 下一项推荐做 `tuition_value_relax` |
| 可直接开发 | 多年稳定性风险增强 | 多年份 `admission_scores`、`school_admission_scores`、`batch_lines` | 是 | 适合作为 `risk_band_relax` 的增强版 |
| 可直接开发 | 就业导向放宽 | `major_employment_profiles` 可与大量录取分记录按 `major_id` join | 有条件 | 推荐先做字段规范，再做 `employment_outcome_relax` |
| 需数据清洗 | 城市偏好 | `schools.city` 覆盖高，但缺少城市质量/机会收益指标 | 暂不适合 | 先定义城市收益证据，不要只凭 city 字段做跃迁 |
| 需数据清洗 | 专业级学科实力 | `school_major_strengths` 数据多，但与录取专业存在映射噪声 | 有条件 | 先清洗 `major_id` / `discipline_name` 映射 |
| 仅展望 | 城市生活质量 | 当前库缺少生活成本、交通、气候等证据 | 否 | 只写局限性或外部数据扩展 |
| 仅展望 | 家庭距离 | 当前库缺少家庭位置和通勤距离证据 | 否 | 只写展望，不能作为当前实验 claim |
| 仅展望 | 校园文化 | 当前库缺少社团、校园氛围、满意度细节 | 否 | 可进入真实用户研究，不进入当前 DB benchmark |
| 仅展望 | 个人兴趣匹配 | 当前库缺少稳定兴趣测评和职业测评数据 | 否 | 可作为 v3 用户画像方向 |

这里的分层有一个底线：如果某个因素不能在 transcript 中落成“学校/专业/分数/位次/费用/排名/就业画像”等具体证据，就不应进入当前论文主实验。

## 4. 实验经验教训

`major_geo_relax` 的价值在于证明“联合放宽”比单独放宽更接近真实咨询。用户经常不是只卡一个条件，而是同时卡专业、地域、风险或预算。`major_geo_v1` 的唯一失败样本 `real-db-set-浙江-569-009` 也说明，放宽阶段选择本身需要被评估：Agent 如果停在较近专业阶段，可能错过隐藏画像要求的更远 `any_major` 集合。

`risk_band_relax` 的价值在于把 v1 的 `1:3:9` 冲稳保工程策略升级为可评测闭环。它证明 Pareto gain 可以来自组合完整性，而不一定来自单个学校 tier 变高。这个结论对论文很重要，因为志愿填报的真实目标往往是组合风险结构，而不是只追求一个最高层次学校。

`strength_relax` 能跑通，但需要克制表述。当前实现采用学校级最佳 `major_ranking` 作为实力证据，这是基于当前数据快照的合理第一版；但它还不是严格的“专业-学校-学科”一一映射。论文中应称为学科/学校实力扩展实验，并把专业级标准映射写入后续工作。

`city_relax` 不能简单写成“城市跃迁”。当前 DB 有 `schools.city` 字段，但没有城市质量、就业机会、生活成本、家庭距离等可核验收益指标。只要没有收益指标，跨城市就只是搜索范围变化，不一定构成 Pareto gain。因此 city 方向应先做证据定义，而不是直接做 Agent-vs-Baseline 实验。

## 5. 下一项实验建议

优先推荐 `tuition_value_relax`。原因是当前 `admission_plans.tuition` 覆盖度高，且与 `admission_scores` 在同校、同专业、同年份上有较多 join 结果，足以构造真实 DB gap。它可以建模一类很真实的冰山画像：用户显性预算保守，隐藏条件是“如果小幅增加学费可以换到更高层次学校、更好风险结构或更强实力证据，可以接受”。

建议的 `tuition_value_relax` 目标不是鼓励用户无上限加钱，而是评估“预算边界是否可被证据化谈判”。可行的候选收益包括：同一专业下学校 tier/ranking 改善、风险层级更完整、最低分/位次仍可达、学费增量可解释。baseline 只保留原预算内候选，`app_pareto` 则展示小幅放宽预算后的可达收益。

备选是 `employment_outcome_relax`。当前 `major_employment_profiles` 有就业排名、行业、城市、岗位和薪资画像，并且能与大量录取分记录按 `major_id` 关联。但该方向需要先规范 JSON 字段和证据表达，例如薪资分布取哪个统计量、就业城市如何与学校所在地关系区分、就业排名文本如何转成可比较指标。因此它适合作为第二优先级。

暂不推荐立刻做 city 质量实验。除非先引入或构造可核验的城市收益指标，例如就业城市分布、产业匹配度、生活成本、通勤距离或家庭距离，否则 city 只能作为过滤条件，不能可靠地成为 Pareto gain。

## 6. 论文写法建议

论文主线应保持克制：主贡献仍是 Benchmark 与 Agent，而不是穷尽所有高考志愿偏好。当前已经可以写成：

> 本文提出的 Agent+Benchmark 框架不是把所有用户偏好一次性实现为规则，而是提供一种可扩展的验证流程：先判断某个偏好是否能由真实数据库形成可核验 gap，再生成冰山画像，最后通过多轮沙盒和事实/过程联合评价验证 Agent 是否能触发 Pareto 妥协。

在论文局限性中，应明确：

- 已闭环：`major_geo_relax`、`risk_band_relax`、`strength_relax`。
- 可直接开发：`tuition_value_relax`、多年稳定性风险增强、`employment_outcome_relax`。
- 需数据清洗：城市偏好、专业级学科实力映射。
- 仅展望：城市生活质量、家庭距离、校园文化、个人兴趣匹配。

这种写法比继续罗列“还有很多因素没做”更强，因为它给出了判断标准：不是所有真实偏好都适合当前 DB benchmark，只有能形成可核验证据链的因素才进入实验闭环。

## 7. 可复现依据

本文档引用当前已有产物：

- `gaokaollm_bench/放宽与跃迁.md`
- `gaokaollm_bench/outputs/agent_benchmark_major_geo_v1/summary.json`
- `gaokaollm_bench/outputs/agent_benchmark_risk_band_v1/summary.json`
- `gaokaollm_bench/outputs/agent_benchmark_school_strength_v1/summary.json`
- `gaokaollm_bench/outputs/thesis_method_experiment_chapters.md`
- `gaokaollm_bench/outputs/thesis_agent_benchmark_contribution.md`

本文档不替代正式实验报告；它的作用是为后续开发排序，并为论文“局限性与后续工作”提供一套可解释的判定框架。
