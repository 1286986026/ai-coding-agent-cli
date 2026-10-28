from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import timedelta

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client

from app.mcp.mcp_config import (
    McpServerSpec,
    load_mcp_server_specs,
)
from app.tools.registry import RegisteredTool


def content_to_text(content) -> str:
    """
    将 MCP 返回的不同 content 类型统一转成文本。
    """

    if content is None:
        return ""

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        return "\n".join(
            content_to_text(item)
            for item in content
        )

    if hasattr(content, "text"):
        return str(content.text)

    return str(content)


class McpClientManager:
    def __init__(
        self,
        project_root: str,
    ) -> None:
        self.project_root = project_root

        self.specs = load_mcp_server_specs(
            project_root
        )

        self.last_errors: dict[str, str] = {}

    @asynccontextmanager
    async def _session(
        self,
        spec: McpServerSpec,
    ):
        """
        根据 MCP Server 类型建立连接。
        """

        if spec.type == "stdio":

            params = StdioServerParameters(
                command=spec.command,
                args=spec.args,
                env={
                    **os.environ,
                    **spec.env,
                },
                cwd=self.project_root,
            )

            with open(
                os.devnull,
                "w",
            ) as errlog:

                async with stdio_client(
                    params,
                    errlog=errlog,
                ) as (
                    read,
                    write,
                ):

                    async with ClientSession(
                        read,
                        write,
                    ) as session:

                        await session.initialize()

                        yield session

        elif spec.type == "streamable_http":

            async with streamablehttp_client(
                spec.url,
                headers=spec.headers or None,
                timeout=spec.timeout,
            ) as (
                read,
                write,
                _session_id,
            ):

                async with ClientSession(
                    read,
                    write,
                ) as session:

                    await session.initialize()

                    yield session

        else:
            raise ValueError(
                f"Unsupported transport: {spec.type}"
            )

    async def list_server_tools(
        self,
        spec: McpServerSpec,
    ) -> list:
        """
        获取指定 MCP Server 提供的工具。
        """

        async with self._session(spec) as session:
            result = await session.list_tools()

            return list(result.tools)

    async def call_server_tool(
        self,
        spec: McpServerSpec,
        tool_name: str,
        arguments: dict,
    ) -> dict:
        """
        调用指定 MCP 工具。
        """

        async with self._session(spec) as session:

            result = await session.call_tool(
                tool_name,
                arguments,
                read_timeout_seconds=timedelta(
                    seconds=spec.timeout
                ),
            )

            return {
                "content": content_to_text(
                    result.content
                ),
                "is_error": bool(
                    result.isError
                ),
            }

    async def _tools_for_server(
        self,
        spec: McpServerSpec,
    ) -> list[RegisteredTool]:
        """
        把 MCP Server 中的远程工具包装成
        ToolRegistry 能注册的 RegisteredTool。
        """

        remote_tools = await self.list_server_tools(
            spec
        )

        wrapped: list[RegisteredTool] = []

        for remote_tool in remote_tools:

            local_name = (
                f"mcp__{spec.name}"
                f"__{remote_tool.name}"
            )

            async def handler(
                args: dict,
                *,
                server_spec=spec,
                remote_name=remote_tool.name,
            ) -> dict:

                return await self.call_server_tool(
                    server_spec,
                    remote_name,
                    args,
                )

            wrapped.append(
                RegisteredTool(
                    name=local_name,
                    description=(
                        remote_tool.description
                        or
                        f"MCP tool {remote_tool.name}"
                    ),
                    parameters=(
                        remote_tool.inputSchema
                        or {
                            "type": "object",
                            "properties": {},
                        }
                    ),
                    handler=handler,
                )
            )

        return wrapped

    async def load_tools(
        self,
    ) -> list[RegisteredTool]:
        """
        加载所有启用的 MCP Server 工具。
        单个 Server 失败不会影响其他 Server。
        """

        all_tools: list[RegisteredTool] = []

        self.last_errors.clear()

        for spec in self.specs.values():

            if not spec.enabled:
                continue

            try:
                tools = await self._tools_for_server(
                    spec
                )

                all_tools.extend(tools)

            except Exception as exc:
                self.last_errors[
                    spec.name
                ] = str(exc)

        return all_tools