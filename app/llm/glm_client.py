from __future__ import annotations

import getpass
import os
from typing import Any

import httpx


# ============================================================
# 异常定义
# ============================================================


class LLMError(RuntimeError):
    """GLM 网络请求或 HTTP 层错误。"""


class ProtocolError(RuntimeError):
    """GLM 返回的数据不符合本实验约定。"""


# ============================================================
# assistant 消息校验
# ============================================================


def validate_message(message: Any) -> dict[str, Any]:
    """
    校验模型返回的 assistant 消息。

    本实验需要保留完整 assistant message，
    因为后面不仅要读取 content，
    还需要读取 tool_calls。
    """

    if not isinstance(message, dict):
        raise ProtocolError(
            "assistant message 必须是字典"
        )

    # role 必须是 assistant
    if message.get("role") != "assistant":
        raise ProtocolError(
            "模型响应的 role 必须是 assistant"
        )

    # content 可以是字符串，也可以是 None
    content = message.get("content")

    if content is not None and not isinstance(
        content,
        str,
    ):
        raise ProtocolError(
            "assistant content 必须是字符串或 None"
        )

    # tool_calls 可以不存在、为 None，或者为列表
    tool_calls = message.get("tool_calls")

    if tool_calls is not None:
        if not isinstance(tool_calls, list):
            raise ProtocolError(
                "tool_calls 必须是列表或 None"
            )

        for tool_call in tool_calls:
            if not isinstance(tool_call, dict):
                raise ProtocolError(
                    "每个 tool_call 必须是字典"
                )

            # 每个工具调用必须有唯一 ID
            call_id = tool_call.get("id")

            if not isinstance(call_id, str) or not call_id:
                raise ProtocolError(
                    "tool_call 缺少有效 id"
                )

            # 当前课程只处理 function 类型
            if tool_call.get("type") != "function":
                raise ProtocolError(
                    "tool_call.type 必须是 function"
                )

            function = tool_call.get("function")

            if not isinstance(function, dict):
                raise ProtocolError(
                    "tool_call.function 必须是字典"
                )

            name = function.get("name")
            arguments = function.get("arguments")

            if not isinstance(name, str) or not name:
                raise ProtocolError(
                    "工具调用缺少有效 name"
                )

            # arguments 仍然是 JSON 字符串，
            # 后续 BasicTools 再进行 json.loads()
            if not isinstance(arguments, str):
                raise ProtocolError(
                    "工具 arguments 必须是 JSON 字符串"
                )

    return message


# ============================================================
# GLMClient
# ============================================================


class GLMClient:
    """智谱 GLM Chat Completions 客户端。"""

    API_URL = (
        "https://open.bigmodel.cn/"
        "api/paas/v4/chat/completions"
    )

    def __init__(
    self,
    model: str | None = None,
    api_key: str | None = None,
    timeout: float = 120.0,
        http_client: httpx.Client | None = None,
    ) -> None:
        """
        初始化 GLMClient。

        model:
            模型标识。
            优先使用传入值，否则读取 GLM_MODEL。

        api_key:
            API Key。
            优先使用传入值，否则读取 GLM_API_KEY。
            如果都没有，则使用 getpass 隐藏输入。

        timeout:
            HTTP 请求超时时间。

        http_client:
            可以注入 httpx.Client。
            后续 pytest 可以注入 MockTransport。
        """

        self.model = (
            model
            or os.environ.get("GLM_MODEL")
        )

        if not self.model:
            raise LLMError(
                "未设置 GLM_MODEL。"
                "请先设置老师确认的模型标识。"
            )

        self.api_key = (
            api_key
            or os.environ.get("GLM_API_KEY")
        )

        if not self.api_key:
            self.api_key = getpass.getpass(
                "GLM API Key: "
            )

        if not self.api_key:
            raise LLMError(
                "GLM API Key 不能为空"
            )

        self.timeout = timeout
        self.http_client = http_client

    # --------------------------------------------------------
    # chat
    # --------------------------------------------------------

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        调用 GLM Chat Completions API。

        返回经过校验的完整 assistant message。

        普通聊天：
            chat(messages)

        Tool Calling：
            chat(messages, tools)
        """

        if not isinstance(messages, list):
            raise ProtocolError(
                "messages 必须是列表"
            )

        # ====================================================
        # 构造请求
        # ====================================================

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        # 普通聊天时不发送 tools
        if tools is not None:
            payload["tools"] = tools

        headers = {
            "Authorization": (
                f"Bearer {self.api_key}"
            ),
            "Content-Type": "application/json",
        }

        try:
            # 如果测试时注入了 Client，
            # 就使用注入的 Client。
            if self.http_client is not None:
                response = self.http_client.post(
                    self.API_URL,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )

            else:
                # 正常真实请求
                with httpx.Client(
                    timeout=self.timeout,
                    follow_redirects=True,
                ) as client:
                    response = client.post(
                        self.API_URL,
                        headers=headers,
                        json=payload,
                    )

            # HTTP 非 2xx 时抛出异常
            response.raise_for_status()

        except httpx.HTTPStatusError as exc:
            status_code = (
                exc.response.status_code
            )

            raise LLMError(
                "GLM HTTP 请求失败，"
                f"状态码: {status_code}"
            ) from exc

        except httpx.RequestError as exc:
            raise LLMError(
                f"GLM 网络请求失败: {exc}"
            ) from exc

        # ====================================================
        # JSON 解析
        # ====================================================

        try:
            data = response.json()

        except ValueError as exc:
            raise ProtocolError(
                "GLM 响应不是合法 JSON"
            ) from exc

        if not isinstance(data, dict):
            raise ProtocolError(
                "GLM 响应顶层必须是 JSON 对象"
            )

        choices = data.get("choices")

        if (
            not isinstance(choices, list)
            or not choices
        ):
            raise ProtocolError(
                "GLM 响应缺少有效 choices"
            )

        choice = choices[0]

        if not isinstance(choice, dict):
            raise ProtocolError(
                "choices[0] 必须是对象"
            )

        # ====================================================
        # finish_reason
        # ====================================================

        finish_reason = choice.get(
            "finish_reason"
        )

        # 本实验只把 stop 和 tool_calls
        # 作为支持的完整结束标记
        if finish_reason not in {
            "stop",
            "tool_calls",
        }:
            raise ProtocolError(
                "不支持的 finish_reason: "
                f"{finish_reason}"
            )

        # ====================================================
        # assistant message
        # ====================================================

        message = choice.get("message")

        return validate_message(message)