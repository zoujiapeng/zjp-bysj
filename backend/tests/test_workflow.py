from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from conftest import create_base_people, login


def create_student_and_case(client: TestClient, admin_headers: dict[str, str], restricted=False):
    org, counselor, psychologist = create_base_people(client, admin_headers)
    counselor_headers = login(client, "counselor1", "Counselor123!")
    student = client.post(
        "/api/v1/students",
        json={
            "student_no": "20260001",
            "name": "测试学生",
            "gender": "男",
            "organization_id": org["id"],
            "major": "软件工程",
            "grade": "2026",
            "class_name": "软件2601",
            "phone": "13800000000",
            "counselor_id": counselor["id"],
        },
        headers=counselor_headers,
    )
    assert student.status_code == 201, student.text
    scheduled_at = datetime.now(timezone.utc) + timedelta(days=1)
    case = client.post(
        "/api/v1/cases",
        json={
            "student_id": student.json()["id"],
            "risk_level": "GREEN",
            "source": "辅导员日常观察",
            "issue_tags": ["学业压力", "睡眠"],
            "summary": "近期缺课，沟通后表示学习压力较大。",
            "confidentiality": "RESTRICTED" if restricted else "NORMAL",
            "next_follow_up_at": scheduled_at.isoformat(),
        },
        headers=counselor_headers,
    )
    assert case.status_code == 201, case.text
    return org, counselor, psychologist, student.json(), case.json(), counselor_headers


def test_complete_followup_referral_and_report(client: TestClient, admin_headers: dict[str, str]):
    org, counselor, psychologist, student, case, counselor_headers = create_student_and_case(
        client, admin_headers
    )

    tasks = client.get("/api/v1/followups?status=PLANNED", headers=counselor_headers)
    assert tasks.status_code == 200, tasks.text
    assert tasks.json()["total"] == 1
    task_id = tasks.json()["items"][0]["id"]

    completed_at = datetime.now(timezone.utc)
    next_at = completed_at + timedelta(days=7)
    completed = client.post(
        f"/api/v1/followups/{task_id}/complete",
        json={
            "method": "IN_PERSON",
            "condition": "STABLE",
            "status": "COMPLETED",
            "issue_tags": ["学业压力"],
            "summary": "学生按约到场，情绪稳定。",
            "actions": "制定一周学习计划，继续观察。",
            "completed_at": completed_at.isoformat(),
            "next_follow_up_at": next_at.isoformat(),
            "next_method": "PHONE",
            "risk_level": "YELLOW",
            "risk_reason": "仍有持续失眠，需要提高关注频率。",
        },
        headers=counselor_headers,
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["status"] == "COMPLETED"

    case_detail = client.get(f"/api/v1/cases/{case['id']}", headers=counselor_headers)
    assert case_detail.status_code == 200, case_detail.text
    assert case_detail.json()["risk_level"] == "YELLOW"
    assert len(case_detail.json()["followups"]) == 2

    referral = client.post(
        f"/api/v1/cases/{case['id']}/referrals",
        json={
            "reason": "持续失眠并影响学习，申请心理老师进一步评估。",
            "assigned_to_id": psychologist["id"],
        },
        headers=counselor_headers,
    )
    assert referral.status_code == 201, referral.text

    psychologist_headers = login(client, "psych1", "Psychologist123!")
    accepted = client.patch(
        f"/api/v1/referrals/{referral.json()['id']}",
        json={"status": "ACCEPTED", "assigned_to_id": psychologist["id"]},
        headers=psychologist_headers,
    )
    assert accepted.status_code == 200, accepted.text

    finished = client.patch(
        f"/api/v1/referrals/{referral.json()['id']}",
        json={
            "status": "COMPLETED",
            "assigned_to_id": psychologist["id"],
            "professional_note": "已完成初次专业访谈，建议维持校内支持与规律随访。",
        },
        headers=psychologist_headers,
    )
    assert finished.status_code == 200, finished.text
    assert finished.json()["status"] == "COMPLETED"

    report = client.get("/api/v1/reports/summary", headers=admin_headers)
    assert report.status_code == 200, report.text
    assert report.json()["active_case_count"] == 1
    assert report.json()["completed_followup_count"] == 1


def test_restricted_case_hidden_from_admin(client: TestClient, admin_headers: dict[str, str]):
    _, _, psychologist, _, case, counselor_headers = create_student_and_case(
        client, admin_headers, restricted=True
    )

    owner_view = client.get(f"/api/v1/cases/{case['id']}", headers=counselor_headers)
    assert owner_view.status_code == 200

    admin_view = client.get(f"/api/v1/cases/{case['id']}", headers=admin_headers)
    assert admin_view.status_code == 403

    psychologist_headers = login(client, "psych1", "Psychologist123!")
    psychologist_view = client.get(f"/api/v1/cases/{case['id']}", headers=psychologist_headers)
    assert psychologist_view.status_code == 200


def test_duplicate_active_case_and_dashboard(client: TestClient, admin_headers: dict[str, str]):
    _, _, _, student, case, counselor_headers = create_student_and_case(client, admin_headers)

    duplicate = client.post(
        "/api/v1/cases",
        json={
            "student_id": student["id"],
            "risk_level": "YELLOW",
            "source": "重复上报",
            "issue_tags": ["学业压力"],
            "summary": "不应创建第二个在管个案。",
        },
        headers=counselor_headers,
    )
    assert duplicate.status_code == 409

    dashboard = client.get("/api/v1/dashboard", headers=counselor_headers)
    assert dashboard.status_code == 200, dashboard.text
    assert dashboard.json()["active_cases"] == 1
    assert len(dashboard.json()["tasks"]) == 1
    assert dashboard.json()["tasks"][0]["case_id"] == case["id"]


def test_referral_status_is_controlled_by_referral_workflow(
    client: TestClient, admin_headers: dict[str, str]
):
    _, _, psychologist, _, case, counselor_headers = create_student_and_case(client, admin_headers)

    manual = client.patch(
        f"/api/v1/cases/{case['id']}",
        json={"status": "REFERRED"},
        headers=counselor_headers,
    )
    assert manual.status_code == 422

    referral = client.post(
        f"/api/v1/cases/{case['id']}/referrals",
        json={
            "reason": "需要心理老师进一步评估。",
            "assigned_to_id": psychologist["id"],
        },
        headers=counselor_headers,
    )
    assert referral.status_code == 201

    bypass = client.patch(
        f"/api/v1/cases/{case['id']}",
        json={"status": "OPEN"},
        headers=counselor_headers,
    )
    assert bypass.status_code == 409


def test_cannot_deactivate_user_with_active_responsibilities(
    client: TestClient, admin_headers: dict[str, str]
):
    _, counselor, _, _, _, _ = create_student_and_case(client, admin_headers)

    deactivate = client.patch(
        f"/api/v1/users/{counselor['id']}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert deactivate.status_code == 409

    change_role = client.patch(
        f"/api/v1/users/{counselor['id']}",
        json={"role": "PSYCHOLOGIST"},
        headers=admin_headers,
    )
    assert change_role.status_code == 409


def test_counselor_requires_organization(client: TestClient, admin_headers: dict[str, str]):
    response = client.post(
        "/api/v1/users",
        json={
            "username": "orphan-counselor",
            "password": "Counselor123!",
            "full_name": "未绑定机构辅导员",
            "role": "COUNSELOR",
            "organization_id": None,
        },
        headers=admin_headers,
    )
    assert response.status_code == 422
