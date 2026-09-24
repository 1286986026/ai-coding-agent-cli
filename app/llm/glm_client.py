from __future__ import annotations

import getpass
import os
from typing import Any

import httpx


# ============================================================
# 自定义异常
# ============================================================


class LLMError(RuntimeError):
    """
    GLM 网络请求或 HTTP 层错误。
    """


class ProtocolError(RuntimeError):
    """
    GLM 返回的数据不符合本实验协议。
    """


# ============================================================
# assistant message 校验
# ============================================================


def validate_message(
    message: Any,
) -> dict[str, Any]:
    """
    校验 GLM 返回的 assistant message。

    需要保留完整 assistant message，
    因为 ReAct Agent 后续既要读取 content，
    也要读取 tool_calls。
    """

    # --------------------------------------------------------
    # message 必须是字典
    # --------------------------------------------------------

    if not isinstance(message, dict):
        raise ProtocolError(
            "assistant message 必须是字典"
        )

    # --------------------------------------------------------
    # role 必须是 assistant
    # --------------------------------------------------------

    if message.get("role") != "assistant":
        raise ProtocolError(
            "模型响应的 role 必须是 assistant"
        )

    # --------------------------------------------------------
    # content 可以是字符串或 None
    # --------------------------------------------------------

    content = message.get("content")

    if (
        content is not None
        and not isinstance(content, str)
    ):
        raise ProtocolError(
            "assistant content 必须是字符串或 None"
        )

    # --------------------------------------------------------
    # tool_calls 可以不存在、None 或 list
    # --------------------------------------------------------

    tool_calls = message.get("tool_calls")

    if tool_calls is not None:

        if not isinstance(tool_calls, list):
            raise ProtocolError(
                "tool_calls 必须是列表或 None"
            )

        for tool_call in tool_calls:

            # 每个调用必须是 dict
            if not isinstance(tool_call, dict):
                raise ProtocolError(
                    "每个 tool_call 必须是字典"
                )

            # ----------------------------------------------
            # id
            # ----------------------------------------------

            call_id = tool_call.get("id")

            if (
                not isinstance(call_id, str)
                or not call_id
            ):
                raise ProtocolError(
                    "tool_call 缺少有效 id"
                )

            # ----------------------------------------------
            # type
            # ----------------------------------------------

            if tool_call.get("type") != "function":
                raise ProtocolError(
                    "tool_call.type 必须是 function"
                )

            # ----------------------------------------------
            # function
            # ----------------------------------------------

            function = tool_call.get("function")

            if not isinstance(function, dict):
                raise ProtocolError(
                    "tool_call.function 必须是字典"
                )

            # ----------------------------------------------
            # name
            # ----------------------------------------------

            name = function.get("name")

            if (
                not isinstance(name, str)
                or not name
            ):
                raise ProtocolError(
                    "工具调用缺少有效 name"
                )

            # ----------------------------------------------
            # arguments
            #
            # 注意：
            # arguments 在模型响应中仍然是 JSON 字符串，
            # 后续 Agent 再用 json.loads() 解码。
            # ----------------------------------------------

            arguments = function.get("arguments")

            if not isinstance(arguments, str):
                raise ProtocolError(
                    "工具 arguments 必须是 JSON 字符串"
                )

    return message


# ============================================================
# GLMClient
# ============================================================


class GLMClient:
    """
    智谱 GLM Chat Completions 客户端。

    职责：
    1. 构造 HTTP 请求
    2. 添加认证 Header
    3. 发送 messages / tools
    4. 检查 HTTP 状态
    5. 解析 JSON
    6. 返回完整 assistant message

    不负责：
    - 文件读写
    - Shell 执行
    - 工具 dispatch
    - ReAct 循环
    """

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
            优先使用传入值，
            否则读取环境变量 GLM_MODEL。

        api_key:
            优先使用传入值，
            否则读取环境变量 GLM_API_KEY。
            若仍不存在，则使用 getpass 隐藏输入。

        timeout:
            HTTP 请求超时时间。

        http_client:
            可注入 httpx.Client，
            pytest 可以使用 MockTransport。
        """

        # ----------------------------------------------------
        # 模型名称
        # ----------------------------------------------------

        self.model = (
            model
            or os.environ.get("GLM_MODEL")
        )

        if not self.model:
            raise LLMError(
                "未设置 GLM_MODEL。"
                "请先设置可用模型标识。"
            )

        # ----------------------------------------------------
        # API Key
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # 其他配置
        # ----------------------------------------------------

        self.timeout = timeout
        self.http_client = http_client

    # ========================================================
    # chat
    # ========================================================

    def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """
        调用 GLM Chat Completions API。

        普通聊天：

            client.chat(messages)

        Tool Calling：

            client.chat(
                messages,
                tools=tools,
            )

        返回：
            完整 assistant message。
        """

        # ----------------------------------------------------
        # messages 基础校验
        # ----------------------------------------------------

        if not isinstance(messages, list):
            raise ProtocolError(
                "messages 必须是列表"
            )

        # ----------------------------------------------------
        # 构造请求 JSON
        # ----------------------------------------------------

        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }

        # 普通聊天时不发 tools。
        # ReAct 模式传入 tools 时才加入请求。
        if tools is not None:
            payload["tools"] = tools

        # ----------------------------------------------------
        # HTTP Headers
        # ----------------------------------------------------

        headers = {
            "Authorization": (
                f"Bearer {self.api_key}"
            ),
            "Content-Type": "application/json",
        }

        # ----------------------------------------------------
        # HTTP 请求
        # ----------------------------------------------------

        try:

            # pytest / HTTP Mock 场景
            if self.http_client is not None:

                response = self.http_client.post(
                    self.API_URL,
                    headers=headers,
                    json=payload,
                    timeout=self.timeout,
                )

            # 真实联网场景
            else:

                with httpx.Client(
                    timeout=self.timeout,
                    follow_redirects=True,
                ) as client:

                    response = client.post(
                        self.API_URL,
                        headers=headers,
                        json=payload,
                    )

            # 非 2xx 自动转为 HTTPStatusError
            response.raise_for_status()

        # ----------------------------------------------------
        # HTTP 非成功状态
        # ----------------------------------------------------

        except httpx.HTTPStatusError as exc:

            status_code = (
                exc.response.status_code
            )

            raise LLMError(
                "GLM HTTP 请求失败，"
                f"状态码: {status_code}"
            ) from exc

        # ----------------------------------------------------
        # 网络连接 / timeout 等错误
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # choices
        # ----------------------------------------------------

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

        # 本实验只接受：
        #
        # stop       -> 普通最终回答
        # tool_calls -> 模型申请工具
        #
        # length 等表示响应不完整，
        # 按 ProtocolError 处理。
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

        message = choice.get(
            "message"
        )

        return validate_message(
            message
        )