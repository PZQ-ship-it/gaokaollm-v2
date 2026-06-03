SiliconFlow / DeepSeek V4 Flash 流式调用

官方 Chat Completions API：https://docs.siliconflow.cn/cn/api-reference/chat-completions/chat-completions
官方快速上手 OpenAI SDK 示例：https://docs.siliconflow.cn/cn/userguide/quickstart
定价页确认 DeepSeek-V4-Flash 已上线，1049K context：https://www.siliconflow.com/pricing
关键点：SiliconFlow 的 OpenAI-compatible endpoint 是 https://api.siliconflow.cn/v1，Chat Completions 支持 stream；设为 true 后会用 SSE 返回 token，结束时 data: [DONE]。DeepSeek V4 Flash 的 API model id 在参数说明里出现为 deepseek-ai/DeepSeek-V4-Flash，并且专有参数 reasoning_effort 支持 high / max。(docs.siliconflow.cn)

最小 Python 调用：

import os
from openai import OpenAI

client = OpenAI(
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1",
)

response = client.chat.completions.create(
    model="deepseek-ai/DeepSeek-V4-Flash",
    messages=[{"role": "user", "content": "用三句话解释高考志愿冲稳保。"}],
    stream=True,
    reasoning_effort="high",  # 可选: "high" 或 "max"
)

for chunk in response:
    if not chunk.choices:
        continue
    delta = chunk.choices[0].delta
    content = getattr(delta, "content", None)
    reasoning = getattr(delta, "reasoning_content", None)
    if reasoning:
        print(reasoning, end="", flush=True)
    if content:
        print(content, end="", flush=True)
LangGraph 流式返回文档

官方 LangGraph Streaming：https://docs.langchain.com/oss/python/langgraph/streaming
ChatOpenAI 参考，含 base_url / extra_body：https://reference.langchain.com/python/langchain-openai/chat_models/base/ChatOpenAI
关键点：LangGraph 支持 graph.stream() / graph.astream()；如果要 token-by-token，使用 stream_mode="messages"，返回 (message_chunk, metadata)；如果不用 LangChain chat model、直接包 SiliconFlow/OpenAI client，也可以用 stream_mode="custom" 自己写入流。(docs.langchain.com) (docs.langchain.com)

LangGraph + SiliconFlow 口径示例：

import os
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model="deepseek-ai/DeepSeek-V4-Flash",
    api_key=os.environ["SILICONFLOW_API_KEY"],
    base_url="https://api.siliconflow.cn/v1",
    extra_body={"reasoning_effort": "high"},
)

for chunk in graph.stream(
    {"messages": [{"role": "user", "content": "你好"}]},
    stream_mode="messages",
    version="v2",
):
    if chunk["type"] == "messages":
        msg, metadata = chunk["data"]
        if msg.content:
            print(msg.content, end="", flush=True)