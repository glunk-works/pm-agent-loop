from unittest.mock import MagicMock, patch

import pytest

from pm_agent_loop.llm.adapters.anthropic import AnthropicLLMClient

DUMMY_KEY = "sk-ant-dummy-test-key-12345"


def test_complete_returns_mocked_response_text(capsys, caplog):
    with (
        patch(
            "pm_agent_loop.llm.adapters.anthropic.keyring.get_password",
            return_value=DUMMY_KEY,
        ),
        patch("pm_agent_loop.llm.adapters.anthropic.Anthropic") as mock_anthropic_cls,
    ):
        mock_content_block = MagicMock()
        mock_content_block.text = "Hello from the mock."
        mock_usage = MagicMock(input_tokens=12, output_tokens=34)
        mock_client = MagicMock()
        mock_client.messages.create.return_value = MagicMock(
            content=[mock_content_block], usage=mock_usage
        )
        mock_anthropic_cls.return_value = mock_client

        client = AnthropicLLMClient()
        result = client.complete(
            system_prompt="You are a helpful assistant.",
            messages=[{"role": "user", "content": "Hi"}],
            model="claude-haiku-4-5",
        )

    assert result.text == "Hello from the mock."
    assert result.input_tokens == 12
    assert result.output_tokens == 34
    captured = capsys.readouterr()
    assert DUMMY_KEY not in captured.out
    assert DUMMY_KEY not in captured.err
    assert all(DUMMY_KEY not in record.getMessage() for record in caplog.records)


def test_missing_key_raises_runtime_error_without_leaking_key(capsys, caplog):
    with (
        patch(
            "pm_agent_loop.llm.adapters.anthropic.keyring.get_password",
            return_value=None,
        ),
        pytest.raises(RuntimeError),
    ):
        AnthropicLLMClient()

    captured = capsys.readouterr()
    assert DUMMY_KEY not in captured.out
    assert DUMMY_KEY not in captured.err
    assert all(DUMMY_KEY not in record.getMessage() for record in caplog.records)
