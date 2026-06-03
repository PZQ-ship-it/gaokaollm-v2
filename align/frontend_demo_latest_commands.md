---
stage: frontend_demo_runtime_commands
stage_status: active
updated_at: 2026-06-03
demo_url: http://127.0.0.1:8000/demo
---

# 前端演示最新版运行命令

以下命令默认在 Git Bash 中执行，项目根目录为：

```bash
cd /d/gaokaollm-v2
source activate gaokao_pg
```

## 1. 录制前完整预检

真实数据库 + 真实大模型 + 多轮 trace + 自动诊断：

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/start_demo_system.ps1 -FullTrace -NoApi
```

预期结果：

- `startup_full_trace_latest.json` 的 `status` 为 `ok`
- `startup_agent_diagnosis_latest.json` 无 root cause
- focused candidates 不再出现 `missing_knowledge_embedding`

输出文件：

```text
outputs/demo_trace/startup_full_trace_latest.json
outputs/demo_trace/startup_agent_diagnosis_latest.json
outputs/demo_trace/startup_agent_diagnosis_latest.md
```

## 2. 启动正式演示系统

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/start_demo_system.ps1
```

启动成功后打开：

```text
http://127.0.0.1:8000/demo
```

## 3. 可选命令

只检查数据库、Python/FastAPI 环境，不跑 LLM、不启动 API：

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/start_demo_system.ps1 -NoApi
```

只跑一轮真实 smoke trace：

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/start_demo_system.ps1 -SmokeTrace -NoApi
```

单独配置 PowerShell 中文 UTF-8：

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/configure_powershell_utf8.ps1
```

回滚 PowerShell UTF-8 配置：

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./scripts/configure_powershell_utf8.ps1 -Revert
```

## 4. 停止服务

FastAPI 服务在启动终端按 `Ctrl+C` 停止。

如果服务是后台启动或端口已被占用，可先按端口查出当前进程。下面命令默认查 `8000` 端口：

```bash
powershell.exe -NoProfile -Command '$ports = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue; $pids = $ports | Select-Object -ExpandProperty OwningProcess -Unique; foreach ($pidValue in $pids) { Get-CimInstance Win32_Process | Where-Object { $_.ProcessId -eq $pidValue } | Select-Object ProcessId,CommandLine | Format-List }'
```

确认输出是本项目的 `uvicorn main:app --host 127.0.0.1 --port 8000` 后，再停止这些进程：

```bash
powershell.exe -NoProfile -Command '$ports = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue; $pids = $ports | Select-Object -ExpandProperty OwningProcess -Unique; foreach ($pidValue in $pids) { Stop-Process -Id $pidValue }'
```

如需停止项目 PostgreSQL：

```bash
powershell.exe -NoProfile -ExecutionPolicy Bypass -File ./db/stop_postgres.ps1
```
