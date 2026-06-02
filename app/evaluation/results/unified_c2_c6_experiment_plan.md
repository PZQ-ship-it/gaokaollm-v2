# Unified c2-c6 实验补跑方案

## 目标

在已经修复 `app_pareto` LangGraph interrupt/resume、用户模拟器防泄露、judge veto 和 transcript 诊断字段之后，继续把统一数据集的 `c2-c6` 实验补完。后续实验只使用 fixed 输出根目录，避免与旧的 invalid run 混表。

本轮实验目标不是立刻改论文，而是先得到可信的分层结果：

- 验证约束数从 `2-constrain` 到 `6-constrain` 时，EDMIE 是否仍能稳定进入“探测-谈判-追踪”链路。
- 比较 `app_pareto` 与 `v1_prompt_direct` 在更高约束画像下的成功率、幻觉率、轮次和 Pareto gain。
- 跑完 `full / no_ucb / no_tracker` 消融，生成 EUDR、PCG、MSTI、CTR、BOI、KBV、MAE、Top-k F1 等过程指标。
- `v1_prompt_cot` 由于当前运行耗时和外层进程限制明显更重，先作为慢批/补充实验单独处理，不阻塞主实验闭环。

## 当前 c1 基线状态

`c1` fixed run 的主要结论：

- `app_pareto` baseline：5 模型 × 30，`150/150` 完成。
- `v1_prompt_direct` baseline：5 模型 × 30，`150/150` 完成。
- `v1_prompt_cot` baseline：当前只落盘 `43` 条，其中 `42` ok、`1` failed，不应作为完整横评结论。
- ablation：
  - `full`：`30/30`
  - `no_tracker`：`30/30`
  - `no_ucb`：`30` rows，`29` ok、`1` TailTimeout。

关键诊断信号：

- `app_pareto` baseline：`echo_rate=0.000`，`probe_question_rate≈0.669`，`pareto_diff_rate≈0.669`。
- ablation full：`echo_rate=0.000`，`probe_question_rate≈0.694`。

这说明原先“复读用户导致结果无效”的问题已修复；后续 c2-c6 可以在同一 fixed 链路上继续跑。

## 数据与输出目录

主数据：

```powershell
gaokaollm_bench\sample_data\unified_iceberg_personas_1c6c_real_db_180.json
```

按约束数拆分目录：

```powershell
gaokaollm_bench\sample_data\unified_by_constraint_fixed
```

fixed 输出根目录：

```powershell
gaokaollm_bench\outputs\unified_adaptive_arena_fixed
```

每个层级的输出结构：

```powershell
gaokaollm_bench\outputs\unified_adaptive_arena_fixed\c{N}\baseline\{model}\{target}
gaokaollm_bench\outputs\unified_adaptive_arena_fixed\c{N}\ablation\Pro_zai-org_GLM-5.1\{target}
```

统一指标输出建议：

```powershell
app\evaluation\results\unified_c2_c6_baseline_results.csv
app\evaluation\results\unified_c2_c6_ablation_results.csv
app\evaluation\results\unified_c2_c6_experiment_summary.md
```

## 推荐执行顺序

更新后的主路径应使用已经验证通过的 4 API lane 分布式方案，而不是单 API 串行跑完 `c2-c5`。

推荐总顺序：

1. 使用 4 lane 分布式 runner 并行跑 `c2-c5`。
2. 每个 lane 独占一个 constraint 层级：
   - `C2 -> siliconflow_1`
   - `C3 -> siliconflow_2`
   - `C4 -> aliyun_1`
   - `C5 -> aliyun_2`
3. `c2-c5` 完成后先运行 `status` 和统一 metrics，检查 echo/probe/pareto 诊断。
4. `c6` 不再按单 lane 慢跑处理，而是在 `c2-c5` 完成后切成 4 个 case shard，复用 4 个 API lane 并行跑。
5. COT 仍然建议作为慢批单独跑，不阻塞主线 baseline + ablation。

原先的单 API 顺序方案只作为 fallback：当某个 lane 失败、某个 provider 限流，或需要单独补尾部 case 时再用。

## 4 API 分布式主路径

