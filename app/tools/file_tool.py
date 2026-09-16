from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path

import chardet


# ============================================================
# 自定义异常
# ============================================================


class FileToolError(Exception):
    """FileTool 所有异常的基类。"""


class FileReadError(FileToolError):
    """文件读取失败。"""


class FileWriteError(FileToolError):
    """文件写入失败。"""


# ============================================================
# 数据结构
# ============================================================


@dataclass
class FileContent:
    """文本文件读取结果。"""

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


# ============================================================
# FileTool
# ============================================================


class FileTool:
    """文件系统工具类。"""

    # --------------------------------------------------------
    # 文本读取
    # --------------------------------------------------------

    def read(
        self,
        path: str | Path,
        encoding: str | None = "utf-8",
    ) -> FileContent:
        """
        读取文本文件。

        encoding:
        - "utf-8"、"gbk" 等：按照指定编码读取
        - None：自动检测文件编码
        """

        target = Path(path)

        if not target.exists():
            raise FileReadError(
                f"文件不存在: {target}"
            )

        if not target.is_file():
            raise FileReadError(
                f"不是普通文件: {target}"
            )

        try:
            # ==================================================
            # 自动检测编码
            # ==================================================

            if encoding is None:
                raw = target.read_bytes()

                # 空文件
                if not raw:
                    content = ""
                    actual_encoding = "utf-8"

                else:
                    # 第一优先：尝试 UTF-8
                    try:
                        content = raw.decode("utf-8")
                        actual_encoding = "utf-8"

                    except UnicodeDecodeError:
                        # UTF-8 失败后使用 chardet 检测
                        detected = chardet.detect(raw)

                        detected_encoding = detected.get(
                            "encoding"
                        )

                        confidence = (
                            detected.get("confidence")
                            or 0.0
                        )

                        candidates: list[str] = []

                        # 中文常见编码优先采用检测结果
                        if detected_encoding:
                            normalized = (
                                detected_encoding
                                .lower()
                                .replace("-", "")
                            )

                            chinese_encodings = {
                                "gb2312",
                                "gbk",
                                "gb18030",
                                "big5",
                                "big5hkscs",
                            }

                            if normalized in chinese_encodings:
                                candidates.append(
                                    detected_encoding
                                )

                        # 中文 Windows 常见编码兜底
                        candidates.append("gb18030")

                        # chardet 有可信结果时加入候选
                        if (
                            detected_encoding
                            and confidence >= 0.5
                            and detected_encoding
                            not in candidates
                        ):
                            candidates.append(
                                detected_encoding
                            )

                        # 最后尝试 UTF-8
                        candidates.append("utf-8")

                        last_error: Exception | None = None

                        for candidate in candidates:
                            try:
                                content = raw.decode(
                                    candidate
                                )

                                actual_encoding = candidate
                                break

                            except (
                                UnicodeDecodeError,
                                LookupError,
                            ) as e:
                                last_error = e

                        else:
                            raise FileReadError(
                                "自动检测编码失败: "
                                f"{last_error}"
                            )

                # 自动模式直接使用原始文件字节数
                size = len(raw)

            # ==================================================
            # 指定编码
            # ==================================================

            else:
                actual_encoding = encoding

                content = target.read_text(
                    encoding=actual_encoding
                )

                size = len(
                    content.encode(actual_encoding)
                )

        except FileReadError:
            raise

        except UnicodeDecodeError as e:
            raise FileReadError(
                "编码解码失败 "
                f"(encoding={encoding}): {e}"
            ) from e

        except LookupError as e:
            raise FileReadError(
                "不支持的编码 "
                f"(encoding={encoding}): {e}"
            ) from e

        except OSError as e:
            raise FileReadError(
                f"读取失败: {e}"
            ) from e

        # ======================================================
        # 计算行数
        # ======================================================

        line_count = content.count("\n")

        # 最后一行没有换行符，也要计为一行
        if content and not content.endswith("\n"):
            line_count += 1

        return FileContent(
            path=str(target),
            content=content,
            encoding=actual_encoding,
            size=size,
            line_count=line_count,
        )

    # --------------------------------------------------------
    # 文本写入
    # --------------------------------------------------------

    def write(
        self,
        path: str | Path,
        content: str,
        encoding: str = "utf-8",
        overwrite: bool = True,
    ) -> WriteResult:
        """写入文本文件。"""

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

        except LookupError as e:
            raise FileWriteError(
                "不支持的编码 "
                f"(encoding={encoding}): {e}"
            ) from e

        except OSError as e:
            raise FileWriteError(
                f"写入失败: {e}"
            ) from e

        return WriteResult(
            path=str(target),
            bytes_written=len(
                content.encode(encoding)
            ),
            created=created,
        )

    # --------------------------------------------------------
    # 列出目录
    # --------------------------------------------------------

    def list_dir(
        self,
        path: str | Path,
        recursive: bool = False,
        pattern: str = "*",
    ) -> list[DirEntry]:
        """
        列出目录内容。

        recursive=False:
            只查看当前目录。

        recursive=True:
            递归查看所有子目录。

        pattern:
            匹配模式，例如 "*.py"。
        """

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
                children = list(
                    target.rglob(pattern)
                )
            else:
                children = list(
                    target.glob(pattern)
                )

        except OSError as e:
            raise FileReadError(
                f"列举目录失败: {e}"
            ) from e

        entries: list[DirEntry] = []

        # 排序保证结果稳定
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

    # --------------------------------------------------------
    # 追加写入
    # --------------------------------------------------------

    def append(
        self,
        path: str | Path,
        content: str,
        encoding: str = "utf-8",
    ) -> WriteResult:
        """向文件末尾追加内容。"""

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
            ) as file:
                file.write(content)

        except LookupError as e:
            raise FileWriteError(
                "不支持的编码 "
                f"(encoding={encoding}): {e}"
            ) from e

        except OSError as e:
            raise FileWriteError(
                f"追加失败: {e}"
            ) from e

        return WriteResult(
            path=str(target),
            bytes_written=len(
                content.encode(encoding)
            ),
            created=created,
        )

    # --------------------------------------------------------
    # 按行读取
    # --------------------------------------------------------

    def read_lines(
        self,
        path: str | Path,
        encoding: str | None = "utf-8",
    ) -> list[str]:
        """按行读取文本文件。"""

        result = self.read(
            path,
            encoding=encoding,
        )

        # splitlines() 会去除换行符
        return result.content.splitlines()

    # --------------------------------------------------------
    # Task 8：二进制读取
    # --------------------------------------------------------

    def read_bytes(
        self,
        path: str | Path,
    ) -> bytes:
        """以二进制方式读取文件。"""

        target = Path(path)

        if not target.exists():
            raise FileReadError(
                f"文件不存在: {target}"
            )

        if not target.is_file():
            raise FileReadError(
                f"不是普通文件: {target}"
            )

        try:
            return target.read_bytes()

        except OSError as e:
            raise FileReadError(
                f"二进制读取失败: {e}"
            ) from e

    # --------------------------------------------------------
    # Task 8：二进制写入
    # --------------------------------------------------------

    def write_bytes(
        self,
        path: str | Path,
        data: bytes,
    ) -> WriteResult:
        """以二进制方式写入文件。"""

        target = Path(path)

        created = not target.exists()

        try:
            # 自动创建父目录
            target.parent.mkdir(
                parents=True,
                exist_ok=True,
            )

            target.write_bytes(data)

        except OSError as e:
            raise FileWriteError(
                f"二进制写入失败: {e}"
            ) from e

        return WriteResult(
            path=str(target),
            bytes_written=len(data),
            created=created,
        )

    # --------------------------------------------------------
    # Task 8：批量处理上下文管理器
    # --------------------------------------------------------

    @contextmanager
    def batch(
        self,
    ) -> Iterator["FileTool"]:
        """
        批量处理文件的上下文管理器。

        使用方式：

        with FileTool().batch() as tool:
            tool.write(...)
            tool.read(...)
        """

        print("批量开始")

        try:
            # 把当前 FileTool 对象交给 with 代码块
            yield self

        finally:
            # 即使中间发生异常，也会执行
            print("批量结束")