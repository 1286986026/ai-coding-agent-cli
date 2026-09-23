import httpx

from app.llm.glm_client import (
    GLMClient,
    LLMError,
)


def test_glm_client_success():
    """
    测试正常 GLM 返回解析。
    """

    requests = {}


    def handler(request: httpx.Request):

        # 保存请求信息
        requests["url"] = str(request.url)

        requests["headers"] = dict(
            request.headers
        )

        requests["json"] = (
            request.content.decode()
        )


        return httpx.Response(
            200,
            json={
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "role": "assistant",
                            "content": "hello",
                        },
                    }
                ]
            },
        )


    transport = httpx.MockTransport(
        handler
    )


    client = GLMClient(
        model="glm-5.3",
        api_key="test-key",
        http_client=httpx.Client(
            transport=transport
        ),
    )


    result = client.chat(
        [
            {
                "role": "user",
                "content": "你好",
            }
        ]
    )


    assert (
        result["content"]
        == "hello"
    )


    # URL
    assert (
        "chat/completions"
        in requests["url"]
    )


    # Header
    assert (
        requests["headers"]
        ["authorization"]
        ==
        "Bearer test-key"
    )


    # payload
    assert (
        "glm-5.3"
        in requests["json"]
    )


def test_glm_client_http_error():
    """
    测试 HTTP 错误处理。
    """

    def handler(request):

        return httpx.Response(
            401,
            json={
                "error": "unauthorized"
            },
        )


    transport = httpx.MockTransport(
        handler
    )


    client = GLMClient(
        model="glm-5.3",
        api_key="bad-key",
        http_client=httpx.Client(
            transport=transport
        ),
    )


    try:

        client.chat(
            [
                {
                    "role": "user",
                    "content": "test",
                }
            ]
        )

        assert False


    except LLMError:

        assert True