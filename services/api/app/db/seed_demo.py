from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import PERMISSION_CATALOG, ROLE_CATALOG, hash_api_key
from app.db.session import SessionLocal
from app.domain.parameter_catalog import PARAMETER_CATALOG
from app.domain.quality_metric_catalog import QUALITY_METRIC_CATALOG
from app.domain.scope_policy import (
    CURRENT_FEATURE_SET_VERSION,
    approved_numeric_values,
)
from app.models.domain import (
    ActualParameter,
    ApiKey,
    AppUser,
    Brush,
    BrushParameter,
    BrushPointContribution,
    Color,
    Factory,
    FactoryVehicleModel,
    IntegrationEndpoint,
    MaterialBatch,
    MeasurementGroup,
    MeasurementGroupPoint,
    MeasurementPoint,
    ModelVersion,
    ParameterDefinition,
    Part,
    PointFeatureSnapshot,
    ProductionRun,
    ProductionStageRun,
    ProgramColor,
    ProgramVehicleModel,
    QualityMeasurement,
    QualityMetricDefinition,
    QualityMetricValue,
    QualityStandard,
    Role,
    RolePermission,
    SprayProgram,
    SprayProgramVersion,
    VehicleModel,
    VehicleModelColor,
    UserRole,
    Permission,
)
from app.schemas.modeling import ModelTrainingRequest
from app.services.feature_aggregation import build_point_feature_snapshot
from app.services.modeling import train_model


def _seed_catalogs(db: Session) -> None:
    parameter_codes = set(db.scalars(select(ParameterDefinition.code)))
    db.add_all(
        [
            ParameterDefinition(**definition)
            for definition in PARAMETER_CATALOG
            if definition["code"] not in parameter_codes
        ]
    )
    metric_keys = set(
        db.execute(
            select(QualityMetricDefinition.quality_type, QualityMetricDefinition.code)
        ).all()
    )
    db.add_all(
        [
            QualityMetricDefinition(**definition)
            for definition in QUALITY_METRIC_CATALOG
            if (definition["quality_type"], definition["code"]) not in metric_keys
        ]
    )
    db.flush()


def _seed_security(db: Session) -> AppUser:
    permissions = {
        permission.code: permission for permission in db.scalars(select(Permission))
    }
    for code, name in PERMISSION_CATALOG.items():
        if code not in permissions:
            permission = Permission(code=code, name=name)
            db.add(permission)
            db.flush()
            permissions[code] = permission

    roles = {role.code: role for role in db.scalars(select(Role))}
    for role_code, permission_codes in ROLE_CATALOG.items():
        role = roles.get(role_code)
        if not role:
            role = Role(code=role_code, name=role_code.replace("_", " ").title())
            db.add(role)
            db.flush()
            roles[role_code] = role
        existing_permission_ids = set(
            db.scalars(
                select(RolePermission.permission_id).where(RolePermission.role_id == role.id)
            )
        )
        db.add_all(
            [
                RolePermission(role_id=role.id, permission_id=permissions[code].id)
                for code in permission_codes
                if permissions[code].id not in existing_permission_ids
            ]
        )

    admin = db.scalar(select(AppUser).where(AppUser.username == "chen.gong"))
    if not admin:
        admin = AppUser(
            username="chen.gong",
            display_name="陈工",
            email="chen.gong@pq-ai.local",
            department="涂装工艺",
        )
        db.add(admin)
        db.flush()
    admin_role = roles["ADMIN"]
    if not db.scalar(
        select(UserRole).where(UserRole.user_id == admin.id, UserRole.role_id == admin_role.id)
    ):
        db.add(UserRole(user_id=admin.id, role_id=admin_role.id))
    bootstrap_hash = hash_api_key(settings.bootstrap_api_key)
    if not db.scalar(select(ApiKey).where(ApiKey.key_hash == bootstrap_hash)):
        db.add(
            ApiKey(
                user_id=admin.id,
                name="演示管理员服务密钥",
                key_prefix=settings.bootstrap_api_key[:12],
                key_hash=bootstrap_hash,
            )
        )
    db.flush()
    return admin


