# LLM Lane Healthcheck

- created_at: `2026-05-17T18:58:12Z`
- overall: `ok`

| lane | provider | stage | model | status | seconds | detail |
| --- | --- | --- | --- | --- | ---: | --- |
| aliyun_1 | aliyun | embedding | text-embedding-v3 | OK | 0.203 | dim=1024 |
| aliyun_1 | aliyun | model_chat | MiniMax-M2.5 | OK | 6.203 | OK |
| aliyun_1 | aliyun | model_chat | deepseek-v3.2 | OK | 1.344 | OK |
| aliyun_1 | aliyun | model_chat | glm-5.1 | OK | 3.125 | OK |
| aliyun_1 | aliyun | model_chat | kimi-k2.6 | OK | 0.609 | OK |
| aliyun_1 | aliyun | model_chat | qwen3.6-plus | OK | 5.047 | OK |
| aliyun_1 | aliyun | rerank | qwen3-rerank | OK | 0.266 | results=1 score=0.4507364055964534 |
| aliyun_1 | aliyun | small_chat | deepseek-v4-flash | OK | 2.875 | OK |
| aliyun_2 | aliyun | embedding | text-embedding-v3 | OK | 0.203 | dim=1024 |
| aliyun_2 | aliyun | model_chat | MiniMax-M2.5 | OK | 1.750 | OK |
| aliyun_2 | aliyun | model_chat | deepseek-v3.2 | OK | 2.515 | OK |
| aliyun_2 | aliyun | model_chat | glm-5.1 | OK | 3.078 | OK |
| aliyun_2 | aliyun | model_chat | kimi-k2.6 | OK | 0.594 | OK |
| aliyun_2 | aliyun | model_chat | qwen3.6-plus | OK | 4.344 | OK |
| aliyun_2 | aliyun | rerank | qwen3-rerank | OK | 0.250 | results=1 score=0.45073644091530585 |
| aliyun_2 | aliyun | small_chat | deepseek-v4-flash | OK | 2.766 | OK |
| siliconflow_1 | siliconflow | embedding | Qwen/Qwen3-Embedding-8B | OK | 1.297 | dim=4096 |
| siliconflow_1 | siliconflow | model_chat | Pro/MiniMaxAI/MiniMax-M2.5 | OK | 1.547 | OK |
| siliconflow_1 | siliconflow | model_chat | Pro/deepseek-ai/DeepSeek-V3.2 | OK | 0.969 | OK |
| siliconflow_1 | siliconflow | model_chat | Pro/moonshotai/Kimi-K2.6 | OK | 1.422 | OK |
| siliconflow_1 | siliconflow | model_chat | Pro/zai-org/GLM-5.1 | OK | 2.843 | OK |
| siliconflow_1 | siliconflow | model_chat | Qwen/Qwen3.6-35B-A3B | OK | 0.250 |  |
| siliconflow_1 | siliconflow | rerank | Qwen/Qwen3-Reranker-8B | OK | 0.234 | results=1 score=0.13253727555274963 |
| siliconflow_1 | siliconflow | small_chat | deepseek-ai/DeepSeek-V4-Flash | OK | 2.266 | OK |
| siliconflow_2 | siliconflow | embedding | Qwen/Qwen3-Embedding-8B | OK | 0.719 | dim=4096 |
| siliconflow_2 | siliconflow | model_chat | Pro/MiniMaxAI/MiniMax-M2.5 | OK | 1.063 | OK |
| siliconflow_2 | siliconflow | model_chat | Pro/deepseek-ai/DeepSeek-V3.2 | OK | 2.297 | OK |
| siliconflow_2 | siliconflow | model_chat | Pro/moonshotai/Kimi-K2.6 | OK | 1.422 | OK |
| siliconflow_2 | siliconflow | model_chat | Pro/zai-org/GLM-5.1 | OK | 2.437 | OK |
| siliconflow_2 | siliconflow | model_chat | Qwen/Qwen3.6-35B-A3B | OK | 0.281 |  |
| siliconflow_2 | siliconflow | rerank | Qwen/Qwen3-Reranker-8B | OK | 0.265 | results=1 score=0.12853741645812988 |
| siliconflow_2 | siliconflow | small_chat | deepseek-ai/DeepSeek-V4-Flash | OK | 2.375 | OK |
