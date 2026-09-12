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


@app.command("help")
def help_command() -> None:
    """显示命令列表和说明。"""
    console.print("Available commands:")
    console.print("  hello --name <名字>    输出欢迎信息")
    console.print("  version                输出版本号")
    console.print("  help                   显示命令说明")


if __name__ == "__main__":
    app()