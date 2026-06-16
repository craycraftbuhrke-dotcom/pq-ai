from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import PERMISSION_CATALOG, ROLE_CATALOG, hash_api_key, hash_password
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
    DatasetSnapshot,
    DurrApplicationController,
    DurrRobot,
    DurrRotaryAtomizer,
    Factory,
    FactoryVehicleModel,
    IntegrationEndpoint,
    MaterialBatch,
    MaterialBatchTestResult,
    MaterialCharacteristicApplicability,
    MaterialCharacteristicDefinition,
    MaterialSpecification,
    MaterialTestMethod,
    MeasurementCalibrationRecord,
    MeasurementGroup,
    MeasurementGroupPoint,
    MeasurementImportProfile,
    MeasurementInstrument,
    MeasurementMethod,
    MeasurementPoint,
    MeasurementReferenceStandard,
    MeasurementRepeatReading,
    ModelAcceptancePolicy,
    ModelApplicabilityScope,
    ModelVersion,
    ModelAcceptanceDecision,
    ParameterDefinition,
    Part,
    PointContributionEntry,
    PointContributionVersion,
    PointFeatureSnapshot,
    ProductionDeviceExecution,
    ProductionRun,
    ProductionStageRun,
    ProgramColor,
    ProgramDeviceConfiguration,
    ProgramVehicleModel,
    QualityMeasurement,
    QualityMetricDefinition,
    QualityMetricValue,
    QualityStandard,
    Role,
    RolePermission,
    SprayProgram,
    SprayProgramVersion,
    TrajectoryPathSegment,
    TrajectoryProgram,
    VehicleModel,
    VehicleModelColor,
    UserRole,
    Permission,
)
from app.schemas.modeling import (
    DatasetBuildRequest,
    ModelAcceptanceRequest,
    ModelTrainingRequest,
)
from app.services.feature_aggregation import build_point_feature_snapshot
from app.services.measurement_reliability import refresh_measurement_reliability
from app.services.material_governance import refresh_material_result_reliability
from app.services.modeling import (
    build_dataset_snapshot,
    record_model_acceptance,
    ensure_model_governance,
    train_model,
    update_model_status,
)


def _ensure_demo_governed_model(db: Session) -> ModelVersion:
    dataset = db.scalar(
        select(DatasetSnapshot).where(
            DatasetSnapshot.dataset_code == "DEMO-DOI-DATASET",
            DatasetSnapshot.version == "6.0-leakage-safe",
        )
    )
    if not dataset:
        dataset = build_dataset_snapshot(
            db,
            DatasetBuildRequest(
                dataset_code="DEMO-DOI-DATASET",
                version="6.0-leakage-safe",
                target_metric="doi",
                feature_set_version=CURRENT_FEATURE_SET_VERSION,
            ),
        )
    model = db.scalar(
        select(ModelVersion).where(
            ModelVersion.model_code == "DEMO-DOI-BASELINE",
            ModelVersion.version == "6.0-leakage-safe",
        )
    )
    if not model:
        model = train_model(
            db,
            ModelTrainingRequest(
                model_code="DEMO-DOI-BASELINE",
                version="6.0-leakage-safe",
                target_metric="doi",
                feature_set_version=CURRENT_FEATURE_SET_VERSION,
                dataset_snapshot_id=dataset.id,
                min_samples=5,
                ridge_lambda=0.1,
            ),
        )
    ensure_model_governance(db, model)
    db.commit()
    model_scopes = list(
        db.scalars(
            select(ModelApplicabilityScope).where(
                ModelApplicabilityScope.model_version_id == model.id,
                ModelApplicabilityScope.status != "INACTIVE",
            )
        )
    )
    for scope in model_scopes:
        demo_policy = db.scalar(
            select(ModelAcceptancePolicy).where(
                ModelAcceptancePolicy.factory_id == scope.factory_id,
                ModelAcceptancePolicy.target_metric == model.target_metric,
                ModelAcceptancePolicy.policy_type == "DEMO",
                ModelAcceptancePolicy.status == "ACTIVE",
            )
        )
        if not demo_policy:
            db.add(
                ModelAcceptancePolicy(
                    policy_code=f"DEMO-{model.target_metric.upper()}-{scope.factory_id[:8]}",
                    version="1.0",
                    factory_id=scope.factory_id,
                    target_metric=model.target_metric,
                    policy_type="DEMO",
                    max_validation_rmse=0.05,
                    min_validation_r2=0.95,
                    min_train_groups=3,
                    min_validation_groups=2,
                    status="ACTIVE",
                    source_uri="demo://model-acceptance-policy",
                    approved_by="演示模型治理员",
                    approved_at=datetime.now(UTC),
                    remark="仅用于功能体验，不代表工厂批准的生产模型验收阈值。",
                )
            )
    db.commit()
    acceptance = db.scalar(
        select(ModelAcceptanceDecision)
        .where(ModelAcceptanceDecision.model_version_id == model.id)
        .order_by(ModelAcceptanceDecision.decided_at.desc())
    )
    if (
        not acceptance
        or acceptance.decision != "ACCEPTED"
        or not acceptance.checks.get("has_configured_applicability_scope")
        or not acceptance.checks.get("has_configured_ood_policy")
        or not acceptance.checks.get("factory_acceptance_policies_present")
        or not acceptance.checks.get("factory_acceptance_thresholds_passed")
    ):
        record_model_acceptance(
            db,
            model,
            ModelAcceptanceRequest(
                decision="ACCEPTED",
                decided_by="演示模型治理员",
                comment="演示数据已通过分组时间留出检查，仅用于功能体验。",
            ),
        )
    if model.status != "ACTIVE":
        update_model_status(db, model, "ACTIVE")
    return model


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
            password_hash=hash_password("admin123"),
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


