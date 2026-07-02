import pytest

from pm_agent_loop.llm.client import LLMClient, LLMConfig


def test_llm_client_cannot_be_instantiated_directly():
    with pytest.raises(TypeError):
        LLMClient()


def test_llm_config_accepts_distinct_pm_and_critic_models():
    config = LLMConfig(
        provider="anthropic",
        pm_model="claude-opus-4-8",
        critic_model="claude-haiku-4-5",
    )

    assert config.pm_model == "claude-opus-4-8"
    assert config.critic_model == "claude-haiku-4-5"
    assert config.pm_model != config.critic_model
