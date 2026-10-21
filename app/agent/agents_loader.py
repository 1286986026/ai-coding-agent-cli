from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


DEFAULT_MAX_CHARS = 20_000


class AgentsLoadError(RuntimeError):
    """
    AGENTS.md 存在，但无法合法加载时抛出的异常。
    """


@dataclass(frozen=True)
class AgentsLoadResult:
    """
    AGENTS.md 的加载结果。

    status:
        loaded  - 成功读取非空文件
        missing - 文件不存在
        empty   - 文件存在，但没有有效内容
    """

    status: str
    content: str | None
    path: Path


def load_agents_md(
    project_root: Path,
    *,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> AgentsLoadResult:
    """
    读取明确指定项目根目录中的单个 AGENTS.md。

    本实验边界：
    1. 不递归搜索；
    2. 不读取父目录规则；
    3. 不做多文件合并；
    4. 文件不存在允许继续；
    5. 文件读取失败明确报错；
    6. 文件超长直接拒绝，不截断。
    """

    root = project_root.resolve()
    path = root / "AGENTS.md"

    # 情况 1：文件不存在
    if not path.exists():
        return AgentsLoadResult(
            status="missing",
            content=None,
            path=path,
        )

    # 情况 2：AGENTS.md 不是普通文件
    if not path.is_file():
        raise AgentsLoadError(
            f"AGENTS.md 存在，但不是普通文件: {path}"
        )

    try:
        # 多读一个字符用于判断是否超过长度上限。
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            content = file.read(max_chars + 1)

    except UnicodeError as exc:
        raise AgentsLoadError(
            f"AGENTS.md 编码错误，无法按 UTF-8 读取: {exc}"
        ) from exc

    except OSError as exc:
        raise AgentsLoadError(
            f"无法读取 AGENTS.md: {exc}"
        ) from exc

    # 情况 3：超长
    if len(content) > max_chars:
        raise AgentsLoadError(
            "AGENTS.md 超过允许的长度上限："
            f"{max_chars} 个字符"
        )

    content = content.strip()

    # 情况 4：空文件
    if not content:
        return AgentsLoadResult(
            status="empty",
            content=None,
            path=path,
        )

    # 情况 5：成功
    return AgentsLoadResult(
        status="loaded",
        content=content,
        path=path,
    )