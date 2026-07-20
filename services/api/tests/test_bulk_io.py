import asyncio
import csv
from datetime import UTC, datetime
from io import StringIO
import re

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from app.db.base import Base
from app.services.request_body import read_limited_request_body
from app.api.routes.factories import create_factory
from app.api.routes.master_data import (
    bind_factory_vehicle_model,
    bind_measurement_group_point,
    bind_vehicle_model_color,
    create_color,
    create_measurement_group,
    create_measurement_point,
    create_part,
    create_vehicle_model,
)
from app.api.routes.process import (
    create_brush,
    create_production_run,
    create_program_version,
    create_spray_program,
)
from app.models.domain import (
    Brush,
    BrushParameter,
    BrushPointContribution,
    Color,
    Factory,
    MeasurementPoint,
    MeasurementPoint3DLayout,
    MeasurementPointLayout,
    ProductionRun,
    ProgramColor,
    ProgramVehicleModel,
    QualityMeasurement,
    QualityMetricValue,
    SprayProgramVersion,
)
from app.schemas.common import FactoryCreate
from app.schemas.master_data import (
    ColorCreate,
    FactoryVehicleModelCreate,
    MeasurementGroupCreate,
    MeasurementGroupPointBind,
    MeasurementPointCreate,
    PartCreate,
    VehicleModelColorCreate,
    VehicleModelCreate,
)
from app.schemas.process import (
    BrushCreate,
    ProductionRunCreate,
    SprayProgramCreate,
    SprayProgramVersionCreate,
)
from app.services.bulk_io import (
    RESOURCES,
    describe_bulk_columns,
    export_resource,
    import_resource,
    render_template,
)
from tests.schema_guard import create_transient_test_schema


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_transient_test_schema(engine)
    return Session(engine)


def test_bulk_request_stream_stops_as_soon_as_limit_is_exceeded() -> None:
    receive_calls = 0
    messages = iter(
        [
            {"type": "http.request", "body": b"1234", "more_body": True},
            {"type": "http.request", "body": b"5678", "more_body": True},
            {"type": "http.request", "body": b"should-not-be-read", "more_body": False},
        ]
    )

    async def receive():
        nonlocal receive_calls
        receive_calls += 1
        return next(messages)

    request = Request({"type": "http", "method": "POST", "path": "/bulk", "headers": []}, receive)
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(read_limited_request_body(request, 6))
    assert exc_info.value.status_code == 413
    assert receive_calls == 2


def test_every_orm_table_has_bulk_support_or_a_governed_exclusion() -> None:
    governed_exclusions = {
        "api_key",
        "app_user",
        "audit_log",
        "closed_loop_evaluation",
        "controlled_trial",
        "dataset_snapshot",
        "dataset_split_member",
        "diagnosis_result",
        "measurement_repeat_reading",
        "model_acceptance_decision",
        "model_acceptance_policy",
        "model_applicability_scope",
        "model_artifact",
        "model_ood_policy",
        "model_validation_fold",
        "model_version",
        "path_segment_execution",
        "permission",
        "point_feature_snapshot",
        "prediction_result",
        "program_rollback_execution",
        "quality_metric_definition",
        "quality_metric_value",
        "recommendation",
        "recommendation_action",
        "remote_parameter_snapshot",
        "remote_program_release",
        "remote_release_event",
        "remote_station_connection",
        "remote_station_reconciliation",
        "role_code",
        "role_permission",
        "training_data_upload",
        "training_wide_sample",
        "user_role",
        "user_session",
    }
    orm_tables = {table.name for table in Base.metadata.sorted_tables}
    bulk_tables = {resource.model.__tablename__ for resource in RESOURCES.values()}

    assert len(orm_tables) == 99
    assert len(RESOURCES) == 63
    assert orm_tables - bulk_tables == governed_exclusions


