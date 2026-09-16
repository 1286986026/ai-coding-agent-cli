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

    result = FileTool().read(p)

    assert result.content == "hello\nworld\n"
    assert result.line_count == 2
    assert result.encoding == "utf-8"
    assert result.size == 12


def test_read_nonexistent_raises(tmp_path: Path) -> None:
    p = tmp_path / "not_exist.txt"

    with pytest.raises(FileReadError):
        FileTool().read(p)


def test_write_then_read_roundtrip(tmp_path: Path) -> None:
    p = tmp_path / "out.txt"

    tool = FileTool()
    result = tool.write(p, "你好")

    assert result.created is True
    assert result.bytes_written == 6
    assert tool.read(p).content == "你好"


def test_write_no_overwrite_raises(tmp_path: Path) -> None:
    p = tmp_path / "exist.txt"
    p.write_text("old", encoding="utf-8")

    with pytest.raises(FileWriteError):
        FileTool().write(
            p,
            "new",
            overwrite=False,
        )


def test_write_creates_parent_dirs(tmp_path: Path) -> None:
    p = tmp_path / "a" / "b" / "c.txt"

    FileTool().write(p, "deep")

    assert p.exists()
    assert p.read_text(encoding="utf-8") == "deep"


def test_list_dir(tmp_path: Path) -> None:
    file_path = tmp_path / "a.txt"
    file_path.write_text("hello", encoding="utf-8")

    dir_path = tmp_path / "folder"
    dir_path.mkdir()

    entries = FileTool().list_dir(tmp_path)

    names = [entry.name for entry in entries]

    assert "a.txt" in names
    assert "folder" in names

    file_entry = next(
        entry for entry in entries
        if entry.name == "a.txt"
    )

    dir_entry = next(
        entry for entry in entries
        if entry.name == "folder"
    )

    assert file_entry.is_dir is False
    assert dir_entry.is_dir is True


def test_list_dir_nonexistent_raises(tmp_path: Path) -> None:
    with pytest.raises(FileReadError):
        FileTool().list_dir(
            tmp_path / "no_such_dir"
        )


def test_append(tmp_path: Path) -> None:
    p = tmp_path / "append.txt"

    tool = FileTool()

    tool.write(p, "first\n")
    result = tool.append(p, "second\n")

    assert result.created is False
    assert tool.read(p).content == "first\nsecond\n"


def test_read_lines(tmp_path: Path) -> None:
    p = tmp_path / "lines.txt"

    p.write_text(
        "a\nb\nc\n",
        encoding="utf-8",
    )

    lines = FileTool().read_lines(p)

    assert lines == ["a", "b", "c"]


def test_read_auto_detect_gbk(tmp_path: Path) -> None:
    """测试 encoding=None 时自动识别 GBK 中文文件。"""

    p = tmp_path / "gbk.txt"

    text = (
        "中文编码自动检测测试："
        "你好世界，这是第二节课堂作业。"
    )

    # 创建 GBK 编码文件
    raw = text.encode("gbk")
    p.write_bytes(raw)

    # encoding=None 表示自动检测编码
    result = FileTool().read(
        p,
        encoding=None,
    )

    # 内容必须正确恢复
    assert result.content == text

    # 字节数应与原始文件一致
    assert result.size == len(raw)

    # 编码名称可能是 GBK、GB2312、gb18030 等
    assert result.encoding


def test_write_and_read_bytes(tmp_path: Path) -> None:
    """测试二进制文件写入和读取。"""

    p = tmp_path / "binary.bin"

    data = b"\x01\x02\x03\x04\x05"

    tool = FileTool()

    result = tool.write_bytes(
        p,
        data,
    )

    assert result.created is True
    assert result.bytes_written == len(data)

    read_data = tool.read_bytes(p)

    assert read_data == data


def test_read_bytes_nonexistent_raises(
    tmp_path: Path,
) -> None:
    """测试读取不存在的二进制文件。"""

    p = tmp_path / "not_exist.bin"

    with pytest.raises(FileReadError):
        FileTool().read_bytes(p)


def test_batch_context_manager(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """测试 batch 上下文管理器。"""

    tool = FileTool()

    with tool.batch():
        print("processing file")

    captured = capsys.readouterr()

    assert "批量开始" in captured.out
    assert "processing file" in captured.out
    assert "批量结束" in captured.out