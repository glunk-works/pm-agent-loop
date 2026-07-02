from unittest.mock import patch

import keyring
import keyring.backend
import pytest
from typer.testing import CliRunner

from pm_agent_loop.cli import app

DUMMY_KEY = "sk-ant-dummy-cli-test-key"


class _InMemoryKeyring(keyring.backend.KeyringBackend):
    priority = 1

    def __init__(self) -> None:
        super().__init__()
        self._store: dict[tuple[str, str], str] = {}

    def get_password(self, service: str, username: str) -> str | None:
        return self._store.get((service, username))

    def set_password(self, service: str, username: str, password: str) -> None:
        self._store[(service, username)] = password

    def delete_password(self, service: str, username: str) -> None:
        self._store.pop((service, username), None)


@pytest.fixture
def fake_keyring_backend():
    original = keyring.get_keyring()
    keyring.set_keyring(_InMemoryKeyring())
    yield
    keyring.set_keyring(original)


def test_configure_key_stores_value_retrievable_via_keyring(fake_keyring_backend):
    runner = CliRunner()

    with patch("pm_agent_loop.cli.typer.prompt", return_value=DUMMY_KEY):
        result = runner.invoke(app, ["configure-key"])

    assert result.exit_code == 0
    assert keyring.get_password("pm-agent-loop", "anthropic-api-key") == DUMMY_KEY
    assert DUMMY_KEY not in result.stdout