def build_quality_bulk_context(db: Session) -> dict[str, str]:
    now = datetime(2026, 7, 8, 8, 0, tzinfo=UTC)
    factory = create_factory(
        FactoryCreate(code="FQ1", name="Factory Quality 01", site_owner="Owner"),
        db,
    )
    vehicle = create_vehicle_model(
        VehicleModelCreate(code="MQ1", name="Model Quality 01"),
        db,
    )
    color = create_color(
        ColorCreate(code="CQ1", name="Color Quality 01", color_type="BASECOAT"),
        db,
    )
    bind_factory_vehicle_model(
        FactoryVehicleModelCreate(factory_id=factory.id, vehicle_model_id=vehicle.id),
        db,
    )
    bind_vehicle_model_color(
        VehicleModelColorCreate(vehicle_model_id=vehicle.id, color_id=color.id),
        db,
    )
    part = create_part(PartCreate(code="PQ1", name="Roof Panel"), db)
    point = create_measurement_point(
        MeasurementPointCreate(
            code="PT1",
            name="Point 01",
            vehicle_model_id=vehicle.id,
            part_id=part.id,
            point_type="QUALITY",
            quality_types=["ORANGE_PEEL"],
        ),
        db,
    )
    group = create_measurement_group(
        MeasurementGroupCreate(
            code="G1",
            name="橘皮编组",
            vehicle_model_id=vehicle.id,
            quality_type="ORANGE_PEEL",
        ),
        db,
    )
    bind_measurement_group_point(
        MeasurementGroupPointBind(
            measurement_group_id=group.id,
            measurement_point_id=point.id,
            sequence_no=1,
        ),
        db,
    )
    run = create_production_run(
        ProductionRunCreate(
            run_no="RUN-QUALITY",
            factory_id=factory.id,
            vehicle_model_id=vehicle.id,
            color_id=color.id,
            started_at=now,
        ),
        db,
    )
    return {
        "factory_id": factory.id,
        "factory_code": factory.code,
        "group_id": group.id,
        "group_code": group.code,
        "color_id": color.id,
        "color_code": color.code,
        "point_id": point.id,
        "point_code": point.code,
        "run_id": run.id,
        "run_no": run.run_no,
        "vehicle_id": vehicle.id,
        "vehicle_code": vehicle.code,
    }


def test_bulk_template_contains_import_headers() -> None:
    response = render_template("master.factories", "csv")
    content = response.body.decode("utf-8-sig")

    assert content.splitlines()[0] == "业务代码,名称,现场调试负责人,备注,是否启用"
    assert "id" not in content.splitlines()[0].lower()


def test_template_hides_fields_supplied_by_current_page_context() -> None:
    response = render_template(
        "process.production-runs",
        "csv",
        default_values={
            "factory_id": "factory-context",
            "vehicle_model_id": "model-context",
            "color_id": "color-context",
        },
    )
    header = response.body.decode("utf-8-sig").splitlines()[0]

    assert "工厂" not in header
    assert "车型" not in header
    assert "颜色" not in header
    assert "生产记录编号" in header


@pytest.mark.parametrize("resource_key", sorted(RESOURCES))
def test_every_upload_template_uses_unique_chinese_headers(resource_key: str) -> None:
    response = render_template(resource_key, "csv")
    content = response.body.decode("utf-8-sig")
    headers = next(csv.reader(StringIO(content)))

    assert headers
    assert len(headers) == len(set(headers))
    assert all(re.search(r"[\u4e00-\u9fff]", header) for header in headers)
    assert all(header.lower() != "id" for header in headers)


@pytest.mark.parametrize(
    "resource_key",
    sorted(key for key in RESOURCES if key != "quality.measurements"),
)
def test_general_upload_template_headers_do_not_contain_internal_english_names(resource_key: str) -> None:
    response = render_template(resource_key, "csv")
    headers = next(csv.reader(StringIO(response.body.decode("utf-8-sig"))))

    assert all(not re.search(r"[A-Za-z_]", header) for header in headers)


