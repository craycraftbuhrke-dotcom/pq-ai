from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

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
    Factory,
    ProductionRun,
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
from app.services.bulk_io import export_resource, import_resource, render_template
from tests.schema_guard import create_transient_test_schema


def build_session() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    create_transient_test_schema(engine)
    return Session(engine)


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
        "factory_code": factory.code,
        "group_id": group.id,
        "group_code": group.code,
        "color_code": color.code,
        "point_id": point.id,
        "point_code": point.code,
        "run_id": run.id,
        "run_no": run.run_no,
        "vehicle_code": vehicle.code,
    }


def test_bulk_template_contains_import_headers() -> None:
    response = render_template("master.factories", "csv")
    content = response.body.decode("utf-8-sig")

    assert "id,code,name,site_owner,remark,is_active" in content


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

    assert "factory_code" in header
    assert "program_code" in header
    assert "program_version" in header
    assert "brush_no" in header
    assert "vehicle_model_code" in header
    assert "measurement_point_code" in header
    assert "F-BC" in content
    assert "PRG-BC" in content
    assert "V2" in content
    assert "B12" in content
    assert "VM-BC" in content
    assert "PT-BC" in content
    assert "Hood Center" in content
    assert point.id in content
    assert brush.id in content
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

    assert "measurement_group_code" in content
    assert "measurement_point_code" in content
    assert "body_no" in content
    assert "factory_code" in content
    assert "color_code" in content
    assert "metric__doi" in content
    assert "metrics" not in content
    assert "repeat_readings" not in content
    assert "data_no" not in content.splitlines()[0]
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
