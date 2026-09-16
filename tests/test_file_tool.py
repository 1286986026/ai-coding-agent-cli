from pathlib import Path

import pytest

from app.tools.file_tool import (
    FileReadError,
    FileTool,
    FileWriteError,
)


def test_read_text_file(tmp_path: Path) -> None:
    p = tmp_path / "a.txt"
    p.write_text("hello\nworld\n", encoding="utf-8")

    fc = FileTool().read(p)

    assert fc.content == "hello\nworld\n"
    assert fc.line_count == 2
    assert fc.encoding == "utf-8"


def test_read_nonexistent_raises(tmp_path: Path) -> None:
    with pytest.raises(FileReadError):
        FileTool().read(tmp_path / "nope.txt")


def test_write_then_read_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "out.txt"

    result = FileTool().write(p, "你好")

    assert result.created is True
    assert FileTool().read(p).content == "你好"


def test_write_no_overwrite_raises(tmp_path: Path) -> None:
    p = tmp_path / "exist.txt"
    p.write_text("x", encoding="utf-8")

    with pytest.raises(FileWriteError):
        FileTool().write(p, "y", overwrite=False)


def test_write_creates_parent_dirs(tmp_path: Path) -> None:
    p = tmp_path / "a" / "b" / "c.txt"

    FileTool().write(p, "deep")
def test_list_dir(tmp_path: Path) -> None:
    # 创建一个文件
    (tmp_path / "a.txt").write_text("hello", encoding="utf-8")

    # 创建一个目录
    (tmp_path / "b").mkdir()

    entries = FileTool().list_dir(tmp_path)

    names = [entry.name for entry in entries]

    assert "a.txt" in names
    assert "b" in names


def test_list_dir_nonexistent_raises(tmp_path: Path) -> None:
    with pytest.raises(FileReadError):
        FileTool().list_dir(tmp_path / "no_such_dir")