def test_bulk_import_accepts_chinese_headers_and_keeps_legacy_headers_compatible() -> None:
    db = build_session()
    chinese_content = (
        "业务代码,名称,现场调试负责人,备注,是否启用\n"
        "F97,中文模板工厂,现场负责人,中文模板导入,是\n"
    )

    created = import_resource(
        "master.factories",
        chinese_content.encode("utf-8"),
        filename="工厂模板.csv",
        mode="upsert",
        db=db,
    )

    assert created["created"] == 1
    factory = db.query(Factory).filter_by(code="F97").one()
    assert factory.name == "中文模板工厂"
    assert factory.is_active is True
    db.close()


def test_bulk_import_resolves_business_codes_and_export_hides_internal_ids() -> None:
    db = build_session()
    context = build_quality_bulk_context(db)
    content = (
        "业务代码,名称,车型,零件,点位类型,区域,适用质量类型,是否匹配点\n"
        f"PT2,车顶后部,{context['vehicle_code']},PQ1,质量检测,车顶,橘皮,否\n"
    )

    result = import_resource(
        "master.measurement-points",
        content.encode("utf-8"),
        filename="测量点模板.csv",
        mode="upsert",
        db=db,
    )

    assert result["created"] == 1
    point = db.query(MeasurementPoint).filter_by(code="PT2").one()
    assert point.vehicle_model_id == context["vehicle_id"]
    assert point.quality_types == ["ORANGE_PEEL"]

    exported = export_resource("master.measurement-points", "csv", db).body.decode("utf-8-sig")
    header = exported.splitlines()[0]
    assert "系统记录号" not in header
    assert context["vehicle_id"] not in exported
    assert "MQ1 / Model Quality 01" in exported
    assert "PQ1 / Roof Panel" in exported
    db.close()


def test_bulk_import_and_export_use_human_readable_detail_cells() -> None:
    db = build_session()
    content = (
        "code,name,color_type,feature_values,supplier,tds_uri,msds_uri,coa_uri,doe_uri,digital_standard,remark\n"
        "C-HUMAN,示例色漆,BASECOAT,金属感=12.5；闪烁=是,供应商甲,,,,,标准板=STD-01,\n"
    )

    result = import_resource(
        "master.colors",
        content.encode("utf-8"),
        filename="颜色模板.csv",
        mode="upsert",
        db=db,
    )

    assert result["created"] == 1
    color = db.query(Color).filter_by(code="C-HUMAN").one()
    assert color.feature_values == {"金属感": 12.5, "闪烁": True}
    exported = export_resource("master.colors", "csv", db).body.decode("utf-8-sig")
    assert '"{' not in exported
    assert "金属感=12.5；闪烁=是" in exported
    db.close()


def test_quality_column_metadata_maps_chinese_labels_to_internal_keys() -> None:
    columns = describe_bulk_columns("quality.measurements", quality_type="ORANGE_PEEL")
    by_key = {str(column["key"]): column for column in columns}

    assert by_key["body_no"]["label"] == "车号"
    assert by_key["measurement_point_code"]["label"] == "测量点代码"
    assert str(by_key["metric__doi"]["label"]).startswith("橘皮指标：")
    assert "data_no" not in by_key


def test_bulk_import_csv_creates_and_upserts_factory() -> None:
    db = build_session()
    csv_content = "\ufeffid,code,name,site_owner,remark,is_active\n,F99,TEST_FACTORY_99,TEST_OWNER,TEST_REMARK,true\n"

    created = import_resource(
        "master.factories",
        csv_content.encode("utf-8"),
        filename="factories.csv",
        mode="upsert",
        db=db,
    )
    assert created["created"] == 1
    factory = db.query(Factory).filter_by(code="F99").one()
    assert factory.name == "TEST_FACTORY_99"

    update_content = f"id,code,name,site_owner,remark,is_active\n{factory.id},F99,TEST_FACTORY_99_UPDATED,TEST_OWNER_2,TEST_REMARK_UPDATED,false\n"
    updated = import_resource(
        "master.factories",
        update_content.encode("utf-8"),
        filename="factories.csv",
        mode="upsert",
        db=db,
    )
    assert updated["updated"] == 1
    db.refresh(factory)
    assert factory.name == "TEST_FACTORY_99_UPDATED"
    assert factory.is_active is False
    db.close()


