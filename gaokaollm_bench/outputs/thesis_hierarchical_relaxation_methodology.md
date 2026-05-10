# 层级放宽方法论：专业树与地域树设计

本文档用于支撑毕业论文中“层级放宽方法”和“Human-in-the-loop 标注设计”的论述。它把已经完成的专业树方法总结为可写入论文的方法贡献，并说明地域树如何从设计方案推进到 reviewed v1 数据层与 `region_tree_v1` 扩展实验。

本文不新增实验结论，只整理当前已有产物。当前专业树 `major_tree_final_reviewed.json` 已支撑 `major_geo_relax` 主实验；地域树也已从 v0 数据标准化层推进到 `region_geo_tree_reviewed_v1.json`、`region_urban_tier_tree_reviewed_v1.json`，并完成 `region_tree_v1` 扩展实验。当前论文事实入口为 `thesis_document_hub.md` 与 `thesis_claims_manifest.json`，统一口径是七组实验：主实验 `major_geo_v1 + risk_band_v1`，五组扩展实验包括 `region_tree_v1`。

## 1. 为什么层级树适合做动态放宽

高考志愿咨询中的“放宽”不是简单删除条件。用户说“只想读临床医学”“只考虑浙江”“不想去太远的地方”时，Agent 如果直接把条件清空，会给出过宽、不可解释、甚至违背用户真实意图的候选。更合理的方式是将偏好组织成层级结构，然后按语义距离或决策距离逐级放宽。

层级树的价值在于：

| 价值 | 解释 | 对 Agent 的意义 |
| --- | --- | --- |
| 可解释 | 每一步放宽都有层级边界 | Agent 能说明“为什么这是相近专业/相邻地域” |
| 可控 | 从近到远逐步扩大候选 | 避免一下子退到无约束搜索 |
| 可审计 | 每个节点和挂载项可记录来源 | Benchmark 能复盘放宽是否合理 |
| 可交互 | 用户可以接受或拒绝某一级放宽 | 支撑 Human-in-the-loop 偏好澄清 |
| 可评测 | baseline 与 relaxed set 可按阶段构造 gap | 支撑冰山画像和 Pareto gain 评价 |

因此，专业树与地域树都不只是分类目录，而是面向志愿决策的“可解释层级放宽本体”。区别在于：专业树已经支撑主实验，地域树当前作为扩展实验证明 reviewed 数据层可以接入同一 Agent+Benchmark 闭环。

## 2. 专业树层级放宽方法

当前项目已经完成专业树构建与使用，核心产物为：

```text
gaokaollm_bench/outputs/major_tree_final_reviewed.json
```

该树服务三类任务：专业约束解析、层级放宽推荐、反事实志愿集合生成。它不是普通教育部专业目录的复制，而是基于真实招生数据库中的专业文本构建的工程化语义树。

### 2.1 专业树统计

当前最终 reviewed tree 的统计如下，与 `major_tree_methodology.md` 保持一致：

| 指标 | 数值 |
| --- | ---: |
| 节点数 | 82 |
| Level 0 大类节点 | 8 |
| Level 1 中层节点 | 22 |
| Level 2 叶子簇 | 52 |
| 叶子簇 observed_names 条目 | 19,096 |
| 全节点 observed_names 条目 | 57,287 |

这些统计说明，专业树既保留了人工定义的可解释层级，又覆盖了真实招生数据库中的大量专业名称变体。

### 2.2 标注与审校流程

专业树采用“人工本体 + 数据库扫描 + probe 辅助 + LLM/人工审校 + 最终审计”的混合流程。

```text
人工本体骨架
  -> PostgreSQL admission_scores.major_name_raw 扫描
  -> include/exclude 规则挂载 observed names
  -> probe 生成 top-k 候选
  -> LLM/人工审校低置信样本
  -> reviewed tree 与 audit artifact
```

| 阶段 | 输入 | 输出 | 作用 |
| --- | --- | --- | --- |
| 人工本体骨架 | `major_clusters.json` | Level 0/1/2 节点、关键词规则 | 定义可解释专业边界 |
| DB observed names 扫描 | `admission_scores.major_name_raw` | 已挂载与未挂载真实专业名 | 覆盖真实招生文本 |
| 规则挂载 | `include_keywords` / `exclude_keywords` | 初始 observed tree | 保守自动归类 |
| probe top-k 候选 | 4096 维 embedding 与 leaf 分类头 | 未归类项的候选叶子簇 | 提高低置信样本处理效率 |
| LLM/人工审校 | 低置信候选及候选标签 | reviewed assignments | 避免 probe 置信度直接污染最终树 |
| 最终审计合成 | observed tree + reviewed candidates | `major_tree_final_reviewed.json` 与 audit | 保留可追溯产物 |

