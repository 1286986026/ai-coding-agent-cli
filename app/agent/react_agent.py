from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any


@dataclass
class AgentResult:
    status: str
    answer: str
    iterations: int


class ReActAgent:
    """
    最小 ReAct Agent。

    流程：

    用户目标
        ↓
    LLM
        ↓
    tool_calls
        ↓
    工具执行
        ↓
    Observation
        ↓
    LLM
    """

    def __init__(
        self,
        client,
        tools,
        max_iterations: int = 10,
    ):
        self.client = client
        self.tools = tools
        self.max_iterations = max_iterations

        self.messages = []


    def run(
        self,
        task: str,
    ) -> AgentResult:

        if not self.messages:
            self.messages = []


        self.messages.append(
            {
            "role": "user",
            "content": task,
            }
        )


        for iteration in range(
            1,
            self.max_iterations + 1,
        ):

            response = self.client.chat(
                self.messages,
                tools=self.tools.schema(),
            )


            # 保存 assistant 消息
            self.messages.append(
                response
            )


            tool_calls = (
                response.get(
                    "tool_calls",
                    []
                )
            )


            # 没有工具调用
            if not tool_calls:

                return AgentResult(
                    status="completed",
                    answer=response.get(
                        "content",
                        "",
                    ),
                    iterations=iteration,
                )


            # 执行工具

            for call in tool_calls:

                tool_id = call["id"]

                function = call["function"]

                name = function["name"]

                arguments = json.loads(
                    function["arguments"]
                )


                result = self.dispatch(
                    name,
                    arguments,
                )


                # Observation 回灌

                self.messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_id,
                        "content": json.dumps(
                            result,
                            ensure_ascii=False,
                        ),
                    }
                )


        return AgentResult(
            status="iteration_limit",
            answer="",
            iterations=self.max_iterations,
        )


    def dispatch(
        self,
        name: str,
        arguments: dict[str, Any],
    ):

        mapping = {
            "read_file":
                self.tools.read_file,

            "write_file":
                self.tools.write_file,

            "list_dir":
                self.tools.list_dir,

            "execute_command":
                self.tools.execute_command,
        }


        if name not in mapping:
            return {
                "ok": False,
                "error":
                    f"unknown tool: {name}",
            }


        return mapping[name](
            **arguments
        )