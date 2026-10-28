from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable


@dataclass
class RegisteredTool:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[[dict], Awaitable[dict]]


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, RegisteredTool] = {}

    def register(
        self,
        name: str,
        description: str,
        parameters: dict,
        handler: Callable,
    ) -> None:
        self._tools[name] = RegisteredTool(
            name=name,
            description=description,
            parameters=parameters,
            handler=handler,
        )

    def definitions(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in self._tools.values()
        ]

    def list_names(self) -> list[str]:
        return sorted(self._tools)

    async def dispatch(
        self,
        name: str,
        arguments: str | dict,
    ) -> dict:
        tool = self._tools.get(name)

        if tool is None:
            return {
                "ok": False,
                "error": f"Unknown tool: {name}",
            }

        try:
            args = (
                json.loads(arguments)
                if isinstance(arguments, str)
                else arguments
            )

            result = await tool.handler(args)

            if isinstance(result, dict):
                return {
                    "ok": True,
                    **result,
                }

            return {
                "ok": True,
                "content": result,
            }

        except Exception as exc:
            return {
                "ok": False,
                "error": str(exc),
            }

def register_builtin_tools(
    registry: ToolRegistry,
    basic,
) -> None:

    async def read_file_handler(args: dict) -> dict:
        return basic.read_file(args["path"])

    async def write_file_handler(args: dict) -> dict:
        return basic.write_file(
            args["path"],
            args["content"],
        )

    async def list_dir_handler(args: dict) -> dict:
        return basic.list_dir(args["path"])

    async def execute_command_handler(args: dict) -> dict:
        return basic.execute_command(
            args["command"]
        )

    definitions = {
        item["function"]["name"]: item["function"]
        for item in basic.schema()
    }

    handlers = {
        "read_file": read_file_handler,
        "write_file": write_file_handler,
        "list_dir": list_dir_handler,
        "execute_command": execute_command_handler,
    }

    for name, handler in handlers.items():
        fn = definitions[name]

        registry.register(
            name=name,
            description=fn["description"],
            parameters=fn["parameters"],
            handler=handler,
        )