这个流程的关键不是让模型自动生成一棵树，而是让自动化只承担候选生成和低置信辅助审校，最终边界仍回到可审计本体。

### 2.3 专业树如何支撑 `major_geo_relax`

`major_geo_relax` 是当前论文主实验 `major_geo_v1` 的核心算法之一。它在保留分数、选科、预算等硬约束的前提下，同时放宽地域和专业偏好。专业树提供了专业放宽的 staged relaxation 路径。

| 阶段 | 放宽范围 | 含义 |
| --- | --- | --- |
| Stage 1 | 同叶子或近邻专业 | 保持高度相似专业方向 |
| Stage 2 | 同父类专业 | 在同一专业类内部扩展 |
| Stage 3 | 相关大类或人工定义近邻 | 扩展到仍可解释的相关方向 |
| Stage 4 | probe 邻居大类 | 用模型辅助发现语义近邻 |
| Stage 5 | `any_major` | 当前专业约束无法产生可用 gap 时的最宽兜底 |

这一机制使 Agent 能向用户解释：“不是完全放弃专业偏好，而是从最接近的专业开始试探；如果没有足够收益，再逐步扩大范围。”这比直接去掉专业限制更符合真实咨询中的协商过程。

当前 `major_geo_v1` 已经完成主实验，`app_pareto` 指标为 `0.900 / 0.900 / 0.000 / 5.20`，`hard_constraint` 为 `0.000 / 0.000 / 0.000 / 7.00`。其中唯一失败样本 `real-db-set-浙江-569-009` 也说明了分层放宽策略本身需要被评估：如果 Agent 停在较近阶段，而 hidden volunteer set 需要更远的 `any_major`，则不会被 judge 判为成功。

## 3. 地域树是否可以类比专业树

地域放宽可以借鉴专业树的思想，但不能简单复制。专业相近性主要来自语义和学科边界，而地域相近性至少有两种不同含义：

1. **地理距离或行政地块相近**：例如江浙沪、华东、长三角、临近省份、不想离家太远。
2. **城市发展层级或繁华程度相近**：例如一线城市、新一线、强省会、就业机会更多、城市资源更好。

这两种偏好经常被用户混合表达。例如“想去好城市”通常更接近城市层级偏好；“别离家太远”更接近地理板块偏好；“江浙沪都可以，但不想去偏远城市”则同时涉及两棵树。因此，地域放宽不宜设计成一棵单一树，而更适合设计成两棵正交树。

## 4. `region_geo_tree`：地理邻近树

`region_geo_tree` 用于表示地理位置、行政地块和距离感知上的层级关系。

建议层级如下：

```text
全国
  -> 大区 / 地理板块
    -> 省份
      -> 城市 / 都市圈
```

可选节点示例：

| 层级 | 示例 | 适用用户表达 |
| --- | --- | --- |
| 全国 | 全国范围 | “哪里都可以” |
| 大区/地理板块 | 华东、华南、华北、西南、长三角、珠三角 | “江浙沪都行”“华东可以考虑” |
| 省份 | 浙江、江苏、上海、安徽 | “只想浙江”“可以去江苏” |
| 城市/都市圈 | 杭州、宁波、南京、上海、苏州、长三角核心城市 | “杭州周边”“离家近一点” |

`region_geo_tree` 的放宽路径可以设计为：

```text
同城市
  -> 同都市圈或相邻城市
  -> 同省
  -> 相邻省份或同地理板块
  -> 全国
```

该树适合处理“近不近”的问题。它不应该直接判断城市好坏，也不应该将地理近邻等同于就业收益。

## 5. `region_urban_tier_tree`：城市层级树

`region_urban_tier_tree` 用于表示城市发展机会、资源密度和繁华程度。它与地理树正交：上海和杭州在地理上属于长三角，但在城市层级上可能属于不同节点；成都与杭州地理距离较远，但都可能被用户视为“较好的大城市”。

建议层级如下：

```text
城市发展层级
  -> 一线城市
  -> 新一线城市
  -> 强省会 / 强经济城市
  -> 普通省会 / 区域中心
  -> 普通地级市
  -> 县域或低线城市
```

可选证据字段包括：

