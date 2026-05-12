# 最终论文人工占位与提交信息检查报告

本文档记录正式 LaTeX 终稿在提交前需要人工确认的非实验性信息。它不修改论文事实、不新增实验、不重跑 benchmark，也不替代 `thesis_latex_final_consistency_report.md` 和 `thesis_latex_pdf_visual_acceptance.md`。

## 1. 检查对象

| 项目 | 内容 |
| --- | --- |
| LaTeX 根目录 | `D:\毕设\latex-for-zju-master\latex-for-zju-master` |
| 主入口 | `zjuthesis.tex` |
| 正文入口 | `body/undergraduate/final/content.tex` |
| PDF 路径 | `D:\毕设\latex-for-zju-master\latex-for-zju-master\out\zjuthesis.pdf` |
| PDF 大小 | `3,578,565` bytes |
| PDF 最近写入时间 | `2026-05-12 12:01:56` |
| 检查时间 | `2026-05-12` |

当前 `content.tex` 实际编译第 1-7 章、参考文献、实验材料附录和作者简历。`body/undergraduate/final/1-introduction.tex`、`body/undergraduate/final/2-body.tex` 是旧结构遗留文件，未被当前正文入口引用。

## 2. 已补齐但提交前仍建议人工核对

| 项目 | 位置 | 当前状态 | 建议 |
| --- | --- | --- | --- |
| 递交日期 | `zjuthesis.tex:25` | 已设为 `SubmitDate = 2026年5月12日` | 若学院要求实际提交日或系统填报日期，提交前只需替换该字段并重编译。 |
| 英文题名 | `zjuthesis.tex:36` | 已设为 `Design of a Data-Driven Preference Compromise Agent and Benchmark for Gaokao College Application Decisions` | 若学院要求英文题名或英文封面，建议导师确认该译名；若模板不使用该字段，也已清理原占位。 |
| 致谢正文 | `body/undergraduate/final/thanksto.tex` | 已补正式致谢正文 | 提交前可按个人真实情况微调致谢对象和措辞。 |
| 作者简历 | `body/undergraduate/final/4-cv.tex` | 已补简短作者简历 | 当前简历只使用已知公开事实，不虚构奖项、论文或实习经历；提交前按学院要求确认是否需要增删。 |

## 3. 建议修改或注意

| 项目 | 位置 | 说明 |
| --- | --- | --- |
| 研究生字段占位 | `zjuthesis.tex:34-35` | `Topic = 研究方向`、`ColaboratorName = 合作导师` 是 graduate-only 字段；当前 `Degree = undergraduate`，不影响本科终稿，但提交前可确认不会进入封面。 |
| 旧正文文件留空注释 | `body/undergraduate/final/2-body.tex` | 该文件未被 `content.tex` 引用，含历史留空注释；不影响当前 PDF，后续不要再把该旧文件作为最终正文来源。 |
| 开题/中期材料中的“示例”字样 | `body/undergraduate/proposal/...` | 当前本科设计 final 模板仍附带开题/中期材料；其中“示例”多为中期报告正文内容，不是最终 7 章正文占位。提交前按学院要求确认是否需要一并提交。 |

## 4. 已通过检查

| 检查项 | 结果 |
| --- | --- |
| 正文第 1-7 章 | 未发现 `TODO`、`FIXME`、`待补`、`占位`、`??`、`citation needed`、`TBD` 等明显占位符。 |
| 摘要与关键词 | 中英文摘要和关键词均存在。 |
| 附录边界说明 | 已写明 `implicit_flexibilities`、`volunteer_set`、`axis_flexibilities` 只用于模拟器/评测器，不进入被测 Agent。 |
| `v1_hybrid_rag` pilot | 已进入第 6 章和附录索引；它是软约束 RAG / 冲稳保推荐 pilot 基线，不进入七组正式实验主表。 |
| 专业树全量覆盖 v2 | 正文保留 `22,759 / 22,759`、`140,995 / 140,995` 与 `remaining_unassigned = 0` 的可审计挂载覆盖口径。 |
| 多轴压力测试 | `multi_axis_v2` 仍写作压力测试修正版，不进入七组正式实验主表。 |
| 参考文献编译 | 编译日志未发现 undefined citations。 |
| 交叉引用 | 编译日志未发现 undefined references。 |
| PDF 编译 | `zjuthesis.pdf` 已生成，无 LaTeX fatal error。 |
| 版式溢出 | 编译日志中 Overfull `\hbox` 为 0。 |

## 5. 编译日志摘要

| 类型 | 数量 | 说明 |
| --- | ---: | --- |
| LaTeX Warning | 1 | 模板类加载提示。 |
| Package Warning | 1 | `xeCJK` 字体族重定义提示。 |
| Overfull `\hbox` | 0 | 未发现明显水平溢出。 |
| Underfull `\hbox` | 17 | 主要来自窄表格列、附录路径和短中文短语断行松散。 |
| Underfull `\vbox` | 3 | 页面垂直排版松散。 |
| undefined reference / citation | 0 | 未发现未定义引用或文献。 |

## 6. 结论

当前终稿的人工占位字段已补齐，实验事实、正文结构、引用编译和页面级视觉验收保持稳定。最新 PDF 已包含 `v1_hybrid_rag` pilot 补充基线、正式递交日期、英文题名、致谢正文和作者简历，并通过重新编译与最新页面快照复查。提交前最后建议人工核对学院实际日期要求、英文题名译法、致谢措辞和作者简历是否符合学院模板。
