from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.llm.glm_client import GLMClient
from app.agent.react_agent import ReActAgent
from app.core.fake_llm import FakeLLMClient
from app.tools.basic_tools import BasicTools

from app.tools.registry import (
    ToolRegistry,
    register_builtin_tools,
)

from app.mcp.mcp_client import (
    McpClientManager,
)


def print_trace(messages):

    print("\n========== TRACE ==========")

    for i, msg in enumerate(messages):

        print(f"\n[{i}] {msg['role']}")

        if msg.get("tool_calls"):

            print("tool_calls:")
            print(
                msg["tool_calls"]
            )

        if msg.get("content"):

            print(
                msg["content"]
            )

    print(
        "\n========== END =========="
    )


async def build_registry(
    root: Path,
) -> tuple[
    ToolRegistry,
    McpClientManager,
]:
    """
    创建统一 ToolRegistry。

    1. 注册 Lab03 原有的 4 个内置工具
    2. 加载 filesystem / zread MCP 工具
    3. 将 MCP 工具注册到同一个 Registry
    """

    # -----------------------------
    # 1. 原有内置工具
    # -----------------------------

    basic = BasicTools(
        root
    )

    registry = ToolRegistry()

    register_builtin_tools(
        registry,
        basic,
    )

    # -----------------------------
    # 2. MCP 工具
    # -----------------------------

    mcp_manager = McpClientManager(
        str(Path.cwd().resolve())
    )

    mcp_tools = await (
        mcp_manager.load_tools()
    )

    for tool in mcp_tools:

        registry.register(
            tool.name,
            tool.description,
            tool.parameters,
            tool.handler,
        )

    # -----------------------------
    # 3. 打印注册结果
    # -----------------------------

    print(
        f"\n已注册 "
        f"{len(registry.list_names())} "
        f"个工具："
    )

    for name in registry.list_names():

        source = (
            "MCP"
            if name.startswith("mcp__")
            else "内置"
        )

        print(
            f"[{source}] {name}"
        )

    # -----------------------------
    # 4. MCP 连接失败信息
    # -----------------------------

    for server, error in (
        mcp_manager.last_errors.items()
    ):

        print(
            f"[警告] MCP 服务器 "
            f"{server} 连接失败："
            f"{error}"
        )

    return registry, mcp_manager


async def live_chat(
    project_root: Path | None = None,
) -> None:
    """
    多轮 ReAct 聊天模式

    支持：
    1. 用户连续输入
    2. 调用 ReActAgent
    3. 保留历史
    4. /exit 退出
    5. 内置工具 + MCP 工具
    """

    root = Path(
        "demo_lab03"
    )

    # -----------------------------
    # 构造统一工具 Registry
    # -----------------------------

    registry, _ = await build_registry(
        root
    )

    # -----------------------------
    # Live GLM
    # -----------------------------

    client = GLMClient()

    agent = ReActAgent(
        client=client,
        registry=registry,
        max_iterations=10,
        project_root=project_root,
    )

    print(
        "\n进入 Lab03 ReAct 聊天模式"
    )

    print(
        "输入 /exit 退出\n"
    )

    while True:

        user_input = input(
            "User: "
        )

        if (
            user_input.strip()
            == "/exit"
        ):

            print(
                "退出聊天"
            )

            break

        # Agent.run() 已改为 async
        result = await agent.run(
            user_input
        )

        print(
            "\n状态:"
        )

        print(
            result.status
        )

        print(
            "\n回答:"
        )

        print(
            result.answer
        )

        print(
            "\n----------------\n"
        )


async def react_demo(
    fake=False,
    trace=False,
    project_root: Path | None = None,
):

    root = Path(
        "demo_lab03"
    )

    # -----------------------------
    # 构造统一工具 Registry
    # -----------------------------

    registry, _ = await build_registry(
        root
    )

    # -----------------------------
    # Fake / Live Client
    # -----------------------------

    if fake:

        client = FakeLLMClient()

    else:

        client = GLMClient()

    # -----------------------------
    # 创建 ReAct Agent
    # -----------------------------

    agent = ReActAgent(
        client=client,
        registry=registry,
        max_iterations=10,
        project_root=project_root,
    )

    # -----------------------------
    # 运行 ReAct
    # -----------------------------

    result = await agent.run(
        """
    你是一个 ReAct Agent。

    你拥有工具：
    - list_dir
    - read_file
    - write_file
    - execute_command

    同时可能拥有通过 MCP 接入的外部工具。

    必须使用工具完成任务。

    禁止：
    - 编写脚本让我执行
    - 解释如何完成
    - 假设执行结果

    必须按照下面顺序：

    1. 调用 list_dir 查看 demo_lab03 目录
    2. 调用 read_file 读取 notes.txt
    3. 调用 write_file 创建 report.txt
    4. 调用 execute_command 执行 echo lab03-shell-ok

    所有工具执行完成后，再输出最终总结。
    """
    )

    print(
        "状态:",
        result.status
    )

    print(
        "回答:",
        result.answer
    )

    if trace:

        print_trace(
            agent.messages
        )


async def main() -> None:

    parser = (
        argparse.ArgumentParser()
    )

    parser.add_argument(
        "--live",
        action="store_true",
    )

    parser.add_argument(
        "--chat-only",
        action="store_true",
    )

    parser.add_argument(
        "--fake",
        action="store_true",
    )

    parser.add_argument(
        "--trace",
        action="store_true",
    )

    parser.add_argument(
        "--project-root",
        type=Path,
        default=None,
        help=(
            "项目根目录；指定后，"
            "新会话启动时加载其中的 "
            "AGENTS.md"
        ),
    )

    args = parser.parse_args()

    # -----------------------------
    # Fake ReAct Demo
    # -----------------------------

    if args.fake:

        await react_demo(
            fake=True,
            trace=args.trace,
            project_root=(
                args.project_root
            ),
        )

    # -----------------------------
    # Live ReAct Demo
    # -----------------------------

    elif (
        args.live
        and not args.chat_only
    ):

        await react_demo(
            fake=False,
            trace=args.trace,
            project_root=(
                args.project_root
            ),
        )

    # -----------------------------
    # Live 多轮聊天
    # -----------------------------

    elif (
        args.live
        and args.chat_only
    ):

        await live_chat(
            project_root=(
                args.project_root
            )
        )

    else:

        parser.print_help()


if __name__ == "__main__":

    asyncio.run(
        main()
    )