分布式 runner 已经完成实现和健康检查，主入口是：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m app.evaluation.distributed_unified_benchmark
```

已验证组件：

- `provider_lanes.py`：读取 4 个 API lane，掩码展示 key，生成 lane 专属临时 `models.txt`，并给子进程注入 lane 环境变量。
- `distributed_unified_benchmark.py`：支持 `init-config / validate-config / healthcheck / run / status`。
- `llm_lanes.local.json` 已生成并被 `.gitignore` 忽略。
- 4 个 lane 的 small model、20 个大模型、4 个 embedding、4 个 rerank 均已通过健康检查。
- dry-run 映射已验证为 `C2 -> siliconflow_1`、`C3 -> siliconflow_2`、`C4 -> aliyun_1`、`C5 -> aliyun_2`。

健康检查报告：

```powershell
app\evaluation\results\llm_lanes_healthcheck.md
```

dry-run manifest：

```powershell
app\evaluation\results\distributed_c2c5_manifest.json
```

### 启动前检查

正式跑批前建议再跑一次轻量校验：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m app.evaluation.distributed_unified_benchmark validate-config
```

如距离上次健康检查较久，或刚切换网络，再跑：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m app.evaluation.distributed_unified_benchmark healthcheck `
  --parallel-lanes 4 `
  --timeout 60
```

### C2-C5 主线分布式跑批命令

建议第一轮主线先不带 `v1_prompt_cot`，只跑可稳定完成的 `app_pareto + v1_prompt_direct + 消融`：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m app.evaluation.distributed_unified_benchmark run `
  --constraints 2 3 4 5 `
  --personas gaokaollm_bench\sample_data\unified_iceberg_personas_1c6c_real_db_180.json `
  --output-root gaokaollm_bench\outputs\unified_distributed_c2c5 `
  --split-dir gaokaollm_bench\sample_data\unified_by_constraint_c2c5 `
  --log-dir app\evaluation\results\logs\c2c5_distributed `
  --manifest app\evaluation\results\distributed_c2c5_manifest.json `
  --baseline-targets app_pareto v1_prompt_direct `
  --ablation-targets app_pareto_full app_pareto_no_ucb app_pareto_no_tracker `
  --parallel-lanes 4 `
  --parallel-models 5 `
  --override-concurrency 10 `
  --min-concurrency 5 `
  --batch-attempts 6 `
  --case-retries 2 `
  --request-timeout 120 `
  --case-timeout 600
```

这个命令会并行启动 4 个 `adaptive_unified_benchmark` 子进程，每个子进程绑定一个 API lane 和一个 constraint 层级。理论主线 case 并发约为：

```text
4 lanes × 5 models × 10 cases = 200 baseline case 并发
```

消融阶段在每个 lane 内使用 `adaptive_unified_benchmark` 的 ablation 设置，主模型为该 lane 的第一行模型，仍按 target 顺序执行。

### 如果确实要“全量含 COT”

`distributed_unified_benchmark.py` 的默认 baseline targets 包含：

```text
app_pareto v1_prompt_direct v1_prompt_cot
```

所以不显式传 `--baseline-targets` 时会把 COT 一起跑进去。但 c1 经验显示 COT 很慢，容易拖住整批。若确实要一次性全量含 COT，可用：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m app.evaluation.distributed_unified_benchmark run `
  --constraints 2 3 4 5 `
  --personas gaokaollm_bench\sample_data\unified_iceberg_personas_1c6c_real_db_180.json `
  --output-root gaokaollm_bench\outputs\unified_distributed_c2c5 `
  --split-dir gaokaollm_bench\sample_data\unified_by_constraint_c2c5 `
  --log-dir app\evaluation\results\logs\c2c5_distributed `
  --manifest app\evaluation\results\distributed_c2c5_manifest.json `
  --parallel-lanes 4 `
  --parallel-models 5 `
  --override-concurrency 5 `
  --min-concurrency 2 `
  --batch-attempts 8 `
  --case-retries 2 `
  --request-timeout 120 `
  --case-timeout 900
```

注意：含 COT 的全量批次更适合无人值守长跑，不建议作为论文主表的阻塞步骤。

### 分布式状态查看

跑批中或跑批后查看 manifest 对应输出：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m app.evaluation.distributed_unified_benchmark status `
  --manifest app\evaluation\results\distributed_c2c5_manifest.json `
  --output-md app\evaluation\results\distributed_c2c5_status.md
```

