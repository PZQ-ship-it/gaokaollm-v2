# LLM Lane Healthcheck

- created_at: `2026-05-17T11:20:51Z`
- overall: `ok`

| lane | provider | stage | model | status | seconds | detail |
| --- | --- | --- | --- | --- | ---: | --- |
| aliyun_1 | aliyun | embedding | text-embedding-v3 | OK | 0.250 | dim=1024 |
| aliyun_1 | aliyun | model_chat | MiniMax-M2.5 | OK | 5.313 | OK |
| aliyun_1 | aliyun | model_chat | deepseek-v3.2 | OK | 1.140 | OK |
| aliyun_1 | aliyun | model_chat | glm-5.1 | OK | 3.297 | OK |
| aliyun_1 | aliyun | model_chat | kimi-k2.6 | OK | 1.219 | OK |
| aliyun_1 | aliyun | model_chat | qwen3.6-plus | OK | 4.031 | OK |
| aliyun_1 | aliyun | rerank | qwen3-rerank | OK | 0.203 | results=1 score=0.4473199723605405 |
| aliyun_1 | aliyun | small_chat | deepseek-v4-flash | OK | 2.578 | OK |
| aliyun_2 | aliyun | embedding | text-embedding-v3 | OK | 0.375 | dim=1024 |
| aliyun_2 | aliyun | model_chat | MiniMax-M2.5 | OK | 2.359 | OK |
| aliyun_2 | aliyun | model_chat | deepseek-v3.2 | OK | 1.407 | OK |
| aliyun_2 | aliyun | model_chat | glm-5.1 | OK | 4.250 | OK |
| aliyun_2 | aliyun | model_chat | kimi-k2.6 | OK | 1.562 | OK |
| aliyun_2 | aliyun | model_chat | qwen3.6-plus | OK | 4.063 | OK |
| aliyun_2 | aliyun | rerank | qwen3-rerank | OK | 0.250 | results=1 score=0.45073644091530585 |
| aliyun_2 | aliyun | small_chat | deepseek-v4-flash | OK | 2.562 | OK |
| siliconflow_1 | siliconflow | embedding | Qwen/Qwen3-Embedding-8B | OK | 0.406 | dim=4096 |
| siliconflow_1 | siliconflow | model_chat | Pro/MiniMaxAI/MiniMax-M2.5 | OK | 1.578 | OK |
| siliconflow_1 | siliconflow | model_chat | Pro/deepseek-ai/DeepSeek-V3.2 | OK | 3.000 | OK |
| siliconflow_1 | siliconflow | model_chat | Pro/moonshotai/Kimi-K2.6 | OK | 7.094 | OK |
| siliconflow_1 | siliconflow | model_chat | Pro/zai-org/GLM-5.1 | OK | 3.234 | OK |
| siliconflow_1 | siliconflow | model_chat | Qwen/Qwen3.6-35B-A3B | OK | 16.828 |  |
| siliconflow_1 | siliconflow | rerank | Qwen/Qwen3-Reranker-8B | OK | 0.266 | results=1 score=0.13058456778526306 |
| siliconflow_1 | siliconflow | small_chat | deepseek-ai/DeepSeek-V4-Flash | OK | 2.672 | OK |
| siliconflow_2 | siliconflow | embedding | Qwen/Qwen3-Embedding-8B | OK | 0.610 | dim=4096 |
| siliconflow_2 | siliconflow | model_chat | Pro/MiniMaxAI/MiniMax-M2.5 | OK | 1.172 | OK |
| siliconflow_2 | siliconflow | model_chat | Pro/deepseek-ai/DeepSeek-V3.2 | OK | 3.390 | OK |
| siliconflow_2 | siliconflow | model_chat | Pro/moonshotai/Kimi-K2.6 | OK | 1.344 | OK |
| siliconflow_2 | siliconflow | model_chat | Pro/zai-org/GLM-5.1 | OK | 2.703 | OK |
| siliconflow_2 | siliconflow | model_chat | Qwen/Qwen3.6-35B-A3B | OK | 0.359 |  |
| siliconflow_2 | siliconflow | rerank | Qwen/Qwen3-Reranker-8B | OK | 0.281 | results=1 score=0.13253025710582733 |
| siliconflow_2 | siliconflow | small_chat | deepseek-ai/DeepSeek-V4-Flash | OK | 2.672 | OK |
