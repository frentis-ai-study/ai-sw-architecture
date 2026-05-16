"""
Lab 1: Ollama 기반 MCP 클라이언트 (사내·로컬 전용)

OpenAI 대신 로컬 Ollama 서버(gemma4:e4b)에 붙어 동작하는 클라이언트.
사외로 데이터를 보내지 않으므로 민감 정보(HR, 인사) 처리에 적합합니다.

전제 조건:
  1) `ollama serve` 가 떠 있고 (기본 http://localhost:11434)
  2) `ollama pull gemma4:e4b` 가 완료되어 있어야 합니다.

참고 (context7):
  - Ollama Python SDK는 OpenAI 호환 tool 스키마를 그대로 받습니다.
  - response.message.tool_calls[i].function.arguments 는 이미 dict 입니다
    (OpenAI와 달리 json.loads 불필요).
  - tool 결과 메시지는 `tool_call_id` 가 아니라 `tool_name` 키를 사용합니다.
"""

from __future__ import annotations

import asyncio
import json
import os
from typing import Any

from fastmcp import Client  # type: ignore[import-untyped]
from ollama import AsyncClient
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.rule import Rule
from rich.table import Table

# Rich 콘솔
console = Console()

# MCP 서버 경로 (같은 디렉터리의 server.py)
SERVER_PATH = str(os.path.join(os.path.dirname(__file__), "server.py"))

# Ollama 설정 (환경변수로 오버라이드 가능)
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
MODEL = os.getenv("OLLAMA_MODEL", "gemma4:e4b")


def mcp_tools_to_ollama_tools(mcp_tools: list) -> list[dict]:
    """MCP 도구 목록을 Ollama(=OpenAI 호환) tool 스키마로 변환합니다."""
    return [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema,
            },
        }
        for tool in mcp_tools
    ]


def extract_result_text(result) -> str:
    """MCP CallToolResult에서 LLM에 전달할 문자열을 안전하게 추출합니다.

    result.data 는 list[dict] 반환 시 pydantic Root 인스턴스가 섞여
    json 직렬화가 깨질 수 있으므로, MCP 표준 응답인 content 블록을 우선 사용합니다.
    """
    if result.content:
        return "\n".join(
            block.text for block in result.content if hasattr(block, "text")
        )
    return json.dumps(
        getattr(result, "structured_content", None) or {},
        ensure_ascii=False,
        default=str,
    )


async def chat_loop() -> None:
    """MCP 서버에 연결하고 Ollama 모델과 대화형 루프를 실행합니다."""

    ollama_client = AsyncClient(host=OLLAMA_HOST)

    console.print(Panel(
        f"HR AI 어시스턴트 (MCP + Ollama)\n[dim]model: {MODEL}  |  host: {OLLAMA_HOST}[/dim]",
        style="bold bright_white",
        border_style="magenta",
    ))
    console.print("[dim]MCP 서버에 연결 중...[/dim]")

    async with Client(SERVER_PATH) as mcp_client:
        mcp_tools = await mcp_client.list_tools()
        ollama_tools = mcp_tools_to_ollama_tools(mcp_tools)

        console.print(f"[green]연결 완료![/green] 사용 가능한 도구 {len(mcp_tools)}개:")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("도구명", style="cyan")
        table.add_column("설명")
        for tool in mcp_tools:
            desc_first_line = (tool.description or "").split("\n")[0]
            table.add_row(tool.name, desc_first_line)
        console.print(table)
        console.print()
        console.print(
            "[dim]예시: '김민수의 남은 연차가 며칠인가요?', "
            "'재택근무 규정을 알려주세요'[/dim]"
        )
        console.print(Rule(style="dim"))

        messages: list[Any] = [
            {
                "role": "system",
                "content": (
                    "당신은 사내 HR 어시스턴트입니다. "
                    "직원의 연차, 사내 규정, 조직도에 대한 질문에 답변합니다. "
                    "제공된 도구를 활용하여 정확한 정보를 조회한 후 답변하십시오. "
                    "이름만 알고 사번을 모르면 먼저 find_employee 도구로 사번을 찾으십시오. "
                    "답변은 한국어로 친절하게 작성합니다."
                ),
            }
        ]

        while True:
            try:
                user_input = Prompt.ask(
                    "\n[bold bright_blue]질문[/bold bright_blue]"
                ).strip()
            except (EOFError, KeyboardInterrupt):
                break

            if not user_input or user_input.lower() in ("quit", "exit", "q"):
                console.print("[dim]종료합니다.[/dim]")
                break

            messages.append({"role": "user", "content": user_input})

            response = await ollama_client.chat(
                model=MODEL,
                messages=messages,
                tools=ollama_tools,
            )
            assistant_message = response.message

            # 도구 호출이 필요한 경우 반복 처리
            while assistant_message.tool_calls:
                # assistant 메시지를 대화 기록에 추가 (pydantic Message는 그대로 append 가능)
                messages.append(assistant_message)

                for tool_call in assistant_message.tool_calls:
                    tool_name = tool_call.function.name
                    # Ollama는 arguments를 이미 dict로 파싱해서 줍니다
                    tool_args = dict(tool_call.function.arguments or {})

                    console.print(
                        f"  [dim][도구 호출][/dim] "
                        f"[cyan]{tool_name}[/cyan]({tool_args})"
                    )

                    result = await mcp_client.call_tool(tool_name, tool_args)
                    result_text = extract_result_text(result)

                    messages.append({
                        "role": "tool",
                        "tool_name": tool_name,
                        "content": result_text,
                    })

                response = await ollama_client.chat(
                    model=MODEL,
                    messages=messages,
                    tools=ollama_tools,
                )
                assistant_message = response.message

            messages.append(assistant_message)
            console.print(Panel(
                assistant_message.content or "(응답 없음)",
                title="답변",
                border_style="green",
                padding=(1, 2),
            ))


if __name__ == "__main__":
    asyncio.run(chat_loop())
