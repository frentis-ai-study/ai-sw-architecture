"""
Lab 1: OpenAI 기반 MCP 클라이언트 (완성 코드)

MCP 서버의 도구 목록을 OpenAI function calling 스키마로 변환하고,
AI가 자연어 질문에 맞는 도구를 자동으로 선택/호출하는 브릿지 패턴을 구현합니다.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from dotenv import load_dotenv
from fastmcp import Client  # type: ignore[import-untyped]
from openai import OpenAI

# .env 파일에서 환경변수 로드
load_dotenv()

# MCP 서버 경로 (같은 디렉터리의 server.py)
SERVER_PATH = str(os.path.join(os.path.dirname(__file__), "server.py"))

# OpenAI 모델 설정
MODEL = "gpt-5-mini"  # 비용 효율적 선택. gpt-5나 o4-mini도 사용 가능


def mcp_tools_to_openai_tools(mcp_tools: list) -> list[dict]:
    """MCP 도구 목록을 OpenAI function calling 스키마로 변환합니다.

    MCP 도구의 이름, 설명, 입력 스키마를 OpenAI tools 형식에 맞게 매핑합니다.
    """
    openai_tools = []
    for tool in mcp_tools:
        openai_tools.append({
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            },
        })
    return openai_tools


async def chat_loop():
    """MCP 서버에 연결하고 대화형 루프를 실행합니다."""

    # OpenAI 클라이언트 초기화
    openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

    print("=" * 60)
    print("  HR AI 어시스턴트 (MCP + OpenAI)")
    print("=" * 60)
    print("MCP 서버에 연결 중...")

    # MCP 서버에 연결 (로컬 Python 스크립트로 실행)
    async with Client(SERVER_PATH) as mcp_client:
        # MCP 서버에서 사용 가능한 도구 목록을 가져옵니다
        mcp_tools = await mcp_client.list_tools()
        openai_tools = mcp_tools_to_openai_tools(mcp_tools)

        print(f"연결 완료! 사용 가능한 도구 {len(mcp_tools)}개:")
        for tool in mcp_tools:
            desc_first_line = (tool.description or "").split("\n")[0]
            print(f"  - {tool.name}: {desc_first_line}")
        print()
        print("질문을 입력하세요 (종료: quit)")
        print("-" * 60)

        # 대화 기록을 유지합니다
        messages: list[Any] = [
            {
                "role": "system",
                "content": (
                    "당신은 사내 HR 어시스턴트입니다. "
                    "직원의 연차, 사내 규정, 조직도에 대한 질문에 답변합니다. "
                    "제공된 도구를 활용하여 정확한 정보를 조회한 후 답변하십시오. "
                    "답변은 한국어로 친절하게 작성합니다."
                ),
            }
        ]

        while True:
            # 사용자 입력 받기
            try:
                user_input = input("\n질문> ").strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input or user_input.lower() in ("quit", "exit", "q"):
                print("종료합니다.")
                break

            # 사용자 메시지를 대화 기록에 추가
            messages.append({"role": "user", "content": user_input})

            # OpenAI에 도구 목록과 함께 요청
            response = openai_client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=openai_tools,
            )

            assistant_message = response.choices[0].message

            # 도구 호출이 필요한 경우 반복 처리
            while assistant_message.tool_calls:
                # assistant 메시지를 대화 기록에 추가
                messages.append(assistant_message)

                # 각 도구 호출을 MCP 서버에서 실행
                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    tool_args = json.loads(tool_call.function.arguments)

                    print(f"  [도구 호출] {tool_name}({tool_args})")

                    # MCP 서버의 도구를 호출하고 결과를 받습니다
                    result = await mcp_client.call_tool(tool_name, tool_args)

                    # 도구 실행 결과를 대화 기록에 추가
                    result_text = (
                        result.data
                        if isinstance(result.data, str)
                        else json.dumps(result.data, ensure_ascii=False)
                    )
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "content": result_text,
                    })

                # 도구 결과를 포함하여 다시 OpenAI에 요청
                response = openai_client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    tools=openai_tools,
                )
                assistant_message = response.choices[0].message

            # 최종 응답 출력
            messages.append(assistant_message)
            print(f"\n답변> {assistant_message.content}")


if __name__ == "__main__":
    asyncio.run(chat_loop())
