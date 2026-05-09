# 高考志愿推荐系统数据库

这个目录包含 PostgreSQL + pgvector 的数据库初始化脚本，用来承载当前浙江高考志愿推荐数据。

本项目内已经放置一份本地可运行的数据快照：

```text
postgres/data/
```

该快照复制自：

```text
D:\BaiduNetdiskDownload\浙江\postgres\data
```

`postgres/data/` 约 1.27GB，只作为本机运行数据目录使用，已经在项目 `.gitignore` 中排除，不应提交到 Git。

## 文件

- `migrations/001_init_gaokao_schema.sql`：创建核心表、推荐支撑表、pgvector 知识库表、外键、约束和索引。
- `import_data.py`：从浙江数据 Excel 文件导入结构化表。
- `start_postgres.ps1` / `stop_postgres.ps1`：启动和停止项目内 `postgres/data/` 快照。

## 执行方式

当前本机环境：

- Conda 环境名：`gaokao_pg`
- PostgreSQL：17.9
- pgvector：0.8.1
- 数据库名：`gaokao_recommendation`
- 连接地址：`postgresql://postgres@127.0.0.1:55432/gaokao_recommendation`
- 本地数据目录：`postgres/data`

在项目根目录确认环境变量：

```powershell
$env:DATABASE_URL = "postgresql://postgres@127.0.0.1:55432/gaokao_recommendation"
```

启动本地 PostgreSQL：

```powershell
.\db\start_postgres.ps1
```

停止本地 PostgreSQL：

```powershell
.\db\stop_postgres.ps1
```

说明：Windows 沙箱或部分终端中 `pg_ctl` 可能因为 restricted token 无法启动服务；`start_postgres.ps1`
已经包含 `postgres.exe` 直接启动兜底，并把 PID 写到 `postgres/postgres.pid`，`stop_postgres.ps1`
会优先 `pg_ctl stop`，失败时再停止该 PID。

启动后快速自检：

```powershell
psql "$env:DATABASE_URL" -c "select count(*) from admission_scores;"
```

确认目标库已经安装 pgvector 后执行：

```powershell
psql "$env:DATABASE_URL" -f .\db\migrations\001_init_gaokao_schema.sql
```

如果不用 `DATABASE_URL`：

```powershell
psql -h localhost -U postgres -d gaokao_recommendation -f .\db\migrations\001_init_gaokao_schema.sql
```

## 设计说明

- 精确推荐走结构化表：`admission_plans`、`admission_scores`、`score_rank_segments`、`batch_lines`。
- 学校和专业统一映射走维表：`schools`、`school_codes`、`majors`。
- 推荐解释、院校简介、专业介绍、就业信息、招生章程等文本走 `knowledge_documents`，embedding 默认使用 `vector(1536)`。
- 每张导入型事实表都保留 `raw jsonb`，方便追溯 Excel 原始字段和后续修正清洗规则。

## 后续导入建议

1. 先导入 `schools`、`school_codes`、`majors`。
2. 再导入一分一段、批次线、招生计划、专业分数和院校分数。
3. 最后导入专业就业、院校专业实力、特殊招生和知识库文本。

已有 `postgres/data/` 快照时，不需要重新执行 migration 或导入脚本；只有在重建数据库或更新 Excel 原始数据时才需要按上述顺序重新导入。
