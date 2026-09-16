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


@dataclass
class DirEntry:
    """目录项。"""

    name: str
    path: str
    is_dir: bool
    size: int


class FileTool:
    """文件读写工具。"""

    def read(
        self,
        path: str | Path,
        encoding: str = "utf-8",
    ) -> FileContent:
        target = Path(path)

        if not target.exists():
            raise FileReadError(f"文件不存在: {target}")

        if not target.is_file():
            raise FileReadError(f"不是普通文件: {target}")

        try:
            content = target.read_text(encoding=encoding)
        except UnicodeDecodeError as e:
            raise FileReadError(
                f"编码解码失败 (encoding={encoding}): {e}"
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
        target = Path(path)

        if target.exists() and not overwrite:
            raise FileWriteError(
                f"文件已存在且不允许覆盖: {target}"
            )

        created = not target.exists()

        try:
            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            target.write_text(
                content,
                encoding=encoding,
            )
        except OSError as e:
            raise FileWriteError(
                f"写入失败: {e}"
            ) from e

        return WriteResult(
            path=str(target),
            bytes_written=len(content.encode(encoding)),
            created=created,
        )

    def list_dir(
        self,
        path: str | Path,
        recursive: bool = False,
        pattern: str = "*",
    ) -> list[DirEntry]:
        target = Path(path)

        if not target.exists():
            raise FileReadError(
                f"目录不存在: {target}"
            )

        if not target.is_dir():
            raise FileReadError(
                f"不是目录: {target}"
            )

        try:
            if recursive:
                children = list(target.rglob(pattern))
            else:
                children = list(target.glob(pattern))
        except OSError as e:
            raise FileReadError(
                f"列举目录失败: {e}"
            ) from e

        entries: list[DirEntry] = []

        for child in sorted(
            children,
            key=lambda p: str(p).lower(),
        ):
            try:
                if child.is_file():
                    size = child.stat().st_size
                else:
                    size = 0
            except OSError:
                size = 0

            entries.append(
                DirEntry(
                    name=child.name,
                    path=str(child),
                    is_dir=child.is_dir(),
                    size=size,
                )
            )

        return entries

    def append(
        self,
        path: str | Path,
        content: str,
        encoding: str = "utf-8",
    ) -> WriteResult:
        target = Path(path)

        created = not target.exists()

        try:
            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            with open(
                target,
                "a",
                encoding=encoding,
            ) as f:
                f.write(content)

        except OSError as e:
            raise FileWriteError(
                f"追加失败: {e}"
            ) from e

        return WriteResult(
            path=str(target),
            bytes_written=len(content.encode(encoding)),
            created=created,
        )

    def read_lines(
        self,
        path: str | Path,
        encoding: str = "utf-8",
    ) -> list[str]:
        fc = self.read(
            path,
            encoding=encoding,
        )

        return fc.content.splitlines()