def _seed_measurement_governance(db: Session, now: datetime) -> dict[str, dict]:
    instrument_specs = {
        "ORANGE_PEEL": {
            "code": "BYK-WAVE-DEMO",
            "name": "BYK wave-scan 演示仪",
            "manufacturer": "BYK-Gardner",
            "model": "wave-scan",
            "instrument_type": "BYK_ORANGE_PEEL",
            "serial_no": "DEMO-BYK-WAVE-001",
            "firmware_version": "DEMO-1.0",
            "supported_quality_types": ["ORANGE_PEEL"],
        },
        "COLOR_DIFFERENCE": {
            "code": "BYK-MAC-DEMO",
            "name": "BYK 多角度色差演示仪",
            "manufacturer": "BYK-Gardner",
            "model": "BYK-mac i",
            "instrument_type": "BYK_COLOR",
            "serial_no": "DEMO-BYK-MAC-001",
            "firmware_version": "DEMO-1.0",
            "supported_quality_types": ["COLOR_DIFFERENCE"],
        },
        "THICKNESS": {
            "code": "FISCHER-THK-DEMO",
            "name": "Fischer 膜厚演示仪",
            "manufacturer": "Helmut Fischer",
            "model": "Dualscope",
            "instrument_type": "FISCHER_THICKNESS",
            "serial_no": "DEMO-FISCHER-001",
            "firmware_version": "DEMO-1.0",
            "supported_quality_types": ["THICKNESS"],
        },
    }
    method_specs = {
        "ORANGE_PEEL": {
            "code": "BYK-WAVE-DOI",
            "name": "BYK 橘皮/DOI 测量",
            "version": "1.0",
            "quality_type": "ORANGE_PEEL",
            "instrument_type": "BYK_ORANGE_PEEL",
            "method_type": "WAVE_SCAN",
            "requires_reference": True,
            "requires_direction": True,
            "minimum_repeats": 1,
        },
        "COLOR_DIFFERENCE": {
            "code": "BYK-MAC-MULTIANGLE",
            "name": "BYK 多角度色差/效应测量",
            "version": "1.0",
            "quality_type": "COLOR_DIFFERENCE",
            "instrument_type": "BYK_COLOR",
            "method_type": "MULTI_ANGLE_COLOR",
            "requires_reference": True,
            "requires_direction": True,
            "minimum_repeats": 1,
        },
        "THICKNESS": {
            "code": "FISCHER-TOTAL-FILM",
            "name": "Fischer 总膜厚测量",
            "version": "1.0",
            "quality_type": "THICKNESS",
            "instrument_type": "FISCHER_THICKNESS",
            "method_type": "MAGNETIC_INDUCTION",
            "probe_code": "DEMO-DUAL-PROBE",
            "substrate_type": "STEEL",
            "geometry_class": "BODY_PANEL",
            "layer_scope": "TOTAL_FILM",
            "requires_reference": False,
            "requires_direction": False,
            "minimum_repeats": 1,
        },
    }
    resources: dict[str, dict] = {}
    for quality_type, instrument_spec in instrument_specs.items():
        instrument = db.scalar(
            select(MeasurementInstrument).where(
                MeasurementInstrument.code == instrument_spec["code"]
            )
        )
        if not instrument:
            instrument = MeasurementInstrument(
                **instrument_spec,
                calibration_required=True,
                status="ACTIVE",
                remark="仅用于本地链路演示，不代表真实仪器配置",
            )
            db.add(instrument)
            db.flush()

        method_spec = method_specs[quality_type]
        method = db.scalar(
            select(MeasurementMethod).where(
                MeasurementMethod.code == method_spec["code"],
                MeasurementMethod.version == method_spec["version"],
            )
        )
        if not method:
            method = MeasurementMethod(
                **method_spec,
                is_active=True,
                instructions="演示测量方法；现场使用前必须替换为批准作业指导书。",
            )
            db.add(method)
            db.flush()

        reference = db.scalar(
            select(MeasurementReferenceStandard).where(
                MeasurementReferenceStandard.code == f"REF-{quality_type}-DEMO"
            )
        )
        if not reference:
            reference = MeasurementReferenceStandard(
                code=f"REF-{quality_type}-DEMO",
                name=f"{quality_type} 演示参考件",
                quality_type=quality_type,
                serial_no=f"DEMO-REF-{quality_type}",
                certificate_no=f"DEMO-CERT-{quality_type}",
                valid_from=now - timedelta(days=365),
                valid_until=now + timedelta(days=365),
                reference_values={"demo_only": 1},
                status="ACTIVE",
            )
            db.add(reference)
            db.flush()

        profile = db.scalar(
            select(MeasurementImportProfile).where(
                MeasurementImportProfile.code == f"IMPORT-{quality_type}-DEMO",
                MeasurementImportProfile.version == "1.0",
            )
        )
        if not profile:
            profile = MeasurementImportProfile(
                code=f"IMPORT-{quality_type}-DEMO",
                name=f"{quality_type} 演示导入模板",
                version="1.0",
                instrument_type=instrument.instrument_type,
                quality_type=quality_type,
                schema_version="demo-1.0",
                field_mapping={"metric_code": "metric_code", "raw_value": "raw_value"},
                is_active=True,
            )
            db.add(profile)
            db.flush()

        calibration = db.scalar(
            select(MeasurementCalibrationRecord).where(
                MeasurementCalibrationRecord.calibration_no
                == f"CAL-{instrument.code}-DEMO"
            )
        )
        if not calibration:
            calibration = MeasurementCalibrationRecord(
                calibration_no=f"CAL-{instrument.code}-DEMO",
                instrument_id=instrument.id,
                method_id=method.id,
                reference_standard_id=reference.id,
                calibrated_at=now - timedelta(days=365),
                valid_until=now + timedelta(days=365),
                result="PASS",
                performed_by="演示校准生成器",
                check_values={"demo_only": 1},
            )
            db.add(calibration)
            db.flush()
        resources[quality_type] = {
            "instrument": instrument,
            "method": method,
            "reference": reference,
            "profile": profile,
            "calibration": calibration,
        }
    db.flush()
    return resources


