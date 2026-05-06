import os

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv()

DEFAULT_MODEL = "gpt-5.2"


def get_chat_model() -> ChatOpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL") or None
    model = os.getenv("OPENAI_MODEL") or DEFAULT_MODEL

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required in .env for LLM calls.")

    return ChatOpenAI(
        model=model,
        api_key=api_key,
        base_url=base_url,
    )