def test_bulk_import_reports_row_errors_without_stopping_batch() -> None:
    db = build_session()
    csv_content = "id,code,name,site_owner,remark,is_active\n,F98,TEST_FACTORY_98,TEST_OWNER,,true\n,F,INVALID_FACTORY,TEST_OWNER,,maybe\n"

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
        "id,code,name,site_owner,remark,is_active\n,F97,TEST_FACTORY_97,TEST_OWNER,,true\n".encode(),
        filename="factories.csv",
        mode="upsert",
        db=db,
    )
    response = export_resource("master.factories", "xlsx", db)

    assert response.media_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    assert response.body[:2] == b"PK"
    db.close()


def test_bulk_export_escapes_spreadsheet_formulas() -> None:
    db = build_session()
    create_factory(
        FactoryCreate(code="F96", name="Factory 96", site_owner="=HYPERLINK(\"unsafe\")"),
        db,
    )

    response = export_resource("master.factories", "csv", db)

    assert "'=HYPERLINK" in response.body.decode("utf-8-sig")
    db.close()


def test_bulk_export_escapes_formula_like_rendered_detail_values() -> None:
    db = build_session()
    db.add(
        Color(
            code="C-FORMULA",
            name="公式防护测试",
            color_type="BASECOAT",
            feature_values={"=危险字段": "普通值"},
        )
    )
    db.commit()

    response = export_resource("master.colors", "csv", db)

    assert "'=危险字段=普通值" in response.body.decode("utf-8-sig")
    db.close()


def test_bulk_import_does_not_turn_blank_rows_into_default_only_records() -> None:
    db = build_session()
    context = build_quality_bulk_context(db)
    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-BLANK",
            name="空行测试程序",
            factory_id=context["factory_id"],
            process_stage="BASECOAT_1",
            station_code="BC1",
            station_name="色漆一站",
        ),
        db,
    )
    result = import_resource(
        "process.program-versions",
        (
            "id,version,status,source_type,is_master_sample,vehicle_model_ids,color_ids\n"
            ",,,,,,\n"
        ).encode("utf-8"),
        filename="空行.csv",
        mode="upsert",
        default_values={"spray_program_id": program.id},
        db=db,
    )

    assert result["skipped"] == 1
    assert result["created"] == 0
    assert result["failed"] == 0
    db.close()


def test_bulk_supports_program_applicability_and_body_map_layouts() -> None:
    db = build_session()
    context = build_quality_bulk_context(db)
    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-LAYOUT",
            name="Layout program",
            factory_id=context["factory_id"],
            process_stage="BASECOAT_1",
            station_code="BC1",
            station_name="色漆一站",
        ),
        db,
    )
    version = create_program_version(
        program.id,
        SprayProgramVersionCreate(version="V1", vehicle_model_ids=[], color_ids=[]),
        db,
    )

    model_result = import_resource(
        "process.program-vehicle-models",
        f"id,program_version_id,vehicle_model_id\n,{version.id},{context['vehicle_id']}\n".encode(),
        filename="program-models.csv",
        mode="upsert",
        db=db,
    )
    color_result = import_resource(
        "process.program-colors",
        f"id,program_version_id,color_id\n,{version.id},{context['color_id']}\n".encode(),
        filename="program-colors.csv",
        mode="upsert",
        db=db,
    )
    layout_result = import_resource(
        "quality.body-map-layouts",
        (
            "id,measurement_point_id,body_view,layout_x,layout_y,grid_col,grid_row\n"
            f",{context['point_id']},RIGHT,0.25,0.60,4,8\n"
        ).encode(),
        filename="body-map-layouts.csv",
        mode="upsert",
        db=db,
    )
    layout_3d_result = import_resource(
        "quality.body-map-3d-layouts",
        (
            "id,measurement_point_id,pos_x,pos_y,pos_z,normal_x,normal_y,normal_z,model_asset_key,project_to_2d\n"
            f",{context['point_id']},1.0,2.0,3.0,0.0,1.0,0.0,default,false\n"
        ).encode(),
        filename="body-map-3d-layouts.csv",
        mode="upsert",
        db=db,
    )

    assert model_result["created"] == 1
    assert color_result["created"] == 1
    assert layout_result["created"] == 1
    assert layout_3d_result["created"] == 1
    assert db.query(ProgramVehicleModel).count() == 1
    assert db.query(ProgramColor).count() == 1
    assert db.query(MeasurementPointLayout).count() == 1
    layout_3d = db.query(MeasurementPoint3DLayout).one()
    layout_3d.status = "INACTIVE"
    db.commit()

    reactivated = import_resource(
        "quality.body-map-3d-layouts",
        (
            "id,measurement_point_id,pos_x,pos_y,pos_z,normal_x,normal_y,normal_z,model_asset_key,project_to_2d\n"
            f",{context['point_id']},1.5,2.5,3.5,0.0,1.0,0.0,default,false\n"
        ).encode(),
        filename="body-map-3d-layouts.csv",
        mode="upsert",
        db=db,
    )

    assert reactivated["updated"] == 1
    assert db.query(MeasurementPoint3DLayout).count() == 1
    db.refresh(layout_3d)
    assert layout_3d.status == "ACTIVE"
    assert layout_3d.pos_x == 1.5
    assert layout_3d.pos_y == 2.5
    assert layout_3d.pos_z == 3.5
    db.close()


