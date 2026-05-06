# gaokaollm-bench 方法学总结

## 摘要

`gaokaollm-bench` 是面向高考志愿决策 Agent 的自动化多轮交互评测框架。其核心研究对象不是静态问答正确率，而是被测系统在真实约束条件下是否能够发现用户表层偏好背后的可妥协空间，并通过可核验的反事实选项引导用户完成理性偏好更新。

传统静态测试集通常将用户需求视为一次性显式输入，而高考志愿咨询场景中，用户常常以“只留本省”“只读某专业”“不接受外省学校”等强硬表述进入对话。这些表述既可能是真实红线，也可能是信息不足下的初始锚定。`gaokaollm-bench` 因此采用“冰山画像数据生成 + 自动化双盲对战沙盒 + 多维过程打分”的设计，将评测目标从单轮答案质量扩展到多轮偏好启发、反事实证据呈现、事实底线校验和最终帕累托增益。

## 评测问题定义

本框架关注如下问题：

1. 被测 Agent 是否能够识别用户显性约束与隐性可妥协条件之间的差异。
2. 被测 Agent 是否能够用真实数据库中的学校、专业、分数和层次差异构造反事实选项。
3. 被测 Agent 是否避免用幻觉学校、错误分数或不可达志愿诱导用户妥协。
4. 被测 Agent 是否能在多轮交互中逐步启发偏好，而不是直接说教或机械推荐。
5. 被测 Agent 最终是否带来可度量的帕累托增益。

这里的帕累托增益主要指：在保持用户核心心理约束可接受的前提下，让用户从原始锚定方案跃迁到更高层次、更优学校或更优志愿集合。

## 总体架构

项目采用模块化结构：

```text
gaokaollm_bench/
  schemas.py
  data_gen/
  simulator/
  sandbox/
  evaluator/
  tests/
```

各模块职责如下：

| 模块 | 职责 |
| --- | --- |
| `schemas.py` | 定义跨模块流转的数据契约 |
| `data_gen/` | 从真实数据库和专业树中生成冰山画像 |
| `simulator/` | 扮演具有显性红线和隐性妥协条件的用户 |
| `sandbox/` | 将用户模拟器与被测 Agent 放入受控多轮对话 |
| `evaluator/` | 对完整对话进行事实校验与过程评分 |
| `tests/` | 以阶段化 TDD 方式验证框架行为 |

被测系统通过 `BaseTargetAgent` 抽象基类接入，接口为：

```python
async def chat(self, user_input: str) -> tuple[str, dict]
```

该接口将沙盒与业务系统解耦，使 benchmark 可以评测不同实现的推荐 Agent、规划 Agent 或对话系统。

## 数据契约

框架以 Pydantic 模型定义标准数据流。

### IcebergPersona

`IcebergPersona` 表示一个“冰山画像”。它包含：

- `case_id`：样本标识。
- `background`：考生背景，如分数、省份、选科、原始锚定学校或专业。
- `explicit_red_lines`：用户显性声明的死守红线。
- `implicit_flexibilities`：隐藏的妥协触发条件。
- `initial_utterance`：用户进入对话时的第一句话。
- `process_milestones`：评测过程中期望观察到的关键行为。

该设计将“用户说出口的偏好”和“用户在充分证据下可能接受的妥协”显式分离，是整个 benchmark 区别于静态测试集的关键。

### ConversationTurn

`ConversationTurn` 表示一轮可观察对话，包含：

- `turn_id`
- `role`
- `content`
- `internal_state`

其中 `role` 仅允许 `user` 或 `target_agent`。`internal_state` 用于记录用户模拟器是否被说服、被测系统内部候选、推荐学校、推理状态等过程变量。

### Transcript

`Transcript` 保存完整交互轨迹，由 `persona` 和 `turns` 组成。它是后续事实校验和 LLM 裁判的输入。

### EvalReport

`EvalReport` 表示最终评测结果，包含：

- `hallucination_rate`
- `elicitation_success`
- `pareto_gain`
- `judge_reasoning`

## 冰山画像生成

数据生成模块的目标不是凭空编写测试用例，而是从真实招生数据库中发现“约束放宽后发生跃迁”的断层，再逆向合成用户画像。

### 省份约束放宽

对于“坚持不出省”的用户，生成器比较：

1. 在原省份约束下可达的最好学校或志愿集合。
2. 放宽到全国范围后可达的最好学校或志愿集合。

如果放宽后学校层次发生跃迁，例如从普通本科到 211 或双一流，则形成一个真实 gap。该 gap 被编码进 `implicit_flexibilities`，使用户只有在看到具体学校名称和真实分数证据时才会动摇。

### 专业约束放宽

