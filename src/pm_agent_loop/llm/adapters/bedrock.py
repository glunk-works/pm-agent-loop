import os

from anthropic import AnthropicBedrockMantle

from pm_agent_loop.llm.client import LLMClient, LLMResponse

_MAX_TOKENS = 4096
_BEDROCK_MODEL_PREFIX = "anthropic."


def _to_bedrock_model_id(model: str) -> str:
    if model.startswith(_BEDROCK_MODEL_PREFIX):
        return model
    return f"{_BEDROCK_MODEL_PREFIX}{model}"


class BedrockLLMClient(LLMClient):
    def __init__(self) -> None:
        region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION")
        if region is None:
            msg = (
                "AWS region not found. Set the AWS_REGION or AWS_DEFAULT_REGION "
                "environment variable to use the bedrock provider."
            )
            raise RuntimeError(msg)
        self._client = AnthropicBedrockMantle(aws_region=region)

    def complete(
        self, system_prompt: str, messages: list[dict], model: str
    ) -> LLMResponse:
        response = self._client.messages.create(
            model=_to_bedrock_model_id(model),
            max_tokens=_MAX_TOKENS,
            system=system_prompt,
            messages=messages,
        )
        return LLMResponse(
            text=response.content[0].text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
        )
