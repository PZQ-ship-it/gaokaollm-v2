# 最终论文人工占位与提交信息检查报告

本文档记录正式 LaTeX 终稿在提交前需要人工确认的非实验性信息。它不修改论文事实、不新增实验、不重跑 benchmark，也不替代 `thesis_latex_final_consistency_report.md` 和 `thesis_latex_pdf_visual_acceptance.md`。

## 1. 检查对象

| 项目 | 内容 |
| --- | --- |
| LaTeX 根目录 | `D:\毕设\latex-for-zju-master\latex-for-zju-master` |
| 主入口 | `zjuthesis.tex` |
| 正文入口 | `body/undergraduate/final/content.tex` |
| PDF 路径 | `D:\毕设\latex-for-zju-master\latex-for-zju-master\out\zjuthesis.pdf` |
| PDF 最近写入时间 | `2026-05-12 09:18:53` |
| 检查时间 | `2026-05-12` |

当前 `content.tex` 实际编译第 1-7 章、参考文献、实验材料附录和作者简历。`body/undergraduate/final/1-introduction.tex`、`body/undergraduate/final/2-body.tex` 是旧结构遗留文件，未被当前正文入口引用。

## 2. 必须人工确认

| 项目 | 位置 | 当前状态 | 建议 |
| --- | --- | --- | --- |
| 递交日期 | `zjuthesis.tex:25` | `SubmitDate = 递交日期` | 提交前按学院最终要求改成正式日期。 |
| 英文题名 | `zjuthesis.tex:36` | `TitleEng = {{Graduation Thesis Title}}` | 若模板或学院要求英文封面/英文题名，应替换为正式英文题名；若本科设计封面不使用该字段，也建议清理占位值，避免后续模板切换时泄漏。 |
| 致谢正文 | `body/undergraduate/final/thanksto.tex` | 目前只有“致谢”标题，无正文 | 提交前补正式致谢文本；如果学院允许空致谢，也建议明确确认。 |
| 作者简历 | `body/undergraduate/final/4-cv.tex` | 目前只有“作者简历”标题，无正文 | 按学院模板要求确认是否必须填写；若需要，应补教育经历、项目经历或获奖情况。 |

## 3. 建议修改或注意

| 项目 | 位置 | 说明 |
| --- | --- | --- |
| 研究生字段占位 | `zjuthesis.tex:34-35` | `Topic = 研究方向`、`ColaboratorName = 合作导师` 是 graduate-only 字段；当前 `Degree = undergraduate`，不影响本科终稿，但建议提交前清理或确认不会进入封面。 |
| 旧正文文件留空注释 | `body/undergraduate/final/2-body.tex` | 该文件未被 `content.tex` 引用，含多处“留空：此处可插入……”历史注释。它不影响当前 PDF，但后续不要再把该旧文件作为最终正文来源。 |
| 开题/中期材料中的“示例”字样 | `body/undergraduate/proposal/...` | 当前本科设计 final 模板仍附带开题/中期材料；其中“示例”多为中期报告正文内容，不是最终 7 章正文占位。提交前应按学院要求确认是否需要一并提交。 |

## 4. 已通过检查

| 检查项 | 结果 |
| --- | --- |
| 正文第 1-7 章 | 未发现 `TODO`、`FIXME`、`待补`、`占位`、`??`、`citation needed`、`TBD` 等明显占位符。 |
| 摘要与关键词 | 中英文摘要和关键词均存在。 |
| 附录边界说明 | 已写明 `implicit_flexibilities`、`volunteer_set`、`axis_flexibilities` 只用于模拟器/评测器，不进入被测 Agent。 |
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
| Underfull `\hbox` | 15 | 主要来自窄表格列或短中文短语断行松散。 |
| Underfull `\vbox` | 3 | 页面垂直排版松散。 |
| undefined reference / citation | 0 | 未发现未定义引用或文献。 |

## 6. 结论

当前终稿的实验事实、正文结构、引用编译和页面级视觉验收已经基本稳定。提交前最需要人工处理的是：正式递交日期、英文题名占位、致谢正文和作者简历。处理完这些人工信息后，建议重新编译 PDF，并同步更新 `thesis_latex_final_consistency_report.md`、`thesis_latex_pdf_visual_acceptance.md` 与 `thesis_final_submission_index.md` 中的 PDF 时间和检查结论。
