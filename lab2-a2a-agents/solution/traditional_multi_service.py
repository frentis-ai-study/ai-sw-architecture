"""
전통적 REST API 기반 멀티서비스 아키텍처 심의 시스템
===================================================
A2A 프로토콜 없이, Flask REST API로 동일한 아키텍처 심의를 구현합니다.
A2A 방식과 비교하여 어떤 차이가 있는지 확인할 수 있습니다.

주요 차이점:
  - 에이전트 자기 설명(AgentCard) 없음: 호출자가 각 서비스의 API 스펙을 사전에 알아야 합니다.
  - 표준 메시지 형식 없음: 서비스마다 요청/응답 JSON 구조가 다릅니다.
  - 에이전트 탐색(Discovery) 불가: URL과 엔드포인트를 하드코딩해야 합니다.
  - 대화 상태 관리 없음: 매 요청이 독립적이며, 멀티턴 상호작용이 어렵습니다.

실행 (서버 모드):
  uv run python solution/traditional_multi_service.py --serve

실행 (클라이언트 모드 - 서버가 실행 중이어야 함):
  uv run python solution/traditional_multi_service.py --client

실행 (단일 프로세스 데모 - 서버 없이):
  uv run python solution/traditional_multi_service.py
"""

import argparse
import json
import sys
import threading
import time
from pathlib import Path

import requests
from flask import Flask, jsonify, request


# ============================================================
# 터미널 출력 헬퍼
# ============================================================
class Colors:
    HEADER = "\033[95m"
    BLUE = "\033[94m"
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    END = "\033[0m"


# ============================================================
# 전통적 REST 서비스 정의
# ============================================================
# 문제 1: 각 서비스마다 고유한 API 엔드포인트와 요청/응답 형식을 갖습니다.
#          호출자는 모든 서비스의 스펙을 사전에 파악하고 하드코딩해야 합니다.
# ============================================================

def create_security_app():
    """보안 리뷰 REST 서비스 (Flask 앱)"""
    app = Flask("security-service")

    # 문제 2: 엔드포인트 경로가 서비스마다 다릅니다.
    #          A2A에서는 모든 에이전트가 동일한 /message 엔드포인트를 사용합니다.
    @app.route("/api/v1/security/review", methods=["POST"])
    def review():
        data = request.get_json()
        # 문제 3: 요청 형식이 서비스마다 다릅니다.
        #          여기서는 {"proposal": {...}}를 기대하지만, 다른 서비스는 다른 형식을 쓸 수 있습니다.
        proposal = data.get("proposal", {})
        findings = _analyze_security(proposal)
        high_count = sum(1 for f in findings if f["severity"] == "높음")
        return jsonify({
            "service": "security-review",  # "agent" 대신 "service" 사용
            "status": "rejected" if high_count >= 2 else "conditional",  # 영문 상태
            "issues": findings,  # "findings" 대신 "issues" 사용
            "issue_count": len(findings),
        })

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    return app


def create_performance_app():
    """성능 리뷰 REST 서비스 (Flask 앱)"""
    app = Flask("performance-service")

    # 문제 2: 각 서비스가 다른 엔드포인트 경로를 사용합니다.
    @app.route("/api/v1/performance/analyze", methods=["POST"])
    def analyze():
        data = request.get_json()
        proposal = data.get("system_spec", {})  # 같은 데이터인데 키 이름이 다릅니다
        findings = _analyze_performance(proposal)
        return jsonify({
            "analyzer": "performance",  # 또 다른 키 이름
            "result": "pass_with_conditions",  # 또 다른 상태 형식
            "findings": findings,
            "score": 72,  # 서비스마다 고유한 메트릭
        })

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    return app


def create_cost_app():
    """비용 리뷰 REST 서비스 (Flask 앱)"""
    app = Flask("cost-service")

    @app.route("/api/v1/cost/estimate", methods=["POST"])
    def estimate():
        data = request.get_json()
        proposal = data.get("project_data", {})  # 또 다른 키 이름
        findings = _analyze_cost(proposal)
        return jsonify({
            "department": "cost-review",
            "decision": "approved_with_conditions",
            "analysis": findings,  # "findings" 대신 "analysis"
            "total_risk_score": 65,
        })

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    return app