def _govern_demo_measurements(db: Session, resources: dict[str, dict]) -> None:
    measurements = list(
        db.scalars(
            select(QualityMeasurement).where(
                (QualityMeasurement.data_no.like("QM-260610-%"))
                | QualityMeasurement.data_no.like("DEMO-TRAIN-QM-%")
            )
        )
    )
    for measurement in measurements:
        governance = resources.get(measurement.quality_type)
        if not governance:
            continue
        measurement.instrument_id = governance["instrument"].id
        measurement.device_code = governance["instrument"].code
        measurement.measurement_method_id = governance["method"].id
        measurement.calibration_record_id = governance["calibration"].id
        measurement.reference_standard_id = governance["reference"].id
        measurement.import_profile_id = governance["profile"].id
        measurement.measurement_direction = (
            "LONGITUDINAL" if governance["method"].requires_direction else None
        )
        measurement.raw_file_uri = f"demo://measurement/{measurement.data_no}"
        metrics = list(
            db.scalars(
                select(QualityMetricValue).where(
                    QualityMetricValue.measurement_id == measurement.id
                )
            )
        )
        for metric in metrics:
            repeat = db.scalar(
                select(MeasurementRepeatReading).where(
                    MeasurementRepeatReading.measurement_id == measurement.id,
                    MeasurementRepeatReading.repeat_no == 1,
                    MeasurementRepeatReading.metric_code == metric.metric_code,
                )
            )
            if not repeat:
                db.add(
                    MeasurementRepeatReading(
                        measurement_id=measurement.id,
                        repeat_no=1,
                        metric_code=metric.metric_code,
                        raw_value=metric.raw_value,
                        corrected_value=metric.corrected_value,
                        unit=metric.unit,
                        is_valid=True,
                    )
                )
        db.flush()
        refresh_measurement_reliability(db, measurement)
    db.commit()