def _seed_integration_endpoints(db: Session) -> None:
    endpoint_specs = (
        ("MES-DEMO", "MES 生产事件", "MES"),
        ("QMS-DEMO", "QMS 质量测量", "QMS"),
        ("ROBOT-DEMO", "机器人与 PLC 实绩", "ROBOT"),
        ("MATERIAL-DEMO", "材料批次与 COA", "MATERIAL"),
    )
    existing_codes = set(db.scalars(select(IntegrationEndpoint.code)))
    db.add_all(
        [
            IntegrationEndpoint(
                code=code,
                name=name,
                system_type=system_type,
                direction="INBOUND",
                auth_type="API_KEY",
                config={"mode": "demo", "secrets_managed_externally": True},
            )
            for code, name, system_type in endpoint_specs
            if code not in existing_codes
        ]
    )
    db.flush()


def _upgrade_existing_demo_scope_data(db: Session) -> ModelVersion | None:
    demo_snapshots = list(
        db.scalars(
            select(PointFeatureSnapshot)
            .join(ProductionRun, ProductionRun.id == PointFeatureSnapshot.production_run_id)
            .where(
                PointFeatureSnapshot.feature_set_version == "point-features-v1",
                (
                    (ProductionRun.run_no == "RUN-20260610-001")
                    | ProductionRun.run_no.like("DEMO-TRAIN-RUN-%")
                ),
            )
        )
    )
    for snapshot in demo_snapshots:
        exists = db.scalar(
            select(PointFeatureSnapshot).where(
                PointFeatureSnapshot.production_run_id == snapshot.production_run_id,
                PointFeatureSnapshot.measurement_point_id == snapshot.measurement_point_id,
                PointFeatureSnapshot.feature_set_version == CURRENT_FEATURE_SET_VERSION,
            )
        )
        if exists:
            continue
        feature_values = approved_numeric_values(snapshot.feature_values)
        if not feature_values:
            continue
        db.add(
            PointFeatureSnapshot(
                production_run_id=snapshot.production_run_id,
                measurement_point_id=snapshot.measurement_point_id,
                feature_set_version=CURRENT_FEATURE_SET_VERSION,
                feature_values=feature_values,
                completeness_score=snapshot.completeness_score,
                generated_at=datetime.now(UTC),
            )
        )
    db.commit()

    model = db.scalar(
        select(ModelVersion).where(
            ModelVersion.model_code == "DEMO-DOI-BASELINE",
            ModelVersion.version == "2.0-scope",
        )
    )
    if model:
        return model

    scoped_snapshot_count = len(
        list(
            db.scalars(
                select(PointFeatureSnapshot)
                .join(ProductionRun, ProductionRun.id == PointFeatureSnapshot.production_run_id)
                .where(
                    PointFeatureSnapshot.feature_set_version == CURRENT_FEATURE_SET_VERSION,
                    (
                        (ProductionRun.run_no == "RUN-20260610-001")
                        | ProductionRun.run_no.like("DEMO-TRAIN-RUN-%")
                    ),
                )
            )
        )
    )
    if scoped_snapshot_count < 5:
        return None
    return train_model(
        db,
        ModelTrainingRequest(
            model_code="DEMO-DOI-BASELINE",
            version="2.0-scope",
            target_metric="doi",
            feature_set_version=CURRENT_FEATURE_SET_VERSION,
            min_samples=5,
            ridge_lambda=0.1,
        ),
    )


