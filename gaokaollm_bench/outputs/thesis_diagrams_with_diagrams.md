# Diagrams 论文插图生成说明

本文档说明如何用 `mingrammer/diagrams` 为毕业论文生成架构类插图。当前图源采用“论文框图风格”：用 Graphviz 纯文本框表达概念关系，尽量避免 Diagrams 默认云架构图标、工程模块名和文件名暴露在图内。

当前图内术语与 LaTeX 终稿保持一致：

- 论文主线：数据贡献 + Agent 贡献 + Benchmark 贡献。
- Agent 角色：约束解析器（Constraint Parser）、机会探测器（Opportunity Detector）、证据谈判器（Evidence Negotiator）。
- 核心机制：硬约束锁定、单变量 Delta Analysis、分阶段放宽、证据驱动的帕累托谈判。
- 专业树表述：专业层级本体、人工骨架、规则挂载、模型辅助候选、低置信审校。
- 地域树表述：经审校的地域层级画像、地理板块、城市层级；城市层级只作为偏好显性化证据，不直接等价于就业机会、生活成本或城市生活质量收益。

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

安装后可用下面命令确认环境：

```powershell
dot -V
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -c "import diagrams; print(diagrams)"
```

脚本也支持常见 Windows/conda Graphviz 路径的自动发现。如果 `dot.exe` 已安装但不在 PATH，可临时设置：

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

脚本只做静态绘图：不启动 PostgreSQL，不调用外部 LLM，不重跑 benchmark，也不读取评测端隐藏偏好字段。

## 3. 输出文件与章节位置

| 图号 | 输出文件 stem | 格式 | 建议章节 | 图内主问题 |
| --- | --- | --- | --- | --- |
| 图 4-1 | `fig_4_1_system_architecture` | `.svg` / `.png` | 第 4 章或第 5 章开头 | 数据层、Agent 层、Benchmark 层与论文产物如何闭环 |
| 图 5-1 | `fig_5_1_mas_workflow` | `.svg` / `.png` | 第 5 章 Agent/MAS 方法 | 约束解析器、机会探测器、证据谈判器如何协作 |
| 图 4-2 | `fig_4_2_benchmark_flow` | `.svg` / `.png` | 第 4 章 Benchmark 方法 | 显性用户话语与评测端隐藏偏好如何隔离 |
| 图 4-3 | `fig_4_3_data_evidence_relax_mapping` | `.svg` / `.png` | 第 4 章数据层设计 | 专业层级本体、风险、学费、质量、就业、地域证据如何支撑放宽动作 |

## 4. 视觉规范

| 元素 | 样式约定 | 含义 |
| --- | --- | --- |
| 数据贡献 | 浅蓝色节点/分组 | 招生事实、专业层级本体、地域层级画像、质量/就业/学费证据 |
| Agent 贡献 | 浅绿色节点/分组 | 约束解析、机会探测、证据谈判和可谈判偏好轴 |
| Benchmark 贡献 | 浅紫色节点/分组 | 冰山画像、多轮用户模拟、事实/过程联合评价、多轴压力测试 |
| 论文产物 | 浅灰色节点/分组 | 聚合指标、逐例证据、论文图表 |
| hidden / evaluator-only | 浅黄色节点与虚线边 | 不进入被测 Agent 输入，只作为 evaluator ground truth |

图内节点优先使用中文学术短句，仅在括注中保留必要英文术语，如 Constraint Parser、Opportunity Detector、Evidence Negotiator。工程 id、文件名、输出目录不进入图内主叙述。

## 5. 与 Mermaid / LaTeX 的关系

`thesis_figures_tables_pack.md` 仍保留 Mermaid 图，适合作为概念草稿和快速修改入口。Diagrams 脚本生成的 SVG/PNG 是当前论文/PPT 首选图像资产：

- SVG 可进入矢量编辑工具或部分 LaTeX 流程。
- PNG 可用于 Word、WPS 或答辩 PPT。
- 实验结果表、三线表和算法伪代码仍建议在 LaTeX 中手工排版，而不是用 Diagrams 表达。
