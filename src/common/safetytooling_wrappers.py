"""
<file_context>
This file contains wrapper functions around safetytooling APIs to add additional functionality
or handle special cases. Currently includes:
- ask_single_question: Wrapper around InferenceAPI.ask_single_question that handles provider prefixes
</file_context>
"""

from typing import Any

from safetytooling.apis import InferenceAPI
from safetytooling.data_models import Prompt


async def ask_single_question(
    api: InferenceAPI,
    model_id: str,
    question: str,
    system_prompt: str | None = None,
    **api_kwargs: Any,
) -> list[str]:
    """Wrapper around InferenceAPI.ask_single_question that handles provider prefixes.

    If model_id contains a colon, everything before the colon is treated as the provider
    and force_provider=True is set. For example:
    - "openai:gpt-4o-2024-08-06" -> force_provider="openai", model_id="gpt-4o-2024-08-06"
    - "anthropic:claude-3-5-sonnet-20240620" -> force_provider="anthropic", model_id="claude-3-5-sonnet-20240620"

    Args:
        api: The InferenceAPI instance to use
        model_id: The model ID, optionally prefixed with provider:
        question: The question to ask
        system_prompt: Optional system prompt
        **api_kwargs: Additional kwargs to pass to ask_single_question

    Returns:
        List of responses from the model
    """
    if ":" in model_id:
        provider, actual_model_id = model_id.split(":", 1)
        api_kwargs["force_provider"] = provider
        model_id = actual_model_id

    return await api.ask_single_question(
        model_id=model_id,
        question=question,
        system_prompt=system_prompt,
        **api_kwargs,
    )


async def api_call(
    api: InferenceAPI,
    prompt: Prompt,
    model_id: str,
    **api_kwargs: Any,
) -> list[str]:
    """Wrapper around InferenceAPI.__call__ that handles provider prefixes.

    If model_id contains a colon, everything before the colon is treated as the provider
    and force_provider=True is set. For example:
    - "openai:gpt-4o-2024-08-06" -> force_provider="openai", model_id="gpt-4o-2024-08-06"
    - "anthropic:claude-3-5-sonnet-20240620" -> force_provider="anthropic", model_id="claude-3-5-sonnet-20240620"

    Args:
        api: The InferenceAPI instance to use
        prompt: The prompt to use
        model_id: The model ID, optionally prefixed with provider:
        **api_kwargs: Additional kwargs to pass to InferenceAPI.__call__

    Returns:
        List of responses from the model
    """
    if ":" in model_id:
        provider, actual_model_id = model_id.split(":", 1)
        api_kwargs["force_provider"] = provider
        model_id = actual_model_id

    return await api(
        prompt=prompt,
        model_id=model_id,
        **api_kwargs,
    )