def seed_demo(db: Session) -> dict:
    _seed_catalogs(db)
    admin = _seed_security(db)
    _seed_integration_endpoints(db)
    demo_boundaries = {
        "clearcoat_2_spray_flow": (280.0, 360.0),
        "clearcoat_2_outer_air": (360.0, 440.0),
        "clearcoat_2_bell_speed": (40000.0, 52000.0),
    }
    for code, (hard_min, hard_max) in demo_boundaries.items():
        definition = db.scalar(
            select(ParameterDefinition).where(ParameterDefinition.code == code)
        )
        definition.hard_min = hard_min
        definition.hard_max = hard_max
        definition.is_recommendable = True
    existing_factory = db.scalar(select(Factory).where(Factory.code == "M9"))
    if existing_factory:
        model = _upgrade_existing_demo_scope_data(db)
        db.commit()
        return {
            "status": "already_seeded",
            "factory_id": existing_factory.id,
            "model_version_id": model.id if model else None,
            "admin_user_id": admin.id,
        }

    now = datetime.now(UTC)
    factory = Factory(code="M9", name="M9 总装涂装工厂", site_owner="陈工")
    vehicle_model = VehicleModel(code="MX11", name="MX11 车型")
    basecoat_color = Color(
        code="C-01",
        name="珍珠白",
        color_type="BASECOAT",
        supplier="供应商 A",
        feature_values={"l": 94.2, "a": -0.4, "b": 1.8},
    )
    midcoat_color = Color(
        code="MID-GRAY",
        name="灰中涂",
        color_type="MIDCOAT",
        supplier="供应商 B",
    )
    parts = {
        code: Part(code=code, name=name, material="镀锌钢板", region=region)
        for code, name, region in (
            ("ROOF", "车顶", "水平面"),
            ("HOOD", "发动机罩", "水平面"),
            ("LEFT_DOOR", "左前门", "垂直面"),
            ("RIGHT_DOOR", "右后门", "垂直面"),
        )
    }
    db.add_all([factory, vehicle_model, basecoat_color, midcoat_color, *parts.values()])
    db.flush()
    db.add_all(
        [
            FactoryVehicleModel(factory_id=factory.id, vehicle_model_id=vehicle_model.id),
            VehicleModelColor(vehicle_model_id=vehicle_model.id, color_id=basecoat_color.id),
            VehicleModelColor(vehicle_model_id=vehicle_model.id, color_id=midcoat_color.id),
        ]
    )

    point_specs = (
        ("P-ROOF-03", "车顶中部 03", "ROOF", ["ORANGE_PEEL"]),
        ("P-HOOD-06", "发动机罩 06", "HOOD", ["THICKNESS"]),
        ("P-LD-02", "左前门 02", "LEFT_DOOR", ["COLOR_DIFFERENCE"]),
    )
    points: dict[str, MeasurementPoint] = {}
    groups: dict[str, MeasurementGroup] = {}
    for sequence, (code, name, part_code, quality_types) in enumerate(point_specs, start=1):
        point = MeasurementPoint(
            code=code,
            name=name,
            vehicle_model_id=vehicle_model.id,
            part_id=parts[part_code].id,
            region=parts[part_code].region,
            quality_types=quality_types,
            is_match_point=quality_types == ["COLOR_DIFFERENCE"],
        )
        group = MeasurementGroup(
            code=f"G-{quality_types[0]}",
            name=f"{quality_types[0]} 测量编组",
            vehicle_model_id=vehicle_model.id,
            quality_type=quality_types[0],
            expected_point_count=1,
        )
        db.add_all([point, group])
        db.flush()
        db.add(
            MeasurementGroupPoint(
                measurement_group_id=group.id,
                measurement_point_id=point.id,
                sequence_no=sequence,
            )
        )
        points[code] = point
        groups[quality_types[0]] = group

    materials = {
        "MIDCOAT": MaterialBatch(
            batch_no="MID-20260610-01",
            material_code="MID-01",
            material_name="灰中涂",
            material_type="MIDCOAT",
            supplier="供应商 B",
            viscosity=24.0,
            solid_ratio=0.52,
        ),
        "BASECOAT": MaterialBatch(
            batch_no="BC-20260610-01",
            material_code="BC-01",
            material_name="珍珠白色漆",
            material_type="BASECOAT",
            supplier="供应商 A",
            viscosity=19.5,
            solid_ratio=0.38,
        ),
        "CLEARCOAT": MaterialBatch(
            batch_no="CC-20260610-01",
            material_code="CC-01",
            material_name="高固清漆",
            material_type="CLEARCOAT",
            supplier="供应商 C",
            viscosity=22.5,
            solid_ratio=0.48,
            coa_values={"density": 1.03},
        ),
    }
    db.add_all(materials.values())
    db.flush()

    run = ProductionRun(
        run_no="RUN-20260610-001",
        body_no="BODY-000126",
        factory_id=factory.id,
        vehicle_model_id=vehicle_model.id,
        color_id=basecoat_color.id,
        shift="白班",
        started_at=now - timedelta(minutes=35),
        completed_at=now - timedelta(minutes=5),
        context_values={"source_batch_sequence": 1},
    )
    db.add(run)
    db.flush()

    stage_specs = (
        ("MIDCOAT_EXT", "midcoat", "P1F1A1", "中涂外喷", "MIDCOAT", 342.0, 45000.0),
        ("BASECOAT_1", "basecoat_1", "P1B1A1", "色漆一站", "BASECOAT", 286.0, 48000.0),
        ("BASECOAT_2", "basecoat_2", "P1B1A2", "色漆二站", "BASECOAT", 212.0, 50000.0),
        ("CLEARCOAT_1", "clearcoat_1", "P1C1A1", "清漆一站", "CLEARCOAT", 302.0, 47000.0),
        ("CLEARCOAT_2", "clearcoat_2", "P1C1A2", "清漆二站", "CLEARCOAT", 315.0, 46000.0),
    )
    parameter_definitions = {
        definition.code: definition for definition in db.scalars(select(ParameterDefinition))
    }
    for index, (
        stage_code,
        prefix,
        station_code,
        stage_name,
        material_type,
        flow,
        rpm,
    ) in enumerate(stage_specs, start=1):
        program = SprayProgram(
            program_code=f"PRG-M9-MX11-{index}",
            name=stage_name,
            factory_id=factory.id,
            process_stage=stage_code,
            station_code=station_code,
            station_name=stage_name,
            robot_model="Dürr EcoRP E043i",
        )
        db.add(program)
        db.flush()
        version = SprayProgramVersion(
            spray_program_id=program.id,
            version="V1.0",
            status="ACTIVE",
            source_type="MASTER_SAMPLE",
            is_master_sample=True,
            approved_by="陈工",
            approved_at=now - timedelta(days=1),
            effective_from=now - timedelta(days=1),
        )
        db.add(version)
        db.flush()
        db.add_all(
            [
                ProgramVehicleModel(
                    program_version_id=version.id, vehicle_model_id=vehicle_model.id
                ),
                ProgramColor(program_version_id=version.id, color_id=basecoat_color.id),
            ]
        )
        brush = Brush(
            program_version_id=version.id,
            brush_no=f"B-{index:03d}",
            brush_table_no=f"BT-{stage_code}",
            spray_position="车身外表面",
            part_id=parts["ROOF"].id,
        )
        db.add(brush)
        db.flush()
        values = {
            f"{prefix}_spray_flow": flow,
            f"{prefix}_bell_speed": rpm,
            f"{prefix}_outer_air": 390.0 + index * 4,
            f"{prefix}_inner_air": 210.0 + index * 3,
            f"{prefix}_voltage": 72.0,
        }
        for parameter_code, configured_value in values.items():
            definition = parameter_definitions[parameter_code]
            db.add(
                BrushParameter(
                    brush_id=brush.id,
                    parameter_definition_id=definition.id,
                    parameter_code=parameter_code,
                    parameter_name=definition.name,
                    configured_value=configured_value,
                    unit=definition.unit,
                    is_recommendable=False,
                )
            )
        for point in points.values():
            db.add(
                BrushPointContribution(
                    brush_id=brush.id,
                    measurement_point_id=point.id,
                    overlap_ratio=1.0,
                    contribution_weight=1.0,
                    source="MASTER_SAMPLE",
                    version="1.0",
                    is_approved=True,
                )
            )
        stage_run = ProductionStageRun(
            production_run_id=run.id,
            process_stage=stage_code,
            program_version_id=version.id,
            material_batch_id=materials[material_type].id,
            actual_parameters={},
        )
        db.add(stage_run)
        db.flush()
        db.add(
            ActualParameter(
                production_stage_run_id=stage_run.id,
                brush_id=brush.id,
                parameter_definition_id=parameter_definitions[f"{prefix}_spray_flow"].id,
                parameter_code=f"{prefix}_spray_flow",
                actual_value=flow + 2.0,
                unit="ml/min",
                sampled_at=now - timedelta(minutes=30 - index),
                source_system="ROBOT_PLC",
            )
        )

    measurement_specs = (
        ("QM-260610-0001", "P-ROOF-03", "ORANGE_PEEL", {"doi": ("DOI", 78.2, None)}),
        (
            "QM-260610-0002",
            "P-HOOD-06",
            "THICKNESS",
            {"thickness_total": ("总膜厚", 116.8, "μm")},
        ),
        ("QM-260610-0003", "P-LD-02", "COLOR_DIFFERENCE", {"de45": ("dE45", 0.71, None)}),
    )
    for index, (data_no, point_code, quality_type, metrics) in enumerate(
        measurement_specs, start=1
    ):
        point = points[point_code]
        measurement = QualityMeasurement(
            data_no=data_no,
            production_run_id=run.id,
            measurement_group_id=groups[quality_type].id,
            measurement_point_id=point.id,
            quality_type=quality_type,
            data_type="TEST",
            measured_at=now - timedelta(minutes=10 - index),
            measured_by="质量工程师",
            status_score=92.0,
        )
        db.add(measurement)
        db.flush()
        db.add_all(
            [
                QualityMetricValue(
                    measurement_id=measurement.id,
                    metric_code=metric_code,
                    metric_name=metric_name,
                    raw_value=value,
                    unit=unit,
                )
                for metric_code, (metric_name, value, unit) in metrics.items()
            ]
        )

    db.add_all(
        [
            QualityStandard(
                standard_no="STD-DOI",
                version="1.0",
                quality_type="ORANGE_PEEL",
                metric_code="doi",
                measurement_point_id=points["P-ROOF-03"].id,
                min_value=82.0,
            ),
            QualityStandard(
                standard_no="STD-THICKNESS",
                version="1.0",
                quality_type="THICKNESS",
                metric_code="thickness_total",
                vehicle_model_id=vehicle_model.id,
                min_value=120.0,
                max_value=145.0,
                unit="μm",
            ),
            QualityStandard(
                standard_no="STD-DE45",
                version="1.0",
                quality_type="COLOR_DIFFERENCE",
                metric_code="de45",
                color_id=basecoat_color.id,
                max_value=0.8,
            ),
        ]
    )
    db.commit()
    snapshot = build_point_feature_snapshot(db, run.id, points["P-ROOF-03"].id)
    base_features = snapshot["feature_values"]
    flow_key = "clearcoat_2.clearcoat_2_spray_flow"
    outer_air_key = "clearcoat_2.clearcoat_2_outer_air"
    for index in range(1, 8):
        historical_run = ProductionRun(
            run_no=f"DEMO-TRAIN-RUN-{index:02d}",
            body_no=f"DEMO-BODY-{index:02d}",
            factory_id=factory.id,
            vehicle_model_id=vehicle_model.id,
            color_id=basecoat_color.id,
            shift="训练演示",
            started_at=now - timedelta(days=index),
            completed_at=now - timedelta(days=index, minutes=-30),
            context_values={"is_demo_training": 1.0},
        )
        db.add(historical_run)
        db.flush()
        historical_features = dict(base_features)
        flow = float(base_features[flow_key]) + (index - 4) * 4.0
        outer_air = float(base_features[outer_air_key]) + ((index % 3) - 1) * 8.0
        historical_features[flow_key] = flow
        historical_features[outer_air_key] = outer_air
        db.add(
            PointFeatureSnapshot(
                production_run_id=historical_run.id,
                measurement_point_id=points["P-ROOF-03"].id,
                feature_set_version=CURRENT_FEATURE_SET_VERSION,
                feature_values=historical_features,
                completeness_score=1.0,
                generated_at=now,
            )
        )
        measurement = QualityMeasurement(
            data_no=f"DEMO-TRAIN-QM-{index:02d}",
            production_run_id=historical_run.id,
            measurement_group_id=groups["ORANGE_PEEL"].id,
            measurement_point_id=points["P-ROOF-03"].id,
            quality_type="ORANGE_PEEL",
            data_type="DEMO_TRAINING",
            measured_at=now - timedelta(days=index, minutes=-35),
            measured_by="演示数据生成器",
        )
        db.add(measurement)
        db.flush()
        db.add(
            QualityMetricValue(
                measurement_id=measurement.id,
                metric_code="doi",
                metric_name="DOI",
                raw_value=78.2 + 0.06 * (flow - float(base_features[flow_key]))
                - 0.08 * (outer_air - float(base_features[outer_air_key])),
            )
        )
    db.commit()
    model = train_model(
        db,
        ModelTrainingRequest(
            model_code="DEMO-DOI-BASELINE",
            version="1.0",
            target_metric="doi",
            feature_set_version=CURRENT_FEATURE_SET_VERSION,
            min_samples=5,
            ridge_lambda=0.1,
        ),
    )
    return {
        "status": "seeded",
        "factory_id": factory.id,
        "production_run_id": run.id,
        "point_feature_snapshot_id": snapshot["snapshot_id"],
        "model_version_id": model.id,
        "admin_user_id": admin.id,
    }


def main() -> None:
    with SessionLocal() as db:
        print(seed_demo(db))


if __name__ == "__main__":
    main()
