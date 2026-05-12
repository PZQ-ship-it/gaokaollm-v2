# LaTeX 终稿 PDF 页面级视觉验收报告

本文档记录对正式 LaTeX 终稿 PDF 的页面级视觉验收。它补充 `thesis_latex_final_consistency_report.md`：后者关注事实一致性与编译日志，本报告关注真实 PDF 页面中封面、摘要、目录、图表和附录是否存在裁切、重叠、乱码或旧口径残留。

本轮只做视觉验收与入口同步，不新增实验、不改 benchmark、不改专业树 artifact、不更新 thesis audit。

## 1. 验收对象

| 项目 | 内容 |
| --- | --- |
| LaTeX 根目录 | `D:\毕设\latex-for-zju-master\latex-for-zju-master` |
| PDF 路径 | `D:\毕设\latex-for-zju-master\latex-for-zju-master\out\zjuthesis.pdf` |
| PDF 页数 | 78 |
| PDF 大小 | `3,578,125` bytes |
| PDF 最近写入时间 | `2026-05-12 21:17:38` |
| 快照目录 | `gaokaollm_bench/outputs/thesis_latex_pdf_snapshots/` |
| 渲染工具 | `pdftoppm` |
| 渲染分辨率 | 144 dpi |

本次快照已基于最新 PDF 重新渲染，覆盖封面、致谢、中英文摘要、目录、四张核心图、专业层级本体表、七组实验表、`v1_hybrid_rag` pilot 对照表、多轴压力测试表、附录边界说明和作者简历。

## 2. 页面快照清单

| PDF 物理页 | 快照 | 验收范围 | 视觉结论 |
| ---: | --- | --- | --- |
| 1 | `thesis_latex_pdf_snapshots/page_01-01.png` | 封面 | 通过。题名三行下划线显示完整，无明显水平溢出。 |
| 5 | `thesis_latex_pdf_snapshots/page_05-05.png` | 致谢页 | 通过。致谢正文已补齐，段落排版正常，未发现裁切、重叠或乱码。 |
| 7 | `thesis_latex_pdf_snapshots/page_07-07.png` | 中文摘要 | 通过。摘要已按自查清单改为三段式，关键词和页眉页脚显示正常。 |
| 9 | `thesis_latex_pdf_snapshots/page_09-09.png` | 英文摘要 | 通过。英文摘要已与中文摘要同步，未见裁切或关键词异常。 |
| 11 | `thesis_latex_pdf_snapshots/page_11-11.png` | 目录首页 | 通过。目录层级、页码和标题对齐正常。 |
| 29 | `thesis_latex_pdf_snapshots/page_29-29.png` | 图 4.1 数据 + Agent + Benchmark 总体架构图 | 通过。图像居中，无裁切；节点使用新 MAS 口径。 |
| 32 | `thesis_latex_pdf_snapshots/page_32-32.png` | 图 4.2 专业层级本体全量覆盖 v2 局部可视化起始页 | 通过。图像无裁切；专业层级本体和可审计挂载边界可读。 |
| 33 | `thesis_latex_pdf_snapshots/page_33-33.png` | 图 4.2 专业层级本体全量覆盖 v2 局部可视化续页 | 通过。典型分支说明未重叠，未暗示全部语义边界已人工逐条确认。 |
| 34 | `thesis_latex_pdf_snapshots/page_34-34.png` | 图 4.3 经人工审校的地域层级画像局部可视化、图 4.4 起始 | 通过。地理邻近层级与城市层级画像并排展示；未把城市层级写成客观收益。 |
| 35 | `thesis_latex_pdf_snapshots/page_35-35.png` | 图 4.4 Benchmark 多轮评测流程图、图 4.5 起始 | 通过。hidden persona 边界清楚，图像未裁切。 |
| 36 | `thesis_latex_pdf_snapshots/page_36-36.png` | 图 4.5 数据证据层与放宽能力映射图 | 通过。映射关系完整，未出现旧三段式 Agent 主叙述。 |
| 37 | `thesis_latex_pdf_snapshots/page_37-37.png` | 图 5.1 轻量 MAS / 多角色 Agent 工作流图 | 通过。包含前置语义归一层、LLM 引导机会规划器、确定性证据探针和证据谈判器；hidden fields 不进入 Agent 的边界清楚。 |
| 43 | `thesis_latex_pdf_snapshots/page_43-43.png` | 第 6 章开头与专业树全量覆盖 v2 描述 | 通过。`22,759 / 22,759`、`140,995 / 140,995` 与剩余未挂载为 0 的事实显示正常。 |
| 44 | `thesis_latex_pdf_snapshots/page_44-44.png` | 表 6.1 专业层级本体全量覆盖 v2 结果 | 通过。表格未越界；全覆盖口径与“不等于全部语义边界人工确认”的说明衔接正常。 |
| 45 | `thesis_latex_pdf_snapshots/page_45-45.png` | 表 6.2 与表 6.3 专业树标注方法/Top-k 结果 | 通过。两张表未裁切，指标可读。 |
| 48 | `thesis_latex_pdf_snapshots/page_48-48.png` | 表 6.5 七组正式实验结果、表 6.6 `v1_hybrid_rag` pilot 对照结果 | 通过。新增 pilot 表无裁切、无重叠；`v1_hybrid_rag` 明确位于七组正式实验表之后，未进入七组实验主表。长字段在段落中有自然换行，但未越界。 |
| 50 | `thesis_latex_pdf_snapshots/page_50-50.png` | 表 6.7 多轴隐藏妥协压力测试 v1/v2 对照结果 | 通过。`multi_axis_v2` 仅作为压力测试修正版出现，未进入七组实验主表。 |
| 57 | `thesis_latex_pdf_snapshots/page_57-57.png` | 附录实验材料说明与 hidden persona 边界 | 通过。新增 `agent_benchmark_v1_hybrid_rag_pilot_evidence.md` 索引可读；`implicit_flexibilities`、`volunteer_set`、`axis_flexibilities` 被明确写作评测端字段，不作为 Agent 输入。 |
| 61 | `thesis_latex_pdf_snapshots/page_61-61.png` | 作者简历 | 通过。作者简历正文已补齐，内容留白正常，未发现裁切、重叠或乱码。 |

