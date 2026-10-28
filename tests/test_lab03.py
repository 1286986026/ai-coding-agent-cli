from pathlib import Path
import asyncio

from app.agent.react_agent import ReActAgent
from app.core.fake_llm import FakeLLMClient
from app.tools.basic_tools import BasicTools
from app.tools.registry import (
    ToolRegistry,
    register_builtin_tools,
)


def make_registry(
    root: Path,
) -> ToolRegistry:
    """
    为测试创建 ToolRegistry，
    并注册 Lab03 原来的 4 个内置工具。
    """

    basic = BasicTools(root)

    registry = ToolRegistry()

    register_builtin_tools(
        registry,
        basic,
    )

    return registry


def test_react_fake_full_flow(
    tmp_path,
):
    """
    测试完整 ReAct 流程：

    FakeLLM
        ↓
    Agent
        ↓
    ToolRegistry
        ↓
    Tools
        ↓
    Observation
        ↓
    Final Answer
    """

    # 创建测试目录
    root = tmp_path

    # 创建测试文件
    notes = (
        root
        / "notes.txt"
    )

    notes.write_text(
        "Lab03 test notes",
        encoding="utf-8",
    )

    registry = make_registry(
        root
    )

    client = FakeLLMClient()

    agent = ReActAgent(
        client=client,
        registry=registry,
        max_iterations=10,
    )

    result = asyncio.run(
        agent.run(
            "完成四工具任务"
        )
    )

    # 最终状态
    assert (
        result.status
        == "completed"
    )

    # Fake 应该调用 5 次
    assert (
        result.iterations
        == 5
    )

    # Fake 请求历史
    assert (
        len(client.requests)
        == 5
    )

    # 最终回答
    assert (
        "任务完成"
        in result.answer
    )

    # 检查 tool 消息回灌
    roles = [
        message["role"]
        for message
        in agent.messages
    ]

    assert (
        roles.count("tool")
        == 4
    )

    # 写文件成功
    assert (
        root / "report.txt"
    ).exists()


def test_tool_call_id_preserved(
    tmp_path,
):
    """
    测试 assistant tool_call_id
    和 tool message 对应。
    """

    client = FakeLLMClient()

    registry = make_registry(
        tmp_path
    )

    agent = ReActAgent(
        client=client,
        registry=registry,
    )

    asyncio.run(
        agent.run(
            "测试工具调用"
        )
    )

    assistant_ids = []

    tool_ids = []

    for msg in agent.messages:

        if (
            msg["role"]
            == "assistant"
        ):

            for call in (
                msg.get(
                    "tool_calls"
                )
                or []
            ):
                assistant_ids.append(
                    call["id"]
                )

        if (
            msg["role"]
            == "tool"
        ):

            tool_ids.append(
                msg[
                    "tool_call_id"
                ]
            )

    assert (
        assistant_ids
        == tool_ids
    )


def test_unknown_tool_handled(
    tmp_path,
):
    """
    测试未知工具不会导致 Agent 崩溃。
    """

    class UnknownToolLLM:

        def chat(
            self,
            messages,
            tools=None,
        ):
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": (
                            "call_unknown"
                        ),
                        "type": "function",
                        "function": {
                            "name": (
                                "not_exist_tool"
                            ),
                            "arguments": "{}",
                        },
                    }
                ],
            }

    registry = make_registry(
        tmp_path
    )

    agent = ReActAgent(
        client=UnknownToolLLM(),
        registry=registry,
        max_iterations=1,
    )

    result = asyncio.run(
        agent.run(
            "调用不存在工具"
        )
    )

    assert (
        result.status
        == "iteration_limit"
        or result.status
        == "completed"
    )

    tool_messages = [
        message
        for message
        in agent.messages
        if (
            message["role"]
            == "tool"
        )
    ]

    assert (
        len(tool_messages)
        == 1
    )

    # ToolRegistry 返回的是
    # "Unknown tool: ..."
    # 因此统一转小写后判断。
    assert (
        "unknown tool"
        in tool_messages[0][
            "content"
        ].lower()
    )


def test_iteration_limit():
    """
    测试超过最大迭代次数后停止。
    """

    class InfiniteToolLLM:

        def chat(
            self,
            messages,
            tools=None,
        ):
            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": (
                            "loop_call"
                        ),
                        "type": "function",
                        "function": {
                            "name": (
                                "list_dir"
                            ),
                            "arguments": (
                                '{"path":"."}'
                            ),
                        },
                    }
                ],
            }

    root = Path(".")

    registry = make_registry(
        root
    )

    agent = ReActAgent(
        client=InfiniteToolLLM(),
        registry=registry,
        max_iterations=2,
    )

    result = asyncio.run(
        agent.run(
            "一直调用工具"
        )
    )

    assert (
        result.status
        == "iteration_limit"
    )

    assert (
        result.iterations
        == 2
    )


def test_fake_llm_deepcopy_snapshot():
    """
    测试 FakeLLMClient 保存历史快照，
    后续 messages 修改不会影响旧记录。
    """

    client = FakeLLMClient()

    messages = [
        {
            "role": "user",
            "content": "hello",
        }
    ]

    client.chat(
        messages
    )

    # 修改原始 messages
    messages.append(
        {
            "role": "assistant",
            "content": "changed",
        }
    )

    # 第一份请求快照不应该变化
    assert (
        len(
            client.requests[0]
        )
        == 1
    )

    assert (
        client.requests[0][0][
            "content"
        ]
        == "hello"
    )


def test_follow_up_keeps_history(
    tmp_path,
):
    """
    测试同一个 Agent 连续运行两次时，
    会保留上一轮消息历史。
    """

    registry = make_registry(
        tmp_path
    )

    agent = ReActAgent(
        client=FakeLLMClient(),
        registry=registry,
    )

    asyncio.run(
        agent.run(
            "第一次任务"
        )
    )

    history_length = len(
        agent.messages
    )

    asyncio.run(
        agent.run(
            "请继续说明刚才结果"
        )
    )

    assert (
        len(agent.messages)
        > history_length
    )

    user_messages = [
        message
        for message
        in agent.messages
        if (
            message["role"]
            == "user"
        )
    ]

    assert (
        len(user_messages)
        == 2
    )