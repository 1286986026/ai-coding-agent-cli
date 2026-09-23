# Lab03：GLMClient 与 ReAct Agent 实验报告


## 1. 实验目标

本实验主要完成基于大语言模型的 Agent 框架实现。

实验目标包括：

1. 封装 GLMClient，实现与大模型 API 的通信；
2. 实现基础工具系统 BasicTools；
3. 实现 ReAct Agent，使模型能够完成：

   Reasoning → Acting → Observing

   的循环过程；
4. 使用 FakeLLMClient 模拟模型行为，验证 Agent 控制流程；
5. 使用 HTTP Mock 测试 GLMClient 请求、响应解析和异常处理。


---

# 2. 实验环境

操作系统：

Windows

Python：

Python 3.14.7


主要依赖：

- pytest
- httpx


项目结构：
app
├── agent
│ └── react_agent.py
│
├── cli
│ └── lab03_demo.py
│
├── core
│ └── fake_llm.py
│
├── llm
│ └── glm_client.py
│
└── tools
├── file_tool.py
└── basic_tools.py

tests
├── test_file_tool.py
├── test_lab03.py
└── test_glm_client.py


---

# 3. 主要模块实现


## 3.1 GLMClient

GLMClient 负责完成大模型 API 调用。

主要功能：

- 构造 HTTP POST 请求；
- 添加 Authorization Header；
- 发送 messages；
- 解析模型返回结果；
- 处理 HTTP 错误。


普通对话流程：
User Message

  ↓

GLMClient

  ↓

GLM API

  ↓

Assistant Message


---

## 3.2 BasicTools

BasicTools 提供 Agent 可以调用的基础工具。


实现四个工具：

### read_file

读取指定文件内容。


### write_file

创建或修改文件。


### list_dir

查看目录结构。


### execute_command

执行允许的系统命令。


工具调用流程：
Agent

↓

BasicTools

↓

真实执行

↓

Observation


---

## 3.3 ReAct Agent

ReAct Agent 实现：
Reasoning

↓

Acting

↓

Observing

↓

再次 Reasoning


执行流程：
用户任务

↓

Agent

↓

LLM 返回 tool_calls

↓

执行工具

↓

生成 Observation

↓

返回模型

↓

最终答案


---

# 4. FakeLLMClient 测试


由于真实模型输出具有随机性，因此实验中实现 FakeLLMClient。


FakeLLMClient 固定返回：

1. list_dir
2. read_file
3. write_file
4. execute_command
5. final answer


用于验证：

- Agent 控制流程；
- 工具调用顺序；
- Observation 回灌。


同时使用 deepcopy 保存请求快照，避免历史消息被后续修改。


---

# 5. 测试结果


运行：
python -m pytest -q



结果：
21 passed



测试覆盖：

## FileTool

- 文件读取
- 文件写入
- 目录创建
- 目录遍历


## ReAct Agent

- 正常工具调用流程
- tool_call_id 对齐
- unknown tool 处理
- iteration_limit
- deepcopy 快照
- 多轮历史保留


## GLMClient

- HTTP Mock 正常响应
- HTTP 错误处理


---

# 6. AI 协作过程


## 第一轮 Prompt

目标：

实现文件工具系统。

过程：

1. AI 生成 FileTool 代码；
2. 运行 pytest；
3. 根据测试结果修复：
   - 编码问题；
   - 文件异常处理；
   - 目录操作。


---

## 第二轮 Prompt

目标：

实现 ReAct Agent。

过程：

1. AI 生成 Agent 框架；
2. 添加 FakeLLMClient；
3. 增加 pytest 测试；
4. 修复：
   - tool_call_id 对齐；
   - 历史消息保存；
   - iteration_limit。


---

# 7. 实验总结

通过本实验，实现了一个简单的大模型 Agent 框架。

系统能够：

- 调用真实 GLM 模型；
- 调用外部工具；
- 接收工具执行结果；
- 将 Observation 返回模型；
- 完成多轮推理过程。


通过 FakeLLMClient 和 HTTP Mock 测试，提高了系统可靠性。