也可以直接查看每个 lane 日志：

```powershell
app\evaluation\results\logs\c2c5_distributed\distributed_c2_siliconflow_1.stdout.log
app\evaluation\results\logs\c2c5_distributed\distributed_c3_siliconflow_2.stdout.log
app\evaluation\results\logs\c2c5_distributed\distributed_c4_aliyun_1.stdout.log
app\evaluation\results\logs\c2c5_distributed\distributed_c5_aliyun_2.stdout.log
```

### C6 4 API 并行处理

`distributed_unified_benchmark.py` 当前默认 lane map 是按 constraint 分配 lane，因此只天然覆盖 `c2-c5`。但 `c6` 仍然可以使用 4 API 并行：不要按 constraint 分 lane，而是把 30 条 `c6` case 切成 4 个互斥 shard，每个 shard 交给一个 lane 跑。

推荐映射：

| shard | lane | 预计 case 数 |
| --- | --- | ---: |
| c6_s1 | siliconflow_1 | 8 |
| c6_s2 | siliconflow_2 | 8 |
| c6_s3 | aliyun_1 | 7 |
| c6_s4 | aliyun_2 | 7 |

这样做的优点：

- 4 个 API 同时工作，`c6` 不再成为最后的单 lane 长尾。
- 每条 c6 case 只出现在一个 shard 中，最终汇总时不会重复计数。
- 每个 shard 内仍可跑该 lane 的 5 个模型、`app_pareto / v1_prompt_direct` 和三组消融。

注意：这种 shard 方案的含义是“并行完成 c6 层级主实验”，不是“每个 c6 case 都在 4 个 provider 上重复横评”。若要做每 case × 4 provider 的完全交叉实验，规模会扩大 4 倍，不建议作为主线。

#### C6 shard 数据生成

建议新增或临时运行一个小工具，将统一数据中的 `constraint_count=6` 样本按 round-robin 切成 4 份：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m app.evaluation.distributed_unified_benchmark shard-cases `
  --personas gaokaollm_bench\sample_data\unified_iceberg_personas_1c6c_real_db_180.json `
  --constraint-count 6 `
  --shards 4 `
  --output-dir gaokaollm_bench\sample_data\unified_c6_shards
```

若当前 runner 还没有 `shard-cases` 子命令，可先用等价的临时脚本生成以下 4 个文件：

```powershell
gaokaollm_bench\sample_data\unified_c6_shards\c6_siliconflow_1.json
gaokaollm_bench\sample_data\unified_c6_shards\c6_siliconflow_2.json
gaokaollm_bench\sample_data\unified_c6_shards\c6_aliyun_1.json
gaokaollm_bench\sample_data\unified_c6_shards\c6_aliyun_2.json
```

#### C6 shard 跑批输出

为避免 4 个 lane 同时写同一个 `c6` 目录造成 report 竞争，建议每个 lane 写入独立输出根：

```powershell
gaokaollm_bench\outputs\unified_distributed_c6_sharded\siliconflow_1
gaokaollm_bench\outputs\unified_distributed_c6_sharded\siliconflow_2
gaokaollm_bench\outputs\unified_distributed_c6_sharded\aliyun_1
gaokaollm_bench\outputs\unified_distributed_c6_sharded\aliyun_2
```

每个输出根内部仍保持 adaptive 的结构：

```powershell
...\c6\baseline\{model}\{target}
...\c6\ablation\{model}\{target}
```

#### C6 shard 跑批命令

建议给 distributed runner 增加一个 `run-shards` 子命令，最终命令形态如下：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m app.evaluation.distributed_unified_benchmark run-shards `
  --constraint 6 `
  --shard-dir gaokaollm_bench\sample_data\unified_c6_shards `
  --output-root gaokaollm_bench\outputs\unified_distributed_c6_sharded `
  --log-dir app\evaluation\results\logs\c6_distributed `
  --manifest app\evaluation\results\distributed_c6_manifest.json `
  --baseline-targets app_pareto v1_prompt_direct `
  --ablation-targets app_pareto_full app_pareto_no_ucb app_pareto_no_tracker `
  --parallel-lanes 4 `
  --parallel-models 5 `
  --override-concurrency 10 `
  --min-concurrency 5 `
  --batch-attempts 6 `
  --case-retries 2 `
  --request-timeout 120 `
  --case-timeout 600
