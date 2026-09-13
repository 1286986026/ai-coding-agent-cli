from pathlib import Path


def main() -> None:
    """自动创建项目目录结构和 __init__.py 文件。"""

    directories = [
        "app/core",
        "app/tools",
        "app/llm",
        "app/agent",
        "app/cli",
        "tests",
        "docs",
    ]

    files = [
        "app/__init__.py",
        "app/core/__init__.py",
        "app/tools/__init__.py",
        "app/llm/__init__.py",
        "app/agent/__init__.py",
        "app/cli/__init__.py",
        "tests/__init__.py",
    ]

    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)

    for file in files:
        path = Path(file)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch(exist_ok=True)

    print("Project structure initialized successfully.")


if __name__ == "__main__":
    main()