对于“坚持某专业”的用户，生成器支持多种专业放宽：

1. `major_any`：去除专业限制。
2. `major_clinical_to_medtech`：从临床医学放宽到医学技术类等相近方向。
3. `major_hierarchy`：基于专业树逐级放宽。

目前推荐的主路径是 `major_hierarchy`。它使用最终审校后的专业树：

```text
gaokaollm_bench/outputs/major_tree_final_reviewed.json
```

层级放宽策略为：

| Stage | 策略 | 含义 |
| --- | --- | --- |
| 1 | `same_leaf_variants` | 同叶子簇内的真实名称变体 |
| 2 | `sibling_leaf_clusters` | 同父节点下的近邻叶子簇 |
| 3 | `cousin_leaf_clusters` | 上一层大类内的其他分支 |
| 4 | `probe_neighbor_categories` | embedding + probe 找到的 3 个相邻 level-1 大类 |
| 5 | `any_major` | 去除专业限制 |

当某一层找到不少于 `--recommendation-threshold` 个跃迁志愿时，生成器停止继续放宽。这保证了“足够近的妥协”优先于“更远的妥协”。

### 志愿集合而非单一学校

早期原型将妥协目标建模为单一学校。后续版本改为志愿集合：

```text
volunteer_set = [volunteer_1, volunteer_2, ...]
```

每个志愿包含学校、专业、年份、最低分、分差、层次标签等字段。该改动更符合真实志愿填报任务，因为高考决策通常不是“接受一所学校”，而是在风险、偏好和可达性之间构造一组候选。

## 专业树与 probe 辅助

专业树构建过程另有详细记录：

```text
gaokaollm_bench/outputs/major_tree_methodology.md
```

简要而言，最终树来自以下流程：

1. 人工定义可审计专业本体骨架。
2. 扫描 `admission_scores.major_name_raw` 聚合真实专业名。
3. 使用规则匹配将专业名填入叶子簇。
4. 对未归类名称训练 embedding 线性 probe。
5. 对低置信候选使用 LLM 审校。
6. 生成最终树和审计文件。

在 benchmark 中，probe 不直接覆盖人工树，而是用于 Stage 4：当同大类内放宽仍不足以构造足量跃迁志愿时，probe 根据起始专业预测相邻专业叶子，再向上归并为 3 个 level-1 相邻大类，并展开这些大类下所有叶子参与推荐。

这一设计兼顾了两点：

1. 语义邻近性来自 embedding 与 probe 的泛化能力。
2. 最终推荐范围仍落在可审计专业树节点上，而不是不可解释的向量邻域。

## 用户模拟器

`UserSimulator` 是一个 LLM-backed stubborn user simulator。它输入 `IcebergPersona`，并在每轮收到被测系统回复后输出结构化 JSON：

```json
{
  "thought": "内部内心戏",
  "is_persuaded": false,
  "utterance": "对外口语化回复"
}
```

模拟器提示词明确规定：

1. 必须死守 `explicit_red_lines`。
2. 对空洞说教、泛泛建议、情绪安慰保持拒绝。
3. 只有当被测系统给出符合 `implicit_flexibilities` 的具体学校名称、专业和真实分数证据时，才允许被说服。

因此，模拟器不是简单的闲聊用户，而是带有隐藏状态和明确妥协触发条件的交互式评测环境。

## 沙盒对战

`run_episode` 负责运行多轮对话：

1. 将 `persona.initial_utterance` 发给被测 Agent。
2. 被测 Agent 返回回复和内部状态。
3. 用户模拟器根据回复更新 `is_persuaded` 并产生下一轮用户话语。
4. 达到 `max_turns` 或用户被说服时停止。
5. 将完整 `Transcript` 持久化为 JSON。

沙盒具有双盲属性：

- 被测 Agent 只能看到用户话语，不能直接读取隐性妥协条件。
- 用户模拟器知道完整画像，但只通过自然语言回应暴露状态。

这使评测更接近真实咨询过程：优秀系统需要通过提问、证据呈现和反事实比较逐步发现可妥协空间。

## 评价器

评价阶段由确定性裁判和 LLM 过程裁判组成。

### 确定性事实裁判

`check_hallucination` 从被测 Agent 的回复和内部状态中抽取学校名称，然后查询真实数据库：

```sql
SELECT
    s.name AS school_name,
    min(a.min_score) AS min_score
FROM admission_scores a
JOIN schools s ON s.id = a.school_id
WHERE s.name = %s
  AND a.min_score IS NOT NULL
GROUP BY s.name
ORDER BY min_score ASC
LIMIT 1
```

若学校不存在，或最低分高于考生分数，则记为幻觉或不可达推荐。最终输出：

