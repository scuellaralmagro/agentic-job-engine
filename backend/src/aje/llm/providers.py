"""Registers real LangChain provider builders. Import for side effects."""
from aje.config import get_settings
from aje.llm.registry import (
    ModelSpec,
    register_chat_provider,
    register_embeddings_provider,
)


def _anthropic_chat(spec: ModelSpec):
    from langchain_anthropic import ChatAnthropic

    return ChatAnthropic(
        model=spec.model, api_key=get_settings().anthropic_api_key, **spec.params
    )


def _openai_chat(spec: ModelSpec):
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(
        model=spec.model, api_key=get_settings().openai_api_key, **spec.params
    )


def _google_chat(spec: ModelSpec):
    from langchain_google_genai import ChatGoogleGenerativeAI

    return ChatGoogleGenerativeAI(
        model=spec.model, google_api_key=get_settings().google_api_key, **spec.params
    )


def _openai_embeddings(spec: ModelSpec):
    from langchain_openai import OpenAIEmbeddings

    return OpenAIEmbeddings(
        model=spec.model, api_key=get_settings().openai_api_key, **spec.params
    )


def register_default_providers() -> None:
    register_chat_provider("anthropic", _anthropic_chat)
    register_chat_provider("openai", _openai_chat)
    register_chat_provider("google", _google_chat)
    register_embeddings_provider("openai", _openai_embeddings)
