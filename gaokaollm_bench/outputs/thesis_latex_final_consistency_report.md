# LaTeX 终稿事实一致性验收报告

本文档记录对浙江大学 LaTeX 模板终稿的事实一致性验收。验收对象为：

- LaTeX 根目录：`D:\毕设\latex-for-zju-master\latex-for-zju-master`
- 主入口：`zjuthesis.tex`
- 正文入口：`body/undergraduate/final/content.tex`
- 事实源：`thesis_claims_manifest.json`、`thesis_document_hub.md`、`major_tree_annotation_summary.md`、`thesis_final_assembly_checklist.md`

本轮只做验收与报告，不新增实验、不改 benchmark、不改专业树 artifact、不更新 thesis audit。

## 1. 模板与章节结构

| 检查项 | 结果 |
| --- | --- |
| `Degree = undergraduate` | 通过 |
| `Type = design` | 通过 |
| `Period = final` | 通过 |
| 正文入口包含第 1-7 章 | 通过 |
| 摘要、参考文献、附录、个人简历入口 | 通过 |

`body/undergraduate/final/content.tex` 当前依次输入：

1. `chapters/01-introduction`
2. `chapters/02-related-work`
3. `chapters/03-v1-prototype`
4. `chapters/04-data-benchmark`
5. `chapters/05-agent-design`
6. `chapters/06-experiments`
7. `chapters/07-conclusion`

之后输出参考文献，并输入 `3-appendix` 与 `4-cv`。

## 2. 关键事实一致性

| 检查项 | 结果 | 位置说明 |
| --- | --- | --- |
| “数据 + Agent + Benchmark”三贡献结构 | 通过 | 摘要、第 1 章、第 7 章 |
| 新 MAS 口径：前置语义归一层、约束解析器、LLM 引导的机会规划器、确定性证据探针、证据谈判器 | 通过 | 摘要、第 1/2/5/7 章、附录边界说明 |
| LLM 不生成事实候选 | 通过 | 摘要、第 1/5/7 章 |
| Agent 不读取 hidden persona 字段 | 通过 | 附录明确 `implicit_flexibilities`、`volunteer_set`、`axis_flexibilities` 只供 simulator / evaluator 使用 |
| 专业层级本体全量覆盖 v2 | 通过 | 第 4/6 章 |
| `22,759 / 22,759` 原始去重专业名覆盖 | 通过 | 第 4/6 章 |
| `140,995 / 140,995` 录取记录覆盖 | 通过 | 第 4/6 章 |
| `remaining_unassigned = 0` 等价表述 | 通过 | 第 4/6 章写为“剩余未挂载为 0” |
| 七组实验主表 | 通过 | 第 6 章 |
| `multi_axis_v2` 压力测试 | 通过 | 摘要、第 6/7 章、附录 |
| `real-db-set-浙江-569-009` 失败样本 | 通过 | 摘要、第 6/7 章 |

说明：`reviewed v1`、地域树文件名等工程化旧术语仅出现在 `term_mapping.json` 的映射表中，属于允许保留的术语追溯位置；正文主叙述未发现这些旧口径残留。

## 3. 旧口径残留检查

| 旧口径 | 结果 |
| --- | --- |
| `六组实验` | 未发现 |
| `四组扩展实验` | 未发现 |
| `八组主实验` / `第八组主实验` | 未发现 |
| `地域树 reviewed v1` | 未在正文主叙述中发现 |
| `gatekeeper -> radar -> negotiator` 主叙述 | 未发现 |

当前 LaTeX 正文将 `multi_axis_v2` 写作轴一致性压力测试修正版，不进入七组实验主表；主实验仍为专业--地域联合放宽实验与风险组合放宽实验，五组扩展实验定位保持不变。

## 4. 编译结果

运行命令：

```powershell
latexmk -xelatex -outdir=out zjuthesis
```

结果：

- 编译成功，无 LaTeX fatal error。
- PDF 输出：`D:\毕设\latex-for-zju-master\latex-for-zju-master\out\zjuthesis.pdf`
- PDF 大小：`3,165,004` bytes
- 最近写入时间：`2026-05-12 06:22:11`
- `latexmk` 报告：`All targets (out/zjuthesis.xdv out/zjuthesis.pdf) are up-to-date`

日志 warning 摘要：

| 类型 | 数量 | 说明 |
| --- | ---: | --- |
| LaTeX Warning | 1 | 模板类加载提示 |
| Package Warning | 1 | `xeCJK` 字体族重定义提示 |
| Overfull `\hbox` | 5 | 主要是表格或长行版式问题 |
| Underfull `\hbox` | 15 | 主要是段落/表格断行松散 |
| Underfull `\vbox` | 4 | 页面垂直排版松散 |
| undefined reference / undefined citation | 0 | 未发现未定义引用或未定义文献 |

## 5. 剩余风险

- 仍有少量 overfull / underfull 版式 warning，后续可在最终排版阶段集中处理。
- 本报告只验证事实口径和编译状态，不替代导师对正文论证、参考文献完整性和格式细节的审阅。
- 若后续重跑实验、调整专业树或修改 `multi_axis_v2` 解释，应先更新 `thesis_claims_manifest.json`、`thesis_document_hub.md` 和 `major_tree_annotation_summary.md`，再重新执行本报告对应的检查。