def test_bulk_import_uses_default_values_for_program_versions() -> None:
    db = build_session()
    factory = create_factory(
        FactoryCreate(code="F01", name="Factory 01", site_owner="Owner"),
        db,
    )
    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-01",
            name="Program 01",
            factory_id=factory.id,
            process_stage="CLEARCOAT_2",
            station_code="ST-01",
            station_name="Station 01",
        ),
        db,
    )
    csv_content = "id,version,status,source_type,is_master_sample,vehicle_model_ids,color_ids\n,V1,DRAFT,MANUAL,false,,\n"

    result = import_resource(
        "process.program-versions",
        csv_content.encode("utf-8"),
        filename="program-versions.csv",
        mode="upsert",
        default_values={"spray_program_id": program.id},
        db=db,
    )

    assert result["created"] == 1
    version = db.query(SprayProgramVersion).filter_by(spray_program_id=program.id, version="V1").one()
    assert version.source_type == "MANUAL"
    db.close()


def test_bulk_import_uses_default_values_for_brushes() -> None:
    db = build_session()
    factory = create_factory(
        FactoryCreate(code="F02", name="Factory 02", site_owner="Owner"),
        db,
    )
    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-02",
            name="Program 02",
            factory_id=factory.id,
            process_stage="CLEARCOAT_2",
            station_code="ST-02",
            station_name="Station 02",
        ),
        db,
    )
    version = create_program_version(program.id, SprayProgramVersionCreate(version="V1"), db)
    csv_content = "id,brush_no,brush_table_no,spray_position,part_id,remark\n,B01,BT01,roof_front,,bulk brush\n"

    result = import_resource(
        "process.brushes",
        csv_content.encode("utf-8"),
        filename="brushes.csv",
        mode="upsert",
        default_values={"program_version_id": version.id},
        db=db,
    )

    assert result["created"] == 1
    brush = db.query(Brush).filter_by(program_version_id=version.id, brush_no="B01").one()
    assert brush.brush_table_no == "BT01"
    db.close()


def test_bulk_import_uses_default_values_for_brush_parameters() -> None:
    db = build_session()
    factory = create_factory(
        FactoryCreate(code="F03", name="Factory 03", site_owner="Owner"),
        db,
    )
    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-03",
            name="Program 03",
            factory_id=factory.id,
            process_stage="CLEARCOAT_2",
            station_code="ST-03",
            station_name="Station 03",
        ),
        db,
    )
    version = create_program_version(program.id, SprayProgramVersionCreate(version="V1"), db)
    brush = create_brush(version.id, BrushCreate(brush_no="B01", brush_table_no="BT01"), db)
    csv_content = "id,parameter_definition_id,parameter_code,parameter_name,configured_value,unit,soft_min,soft_max,hard_min,hard_max,is_recommendable\n,,clearcoat_2_flow,Clearcoat Flow,320,ml/min,280,360,,,true\n"

    result = import_resource(
        "process.brush-parameters",
        csv_content.encode("utf-8"),
        filename="brush-parameters.csv",
        mode="upsert",
        default_values={"brush_id": brush.id},
        db=db,
    )

    assert result["created"] == 1
    parameter = db.query(BrushParameter).filter_by(brush_id=brush.id, parameter_code="clearcoat_2_flow").one()
    assert parameter.configured_value == 320
    db.close()


