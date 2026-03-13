"""
의도 분류 서비스 (Intent Classification Service)

사용자 질문을 분석하여 적절한 도메인(HR, IT, 재무)으로 라우팅합니다.
LO8 서비스 분해도의 '도메인 서비스 계층 > 의도 분류 서비스'에 해당합니다.

포트: 8001
"""

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="의도 분류 서비스", version="0.1.0")

# 도메인별 키워드 사전 (실제 환경에서는 경량 ML 모델로 대체)
DOMAIN_KEYWORDS: dict[str, list[str]] = {
    "hr": [
        "연차", "휴가", "재택", "근무", "출장", "경조사", "복지",
        "교육", "자격증", "건강검진", "학자금", "동호회",
    ],
    "it": [
        "vpn", "VPN", "장비", "노트북", "모니터", "비밀번호", "패스워드",
        "소프트웨어", "설치", "네트워크", "와이파이", "프린터", "계정",
    ],
    "finance": [
        "경비", "정산", "예산", "법인카드", "세금계산서", "세무",
        "급여", "카드", "영수증", "매입", "부가세",
    ],
}


class ClassifyRequest(BaseModel):
    message: str
    context: list[str] = []


class ClassifyResponse(BaseModel):
    domain: str
    confidence: float
    sub_intent: str
    matched_keywords: list[str]


def classify_intent(message: str) -> ClassifyResponse:
    """키워드 매칭 기반 의도 분류 (룰 기반)."""
    message_lower = message.lower()
    scores: dict[str, list[str]] = {}

    for domain, keywords in DOMAIN_KEYWORDS.items():
        matched = [kw for kw in keywords if kw.lower() in message_lower]
        if matched:
            scores[domain] = matched

    if not scores:
        return ClassifyResponse(
            domain="general",
            confidence=0.3,
            sub_intent="unknown",
            matched_keywords=[],
        )

    # 매칭 키워드가 가장 많은 도메인을 선택
    best_domain = max(scores, key=lambda d: len(scores[d]))
    matched_keywords = scores[best_domain]
    confidence = min(0.5 + len(matched_keywords) * 0.15, 0.95)

    # 서브 인텐트 추출 (첫 번째 매칭 키워드 기반)
    sub_intent = matched_keywords[0]

    return ClassifyResponse(
        domain=best_domain,
        confidence=round(confidence, 2),
        sub_intent=sub_intent,
        matched_keywords=matched_keywords,
    )


@app.post("/classify", response_model=ClassifyResponse)
async def classify(request: ClassifyRequest) -> ClassifyResponse:
    """사용자 메시지를 분석하여 도메인과 의도를 분류합니다."""
    return classify_intent(request.message)


@app.get("/health")
async def health():
    """서비스 상태를 확인합니다."""
    return {"status": "healthy", "service": "intent-classifier"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
