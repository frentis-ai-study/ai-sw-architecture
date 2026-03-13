# Lab 2: A2A 프로토콜 기반 아키텍처 심의위원회 (ARB)

## 실습 목표

단일 AI 에이전트는 하나의 관점에 편향된 분석을 제공합니다.
실제 아키텍처 심의에서는 보안, 성능, 비용, 운영 등 **서로 다른 우선순위를 가진 전문가들이 의견을 교환**하며 균형 잡힌 결론을 도출합니다.

이 실습에서는 A2A(Agent-to-Agent) 프로토콜을 사용하여 4명의 전문가 에이전트가 설계 제안서를 리뷰하고, 오케스트레이터가 **상충하는 의견을 종합**하여 최종 심의 결과를 도출하는 시스템을 구현합니다.

### 학습 포인트

- A2A 프로토콜의 핵심 개념: AgentCard, Task, Message, Artifact
- 멀티에이전트 시스템에서의 관점 충돌과 해결
- 오케스트레이터 패턴을 통한 에이전트 협업
- 전통적 REST API 방식과 A2A 프로토콜의 구조적 차이

---

## A2A 프로토콜 핵심 개념

A2A(Agent-to-Agent)는 Google이 2024년 4월에 공개한 에이전트 간 통신 표준 프로토콜입니다.
에이전트들이 서로를 발견하고, 메시지를 주고받으며, 작업을 위임할 수 있게 합니다.

### 4가지 핵심 구성 요소

| 구성 요소 | 역할 | 이 실습에서의 적용 |
|-----------|------|-------------------|
| **AgentCard** | 에이전트가 자신의 이름, 능력, URL을 공개하는 메타데이터. 다른 에이전트가 이를 읽고 적절한 에이전트를 찾을 수 있습니다. | 보안/성능/비용/운영 에이전트가 각자의 AgentCard를 등록합니다. 오케스트레이터는 AgentCard를 통해 에이전트를 탐색합니다. |
| **Message** | 에이전트 간 통신의 기본 단위. 역할(USER/AGENT)과 내용(TextContent 등)으로 구성됩니다. 모든 에이전트가 **동일한 형식**으로 메시지를 주고받습니다. | 오케스트레이터가 설계안을 Message로 전송하고, 에이전트가 리뷰 결과를 Message로 반환합니다. |
| **Task** | 에이전트에게 요청한 작업의 상태를 추적합니다. submitted, working, completed, failed 등의 상태를 가집니다. | 각 에이전트에 대한 리뷰 요청이 하나의 Task입니다. |
| **Artifact** | Task 수행 결과물. 텍스트, 이미지, 파일 등 다양한 형태의 산출물을 포함할 수 있습니다. | 각 에이전트의 리뷰 보고서(JSON)가 Artifact입니다. |

### A2A 통신 흐름

```
1. 에이전트 등록
   SecurityAgent → AgentCard(name="보안 리뷰", url=":5001", skills=["보안 분석"])
   PerformanceAgent → AgentCard(name="성능 리뷰", url=":5002", skills=["성능 분석"])

2. 에이전트 탐색 (Discovery)
   오케스트레이터가 AgentCard를 읽어 어떤 에이전트가 있는지 파악

3. 메시지 교환
   오케스트레이터 → Message(role=USER, content="설계안 JSON")
   에이전트     → Message(role=AGENT, content="리뷰 결과 JSON")

4. 결과 종합
   오케스트레이터가 모든 에이전트의 응답을 취합하여 최종 보고서 생성
```

---

## 전통적 REST API vs A2A 프로토콜 비교

전통적 REST API로 동일한 멀티에이전트 시스템을 구현하면 어떤 문제가 발생하는지 비교합니다.
`solution/traditional_multi_service.py`에서 실제 코드를 확인할 수 있습니다.

### 구조 비교

| 항목 | 전통적 REST API | A2A 프로토콜 |
|------|----------------|-------------|
| **엔드포인트** | 서비스마다 개별 정의 (`/api/v1/security/review`, `/api/v1/ops/readiness`) | 모든 에이전트 동일 (`/message`) |
| **요청 형식** | 서비스마다 다름 (`{"proposal": ...}`, `{"system_spec": ...}`) | 표준화된 Message 객체 |
| **응답 형식** | 서비스마다 다름 (`issues`, `findings`, `analysis`, `gaps`) | 표준화된 Message 객체 |
| **응답 변환** | 서비스별 변환 코드 필요 (`normalize_response()`) | 불필요 |
| **서비스 탐색** | URL/스펙을 하드코딩 | AgentCard 기반 자동 탐색 |
| **새 서비스 추가** | 엔드포인트, 요청 형식, 변환 코드 모두 수정 | AgentCard 등록만으로 추가 |
| **대화 상태** | 직접 구현 필요 | 프로토콜 내장 (Task, Conversation) |
| **에이전트 간 통신** | 개별 API 호출 코드 작성 | 표준 프로토콜로 통일 |

