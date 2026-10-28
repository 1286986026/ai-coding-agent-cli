import asyncio
import json
from pathlib import Path

from app.mcp.mcp_config import (
    load_mcp_server_specs,
)
from app.tools.registry import (
    ToolRegistry,
)


def test_mcp_config_expands_project_dir(
    tmp_path: Path,
):
    """
    测试 mcp.json 可以正常加载，
    并正确展开 ${PROJECT_DIR}。
    """

    config = {
        "mcpServers": {
            "filesystem": {
                "type": "stdio",
                "command": "npx",
                "args": [
                    "-y",
                    "server-filesystem",
                    "${PROJECT_DIR}/demo_lab03",
                ],
            }
        }
    }

    (
        tmp_path / "mcp.json"
    ).write_text(
        json.dumps(config),
        encoding="utf-8",
    )

    specs = load_mcp_server_specs(
        str(tmp_path)
    )

    assert "filesystem" in specs

    spec = specs["filesystem"]

    assert spec.type == "stdio"
    assert spec.command == "npx"

    # ${PROJECT_DIR} 应被展开成真实目录
    assert (
        str(tmp_path)
        in spec.args[-1]
    )

    assert (
        "${PROJECT_DIR}"
        not in spec.args[-1]
    )


def test_registry_dispatch():
    """
    测试 ToolRegistry 能正常注册
    并异步执行工具。
    """

    registry = ToolRegistry()

    async def echo_handler(
        args: dict,
    ) -> dict:
        return {
            "value": args["value"]
        }

    registry.register(
        name="echo",
        description="echo test",
        parameters={
            "type": "object",
            "properties": {
                "value": {
                    "type": "string"
                }
            },
            "required": [
                "value"
            ],
        },
        handler=echo_handler,
    )

    result = asyncio.run(
        registry.dispatch(
            "echo",
            {
                "value": "ok"
            },
        )
    )

    assert result["ok"] is True
    assert result["value"] == "ok"


def test_registry_unknown_tool():
    """
    测试调用不存在的工具时，
    Registry 返回错误而不是崩溃。
    """

    registry = ToolRegistry()

    result = asyncio.run(
        registry.dispatch(
            "does_not_exist",
            {},
        )
    )

    assert result["ok"] is False

    assert (
        "Unknown tool"
        in result["error"]
    )