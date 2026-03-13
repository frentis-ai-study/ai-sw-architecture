"""
MSA 서비스 일괄 실행

3개 마이크로서비스를 하나의 프로세스에서 동시에 실행합니다.

실행:
  uv run python solution/run_all.py
"""

import threading
import time

import uvicorn

from intent_service import app as intent_app
from rag_service import app as rag_app
from orchestrator import app as orchestrator_app


SERVICE_CONFIGS = [
    {"name": "의도 분류 서비스", "app": intent_app, "port": 8001},
    {"name": "RAG 검색 서비스", "app": rag_app, "port": 8002},
    {"name": "오케스트레이터", "app": orchestrator_app, "port": 8000},
]


def start_service(config: dict):
    """개별 서비스를 uvicorn으로 실행합니다."""
    uvicorn.run(
        config["app"],
        host="0.0.0.0",
        port=config["port"],
        log_level="warning",
    )


if __name__ == "__main__":
    print("=" * 60)
    print("  MSA AI 어시스턴트 — 전체 서비스 시작")
    print("=" * 60)
    print()

    threads = []
    for cfg in SERVICE_CONFIGS:
        t = threading.Thread(target=start_service, args=(cfg,), daemon=True)
        t.start()
        threads.append(t)
        print(f"  [{cfg['name']}] http://localhost:{cfg['port']}")

    print()
    print("  모든 서비스가 실행 중입니다. Ctrl+C로 종료하십시오.")
    print("  Swagger UI:")
    print("    의도 분류:     http://localhost:8001/docs")
    print("    RAG 검색:      http://localhost:8002/docs")
    print("    오케스트레이터: http://localhost:8000/docs")
    print("=" * 60)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n서비스를 종료합니다.")
