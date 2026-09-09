"""AI Coding Agent CLI 的命令行入口。"""

import typer
from rich.console import Console

# 应用基本信息
APP_NAME = "AI Coding Agent CLI"
VERSION = "0.1"

# 创建 Typer 命令行应用
app = typer.Typer(
    help="AI Coding Agent CLI - 一个简单的 AI 编程助手命令行工具。"
)

# 创建 Rich 控制台，用于美化终端输出
console = Console()


@app.command()
def hello(
    name: str = typer.Option(
        "Developer",
        "--name",
        "-n",
        help="指定需要欢迎的用户名。",
    ),
) -> None:
    """输出程序版本及个性化欢迎信息。"""

    console.print(
        f"[bold cyan]{APP_NAME} v{VERSION}[/bold cyan]"
    )

    console.print(
        f"Hello, {name}! Welcome to {APP_NAME}.",
        markup=False,
    )


@app.command()
def version() -> None:
    """输出当前程序版本号。"""

    console.print(
        f"[bold green]{APP_NAME} v{VERSION}[/bold green]"
    )


def main() -> None:
    """启动命令行应用。"""

    app()


if __name__ == "__main__":
    main()