```

如果暂时不扩展 runner，也可以手动开 4 个 lane 进程，分别指定 shard persona、lane 专属 runtime `models.txt` 和 lane 环境变量。原则是：4 个进程必须写入 4 个不同 output root，最后由 metrics 脚本多 root 汇总。

## 单 API fallback 执行顺序

以下方案只在分布式 runner 某个 lane 不稳定、需要补尾部 case，或需要局部复查时使用。

不要一次性把 `c2-c6` 全部塞进单 API 大批次。建议按约束层级串行推进：

1. 跑 `c2` 的 `app_pareto + v1_prompt_direct` baseline。
2. 跑 `c2` 的 `full / no_ucb / no_tracker` 消融。
3. 生成 `c2` 临时 summary，检查诊断信号。
4. 若通过，再进入 `c3`，依次直到 `c6`。

这样可以尽早发现某一约束层级的数据或系统问题，避免把大量 API 消耗在不可用批次上。

## 并行运行策略

优先级：

1. C2-C5：优先使用 4 API lane 分布式 runner。
2. C6：等 C2-C5 完成后，切成 4 个 case shard，复用 4 API lane 并行跑。
3. 单 API 命令：只作为 fallback 或尾部补跑工具。

并行分三层理解：

- 模型级并行：`--parallel-models` 控制几个被测模型同时跑。
- case 级并发：`--override-concurrency` 控制每个模型/target 内同时跑几个 persona case。
- 进程级并行：同时开几个独立命令，例如 baseline 和 ablation 分两个终端跑，或 c2/c3 分两个终端跑。
- lane 级并行：`distributed_unified_benchmark.py --parallel-lanes 4` 控制 4 个 API lane 同时跑不同 constraint。

有效并发近似为：

```text
有效并发 = 进程数 × parallel-models × override-concurrency
```

但每个 case 里还会调用被测 agent、用户模拟器和 judge，因此实际 API 压力会高于这个数。当前 fixed c1 的经验是：`app_pareto` 与 `v1_prompt_direct` 可以承受较高并发，`v1_prompt_cot` 明显更慢，不适合放进主线高并发。

### 推荐默认并行

分布式主线：

```text
C2-C5: 4 lanes 并行
每个 lane: 1 个 constraint 层级
每个 lane 内 baseline: 5 models × 10 cases
每个 lane 内 ablation: 1 model × 10 cases
```

这是目前的首选方案。

单 API fallback 的主线 baseline：

```text
1 个 constraint 层级 × 2 个 baseline target 串行
每个 target 内：5 个模型并行 × 每模型 10 case 并发
理论 case 并发：50
```

也就是文档中 baseline 命令的默认设置：

```powershell
--parallel-models 5 `
--override-concurrency 10 `
--min-concurrency 5
```

单 API fallback 的主线 ablation：

```text
1 个 constraint 层级 × 3 个 ablation target 串行
每个 target 内：1 个模型 × 10 case 并发
理论 case 并发：10
```

也就是文档中 ablation 命令的默认设置：

```powershell
--parallel-models 1 `
--override-concurrency 10 `
--min-concurrency 5
```

这个默认策略最稳：先保证每个 constraint 层级有完整验收，不让多个层级的失败混在一起。

### 可接受的加速策略

如果 `c2` 跑完后诊断信号稳定，可以采用“双进程并行”：

- 终端 A：跑当前层级 baseline。
- 终端 B：跑同一层级 ablation。

此时理论 case 并发约为：

```text
baseline 50 + ablation 10 = 60
```

这个配置通常比同时跑多个 constraint 层级更容易排查问题，因为所有输出仍集中在同一个 `c{N}` 下。

如果 API 状态非常稳定，也可以采用“两层级并行”：

- 终端 A：跑 `c2 baseline`。
- 终端 B：跑 `c3 baseline`。

但不建议同时再开 ablation。否则理论并发会迅速升到 100 以上，simulator/judge 的小模型也会变成瓶颈。

### 激进策略

只在确认网络、API、DB 都稳定时使用：

```text
终端 A：cN baseline，parallel-models=5，concurrency=10
终端 B：cN ablation，parallel-models=1，concurrency=10
终端 C：cN+1 baseline，parallel-models=5，concurrency=5
```

理论 case 并发：

```text
50 + 10 + 25 = 85
```

超过这个强度后，失败通常不再能清楚区分是模型能力、数据设计还是 API 拥塞，因此不建议作为正式跑批默认策略。

### 不建议并行的情况

以下场景应降并发或串行：

- `APITimeoutError` 在 10 分钟内连续出现，或同一 target 多次 tail timeout。
- `summary.json` 里 failed cases 超过 10%。
- `app_pareto*` 的 `echo_rate` 不再接近 0。
- `probe_question_rate` 或 `pareto_diff_rate` 低于 0.55。
- `v1_prompt_cot` 正在跑。COT 建议单独慢批，不与主线 baseline/ablation 并行。

降并发顺序：

```text
baseline: 5 models × 10 -> 5 models × 5 -> 3 models × 5 -> 1 model × 5
ablation: 1 model × 10 -> 1 model × 5 -> 1 model × 3 -> 1 model × 1
COT: 5 models × 2 -> 2 models × 2 -> 1 model × 1
```

### 推荐实际排程

建议按如下节奏推进：

```text
c2-c5:
  A. 4 API lane 分布式并行跑完主线 baseline + ablation
  B. status + metrics 汇总
  C. 检查 echo/probe/pareto 诊断信号

