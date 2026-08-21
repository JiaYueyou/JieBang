"""企业内部转岗独立业务域 API 集成测试。"""


def talent_payload():
    return {
        "employee_no": "E-1001",
        "name": "张敏",
        "department": "业务研发部",
        "current_position": "Java 工程师",
        "level": "mid",
        "location": "合肥",
        "tenure_months": 30,
        "position_tenure_months": 18,
        "skills": ["Java", "MySQL", "Redis"],
        "project_highlights": ["参与交易平台改造"],
        "status": "active",
    }


def position_payload():
    return {
        "title": "内部平台工程师",
        "standardized_title": "平台工程师",
        "department": "平台研发部",
        "receiving_manager": "平台负责人",
        "level": "mid",
        "headcount": 2,
        "open_reason": "平台能力升级",
        "responsibilities": ["负责内部平台服务建设"],
        "requirements": ["具备服务端研发经验"],
        "required_skills": ["Java", "MySQL"],
        "trainable_skills": ["Kubernetes"],
        "transfer_profile": ["有复杂系统研发经验"],
        "manager_confirmations": ["确认到岗时间"],
        "min_tenure_months": 12,
        "min_position_tenure_months": 6,
        "allowed_departments": ["业务研发部"],
        "restrictions": [],
        "internal_description": "仅供内部转岗使用",
        "status": "draft",
    }


async def test_internal_transfer_flow_is_isolated_from_public_jobs(client, auth_headers):
    talent_response = await client.post(
        "/api/v1/internal-transfer/talents", headers=auth_headers, json=talent_payload()
    )
    position_response = await client.post(
        "/api/v1/internal-transfer/positions", headers=auth_headers, json=position_payload()
    )
    assert talent_response.status_code == position_response.status_code == 200
    talent = talent_response.json()["data"]
    position = position_response.json()["data"]

    pending = await client.put(
        f"/api/v1/internal-transfer/positions/{position['id']}/status",
        headers=auth_headers,
        json={"status": "pending_approval"},
    )
    assert pending.status_code == 200
    opened = await client.put(
        f"/api/v1/internal-transfer/positions/{position['id']}/status",
        headers=auth_headers,
        json={"status": "open"},
    )
    assert opened.status_code == 200

    rule_response = await client.post(
        "/api/v1/internal-transfer/rule-sets",
        headers=auth_headers,
        json={
            "name": "研发序列内部流动规则",
            "min_tenure_months": 12,
            "min_position_tenure_months": 6,
            "min_match_score": 70,
            "skill_weight": 85,
            "tenure_weight": 15,
            "status": "active",
        },
    )
    assert rule_response.status_code == 200
    rule = rule_response.json()["data"]

    match_response = await client.post(
        "/api/v1/internal-transfer/matches/by-position",
        headers=auth_headers,
        json={"position_id": position["id"], "rule_set_id": rule["id"]},
    )
    assert match_response.status_code == 200
    match = match_response.json()["data"][0]
    assert match["talent_id"] == talent["id"]
    assert match["eligible"] is True
    assert match["score"] == 100
    assert match["missing_skills"] == []

    decision_response = await client.post(
        "/api/v1/internal-transfer/decisions",
        headers=auth_headers,
        json={
            "talent_id": talent["id"],
            "position_id": position["id"],
            "rule_set_id": rule["id"],
            "note": "管理层会议确认",
        },
    )
    assert decision_response.status_code == 200
    assert decision_response.json()["data"]["status"] == "confirmed"

    duplicate_decision = await client.post(
        "/api/v1/internal-transfer/decisions",
        headers=auth_headers,
        json={
            "talent_id": talent["id"],
            "position_id": position["id"],
            "rule_set_id": rule["id"],
        },
    )
    assert duplicate_decision.status_code == 422
    assert "已经存在" in duplicate_decision.json()["message"]

    demand_response = await client.get(
        "/api/v1/internal-transfer/skill-demands", headers=auth_headers
    )
    assert demand_response.status_code == 200
    assert {item["skill"] for item in demand_response.json()["data"]} == {
        "Java", "MySQL", "Kubernetes"
    }

    public_jobs = await client.get("/api/v1/jobs", headers=auth_headers)
    assert public_jobs.status_code == 200
    assert public_jobs.json()["data"] == []


async def test_internal_position_requires_authentication(client):
    response = await client.get("/api/v1/internal-transfer/positions")
    assert response.status_code == 401