| 证据 | 当前状态 | 是否可直接进入实验 |
| --- | --- | --- |
| `schools.city` | 当前 DB 已有 | 只能作为城市实体，不能单独表示繁华程度 |
| 城市层级标签 | 需要人工或外部数据标准化 | 标准化后可用 |
| 就业机会/产业匹配 | 当前未形成城市级证据层 | 需要后续数据清洗 |
| 生活成本 | 当前缺少稳定数据 | 不适合当前实验 |
| 距离或交通时间 | 当前缺少用户家庭位置与交通数据 | 需要用户画像或外部数据 |

因此，`region_urban_tier_tree` 不能只凭 `schools.city` 包装成已实现 Pareto gain。它必须先有可审计的城市层级证据，例如人工标注、公开城市分级、就业机会指标或产业匹配指标。

## 6. 双树地域放宽策略

当前地域放宽已经以 `region_tree_relax` 形式完成最小扩展实验，内部包含两个子策略：

| 子策略 | 树结构 | 放宽对象 | 适用表达 |
| --- | --- | --- | --- |
| `geo_block_relax` | `region_geo_tree_reviewed_v1.json` | 地理距离、行政地块、相邻省市 | “别太远”“江浙沪”“华东可以” |
| `urban_tier_relax` | `region_urban_tier_tree_reviewed_v1.json` | 城市层级、资源密度、发展机会 | “想去大城市”“希望城市更繁华”“就业机会多一点” |

当用户表达清楚时，Agent 可以选择其中一棵树；当用户表达模糊时，应先进入在线 Human-in-the-loop 澄清，而不是擅自假设。

示例：

| 用户表达 | 建议处理 |
| --- | --- |
| “不想离家太远” | 优先 `geo_block_relax`，从同省/相邻省/同地理板块逐级放宽 |
| “想去更好的城市” | 优先 `urban_tier_relax`，但需要城市层级证据 |
| “江浙沪可以，但不要太偏” | 两棵树联合：先限定地理板块，再过滤城市层级 |
| “哪里就业好就去哪” | 不应直接用地域树，应优先走 `employment_outcome_relax` 或就业城市匹配增强 |

## 7. Human-in-the-loop 设计

地域树尤其需要 Human-in-the-loop，因为“近”“繁华”“发展机会”不是单一事实字段，且不同家庭对这些词的理解不同。HITL 应分为离线标注审校和在线偏好澄清两层。

### 7.1 离线 HITL：树与证据层标注

离线流程建议如下：

```text
人工定义地域树骨架
  -> 扫描 DB 中 schools.province / schools.city
  -> 自动挂载省份与城市
  -> 标记低置信或争议城市
  -> 人工 review queue 审校
  -> 输出 reviewed region tree 与 audit
```

产物应保留以下字段：

| 字段 | 作用 |
| --- | --- |
| `node_id` | 树节点唯一标识 |
| `label` | 节点名称 |
| `parent` | 父节点 |
| `tree_type` | `geo` 或 `urban_tier` |
| `source` | 数据来源，如 DB、人工、外部城市分级 |
| `mapping_rule` | 挂载规则 |
| `confidence` | 挂载置信度 |
| `review_status` | `auto_assigned`、`needs_review`、`reviewed` |
| `reviewer_note` | 人工审校说明 |

这种设计与专业树保持一致：自动化负责覆盖和候选生成，人工负责边界确认和争议处理。

### 7.2 在线 HITL：偏好澄清

在线 Agent 不应在用户表达模糊时擅自选择地域树。例如用户说“想去好一点的地方”，这可能表示城市层级、学校层次、就业机会，也可能只是生活环境。此时 Agent 应先追问：

```text
你说的“好一点的地方”，更看重离家近，还是城市发展机会和就业资源？
```

澄清后的策略：

| 用户回答 | Agent 策略 |
| --- | --- |
| 更看重离家近 | 使用 `region_geo_tree` |
| 更看重大城市资源 | 使用 `region_urban_tier_tree` |
| 两者都看重 | 先按地理树限定范围，再按城市层级排序或过滤 |
| 不确定 | 给出两组小样本证据，让用户选择方向 |

这也是论文中可以强调的 human-in-the-loop：用户不是被动接受 Agent 的放宽路线，而是在关键模糊点参与选择放宽维度。

### 7.3 Benchmark HITL 边界

Benchmark 可以把地域树偏好写入 persona hidden fields，但被测 Agent 不能读取这些 hidden fields。Agent 只能看到用户显式话语和 PostgreSQL/地域树标准化层查询结果。

也就是说：

```text
Agent 可见：
  用户话语
  PostgreSQL 查询结果
  reviewed region tree / standardized region evidence

Evaluator 可见：
  implicit_flexibilities
  volunteer_set
  hidden accepted region stage
```