c6:
  A. 生成 4 个 c6 case shard
  B. 4 API lane 并行跑 c6 shards
  C. 与 c2-c5 一起汇总
```

如果分布式 runner 不可用，再回退到单 API 双进程排程：

```text
第一批：
  终端 A: c2 baseline
  终端 B: c2 ablation

第二批：
  终端 A: c3 baseline
  终端 B: c3 ablation

第三批：
  终端 A: c4 baseline
  终端 B: c4 ablation

第四批：
  终端 A: c5 baseline
  终端 B: c5 ablation

第五批：
  终端 A: c6 baseline
  终端 B: c6 ablation
```

每批结束后都先跑汇总和诊断，再进入下一批。

### 并行监控命令

检查正在运行的 benchmark 进程：

```powershell
Get-CimInstance Win32_Process -Filter "name='python.exe'" |
  Where-Object { $_.CommandLine -like '*agent_benchmark_run*' -or $_.CommandLine -like '*adaptive_unified_benchmark*' } |
  Select-Object ProcessId,ParentProcessId,CreationDate,CommandLine
```

检查某个 constraint 层级完成数：

```powershell
$c = 2
Get-ChildItem -Recurse -Filter summary.json gaokaollm_bench\outputs\unified_adaptive_arena_fixed\c$c |
  ForEach-Object {
    $j = Get-Content -Raw $_.FullName | ConvertFrom-Json
    $j.targets.PSObject.Properties | ForEach-Object {
      [PSCustomObject]@{
        Path = $_.Name
        Cases = $_.Value.cases
        Completed = $_.Value.completed_cases
        Failed = $_.Value.failed_cases
      }
    }
  }
```

## 主线 Baseline 命令

对每个约束层级 `$c` 运行：

```powershell
$c = 2
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m app.evaluation.adaptive_unified_benchmark `
  --mode baseline `
  --personas gaokaollm_bench\sample_data\unified_iceberg_personas_1c6c_real_db_180.json `
  --models-file models.txt `
  --constraint-counts $c `
  --output-root gaokaollm_bench\outputs\unified_adaptive_arena_fixed `
  --split-dir gaokaollm_bench\sample_data\unified_by_constraint_fixed `
  --log-dir app\evaluation\results\logs `
  --baseline-targets app_pareto v1_prompt_direct `
  --parallel-models 5 `
  --override-concurrency 10 `
  --min-concurrency 5 `
  --batch-attempts 4 `
  --case-retries 2 `
  --request-timeout 120 `
  --case-timeout 600
```

预期每个 `$c`：

- `app_pareto`：5 模型 × 30 = 150 rows。
- `v1_prompt_direct`：5 模型 × 30 = 150 rows。
- 合计 300 rows。

`c2-c6` 主线 baseline 总量：

- 5 个约束层级 × 300 = 1500 rows。

## 消融命令

对每个约束层级 `$c` 运行：