def test_bulk_import_uses_default_values_for_brush_contributions() -> None:
    db = build_session()
    factory = create_factory(
        FactoryCreate(code="F04", name="Factory 04", site_owner="Owner"),
        db,
    )
    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-04",
            name="Program 04",
            factory_id=factory.id,
            process_stage="CLEARCOAT_2",
            station_code="ST-04",
            station_name="Station 04",
        ),
        db,
    )
    version = create_program_version(program.id, SprayProgramVersionCreate(version="V1"), db)
    brush = create_brush(version.id, BrushCreate(brush_no="B01", brush_table_no="BT01"), db)
    model = create_vehicle_model(VehicleModelCreate(code="VM-04", name="Vehicle 04"), db)
    part = create_part(PartCreate(code="PART-04", name="Roof Panel"), db)
    point = create_measurement_point(
        MeasurementPointCreate(
            code="P01",
            name="Point 01",
            vehicle_model_id=model.id,
            part_id=part.id,
            point_type="QUALITY",
            region="Roof",
            quality_types=["ORANGE_PEEL"],
        ),
        db,
    )
    csv_content = f"id,measurement_point_id,overlap_ratio,contribution_weight,source,version,is_approved\n,{point.id},0.6,0.6,EXPERT,1.0,true\n"

    result = import_resource(
        "process.brush-contributions",
        csv_content.encode("utf-8"),
        filename="brush-contributions.csv",
        mode="upsert",
        default_values={"brush_id": brush.id},
        db=db,
    )

    assert result["created"] == 1
    contribution = db.query(BrushPointContribution).filter_by(brush_id=brush.id, measurement_point_id=point.id).one()
    assert contribution.contribution_weight == 0.6
    db.close()


def test_brush_contribution_template_prefills_parent_lineage() -> None:
    db = build_session()
    factory = create_factory(
        FactoryCreate(code="F-BC", name="Brush Contrib Factory", site_owner="Owner"),
        db,
    )
    model = create_vehicle_model(VehicleModelCreate(code="VM-BC", name="Brush Contrib Model"), db)
    part = create_part(PartCreate(code="PART-BC", name="Hood"), db)
    point = create_measurement_point(
        MeasurementPointCreate(
            code="PT-BC",
            name="Hood Center",
            vehicle_model_id=model.id,
            part_id=part.id,
            point_type="QUALITY",
            region="Hood",
            quality_types=["ORANGE_PEEL"],
        ),
        db,
    )
    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-BC",
            name="Brush Contrib Program",
            factory_id=factory.id,
            process_stage="CLEARCOAT_1",
            station_code="ST-BC",
            station_name="Station BC",
        ),
        db,
    )
    version = create_program_version(
        program.id,
        SprayProgramVersionCreate(version="V2", vehicle_model_ids=[model.id]),
        db,
    )
    brush = create_brush(
        version.id,
        BrushCreate(brush_no="B12", brush_table_no="BT12", part_id=part.id),
        db,
    )

    response = render_template(
        "process.brush-contributions",
        "csv",
        db=db,
        brush_id=brush.id,
    )
    content = response.body.decode("utf-8-sig")
    header = content.splitlines()[0]

    assert "工厂代码" in header
    assert "喷涂程序代码" in header
    assert "程序版本号" in header
    assert "刷子号" in header
    assert "车型代码" in header
    assert "测量点代码" in header
    assert "F-BC" in content
    assert "PRG-BC" in content
    assert "V2" in content
    assert "B12" in content
    assert "VM-BC" in content
    assert "PT-BC" in content
    assert "Hood Center" in content
    assert point.id not in content
    assert brush.id not in content
    db.close()


