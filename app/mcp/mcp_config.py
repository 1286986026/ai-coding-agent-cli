from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class McpServerSpec:
    name: str
    type: str = "stdio"
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str | None = None
    headers: dict[str, str] = field(default_factory=dict)
    enabled: bool = True
    timeout: float = 30.0


def expand(value: str, project_root: str) -> str:
    """
    展开 mcp.json 中使用的路径变量。
    """
    return (
        value
        .replace("${PROJECT_DIR}", project_root)
        .replace("${HOME}", str(Path.home()))
    )


def load_mcp_server_specs(
    project_root: str,
) -> dict[str, McpServerSpec]:
    """
    读取项目根目录中的 mcp.json，
    并解析成 McpServerSpec 字典。
    """

    root = Path(project_root).resolve()
    config_path = root / "mcp.json"

    if not config_path.exists():
        return {}

    data = json.loads(
        config_path.read_text(
            encoding="utf-8"
        )
    )

    servers = data.get(
        "mcpServers",
        {},
    )

    result: dict[
        str,
        McpServerSpec,
    ] = {}

    for name, raw in servers.items():

        expanded_args = [
            expand(
                str(arg),
                str(root),
            )
            for arg in raw.get(
                "args",
                [],
            )
        ]

        expanded_url = None

        if raw.get("url"):
            expanded_url = expand(
                raw["url"],
                str(root),
            )

        result[name] = McpServerSpec(
            name=name,
            type=raw.get(
                "type",
                (
                    "streamable_http"
                    if raw.get("url")
                    else "stdio"
                ),
            ),
            command=raw.get(
                "command"
            ),
            args=expanded_args,
            env=raw.get(
                "env",
                {},
            ),
            url=expanded_url,
            headers=raw.get(
                "headers",
                {},
            ),
            enabled=raw.get(
                "enabled",
                True,
            ),
            timeout=float(
                raw.get(
                    "timeout",
                    30.0,
                )
            ),
        )

    return result