# 论文插图生成说明：手工 SVG/PNG 框图

本文档说明如何生成毕业论文中的架构类插图。当前正式图源采用手工 SVG 论文框图布局，并使用本地 Edge/Chrome headless 导出 PNG；早期 `mingrammer/diagrams` / Graphviz 版本仅作为探索记录保留。当前图内不使用默认云架构大图标，也不把代码文件名、实验目录名或内部字段名放进图内主叙述。

当前图内术语与 LaTeX 终稿保持一致：

- 论文主线：数据贡献 + Agent 贡献 + Benchmark 贡献。
- 业务 Agent：前置语义归一层 -> 约束解析器 -> LLM 引导的机会规划器 -> 确定性证据探针 -> 证据谈判器。
- LLM 参与边界：LLM 只做查询归一、机会排序、证据编排顺序和澄清提示，不生成事实候选。
- 事实来源边界：学校、专业、分数、位次、学费、专业质量、就业结果和地域层级候选均来自 PostgreSQL 或标准化证据层。
- 评测边界：业务 Agent 不读取 `implicit_flexibilities`、`volunteer_set` 或 `axis_flexibilities`；这些字段只用于模拟器和评测器。

历史参考资料：

- Diagrams GitHub: <https://github.com/mingrammer/diagrams>
- Diagrams 安装文档: <https://diagrams.mingrammer.com/docs/getting-started/installation>
- Diagrams 使用指南: <https://diagrams.mingrammer.com/docs/guides/diagram>

Diagrams 是 Python 绘图 DSL，不控制任何云资源。当前脚本已经不依赖 Diagrams/Graphviz 生成最终图像；它只需要 Python 和本地 Edge/Chrome 用于 PNG 导出。

## 1. 环境配置

推荐在 `gaokao_pg` 环境中运行脚本。若需要复现实验性 Diagrams 草稿，可另行安装可选依赖；当前正式图像不依赖这些包：

```powershell
conda install -n gaokao_pg -c conda-forge graphviz
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -m pip install -r requirements-diagrams.txt
```

若仍需检查早期 Diagrams/Graphviz 环境，可使用：

```powershell
dot -V
C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe -c "import diagrams; print(diagrams)"
```

当前正式脚本会自动寻找 Edge 或 Chrome。若找不到浏览器，将无法导出 PNG，但 SVG 生成逻辑本身仍是本地静态作图。

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

该脚本只做静态绘图：不启动 PostgreSQL，不调用外部 LLM，不重跑 benchmark，也不读取评测端隐藏偏好字段。

## 3. 输出文件与章节位置

| 图号 | 输出文件 stem | 格式 | 建议章节 | 图内主问题 |
| --- | --- | --- | --- | --- |
| 图 4-1 | `fig_4_1_system_architecture` | `.svg` / `.png` | 第 4 章或第 5 章开头 | 数据层、业务 Agent、Benchmark 层和论文产物如何闭环 |
| 图 5-1 | `fig_5_1_mas_workflow` | `.svg` / `.png` | 第 5 章 Agent/MAS 方法 | 前置语义归一、LLM 机会规划、确定性探针与证据谈判如何协作 |
| 图 4-2 | `fig_4_2_benchmark_flow` | `.svg` / `.png` | 第 4 章 Benchmark 方法 | 显式用户话语与评测端隐藏偏好如何隔离 |
| 图 4-3 | `fig_4_3_data_evidence_relax_mapping` | `.svg` / `.png` | 第 4 章数据层设计 | 数据证据族如何支撑各类可谈判偏好轴 |

## 4. 视觉规范

| 元素 | 样式约定 | 含义 |
| --- | --- | --- |
| 数据贡献 | 浅蓝色节点/分组 | 招生事实、专业层级本体、地域层级画像、质量/就业/学费证据 |
| Agent 贡献 | 浅绿色节点/分组 | 语义归一、约束解析、LLM 规划、确定性探针和证据谈判 |
| Benchmark 贡献 | 浅紫色节点/分组 | 冰山画像、多轮用户模拟、事实/过程联合评价、多轴压力测试 |
| 论文产物 | 浅灰色节点/分组 | 聚合指标、逐例证据、论文图表 |
| hidden / evaluator-only | 浅黄色节点与虚线边 | 不进入被测 Agent 输入，只作为 evaluator ground truth |

图内节点优先使用中文学术短句，仅在必要处括注英文术语。实现层名称如 `gatekeeper`、`radar`、`negotiator` 可在正文或附录中括注，但不作为图 5-1 的主标题和主路径。

## 5. 与 Mermaid / LaTeX 的关系

`thesis_figures_tables_pack.md` 中仍保留少量 Mermaid 草稿，适合作为概念备份和快速修改入口。手工 SVG/PNG 论文框图生成器输出的 SVG/PNG 是当前论文和答辩 PPT 的首选图像资产：

- SVG 可进入矢量编辑工具或部分 LaTeX 流程。
- PNG 可用于 Word、WPS 或答辩 PPT。
- 实验结果表、三线表和算法伪代码仍建议在 LaTeX 中手工排版，而不是用框图表达。
- PDF 页面级视觉验收见 `thesis_figure_visual_acceptance.md`，快照位于 `thesis_figures_pdf_snapshots/`。
