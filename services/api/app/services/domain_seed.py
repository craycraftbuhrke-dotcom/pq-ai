"""部署时写入一次的领域演示数据（每个业务领域模型 5 条）。

设计约束：
- **只写一次**：以 Factory.code == DEMO-F01 作为全局标记；已存在则整批跳过。
- **不做 DDL / DELETE**：仅 INSERT；失败由 startup_seed 吞掉，不阻断进程。
- **跳过**：系统字典（ParameterDefinition / QualityMetricDefinition，由 catalog_seed 负责）、
  用户认证体系（AppUser / Role / Permission / UserRole / RolePermission / UserSession /
  ApiKey / AuditLog——库表未齐备前不写入）、运行态会话与审计流水。
- 业务主键统一 ``DEMO-*`` 前缀，便于识别与排查。
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from hashlib import sha256

from sqlalchemy import inspect, select
from sqlalchemy.orm import Session

from app.models.domain import (
    ActualParameter,
    Brush,
    BrushParameter,
    BrushPointContribution,
    ClosedLoopEvaluation,
    Color,
    ContributionValidationStudy,
    ControlledTrial,
    DatasetSnapshot,
    DatasetSplitMember,
    DiagnosisResult,
    DurrApplicationController,
    DurrRobot,
    DurrRotaryAtomizer,
    EngineeringKnowledgeEntry,
    Factory,
    FactoryVehicleModel,
    FileImportJob,
    FileImportProfile,
    IntegrationEndpoint,
    IntegrationEvent,
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
    MeasurementMsaStudy,
    MeasurementPoint,
    MeasurementPoint3DLayout,
    MeasurementPointLayout,
    MeasurementProbe,
    MeasurementReferenceStandard,
    MeasurementRepeatReading,
    ModelAcceptanceDecision,
    ModelAcceptancePolicy,
    ModelApplicabilityScope,
    ModelArtifact,
    ModelExplanation,
    ModelOodPolicy,
    ModelValidationFold,
    ModelVersion,
    ParameterConstraintSource,
    ParameterDefinition,
    Part,
    PathSegmentExecution,
    PointContributionEntry,
    PointContributionVersion,
    PointFeatureSnapshot,
    PredictionResult,
    ProcessRoute,
    ProcessRouteApplicability,
    ProcessRouteStep,
    ProcessStage,
    ProductionDeviceExecution,
    ProductionRun,
    ProductionStageRun,
    ProgramColor,
    ProgramDeviceConfiguration,
    ProgramRollbackExecution,
    ProgramVehicleModel,
    QualityIssueComment,
    QualityIssueEvidence,
    QualityIssueTask,
    QualityMeasurement,
    QualityMetricValue,
    QualityStandard,
    QualityType,
    Recommendation,
    RecommendationAction,
    RecommendationStatus,
    SprayProgram,
    SprayProgramVersion,
    SupplierMaterialIssue,
    SupplierMaterialSubmission,
    TrajectoryPathSegment,
    TrajectoryProgram,
    TrajectorySegmentGeometry,
    VehicleModel,
    VehicleModelColor,
    VersionStatus,
)

SEED_MARKER_FACTORY_CODE = "DEMO-F01"
N = 5

STAGES = [
    ProcessStage.MIDCOAT_EXT,
    ProcessStage.BASECOAT_1,
    ProcessStage.BASECOAT_2,
    ProcessStage.CLEARCOAT_1,
    ProcessStage.CLEARCOAT_2,
]
QUALITY_TYPES = [
    QualityType.THICKNESS,
    QualityType.COLOR_DIFFERENCE,
    QualityType.ORANGE_PEEL,
    QualityType.THICKNESS,
    QualityType.ORANGE_PEEL,
]
BODY_VIEWS = ["RIGHT", "LEFT", "TOP", "REAR", "RIGHT"]
MATERIAL_TYPES = ["MIDCOAT", "BASECOAT", "CLEARCOAT", "BASECOAT", "CLEARCOAT"]
COLOR_TYPES = ["SOLID", "METALLIC", "PEARL", "SOLID", "METALLIC"]


def _now() -> datetime:
    return datetime.now(UTC)


def _hash(text: str) -> str:
    return sha256(text.encode("utf-8")).hexdigest()


def _existing_tables(db: Session) -> set[str]:
    bind = db.get_bind()
    return set(inspect(bind).get_table_names())


def seed_domain_demo_data(db: Session) -> dict:
    """幂等写入每个业务领域模型各 5 条演示数据。返回统计字典。"""
    tables = _existing_tables(db)
    required = {
        Factory.__tablename__,
        VehicleModel.__tablename__,
        Color.__tablename__,
        Part.__tablename__,
    }
    missing = sorted(required - tables)
    if missing:
        return {
            "created": 0,
            "skipped": True,
            "marker": SEED_MARKER_FACTORY_CODE,
            "missing_tables": missing,
        }

    marker = db.scalar(select(Factory).where(Factory.code == SEED_MARKER_FACTORY_CODE))
    if marker is not None:
        return {"created": 0, "skipped": True, "marker": SEED_MARKER_FACTORY_CODE}

    now = _now()
    created = 0

    def add_all(rows: list) -> list:
        nonlocal created
        db.add_all(rows)
        db.flush()
        created += len(rows)
        return rows

    # ---- L1 roots（不含认证体系表）----
    factories = add_all(
        [
            Factory(
                code=f"DEMO-F{i:02d}",
                name=f"演示工厂{i}",
                site_owner=f"owner{i}",
                remark="domain seed",
                is_active=True,
            )
            for i in range(1, N + 1)
        ]
    )
    models = add_all(
        [
            VehicleModel(code=f"DEMO-VM{i:02d}", name=f"演示车型{i}", remark="domain seed")
            for i in range(1, N + 1)
        ]
    )
    colors = add_all(
        [
            Color(
                code=f"DEMO-CLR{i:02d}",
                name=f"演示颜色{i}",
                color_type=COLOR_TYPES[i - 1],
                supplier="演示涂料商",
                remark="domain seed",
            )
            for i in range(1, N + 1)
        ]
    )
    parts = add_all(
        [
            Part(
                code=f"DEMO-PART{i:02d}",
                name=["左前门", "右前门", "引擎盖", "后盖", "左后翼子板"][i - 1],
                material="钢",
                region=["侧面", "侧面", "顶部", "后部", "侧面"][i - 1],
            )
            for i in range(1, N + 1)
        ]
    )
    material_batches = add_all(
        [
            MaterialBatch(
                batch_no=f"DEMO-BATCH-{i:02d}",
                material_code=f"MAT-{MATERIAL_TYPES[i - 1]}-{i:02d}",
                material_name=f"演示{MATERIAL_TYPES[i - 1]}材料{i}",
                material_type=MATERIAL_TYPES[i - 1],
                supplier="BASF-Demo",
                viscosity=20.0 + i,
                solid_ratio=40.0 + i,
            )
            for i in range(1, N + 1)
        ]
    )
    import_profiles = add_all(
        [
            FileImportProfile(
                code=f"DEMO-IMP-{i:02d}",
                name=f"演示导入模板{i}",
                version="1.0",
                domain_type=["QUALITY", "MATERIAL", "PROCESS", "QUALITY", "MATERIAL"][i - 1],
                parser_type="CSV",
                target_resource="quality_measurement",
                field_mapping={"body_no": "A", "point_code": "B"},
                required_fields=["body_no", "point_code"],
                status="ACTIVE",
            )
            for i in range(1, N + 1)
        ]
    )
    mat_chars = add_all(
        [
            MaterialCharacteristicDefinition(
                code=f"DEMO-MCHAR-{i:02d}",
                name=["粘度", "固含", "细度", "色相", "遮盖力"][i - 1],
                category="PHYSICAL",
                canonical_unit=["s", "%", "μm", "-", "%"][i - 1],
                target_families=[QUALITY_TYPES[i - 1].value],
                is_model_feature=True,
                status="ACTIVE",
            )
            for i in range(1, N + 1)
        ]
    )
    instruments = add_all(
        [
            MeasurementInstrument(
                code=f"DEMO-INST-{i:02d}",
                name=f"演示仪器{i}",
                manufacturer=["BYK", "Fischer", "BYK", "Fischer", "BYK"][i - 1],
                model=f"Model-{i}",
                instrument_type=["BYK", "FISCHER", "BYK", "FISCHER", "BYK"][i - 1],
                serial_no=f"DEMO-SN-{i:04d}",
                supported_quality_types=[QUALITY_TYPES[i - 1].value],
                calibration_required=True,
                status="ACTIVE",
            )
            for i in range(1, N + 1)
        ]
    )
    methods = add_all(
        [
            MeasurementMethod(
                code=f"DEMO-MM-{i:02d}",
                name=f"演示测量方法{i}",
                version="1.0",
                quality_type=QUALITY_TYPES[i - 1].value,
                instrument_type=instruments[i - 1].instrument_type,
                method_type="STANDARD",
                requires_reference=False,
                requires_direction=False,
                minimum_repeats=1,
                is_active=True,
            )
            for i in range(1, N + 1)
        ]
    )
    refs = add_all(
        [
            MeasurementReferenceStandard(
                code=f"DEMO-REF-{i:02d}",
                name=f"演示参考件{i}",
                quality_type=QUALITY_TYPES[i - 1].value,
                serial_no=f"REF-SN-{i:02d}",
                status="ACTIVE",
                reference_values={"nominal": float(i)},
            )
            for i in range(1, N + 1)
        ]
    )
    meas_import_profiles = add_all(
        [
            MeasurementImportProfile(
                code=f"DEMO-MIP-{i:02d}",
                name=f"演示测量导入{i}",
                version="1.0",
                instrument_type=instruments[i - 1].instrument_type,
                quality_type=QUALITY_TYPES[i - 1].value,
                schema_version="v1",
                field_mapping={"value": "C"},
                is_active=True,
            )
            for i in range(1, N + 1)
        ]
    )
    knowledge = add_all(
        [
            EngineeringKnowledgeEntry(
                entry_code=f"DEMO-KNOW-{i:02d}",
                version="1.0",
                title=f"演示知识条目{i}",
                category="PROCESS",
                target_quality_type=QUALITY_TYPES[i - 1].value,
                metric_code=["THICKNESS", "L_STAR", "LW", "THICKNESS", "DOI"][i - 1],
                symptom_pattern=f"演示症状{i}",
                diagnosis_rule=f"演示诊断规则{i}",
                recommended_checks={"checks": ["检查旋杯转速", "核对刷子流量"]},
                related_parameters=["FLOW_RATE"],
                evidence_level="RULE",
                status="ACTIVE",
                created_by="domain-seed",
            )
            for i in range(1, N + 1)
        ]
    )
    endpoints = add_all(
        [
            IntegrationEndpoint(
                code=f"DEMO-EP-{i:02d}",
                name=f"演示对接端点{i}",
                system_type=["MES", "QMS", "ROBOT", "MATERIAL", "MES"][i - 1],
                direction=["INBOUND", "OUTBOUND", "INBOUND", "INBOUND", "OUTBOUND"][i - 1],
                auth_type="API_KEY",
                is_active=True,
            )
            for i in range(1, N + 1)
        ]
    )
    datasets = add_all(
        [
            DatasetSnapshot(
                dataset_code=f"DEMO-DS-{i:02d}",
                version="1.0",
                target_metric=["THICKNESS", "L_STAR", "LW", "THICKNESS", "DOI"][i - 1],
                feature_set_version="fs-demo-1",
                split_strategy="TEMPORAL",
                group_key="production_run",
                holdout_ratio=0.2,
                status="BUILT",
                sample_count=100 + i,
                group_count=10 + i,
                train_sample_count=80 + i,
                validation_sample_count=20,
                train_group_count=8,
                validation_group_count=2,
                feature_names=["flow", "rpm", "hv"],
                lineage={"source": "domain-seed"},
                leakage_check={"ok": True},
                built_at=now - timedelta(days=i),
            )
            for i in range(1, N + 1)
        ]
    )

    # ---- L2 links / children ----
    add_all(
        [
            FactoryVehicleModel(
                factory_id=factories[i].id, vehicle_model_id=models[i].id, is_active=True
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            VehicleModelColor(vehicle_model_id=models[i].id, color_id=colors[i].id, is_active=True)
            for i in range(N)
        ]
    )
    points = add_all(
        [
            MeasurementPoint(
                code=f"P{i:02d}",
                name=f"演示点位{i}",
                vehicle_model_id=models[0].id if i < 3 else models[1].id,
                part_id=parts[i].id,
                point_type="QUALITY",
                region=parts[i].region,
                quality_types=[QUALITY_TYPES[i].value],
                is_match_point=(i == 0),
            )
            for i in range(N)
        ]
    )
    groups = add_all(
        [
            MeasurementGroup(
                code=f"DEMO-GRP-{i:02d}",
                name=f"演示编组{i}",
                vehicle_model_id=models[0].id,
                quality_type=QUALITY_TYPES[i].value,
                expected_point_count=N,
            )
            for i in range(N)
        ]
    )
    programs = add_all(
        [
            SprayProgram(
                program_code=f"DEMO-PROG-{i:02d}",
                name=f"演示喷涂程序{i}",
                factory_id=factories[i].id,
                process_stage=STAGES[i].value,
                station_code=f"STN-{i:02d}",
                station_name=f"工位{i}",
                robot_model="EcoRP E043i",
            )
            for i in range(N)
        ]
    )
    routes = add_all(
        [
            ProcessRoute(
                factory_id=factories[i].id,
                route_code=f"DEMO-ROUTE-{i:02d}",
                name=f"演示工艺路线{i}",
                version="1.0",
                route_type="3C3B",
                status="ACTIVE",
            )
            for i in range(N)
        ]
    )
    robots = add_all(
        [
            DurrRobot(
                factory_id=factories[i].id,
                code=f"RBT-{i:02d}",
                name=f"演示机器人{i}",
                model="EcoRP E043i",
                serial_no=f"DEMO-RBT-SN-{i:04d}",
                status="ACTIVE",
            )
            for i in range(N)
        ]
    )
    controllers = add_all(
        [
            DurrApplicationController(
                factory_id=factories[i].id,
                code=f"CTL-{i:02d}",
                name=f"演示控制器{i}",
                model="EcoDocu",
                serial_no=f"DEMO-CTL-SN-{i:04d}",
                status="ACTIVE",
            )
            for i in range(N)
        ]
    )
    atomizers = add_all(
        [
            DurrRotaryAtomizer(
                factory_id=factories[i].id,
                controller_id=controllers[i].id,
                code=f"ATM-{i:02d}",
                name=f"演示旋杯{i}",
                model="EcoBell3",
                serial_no=f"DEMO-ATM-SN-{i:04d}",
                status="ACTIVE",
            )
            for i in range(N)
        ]
    )
    test_methods = add_all(
        [
            MaterialTestMethod(
                characteristic_definition_id=mat_chars[i].id,
                code=f"DEMO-MTM-{i:02d}",
                name=f"演示材料方法{i}",
                version="1.0",
                method_type="LAB",
                result_unit=mat_chars[i].canonical_unit,
                status="ACTIVE",
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            MaterialCharacteristicApplicability(
                characteristic_definition_id=mat_chars[i].id,
                material_type=MATERIAL_TYPES[i],
                process_stage=STAGES[i].value,
                target_family=QUALITY_TYPES[i].value,
                is_required=True,
                status="ACTIVE",
            )
            for i in range(N)
        ]
    )
    accept_policies = add_all(
        [
            ModelAcceptancePolicy(
                policy_code=f"DEMO-AP-{i:02d}",
                version="1.0",
                factory_id=factories[i].id,
                target_metric=datasets[i].target_metric,
                policy_type="DEMO",
                max_validation_rmse=1.0,
                min_validation_r2=0.7,
                min_train_groups=5,
                min_validation_groups=2,
                status="ACTIVE",
                source_uri=f"demo://policy/{i}",
            )
            for i in range(N)
        ]
    )

    # Parameter constraints need catalog ParameterDefinition if present
    param_defs = list(db.scalars(select(ParameterDefinition).limit(N)).all())
    if len(param_defs) < N:
        # catalog not ready — create minimal disposable defs with DEMO codes
        param_defs = add_all(
            [
                ParameterDefinition(
                    code=f"DEMO-PARAM-{i:02d}",
                    name=f"演示参数{i}",
                    category="SPRAY",
                    unit="ml/min",
                    aggregation_method="WEIGHTED_AVERAGE",
                    is_recommendable=True,
                )
                for i in range(1, N + 1)
            ]
        )
    else:
        param_defs = param_defs[:N]

    add_all(
        [
            ParameterConstraintSource(
                parameter_definition_id=param_defs[i].id,
                factory_id=factories[i].id,
                process_stage=STAGES[i].value,
                constraint_code=f"DEMO-PCS-{i:02d}",
                version="1.0",
                source_type="FACTORY",
                lower_limit=10.0 + i,
                upper_limit=100.0 + i,
                unit=param_defs[i].unit,
                status="ACTIVE",
            )
            for i in range(N)
        ]
    )

    # ---- L3 ----
    add_all(
        [
            MeasurementPointLayout(
                measurement_point_id=points[i].id,
                body_view=BODY_VIEWS[i],
                layout_x=0.1 + 0.15 * i,
                layout_y=0.2 + 0.1 * i,
                status="ACTIVE",
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            MeasurementPoint3DLayout(
                measurement_point_id=points[i].id,
                pos_x=float(i),
                pos_y=0.5,
                pos_z=1.0 + 0.1 * i,
                status="ACTIVE",
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            MeasurementGroupPoint(
                measurement_group_id=groups[i].id,
                measurement_point_id=points[i].id,
                sequence_no=i + 1,
            )
            for i in range(N)
        ]
    )
    versions = add_all(
        [
            SprayProgramVersion(
                spray_program_id=programs[i].id,
                version=f"v{i}",
                status=VersionStatus.ACTIVE if i < 3 else VersionStatus.DRAFT,
                source_type="MANUAL",
                is_master_sample=(i == 0),
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            ProcessRouteStep(
                process_route_id=routes[i].id,
                sequence_no=i + 1,
                step_code=f"STEP-{i:02d}",
                step_name=f"步骤{i}",
                step_type="SPRAY",
                process_stage=STAGES[i].value,
                is_ai_feature_source=True,
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            ProcessRouteApplicability(
                process_route_id=routes[i].id,
                vehicle_model_id=models[i].id,
                color_id=colors[i].id,
                status="ACTIVE",
            )
            for i in range(N)
        ]
    )
    mat_specs = add_all(
        [
            MaterialSpecification(
                material_code=material_batches[i].material_code,
                characteristic_definition_id=mat_chars[i].id,
                method_id=test_methods[i].id,
                version="1.0",
                lower_limit=1.0,
                upper_limit=100.0,
                status="ACTIVE",
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            MaterialBatchTestResult(
                result_no=f"DEMO-MTR-{i:02d}",
                material_batch_id=material_batches[i].id,
                characteristic_definition_id=mat_chars[i].id,
                method_id=test_methods[i].id,
                specification_id=mat_specs[i].id,
                result_value=20.0 + i,
                unit=mat_chars[i].canonical_unit,
                tested_at=now - timedelta(days=i),
                reliability_status="VERIFIED",
                is_within_spec=True,
            )
            for i in range(N)
        ]
    )
    probes = add_all(
        [
            MeasurementProbe(
                instrument_id=instruments[i].id,
                code=f"PROBE-{i:02d}",
                name=f"探头{i}",
                probe_type="STANDARD",
                status="ACTIVE",
            )
            for i in range(N)
        ]
    )
    calibrations = add_all(
        [
            MeasurementCalibrationRecord(
                calibration_no=f"DEMO-CAL-{i:02d}",
                instrument_id=instruments[i].id,
                method_id=methods[i].id,
                reference_standard_id=refs[i].id,
                calibrated_at=now - timedelta(days=30 + i),
                valid_until=now + timedelta(days=180 - 20 * i),
                result="PASS",
                performed_by="domain-seed",
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            MeasurementMsaStudy(
                study_no=f"DEMO-MSA-{i:02d}",
                instrument_id=instruments[i].id,
                probe_id=probes[i].id,
                method_id=methods[i].id,
                quality_type=QUALITY_TYPES[i].value,
                metric_code=["THICKNESS", "L_STAR", "LW", "THICKNESS", "DOI"][i],
                study_type="GRR",
                sample_count=10,
                operator_count=2,
                repeat_count=3,
                grr_percent=8.0 + i,
                result="PASS",
                study_at=now - timedelta(days=i),
            )
            for i in range(N)
        ]
    )
    import_jobs = add_all(
        [
            FileImportJob(
                import_no=f"DEMO-JOB-{i:02d}",
                profile_id=import_profiles[i].id,
                domain_type=import_profiles[i].domain_type,
                source_filename=f"demo-import-{i}.csv",
                status="IMPORTED",
                row_count=10,
                valid_row_count=10,
                failed_row_count=0,
                submitted_by="domain-seed",
                submitted_at=now - timedelta(hours=i),
                imported_at=now - timedelta(hours=i),
            )
            for i in range(N)
        ]
    )
    submissions = add_all(
        [
            SupplierMaterialSubmission(
                submission_no=f"DEMO-SUB-{i:02d}",
                supplier="BASF-Demo",
                material_batch_id=material_batches[i].id,
                material_code=material_batches[i].material_code,
                material_name=material_batches[i].material_name,
                document_type="COA",
                profile_id=import_profiles[i].id,
                status="APPROVED",
                submitted_by="supplier",
                submitted_at=now - timedelta(days=i),
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            SupplierMaterialIssue(
                issue_no=f"DEMO-SMI-{i:02d}",
                submission_id=submissions[i].id,
                material_batch_id=material_batches[i].id,
                issue_type="SPEC_DEVIATION",
                severity=["LOW", "MEDIUM", "HIGH", "MEDIUM", "LOW"][i],
                status="OPEN" if i < 2 else "CLOSED",
                description=f"演示材料问题{i + 1}",
            )
            for i in range(N)
        ]
    )

    # ---- L4 recipe graph ----
    add_all(
        [
            ProgramVehicleModel(program_version_id=versions[i].id, vehicle_model_id=models[i].id)
            for i in range(N)
        ]
    )
    add_all(
        [ProgramColor(program_version_id=versions[i].id, color_id=colors[i].id) for i in range(N)]
    )
    brushes = add_all(
        [
            Brush(
                program_version_id=versions[0].id,
                brush_no=f"B{i:02d}",
                brush_table_no="TABLE-01",
                spray_position=f"POS-{i}",
                part_id=parts[i].id,
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            BrushParameter(
                brush_id=brushes[i].id,
                parameter_definition_id=param_defs[i].id,
                parameter_code=param_defs[i].code,
                parameter_name=param_defs[i].name,
                configured_value=50.0 + i,
                unit=param_defs[i].unit,
                soft_min=10.0,
                soft_max=120.0,
                is_recommendable=True,
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            BrushPointContribution(
                brush_id=brushes[i].id,
                measurement_point_id=points[i].id,
                overlap_ratio=0.6 + 0.05 * i,
                contribution_weight=0.2,
                source="EXPERT",
                version="1.0",
                is_approved=True,
            )
            for i in range(N)
        ]
    )
    device_cfgs = add_all(
        [
            ProgramDeviceConfiguration(
                program_version_id=versions[i].id,
                robot_id=robots[i].id,
                atomizer_id=atomizers[i].id,
                controller_id=controllers[i].id,
                configuration_version="1.0",
                status="ACTIVE",
            )
            for i in range(N)
        ]
    )
    trajectories = add_all(
        [
            TrajectoryProgram(
                program_version_id=versions[i].id,
                trajectory_code=f"TRAJ-{i:02d}",
                name=f"演示轨迹{i}",
                version="1.0",
                checksum=_hash(f"traj-{i}")[:32],
                status="ACTIVE",
            )
            for i in range(N)
        ]
    )
    segments = add_all(
        [
            TrajectoryPathSegment(
                trajectory_program_id=trajectories[i].id,
                segment_no=i + 1,
                name=f"段{i}",
                brush_id=brushes[i].id,
                part_id=parts[i].id,
                trigger_state="ON",
                configured_speed=400.0 + 10 * i,
                speed_unit="mm/s",
            )
            for i in range(N)
        ]
    )
    contrib_versions = add_all(
        [
            PointContributionVersion(
                program_version_id=versions[i].id,
                target_family=QUALITY_TYPES[i].value,
                version="1.0",
                method="EXPERT",
                status="ACTIVE",
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            PointContributionEntry(
                contribution_version_id=contrib_versions[i].id,
                measurement_point_id=points[i].id,
                brush_id=brushes[i].id,
                path_segment_id=None,
                source_key=f"brush:{brushes[i].brush_no}",
                overlap_ratio=0.7,
                contribution_weight=0.25,
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            ContributionValidationStudy(
                contribution_version_id=contrib_versions[i].id,
                study_no=f"CVS-{i:02d}",
                target_family=QUALITY_TYPES[i].value,
                method="DOE",
                status="APPROVED",
                sample_count=30,
                validation_score=0.9,
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            TrajectorySegmentGeometry(
                path_segment_id=segments[i].id,
                geometry_version="1.0",
                source_import_job_id=import_jobs[i].id,
                gun_distance=200.0 + i,
                overlap_ratio=0.5,
                status="ACTIVE",
            )
            for i in range(N)
        ]
    )

    # ---- L5 production ----
    runs = add_all(
        [
            ProductionRun(
                run_no=f"DEMO-RUN-{i:02d}",
                body_no=f"BODY-{1000 + i}",
                factory_id=factories[i].id,
                vehicle_model_id=models[i].id,
                color_id=colors[i].id,
                shift=["A", "B", "C", "A", "B"][i],
                started_at=now - timedelta(hours=6 * i),
                completed_at=None if i < 2 else now - timedelta(hours=6 * i - 2),
            )
            for i in range(N)
        ]
    )
    stage_runs = add_all(
        [
            ProductionStageRun(
                production_run_id=runs[i].id,
                process_stage=STAGES[i].value,
                program_version_id=versions[i].id,
                material_batch_id=material_batches[i].id,
                status="RUNNING" if i < 2 else "COMPLETED",
            )
            for i in range(N)
        ]
    )
    device_execs = add_all(
        [
            ProductionDeviceExecution(
                production_stage_run_id=stage_runs[i].id,
                device_configuration_id=device_cfgs[i].id,
                trajectory_program_id=trajectories[i].id,
                executed_checksum=trajectories[i].checksum,
                status="COMPLETED",
                started_at=now - timedelta(hours=5 * i),
                completed_at=now - timedelta(hours=5 * i - 1),
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            PathSegmentExecution(
                device_execution_id=device_execs[i].id,
                path_segment_id=segments[i].id,
                actual_speed=410.0 + i,
                speed_unit="mm/s",
                trigger_state="ON",
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            ActualParameter(
                production_stage_run_id=stage_runs[i].id,
                brush_id=brushes[i].id,
                parameter_definition_id=param_defs[i].id,
                parameter_code=param_defs[i].code,
                actual_value=51.0 + i,
                unit=param_defs[i].unit,
                sampled_at=now - timedelta(hours=4 * i),
                source_system="ROBOT",
            )
            for i in range(N)
        ]
    )

    # ---- L6 quality / features ----
    measurements = add_all(
        [
            QualityMeasurement(
                data_no=f"DEMO-QM-{i:02d}",
                production_run_id=runs[i].id,
                measurement_group_id=groups[i].id,
                measurement_point_id=points[i].id,
                quality_type=QUALITY_TYPES[i].value,
                data_type="TEST",
                measured_at=now - timedelta(hours=3 * i),
                measured_by="domain-seed",
                instrument_id=instruments[i].id,
                measurement_probe_id=probes[i].id,
                measurement_method_id=methods[i].id,
                calibration_record_id=calibrations[i].id,
                reliability_status="VERIFIED",
                is_valid=True,
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            QualityMetricValue(
                measurement_id=measurements[i].id,
                metric_code=["THICKNESS", "L_STAR", "LW", "THICKNESS", "DOI"][i],
                metric_name=["膜厚", "L*", "LW", "膜厚", "DOI"][i],
                raw_value=10.0 + i,
                unit=["μm", "-", "-", "μm", "-"][i],
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            MeasurementRepeatReading(
                measurement_id=measurements[i].id,
                repeat_no=1,
                metric_code=["THICKNESS", "L_STAR", "LW", "THICKNESS", "DOI"][i],
                raw_value=10.0 + i + 0.1,
                unit=["μm", "-", "-", "μm", "-"][i],
                is_valid=True,
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            QualityStandard(
                standard_no=f"DEMO-STD-{i:02d}",
                version="1.0",
                standard_type="PRODUCTION",
                quality_type=QUALITY_TYPES[i].value,
                metric_code=["THICKNESS", "L_STAR", "LW", "THICKNESS", "DOI"][i],
                vehicle_model_id=models[i].id,
                color_id=colors[i].id,
                min_value=5.0,
                max_value=50.0,
                unit=["μm", "-", "-", "μm", "-"][i],
                is_active=True,
            )
            for i in range(N)
        ]
    )
    feature_snaps = add_all(
        [
            PointFeatureSnapshot(
                production_run_id=runs[i].id,
                measurement_point_id=points[i].id,
                feature_set_version="fs-demo-1",
                target_family=QUALITY_TYPES[i].value,
                feature_values={"flow": 50.0 + i, "rpm": 30000 + 100 * i},
                lineage={"seed": True},
                completeness_score=0.95,
                generated_at=now - timedelta(hours=2 * i),
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            DatasetSplitMember(
                dataset_snapshot_id=datasets[i].id,
                point_feature_snapshot_id=feature_snaps[i].id,
                production_run_id=runs[i].id,
                measurement_point_id=points[i].id,
                target_measurement_id=measurements[i].id,
                group_value=runs[i].run_no,
                split="TRAIN" if i < 4 else "VALIDATION",
                target_value=10.0 + i,
                feature_values=feature_snaps[i].feature_values,
                occurred_at=measurements[i].measured_at,
            )
            for i in range(N)
        ]
    )

    # ---- L7 models / predictions ----
    model_versions = add_all(
        [
            ModelVersion(
                model_code=f"DEMO-MDL-{i:02d}",
                version="1.0",
                model_type=["THICKNESS", "COLOR", "ORANGE_PEEL", "THICKNESS", "ORANGE_PEEL"][i],
                target_metric=datasets[i].target_metric,
                feature_set_version="fs-demo-1",
                artifact_uri=f"demo://model/{i}",
                dataset_snapshot_id=datasets[i].id,
                model_payload={"algo": "ridge"},
                evaluation_metrics={"rmse": 0.5 + 0.1 * i, "r2": 0.8},
                training_sample_count=80 + i,
                trained_at=now - timedelta(days=i),
                status=VersionStatus.APPROVED if i < 3 else VersionStatus.DRAFT,
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            ModelValidationFold(
                model_version_id=model_versions[i].id,
                dataset_snapshot_id=datasets[i].id,
                validation_axis="TEMPORAL",
                fold_key=f"fold-{i}",
                train_sample_count=80,
                validation_sample_count=20,
                train_group_count=8,
                validation_group_count=2,
                metrics={"rmse": 0.5},
                status="COMPLETED",
                evaluated_at=now - timedelta(days=i),
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            ModelArtifact(
                model_version_id=model_versions[i].id,
                artifact_type="MODEL_PAYLOAD",
                artifact_uri=f"demo://artifact/{i}",
                storage_backend="MYSQL",
                payload_hash=_hash(f"artifact-{i}"),
                metadata_payload={"seed": True},
                status="REGISTERED",
                created_by="domain-seed",
                registered_at=now - timedelta(days=i),
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            ModelAcceptanceDecision(
                model_version_id=model_versions[i].id,
                dataset_snapshot_id=datasets[i].id,
                decision="ACCEPT" if i < 3 else "PENDING",
                criteria={"max_rmse": 1.0},
                checks={"rmse_ok": True},
                decided_by="domain-seed",
                decided_at=now - timedelta(days=i),
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            ModelApplicabilityScope(
                model_version_id=model_versions[i].id,
                factory_id=factories[i].id,
                vehicle_model_id=models[i].id,
                color_id=colors[i].id,
                status="ACTIVE",
                source="DATASET_DERIVED",
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            ModelOodPolicy(
                model_version_id=model_versions[i].id,
                max_abs_standardized_shift=3.0,
                max_outlier_feature_ratio=0.2,
                min_feature_completeness=0.8,
                action="BLOCK",
                status="ACTIVE",
            )
            for i in range(N)
        ]
    )
    predictions = add_all(
        [
            PredictionResult(
                model_version_id=model_versions[i].id,
                production_run_id=runs[i].id,
                measurement_point_id=points[i].id,
                metric_code=datasets[i].target_metric,
                predicted_value=11.0 + i,
                confidence=0.8,
                applicability_status="IN_SCOPE",
                ood_status="IN_DISTRIBUTION",
                predicted_at=now - timedelta(hours=i),
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            DiagnosisResult(
                prediction_result_id=predictions[i].id,
                production_run_id=runs[i].id,
                measurement_point_id=points[i].id,
                metric_code=datasets[i].target_metric,
                summary=f"演示诊断摘要{i + 1}",
                factor_contributions=[{"factor": "flow", "weight": 0.4}],
                confidence=0.75,
                causality_status="CORRELATION_ONLY",
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            ModelExplanation(
                model_version_id=model_versions[i].id,
                explanation_type="GLOBAL",
                target_metric=datasets[i].target_metric,
                feature_impacts={"flow": 0.4, "rpm": 0.3},
                generated_at=now - timedelta(hours=i),
                generated_by="domain-seed",
            )
            for i in range(N)
        ]
    )

    # ---- L8 closed loop / issues / integration ----
    recommendations = add_all(
        [
            Recommendation(
                recommendation_no=f"DEMO-REC-{i:02d}",
                production_run_id=runs[i].id,
                measurement_point_id=points[i].id,
                target_quality_type=QUALITY_TYPES[i].value,
                target_metric=datasets[i].target_metric,
                diagnosis_summary=f"演示推荐诊断{i + 1}",
                predicted_improvement=0.5 + 0.1 * i,
                confidence=0.7,
                status=RecommendationStatus.PENDING if i < 2 else RecommendationStatus.APPROVED,
                model_version=f"{model_versions[i].model_code}:{model_versions[i].version}",
                constraints_checked=True,
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            RecommendationAction(
                recommendation_id=recommendations[i].id,
                process_stage=STAGES[i].value,
                brush_no=brushes[i].brush_no,
                parameter_code=param_defs[i].code,
                parameter_name=param_defs[i].name,
                current_value=50.0 + i,
                recommended_value=55.0 + i,
                unit=param_defs[i].unit,
            )
            for i in range(N)
        ]
    )
    trials = add_all(
        [
            ControlledTrial(
                recommendation_id=recommendations[i].id,
                trial_no=f"DEMO-TRIAL-{i:02d}",
                production_run_id=runs[i].id,
                measurement_point_id=points[i].id,
                target_metric=datasets[i].target_metric,
                evidence_type="CONTROLLED_TRIAL",
                hypothesis=f"假设{i + 1}",
                expected_outcome=f"预期{i + 1}",
                risk_assessment="低风险",
                rollback_plan="回退到上一版本",
                sustained_observation_plan="观察 24h",
                constraint_evidence={"ok": True},
                status=["PLANNED", "APPROVED", "RUNNING", "COMPLETED", "COMPLETED"][i],
                requested_by="domain-seed",
                requested_at=now - timedelta(days=i),
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            ProgramRollbackExecution(
                rollback_no=f"DEMO-RB-{i:02d}",
                recommendation_id=recommendations[i].id,
                controlled_trial_id=trials[i].id,
                rollback_to_program_version_id=versions[i].id,
                rollback_reason=f"演示回滚原因{i + 1}",
                executed_by="domain-seed",
                executed_at=now - timedelta(hours=i),
                status="EXECUTED",
                action_snapshot={"action": "rollback"},
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            ClosedLoopEvaluation(
                recommendation_id=recommendations[i].id,
                baseline_value=10.0 + i,
                verified_value=11.0 + i,
                actual_improvement=1.0,
                is_effective=True,
                verified_at=now - timedelta(hours=i),
                verified_by="domain-seed",
                conclusion="有效",
            )
            for i in range(N)
        ]
    )
    tasks = add_all(
        [
            QualityIssueTask(
                task_no=f"DEMO-TASK-{i:02d}",
                title=f"演示质量问题{i}",
                task_type="QUALITY_ISSUE",
                status="OPEN" if i < 3 else "CLOSED",
                severity=["LOW", "MEDIUM", "HIGH", "MEDIUM", "LOW"][i],
                factory_id=factories[i].id,
                vehicle_model_id=models[i].id,
                color_id=colors[i].id,
                production_run_id=runs[i].id,
                measurement_point_id=points[i].id,
                created_by="domain-seed",
                problem_statement=f"演示问题描述{i + 1}",
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            QualityIssueEvidence(
                task_id=tasks[i].id,
                evidence_type="MEASUREMENT",
                source_type="QUALITY_MEASUREMENT",
                summary=f"演示证据{i + 1}",
                causality_status="CORRELATION_ONLY",
                created_by="domain-seed",
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            QualityIssueComment(
                task_id=tasks[i].id,
                author="domain-seed",
                comment_type="NOTE",
                body=f"演示评论{i + 1}",
            )
            for i in range(N)
        ]
    )
    add_all(
        [
            IntegrationEvent(
                event_no=f"DEMO-EVT-{i:02d}",
                endpoint_id=endpoints[i].id,
                source_event_id=f"SRC-{i:02d}",
                event_type="SYNC",
                direction=endpoints[i].direction,
                status="PROCESSED",
                payload={"demo": i + 1},
                attempt_count=1,
                processed_at=now - timedelta(minutes=10 * i),
            )
            for i in range(N)
        ]
    )

    # silence unused accept_policies / knowledge warnings in some linters
    _ = (accept_policies, knowledge)

    db.commit()
    return {
        "created": created,
        "skipped": False,
        "marker": SEED_MARKER_FACTORY_CODE,
        "rows_per_model": N,
    }


__all__ = ["SEED_MARKER_FACTORY_CODE", "seed_domain_demo_data"]