def _seed_durr_governance(db: Session, factory: Factory, now: datetime) -> None:
    programs = list(
        db.scalars(select(SprayProgram).where(SprayProgram.factory_id == factory.id))
    )
    for program in programs:
        device_code = program.station_code
        controller = db.scalar(
            select(DurrApplicationController).where(
                DurrApplicationController.factory_id == factory.id,
                DurrApplicationController.code == f"CTRL-{device_code}",
            )
        )
        if not controller:
            controller = DurrApplicationController(
                factory_id=factory.id,
                code=f"CTRL-{device_code}",
                name=f"{program.station_name}应用控制器",
                model="DEMO-DURR-APPLICATION-CONTROLLER",
                serial_no=f"DEMO-CTRL-{device_code}",
                software_version="DEMO-1.0",
                status="ACTIVE",
                source_uri="demo://durr/controller",
                remark="仅用于本地链路演示，现场使用前必须替换为受批准设备资料",
            )
            db.add(controller)
            db.flush()
        robot = db.scalar(
            select(DurrRobot).where(
                DurrRobot.factory_id == factory.id,
                DurrRobot.code == f"ROBOT-{device_code}",
            )
        )
        if not robot:
            robot = DurrRobot(
                factory_id=factory.id,
                code=f"ROBOT-{device_code}",
                name=f"{program.station_name}机器人",
                model=program.robot_model or "DEMO-DURR-PAINT-ROBOT",
                serial_no=f"DEMO-ROBOT-{device_code}",
                controller_software_version="DEMO-1.0",
                status="ACTIVE",
                source_uri="demo://durr/robot",
                remark="仅用于本地链路演示，现场使用前必须替换为受批准设备资料",
            )
            db.add(robot)
            db.flush()
        atomizer = db.scalar(
            select(DurrRotaryAtomizer).where(
                DurrRotaryAtomizer.factory_id == factory.id,
                DurrRotaryAtomizer.code == f"BELL-{device_code}",
            )
        )
        if not atomizer:
            atomizer = DurrRotaryAtomizer(
                factory_id=factory.id,
                controller_id=controller.id,
                code=f"BELL-{device_code}",
                name=f"{program.station_name}静电旋杯",
                model="DEMO-DURR-ROTARY-BELL",
                serial_no=f"DEMO-BELL-{device_code}",
                bell_cup_type="DEMO-APPROVED-BELL-CUP",
                bell_cup_code=f"DEMO-CUP-{device_code}",
                status="ACTIVE",
                source_uri="demo://durr/atomizer",
                remark="仅用于本地链路演示，不代表真实 Dürr 型号或设备边界",
            )
            db.add(atomizer)
            db.flush()

        versions = list(
            db.scalars(
                select(SprayProgramVersion).where(
                    SprayProgramVersion.spray_program_id == program.id
                )
            )
        )
        for version in versions:
            configuration = db.scalar(
                select(ProgramDeviceConfiguration).where(
                    ProgramDeviceConfiguration.program_version_id == version.id,
                    ProgramDeviceConfiguration.configuration_version == "1.0",
                )
            )
            if not configuration:
                configuration = ProgramDeviceConfiguration(
                    program_version_id=version.id,
                    robot_id=robot.id,
                    atomizer_id=atomizer.id,
                    controller_id=controller.id,
                    configuration_version="1.0",
                    status="ACTIVE",
                    source_uri="demo://durr/device-configuration",
                    approved_by="演示设备治理生成器",
                    approved_at=now - timedelta(days=1),
                    effective_from=now - timedelta(days=1),
                )
                db.add(configuration)
                db.flush()
            trajectory = db.scalar(
                select(TrajectoryProgram).where(
                    TrajectoryProgram.program_version_id == version.id,
                    TrajectoryProgram.trajectory_code == f"TRJ-{program.program_code}",
                    TrajectoryProgram.version == "1.0",
                )
            )
            if not trajectory:
                trajectory = TrajectoryProgram(
                    program_version_id=version.id,
                    trajectory_code=f"TRJ-{program.program_code}",
                    name=f"{program.name}演示轨迹",
                    version="1.0",
                    checksum=f"DEMO-CHECKSUM-{program.program_code}-{version.version}",
                    coordinate_system="DEMO-BODY",
                    tcp_name="DEMO-BELL-TCP",
                    status="ACTIVE",
                    source_uri="demo://durr/trajectory",
                    approved_by="演示轨迹治理生成器",
                    approved_at=now - timedelta(days=1),
                    remark="演示轨迹不包含真实坐标、速度或触发边界",
                )
                db.add(trajectory)
                db.flush()
            brushes = list(
                db.scalars(
                    select(Brush)
                    .where(Brush.program_version_id == version.id)
                    .order_by(Brush.brush_no)
                )
            )
            segments: dict[str, TrajectoryPathSegment] = {}
            for segment_no, brush in enumerate(brushes, start=1):
                segment = db.scalar(
                    select(TrajectoryPathSegment).where(
                        TrajectoryPathSegment.trajectory_program_id == trajectory.id,
                        TrajectoryPathSegment.segment_no == segment_no,
                    )
                )
                if not segment:
                    segment = TrajectoryPathSegment(
                        trajectory_program_id=trajectory.id,
                        segment_no=segment_no,
                        name=f"{brush.brush_no} 演示路径段",
                        brush_id=brush.id,
                        part_id=brush.part_id,
                        tcp_name=trajectory.tcp_name,
                        trigger_state="ON",
                        remark="未虚构坐标和速度；等待真实轨迹导入",
                    )
                    db.add(segment)
                    db.flush()
                segments[brush.id] = segment
            for target_family in ("ORANGE_PEEL", "COLOR_DIFFERENCE", "THICKNESS"):
                contribution_version = db.scalar(
                    select(PointContributionVersion).where(
                        PointContributionVersion.program_version_id == version.id,
                        PointContributionVersion.target_family == target_family,
                        PointContributionVersion.version == "1.0",
                    )
                )
                if not contribution_version:
                    contribution_version = PointContributionVersion(
                        program_version_id=version.id,
                        target_family=target_family,
                        version="1.0",
                        method="EXPERT",
                        status="ACTIVE",
                        evidence_uri="demo://durr/contribution",
                        approved_by="演示贡献治理生成器",
                        approved_at=now - timedelta(days=1),
                        remark="由历史演示刷子贡献迁移，现场使用前必须验证",
                    )
                    db.add(contribution_version)
                    db.flush()
                legacy_rows = db.execute(
                    select(BrushPointContribution, MeasurementPoint)
                    .join(
                        MeasurementPoint,
                        MeasurementPoint.id == BrushPointContribution.measurement_point_id,
                    )
                    .where(
                        BrushPointContribution.brush_id.in_([brush.id for brush in brushes]),
                        BrushPointContribution.is_approved.is_(True),
                    )
                ).all()
                for legacy, point in legacy_rows:
                    if target_family not in point.quality_types:
                        continue
                    segment = segments[legacy.brush_id]
                    source_key = f"PATH:{segment.id}"
                    if not db.scalar(
                        select(PointContributionEntry).where(
                            PointContributionEntry.contribution_version_id
                            == contribution_version.id,
                            PointContributionEntry.measurement_point_id == point.id,
                            PointContributionEntry.source_key == source_key,
                        )
                    ):
                        db.add(
                            PointContributionEntry(
                                contribution_version_id=contribution_version.id,
                                measurement_point_id=point.id,
                                path_segment_id=segment.id,
                                source_key=source_key,
                                overlap_ratio=legacy.overlap_ratio,
                                contribution_weight=legacy.contribution_weight,
                                evidence={"migrated_from": "brush_point_contribution"},
                            )
                        )
            stage_runs = list(
                db.scalars(
                    select(ProductionStageRun).where(
                        ProductionStageRun.program_version_id == version.id
                    )
                )
            )
            for stage_run in stage_runs:
                execution = db.scalar(
                    select(ProductionDeviceExecution).where(
                        ProductionDeviceExecution.production_stage_run_id == stage_run.id
                    )
                )
                if not execution:
                    execution = ProductionDeviceExecution(
                        production_stage_run_id=stage_run.id,
                        device_configuration_id=configuration.id,
                        trajectory_program_id=trajectory.id,
                        executed_checksum=trajectory.checksum,
                        status="COMPLETED",
                        source_system="DEMO-ROBOT-PLC",
                    )
                    db.add(execution)
    db.commit()


