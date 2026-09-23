from __future__ import annotations

import argparse

from app.llm.glm_client import GLMClient


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

    args = parser.parse_args()

    if (
        args.live
        and args.chat_only
    ):
        live_chat()

    else:
        parser.print_help()


if __name__ == "__main__":
    main()