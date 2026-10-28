from pathlib import Path

import asyncio
import pytest

from app.agent.agents_loader import (
    AgentsLoadError,
    load_agents_md,
)
from app.agent.react_agent import ReActAgent
from app.tools.registry import ToolRegistry


MAX_CHARS = 20_000


# ============================================================
# AGENTS.md 文件加载测试
# ============================================================


def test_agents_md_exists_and_readable(
    tmp_path: Path,
):
    (tmp_path / "AGENTS.md").write_text(
        "修改完成后运行测试。",
        encoding="utf-8",
    )

    result = load_agents_md(
        tmp_path,
        max_chars=MAX_CHARS,
    )

    assert result.status == "loaded"
    assert result.content == "修改完成后运行测试。"


def test_agents_md_missing_is_non_fatal(
    tmp_path: Path,
):
    result = load_agents_md(
        tmp_path,
        max_chars=MAX_CHARS,
    )

    assert result.status == "missing"
    assert result.content is None


def test_agents_md_empty(
    tmp_path: Path,
):
    (tmp_path / "AGENTS.md").write_text(
        "",
        encoding="utf-8",
    )

    result = load_agents_md(
        tmp_path,
        max_chars=MAX_CHARS,
    )

    assert result.status == "empty"
    assert result.content is None


def test_agents_md_too_large_is_rejected(
    tmp_path: Path,
):
    (tmp_path / "AGENTS.md").write_text(
        "A" * (MAX_CHARS + 1),
        encoding="utf-8",
    )

    with pytest.raises(
        AgentsLoadError,
    ):
        load_agents_md(
            tmp_path,
            max_chars=MAX_CHARS,
        )


def test_agents_md_decode_error_fails_startup(
    tmp_path: Path,
):
    (tmp_path / "AGENTS.md").write_bytes(
        b"\xff\xfe\xfa"
    )

    with pytest.raises(
        AgentsLoadError,
    ):
        load_agents_md(
            tmp_path,
            max_chars=MAX_CHARS,
        )


def test_new_load_reads_updated_file(
    tmp_path: Path,
):
    path = tmp_path / "AGENTS.md"

    path.write_text(
        "RULE_V1",
        encoding="utf-8",
    )

    first = load_agents_md(
        tmp_path
    )

    path.write_text(
        "RULE_V2",
        encoding="utf-8",
    )

    second = load_agents_md(
        tmp_path
    )

    assert first.content == "RULE_V1"
    assert second.content == "RULE_V2"


# ============================================================
# ReActAgent + AGENTS.md 上下文测试
# ============================================================


class RecordingClient:
    """
    记录 ReActAgent 实际发送给模型的 messages。

    本文件只测试 AGENTS.md 上下文行为，
    不需要真正执行任何工具。
    """

    def __init__(self):
        self.calls = []

    def chat(
        self,
        messages,
        tools=None,
    ):
        # 保存当前请求的消息快照。
        self.calls.append(
            [
                dict(message)
                for message in messages
            ]
        )

        # 不产生 tool_calls，
        # 让本轮 ReAct 直接结束。
        return {
            "role": "assistant",
            "content": "done",
        }


def make_registry() -> ToolRegistry:
    """
    AGENTS.md 测试不需要真正执行工具，
    因此使用空 ToolRegistry 即可。

    这同时适配 Lab06 中 ReActAgent
    从 tools 参数切换到 registry 参数的变化。
    """
    return ToolRegistry()


def test_agents_md_enters_model_context(
    tmp_path: Path,
):
    """
    AGENTS.md 内容必须真正进入
    client.chat() 收到的 system message。
    """

    (
        tmp_path
        / "AGENTS.md"
    ).write_text(
        "RULE_X",
        encoding="utf-8",
    )

    client = RecordingClient()

    agent = ReActAgent(
        client=client,
        registry=make_registry(),
        project_root=tmp_path,
    )

    asyncio.run(
        agent.run(
            "hello"
        )
    )

    assert len(client.calls) == 1

    messages = client.calls[0]

    system_messages = [
        message
        for message in messages
        if message.get("role")
        == "system"
    ]

    assert len(system_messages) == 1

    assert (
        "RULE_X"
        in system_messages[0]["content"]
    )


def test_agents_md_not_duplicated_between_runs(
    tmp_path: Path,
):
    """
    同一会话进行多轮 run() 时，
    AGENTS.md 只能存在一份，
    不能每轮重复追加。
    """

    (
        tmp_path
        / "AGENTS.md"
    ).write_text(
        "RULE_X",
        encoding="utf-8",
    )

    client = RecordingClient()

    agent = ReActAgent(
        client=client,
        registry=make_registry(),
        project_root=tmp_path,
    )

    asyncio.run(
        agent.run(
            "first"
        )
    )

    asyncio.run(
        agent.run(
            "second"
        )
    )

    assert len(client.calls) == 2

    for messages in client.calls:

        system_messages = [
            message
            for message in messages
            if message.get("role")
            == "system"
        ]

        assert (
            len(system_messages)
            == 1
        )

        assert (
            "RULE_X"
            in system_messages[0][
                "content"
            ]
        )


def test_current_session_keeps_startup_snapshot(
    tmp_path: Path,
):
    """
    Agent 创建时读取 AGENTS.md。

    同一个 Agent 会话创建完成后，
    即使磁盘 AGENTS.md 被修改，
    当前会话仍应继续使用启动时版本。
    """

    agents_file = (
        tmp_path
        / "AGENTS.md"
    )

    agents_file.write_text(
        "RULE_V1",
        encoding="utf-8",
    )

    client = RecordingClient()

    # 创建 Agent 时读取 RULE_V1。
    agent = ReActAgent(
        client=client,
        registry=make_registry(),
        project_root=tmp_path,
    )

    # Agent 已创建后再修改磁盘文件。
    agents_file.write_text(
        "RULE_V2",
        encoding="utf-8",
    )

    asyncio.run(
        agent.run(
            "hello"
        )
    )

    text = "\n".join(
        str(
            message.get(
                "content",
                "",
            )
        )
        for message
        in client.calls[0]
    )

    assert "RULE_V1" in text
    assert "RULE_V2" not in text


def test_new_session_reads_new_version(
    tmp_path: Path,
):
    """
    创建新的 ReActAgent，
    相当于创建新的会话。

    新会话应该重新读取磁盘上的
    最新 AGENTS.md。
    """

    agents_file = (
        tmp_path
        / "AGENTS.md"
    )

    agents_file.write_text(
        "RULE_V1",
        encoding="utf-8",
    )

    client1 = RecordingClient()

    agent1 = ReActAgent(
        client=client1,
        registry=make_registry(),
        project_root=tmp_path,
    )

    asyncio.run(
        agent1.run(
            "first"
        )
    )

    # 修改磁盘中的规则。
    agents_file.write_text(
        "RULE_V2",
        encoding="utf-8",
    )

    client2 = RecordingClient()

    # 新建 Agent = 新会话。
    agent2 = ReActAgent(
        client=client2,
        registry=make_registry(),
        project_root=tmp_path,
    )

    asyncio.run(
        agent2.run(
            "second"
        )
    )

    text1 = "\n".join(
        str(
            message.get(
                "content",
                "",
            )
        )
        for message
        in client1.calls[0]
    )

    text2 = "\n".join(
        str(
            message.get(
                "content",
                "",
            )
        )
        for message
        in client2.calls[0]
    )

    assert "RULE_V1" in text1
    assert "RULE_V2" in text2