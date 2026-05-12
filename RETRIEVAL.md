# 系统检索机制说明

本文档说明当前 `gaokaollm-v2` 系统如何产生候选结果、检索证据，以及 v2 主 Agent 与补充的 v1 风格 RAG 基线之间的边界。

## 结论

当前系统存在一些分散说明，但在新增本文档之前，没有一份专门讲解“系统如何进行检索”的入口文件。相关分散材料包括：

- `gaokaollm_bench/outputs/thesis_system_architecture_algorithms.md`：论文架构与算法母版，说明数据层、确定性证据探针和各类放宽算法。
- `gaokaollm_bench/README.md`：说明业务 Agent 的多角色流程，以及 `v1_hybrid_rag` 是补充的软约束 RAG 基线。
- `db/README.md`：说明 PostgreSQL + pgvector 数据库、核心表和 `knowledge_documents` 知识库表。
- `gaokaollm_bench/sandbox/v1_hybrid_rag.py`：实现 v1 风格混合检索基线。

本文档作为开发者检索入口，集中描述线上业务 Agent 和补充 RAG baseline 的实际检索链路。

## v2 主 Agent 的检索链路

v2 主 Agent 不是让大模型直接检索或生成学校、专业、分数、位次等事实候选。它采用轻量 MAS / 多角色 Agent 流程：

```text
semantic_normalizer -> gatekeeper -> radar planner -> deterministic probes -> negotiator
```

论文口径对应为：

```text
前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器
```

核心原则是：LLM 可以做意图归一、探针规划、解释顺序建议和澄清提示，但事实候选只能来自 PostgreSQL 与标准化证据层查询。

### 1. 语义归一

入口：`app/graphs/nodes/semantic_normalizer.py`

该节点读取用户最新话语，输出：

- `rewritten_query`
- `intent_axes`
- `ambiguities`
- `clarification_hint`

它只归一化用户显式输入，不读取或输出 benchmark hidden fields，例如 `implicit_flexibilities`、`volunteer_set`、`axis_flexibilities`。

### 2. 约束抽取与硬约束 baseline

入口：`app/graphs/nodes/gatekeeper.py`

该节点从用户话语中抽取结构化约束：

- 分数：`score`
- 省份和城市：`province`、`city`
- 专业：`major`
- 选科：`selected_subjects`
- 预算：`budget`
- 风险偏好：`risk_preference`
- 学科实力或就业偏好：`strength`、`employment_preference`

当必要约束齐全后，调用 `app/flows/probers.py` 中的 `run_baseline()` 查询当前硬约束下的候选。baseline 是后续判断“是否存在可谈判空间”的锚点。

### 3. 机会规划

入口：`app/graphs/nodes/radar.py`

`radar` 会根据显式约束、baseline 数量、分数浪费和归一化意图轴生成 `probe_plan`。LLM 只允许选择要调用哪些确定性探针，不允许生成事实候选。

可规划的探针包括：

- `major_geo_relax`
- `risk_band_relax`
- `tuition_value_relax`
- `major_quality_relax`
- `employment_outcome_relax`
- `region_tree_relax`
- `strength_relax`
- `geo_relax`
- `city_relax`
- `major_relax`

### 4. 确定性证据探针

入口：`app/flows/probers.py`

这是 v2 主 Agent 的事实候选来源。探针通过 SQL 查询 PostgreSQL 快照和标准化证据层，生成可审计的候选集合。主要数据来源包括：

- `admission_scores`：专业最低分、最低位次。
- `schools`：学校省份、城市、层次、排名等。
- `subject_requirements`：选科要求标准化。
- `admission_plans`：招生计划与学费。
- `score_rank_segments`：分数与位次换算。
- `school_major_quality_profiles`：学校-专业质量画像。
- `major_employment_outcome_profiles`：专业就业结果画像。
- 专业树与地域树 JSON：专业层级放宽、地理板块和城市层级放宽。

不同探针对应不同检索策略：

| 探针 | 检索目标 | 典型放宽方式 |
| --- | --- | --- |
| `run_baseline` | 当前显式硬约束下可达候选 | 不放宽 |
| `major_geo_relax` | 专业 + 地域联合放宽后的更高收益候选 | 放宽省份和专业层级 |
| `risk_band_relax` | 冲稳保组合 | 放宽“只求稳”的风险偏好 |
| `tuition_value_relax` | 学费小幅增加后的性价比候选 | 放宽预算窗口 |
| `major_quality_relax` | 综合学校-专业质量更强候选 | 使用质量画像比较 `quality_score` |
| `employment_outcome_relax` | 就业结果更强候选 | 使用就业画像比较 `outcome_score` |
| `region_tree_relax` | 地域层级可谈判候选 | 使用地理邻近树和城市层级树 |
| `strength_relax` | 学校-专业证据轴的窄口径实力候选 | 使用 `major_strength_rank` 或评级证据 |