```text
hallucination_rate = failed_mentions / total_mentions
```

该裁判用于约束推荐系统的事实底线，避免模型用虚假数据诱导用户妥协。

### LLM 过程裁判

`evaluate_process` 将完整画像和对话轨迹输入裁判模型，输出 `EvalReport`。裁判关注：

1. 是否成功启发隐藏偏好。
2. 是否只是空洞说教。
3. 是否给出足够具体的反事实证据。
4. 最终接受方案相对于原始锚定的层次增益。

其中 `pareto_gain` 表示最终接受层次与原始基线层次之间的差值。

## 指标体系

当前框架中的核心指标为：

| 指标 | 类型 | 解释 |
| --- | --- | --- |
| `hallucination_rate` | factual | 被测系统推荐中未通过数据库核验的比例 |
| `elicitation_success` | process | 是否成功引导用户暴露或接受隐性妥协条件 |
| `pareto_gain` | outcome | 最终方案相对原始锚定的层次增益 |
| `volunteer_count` | data generation | 当前样本中真实可达跃迁志愿数量 |
| `relaxation_stage` | data generation | 用户妥协发生在哪个放宽层级 |

这些指标分别对应事实可靠性、交互质量、结果收益和样本结构。

## TDD 阶段化实现

框架按五个阶段递进开发，并为每个阶段编写 pytest：

| Phase | 内容 | 测试 |
| --- | --- | --- |
| 1 | Pydantic schema 契约 | `test_phase1.py` |
| 2 | DB gap 探测与画像合成 | `test_phase2.py` |
| 3 | 固执用户模拟器 | `test_phase3.py` |
| 4 | 多轮沙盒引擎 | `test_phase4.py` |
| 5 | 确定性裁判与 LLM 裁判 | `test_phase5.py` |

后续围绕真实 DB 生成、专业树、embedding probe、LLM 审校和层级放宽的测试集中在：

```text
gaokaollm_bench/tests/test_real_db_generator_cli.py
```
运行命令
```bash
python -m pytest gaokaollm_bench/tests/test_real_db_generator_cli.py -q
```

该 TDD 路径保证了每次扩展都能被最小闭环验证。

## 可复现实验产物

项目中已经保留若干中间与最终产物：

```text
gaokaollm_bench/sample_data/
gaokaollm_bench/outputs/
```

其中包括：

- 真实 DB 生成的 persona 样本。
- 专业树规则扫描结果。
- 未归类专业清单。
- embedding probe 训练集、验证集、权重和日志。
- LLM 审校候选。
- 最终专业树与审计文件。

这些文件使 benchmark 不只是运行时代码，也是一条可审计的数据构建流水线。

## 方法学贡献

`gaokaollm-bench` 的主要贡献可以概括为：

1. 将高考志愿 Agent 的评测对象从静态答案扩展为多轮偏好更新过程。
2. 用真实数据库 gap 生成反事实样本，降低人工构造测试集的幻觉风险。
3. 通过冰山画像显式区分显性红线和隐性妥协条件。
4. 将专业放宽建模为可审计树上的逐级遍历，而不是一次性粗暴去约束。
5. 用用户模拟器和被测 Agent 构成自动化对战沙盒，捕捉过程质量。
6. 结合确定性事实裁判和 LLM 过程裁判，分别约束事实底线和交互质量。

## 局限性与后续工作

当前框架仍有若干局限：

1. `hallucination_rate` 主要验证学校可达性，对专业、年份、省份批次等条件的联合校验仍可加强。
2. LLM 用户模拟器和 LLM 裁判本身存在模型偏差，需要通过多裁判一致性或人工抽样审计校准。
3. 专业树虽然可审计，但仍依赖人工骨架和审校策略，跨年份、跨省份、跨批次迁移需要持续维护。
4. 当前 `pareto_gain` 主要基于学校 tier，未来可引入风险、专业匹配度、城市偏好、就业预期等多目标收益。
5. 沙盒尚未显式建模用户信任、反问、犹豫和信息寻求等更细粒度心理状态。

后续可以进一步发展为：

- 多裁判 ensemble。
- 更严格的 SQL 事实核验。
- 基于真实咨询日志的行为校准。
- 分省份、分科类、分分段的 benchmark 子集。
- 面向不同 Agent 策略的 leaderboard。

## 结论

`gaokaollm-bench` 将高考志愿推荐评测从“模型是否会回答”推进到“模型是否能在真实约束、真实数据和多轮交互中促成可靠的偏好妥协”。其核心思想是：优秀的决策 Agent 不应只迎合用户的初始表述，也不应强行说服用户放弃偏好，而应通过可核验的反事实证据帮助用户发现更优且可接受的志愿集合。