def _seed_material_governance(db: Session, now: datetime) -> None:
    definition_specs = (
        (
            "viscosity",
            "粘度/流变结果",
            "VISCOSITY_RHEOLOGY",
            "DEMO_UNIT",
            ["ORANGE_PEEL", "THICKNESS"],
        ),
        ("solid_ratio", "固含比结果", "SOLIDS", "ratio", ["THICKNESS"]),
        ("density", "密度结果", "DENSITY", "DEMO_UNIT", ["THICKNESS"]),
    )
    definitions: dict[str, MaterialCharacteristicDefinition] = {}
    methods: dict[str, MaterialTestMethod] = {}
    for code, name, category, unit, target_families in definition_specs:
        definition = db.scalar(
            select(MaterialCharacteristicDefinition).where(
                MaterialCharacteristicDefinition.code == code
            )
        )
        if not definition:
            definition = MaterialCharacteristicDefinition(
                code=code,
                name=name,
                category=category,
                canonical_unit=unit,
                target_families=target_families,
                is_model_feature=True,
                status="ACTIVE",
                description=(
                    "演示迁移定义；DEMO_UNIT 不代表真实检测单位，现场使用前必须"
                    "替换为批准方法、单位和来源"
                ),
            )
            db.add(definition)
            db.flush()
        definitions[code] = definition
        method = db.scalar(
            select(MaterialTestMethod).where(
                MaterialTestMethod.code == f"DEMO-{code.upper()}",
                MaterialTestMethod.version == "1.0",
            )
        )
        if not method:
            method = MaterialTestMethod(
                characteristic_definition_id=definition.id,
                code=f"DEMO-{code.upper()}",
                name=f"{name}演示迁移方法",
                version="1.0",
                method_type="DEMO_MIGRATION_PLACEHOLDER",
                result_unit=unit,
                procedure_uri=f"demo://material/method/{code}",
                conditions={"requires_factory_approved_replacement": True},
                status="ACTIVE",
                remark="仅用于验证治理数据链，不代表真实材料检测方法",
            )
            db.add(method)
            db.flush()
        methods[code] = method

    stage_material_types = (
        ("MIDCOAT_EXT", "MIDCOAT"),
        ("BASECOAT_1", "BASECOAT"),
        ("BASECOAT_2", "BASECOAT"),
        ("CLEARCOAT_1", "CLEARCOAT"),
        ("CLEARCOAT_2", "CLEARCOAT"),
    )
    for stage, material_type in stage_material_types:
        if not db.scalar(
            select(MaterialCharacteristicApplicability).where(
                MaterialCharacteristicApplicability.characteristic_definition_id
                == definitions["viscosity"].id,
                MaterialCharacteristicApplicability.material_type == material_type,
                MaterialCharacteristicApplicability.process_stage == stage,
                MaterialCharacteristicApplicability.target_family == "ORANGE_PEEL",
            )
        ):
            db.add(
                MaterialCharacteristicApplicability(
                    characteristic_definition_id=definitions["viscosity"].id,
                    material_type=material_type,
                    process_stage=stage,
                    target_family="ORANGE_PEEL",
                    is_required=True,
                    status="ACTIVE",
                    approved_by="演示材料治理生成器",
                    approved_at=now - timedelta(days=1),
                    remark="演示适用关系，现场使用前必须由材料/工艺工程师批准",
                )
            )
        for code in ("viscosity", "solid_ratio", "density"):
            if "THICKNESS" not in definitions[code].target_families:
                continue
            if not db.scalar(
                select(MaterialCharacteristicApplicability).where(
                    MaterialCharacteristicApplicability.characteristic_definition_id
                    == definitions[code].id,
                    MaterialCharacteristicApplicability.material_type == material_type,
                    MaterialCharacteristicApplicability.process_stage == stage,
                    MaterialCharacteristicApplicability.target_family == "THICKNESS",
                )
            ):
                db.add(
                    MaterialCharacteristicApplicability(
                        characteristic_definition_id=definitions[code].id,
                        material_type=material_type,
                        process_stage=stage,
                        target_family="THICKNESS",
                        is_required=False,
                        status="ACTIVE",
                        approved_by="演示材料治理生成器",
                        approved_at=now - timedelta(days=1),
                        remark="演示适用关系，现场使用前必须由材料/工艺工程师批准",
                    )
                )
    db.flush()

    for batch in db.scalars(select(MaterialBatch)):
        first_use_started_at = db.scalar(
            select(ProductionRun.started_at)
            .join(
                ProductionStageRun,
                ProductionStageRun.production_run_id == ProductionRun.id,
            )
            .where(ProductionStageRun.material_batch_id == batch.id)
            .order_by(ProductionRun.started_at)
            .limit(1)
        )
        demo_tested_at = (
            first_use_started_at - timedelta(hours=1)
            if first_use_started_at
            else now - timedelta(days=2)
        )
        legacy_values = {
            "viscosity": batch.viscosity,
            "solid_ratio": batch.solid_ratio,
            "density": (batch.coa_values or {}).get("density"),
        }
        for code, value in legacy_values.items():
            if value is None:
                continue
            definition = definitions[code]
            method = methods[code]
            specification = db.scalar(
                select(MaterialSpecification).where(
                    MaterialSpecification.material_code == batch.material_code,
                    MaterialSpecification.characteristic_definition_id == definition.id,
                    MaterialSpecification.method_id == method.id,
                    MaterialSpecification.version == "DEMO-1.0",
                )
            )
            if not specification:
                specification = MaterialSpecification(
                    material_code=batch.material_code,
                    characteristic_definition_id=definition.id,
                    method_id=method.id,
                    version="DEMO-1.0",
                    status="ACTIVE",
                    source_uri=f"demo://material/spec/{batch.material_code}/{code}",
                    effective_from=now - timedelta(days=30),
                    approved_by="演示材料治理生成器",
                    approved_at=now - timedelta(days=1),
                    remark="未设置数值上下限，不代表真实 TDS/COA 规格",
                )
                db.add(specification)
                db.flush()
            result_no = f"DEMO-{batch.batch_no}-{code}".upper()
            result = db.scalar(
                select(MaterialBatchTestResult).where(
                    MaterialBatchTestResult.result_no == result_no
                )
            )
            if not result:
                result = MaterialBatchTestResult(
                    result_no=result_no,
                    material_batch_id=batch.id,
                    characteristic_definition_id=definition.id,
                    method_id=method.id,
                    result_value=float(value),
                    unit=definition.canonical_unit,
                    tested_at=demo_tested_at,
                    tested_by="演示材料治理生成器",
                    source_uri=f"demo://material/result/{batch.batch_no}/{code}",
                    raw_values={"migrated_from": f"material_batch.{code}"},
                    remark="由历史演示字段迁移，现场使用前必须以真实检测结果替换",
                )
                db.add(result)
                db.flush()
            elif (result.raw_values or {}).get("migrated_from"):
                result.tested_at = demo_tested_at
            refresh_material_result_reliability(db, result)
    db.commit()