## 3. 关键口径复核

| 检查项 | 结果 |
| --- | --- |
| 新 MAS 口径：前置语义归一层、约束解析器、LLM 引导的机会规划器、确定性证据探针、证据谈判器 | 通过 |
| LLM 只负责归一、规划、排序和澄清提示，不生成事实候选 | 通过 |
| 专业层级本体全量覆盖 v2：`22,759 / 22,759`、`140,995 / 140,995`、剩余未挂载为 0 | 通过 |
| 七组实验主表仍保持主实验 + 五组扩展实验口径 | 通过 |
| `v1_hybrid_rag` 是软约束 RAG / 冲稳保推荐 pilot 基线，不进入七组实验主表 | 通过 |
| `multi_axis_v2` 写作 Benchmark 压力测试修正版，不进入七组实验主表 | 通过 |
| hidden persona 字段不进入 Agent | 通过 |
| 封面、摘要、目录、核心图、关键表和附录未发现明显裁切或重叠 | 通过 |
| 致谢页和作者简历页已对应最新 PDF 快照 | 通过 |

## 4. 剩余视觉风险

- 图 4.1、图 4.2、图 4.3 与图 5.1 内部辅助文字相对较小，但在 PDF 快照中未出现裁切或重叠；正文段落已承担主要解释功能。答辩 PPT 中建议直接使用原始 SVG/PNG 放大展示。
- 第 6 章 `v1_hybrid_rag` pilot 段落包含较长模型名和字段名，PDF 中出现自然换行；当前未观察到裁切、重叠或越界。如后续追求更细排版，可将模型名移至脚注或附录。
- 本报告只抽查论文提交前最关键页面，不替代逐页人工通读。若后续修改 LaTeX 图表、章节结构、致谢、作者简历或实验表，应重新渲染快照并更新本报告。
- 当前 PDF 编译事实仍以 `thesis_latex_final_consistency_report.md` 为准；该报告显示无 LaTeX fatal error、无 undefined references / citations、无 overfull `\hbox`。

## 5. 结论

本次页面级视觉验收通过。当前 `zjuthesis.pdf` 的核心提交页面未发现明显裁切、重叠、乱码或旧 MAS 口径回退；致谢和作者简历已补齐并通过页面快照复查；专业树全量覆盖 v2、七组实验、`v1_hybrid_rag` pilot 基线、`multi_axis_v2` 压力测试和 hidden persona 边界均能在 PDF 页面中复查。