def create_ops_app():
    """운영 리뷰 REST 서비스 (Flask 앱)"""
    app = Flask("ops-service")

    @app.route("/api/v1/ops/readiness", methods=["POST"])
    def readiness():
        data = request.get_json()
        proposal = data.get("migration_plan", {})  # 또 다른 키 이름
        findings = _analyze_ops(proposal)
        high_count = sum(1 for f in findings if f["level"] == "critical")
        return jsonify({
            "team": "operations",
            "readiness": "not_ready" if high_count >= 2 else "partially_ready",
            "gaps": findings,  # "findings" 대신 "gaps"
            "critical_count": high_count,
        })

    @app.route("/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok"})

    return app


# ============================================================
# 분석 로직 (A2A 버전과 동일한 내용, 다른 데이터 형식)
# ============================================================

def _analyze_security(proposal):
    """보안 분석 — REST 버전은 반환 형식이 A2A 버전과 다릅니다."""
    findings = []
    proposed = proposal.get("proposed_changes", {})
    current = proposal.get("current_system", {})

    if proposed.get("target_cloud") == "AWS":
        findings.append({
            "type": "data_sovereignty",
            "severity": "높음",
            "description": "퍼블릭 클라우드 전환 시 개인정보보호법 및 데이터 3법에 따른 "
            "국내 데이터 저장 의무 검토가 필요합니다.",
            "action": "데이터 분류 체계를 수립하고, 민감 데이터는 국내 리전에만 저장하십시오.",
        })

    if "Oracle" in current.get("stack", ""):
        findings.append({
            "type": "encryption",
            "severity": "높음",
            "description": "Oracle DB에서 Aurora PostgreSQL 전환 시 TDE 설정이 유실될 수 있습니다.",
            "action": "AWS KMS 기반 암호화 키 관리를 도입하십시오.",
        })

    if "EKS" in proposed.get("architecture", ""):
        findings.append({
            "type": "access_control",
            "severity": "중간",
            "description": "EKS 클러스터의 RBAC 설정이 제안서에 명시되어 있지 않습니다.",
            "action": "Pod Security Standards Restricted 프로파일을 적용하십시오.",
        })

    findings.append({
        "type": "compliance",
        "severity": "중간",
        "description": "ISMS-P 인증 범위 변경 신고가 필요합니다.",
        "action": "전환 착수 전 ISMS-P 인증 기관에 범위 변경을 사전 협의하십시오.",
    })
    return findings


def _analyze_performance(proposal):
    """성능 분석"""
    findings = []
    proposed = proposal.get("proposed_changes", {})

    if "EKS" in proposed.get("architecture", ""):
        findings.append({
            "area": "auto_scaling",
            "risk": "low",
            "note": "EKS HPA/VPA를 통한 자동 스케일링이 가능합니다.",
        })

    if "Aurora" in proposed.get("database", ""):
        findings.append({
            "area": "database_migration",
            "risk": "high",
            "note": "Oracle에서 PostgreSQL 전환 시 20% 이상 쿼리 성능 저하 가능성이 있습니다.",
        })

    findings.append({
        "area": "network_latency",
        "risk": "medium",
        "note": "마이크로서비스 전환 시 서비스 간 네트워크 호출이 증가합니다.",
    })
    return findings


def _analyze_cost(proposal):
    """비용 분석"""
    findings = []
    proposed = proposal.get("proposed_changes", {})

    findings.append({
        "item": "tco",
        "impact": "높음",
        "detail": "클라우드 3년 TCO는 약 21억원으로 온프레미스(15억원) 대비 40% 높습니다.",
    })

    if "Oracle" in proposal.get("current_system", {}).get("stack", ""):
        findings.append({
            "item": "license_savings",
            "impact": "낮음",
            "detail": "Oracle 라이선스 해지 시 연간 약 3억원 절감이 가능합니다.",
        })

    findings.append({
        "item": "contingency",
        "impact": "중간",
        "detail": "예비비(전체의 15%)가 미책정되어 있습니다.",
    })
    return findings