```powershell
$c = 2
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m app.evaluation.adaptive_unified_benchmark `
  --mode ablation `
  --personas gaokaollm_bench\sample_data\unified_iceberg_personas_1c6c_real_db_180.json `
  --models-file models.txt `
  --constraint-counts $c `
  --output-root gaokaollm_bench\outputs\unified_adaptive_arena_fixed `
  --split-dir gaokaollm_bench\sample_data\unified_by_constraint_fixed `
  --log-dir app\evaluation\results\logs `
  --ablation-targets app_pareto_full app_pareto_no_ucb app_pareto_no_tracker `
  --parallel-models 1 `
  --override-concurrency 10 `
  --min-concurrency 5 `
  --batch-attempts 4 `
  --case-retries 2 `
  --request-timeout 120 `
  --case-timeout 600
```

预期每个 `$c`：

- `full / no_ucb / no_tracker`：3 targets × 30 = 90 rows。

`c2-c6` 消融总量：

- 5 个约束层级 × 90 = 450 rows。

## COT 慢批策略

`v1_prompt_cot` 在 c1 中没有跑满，主要问题是运行时非常长，且每条 case 会触发多轮 baseline 回复、simulator 和 judge。建议不要把 COT 放进主线命令里。

可选方案 A：单独慢批补齐。

```powershell
$c = 2
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m app.evaluation.adaptive_unified_benchmark `
  --mode baseline `
  --personas gaokaollm_bench\sample_data\unified_iceberg_personas_1c6c_real_db_180.json `
  --models-file models.txt `
  --constraint-counts $c `
  --output-root gaokaollm_bench\outputs\unified_adaptive_arena_fixed `
  --split-dir gaokaollm_bench\sample_data\unified_by_constraint_fixed `
  --log-dir app\evaluation\results\logs `
  --baseline-targets v1_prompt_cot `
  --parallel-models 5 `
  --override-concurrency 2 `
  --min-concurrency 1 `
  --batch-attempts 8 `
  --case-retries 2 `
  --request-timeout 120 `
  --case-timeout 900
```

可选方案 B：把 COT 改造成真正的短轮强基线，只做一次显式输入分析和一次推荐，不再跑 6 轮对话。这个方案更适合作为论文中的 “strong CoT baseline”，但需要先改 target 实现。

论文主实验建议先不依赖 COT 完整批次；COT 可作为补充讨论。

## 诊断验收条件

每个约束层级完成后，先检查 `summary.json` 和统一 summary：

- `app_pareto` 每模型应为 `30/30`。
- `v1_prompt_direct` 每模型应为 `30/30`。
- `full` 和 `no_tracker` 应尽量为 `30/30`。
- `no_ucb` 若出现少量尾部 timeout，应显式标记 `TailTimeout`，不能静默丢行。

关键有效性信号：

- `echo_rate` 应接近 0；若 `app_pareto*` 出现大面积 echo，直接判为 invalid run。
- `probe_question_rate` 建议不低于 0.55；否则说明探测链路没有稳定进入。
- `pareto_diff_rate` 建议不低于 0.55；否则说明证据谈判器没有稳定生成候选差异。
- 成功 case 的 golden/acceptable candidate 首次出现角色必须是 `target_agent`，不能是 `user_simulator`。
- `no_tracker` 的 `uniform_weight_rate` 和 `constant_variance_rate` 高是预期现象，因为它本来就不更新显式偏好状态。
- `no_ucb` 的 `valid_probe_hit_rate`、`valid_probe_coverage`、`pcg_final_coverage` 应明显低于 full，这是消融应观察到的退化方向。

## Tail Case 处理规则

遇到少数尾部失败时按以下顺序处理：

1. 若 report 缺失但 transcript 已存在：
   - 可用 deterministic judge/backfill 补评。
   - row 中保留 `backfilled_from_transcript=True`。
   - 这只用于 judge/report timeout，不用于虚构对话结果。
2. 若 transcript 不存在：
   - 单独抽出该 case，`concurrency=1` 补跑。
3. 若单 case 仍长时间无 transcript：
   - 标记为 `TailTimeout` failed row。
   - 不要从统计表中静默删除。

## 汇总命令