`strength_relax` 与 `major_quality_relax` 是层级/扩展关系，而不是完全正交的两个偏好轴。`strength_relax` 只验证排名或评级型实力信号能否进入 Pareto 谈判闭环；`major_quality_relax` 覆盖其中一部分排名型证据，并进一步融合专业排名、学科评估、特色/重点专业和满意度等信号为 `quality_score`。论文叙事中应把二者归入同一类学校-专业质量/实力证据轴，优先把 `major_quality_relax` 作为综合画像主叙述对象。

### 5. 证据组织与回复

入口：`app/graphs/nodes/negotiator.py`

`negotiator` 接收 baseline、`pareto_opportunities`、`probe_plan` 和 `opportunity_rankings`，把真实候选组织成面向用户的谈判回复。回复中的学校、专业、最低分、位次、学费、质量、就业或地域节点证据都必须来自探针结果。

## v1 风格混合 RAG 基线

入口：`gaokaollm_bench/sandbox/v1_hybrid_rag.py`

`v1_hybrid_rag` 是补充基线，不是当前 v2 主 Agent 的主要检索方式。它用于比较“软约束 RAG / 冲稳保推荐系统”和“证据驱动 Pareto 谈判 Agent”的差异。

它的检索流程是：

```text
用户话语
  -> 显式意图归一
  -> 约束抽取
  -> PostgreSQL 关系过滤候选池
  -> embedding dense scoring
  -> chong / wen / bao 分段
  -> reranker 二阶段重排
  -> 输出分段候选
```

默认后端优先级：

- 如果配置了 `EMBEDDING_MODEL`，使用 OpenAI-compatible embedding 后端；否则尝试本地 BGE-M3。
- 如果配置了 `RERANKING_MODEL` 或 `RERANKER_MODEL`，使用 OpenAI-compatible rerank 后端；否则尝试本地 BCEmbedding reranker。

该基线会返回：

- `dense_retrieval_candidates`
- `second_stage_reranked_candidates`
- `risk_segments`
- `baseline_results`

它不会输出 v2 的 `pareto_opportunities`，也不进入七组正式实验主表。

## 数据库与 pgvector

数据库初始化见 `db/migrations/001_init_gaokao_schema.sql`，连接封装见 `app/core/db_pg.py`。

当前 v2 主 Agent 的候选检索主要依赖结构化 SQL 与标准化证据层。数据库中也定义了 `knowledge_documents.embedding vector(1536)` 及 HNSW 索引，用于承载 RAG 文本知识库；但在当前 v2 Pareto Agent 的事实候选生成中，学校、专业、分数、位次等候选仍以确定性探针查询结果为准。

## 代码入口速查

| 文件 | 作用 |
| --- | --- |
| `app/graphs/workflow.py` | LangGraph 节点编排 |
| `app/graphs/nodes/semantic_normalizer.py` | 用户显式话语归一 |
| `app/graphs/nodes/gatekeeper.py` | 约束抽取与 baseline 查询 |
| `app/graphs/nodes/radar.py` | 探针规划与机会触发 |
| `app/flows/probers.py` | SQL 探针与候选检索核心 |
| `app/graphs/nodes/negotiator.py` | 候选证据组织与谈判回复 |
| `app/core/db_pg.py` | PostgreSQL 异步连接和查询封装 |
| `gaokaollm_bench/sandbox/v1_hybrid_rag.py` | v1 风格混合 RAG baseline |
| `db/migrations/001_init_gaokao_schema.sql` | 数据库表、索引和 pgvector schema |

## 边界

- v2 主 Agent 的事实候选只能来自 PostgreSQL / 标准化证据层 / 专业树 / 地域树。
- LLM 不直接生成学校、专业、分数、位次、学费、就业排名或地域节点等事实候选。
- benchmark hidden fields 只用于 simulator / evaluator，不进入 target Agent 输入。
- `v1_hybrid_rag` 是补充检索基线，用于对照，不代表 v2 主 Agent 的事实候选生成方式。
