import io

from fastapi.testclient import TestClient

from conftest import create_base_people


def test_student_csv_import_and_export(client: TestClient, admin_headers: dict[str, str]):
    create_base_people(client, admin_headers)
    content = (
        "学号,姓名,性别,机构编码,专业,年级,班级,手机号,紧急联系人,紧急联系电话,辅导员账号\n"
        "20269999,导入学生,女,CS,软件工程,2026,软件2609,13800000000,家长,13900000000,counselor1\n"
    ).encode("utf-8")

    imported = client.post(
        "/api/v1/students/import",
        files={"file": ("students.csv", io.BytesIO(content), "text/csv")},
        headers=admin_headers,
    )
    assert imported.status_code == 200, imported.text
    assert imported.json()["created"] == 1
    assert imported.json()["errors"] == []

    exported = client.get("/api/v1/students/export.csv", headers=admin_headers)
    assert exported.status_code == 200
    assert exported.content.startswith(b"\xef\xbb\xbf")
    text = exported.content.decode("utf-8-sig")
    assert "20269999" in text
    assert "导入学生" in text
