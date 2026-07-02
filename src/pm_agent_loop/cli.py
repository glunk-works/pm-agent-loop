import keyring
import typer

app = typer.Typer()

_SERVICE_NAME = "pm-agent-loop"
_KEY_USERNAME = "anthropic-api-key"


@app.callback()
def main() -> None:
    pass


@app.command()
def configure_key() -> None:
    api_key = typer.prompt("Anthropic API key", hide_input=True)
    keyring.set_password(_SERVICE_NAME, _KEY_USERNAME, api_key)
    typer.echo("Anthropic API key stored successfully.")


if __name__ == "__main__":
    app()