该边界与当前 `major_geo_v1`、`risk_band_v1` 一致，避免信息泄漏。

## 8. 地域树 v0/v1 数据层与扩展实验

当前项目已经新增地域树 v0 数据 artifact，并通过 HITL 回填形成 reviewed v1 seed。v1 reviewed 地域树已进入 `region_tree_relax` 最小 Agent+Benchmark 闭环，形成 `region_tree_v1` 扩展实验。需要注意的是，历史 coverage report 仍是数据质量报告，不是当前论文主结果表。

| 产物 | 作用 | 当前边界 |
| --- | --- | --- |
| `gaokaollm_bench/outputs/region_geo_tree.json` | 记录全国、大区/地理板块、省份、城市/都市圈的地理邻近层级 | v0 artifact，用于生成 reviewed v1 |
| `gaokaollm_bench/outputs/region_urban_tier_tree.json` | 记录一线、新一线、强省会、普通省会/重要地级市等城市层级 | 是人工/规则 v0 标注，需要继续审校，不等同于完整城市收益指标 |
| `gaokaollm_bench/outputs/region_tree_coverage_report.json` | 机器可读覆盖报告 | 记录 DB 城市、省份挂载和 review queue |
| `gaokaollm_bench/outputs/region_tree_coverage_report.md` | 论文/开发可读覆盖报告 | 说明未匹配、低置信和人工审校建议 |
| `gaokaollm_bench/outputs/region_tree_review_packet.csv/jsonl` | HITL 审校包 | 给人工补充 geo/urban 挂载、置信度和 reviewer note |
| `gaokaollm_bench/outputs/region_geo_tree_reviewed_v1.json` / `region_urban_tier_tree_reviewed_v1.json` | v1 reviewed seed | 支撑 `geo_block_relax`、`urban_tier_relax` 和 `region_tree_v1` 扩展实验 |
| `gaokaollm_bench/outputs/region_tree_v1_coverage_report.md/json` | v0/v1 覆盖对比报告 | 验证数据层覆盖提升，作为数据质量报告保留 |
| `gaokaollm_bench/outputs/agent_benchmark_region_tree_v1_summary.md` | `region_tree_v1` 聚合结果 | `app_pareto 1.000 / 1.000 / 0.000 / 3.00` vs `hard_constraint 0.000 / 0.000 / 0.000 / 11.00` |
| `gaokaollm_bench/outputs/agent_benchmark_region_tree_v1_evidence.md` | `region_tree_v1` 逐例证据 | 记录每个成功 case 的学校、城市、地域树节点、最低分/位次和放宽策略 |

覆盖检查脚本只读取 PostgreSQL `schools.province` / `schools.city`，不启动 LLM，也不重跑 benchmark。当前报告摘要如下：

| 指标 | 数值 |
| --- | ---: |
| DB 中省份-城市组合数 | 414 |
| 覆盖学校数 | 3,219 |
| DB 中省份数 | 35 |
| 已挂载省份数 | 29 |
| 地理树可挂载城市组合数 | 395 |
| 地理树高置信城市组合数 | 12 |
| 城市层级树可挂载城市组合数 | 72 |
| 城市层级树高置信城市组合数 | 71 |
| review queue 条目 | 404 |

这些数字的含义是：地理树已经能通过省份或少量城市节点覆盖大部分学校所在地，但城市层级树仍然需要更充分的人工审校和证据补充。`review_queue_count = 404` 说明 v0 数据层仍然粗糙，因此后续 HITL 审校仍有价值；但这不再意味着地域树完全不能进入 Agent+Benchmark。当前 `region_tree_v1` 已证明 reviewed v1 seed 可以支撑最小扩展实验。

当前已进一步生成 v1 HITL seed：审校包包含 404 条 review queue，规则优先回填 50 条高优先级样本，v1 报告中 `review_queue_count` 从 404 降到 353，`urban_city_pair_mapped_count` 从 72 提升到 123。该流程证明地域树可以沿着“v0 自动挂载 -> HITL 审校包 -> v1 reviewed artifact -> 覆盖对比报告 -> `region_tree_v1` 扩展实验”的路线推进。v1 seed 仍不是最终人工审校完成版，因此 `region_tree_v1` 应定位为扩展实验，不替代主实验。

## 9. 地域树扩展实验与后续增强

地域树已经完成最小数据 + Agent + Benchmark 扩展实验。后续重点不再是“实现 `region_tree_relax`”，而是提升地域树数据质量、增强城市收益证据和优化在线偏好澄清。