### 코드 비교 예시

**REST API 방식 (서비스마다 다른 호출 코드)**
```python
# 보안 서비스 호출
resp1 = requests.post("http://localhost:6001/api/v1/security/review",
                       json={"proposal": proposal})
# 성능 서비스 호출 (다른 URL, 다른 키)
resp2 = requests.post("http://localhost:6002/api/v1/performance/analyze",
                       json={"system_spec": proposal})
# 응답 형식도 다름: resp1은 "issues", resp2는 "findings"
```

**A2A 프로토콜 방식 (동일한 호출 코드)**
```python
# 모든 에이전트에 동일한 코드
for agent_url in ["http://localhost:5001", "http://localhost:5002"]:
    client = A2AClient(agent_url)
    message = Message(role=MessageRole.USER, content=TextContent(text=proposal_json))
    response = client.send_message(message)  # 동일한 응답 형식
```

### 비교 데모 실행

```bash
# 서버 없이 코드 구조 차이를 확인하는 데모
uv run python solution/traditional_multi_service.py
```

---

## 아키텍처 구조

```
                    설계 제안서
                        |
                        v
              +-------------------+
              |   오케스트레이터   |
              | (orchestrator.py) |
              +-------------------+
               /    |    |    \
              v     v    v     v
         +------+ +------+ +------+ +------+
         | 보안 | | 성능 | | 비용 | | 운영 |
         | :5001| | :5002| | :5003| | :5004|
         +------+ +------+ +------+ +------+
              \    |    |    /
               v   v    v  v
        +-----------------------------+
        |  관점 충돌 분석 및 종합 보고서  |
        +-----------------------------+
```

- 각 에이전트는 독립된 A2A 서버로 실행됩니다 (port 5001 ~ 5004).
- 오케스트레이터가 순차적으로 각 에이전트에게 리뷰를 요청합니다.
- 에이전트 간 관점 충돌을 분석하여 최종 판정을 내립니다.

### 시나리오 상세

1. **설계 제안서 입력**: 사내 레거시 시스템(Java 8, Oracle, WebLogic)을 AWS EKS로 전환하는 제안
2. **전문가별 독립 분석**: 각 에이전트가 자신의 관점에서 제안서를 리뷰
3. **관점 충돌 식별**: 오케스트레이터가 에이전트 간 상충하는 의견 3건을 탐지
   - 성능(오토스케일링 긍정) vs 비용(TCO 증가 우려)
   - 보안(고급 보안 체계 요구) vs 운영(팀 역량 부재)
   - 제안서(인력 60% 감축 기대) vs 운영(초기 인력 증가 필요)
4. **종합 판정**: 반려 2건(보안, 운영) 이상으로 최종 반려, 재심의 조건 제시

---

## 사전 준비

### 1. 의존성 설치

```bash
cd lab2-a2a-agents
uv sync
```

### 2. 환경 변수 설정 (선택)

규칙 기반 분석이 기본이므로 API 키 없이도 실행할 수 있습니다.

```bash
cp .env.example .env
# 필요한 경우 OPENAI_API_KEY를 설정하십시오.
```

---

## 실습 순서 (20분)

### Step 1: 설계 제안서 확인 (2분)

`data/design_proposal.json` 파일을 열어 제안 내용을 확인하십시오.

```bash
cat data/design_proposal.json | python -m json.tool
```

핵심 확인 사항:
- **현재 시스템**: Java 8, Oracle DB, WebLogic 기반 온프레미스
- **전환 대상**: AWS EKS 기반 컨테이너 아키텍처
- **예산/기간**: 12억원 / 18개월
- **기대 효과**: 장애 복구 4시간에서 15분으로 단축, 운영 인력 60% 감축

### Step 2: 전문가 에이전트 구현 (10분)

`starter/agents.py` 파일을 열어 4개 에이전트의 분석 로직을 구현하십시오.

각 에이전트의 `handle_message` 메서드에서 TODO 주석을 따라 분석을 추가합니다.

```python
# 예시: SecurityReviewAgent의 데이터 주권 분석
if proposal.get("proposed_changes", {}).get("target_cloud") == "AWS":
    findings.append({
        "category": "데이터 주권",
        "severity": "높음",
        "finding": "퍼블릭 클라우드 전환 시 개인정보보호법에 따른 ...",
        "recommendation": "데이터 분류 체계를 수립하고 ...",
    })
```

