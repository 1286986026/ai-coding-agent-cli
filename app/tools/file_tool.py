from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class FileToolError(Exception):
    """FileTool 所有异常的基类。"""


class FileReadError(FileToolError):
    """文件读取失败。"""


class FileWriteError(FileToolError):
    """文件写入失败。"""


@dataclass
class FileContent:
    """文件读取结果。"""

    path: str
    content: str
    encoding: str
    size: int
    line_count: int


@dataclass
class WriteResult:
    """文件写入结果。"""

    path: str
    bytes_written: int
    created: bool


class FileTool:
    """文件读写工具。"""

    def read(
        self,
        path: str | Path,
        encoding: str = "utf-8",
    ) -> FileContent:
        """读取文本文件并返回结构化结果。"""

        target = Path(path)

        if not target.exists():
            raise FileReadError(f"文件不存在: {target}")

        if not target.is_file():
            raise FileReadError(f"不是普通文件: {target}")

        try:
            content = target.read_text(encoding=encoding)
        except UnicodeDecodeError as e:
            raise FileReadError(
                f"编码解码失败 (encoding={encoding})，请检查文件编码: {e}"
            ) from e
        except OSError as e:
            raise FileReadError(f"读取失败: {e}") from e

        size = len(content.encode(encoding))

        line_count = content.count("\n")
        if content and not content.endswith("\n"):
            line_count += 1

        return FileContent(
            path=str(target),
            content=content,
            encoding=encoding,
            size=size,
            line_count=line_count,
        )

    def write(
        self,
        path: str | Path,
        content: str,
        encoding: str = "utf-8",
        overwrite: bool = True,
    ) -> WriteResult:
        """写入文本文件并返回写入结果。"""

        target = Path(path)

        if target.exists() and not overwrite:
            raise FileWriteError(f"文件已存在且不允许覆盖: {target}")

        created = not target.exists()

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding=encoding)
        except OSError as e:
            raise FileWriteError(f"写入失败: {e}") from e

        return WriteResult(
            path=str(target),
            bytes_written=len(content.encode(encoding)),
            created=created,
        )