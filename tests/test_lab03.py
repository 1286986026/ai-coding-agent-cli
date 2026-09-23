from pathlib import Path

from app.agent.react_agent import ReActAgent
from app.core.fake_llm import FakeLLMClient
from app.tools.basic_tools import BasicTools


def test_react_fake_full_flow(tmp_path):
    """
    测试完整 ReAct 流程：

    FakeLLM
        ↓
    Agent
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
    notes = root / "notes.txt"

    notes.write_text(
        "Lab03 test notes",
        encoding="utf-8",
    )


    tools = BasicTools(
        root
    )


    client = FakeLLMClient()


    agent = ReActAgent(
        client=client,
        tools=tools,
        max_iterations=10,
    )


    result = agent.run(
        "完成四工具任务"
    )


    # 最终状态
    assert result.status == "completed"


    # Fake 应该调用5次
    assert result.iterations == 5


    # Fake 请求历史
    assert len(client.requests) == 5


    # 最终回答
    assert (
        "任务完成"
        in result.answer
    )


    # 检查 tool 消息回灌
    roles = [
        m["role"]
        for m in agent.messages
    ]


    assert roles.count(
        "tool"
    ) == 4


    # 写文件成功
    assert (
        root / "report.txt"
    ).exists()

def test_tool_call_id_preserved(tmp_path):
    """
    测试 assistant tool_call_id
    和 tool message 对应。
    """

    from app.agent.react_agent import ReActAgent
    from app.core.fake_llm import FakeLLMClient
    from app.tools.basic_tools import BasicTools


    client = FakeLLMClient()

    tools = BasicTools(
        tmp_path
    )


    agent = ReActAgent(
        client,
        tools,
    )


    agent.run(
        "测试工具调用"
    )


    assistant_ids = []

    tool_ids = []


    for msg in agent.messages:

        if msg["role"] == "assistant":

            for call in (
                msg.get(
                    "tool_calls"
             )
            or []
    ):
                assistant_ids.append(
                    call["id"]
                )


        if msg["role"] == "tool":

            tool_ids.append(
                msg["tool_call_id"]
            )


    assert assistant_ids == tool_ids


def test_unknown_tool_handled(tmp_path):
    """
    测试未知工具不会导致 Agent 崩溃。
    """

    from app.agent.react_agent import ReActAgent
    from app.tools.basic_tools import BasicTools


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
                        "id": "call_unknown",
                        "type": "function",
                        "function": {
                            "name": "not_exist_tool",
                            "arguments": "{}",
                        },
                    }
                ],
            }


    agent = ReActAgent(
        UnknownToolLLM(),
        BasicTools(tmp_path),
        max_iterations=1,
    )


    result = agent.run(
        "调用不存在工具"
    )


    assert (
        result.status
        == "iteration_limit"
        or result.status
        == "completed"
    )


    tool_messages = [
        m
        for m in agent.messages
        if m["role"] == "tool"
    ]


    assert len(tool_messages) == 1


    assert (
        "unknown tool"
        in tool_messages[0]["content"]
    )

def test_iteration_limit():
    """
    测试超过最大迭代次数后停止。
    """

    from app.agent.react_agent import ReActAgent
    from app.tools.basic_tools import BasicTools
    from pathlib import Path


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
                        "id": "loop_call",
                        "type": "function",
                        "function": {
                            "name": "list_dir",
                            "arguments": (
                                '{"path":"."}'
                            ),
                        },
                    }
                ],
            }


    agent = ReActAgent(
        InfiniteToolLLM(),
        BasicTools(
            Path(".")
        ),
        max_iterations=2,
    )


    result = agent.run(
        "一直调用工具"
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

    from app.core.fake_llm import FakeLLMClient


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
        len(client.requests[0])
        == 1
    )


    assert (
        client.requests[0][0]["content"]
        == "hello"
    )

def test_follow_up_keeps_history(tmp_path):

    from app.agent.react_agent import ReActAgent
    from app.core.fake_llm import FakeLLMClient
    from app.tools.basic_tools import BasicTools


    agent = ReActAgent(
        FakeLLMClient(),
        BasicTools(tmp_path),
    )


    agent.run(
        "第一次任务"
    )


    history_length = len(
        agent.messages
    )


    agent.run(
        "请继续说明刚才结果"
    )


    assert len(
        agent.messages
    ) > history_length


    user_messages = [
        m
        for m in agent.messages
        if m["role"] == "user"
    ]


    assert len(
        user_messages
    ) == 2


