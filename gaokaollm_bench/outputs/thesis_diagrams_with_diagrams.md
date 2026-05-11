# Diagrams 论文插图生成说明

本文档说明如何用 `mingrammer/diagrams` 为毕业论文生成第一批可迁入正文、PPT 或 LaTeX 的架构类插图。它不新增实验结果，不替代 `thesis_figures_tables_pack.md` 中的 Mermaid 草稿；它的作用是把其中最核心的架构与流程图转成可复现的 SVG/PNG 文件。

参考资料：

- Diagrams GitHub: <https://github.com/mingrammer/diagrams>
- Diagrams 安装文档: <https://diagrams.mingrammer.com/docs/getting-started/installation>
- Diagrams 使用指南: <https://diagrams.mingrammer.com/docs/guides/diagram>

Diagrams 本身是 Python 绘图 DSL，不控制任何云资源。它依赖 Graphviz 渲染，因此运行脚本前需要保证 `dot` 可执行文件在 PATH 中。

## 1. 环境配置

推荐在本项目已有的 `gaokao_pg` 环境中安装可选作图依赖：

```powershell
conda install -n gaokao_pg -c conda-forge graphviz
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m pip install -r requirements-diagrams.txt
```

安装后可以用下面的命令确认环境：

```powershell
dot -V
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -c "import diagrams; print(diagrams)"
```

如果脚本检测不到 `dot` 或 Python 包 `diagrams`，会输出安装提示并退出，不会修改数据库、实验产物或论文事实源。

脚本也支持常见的 Windows/conda Graphviz 发现路径。如果 `dot.exe` 已安装但不在 PATH，可以临时设置：

```powershell
$env:GRAPHVIZ_BIN="C:\ProgramData\Anaconda3\pkgs\graphviz-14.1.3-h56570d3_0\Library\bin"
```

然后重新运行渲染命令即可。

## 2. 渲染命令

默认输出目录为 `gaokaollm_bench/outputs/thesis_figures/`：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m gaokaollm_bench.tests.manual.render_thesis_diagrams
```

也可以指定输出目录：

```powershell
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m gaokaollm_bench.tests.manual.render_thesis_diagrams --output-dir gaokaollm_bench/outputs/thesis_figures
```

脚本只做静态绘图：不启动 PostgreSQL，不调用外部 LLM，不重跑 benchmark，也不读取 `implicit_flexibilities` 或 `volunteer_set`。

## 3. 输出文件

| 图号 | 输出文件 stem | 格式 | 建议章节 | 对应 Mermaid 草稿 |
| --- | --- | --- | --- | --- |
| 图 4-1 | `fig_4_1_system_architecture` | `.svg` / `.png` | 第 4 章或第 5 章开头 | `thesis_figures_tables_pack.md` 第 2 节 |
| 图 5-1 | `fig_5_1_mas_workflow` | `.svg` / `.png` | 第 5 章 Agent/MAS 方法 | `thesis_figures_tables_pack.md` 第 3 节 |
| 图 4-2 | `fig_4_2_benchmark_flow` | `.svg` / `.png` | 第 4 章 Benchmark 方法 | `thesis_figures_tables_pack.md` 第 4 节 |
| 图 4-3 | `fig_4_3_data_evidence_relax_mapping` | `.svg` / `.png` | 第 4 章数据层设计 | `thesis_figures_tables_pack.md` 第 5 节 |

首批图采用英文节点标签，主要是为了降低 Graphviz 在不同系统上的中文字体渲染风险。正式论文中可以在图题、图注或 PPT 中补充中文解释；如果需要中文图内标签，可在本脚本中统一替换节点文本并指定可用字体。

## 4. 当前论文口径

这些插图遵守当前事实源 `thesis_claims_manifest.json` 中的统一口径：

- 论文贡献结构是“数据 + Agent + Benchmark”。
- 业务 Agent 是轻量 MAS / 多角色 Agent 工作流：`gatekeeper -> radar -> negotiator`。
- 主实验是 `major_geo_v1 + risk_band_v1`。
- 扩展实验是 `school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1`、`region_tree_v1`。
- `region_tree_v1` 是扩展实验；城市层级只作为 reviewed region-tree 证据，不直接等价于就业机会、生活成本或城市生活质量收益。
- Agent 不读取 hidden persona 字段：`implicit_flexibilities` 或 `volunteer_set`。

## 5. 图与论文叙事的对应

| 插图 | 论文要表达的核心点 |
| --- | --- |
| 系统总体架构图 | 数据层不是附属材料，而是 Agent 谈判和 Benchmark 判定的事实基础。 |
| MAS 工作流图 | `gatekeeper`、`radar`、`negotiator` 是角色化协作工作流，不夸大为完全自治多智能体系统。 |
| Benchmark 流程图 | 冰山画像 hidden fields 只进入 evaluator ground truth，不进入被测 Agent 输入。 |
| 数据证据层映射图 | 七类 relax 都有对应证据层，避免把主观偏好包装成不可核验收益。 |

## 6. 与 Mermaid / LaTeX 的关系

`thesis_figures_tables_pack.md` 仍保留 Mermaid 图，适合作为概念草稿和快速修改入口。Diagrams 脚本适合生成较稳定的架构图源文件。正式成稿时：

- SVG 可直接进入部分 LaTeX 或矢量编辑工具。
- PNG 可用于 Word、WPS 或答辩 PPT。
- 论文三线表、实验结果表和算法伪代码仍建议从 Markdown 手工迁入 LaTeX，而不是用 Diagrams 表达。