只汇总 `c2-c6`：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m app.evaluation.unified_experiment_metrics `
  --baseline-root `
    gaokaollm_bench\outputs\unified_adaptive_arena_fixed\c2\baseline `
    gaokaollm_bench\outputs\unified_adaptive_arena_fixed\c3\baseline `
    gaokaollm_bench\outputs\unified_adaptive_arena_fixed\c4\baseline `
    gaokaollm_bench\outputs\unified_adaptive_arena_fixed\c5\baseline `
    gaokaollm_bench\outputs\unified_adaptive_arena_fixed\c6\baseline `
  --ablation-root `
    gaokaollm_bench\outputs\unified_adaptive_arena_fixed\c2\ablation `
    gaokaollm_bench\outputs\unified_adaptive_arena_fixed\c3\ablation `
    gaokaollm_bench\outputs\unified_adaptive_arena_fixed\c4\ablation `
    gaokaollm_bench\outputs\unified_adaptive_arena_fixed\c5\ablation `
    gaokaollm_bench\outputs\unified_adaptive_arena_fixed\c6\ablation `
  --baseline-csv app\evaluation\results\unified_c2_c6_baseline_results.csv `
  --ablation-csv app\evaluation\results\unified_c2_c6_ablation_results.csv `
  --summary app\evaluation\results\unified_c2_c6_experiment_summary.md
```

汇总 `c1-c6` 全部 fixed 结果：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m app.evaluation.unified_experiment_metrics `
  --baseline-root gaokaollm_bench\outputs\unified_adaptive_arena_fixed `
  --ablation-root gaokaollm_bench\outputs\unified_adaptive_arena_fixed `
  --baseline-csv app\evaluation\results\unified_c1_c6_fixed_baseline_results.csv `
  --ablation-csv app\evaluation\results\unified_c1_c6_fixed_ablation_results.csv `
  --summary app\evaluation\results\unified_c1_c6_fixed_experiment_summary.md
```

如果使用整个 `unified_adaptive_arena_fixed` 作为 root，需要确认其中没有旧 invalid 子目录或临时 tail 单跑目录混入。

## 最终判断口径

完成 c2-c6 后先做三类判断：

1. 复杂约束下的相对优势是否扩大：
   - 不把绝对成功率预设为 `c1 >= c2 >= ... >= c6`；约束越复杂，EDMIE 相比 direct / CoT / no-UCB / no-tracker 的相对优势应更明显。
   - 重点看 `Δsuccess = success(full) - success(direct/cot)`、`Δgain = pareto_gain(full) - pareto_gain(direct/cot)`、`ΔPCG = PCG(full) - PCG(no_ucb)`、`ΔMAE/F1 = full - no_tracker` 是否随 `constraint_count` 增大而扩大或保持稳定优势。
   - 若高约束层级的 full 绝对成功率也上升，这是强证据；若 full 稳定或小幅下降但 direct/cot 下降更快，仍支持“多轮证据驱动启发在复杂约束下更有价值”的论文叙事。
   - 若 full 在 `c5-c6` 明显下滑，需要结合诊断字段判断：probe/pareto 正常则偏向数据可达性或候选池稀疏问题，probe/pareto 缺失则优先回看系统链路。
2. 系统机制是否成立：
   - full 的 PCG、valid probe coverage、MSTI、MAE/F1 应优于 no-UCB/no-tracker 的关键维度。
   - direct baseline 若持续高 hallucination/低成功，说明单轮静态检索难以替代多轮偏好启发。
3. 数据是否适合写入论文：
   - 若 `c2` 就出现大量无 Pareto diff 或 probe 缺失，优先回看数据构造和 radar 候选发现逻辑。
   - 若 `c5-c6` 中 full 的绝对成功率下降，但相对 direct/cot 与消融组的优势扩大，可作为高约束下架构优势更明显的压力测试结论，而非主实验失败。
   - 若 `c5-c6` 中 full 与 direct/cot 同时接近失效，则不急着写成系统失败，先检查 golden candidate 可达性、候选召回、probe 维度映射和用户模拟触发条件。

## 论文使用建议

在论文中建议分层使用：

- 主实验：`c1-c3` 或全部 `c1-c6` 中通过诊断验收的 fixed run。
- 压力测试：`c4-c6`，重点写趋势和失败边界。
- COT：仅在完整跑满后作为补充强基线；若未跑满，不进入主表。

不要把 LLM 合成/扩展画像写成真实用户泛化证据。应表述为“基于真实 DB golden candidate 的统一约束梯度诊断集/压力集”。
