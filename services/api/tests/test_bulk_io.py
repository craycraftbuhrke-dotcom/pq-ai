from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.models.domain import Factory
from app.services.bulk_io import export_resource, import_resource, render_template
from tests.schema_guard import create_transient_test_schema


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_transient_test_schema(engine)
    return Session(engine)


def test_bulk_template_contains_import_headers() -> None:
    response = render_template("master.factories", "csv")
    content = response.body.decode("utf-8-sig")

    assert "id,code,name,site_owner,remark,is_active" in content


def test_bulk_import_csv_creates_and_upserts_factory() -> None:
    db = build_session()
    csv_content = "\ufeffid,code,name,site_owner,remark,is_active\n,F99,九十九号工厂,陈工,初始,true\n"

    created = import_resource(
        "master.factories",
        csv_content.encode("utf-8"),
        filename="factories.csv",
        mode="upsert",
        db=db,
    )
    assert created["created"] == 1
    factory = db.query(Factory).filter_by(code="F99").one()
    assert factory.name == "九十九号工厂"

    update_content = f"id,code,name,site_owner,remark,is_active\n{factory.id},F99,九十九号涂装工厂,李工,更新,false\n"
    updated = import_resource(
        "master.factories",
        update_content.encode("utf-8"),
        filename="factories.csv",
        mode="upsert",
        db=db,
    )
    assert updated["updated"] == 1
    db.refresh(factory)
    assert factory.name == "九十九号涂装工厂"
    assert factory.is_active is False
    db.close()


def test_bulk_import_reports_row_errors_without_stopping_batch() -> None:
    db = build_session()
    csv_content = "id,code,name,site_owner,remark,is_active\n,F98,九十八号工厂,陈工,,true\n,F,坏,陈工,,maybe\n"

    result = import_resource(
        "master.factories",
        csv_content.encode("utf-8"),
        filename="factories.csv",
        mode="upsert",
        db=db,
    )

    assert result["created"] == 1
    assert result["failed"] == 1
    assert "布尔字段无法识别" in result["errors"][0]["message"]
    db.close()


def test_bulk_export_returns_excel_workbook() -> None:
    db = build_session()
    import_resource(
        "master.factories",
        "id,code,name,site_owner,remark,is_active\n,F97,九十七号工厂,陈工,,true\n".encode(),
        filename="factories.csv",
        mode="upsert",
        db=db,
    )
    response = export_resource("master.factories", "xlsx", db)

    assert response.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert response.body[:2] == b"PK"
    db.close()
