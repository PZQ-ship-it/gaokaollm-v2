# LLM Lane Healthcheck

- created_at: `2026-05-17T14:22:14Z`
- overall: `ok`

| lane | provider | stage | model | status | seconds | detail |
| --- | --- | --- | --- | --- | ---: | --- |
| aliyun_1 | aliyun | embedding | text-embedding-v3 | OK | 0.421 | dim=1024 |
| aliyun_1 | aliyun | model_chat | MiniMax-M2.5 | OK | 6.047 | OK |
| aliyun_1 | aliyun | model_chat | deepseek-v3.2 | OK | 1.016 | OK |
| aliyun_1 | aliyun | model_chat | glm-5.1 | OK | 2.719 | OK |
| aliyun_1 | aliyun | model_chat | kimi-k2.6 | OK | 0.593 | OK |
| aliyun_1 | aliyun | model_chat | qwen3.6-plus | OK | 4.204 | OK |
| aliyun_1 | aliyun | rerank | qwen3-rerank | OK | 0.266 | results=1 score=0.4473199723605405 |
| aliyun_1 | aliyun | small_chat | deepseek-v4-flash | OK | 3.296 | OK |
| aliyun_2 | aliyun | embedding | text-embedding-v3 | OK | 0.375 | dim=1024 |
| aliyun_2 | aliyun | model_chat | MiniMax-M2.5 | OK | 4.625 | OK |
| aliyun_2 | aliyun | model_chat | deepseek-v3.2 | OK | 1.328 | OK |
| aliyun_2 | aliyun | model_chat | glm-5.1 | OK | 2.656 | OK |
| aliyun_2 | aliyun | model_chat | kimi-k2.6 | OK | 5.187 | OK |
| aliyun_2 | aliyun | model_chat | qwen3.6-plus | OK | 4.094 | OK |
| aliyun_2 | aliyun | rerank | qwen3-rerank | OK | 0.281 | results=1 score=0.4507364055964534 |
| aliyun_2 | aliyun | small_chat | deepseek-v4-flash | OK | 3.375 | OK |
| siliconflow_1 | siliconflow | embedding | Qwen/Qwen3-Embedding-8B | OK | 1.390 | dim=4096 |
| siliconflow_1 | siliconflow | model_chat | Pro/MiniMaxAI/MiniMax-M2.5 | OK | 1.672 | OK |
| siliconflow_1 | siliconflow | model_chat | Pro/deepseek-ai/DeepSeek-V3.2 | OK | 0.969 | OK |
| siliconflow_1 | siliconflow | model_chat | Pro/moonshotai/Kimi-K2.6 | OK | 2.031 | OK |
| siliconflow_1 | siliconflow | model_chat | Pro/zai-org/GLM-5.1 | OK | 2.859 | OK |
| siliconflow_1 | siliconflow | model_chat | Qwen/Qwen3.6-35B-A3B | OK | 0.516 |  |
| siliconflow_1 | siliconflow | rerank | Qwen/Qwen3-Reranker-8B | OK | 0.282 | results=1 score=0.13433389365673065 |
| siliconflow_1 | siliconflow | small_chat | deepseek-ai/DeepSeek-V4-Flash | OK | 26.734 | OK |
| siliconflow_2 | siliconflow | embedding | Qwen/Qwen3-Embedding-8B | OK | 0.906 | dim=4096 |
| siliconflow_2 | siliconflow | model_chat | Pro/MiniMaxAI/MiniMax-M2.5 | OK | 1.563 | OK |
| siliconflow_2 | siliconflow | model_chat | Pro/deepseek-ai/DeepSeek-V3.2 | OK | 5.078 | OK |
| siliconflow_2 | siliconflow | model_chat | Pro/moonshotai/Kimi-K2.6 | OK | 1.593 | OK |
| siliconflow_2 | siliconflow | model_chat | Pro/zai-org/GLM-5.1 | OK | 2.656 | OK |
| siliconflow_2 | siliconflow | model_chat | Qwen/Qwen3.6-35B-A3B | OK | 0.454 |  |
| siliconflow_2 | siliconflow | rerank | Qwen/Qwen3-Reranker-8B | OK | 0.312 | results=1 score=0.13253025710582733 |
| siliconflow_2 | siliconflow | small_chat | deepseek-ai/DeepSeek-V4-Flash | OK | 2.781 | OK |
