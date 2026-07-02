from unittest.mock import MagicMock, patch

import pytest

from pm_agent_loop.llm.adapters.bedrock import BedrockLLMClient, _to_bedrock_model_id


def test_complete_returns_mocked_response_text(monkeypatch):
    monkeypatch.setenv("AWS_REGION", "us-east-1")

    with patch(
        "pm_agent_loop.llm.adapters.bedrock.AnthropicBedrockMantle"
    ) as mock_bedrock_cls:
        mock_content_block = MagicMock()
        mock_content_block.text = "Hello from the mock."
        mock_usage = MagicMock(input_tokens=12, output_tokens=34)
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[mock_content_block], usage=mock_usage
        )
        mock_bedrock_cls.return_value = mock_client

        client = BedrockLLMClient()
        result = client.complete(
            system_prompt="You are a helpful assistant.",
            messages=[{"role": "user", "content": "Hi"}],
            model="claude-haiku-4-5",
        )

    mock_bedrock_cls.assert_called_once_with(aws_region="us-east-1")
    mock_client.messages.create.assert_called_once_with(
        model="anthropic.claude-haiku-4-5",
        max_tokens=4096,
        system="You are a helpful assistant.",
        messages=[{"role": "user", "content": "Hi"}],
    )
    assert result.text == "Hello from the mock."
    assert result.input_tokens == 12
    assert result.output_tokens == 34


def test_falls_back_to_aws_default_region(monkeypatch):
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.setenv("AWS_DEFAULT_REGION", "eu-west-1")

    with patch(
        "pm_agent_loop.llm.adapters.bedrock.AnthropicBedrockMantle"
    ) as mock_bedrock_cls:
        BedrockLLMClient()

    mock_bedrock_cls.assert_called_once_with(aws_region="eu-west-1")


def test_missing_region_raises_runtime_error(monkeypatch):
    monkeypatch.delenv("AWS_REGION", raising=False)
    monkeypatch.delenv("AWS_DEFAULT_REGION", raising=False)

    with pytest.raises(RuntimeError, match="AWS region not found"):
        BedrockLLMClient()


def test_model_id_gets_anthropic_prefix():
    assert _to_bedrock_model_id("claude-haiku-4-5") == "anthropic.claude-haiku-4-5"


def test_model_id_prefix_not_duplicated():
    assert (
        _to_bedrock_model_id("anthropic.claude-haiku-4-5")
        == "anthropic.claude-haiku-4-5"
    )
