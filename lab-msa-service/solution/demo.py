"""
MSA 시연 데모 스크립트

3개 서비스를 순차적으로 호출하여 파이프라인 동작을 시각적으로 보여줍니다.
서비스가 이미 실행 중이어야 합니다.

사용법:
  # 터미널 1, 2, 3에서 각각 서비스를 실행
  uv run python solution/intent_service.py   # 포트 8001
  uv run python solution/rag_service.py      # 포트 8002
  uv run python solution/orchestrator.py     # 포트 8000

  # 터미널 4에서 데모 실행
  uv run python solution/demo.py
"""

import httpx


ORCHESTRATOR_URL = "http://localhost:8000"

DEMO_QUESTIONS = [
    "재택근무 규정이 어떻게 되나요?",
    "VPN 접속하려면 어떻게 해야 하나요?",
    "경비 정산은 어디서 하나요?",
    "김민수 사원의 연차 잔여일이 궁금합니다",
]


def print_separator():
    print("\n" + "=" * 70 + "\n")


def demo_single_question(question: str):
    """단일 질문에 대한 파이프라인 실행 과정을 시각화합니다."""
    print(f"질문: {question}")
    print("-" * 50)

    response = httpx.post(
        f"{ORCHESTRATOR_URL}/chat",
        json={"message": question},
        timeout=30.0,
    )

    if response.status_code != 200:
        print(f"  오류: {response.status_code} - {response.text}")
        return

    data = response.json()

    # 파이프라인 단계별 결과 출력
    for i, step in enumerate(data["pipeline"], 1):
        print(f"  [{i}] {step['step']} ({step['service']})")
        if step["step"] == "의도 분류":
            r = step["result"]
            print(f"      도메인: {r['domain']} (신뢰도: {r['confidence']})")
            print(f"      매칭 키워드: {r.get('matched_keywords', [])}")
        elif step["step"] == "RAG 검색":
            r = step["result"]
            print(f"      검색 결과: {r['total_found']}건")
            for doc in r.get("results", []):
                print(f"      - [{doc['id']}] {doc['title']} (점수: {doc['score']})")
        elif step["step"] == "LLM 응답 생성":
            print(f"      모델: OpenAI gpt-4o-mini")

    print()
    print(f"  답변: {data['answer']}")
    print(f"  출처: {', '.join(data['sources'])}")


def demo_health_check():
    """전체 서비스 상태를 확인합니다."""
    print("서비스 상태 확인")
    print("-" * 50)

    response = httpx.get(f"{ORCHESTRATOR_URL}/health", timeout=5.0)
    data = response.json()

    print(f"  오케스트레이터: {data['status']} (포트 8000)")
    for name, info in data.get("downstream", {}).items():
        port = "8001" if name == "intent" else "8002"
        print(f"  {name}: {info['status']} (포트 {port})")


def main():
    print("=" * 70)
    print("  MSA AI 어시스턴트 시연 데모")
    print("  서비스: 의도 분류(8001) + RAG 검색(8002) + 오케스트레이터(8000)")
    print("=" * 70)

    # 1. 헬스 체크
    print()
    try:
        demo_health_check()
    except httpx.ConnectError:
        print("  오케스트레이터에 연결할 수 없습니다.")
        print("  3개 서비스를 먼저 실행하십시오.")
        return

    # 2. 데모 질문 순차 실행
    for question in DEMO_QUESTIONS:
        print_separator()
        try:
            demo_single_question(question)
        except httpx.ConnectError as e:
            print(f"  서비스 연결 실패: {e}")

    print_separator()
    print("시연 완료")


if __name__ == "__main__":
    main()
