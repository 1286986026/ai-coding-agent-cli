import typer
from rich.console import Console

app = typer.Typer()
console = Console()


@app.command()
def hello(
    name: str = typer.Option(..., "--name")
) -> None:
    """输出欢迎信息。"""
    console.print("AI Coding Agent CLI v0.1")
    console.print(f"Hello, {name}! Welcome to AI Coding Agent CLI.")


@app.command()
def version() -> None:
    """输出版本号。"""
    console.print("AI Coding Agent CLI v0.1")


if __name__ == "__main__":
    app()