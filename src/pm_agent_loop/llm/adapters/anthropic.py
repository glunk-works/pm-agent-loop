import keyring
from anthropic import Anthropic

from pm_agent_loop.llm.client import LLMClient, LLMResponse

_SERVICE_NAME = "pm-agent-loop"
_KEY_USERNAME = "anthropic-api-key"
_MAX_TOKENS = 4096


class AnthropicLLMClient(LLMClient):
    def __init__(self) -> None:
        api_key = keyring.get_password(_SERVICE_NAME, _KEY_USERNAME)
        if api_key is None:
            msg = "Anthropic API key not found in the OS keyring."
            raise RuntimeError(msg)
        self._client = Anthropic(api_key=api_key)

    def complete(
        self, system_prompt: str, messages: list[dict], model: str
    ) -> LLMResponse:
        response = self._client.messages.create(
            model=model,
            max_tokens=_MAX_TOKENS,
            system=system_prompt,
            messages=messages,
        )
        return LLMResponse(
            text=response.content[0].text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
