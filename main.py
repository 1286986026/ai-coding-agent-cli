"""AI Coding Agent CLI 主程序。"""

import typer
from rich.console import Console

# 创建 Typer 应用
app = typer.Typer(
    help="AI Coding Agent CLI - 一个简单的命令行工具。"
)

# 创建 Rich 控制台
console = Console()


@app.command()
def hello(
    name: str = typer.Option(
        "Developer",
        "--name",
        help="指定用户名。",
    )
) -> None:
    """输出欢迎信息。"""

    console.print("AI Coding Agent CLI v0.1")
    console.print(
        f"Hello, {name}! Welcome to AI Coding Agent CLI."
    )


@app.command()
def version() -> None:
    """输出版本号。"""

    console.print("AI Coding Agent CLI v0.1")


def main() -> None:
    """程序入口。"""

    app()


if __name__ == "__main__":
    main()