def test_brush_contribution_bulk_import_resolves_business_codes() -> None:
    db = build_session()
    factory = create_factory(
        FactoryCreate(code="F-BC2", name="Factory BC2", site_owner="Owner"),
        db,
    )
    model = create_vehicle_model(VehicleModelCreate(code="VM-BC2", name="Model BC2"), db)
    part = create_part(PartCreate(code="PART-BC2", name="Door"), db)
    point = create_measurement_point(
        MeasurementPointCreate(
            code="PT-BC2",
            name="Door Outer",
            vehicle_model_id=model.id,
            part_id=part.id,
            point_type="QUALITY",
            region="Door",
            quality_types=["THICKNESS"],
        ),
        db,
    )
    program = create_spray_program(
        SprayProgramCreate(
            program_code="PRG-BC2",
            name="Program BC2",
            factory_id=factory.id,
            process_stage="BASECOAT_1",
            station_code="ST-BC2",
            station_name="Station BC2",
        ),
        db,
    )
    version = create_program_version(
        program.id,
        SprayProgramVersionCreate(version="V1", vehicle_model_ids=[model.id]),
        db,
    )
    brush = create_brush(version.id, BrushCreate(brush_no="B20", brush_table_no="BT20"), db)
    csv_content = (
        "factory_code,program_code,program_version,brush_no,vehicle_model_code,measurement_point_code,"
        "overlap_ratio,contribution_weight,source,version,is_approved\n"
        "F-BC2,PRG-BC2,V1,B20,VM-BC2,PT-BC2,0.4,0.35,EXPERT,1.0,false\n"
    )

    result = import_resource(
        "process.brush-contributions",
        csv_content.encode("utf-8"),
        filename="brush-contributions-codes.csv",
        mode="upsert",
        db=db,
    )

    assert result["created"] == 1
    assert result["failed"] == 0
    contribution = db.query(BrushPointContribution).filter_by(
        brush_id=brush.id,
        measurement_point_id=point.id,
    ).one()
    assert contribution.overlap_ratio == 0.4
    assert contribution.contribution_weight == 0.35
    db.close()


def test_quality_measurement_template_uses_flat_metric_columns() -> None:
    db = build_session()
    build_quality_bulk_context(db)

    response = render_template("quality.measurements", "csv", db=db, quality_type="ORANGE_PEEL")
    content = response.body.decode("utf-8-sig")

    header = content.splitlines()[0]
    assert "测量编组代码" in header
    assert "测量点代码" in header
    assert "车号" in header
    assert "工厂代码" in header
    assert "颜色代码" in header
    assert "DOI" in header
    assert "metrics" not in header
    assert "repeat_readings" not in header
    assert "质量数据编号" not in header
    assert "G1" in content
    assert "PT1" in content
    db.close()


def test_quality_measurement_bulk_import_transforms_flat_metric_columns() -> None:
    db = build_session()
    context = build_quality_bulk_context(db)
    csv_content = (
        "data_no,production_run_no,measurement_group_code,measurement_point_code,quality_type,measured_at,metric__doi\n"
        f"QM-BULK-1,{context['run_no']},{context['group_code']},{context['point_code']},ORANGE_PEEL,2026-07-08T08:00:00+00:00,88.2\n"
    )

    result = import_resource(
        "quality.measurements",
        csv_content.encode("utf-8"),
        filename="quality-measurements.csv",
        mode="upsert",
        db=db,
    )

    assert result["created"] == 1
    measurement = db.query(QualityMeasurement).filter_by(data_no="QM-BULK-1").one()
    metric = db.query(QualityMetricValue).filter_by(measurement_id=measurement.id, metric_code="doi").one()
    assert measurement.measurement_group_id == context["group_id"]
    assert measurement.measurement_point_id == context["point_id"]
    assert metric.raw_value == 88.2
    db.close()


