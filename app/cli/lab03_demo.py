from __future__ import annotations

import argparse
from pathlib import Path

from app.llm.glm_client import GLMClient

from app.agent.react_agent import ReActAgent
from app.core.fake_llm import FakeLLMClient
from app.tools.basic_tools import BasicTools

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



def live_chat() -> None:
    """
    普通 GLM 对话测试。
    当前阶段不接入 tools。
    """

    client = GLMClient()

    messages = [
        {
            "role": "system",
            "content": "你是一个 Python 助手。",
        },
        {
            "role": "user",
            "content": "请用一句话介绍 Python。",
        },
    ]

    response = client.chat(
        messages
    )

    print(
        response["content"]
    )


def react_demo(
    fake=False,
    trace=False,
):

    root = Path(
        "demo_lab03"
    )


    tools = BasicTools(
        root
    )


    if fake:

        client = FakeLLMClient()

    else:

        client = GLMClient()


    agent = ReActAgent(
        client=client,
        tools=tools,
        max_iterations=10,
    )


    result = agent.run(
        """
    你是一个 ReAct Agent。

    你拥有工具：
    - list_dir
    - read_file
    - write_file
    - execute_command

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


def main() -> None:

    parser = argparse.ArgumentParser()

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




    args = parser.parse_args()


    if args.fake:

        react_demo(
            fake=True,
            trace=args.trace,
        )


    elif args.live and not args.chat_only:

        react_demo(
            fake=False,
            trace=args.trace,
        )


    elif (
        args.live
        and args.chat_only
    ):

        live_chat()


    else:

        parser.print_help()


if __name__ == "__main__":
    main()