**핵심 포인트**: 각 에이전트가 **서로 다른 관점**에서 분석하도록 구현하십시오.
- 성능 에이전트는 오토스케일링을 긍정적으로 평가
- 비용 에이전트는 TCO 증가를 우려
- 보안 에이전트는 고급 보안 체계를 요구
- 운영 에이전트는 팀 역량 부족을 지적

### Step 3: 에이전트 서버 실행 (2분)

터미널 1에서 에이전트를 실행합니다.

```bash
# starter 코드 실행
uv run python starter/agents.py

# 또는 완성된 solution 코드 실행
uv run python solution/agents.py
```

실행하면 4개의 에이전트가 각각 port 5001 ~ 5004에서 시작됩니다.

```
============================================================
  아키텍처 심의위원회(ARB) — 전문가 에이전트 시작
============================================================

  [Security Review Agent] http://localhost:5001
  [Performance Review Agent] http://localhost:5002
  [Cost Review Agent] http://localhost:5003
  [Ops Review Agent] http://localhost:5004

  모든 에이전트가 실행 중입니다. Ctrl+C로 종료하십시오.
============================================================
```

### Step 4: 오케스트레이터로 심의 실행 (6분)

터미널 2를 열어 오케스트레이터를 실행합니다.

```bash
# starter 코드 실행
uv run python starter/orchestrator.py

# 또는 완성된 solution 코드 실행
uv run python solution/orchestrator.py
```

---

## 실행 결과 예시

```
============================================================
  아키텍처 심의위원회(ARB) 시작
============================================================

  설계 제안서를 로드합니다...
  제안: 사내 레거시 시스템의 퍼블릭 클라우드 전환
  예산: 12억원
  기간: 18개월

--- 전문가 리뷰 수집 ---

  [보안] 보안 리뷰 에이전트에게 리뷰를 요청합니다...
    응답 수신 완료 (0.1초) - 판정: 반려

  [성능] 성능 리뷰 에이전트에게 리뷰를 요청합니다...
    응답 수신 완료 (0.1초) - 판정: 조건부 승인

  [비용] 비용 리뷰 에이전트에게 리뷰를 요청합니다...
    응답 수신 완료 (0.1초) - 판정: 조건부 승인

  [운영] 운영 리뷰 에이전트에게 리뷰를 요청합니다...
    응답 수신 완료 (0.1초) - 판정: 반려

============================================================
  아키텍처 심의위원회(ARB) 종합 보고서
============================================================

--- 2. 전문가별 판정 ---
  보안 리뷰 에이전트: 반려
  성능 리뷰 에이전트: 조건부 승인
  비용 리뷰 에이전트: 조건부 승인
  운영 리뷰 에이전트: 반려

--- 4. 관점 충돌 분석 ---
  1. [성능 대 비용]
     성능 에이전트는 오토스케일링을 긍정적으로 평가하나,
     비용 에이전트는 3년 TCO 증가를 우려합니다.

  2. [보안 요구 대 운영 역량]
     보안 에이전트는 고급 보안 체계를 요구하나,
     운영 에이전트는 팀의 클라우드 역량 부재를 지적합니다.

  3. [기대 효과 대 운영 현실]
     제안서는 운영 인력 60% 감축을 기대하나,
     운영 에이전트는 전환 초기 오히려 인력 증가가 필요하다고 판단합니다.

============================================================
  최종 판정: 반려
============================================================
```

---

## 평가 (Evaluation)

멀티에이전트 시스템은 개별 에이전트의 응답 품질뿐 아니라, 에이전트 간 상호작용까지 검증해야 합니다.

`solution/eval.py`는 3가지 평가 패턴을 실제로 구현합니다.

### 실행 방법

에이전트 서버가 실행 중인 상태에서 별도 터미널에서 실행합니다.

```bash
# 터미널 1: 에이전트 실행 (이미 실행 중이면 생략)
uv run python solution/agents.py

# 터미널 2: 평가 실행
uv run python solution/eval.py
```

### 3가지 평가 패턴

| 패턴 | 검증 대상 | 사례 |
|------|----------|------|
| 1. 에이전트별 응답 평가 | 각 에이전트가 올바른 분석 결과를 반환하는지 | 보안 에이전트가 데이터 주권/암호화를 분석하는지, 운영 에이전트가 역량 부재를 지적하는지 |
| 2. 의사결정 일관성 평가 | 판정(verdict) 로직이 규칙에 부합하는지 | 높은 심각도 2건 이상이면 반려, high_severity_count가 정확한지 |
| 3. 에이전트 간 충돌 탐지 | 상충하는 관점이 올바르게 식별되는지 | 성능 대 비용 충돌, 보안 요구 대 운영 역량 충돌이 감지되는지 |

