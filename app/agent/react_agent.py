from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any
from pathlib import Path
from app.agent.agents_loader import (
    load_agents_md,
)


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
        project_root: Path | None = None,
    ):
        self.client = client
        self.tools = tools
        self.max_iterations = max_iterations

        # ---------------------------------
        # Lab05：项目根目录
        # ---------------------------------

        self.project_root = (
            project_root.resolve()
            if project_root is not None
            else None
        )

        # ---------------------------------
        # Lab05：项目级规则快照
        # ---------------------------------

        self.agents_status = "not_configured"
        self.project_instructions = None

        # ---------------------------------
        # 初始化会话历史
        # ---------------------------------

        self.messages = []

        # 只有明确传入 project_root 时，
        # 才尝试加载 AGENTS.md。
        #
        # 这样旧代码 ReActAgent(client, tools)
        # 的行为完全保持不变。
        if self.project_root is not None:
            agents_result = load_agents_md(
                self.project_root
            )

            self.agents_status = (
                agents_result.status
            )

            self.project_instructions = (
                agents_result.content
            )

            # 有有效规则时，只加入一次 system message。
            if self.project_instructions:
                self.messages.append(
                    {
                        "role": "system",
                        "content": (
                            "以下是当前项目的项目级规则，"
                            "来自 AGENTS.md：\n\n"
                            f"{self.project_instructions}"
                        ),
                    }
                )

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