async def test_internal_positions_support_server_pagination_and_filters(client, auth_headers):
    for title in ("内部平台工程师", "数据治理工程师", "平台架构师"):
        response = await client.post(
            "/api/v1/internal-transfer/positions",
            headers=auth_headers,
            json={**position_payload(), "title": title},
        )
        assert response.status_code == 200

    first_page = await client.get(
        "/api/v1/internal-transfer/positions?page=1&page_size=1&keyword=平台&status=draft",
        headers=auth_headers,
    )
    assert first_page.status_code == 200
    body = first_page.json()
    assert len(body["data"]) == 1
    assert "平台" in body["data"][0]["title"]
    assert body["meta"] == {
        "page": 1,
        "page_size": 1,
        "total": 3,
        "total_pages": 3,
    }


async def test_employee_number_search_autofills_talent_from_directory(client, auth_headers):
    synced = await client.post(
        "/api/v1/internal-transfer/employee-directory",
        headers=auth_headers,
        json={
            "employee_no": "20260715018",
            "name": "李然",
            "department": "数据平台部",
            "current_position": "数据开发工程师",
            "level": "senior",
            "location": "合肥",
            "tenure_months": 26,
            "position_tenure_months": 14,
            "skills": ["Python", "Spark"],
            "project_highlights": ["建设离线数仓"],
            "status": "active",
            "source": "test_hr_sync",
        },
    )
    assert synced.status_code == 200
    employee = synced.json()["data"]
    assert employee["in_talent_pool"] is False

    searched = await client.get(
        "/api/v1/internal-transfer/employee-directory?keyword=15018",
        headers=auth_headers,
    )
    assert searched.status_code == 200
    assert searched.json()["data"][0]["department"] == "数据平台部"

    created = await client.post(
        f"/api/v1/internal-transfer/talents/from-directory/{employee['id']}",
        headers=auth_headers,
    )
    assert created.status_code == 200
    assert created.json()["data"]["employee_no"] == "20260715018"
    assert created.json()["data"]["skills"] == ["Python", "Spark"]

    searched_again = await client.get(
        "/api/v1/internal-transfer/employee-directory?keyword=20260715",
        headers=auth_headers,
    )
    assert searched_again.json()["data"][0]["in_talent_pool"] is True


