from __future__ import annotations

import copy


class FakeLLMClient:
    """
    模拟 LLM。

    固定返回：
    第1次 list_dir
    第2次 read_file
    第3次 write_file
    第4次 execute_command
    第5次最终回答
    """

    def __init__(self):

        # 保存请求历史
        self.requests = []

        # 当前调用次数
        self.index = 0


    def chat(
        self,
        messages,
        tools=None,
    ):

        # ===============================
        # 使用 deepcopy 保存快照
        # ===============================

        self.requests.append(
            copy.deepcopy(messages)
        )


        self.index += 1


        # -------------------------------
        # 第一次：查看目录
        # -------------------------------

        if self.index == 1:

            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_1",
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


        # -------------------------------
        # 第二次：读取文件
        # -------------------------------

        if self.index == 2:

            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_2",
                        "type": "function",
                        "function": {
                            "name": "read_file",
                            "arguments": (
                                '{"path":"notes.txt"}'
                            ),
                        },
                    }
                ],
            }


        # -------------------------------
        # 第三次：写文件
        # -------------------------------

        if self.index == 3:

            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_3",
                        "type": "function",
                        "function": {
                            "name": "write_file",
                            "arguments": (
                                '{"path":"report.txt",'
                                '"content":"Lab03 Report"}'
                            ),
                        },
                    }
                ],
            }


        # -------------------------------
        # 第四次：执行命令
        # -------------------------------

        if self.index == 4:

            return {
                "role": "assistant",
                "content": None,
                "tool_calls": [
                    {
                        "id": "call_4",
                        "type": "function",
                        "function": {
                            "name": "execute_command",
                            "arguments": (
                                '{"command":'
                                '"echo lab03-shell-ok"}'
                            ),
                        },
                    }
                ],
            }


        # -------------------------------
        # 第五次：最终回答
        # -------------------------------

        return {
            "role": "assistant",
            "content": (
                "任务完成，"
                "已经完成目录查看、文件读取、"
                "报告生成和命令执行。"
            ),
            "tool_calls": None,
        }