def test_quality_measurement_bulk_import_auto_generates_data_no() -> None:
    db = build_session()
    context = build_quality_bulk_context(db)
    csv_content = (
        "production_run_no,body_no,factory_code,measurement_group_code,measurement_point_code,vehicle_model_code,quality_type,color_code,measured_at,metric__doi\n"
        f",BODY-AUTO-DN,{context['factory_code']},{context['group_code']},{context['point_code']},{context['vehicle_code']},ORANGE_PEEL,{context['color_code']},2026-07-08T08:00:00+00:00,90.1\n"
    )

    result = import_resource(
        "quality.measurements",
        csv_content.encode("utf-8"),
        filename="quality-measurements-auto-data-no.csv",
        mode="upsert",
        db=db,
    )

    assert result["created"] == 1
    expected = f"QM-BODY-AUTO-DN-{context['point_code']}-OP"
    measurement = db.query(QualityMeasurement).filter_by(data_no=expected).one()
    run = db.query(ProductionRun).filter_by(run_no="RUN-BODY-AUTO-DN").one()
    assert measurement.production_run_id == run.id
    db.close()


def test_quality_measurement_template_prefills_production_context() -> None:
    db = build_session()
    context = build_quality_bulk_context(db)

    response = render_template(
        "quality.measurements",
        "csv",
        db=db,
        quality_type="ORANGE_PEEL",
        factory_code=context["factory_code"],
        color_code=context["color_code"],
        vehicle_model_code=context["vehicle_code"],
        shift="A",
    )
    content = response.body.decode("utf-8-sig")
    assert context["factory_code"] in content
    assert context["color_code"] in content
    assert ",A," in content or content.endswith(",A")
    db.close()


def test_quality_measurement_bulk_import_creates_production_run_with_body_no() -> None:
    db = build_session()
    context = build_quality_bulk_context(db)
    csv_content = (
        "data_no,production_run_no,body_no,factory_code,measurement_group_code,measurement_point_code,vehicle_model_code,quality_type,color_code,shift,production_started_at,measured_at,metric__doi\n"
        f"QM-BULK-2,RUN-QUALITY-NEW,BODY-9001,{context['factory_code']},{context['group_code']},{context['point_code']},{context['vehicle_code']},ORANGE_PEEL,{context['color_code']},B,2026-07-08T07:30:00+00:00,2026-07-08T08:00:00+00:00,91.5\n"
    )

    result = import_resource(
        "quality.measurements",
        csv_content.encode("utf-8"),
        filename="quality-measurements-with-run.csv",
        mode="upsert",
        db=db,
    )

    assert result["created"] == 1
    run = db.query(ProductionRun).filter_by(run_no="RUN-QUALITY-NEW").one()
    measurement = db.query(QualityMeasurement).filter_by(data_no="QM-BULK-2").one()
    assert run.body_no == "BODY-9001"
    assert run.shift == "B"
    assert measurement.production_run_id == run.id
    db.close()


def test_quality_measurement_bulk_import_auto_generates_run_no_from_body() -> None:
    db = build_session()
    context = build_quality_bulk_context(db)
    csv_content = (
        "data_no,production_run_no,body_no,factory_code,measurement_group_code,measurement_point_code,vehicle_model_code,quality_type,color_code,measured_at,metric__doi\n"
        f"QM-BULK-3,,BODY-AUTO-1,{context['factory_code']},{context['group_code']},{context['point_code']},{context['vehicle_code']},ORANGE_PEEL,{context['color_code']},2026-07-08T08:00:00+00:00,90.1\n"
    )

    result = import_resource(
        "quality.measurements",
        csv_content.encode("utf-8"),
        filename="quality-measurements-auto-run.csv",
        mode="upsert",
        db=db,
    )

    assert result["created"] == 1
    run = db.query(ProductionRun).filter_by(run_no="RUN-BODY-AUTO-1").one()
    measurement = db.query(QualityMeasurement).filter_by(data_no="QM-BULK-3").one()
    assert run.body_no == "BODY-AUTO-1"
    assert measurement.production_run_id == run.id
    db.close()
