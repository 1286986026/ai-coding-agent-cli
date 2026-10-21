from pathlib import Path

import pytest

from app.agent.agents_loader import (
    AgentsLoadError,
    load_agents_md,
)


MAX_CHARS = 20_000


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

    first = load_agents_md(tmp_path)

    path.write_text(
        "RULE_V2",
        encoding="utf-8",
    )

    second = load_agents_md(tmp_path)

    assert first.content == "RULE_V1"
    assert second.content == "RULE_V2"

from app.agent.react_agent import ReActAgent


class RecordingClient:
    """
    记录 ReActAgent 实际发送给模型的 messages。
    """

    def __init__(self):
        self.calls = []

    def chat(
        self,
        messages,
        tools=None,
    ):
        # 保存本次请求的消息快照
        self.calls.append(
            [
                dict(message)
                for message in messages
            ]
        )

        # 本测试只验证上下文，
        # 不需要真正产生工具调用
        return {
            "role": "assistant",
            "content": "done",
        }


class DummyTools:
    """
    测试上下文时使用的最小工具对象。
    """

    def schema(self):
        return []


def test_agents_md_enters_model_context(
    tmp_path: Path,
):
    """
    AGENTS.md 的内容必须真正进入
    client.chat() 收到的 messages。
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
        tools=DummyTools(),
        project_root=tmp_path,
    )

    agent.run("hello")

    assert len(client.calls) == 1

    messages = client.calls[0]

    system_messages = [
        message
        for message in messages
        if message.get("role") == "system"
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
    同一会话多轮调用时，
    AGENTS.md 只能保留一份，
    不能每次 run() 都重复追加。
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
        tools=DummyTools(),
        project_root=tmp_path,
    )

    agent.run("first")
    agent.run("second")

    assert len(client.calls) == 2

    for messages in client.calls:
        system_messages = [
            message
            for message in messages
            if message.get("role") == "system"
        ]

        assert len(system_messages) == 1

        assert (
            "RULE_X"
            in system_messages[0]["content"]
        )


def test_current_session_keeps_startup_snapshot(
    tmp_path: Path,
):
    """
    当前会话创建以后，即使磁盘上的
    AGENTS.md 被修改，也仍使用启动时版本。
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

    # 此时会话读取 RULE_V1
    agent = ReActAgent(
        client=client,
        tools=DummyTools(),
        project_root=tmp_path,
    )

    # 会话已经创建，再修改磁盘文件
    agents_file.write_text(
        "RULE_V2",
        encoding="utf-8",
    )

    agent.run("hello")

    text = "\n".join(
        str(message.get("content", ""))
        for message in client.calls[0]
    )

    assert "RULE_V1" in text
    assert "RULE_V2" not in text


def test_new_session_reads_new_version(
    tmp_path: Path,
):
    """
    新会话重新创建时，
    应当读取磁盘上的新版 AGENTS.md。
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
        tools=DummyTools(),
        project_root=tmp_path,
    )

    agent1.run("first")

    # 修改规则文件
    agents_file.write_text(
        "RULE_V2",
        encoding="utf-8",
    )

    client2 = RecordingClient()

    # 新建 Agent = 新会话
    agent2 = ReActAgent(
        client=client2,
        tools=DummyTools(),
        project_root=tmp_path,
    )

    agent2.run("second")

    text1 = "\n".join(
        str(message.get("content", ""))
        for message in client1.calls[0]
    )

    text2 = "\n".join(
        str(message.get("content", ""))
        for message in client2.calls[0]
    )

    assert "RULE_V1" in text1
    assert "RULE_V2" in text2

from app.agent.react_agent import ReActAgent


class RecordingClient:
    """
    记录 Agent 实际发送给模型的 messages。
    """

    def __init__(self):
        self.calls = []

    def chat(
        self,
        messages,
        tools=None,
    ):
        # 保存当前请求快照
        self.calls.append(
            [
                dict(message)
                for message in messages
            ]
        )

        # 本测试不需要工具调用，
        # 直接返回最终回答
        return {
            "role": "assistant",
            "content": "done",
        }


class DummyTools:
    """
    本测试只验证上下文，
    不真正执行工具。
    """

    def schema(self):
        return []

def test_agents_md_enters_model_context(
    tmp_path: Path,
):
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
        tools=DummyTools(),
        project_root=tmp_path,
    )

    agent.run("hello")

    assert len(client.calls) == 1

    messages = client.calls[0]

    system_messages = [
        message
        for message in messages
        if message.get("role") == "system"
    ]

    assert len(system_messages) == 1

    assert (
        "RULE_X"
        in system_messages[0]["content"]
    )

def test_agents_md_enters_model_context(
    tmp_path: Path,
):
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
        tools=DummyTools(),
        project_root=tmp_path,
    )

    agent.run("hello")

    assert len(client.calls) == 1

    messages = client.calls[0]

    system_messages = [
        message
        for message in messages
        if message.get("role") == "system"
    ]

    assert len(system_messages) == 1

    assert (
        "RULE_X"
        in system_messages[0]["content"]
    )

def test_current_session_keeps_startup_snapshot(
    tmp_path: Path,
):
    agents_file = (
        tmp_path
        / "AGENTS.md"
    )

    agents_file.write_text(
        "RULE_V1",
        encoding="utf-8",
    )

    client = RecordingClient()

    agent = ReActAgent(
        client=client,
        tools=DummyTools(),
        project_root=tmp_path,
    )

    # Agent 已经创建完成以后，
    # 再修改磁盘文件
    agents_file.write_text(
        "RULE_V2",
        encoding="utf-8",
    )

    agent.run("hello")

    text = "\n".join(
        str(message.get("content", ""))
        for message in client.calls[0]
    )

    assert "RULE_V1" in text
    assert "RULE_V2" not in text

def test_new_session_reads_new_version(
    tmp_path: Path,
):
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
        tools=DummyTools(),
        project_root=tmp_path,
    )

    agent1.run("first")

    # 修改磁盘规则
    agents_file.write_text(
        "RULE_V2",
        encoding="utf-8",
    )

    client2 = RecordingClient()

    # 创建新的 Agent = 新会话
    agent2 = ReActAgent(
        client=client2,
        tools=DummyTools(),
        project_root=tmp_path,
    )

    agent2.run("second")

    text1 = "\n".join(
        str(message.get("content", ""))
        for message in client1.calls[0]
    )

    text2 = "\n".join(
        str(message.get("content", ""))
        for message in client2.calls[0]
    )

    assert "RULE_V1" in text1
    assert "RULE_V2" in text2