| 阶段 | 目标 | 产物 |
| --- | --- | --- |
| 已完成数据层 | v0 自动挂载、review packet、reviewed v1 seed、覆盖对比报告 | `region_geo_tree_reviewed_v1.json`、`region_urban_tier_tree_reviewed_v1.json` |
| 已完成 Agent 层 | `region_tree_relax`，包含 `geo_block_relax` 与 `urban_tier_relax` | 候选包含学校、省份、城市、地域树节点、最低分/位次和树置信度 |
| 已完成 Benchmark 层 | 地域树冰山画像和 deterministic judge | `iceberg_personas_region_tree_real_db_10.json`、`agent_benchmark_region_tree_v1/` |
| 已完成 Evidence 层 | 逐例证据附录 | `agent_benchmark_region_tree_v1_evidence.md` |
| 后续增强 | 继续 HITL 审校、城市收益指标证据、在线偏好澄清质量 | 不把城市层级直接写成就业、生活成本或生活质量收益 |

当前 `region_tree_v1` 的论文定位是：扩展实验，用于证明 reviewed 地域树可以接入轻量 MAS 与沙盒评测。它不替代 `major_geo_v1 + risk_band_v1` 主实验，也不证明城市层级本身等价于就业机会、生活成本或生活质量收益。

## 10. 与当前论文主线的关系

当前论文仍以“数据 + Agent + Benchmark”为主线。

| 内容 | 当前状态 | 论文放置建议 |
| --- | --- | --- |
| 专业树 | 已完成并支撑 `major_geo_relax` | 写入数据贡献与算法方法 |
| `major_geo_v1` | 已完成主实验 | 写入实验主结果 |
| 地域树 | reviewed v1 数据层已建立，并完成 `region_tree_v1` 扩展实验 | 写入数据贡献、方法扩展和扩展实验 |
| Human-in-the-loop | 专业树已有离线审校实践，地域树提出离线+在线设计 | 写入方法论与后续工作 |

专业树可以作为已完成方法写实：它证明树结构可以将“放宽”变成可解释、可审计、可评测的阶段式算法。地域树则作为扩展方法写实：同样用树结构组织放宽路径，并通过 reviewed v1 seed 完成最小闭环；但它仍需要 Human-in-the-loop 持续解决用户意图模糊和城市收益证据不足的问题。

## 11. 可迁入论文的总结表述

可直接写入论文的方法总结如下：

> 本文将“约束放宽”设计为层级树上的可解释移动，而不是简单删除条件。专业偏好通过 reviewed 专业树实现从同叶子、同父类、相关大类到任意专业的阶段式放宽；地域偏好则通过地理邻近树和城市层级树两类正交结构，形成 `geo_block_relax` 与 `urban_tier_relax` 两种可审计放宽路径。前者回答“离家或原区域有多近”，后者回答“城市层级或资源密度如何变化”。在这类树结构中，Human-in-the-loop 的作用不是事后修补结果，而是参与定义树边界、审校低置信挂载项，并在用户表达模糊时选择放宽方向。这样，Agent 的妥协建议既保持事实可核验，又能避免无约束地扩大搜索空间。

## 12. 边界说明

本文档只整理方法论、v0/v1 数据层和已完成扩展实验，不新增 Agent/Benchmark 实验结果。

必须保留以下边界：

- `major_tree_final_reviewed.json` 与 `major_geo_relax` 是已完成主实验能力。
- `region_geo_tree_reviewed_v1.json` 与 `region_urban_tier_tree_reviewed_v1.json` 已支撑 `region_tree_v1` 扩展实验。
- `region_tree_coverage_report.md/json` 与 `region_tree_v1_coverage_report.md/json` 是历史/数据质量报告，不作为当前论文主口径事实源。
- `region_tree_review_packet.csv/jsonl` 证明 HITL 数据层可回填，后续仍可继续提高 reviewed 地域树质量。
- 当前 PostgreSQL 有 `province` / `city` 字段，但没有完整城市繁华程度、生活成本、就业机会等证据层。
- 地域树不能只凭 `schools.city` 包装成城市收益；`region_tree_v1` 的 Pareto gain 仍按学校 tier/ranking 改善计算。
- Agent 不读取 `implicit_flexibilities` 或 `volunteer_set`。
- `region_tree_v1` 是扩展实验，不替代 `major_geo_v1 + risk_band_v1` 主实验。
- 当前论文事实入口是 `thesis_document_hub.md` 与 `thesis_claims_manifest.json`。