def _analyze_ops(proposal):
    """운영 분석"""
    findings = []

    findings.append({
        "area": "team_capability",
        "level": "critical",
        "description": "현재 운영팀은 Kubernetes/EKS 운영 경험이 부재합니다.",
    })

    findings.append({
        "area": "monitoring",
        "level": "warning",
        "description": "마이크로서비스 전환 시 모니터링 복잡도가 10배 이상 증가합니다.",
    })

    findings.append({
        "area": "staffing",
        "level": "critical",
        "description": "운영 인력 5명에서 2명 감축은 비현실적입니다.",
    })
    return findings


# ============================================================
# REST 서비스 설정 (하드코딩)
# ============================================================
# 문제 4: 서비스 정보를 하드코딩해야 합니다.
#          A2A에서는 AgentCard를 통해 에이전트가 자신의 능력을 설명합니다.
# ============================================================

REST_SERVICES = [
    {
        "name": "보안 리뷰 서비스",
        "url": "http://localhost:6001/api/v1/security/review",
        "method": "POST",
        "request_key": "proposal",  # 각 서비스마다 다른 요청 키
    },
    {
        "name": "성능 리뷰 서비스",
        "url": "http://localhost:6002/api/v1/performance/analyze",
        "method": "POST",
        "request_key": "system_spec",
    },
    {
        "name": "비용 리뷰 서비스",
        "url": "http://localhost:6003/api/v1/cost/estimate",
        "method": "POST",
        "request_key": "project_data",
    },
    {
        "name": "운영 리뷰 서비스",
        "url": "http://localhost:6004/api/v1/ops/readiness",
        "method": "POST",
        "request_key": "migration_plan",
    },
]


# ============================================================
# 오케스트레이터 (REST 버전)
# ============================================================
# 문제 5: 각 서비스의 응답 형식이 달라서, 응답 파싱 코드를 서비스마다 별도로 작성해야 합니다.
# ============================================================

def normalize_response(service_name, raw_response):
    """
    각 서비스의 서로 다른 응답 형식을 공통 형식으로 변환합니다.

    문제 6: A2A에서는 이 변환이 불필요합니다.
    모든 에이전트가 동일한 Message 형식으로 통신하기 때문입니다.
    """
    if "security" in service_name:
        return {
            "agent": "보안 리뷰 에이전트",
            "verdict": "반려" if raw_response.get("status") == "rejected" else "조건부 승인",
            "findings": [
                {
                    "category": f["type"],
                    "severity": f["severity"],
                    "finding": f["description"],
                    "recommendation": f["action"],
                }
                for f in raw_response.get("issues", [])
            ],
        }
    elif "성능" in service_name:
        risk_map = {"high": "높음", "medium": "중간", "low": "낮음"}
        return {
            "agent": "성능 리뷰 에이전트",
            "verdict": "조건부 승인",
            "findings": [
                {
                    "category": f["area"],
                    "severity": risk_map.get(f["risk"], "중간"),
                    "finding": f["note"],
                    "recommendation": "",
                }
                for f in raw_response.get("findings", [])
            ],
        }
    elif "비용" in service_name:
        return {
            "agent": "비용 리뷰 에이전트",
            "verdict": "조건부 승인",
            "findings": [
                {
                    "category": f["item"],
                    "severity": f["impact"],
                    "finding": f["detail"],
                    "recommendation": "",
                }
                for f in raw_response.get("analysis", [])
            ],
        }
    elif "운영" in service_name:
        level_map = {"critical": "높음", "warning": "중간", "info": "낮음"}
        return {
            "agent": "운영 리뷰 에이전트",
            "verdict": "반려" if raw_response.get("readiness") == "not_ready" else "조건부 승인",
            "findings": [
                {
                    "category": f["area"],
                    "severity": level_map.get(f["level"], "중간"),
                    "finding": f["description"],
                    "recommendation": "",
                }
                for f in raw_response.get("gaps", [])
            ],
        }
    return {"agent": service_name, "verdict": "알 수 없음", "findings": []}


