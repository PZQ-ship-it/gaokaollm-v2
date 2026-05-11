# Diagrams 论文插图生成说明

本文档说明如何用 `mingrammer/diagrams` 为毕业论文生成架构类插图。当前版本采用“论文框图风格”：用 Graphviz 纯文本框表达系统结构，避免 Diagrams 默认云架构图标过大、边交叉过多、图内命名不适合中文论文的问题。

参考资料：

- Diagrams GitHub: <https://github.com/mingrammer/diagrams>
- Diagrams 安装文档: <https://diagrams.mingrammer.com/docs/getting-started/installation>
- Diagrams 使用指南: <https://diagrams.mingrammer.com/docs/guides/diagram>

Diagrams 是 Python 绘图 DSL，不控制任何云资源。它依赖 Graphviz 渲染，因此运行脚本前需要保证 `dot` 可执行文件可用。

## 1. 环境配置

推荐在 `gaokao_pg` 环境中安装可选作图依赖：

```powershell
conda install -n gaokao_pg -c conda-forge graphviz
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m pip install -r requirements-diagrams.txt
```

安装后可以用下面的命令确认环境：

```powershell
dot -V
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -c "import diagrams; print(diagrams)"
```

脚本也支持常见 Windows/conda Graphviz 路径的自动发现。如果 `dot.exe` 已安装但不在 PATH，可以临时设置：

```powershell
$env:GRAPHVIZ_BIN="C:\ProgramData\Anaconda3\pkgs\graphviz-14.1.3-h56570d3_0\Library\bin"
```

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

| 图号 | 输出文件 stem | 格式 | 建议章节 | 图内主问题 |
| --- | --- | --- | --- | --- |
| 图 4-1 | `fig_4_1_system_architecture` | `.svg` / `.png` | 第 4 章或第 5 章开头 | 数据、Agent、Benchmark 与论文产物如何闭环 |
| 图 5-1 | `fig_5_1_mas_workflow` | `.svg` / `.png` | 第 5 章 Agent/MAS 方法 | `gatekeeper -> radar -> negotiator` 如何协作 |
| 图 4-2 | `fig_4_2_benchmark_flow` | `.svg` / `.png` | 第 4 章 Benchmark 方法 | hidden persona 如何只进入 evaluator |
| 图 4-3 | `fig_4_3_data_evidence_relax_mapping` | `.svg` / `.png` | 第 4 章数据层设计 | 证据族如何支撑七类 relax |

## 4. 视觉规范

| 元素 | 样式约定 | 含义 |
| --- | --- | --- |
| 数据贡献 | 浅蓝色节点/分组 | PostgreSQL、专业树、地域树、质量/就业/学费等证据层 |
| Agent 贡献 | 浅绿色节点/分组 | 轻量 MAS / 多角色 Agent 的业务能力 |
| Benchmark 贡献 | 浅紫色节点/分组 | 冰山画像、多轮沙盒、事实/过程联合评价 |
| 论文产物 | 浅灰色节点/分组 | summary、transcripts、evidence、SVG/PNG 图表 |
| hidden / evaluator-only | 浅黄色节点与虚线边 | 不进入被测 Agent 输入，只作为 evaluator ground truth |

图内节点采用中文短句，保留必要英文关键词，例如 `gatekeeper`、`radar`、`negotiator`、`region_tree_relax`。图文件本身不显示底部 `fig_...` 标题；图号和图题应放在论文正文或 PPT 标题中。

## 5. 当前论文口径

这些插图遵守 `thesis_claims_manifest.json` 的统一口径：

- 论文贡献结构是“数据 + Agent + Benchmark”。
- 业务 Agent 是轻量 MAS / 多角色 Agent 工作流：`gatekeeper -> radar -> negotiator`。
- 主实验是 `major_geo_v1 + risk_band_v1`。
- 扩展实验是 `school_strength_v1`、`tuition_value_v1`、`major_quality_v1`、`employment_outcome_v1`、`region_tree_v1`。
- `region_tree_v1` 是扩展实验；城市层级只作为 reviewed region-tree 证据，不直接等价于就业机会、生活成本或城市生活质量收益。
- Agent 不读取 hidden persona 字段：`implicit_flexibilities` 或 `volunteer_set`。

## 6. 与 Mermaid / LaTeX 的关系

`thesis_figures_tables_pack.md` 仍保留 Mermaid 图，适合作为概念草稿和快速修改入口。Diagrams 脚本适合生成较稳定的架构图源文件。正式成稿时：

- SVG 可进入矢量编辑工具或部分 LaTeX 流程。
- PNG 可用于 Word、WPS 或答辩 PPT。
- 三线表、实验结果表和算法伪代码仍建议从 Markdown 手工迁入 LaTeX，而不是用 Diagrams 表达。
