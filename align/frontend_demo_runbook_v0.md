---
stage: frontend_demo_runbook
stage_status: draft
created_at: 2026-06-01
related_brief: align/frontend_demo_design_brief_v0.md
demo_url: http://127.0.0.1:8000/demo
---

## 0. Recommended One-Command Startup

在项目根目录 `D:\gaokaollm-v2` 执行：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_demo_system.ps1
```

录制前如果想先用真实数据库和真实大模型跑一轮 smoke trace：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_demo_system.ps1 -SmokeTrace
```

只做依赖预检、不启动 API：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_demo_system.ps1 -NoApi
```

完整多轮真实回放并自动诊断：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\start_demo_system.ps1 -FullTrace -NoApi
```

脚本会自动设置 `DATABASE_URL`、清理离线兜底环境变量、设置 LLM timeout、确保 PostgreSQL ready，并在正常模式下启动 `http://127.0.0.1:8000/demo`。

# 前端交互演示录制 runbook v0

## 1. Preflight

在项目根目录 `D:\gaokaollm-v2` 执行。

```powershell
source activate gaokao_pg
$env:DATABASE_URL = "postgresql://postgres@127.0.0.1:55432/gaokao_recommendation"
```

如果当前 PowerShell 不支持 `source activate`，使用等价方式：

```powershell
cmd.exe /d /c "call C:\ProgramData\Anaconda3\Scripts\activate.bat gaokao_pg && python -c ""import main; print(main.app.title)"""
```

或直接调用环境内 Python：

```powershell
& "C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe" -c "import main; print(main.app.title)"
```

## 2. Start Database

```powershell
.\db\ensure_postgres.ps1
```

自检：

```powershell
& "C:\ProgramData\Anaconda3\envs\gaokao_pg\Library\bin\psql.exe" "$env:DATABASE_URL" -c "select count(*) from admission_scores;"
```

期望结果：`admission_scores = 140995`。

## 3. Start API

为让演示更像“真实系统现场跑一次”，建议打开真实 LLM 生成追问；候选和探针仍来自真实 PostgreSQL。

```powershell
Remove-Item Env:\GAOKAOLLM_OFFLINE_DETERMINISTIC -ErrorAction SilentlyContinue
Remove-Item Env:\GAOKAOLLM_SKIP_LLM_PARETO_QUESTION -ErrorAction SilentlyContinue
$env:OPENAI_TIMEOUT = "120"
$env:OPENAI_STRUCTURED_TIMEOUT = "120"
$env:OPENAI_REASONING_TIMEOUT = "180"
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

如果不用 `source activate`：

```powershell
Remove-Item Env:\GAOKAOLLM_OFFLINE_DETERMINISTIC -ErrorAction SilentlyContinue
Remove-Item Env:\GAOKAOLLM_SKIP_LLM_PARETO_QUESTION -ErrorAction SilentlyContinue
$env:OPENAI_TIMEOUT = "120"
$env:OPENAI_STRUCTURED_TIMEOUT = "120"
$env:OPENAI_REASONING_TIMEOUT = "180"
& "C:\ProgramData\Anaconda3\envs\gaokao_pg\python.exe" -m uvicorn main:app --host 127.0.0.1 --port 8000
```

自检：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
```

## 4. Open Demo

浏览器打开：

```text
http://127.0.0.1:8000/demo
```

推荐录制分辨率：`1440 x 900` 或更宽。

## 5. Recommended Script

首轮点击“医学样例”，或输入：

```text
我是浙江考生，分数600，选科物理、化学、生物，想读医学相关专业，只看江浙沪的学校，预算每年5500元以内。
```

录制重点：

- 左侧显示分数、专业、预算、选科等约束锁定。
- 中间出现真实系统问题，而不是静态文字。
- 右侧显示 UCB 目标维度、探针计划、BT 初始权重。
- 候选区先展示当前硬约束范围内前几个候选，再突出一个放宽后发现的引导候选。
- 讲解放宽引导候选时，重点说清楚“放宽了什么”和“换来了什么”，例如学校层次/排名更高、985/211/双一流标签、学科质量或就业画像更强。
- 候选卡片展示学校、专业、地域、最低分/位次、学费或风险字段，强调事实来自数据库探针。

第二轮点击“偏向接受”。

录制重点：

- 状态显示 `resume`。
- 轮次从 `0` 变成 `1`。
- `preference_tracker` 变成 `updated`。
- BT 权重条发生变化。
- 系统生成下一轮取舍问题。
- 放宽引导候选或问题解释随反馈进入下一轮，体现系统不是静态推荐列表。

## 5.1 Algorithm Notes

- 600 分样例的位次直接显示估计结果 `r=52529`。
- 当前候选不是按分数线直接截断，而是先按非分数硬条件召回，再按 `c/r` 分成冲、稳、保。
- 每个桶内按当前 `_implicit_utility` 排序取 Top 3；录制时可以强调“用户反馈改变权重后，下一轮排序会随权重变化”。
- `c/r` 越小表示候选历史位次要求越靠前，风险更高；`c/r` 越大表示更偏稳妥。

## 5.2 Real DB Trace Check

Git Bash 下可在录制前跑一次真实库自动交互审计：

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./db/ensure_postgres.ps1
export DATABASE_URL='postgresql://postgres@127.0.0.1:55432/gaokao_recommendation'
export GAOKAOLLM_OFFLINE_DETERMINISTIC=1

/c/ProgramData/Anaconda3/envs/gaokao_pg/python.exe scripts/run_demo_trace.py \
  --mode probe-audit \
  --turn-timeout-seconds 90 \
  --output outputs/demo_trace/probe_audit_realdb_latest.json

/c/ProgramData/Anaconda3/envs/gaokao_pg/python.exe scripts/run_demo_trace.py \
  --mode graph \
  --max-turns 4 \
  --turn-timeout-seconds 90 \
  --output outputs/demo_trace/graph_realdb_offline_latest.json
```

期望两条命令都输出 `status: ok`。`graph_realdb_offline_latest.json` 会记录每轮 probe、候选数、放宽成本维度、被屏蔽维度和最终是否进入全局推荐。

## 6. Known Boundaries

- 这个 demo 是真实服务驱动，但不是生产级部署。
- `GAOKAOLLM_OFFLINE_DETERMINISTIC=1` 会让显式约束、探针规划和提问文案都走确定性兜底；录制真实交互时不要设置它。
- `GAOKAOLLM_SKIP_LLM_PARETO_QUESTION=1` 会强制追问文案走本地兜底；录制真实交互时不要设置它。
- 真实 LLM 模式可能更慢，录制前要提前预跑一遍同样输入。
- 不要在录制中展示 `.env`、`auth.json`、API key 或数据库凭据。
- 如果 `/api/v1/chat` 报 `ConnectionTimeout`，先运行 `.\db\ensure_postgres.ps1`；它会检查 55432 和 SQL 健康状态，必要时自动启动 PostgreSQL。

## 7. Stop Services

停止 FastAPI：在启动服务的终端按 `Ctrl+C`。

停止 PostgreSQL：

```powershell
.\db\stop_postgres.ps1
```