def load_proposal():
    """설계 제안서를 로드합니다."""
    proposal_path = Path(__file__).parent.parent / "data" / "design_proposal.json"
    with open(proposal_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ============================================================
# 단일 프로세스 데모 (서버 없이 비교)
# ============================================================

def run_demo_without_server():
    """
    서버 없이 직접 함수를 호출하여 REST 방식의 문제점을 보여줍니다.
    실제 HTTP 통신은 하지 않지만, 코드 구조의 차이를 명확히 보여줍니다.
    """
    proposal = load_proposal()

    print()
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 64}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}  전통적 REST API 방식 vs A2A 프로토콜 비교 데모{Colors.END}")
    print(f"{Colors.BOLD}{Colors.HEADER}{'=' * 64}{Colors.END}")

    # ---- REST 방식의 문제점 시연 ----
    print()
    print(f"{Colors.RED}{Colors.BOLD}{'=' * 64}{Colors.END}")
    print(f"{Colors.RED}{Colors.BOLD}  [문제점 시연] 전통적 REST API 방식{Colors.END}")
    print(f"{Colors.RED}{Colors.BOLD}{'=' * 64}{Colors.END}")

    print(f"""
{Colors.YELLOW}문제 1: 서비스마다 다른 API 엔드포인트{Colors.END}
  보안: POST /api/v1/security/review
  성능: POST /api/v1/performance/analyze
  비용: POST /api/v1/cost/estimate
  운영: POST /api/v1/ops/readiness

{Colors.YELLOW}문제 2: 서비스마다 다른 요청 형식{Colors.END}
  보안: {{"proposal": {{...}}}}
  성능: {{"system_spec": {{...}}}}
  비용: {{"project_data": {{...}}}}
  운영: {{"migration_plan": {{...}}}}
""")

    # 각 서비스 직접 호출
    print(f"{Colors.CYAN}{Colors.BOLD}--- 각 서비스 호출 결과 ---{Colors.END}")
    raw_responses = {
        "보안": _analyze_security(proposal),
        "성능": _analyze_performance(proposal),
        "비용": _analyze_cost(proposal),
        "운영": _analyze_ops(proposal),
    }

    for name, findings in raw_responses.items():
        print(f"\n  {Colors.BOLD}[{name}]{Colors.END} 응답 필드 구조:")
        if findings:
            fields = list(findings[0].keys())
            print(f"    필드: {fields}")

    print(f"""
{Colors.YELLOW}문제 3: 서비스마다 다른 응답 형식{Colors.END}
  보안: type, severity, description, action
  성능: area, risk, note
  비용: item, impact, detail
  운영: area, level, description

{Colors.YELLOW}문제 4: 응답 통합을 위해 서비스별 변환 코드가 필요합니다.{Colors.END}
  normalize_response() 함수에서 서비스별 분기 처리 필요
  새 서비스 추가 시 변환 코드도 함께 수정해야 합니다.
""")

    # ---- A2A 방식의 장점 시연 ----
    print(f"{Colors.GREEN}{Colors.BOLD}{'=' * 64}{Colors.END}")
    print(f"{Colors.GREEN}{Colors.BOLD}  [해결] A2A 프로토콜 방식{Colors.END}")
    print(f"{Colors.GREEN}{Colors.BOLD}{'=' * 64}{Colors.END}")

    print(f"""
{Colors.GREEN}해결 1: 모든 에이전트가 동일한 엔드포인트{Colors.END}
  보안: POST http://localhost:5001  (A2A /message)
  성능: POST http://localhost:5002  (A2A /message)
  비용: POST http://localhost:5003  (A2A /message)
  운영: POST http://localhost:5004  (A2A /message)

{Colors.GREEN}해결 2: 표준화된 메시지 형식{Colors.END}
  모든 에이전트: Message(role=USER, content=TextContent(text=...))

{Colors.GREEN}해결 3: AgentCard를 통한 자기 설명{Colors.END}
  각 에이전트가 자신의 이름, 능력, URL을 AgentCard로 공개합니다.
  오케스트레이터는 AgentCard만 보고 어떤 에이전트가 있는지 파악할 수 있습니다.

{Colors.GREEN}해결 4: 응답 형식도 표준화{Colors.END}
  모든 에이전트: Message(role=AGENT, content=TextContent(text=...))
  변환 코드 불필요, 새 에이전트 추가 시 코드 변경 최소화
""")

    # ---- 코드 양 비교 ----
    print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 64}{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}  코드 복잡도 비교{Colors.END}")
    print(f"{Colors.CYAN}{Colors.BOLD}{'=' * 64}{Colors.END}")

    print(f"""
  {'항목':<30} {'REST API':<20} {'A2A 프로토콜':<20}
  {'─' * 70}
  {'엔드포인트 정의':<30} {'서비스마다 개별':<20} {'자동 (/message)':<20}
  {'요청 형식':<30} {'서비스마다 다름':<20} {'Message (표준)':<20}
  {'응답 형식':<30} {'서비스마다 다름':<20} {'Message (표준)':<20}
  {'응답 변환 코드':<30} {'필요 (서비스별)':<20} {'불필요':<20}
  {'에이전트 탐색':<30} {'수동 (하드코딩)':<20} {'AgentCard 기반':<20}
  {'새 에이전트 추가':<30} {'코드 변경 필요':<20} {'설정만 추가':<20}
  {'대화 상태 관리':<30} {'직접 구현':<20} {'프로토콜 내장':<20}
  {'에이전트 간 통신':<30} {'개별 API 호출':<20} {'표준 프로토콜':<20}
""")

    print(f"{Colors.BOLD}  결론: A2A 프로토콜은 에이전트 간 통신을 표준화하여{Colors.END}")
    print(f"{Colors.BOLD}  통합 복잡도를 크게 줄이고, 확장성을 높입니다.{Colors.END}")
    print()