### 기대 출력

```
============================================================
  멀티에이전트 시스템 — 평가 시작
============================================================

--- 1. 에이전트별 응답 평가 ---
  [보안 리뷰 에이전트] 응답 수신 (0.05초)
  [PASS] 응답 구조: agent, verdict, findings 필드 존재
  [PASS] 도메인 분석: 데이터 주권 관련 finding 존재
  [PASS] 도메인 분석: 암호화 관련 finding 존재
  ...

--- 2. 의사결정 일관성 평가 ---
  [PASS] 보안 에이전트: high_severity_count 정확
  [PASS] 보안 에이전트: 반려 규칙 준수
  ...

--- 3. 에이전트 간 충돌 탐지 평가 ---
  [PASS] 성능 대 비용 충돌 감지됨
  [PASS] 보안 요구 대 운영 역량 충돌 감지됨
  ...

============================================================
  평가 완료: 전체 통과
============================================================
```

---

## A2A 프로토콜 구성 요소와 코드 매핑

이 실습의 코드가 A2A 프로토콜의 각 구성 요소를 어떻게 사용하는지 정리합니다.

### AgentCard — 에이전트 자기 설명

```python
# agents.py에서 에이전트를 등록할 때 AgentCard를 생성합니다.
card = AgentCard(
    name="Security Review Agent",           # 에이전트 이름
    description="보안 관점에서 아키텍처를 리뷰합니다",  # 능력 설명
    url="http://localhost:5001",            # 접근 URL
    version="1.0.0",                        # 버전
    capabilities={                          # 지원 기능
        "pushNotifications": False,
        "stateTransitionHistory": False,
    },
)
```

### A2AServer — 에이전트 서버

```python
# 에이전트는 A2AServer를 상속하고 handle_message를 구현합니다.
class SecurityReviewAgent(A2AServer):
    def handle_message(self, message):
        # message.content.text에서 설계안을 읽고
        # 분석 결과를 Message로 반환합니다.
        return Message(
            role=MessageRole.AGENT,
            content=TextContent(text=json.dumps(result)),
        )
```

### A2AClient — 에이전트 호출

```python
# 오케스트레이터에서 에이전트를 호출합니다.
client = A2AClient("http://localhost:5001")
message = Message(
    role=MessageRole.USER,
    content=TextContent(text=proposal_json),
)
response = client.send_message(message)  # 표준화된 응답
```

### Message — 표준 메시지 형식

```python
# 모든 에이전트가 동일한 Message 형식을 사용합니다.
# 요청: role=USER, 응답: role=AGENT
Message(
    role=MessageRole.USER,              # 또는 MessageRole.AGENT
    content=TextContent(text="..."),    # 텍스트 내용
)
```

---

## 관점 충돌이 가치 있는 이유

단일 에이전트는 하나의 최적화 목표만 추구합니다.
멀티에이전트 시스템에서 관점 충돌이 발생하면, 오케스트레이터가 **트레이드오프를 명시적으로 드러내고** 균형 잡힌 의사결정을 지원할 수 있습니다.

이 패턴은 실제 기업의 아키텍처 심의위원회, 투자 심의, 리스크 평가 등에 적용할 수 있습니다.

---

## 파일 구조

```
lab2-a2a-agents/
├── README.md                              ← 이 문서
├── pyproject.toml                         ← 의존성 정의
├── .env.example                           ← 환경 변수 템플릿
├── data/
│   └── design_proposal.json               ← 아키텍처 설계 제안서
├── solution/
│   ├── agents.py                          ← 전문가 에이전트 4종 (완성본)
│   ├── orchestrator.py                    ← 오케스트레이터 (완성본)
│   ├── eval.py                            ← 멀티에이전트 평가 스크립트
│   └── traditional_multi_service.py       ← REST API 비교 예제
└── starter/
    ├── agents.py                          ← 에이전트 (TODO 포함, 실습용)
    └── orchestrator.py                    ← 오케스트레이터 (TODO 포함, 실습용)
```

---

## 확장 아이디어

- LLM을 연결하여 에이전트가 동적으로 분석하도록 개선
- 에이전트 간 토론(Debate) 라운드를 추가하여 합의를 도출
- 새로운 전문가 에이전트(법무, 데이터, UX 등)를 추가하여 심의 범위를 확장
- AgentRegistry를 도입하여 에이전트 동적 탐색 구현