def _upgrade_existing_demo_scope_data(db: Session) -> ModelVersion | None:
    upgraded_keys = set(
        db.execute(
            select(
                PointFeatureSnapshot.production_run_id,
                PointFeatureSnapshot.measurement_point_id,
                PointFeatureSnapshot.target_family,
            ).where(
                PointFeatureSnapshot.feature_set_version == CURRENT_FEATURE_SET_VERSION
            )
        ).all()
    )
    demo_snapshots = list(
        db.scalars(
            select(PointFeatureSnapshot)
            .join(ProductionRun, ProductionRun.id == PointFeatureSnapshot.production_run_id)
            .where(
                PointFeatureSnapshot.feature_set_version != CURRENT_FEATURE_SET_VERSION,
                (
                    (ProductionRun.run_no == "RUN-20260610-001")
                    | ProductionRun.run_no.like("DEMO-TRAIN-RUN-%")
                ),
            )
            .order_by(PointFeatureSnapshot.generated_at.desc())
        )
    )
    for snapshot in demo_snapshots:
        snapshot_key = (
            snapshot.production_run_id,
            snapshot.measurement_point_id,
            "ORANGE_PEEL",
        )
        if snapshot_key in upgraded_keys:
            continue
        feature_values = approved_numeric_values(snapshot.feature_values)
        feature_values = {
            key.replace(".material_viscosity", ".material.viscosity")
            .replace(".material_solid_ratio", ".material.solid_ratio")
            .replace(".coa.density", ".material.density"): value
            for key, value in feature_values.items()
        }
        if not feature_values:
            continue
        db.add(
            PointFeatureSnapshot(
                production_run_id=snapshot.production_run_id,
                measurement_point_id=snapshot.measurement_point_id,
                feature_set_version=CURRENT_FEATURE_SET_VERSION,
                target_family="ORANGE_PEEL",
                feature_values=feature_values,
                lineage={"source": "demo-historical-upgrade"},
                completeness_score=snapshot.completeness_score,
                generated_at=datetime.now(UTC),
            )
        )
        upgraded_keys.add(snapshot_key)
    db.commit()

    model = db.scalar(
        select(ModelVersion).where(
            ModelVersion.model_code == "DEMO-DOI-BASELINE",
            ModelVersion.version == "6.0-leakage-safe",
        )
    )
    if model:
        return _ensure_demo_governed_model(db)

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
    return _ensure_demo_governed_model(db)


