from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.master_data import ResourceRead


class ProcessRouteCreate(BaseModel):
    factory_id: str
    route_code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    version: str = Field(min_length=1, max_length=32)
    route_type: str = Field(default="3C3B", pattern="^3C3B$")
    status: str = Field(default="DRAFT", pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$")
    bake_strategy: str | None = Field(default=None, max_length=120)
    source_uri: str | None = Field(default=None, max_length=500)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class ProcessRouteUpdate(BaseModel):
    factory_id: str | None = None
    route_code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    version: str | None = Field(default=None, min_length=1, max_length=32)
    route_type: str | None = Field(default=None, pattern="^3C3B$")
    status: str | None = Field(default=None, pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$")
    bake_strategy: str | None = Field(default=None, max_length=120)
    source_uri: str | None = Field(default=None, max_length=500)
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class ProcessRouteRead(ProcessRouteCreate, ResourceRead):
    approved_at: datetime | None = None


class ProcessRouteStepCreate(BaseModel):
    process_route_id: str
    sequence_no: int = Field(ge=1)
    step_code: str = Field(min_length=1, max_length=64)
    step_name: str = Field(min_length=1, max_length=160)
    step_type: str = Field(pattern="^(SPRAY_STAGE|FLASH|BAKE|INSPECTION|TRANSFER)$")
    coating_system: str | None = Field(default=None, pattern="^(MIDCOAT|BASECOAT|CLEARCOAT)$")
    process_stage: str | None = None
    station_code: str | None = Field(default=None, max_length=64)
    upstream_step_code: str | None = Field(default=None, max_length=64)
    downstream_step_code: str | None = Field(default=None, max_length=64)
    is_ai_feature_source: bool = False
    control_requirements: dict | None = None
    remark: str | None = None


class ProcessRouteStepUpdate(BaseModel):
    process_route_id: str | None = None
    sequence_no: int | None = Field(default=None, ge=1)
    step_code: str | None = Field(default=None, min_length=1, max_length=64)
    step_name: str | None = Field(default=None, min_length=1, max_length=160)
    step_type: str | None = Field(default=None, pattern="^(SPRAY_STAGE|FLASH|BAKE|INSPECTION|TRANSFER)$")
    coating_system: str | None = Field(default=None, pattern="^(MIDCOAT|BASECOAT|CLEARCOAT)$")
    process_stage: str | None = None
    station_code: str | None = Field(default=None, max_length=64)
    upstream_step_code: str | None = Field(default=None, max_length=64)
    downstream_step_code: str | None = Field(default=None, max_length=64)
    is_ai_feature_source: bool | None = None
    control_requirements: dict | None = None
    remark: str | None = None


class ProcessRouteStepRead(ProcessRouteStepCreate, ResourceRead):
    pass


class ProcessRouteApplicabilityCreate(BaseModel):
    process_route_id: str
    vehicle_model_id: str | None = None
    color_id: str | None = None
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|RETIRED)$")
    remark: str | None = None


class ProcessRouteApplicabilityUpdate(BaseModel):
    process_route_id: str | None = None
    vehicle_model_id: str | None = None
    color_id: str | None = None
    status: str | None = Field(default=None, pattern="^(ACTIVE|RETIRED)$")
    remark: str | None = None


class ProcessRouteApplicabilityRead(ProcessRouteApplicabilityCreate, ResourceRead):
    pass


class FileImportProfileCreate(BaseModel):
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=160)
    version: str = Field(min_length=1, max_length=32)
    domain_type: str = Field(
        pattern="^(DURR_DXQ|DURR_PLC|BYK_COLOR|BYK_ORANGE_PEEL|FISCHER_THICKNESS|MATERIAL_COA|MATERIAL_TDS)$"
    )
    parser_type: str = Field(default="CSV", pattern="^(CSV|XLSX|JSON|XML|DXQ_EXPORT)$")
    target_resource: str = Field(min_length=1, max_length=80)
    field_mapping: dict
    required_fields: list[str] = Field(default_factory=list)
    validation_rules: dict | None = None
    status: str = Field(default="DRAFT", pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$")
    source_uri: str | None = Field(default=None, max_length=500)
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class FileImportProfileUpdate(BaseModel):
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    version: str | None = Field(default=None, min_length=1, max_length=32)
    domain_type: str | None = Field(
        default=None,
        pattern="^(DURR_DXQ|DURR_PLC|BYK_COLOR|BYK_ORANGE_PEEL|FISCHER_THICKNESS|MATERIAL_COA|MATERIAL_TDS)$",
    )
    parser_type: str | None = Field(default=None, pattern="^(CSV|XLSX|JSON|XML|DXQ_EXPORT)$")
    target_resource: str | None = Field(default=None, min_length=1, max_length=80)
    field_mapping: dict | None = None
    required_fields: list[str] | None = None
    validation_rules: dict | None = None
    status: str | None = Field(default=None, pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$")
    source_uri: str | None = Field(default=None, max_length=500)
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class FileImportProfileRead(FileImportProfileCreate, ResourceRead):
    approved_at: datetime | None = None


class FileImportJobCreate(BaseModel):
    import_no: str = Field(min_length=1, max_length=64)
    profile_id: str
    domain_type: str = Field(max_length=48)
    source_filename: str = Field(min_length=1, max_length=240)
    source_uri: str | None = Field(default=None, max_length=500)
    source_checksum: str | None = Field(default=None, max_length=128)
    status: str = Field(default="PREVIEWED", pattern="^(PREVIEWED|VALIDATED|IMPORTED|FAILED|REPLAYED)$")
    row_count: int = Field(default=0, ge=0)
    valid_row_count: int = Field(default=0, ge=0)
    failed_row_count: int = Field(default=0, ge=0)
    preview_payload: dict | None = None
    error_report: dict | None = None
    submitted_by: str = Field(default="system", max_length=80)
    submitted_at: datetime | None = None
    imported_at: datetime | None = None
    replay_of_job_id: str | None = None
    remark: str | None = None


class FileImportJobUpdate(BaseModel):
    status: str | None = Field(default=None, pattern="^(PREVIEWED|VALIDATED|IMPORTED|FAILED|REPLAYED)$")
    row_count: int | None = Field(default=None, ge=0)
    valid_row_count: int | None = Field(default=None, ge=0)
    failed_row_count: int | None = Field(default=None, ge=0)
    preview_payload: dict | None = None
    error_report: dict | None = None
    imported_at: datetime | None = None
    remark: str | None = None


class FileImportJobRead(FileImportJobCreate, ResourceRead):
    submitted_at: datetime


class FileImportPreviewRequest(BaseModel):
    profile_id: str
    source_filename: str = Field(min_length=1, max_length=240)
    content_base64: str = Field(min_length=1)
    import_no: str | None = Field(default=None, max_length=64)
    source_uri: str | None = Field(default=None, max_length=500)
    source_checksum: str | None = Field(default=None, max_length=128)
    submitted_by: str = Field(default="system", max_length=80)
    remark: str | None = None


class FileImportReplayRequest(BaseModel):
    import_no: str | None = Field(default=None, max_length=64)
    submitted_by: str = Field(default="system", max_length=80)
    remark: str | None = None


class MeasurementProbeCreate(BaseModel):
    instrument_id: str
    code: str = Field(min_length=1, max_length=64)
    name: str = Field(min_length=1, max_length=120)
    probe_type: str = Field(min_length=1, max_length=64)
    serial_no: str | None = Field(default=None, max_length=120)
    substrate_type: str | None = Field(default=None, max_length=80)
    geometry_class: str | None = Field(default=None, max_length=80)
    layer_scope: str | None = Field(default=None, max_length=80)
    status: str = Field(default="ACTIVE", pattern="^(ACTIVE|MAINTENANCE|RETIRED)$")
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    remark: str | None = None


class MeasurementProbeUpdate(BaseModel):
    instrument_id: str | None = None
    code: str | None = Field(default=None, min_length=1, max_length=64)
    name: str | None = Field(default=None, min_length=1, max_length=120)
    probe_type: str | None = Field(default=None, min_length=1, max_length=64)
    serial_no: str | None = Field(default=None, max_length=120)
    substrate_type: str | None = Field(default=None, max_length=80)
    geometry_class: str | None = Field(default=None, max_length=80)
    layer_scope: str | None = Field(default=None, max_length=80)
    status: str | None = Field(default=None, pattern="^(ACTIVE|MAINTENANCE|RETIRED)$")
    valid_from: datetime | None = None
    valid_until: datetime | None = None
    remark: str | None = None


class MeasurementProbeRead(MeasurementProbeCreate, ResourceRead):
    pass


class MeasurementMsaStudyCreate(BaseModel):
    study_no: str = Field(min_length=1, max_length=64)
    instrument_id: str
    probe_id: str | None = None
    method_id: str | None = None
    quality_type: str
    metric_code: str = Field(min_length=1, max_length=64)
    study_type: str = Field(default="GRR", max_length=32)
    sample_count: int = Field(ge=1)
    operator_count: int = Field(ge=1)
    repeat_count: int = Field(ge=1)
    grr_percent: float | None = None
    ndc: float | None = None
    result: str = Field(default="PENDING", pattern="^(PENDING|PASS|FAIL)$")
    study_at: datetime
    approved_by: str | None = Field(default=None, max_length=80)
    raw_results: dict | None = None
    remark: str | None = None


class MeasurementMsaStudyUpdate(BaseModel):
    instrument_id: str | None = None
    probe_id: str | None = None
    method_id: str | None = None
    quality_type: str | None = None
    metric_code: str | None = Field(default=None, min_length=1, max_length=64)
    study_type: str | None = Field(default=None, max_length=32)
    sample_count: int | None = Field(default=None, ge=1)
    operator_count: int | None = Field(default=None, ge=1)
    repeat_count: int | None = Field(default=None, ge=1)
    grr_percent: float | None = None
    ndc: float | None = None
    result: str | None = Field(default=None, pattern="^(PENDING|PASS|FAIL)$")
    study_at: datetime | None = None
    approved_by: str | None = Field(default=None, max_length=80)
    raw_results: dict | None = None
    remark: str | None = None


class MeasurementMsaStudyRead(MeasurementMsaStudyCreate, ResourceRead):
    approved_at: datetime | None = None


class QualityIssueTaskCreate(BaseModel):
    task_no: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=180)
    task_type: str = Field(default="QUALITY_ISSUE", pattern="^(QUALITY_ISSUE|PROCESS_DEBUG|SUPPLIER_FEEDBACK|CONTROLLED_TRIAL)$")
    status: str = Field(default="OPEN", pattern="^(OPEN|TRIAGE|IN_TRIAL|WAITING_SUPPLIER|VERIFIED|CLOSED)$")
    severity: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    factory_id: str | None = None
    vehicle_model_id: str | None = None
    color_id: str | None = None
    production_run_id: str | None = None
    measurement_point_id: str | None = None
    quality_measurement_id: str | None = None
    material_batch_id: str | None = None
    recommendation_id: str | None = None
    controlled_trial_id: str | None = None
    process_stage: str | None = None
    target_quality_type: str | None = None
    target_metric: str | None = Field(default=None, max_length=64)
    owner_role: str | None = Field(default=None, max_length=64)
    owner_user_id: str | None = None
    created_by: str = Field(min_length=1, max_length=80)
    due_at: datetime | None = None
    problem_statement: str = Field(min_length=1)
    hypothesis: str | None = None
    suspected_cause: str | None = None
    conclusion: str | None = None
    causality_status: str = Field(default="CORRELATION_ONLY", pattern="^(CORRELATION_ONLY|RULE_SUPPORTED|DOE_SUPPORTED|VERIFIED_CAUSE)$")
    data_quality_status: str = Field(default="PENDING", max_length=32)
    material_status: str = Field(default="PENDING", max_length=32)
    durr_execution_status: str = Field(default="PENDING", max_length=32)
    ai_summary: str | None = None
    tags: list[str] | None = None


class QualityIssueTaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    task_type: str | None = Field(default=None, pattern="^(QUALITY_ISSUE|PROCESS_DEBUG|SUPPLIER_FEEDBACK|CONTROLLED_TRIAL)$")
    status: str | None = Field(default=None, pattern="^(OPEN|TRIAGE|IN_TRIAL|WAITING_SUPPLIER|VERIFIED|CLOSED)$")
    severity: str | None = Field(default=None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    factory_id: str | None = None
    vehicle_model_id: str | None = None
    color_id: str | None = None
    production_run_id: str | None = None
    measurement_point_id: str | None = None
    quality_measurement_id: str | None = None
    material_batch_id: str | None = None
    recommendation_id: str | None = None
    controlled_trial_id: str | None = None
    process_stage: str | None = None
    target_quality_type: str | None = None
    target_metric: str | None = Field(default=None, max_length=64)
    owner_role: str | None = Field(default=None, max_length=64)
    owner_user_id: str | None = None
    due_at: datetime | None = None
    problem_statement: str | None = None
    hypothesis: str | None = None
    suspected_cause: str | None = None
    conclusion: str | None = None
    causality_status: str | None = Field(default=None, pattern="^(CORRELATION_ONLY|RULE_SUPPORTED|DOE_SUPPORTED|VERIFIED_CAUSE)$")
    data_quality_status: str | None = Field(default=None, max_length=32)
    material_status: str | None = Field(default=None, max_length=32)
    durr_execution_status: str | None = Field(default=None, max_length=32)
    ai_summary: str | None = None
    tags: list[str] | None = None


class QualityIssueTaskRead(QualityIssueTaskCreate, ResourceRead):
    closed_at: datetime | None = None


class QualityIssueEvidenceCreate(BaseModel):
    evidence_type: str = Field(min_length=1, max_length=48)
    source_type: str = Field(min_length=1, max_length=64)
    source_id: str | None = Field(default=None, max_length=36)
    summary: str = Field(min_length=1)
    evidence_payload: dict | None = None
    confidence: float | None = Field(default=None, ge=0, le=1)
    causality_status: str = Field(default="CORRELATION_ONLY", pattern="^(CORRELATION_ONLY|RULE_SUPPORTED|DOE_SUPPORTED|VERIFIED_CAUSE)$")
    created_by: str = Field(min_length=1, max_length=80)


class QualityIssueEvidenceRead(QualityIssueEvidenceCreate, ResourceRead):
    task_id: str


class QualityIssueCommentCreate(BaseModel):
    author: str = Field(min_length=1, max_length=80)
    role: str | None = Field(default=None, max_length=64)
    comment_type: str = Field(default="COMMENT", max_length=32)
    body: str = Field(min_length=1)


class QualityIssueCommentRead(QualityIssueCommentCreate, ResourceRead):
    task_id: str


class EngineeringKnowledgeEntryCreate(BaseModel):
    entry_code: str = Field(min_length=1, max_length=64)
    version: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=180)
    category: str = Field(min_length=1, max_length=48)
    target_quality_type: str | None = None
    metric_code: str | None = Field(default=None, max_length=64)
    symptom_pattern: str = Field(min_length=1)
    diagnosis_rule: str = Field(min_length=1)
    recommended_checks: dict = Field(default_factory=dict)
    related_parameters: list[str] = Field(default_factory=list)
    evidence_level: str = Field(default="RULE", pattern="^(RULE|SIMULATION|DOE|CONTROLLED_CHANGE|VERIFIED_CAUSE)$")
    status: str = Field(default="DRAFT", pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$")
    source_uri: str | None = Field(default=None, max_length=500)
    created_by: str = Field(min_length=1, max_length=80)
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class EngineeringKnowledgeEntryUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=180)
    category: str | None = Field(default=None, min_length=1, max_length=48)
    target_quality_type: str | None = None
    metric_code: str | None = Field(default=None, max_length=64)
    symptom_pattern: str | None = None
    diagnosis_rule: str | None = None
    recommended_checks: dict | None = None
    related_parameters: list[str] | None = None
    evidence_level: str | None = Field(default=None, pattern="^(RULE|SIMULATION|DOE|CONTROLLED_CHANGE|VERIFIED_CAUSE)$")
    status: str | None = Field(default=None, pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$")
    source_uri: str | None = Field(default=None, max_length=500)
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class EngineeringKnowledgeEntryRead(EngineeringKnowledgeEntryCreate, ResourceRead):
    approved_at: datetime | None = None


class SupplierMaterialSubmissionCreate(BaseModel):
    submission_no: str = Field(min_length=1, max_length=64)
    supplier: str = Field(min_length=1, max_length=120)
    material_batch_id: str | None = None
    material_code: str = Field(min_length=1, max_length=64)
    material_name: str | None = Field(default=None, max_length=120)
    document_type: str = Field(pattern="^(COA|TDS|MSDS|DOE)$")
    source_uri: str | None = Field(default=None, max_length=500)
    profile_id: str | None = None
    status: str = Field(default="SUBMITTED", pattern="^(SUBMITTED|VALIDATED|ACCEPTED|REJECTED|SUPERSEDED)$")
    submitted_by: str = Field(min_length=1, max_length=80)
    submitted_at: datetime | None = None
    reviewed_by: str | None = Field(default=None, max_length=80)
    reviewed_at: datetime | None = None
    field_values: dict | None = None
    validation_result: dict | None = None
    deviation_decision: str | None = Field(default=None, max_length=32)
    remark: str | None = None


class SupplierMaterialSubmissionUpdate(BaseModel):
    supplier: str | None = Field(default=None, min_length=1, max_length=120)
    material_batch_id: str | None = None
    material_code: str | None = Field(default=None, min_length=1, max_length=64)
    material_name: str | None = Field(default=None, max_length=120)
    document_type: str | None = Field(default=None, pattern="^(COA|TDS|MSDS|DOE)$")
    source_uri: str | None = Field(default=None, max_length=500)
    profile_id: str | None = None
    status: str | None = Field(default=None, pattern="^(SUBMITTED|VALIDATED|ACCEPTED|REJECTED|SUPERSEDED)$")
    reviewed_by: str | None = Field(default=None, max_length=80)
    reviewed_at: datetime | None = None
    field_values: dict | None = None
    validation_result: dict | None = None
    deviation_decision: str | None = Field(default=None, max_length=32)
    remark: str | None = None


class SupplierMaterialSubmissionRead(SupplierMaterialSubmissionCreate, ResourceRead):
    submitted_at: datetime


class SupplierMaterialIssueCreate(BaseModel):
    issue_no: str = Field(min_length=1, max_length=64)
    submission_id: str | None = None
    material_batch_id: str | None = None
    issue_type: str = Field(min_length=1, max_length=48)
    severity: str = Field(default="MEDIUM", pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    status: str = Field(default="OPEN", pattern="^(OPEN|WAITING_SUPPLIER|CONTAINED|CLOSED)$")
    description: str = Field(min_length=1)
    containment_action: str | None = None
    supplier_response: str | None = None
    resolution: str | None = None
    owner: str | None = Field(default=None, max_length=80)
    due_at: datetime | None = None


class SupplierMaterialIssueUpdate(BaseModel):
    issue_type: str | None = Field(default=None, min_length=1, max_length=48)
    severity: str | None = Field(default=None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    status: str | None = Field(default=None, pattern="^(OPEN|WAITING_SUPPLIER|CONTAINED|CLOSED)$")
    description: str | None = None
    containment_action: str | None = None
    supplier_response: str | None = None
    resolution: str | None = None
    owner: str | None = Field(default=None, max_length=80)
    due_at: datetime | None = None


class SupplierMaterialIssueRead(SupplierMaterialIssueCreate, ResourceRead):
    closed_at: datetime | None = None


class ContributionValidationStudyCreate(BaseModel):
    contribution_version_id: str
    study_no: str = Field(min_length=1, max_length=64)
    target_family: str
    method: str = Field(pattern="^(EXPERT|DXQ_SIMULATION|DOE|DEPOSITION_MODEL)$")
    status: str = Field(default="DRAFT", pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$")
    sample_count: int | None = Field(default=None, ge=0)
    validation_score: float | None = Field(default=None, ge=0, le=1)
    evidence_uri: str | None = Field(default=None, max_length=500)
    evidence_payload: dict | None = None
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class ContributionValidationStudyUpdate(BaseModel):
    target_family: str | None = None
    method: str | None = Field(default=None, pattern="^(EXPERT|DXQ_SIMULATION|DOE|DEPOSITION_MODEL)$")
    status: str | None = Field(default=None, pattern="^(DRAFT|APPROVED|ACTIVE|RETIRED)$")
    sample_count: int | None = Field(default=None, ge=0)
    validation_score: float | None = Field(default=None, ge=0, le=1)
    evidence_uri: str | None = Field(default=None, max_length=500)
    evidence_payload: dict | None = None
    approved_by: str | None = Field(default=None, max_length=80)
    remark: str | None = None


class ContributionValidationStudyRead(ContributionValidationStudyCreate, ResourceRead):
    approved_at: datetime | None = None


class TrajectorySegmentGeometryCreate(BaseModel):
    path_segment_id: str
    geometry_version: str = Field(min_length=1, max_length=32)
    source_import_job_id: str | None = None
    start_position: dict | None = None
    end_position: dict | None = None
    orientation: dict | None = None
    normal_vector: dict | None = None
    gun_distance: float | None = None
    path_spacing: float | None = None
    overlap_ratio: float | None = Field(default=None, ge=0, le=1)
    collision_risk_score: float | None = Field(default=None, ge=0, le=1)
    status: str = Field(default="DRAFT", pattern="^(DRAFT|VALIDATED|ACTIVE|RETIRED)$")
    evidence_uri: str | None = Field(default=None, max_length=500)
    remark: str | None = None


class TrajectorySegmentGeometryUpdate(BaseModel):
    source_import_job_id: str | None = None
    start_position: dict | None = None
    end_position: dict | None = None
    orientation: dict | None = None
    normal_vector: dict | None = None
    gun_distance: float | None = None
    path_spacing: float | None = None
    overlap_ratio: float | None = Field(default=None, ge=0, le=1)
    collision_risk_score: float | None = Field(default=None, ge=0, le=1)
    status: str | None = Field(default=None, pattern="^(DRAFT|VALIDATED|ACTIVE|RETIRED)$")
    evidence_uri: str | None = Field(default=None, max_length=500)
    remark: str | None = None


class TrajectorySegmentGeometryRead(TrajectorySegmentGeometryCreate, ResourceRead):
    pass


class ModelExplanationCreate(BaseModel):
    model_version_id: str
    prediction_result_id: str | None = None
    explanation_type: str = Field(pattern="^(SHAP|SENSITIVITY|UNCERTAINTY|FEATURE_IMPORTANCE)$")
    target_metric: str = Field(min_length=1, max_length=64)
    feature_impacts: dict = Field(default_factory=dict)
    sensitivity_grid: dict | None = None
    uncertainty: dict | None = None
    generated_at: datetime | None = None
    generated_by: str = Field(default="system", max_length=80)


class ModelExplanationRead(ModelExplanationCreate, ResourceRead):
    generated_at: datetime