# ============================================================
# HTTP 서버 모드
# ============================================================

def run_servers():
    """4개의 REST 서비스를 별도 스레드에서 실행합니다."""
    apps = [
        (create_security_app(), 6001),
        (create_performance_app(), 6002),
        (create_cost_app(), 6003),
        (create_ops_app(), 6004),
    ]

    print(f"{Colors.BOLD}{'=' * 64}{Colors.END}")
    print(f"{Colors.BOLD}  전통적 REST 서비스 시작 (포트 6001 ~ 6004){Colors.END}")
    print(f"{Colors.BOLD}{'=' * 64}{Colors.END}")

    for app, port in apps:
        t = threading.Thread(
            target=lambda a, p: a.run(host="0.0.0.0", port=p, debug=False),
            args=(app, port),
            daemon=True,
        )
        t.start()
        print(f"  [{app.name}] http://localhost:{port}")

    print()
    print(f"  모든 서비스가 실행 중입니다. Ctrl+C로 종료하십시오.")
    print(f"{Colors.BOLD}{'=' * 64}{Colors.END}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n서비스를 종료합니다.")


def run_client():
    """REST 서비스에 요청을 보내고 결과를 종합합니다."""
    proposal = load_proposal()

    print(f"\n{Colors.BOLD}{'=' * 64}{Colors.END}")
    print(f"{Colors.BOLD}  전통적 REST 오케스트레이터 실행{Colors.END}")
    print(f"{Colors.BOLD}{'=' * 64}{Colors.END}")

    reviews = []
    for svc in REST_SERVICES:
        print(f"\n  {Colors.BOLD}{svc['name']}{Colors.END}에 요청을 전송합니다...")
        print(f"    URL: {svc['url']}")
        print(f"    요청 키: {svc['request_key']}")

        try:
            start = time.time()
            resp = requests.post(
                svc["url"],
                json={svc["request_key"]: proposal},
                timeout=5,
            )
            elapsed = time.time() - start
            raw = resp.json()

            # 문제: 서비스마다 다른 응답을 수동으로 변환해야 합니다
            normalized = normalize_response(svc["name"], raw)
            reviews.append(normalized)

            print(f"    {Colors.GREEN}응답 수신 ({elapsed:.1f}초) "
                  f"- 판정: {normalized['verdict']}{Colors.END}")
        except Exception as e:
            print(f"    {Colors.RED}연결 실패: {e}{Colors.END}")

    if reviews:
        print(f"\n{Colors.BOLD}종합 결과:{Colors.END}")
        for r in reviews:
            print(f"  {r['agent']}: {r['verdict']} ({len(r['findings'])}건)")

    print()


# ============================================================
# 메인
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="전통적 REST API 방식의 멀티서비스 아키텍처 심의 (A2A 비교용)"
    )
    parser.add_argument("--serve", action="store_true", help="REST 서비스 서버를 시작합니다")
    parser.add_argument("--client", action="store_true", help="REST 오케스트레이터를 실행합니다")
    args = parser.parse_args()

    if args.serve:
        run_servers()
    elif args.client:
        run_client()
    else:
        # 기본: 단일 프로세스 데모 (서버 없이 비교)
        run_demo_without_server()


if __name__ == "__main__":
    main()
