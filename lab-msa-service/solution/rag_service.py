"""
RAG 검색 서비스 (Retrieval-Augmented Generation Service)

도메인별 지식 베이스에서 관련 문서를 검색하여 반환합니다.
LO8 서비스 분해도의 'AI 인프라 계층 > RAG 서비스'에 해당합니다.

실제 환경에서는 벡터 DB(ChromaDB, Pinecone 등)와 임베딩 모델을 사용하지만,
이 시연에서는 키워드 기반 검색으로 RAG의 구조를 보여줍니다.

포트: 8002
"""

import json
from pathlib import Path

from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI(title="RAG 검색 서비스", version="0.1.0")

DATA_DIR = Path(__file__).parent.parent / "data"

# 도메인별 지식 베이스 매핑
DOMAIN_FILES: dict[str, str] = {
    "hr": "hr_knowledge.json",
    "it": "it_knowledge.json",
    "finance": "finance_knowledge.json",
}


def load_knowledge(domain: str) -> list[dict]:
    """도메인별 지식 베이스를 로드합니다."""
    filename = DOMAIN_FILES.get(domain)
    if not filename:
        return []
    file_path = DATA_DIR / filename
    if not file_path.exists():
        return []
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


class SearchRequest(BaseModel):
    query: str
    domain: str
    top_k: int = 3


class SearchResult(BaseModel):
    id: str
    title: str
    content: str
    score: float
    source: str


class SearchResponse(BaseModel):
    results: list[SearchResult]
    domain: str
    total_found: int


def keyword_search(query: str, documents: list[dict], top_k: int) -> list[SearchResult]:
    """키워드 매칭 기반 검색 (실제 환경에서는 벡터 유사도 검색으로 대체)."""
    scored: list[tuple[float, dict]] = []
    query_terms = query.lower().split()

    for doc in documents:
        searchable = f"{doc['title']} {doc['category']} {doc['content']}".lower()
        # 매칭 키워드 수와 위치 기반 점수 계산
        match_count = sum(1 for term in query_terms if term in searchable)
        if match_count > 0:
            score = round(match_count / len(query_terms), 2)
            scored.append((score, doc))

    # 점수 내림차순 정렬 후 top_k 반환
    scored.sort(key=lambda x: x[0], reverse=True)
    return [
        SearchResult(
            id=doc["id"],
            title=doc["title"],
            content=doc["content"],
            score=score,
            source=f"{doc['category']} > {doc['title']}",
        )
        for score, doc in scored[:top_k]
    ]


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """도메인별 지식 베이스에서 관련 문서를 검색합니다."""
    documents = load_knowledge(request.domain)

    if not documents:
        return SearchResponse(results=[], domain=request.domain, total_found=0)

    results = keyword_search(request.query, documents, request.top_k)
    return SearchResponse(
        results=results,
        domain=request.domain,
        total_found=len(results),
    )


@app.get("/domains")
async def list_domains():
    """사용 가능한 도메인 목록을 반환합니다."""
    return {
        "domains": list(DOMAIN_FILES.keys()),
        "total_documents": {
            domain: len(load_knowledge(domain)) for domain in DOMAIN_FILES
        },
    }


@app.get("/health")
async def health():
    """서비스 상태를 확인합니다."""
    return {"status": "healthy", "service": "rag-search"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8002)