def seed_demo(db: Session) -> dict:
    _seed_catalogs(db)
    admin = _seed_security(db)
    _seed_integration_endpoints(db)
    now = datetime.now(UTC)
    measurement_governance = _seed_measurement_governance(db, now)
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
        _govern_demo_measurements(db, measurement_governance)
        _seed_durr_governance(db, existing_factory, now)
        _seed_material_governance(db, now)
        demo_run = db.scalar(
            select(ProductionRun).where(ProductionRun.run_no == "RUN-20260610-001")
        )
        demo_point = db.scalar(
            select(MeasurementPoint).where(MeasurementPoint.code == "P-ROOF-03")
        )
        if demo_run and demo_point:
            build_point_feature_snapshot(
                db,
                demo_run.id,
                demo_point.id,
                target_family="ORANGE_PEEL",
            )
        model = _upgrade_existing_demo_scope_data(db)
        db.commit()
        return {
            "status": "already_seeded",
            "factory_id": existing_factory.id,
            "model_version_id": model.id if model else None,
            "admin_user_id": admin.id,
        }

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
    _govern_demo_measurements(db, measurement_governance)
    _seed_durr_governance(db, factory, now)
    _seed_material_governance(db, now)
    snapshot = build_point_feature_snapshot(
        db, run.id, points["P-ROOF-03"].id, target_family="ORANGE_PEEL"
    )
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
                target_family="ORANGE_PEEL",
                feature_values=historical_features,
                lineage={"source": "demo-synthetic-training"},
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
    _govern_demo_measurements(db, measurement_governance)
    model = _ensure_demo_governed_model(db)
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