async def test_department_and_employee_directory_crud(client, auth_headers):
    department = (await client.post(
        "/api/v1/internal-transfer/departments",
        headers=auth_headers,
        json={"code": "D101", "name": "智能平台部", "manager": "王经理", "location": "合肥", "status": "active"},
    )).json()["data"]
    listed = await client.get("/api/v1/internal-transfer/departments", headers=auth_headers)
    assert any(item["name"] == "智能平台部" for item in listed.json()["data"])

    employee_payload = {
        "employee_no": "E-9001", "name": "陈晨", "department": "智能平台部",
        "current_position": "算法工程师", "level": "mid", "location": "合肥",
        "tenure_months": 12, "position_tenure_months": 8, "skills": ["Python"],
        "project_highlights": [], "status": "active", "source": "manual",
    }
    employee = (await client.post(
        "/api/v1/internal-transfer/employee-directory", headers=auth_headers, json=employee_payload
    )).json()["data"]
    department_search = await client.get(
        "/api/v1/internal-transfer/employee-directory",
        headers=auth_headers,
        params={"keyword": "陈", "department": "智能平台部"},
    )
    assert [item["id"] for item in department_search.json()["data"]] == [employee["id"]]
    other_department_search = await client.get(
        "/api/v1/internal-transfer/employee-directory",
        headers=auth_headers,
        params={"keyword": "陈", "department": "其他部门"},
    )
    assert other_department_search.json()["data"] == []
    updated = await client.put(
        f"/api/v1/internal-transfer/employee-directory/{employee['id']}",
        headers=auth_headers,
        json={**employee_payload, "current_position": "高级算法工程师", "skills": ["Python", "PyTorch"]},
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["skills"] == ["Python", "PyTorch"]

    blocked = await client.delete(
        f"/api/v1/internal-transfer/departments/{department['id']}", headers=auth_headers
    )
    assert blocked.status_code == 422
    deleted_employee = await client.delete(
        f"/api/v1/internal-transfer/employee-directory/{employee['id']}", headers=auth_headers
    )
    assert deleted_employee.status_code == 204
    deleted_department = await client.delete(
        f"/api/v1/internal-transfer/departments/{department['id']}", headers=auth_headers
    )
    assert deleted_department.status_code == 204


async def test_internal_position_cannot_skip_approval(client, auth_headers):
    direct_open = await client.post(
        "/api/v1/internal-transfer/positions",
        headers=auth_headers,
        json={**position_payload(), "status": "open"},
    )
    assert direct_open.status_code == 422

    created = await client.post(
        "/api/v1/internal-transfer/positions",
        headers=auth_headers,
        json=position_payload(),
    )
    position_id = created.json()["data"]["id"]
    skipped = await client.put(
        f"/api/v1/internal-transfer/positions/{position_id}/status",
        headers=auth_headers,
        json={"status": "open"},
    )
    assert skipped.status_code == 422


async def test_transfer_rules_support_read_update_and_safe_delete(client, auth_headers):
    created = await client.post(
        "/api/v1/internal-transfer/rule-sets",
        headers=auth_headers,
        json={
            "name": "研发人才流动规则",
            "min_tenure_months": 6,
            "min_position_tenure_months": 3,
            "min_match_score": 65,
            "skill_weight": 80,
            "tenure_weight": 20,
            "status": "draft",
        },
    )
    assert created.status_code == 200
    rule = created.json()["data"]

    detail = await client.get(
        f"/api/v1/internal-transfer/rule-sets/{rule['id']}", headers=auth_headers
    )
    assert detail.status_code == 200
    assert detail.json()["data"]["name"] == "研发人才流动规则"

    updated = await client.put(
        f"/api/v1/internal-transfer/rule-sets/{rule['id']}",
        headers=auth_headers,
        json={
            "name": "研发人才流动规则（修订）",
            "min_tenure_months": 12,
            "min_position_tenure_months": 6,
            "min_match_score": 70,
            "skill_weight": 85,
            "tenure_weight": 15,
            "status": "draft",
        },
    )
    assert updated.status_code == 200
    assert updated.json()["data"]["min_tenure_months"] == 12

    deleted = await client.delete(
        f"/api/v1/internal-transfer/rule-sets/{rule['id']}", headers=auth_headers
    )
    assert deleted.status_code == 200
    missing = await client.get(
        f"/api/v1/internal-transfer/rule-sets/{rule['id']}", headers=auth_headers
    )
    assert missing.status_code == 404


async def test_external_candidate_admission_allocates_employee_number_and_enters_pool(client, auth_headers):
    uploaded = await client.post(
        "/api/v1/resumes",
        headers=auth_headers,
        data={
            "name": "周晴",
            "current_position": "后端开发工程师",
            "experience": "2年工作经验",
            "department": "研发部",
            "location": "合肥",
        },
        files={"file": ("zhouqing.txt", "熟悉 Python、FastAPI 和 Redis".encode(), "text/plain")},
    )
    assert uploaded.status_code == 200, uploaded.text
    resume_id = uploaded.json()["data"]["id"]

    admitted = await client.post(
        f"/api/v1/internal-transfer/talents/from-resume/{resume_id}",
        headers=auth_headers,
        json={
            "department": "平台研发部",
            "current_position": "Python 开发工程师",
            "level": "junior",
            "location": "合肥",
        },
    )
    assert admitted.status_code == 200, admitted.text
    talent = admitted.json()["data"]
    assert talent["employee_no"].startswith("2026")
    assert talent["department"] == "平台研发部"
    assert talent["tenure_months"] == 24
    assert {"Python", "FastAPI", "Redis"}.issubset(set(talent["skills"]))

    pool = await client.get("/api/v1/internal-transfer/talents", headers=auth_headers)
    assert pool.json()["data"][0]["employee_no"] == talent["employee_no"]
    directory = await client.get(
        f"/api/v1/internal-transfer/employee-directory?keyword={talent['employee_no']}",
        headers=auth_headers,
    )
    assert directory.json()["data"][0]["in_talent_pool"] is True

    duplicate = await client.post(
        f"/api/v1/internal-transfer/talents/from-resume/{resume_id}",
        headers=auth_headers,
        json={"department": "平台研发部", "current_position": "Python 开发工程师"},
    )
    assert duplicate.status_code == 422
    assert "已录用" in duplicate.json()["message"]
