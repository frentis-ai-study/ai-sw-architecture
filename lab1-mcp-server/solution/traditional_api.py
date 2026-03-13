"""
Lab 1: 전통적 REST API 비교 예제 (완성 코드)

같은 HR 데이터를 FastAPI REST API로 서빙합니다.
MCP 서버와의 차이점을 코드 레벨에서 비교할 수 있습니다.
"""

import json
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query

app = FastAPI(
    title="HR REST API",
    description="전통적 REST API 방식의 HR 시스템",
)

# 데이터 파일 경로 설정
DATA_DIR = Path(__file__).parent.parent / "data"


def load_json(filename: str) -> list | dict:
    """JSON 데이터 파일을 읽어서 반환합니다."""
    file_path = DATA_DIR / filename
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ──────────────────────────────────────────────
# 엔드포인트 1: HR 규정 검색
# ──────────────────────────────────────────────


@app.get("/api/hr-policies")
def search_hr_policies(q: str = Query(..., description="검색 키워드")):
    """사내 HR 규정을 키워드로 검색합니다."""
    policies = load_json("hr_policies.json")

    results = []
    for policy in policies:
        searchable = f"{policy['title']} {policy['category']} {policy['content']}"
        if q.lower() in searchable.lower():
            results.append(policy)

    if not results:
        return {"message": f"'{q}' 관련 규정을 찾을 수 없습니다.", "results": []}

    return {"query": q, "count": len(results), "results": results}


# ──────────────────────────────────────────────
# 엔드포인트 2: 직원 연차 조회
# ──────────────────────────────────────────────


@app.get("/api/employees/{employee_id}/leave")
def get_employee_leave(employee_id: str):
    """직원의 연차 잔여일을 조회합니다."""
    employees = load_json("employees.json")

    for emp in employees:
        if emp["employee_id"] == employee_id:
            return {
                "employee_id": emp["employee_id"],
                "name": emp["name"],
                "department": emp["department"],
                "total_leave": emp["total_leave"],
                "used_leave": emp["used_leave"],
                "remaining_leave": emp["remaining_leave"],
            }

    raise HTTPException(
        status_code=404,
        detail=f"사번 '{employee_id}'에 해당하는 직원을 찾을 수 없습니다.",
    )


# ──────────────────────────────────────────────
# 엔드포인트 3: 부서 조직도 조회
# ──────────────────────────────────────────────


@app.get("/api/org-chart/{department}")
def get_org_chart(department: str):
    """부서별 조직도를 조회합니다."""
    org_chart = load_json("org_chart.json")

    if department in org_chart:
        dept_info = org_chart[department]
        return {
            "department": department,
            "department_id": dept_info["department_id"],
            "head": dept_info["head"],
            "head_position": dept_info["head_position"],
            "members": dept_info["members"],
            "sub_teams": dept_info["sub_teams"],
            "total_members": len(dept_info["members"]) + 1,
        }

    raise HTTPException(
        status_code=404,
        detail={
            "message": f"'{department}' 부서를 찾을 수 없습니다.",
            "available_departments": list(org_chart.keys()),
        },
    )


if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("  HR REST API 서버")
    print("=" * 60)
    print("Swagger UI: http://localhost:8000/docs")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000)
