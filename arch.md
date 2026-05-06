gaokao_agent_project/
├── app/
│   ├── api/               # 🤵【表现层 / 服务员】(接单与响应)
│   │   └── chat_api.py    # FastAPI 路由。只负责接收 HTTP 请求与 thread_id，无业务逻辑。
│   │
│   ├── graphs/            # 🧠【编排层 / 主厨与大堂经理】(状态流转与 AI 交互)
│   │   ├── nodes/         # 独立节点函数
│   │   │   ├── gatekeeper.py # 动作1：底线守门员 (调 LLM 提取意图 -> 调 flows 查基准)
│   │   │   ├── radar.py      # 动作2：机会雷达 (调度 flows 里的并发 SQL 探针)
│   │   │   └── negotiator.py # 动作3：谈判官 (汇总探针结果，调 LLM 生成权衡话术)
│   │   └── workflow.py    # 组装 LangGraph，配置动态路由，挂载 Checkpointer (事件溯源记事本)
│   │
│   ├── flows/             # 🏭【流水线层 / 后厨】(确定性、0 幻觉的核心引擎)
│   │   └── probers.py     # 动作2底层：纯粹的异步 SQL 组合查询。绝对禁止引入大模型！
│   │
│   ├── core/              # ⚙️【基础设施层 / 厨房设备】(外部依赖封装)
│   │   ├── db_pg.py       # PostgreSQL + pgvector 异步连接池封装。
│   │   ├── llm_client.py  # 大模型统一调用入口。
│   │   └── prompts.py     # 集中管理所有 System Prompts。
│   │
│   └── schemas/           # 📜【数据契约层 / 菜单规范】(极致轻量，系统流通标准)
│       ├── state.py       # 定义 LangGraph 的 AgentState (包含约束、分数浪费、探针信道)
│       └── models.py      # 定义 Pydantic 模型 (UserConstraints, API Request)
│
├── tests/                 # 🧪 对应每一个迭代的验证脚本 (TDD 核心)
└── main.py                # 🚀 FastAPI 启动入口