from __future__ import annotations

import subprocess
from pathlib import Path
from typing import Any

from app.tools.file_tool import (
    FileTool,
    FileReadError,
    FileWriteError,
)


class BasicTools:
    """
    Lab03 基础工具集合。

    提供：
    1. read_file
    2. write_file
    3. list_dir
    4. execute_command
    """

    def __init__(
        self,
        root: Path,
    ) -> None:

        # 工具允许访问的根目录
        self.root = root.resolve()

        self.file_tool = FileTool()


    # =====================================================
    # 路径安全检查
    # =====================================================

    def schema(self) -> list[dict[str, Any]]:
        """
        返回提供给大模型的四个工具定义。
        GLM 根据这些 Schema 生成标准 tool_calls。
        """

        return [
            {
                "type": "function",
                "function": {
                    "name": "list_dir",
                    "description": "列出教学目录中指定相对路径的一层文件和目录",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "相对于教学根目录的目录路径，默认使用当前根目录",
                            }
                        },
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "读取教学目录中的 UTF-8 文本文件",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "相对于教学根目录的文件路径",
                            }
                        },
                        "required": ["path"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "在教学目录中创建 UTF-8 文本文件，不覆盖已经存在的文件",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "相对于教学根目录的新文件路径",
                            },
                            "content": {
                                "type": "string",
                                "description": "需要写入文件的文本内容",
                            },
                        },
                        "required": ["path", "content"],
                        "additionalProperties": False,
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_command",
                    "description": "执行实验允许的固定 Shell 命令",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "只允许实验白名单中的命令",
                                "enum": [
                                    "echo lab03-shell-ok",
                                    "cd",
                                ],
                            }
                        },
                        "required": ["command"],
                        "additionalProperties": False,
                    },
                },
            },
        ]




    def _safe_path(
        self,
        path: str,
    ) -> Path:
        """
        限制文件只能在 root 目录内。
        """

        target = (
            self.root / path
        ).resolve()

        if not target.is_relative_to(
            self.root
        ):
            raise ValueError(
                "路径越界"
            )

        return target


    # =====================================================
    # read_file
    # =====================================================

    def read_file(
        self,
        path: str,
    ) -> dict[str, Any]:
        """
        读取文件。
        """

        try:
            target = self._safe_path(path)

            result = self.file_tool.read(
                target,
                encoding="utf-8",
            )

            return {
                "ok": True,
                "path": str(target),
                "content": result.content,
                "size": result.size,
            }


        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
            }


    # =====================================================
    # write_file
    # =====================================================

    def write_file(
        self,
        path: str,
        content: str,
    ) -> dict[str, Any]:
        """
        写文件。
        """

        try:
            target = self._safe_path(path)

            result = self.file_tool.write(
                target,
                content,
                overwrite=False,
            )

            return {
                "ok": True,
                "path": str(target),
                "bytes_written": (
                    result.bytes_written
                ),
            }


        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
            }


    # =====================================================
    # list_dir
    # =====================================================

    def list_dir(
        self,
        path: str = ".",
    ) -> dict[str, Any]:
        """
        查看目录。
        """

        try:

            target = self._safe_path(path)

            entries = (
                self.file_tool.list_dir(
                    target
                )
            )

            return {
                "ok": True,
                "entries": [
                    {
                        "name": e.name,
                        "is_dir": e.is_dir,
                        "size": e.size,
                    }
                    for e in entries
                ],
                "truncated": False,
            }


        except Exception as exc:

            return {
                "ok": False,
                "error": str(exc),
            }


    # =====================================================
    # execute_command
    # =====================================================

    def execute_command(
        self,
        command: str,
    ) -> dict[str, Any]:
        """
        执行白名单命令。

        Windows 使用 cmd。
        """

        allowed = {
            "echo lab03-shell-ok",
            "cd",
        }


        if command not in allowed:

            return {
                "ok": False,
                "error": (
                    "command not allowed"
                ),
            }


        try:

            result = subprocess.run(
                command,
                shell=True,
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=10,
            )


            return {
                "ok": True,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }


        except subprocess.TimeoutExpired:

            return {
                "ok": False,
                "error": "command timeout",
            }