from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.referential_integrity import check_fk, check_delete_safe
from app.db.session import get_db
from app.domain.scope_policy import ScopeViolation, require_approved_quality_type
from app.models.domain import (
    Brush,
    DurrApplicationController,
    DurrRobot,
    DurrRotaryAtomizer,
    Factory,
    MeasurementPoint,
    Part,
    PathSegmentExecution,
    PointContributionEntry,
    PointContributionVersion,
    ProductionDeviceExecution,
    ProductionStageRun,
    ProgramDeviceConfiguration,
    SprayProgramVersion,
    TrajectoryPathSegment,
    TrajectoryProgram,
)
from app.schemas.process import (
    DurrAtomizerCreate,
    DurrAtomizerRead,
    DurrAtomizerUpdate,
    DurrControllerCreate,
    DurrControllerRead,
    DurrControllerUpdate,
    DurrRobotCreate,
    DurrRobotRead,
    DurrRobotUpdate,
    PathSegmentExecutionCreate,
    PathSegmentExecutionRead,
    PointContributionEntryCreate,
    PointContributionEntryRead,
    PointContributionEntryUpdate,
    PointContributionVersionCreate,
    PointContributionVersionRead,
    PointContributionVersionUpdate,
    ProductionDeviceExecutionCreate,
    ProductionDeviceExecutionRead,
    ProductionDeviceExecutionUpdate,
    ProgramDeviceConfigurationCreate,
    ProgramDeviceConfigurationRead,
    ProgramDeviceConfigurationUpdate,
    TrajectoryPathSegmentCreate,
    TrajectoryPathSegmentRead,
    TrajectoryPathSegmentUpdate,
    TrajectoryProgramCreate,
    TrajectoryProgramRead,
    TrajectoryProgramUpdate,
)

router = APIRouter(prefix="/robot-governance", tags=["robot-trajectory-governance"])


def _required(db: Session, model: type, resource_id: str, label: str):
    resource = db.get(model, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"{label}不存在")
    return resource


def _save(db: Session, resource):
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def _delete(db: Session, resource, label: str) -> Response:
    try:
        db.delete(resource)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"{label}已被程序、贡献或生产实绩引用，请保留追溯或先解除关联",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _validate_quality_type(value: str) -> None:
    try:
        require_approved_quality_type(value)
    except ScopeViolation as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


def _validate_time_range(start: datetime | None, end: datetime | None) -> None:
    if start and end:
        start_value = start.replace(tzinfo=UTC) if start.tzinfo is None else start.astimezone(UTC)
        end_value = end.replace(tzinfo=UTC) if end.tzinfo is None else end.astimezone(UTC)
        if end_value < start_value:
            raise HTTPException(status_code=422, detail="完成时间不能早于开始时间")


def _unique_device(
    db: Session,
    model: type,
    factory_id: str,
    code: str,
    serial_no: str,
    resource_id: str | None = None,
) -> None:
    conditions = [
        or_(
            (model.factory_id == factory_id) & (model.code == code),
            model.serial_no == serial_no,
        )
    ]
    if resource_id:
        conditions.append(model.id != resource_id)
    if db.scalar(select(model).where(*conditions)):
        raise HTTPException(status_code=409, detail="同工厂设备代码或序列号已存在")


def _activate_single_version(
    db: Session,
    model: type,
    resource,
    status_value: str,
    *scope_conditions,
) -> None:
    if status_value in {"APPROVED", "ACTIVE"}:
        resource.approved_at = datetime.now(UTC)
    if status_value == "ACTIVE":
        for active in db.scalars(
            select(model).where(
                *scope_conditions,
                model.status == "ACTIVE",
                model.id != resource.id,
            )
        ):
            active.status = "RETIRED"


def _validate_device_configuration(db: Session, values: dict) -> None:
    _required(
        db, SprayProgramVersion, values["program_version_id"], "喷涂程序版本"
    )
    robot = _required(db, DurrRobot, values["robot_id"], "Dürr 机器人")
    atomizer = _required(db, DurrRotaryAtomizer, values["atomizer_id"], "Dürr 旋杯")
    controller = _required(
        db, DurrApplicationController, values["controller_id"], "Dürr 应用控制器"
    )
    if len({robot.factory_id, atomizer.factory_id, controller.factory_id}) != 1:
        raise HTTPException(status_code=422, detail="机器人、旋杯和控制器必须属于同一工厂")
    if atomizer.controller_id and atomizer.controller_id != controller.id:
        raise HTTPException(status_code=422, detail="旋杯绑定的控制器与设备配置不一致")


def _entry_source(
    db: Session,
    contribution_version: PointContributionVersion,
    brush_id: str | None,
    path_segment_id: str | None,
) -> str:
    if bool(brush_id) == bool(path_segment_id):
        raise HTTPException(status_code=422, detail="贡献条目必须且只能选择刷子或路径段之一")
    if brush_id:
        brush = _required(db, Brush, brush_id, "刷子")
        if brush.program_version_id != contribution_version.program_version_id:
            raise HTTPException(status_code=422, detail="刷子不属于贡献版本对应的程序版本")
        return f"BRUSH:{brush_id}"
    segment = _required(db, TrajectoryPathSegment, path_segment_id, "路径段")
    trajectory = _required(db, TrajectoryProgram, segment.trajectory_program_id, "轨迹程序")
    if trajectory.program_version_id != contribution_version.program_version_id:
        raise HTTPException(status_code=422, detail="路径段不属于贡献版本对应的程序版本")
    return f"PATH:{path_segment_id}"


@router.get("/summary")
def robot_governance_summary(db: Session = Depends(get_db)) -> dict:
    def count(model: type) -> int:
        return int(db.scalar(select(func.count()).select_from(model)) or 0)

    return {
        "robots": count(DurrRobot),
        "controllers": count(DurrApplicationController),
        "atomizers": count(DurrRotaryAtomizer),
        "device_configurations": count(ProgramDeviceConfiguration),
        "active_device_configurations": int(
            db.scalar(
                select(func.count())
                .select_from(ProgramDeviceConfiguration)
                .where(ProgramDeviceConfiguration.status == "ACTIVE")
            )
            or 0
        ),
        "trajectory_programs": count(TrajectoryProgram),
        "path_segments": count(TrajectoryPathSegment),
        "contribution_versions": count(PointContributionVersion),
        "active_contribution_versions": int(
            db.scalar(
                select(func.count())
                .select_from(PointContributionVersion)
                .where(PointContributionVersion.status == "ACTIVE")
            )
            or 0
        ),
        "contribution_entries": count(PointContributionEntry),
        "device_executions": count(ProductionDeviceExecution),
        "checksum_mismatches": int(
            db.scalar(
                select(func.count())
                .select_from(ProductionDeviceExecution)
                .where(ProductionDeviceExecution.status == "CHECKSUM_MISMATCH")
            )
            or 0
        ),
    }


@router.get("/robots", response_model=list[DurrRobotRead])
def list_robots(db: Session = Depends(get_db)) -> list[DurrRobot]:
    return list(db.scalars(select(DurrRobot).order_by(DurrRobot.code)))


@router.post("/robots", response_model=DurrRobotRead, status_code=status.HTTP_201_CREATED)
def create_robot(payload: DurrRobotCreate, db: Session = Depends(get_db)) -> DurrRobot:
    check_fk(db, Factory, payload.factory_id, "工厂")
    _required(db, Factory, payload.factory_id, "工厂")
    _unique_device(db, DurrRobot, payload.factory_id, payload.code, payload.serial_no)
    return _save(db, DurrRobot(**payload.model_dump()))


@router.patch("/robots/{resource_id}", response_model=DurrRobotRead)
def update_robot(
    resource_id: str, payload: DurrRobotUpdate, db: Session = Depends(get_db)
) -> DurrRobot:
    resource = _required(db, DurrRobot, resource_id, "Dürr 机器人")
    changes = payload.model_dump(exclude_unset=True)
    factory_id = changes.get("factory_id", resource.factory_id)
    _required(db, Factory, factory_id, "工厂")
    _unique_device(
        db,
        DurrRobot,
        factory_id,
        changes.get("code", resource.code),
        changes.get("serial_no", resource.serial_no),
        resource_id,
    )
    for field, value in changes.items():
        setattr(resource, field, value)
    return _save(db, resource)


@router.delete("/robots/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_robot(resource_id: str, db: Session = Depends(get_db)) -> Response:
    resource = _required(db, DurrRobot, resource_id, "Dürr 机器人")
    check_delete_safe(db, ProgramDeviceConfiguration, ProgramDeviceConfiguration.robot_id, resource_id, "Dürr 机器人")
    return _delete(db, resource, "Dürr 机器人")


@router.get("/controllers", response_model=list[DurrControllerRead])
def list_controllers(db: Session = Depends(get_db)) -> list[DurrApplicationController]:
    return list(
        db.scalars(select(DurrApplicationController).order_by(DurrApplicationController.code))
    )


@router.post(
    "/controllers", response_model=DurrControllerRead, status_code=status.HTTP_201_CREATED
)
def create_controller(
    payload: DurrControllerCreate, db: Session = Depends(get_db)
) -> DurrApplicationController:
    check_fk(db, Factory, payload.factory_id, "工厂")
    _required(db, Factory, payload.factory_id, "工厂")
    _unique_device(
        db,
        DurrApplicationController,
        payload.factory_id,
        payload.code,
        payload.serial_no,
    )
    return _save(db, DurrApplicationController(**payload.model_dump()))


@router.patch("/controllers/{resource_id}", response_model=DurrControllerRead)
def update_controller(
    resource_id: str, payload: DurrControllerUpdate, db: Session = Depends(get_db)
) -> DurrApplicationController:
    resource = _required(db, DurrApplicationController, resource_id, "Dürr 应用控制器")
    changes = payload.model_dump(exclude_unset=True)
    factory_id = changes.get("factory_id", resource.factory_id)
    _required(db, Factory, factory_id, "工厂")
    _unique_device(
        db,
        DurrApplicationController,
        factory_id,
        changes.get("code", resource.code),
        changes.get("serial_no", resource.serial_no),
        resource_id,
    )
    for field, value in changes.items():
        setattr(resource, field, value)
    return _save(db, resource)


@router.delete("/controllers/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_controller(resource_id: str, db: Session = Depends(get_db)) -> Response:
    resource = _required(db, DurrApplicationController, resource_id, "Dürr 应用控制器")
    check_delete_safe(db, DurrRotaryAtomizer, DurrRotaryAtomizer.controller_id, resource_id, "Dürr 应用控制器")
    check_delete_safe(db, ProgramDeviceConfiguration, ProgramDeviceConfiguration.controller_id, resource_id, "Dürr 应用控制器")
    return _delete(db, resource, "Dürr 应用控制器")


@router.get("/atomizers", response_model=list[DurrAtomizerRead])
def list_atomizers(db: Session = Depends(get_db)) -> list[DurrRotaryAtomizer]:
    return list(db.scalars(select(DurrRotaryAtomizer).order_by(DurrRotaryAtomizer.code)))


@router.post(
    "/atomizers", response_model=DurrAtomizerRead, status_code=status.HTTP_201_CREATED
)
def create_atomizer(
    payload: DurrAtomizerCreate, db: Session = Depends(get_db)
) -> DurrRotaryAtomizer:
    check_fk(db, Factory, payload.factory_id, "工厂")
    _required(db, Factory, payload.factory_id, "工厂")
    if payload.controller_id:
        controller = _required(
            db, DurrApplicationController, payload.controller_id, "Dürr 应用控制器"
        )
        if controller.factory_id != payload.factory_id:
            raise HTTPException(status_code=422, detail="旋杯与控制器必须属于同一工厂")
    _unique_device(
        db, DurrRotaryAtomizer, payload.factory_id, payload.code, payload.serial_no
    )
    return _save(db, DurrRotaryAtomizer(**payload.model_dump()))


@router.patch("/atomizers/{resource_id}", response_model=DurrAtomizerRead)
def update_atomizer(
    resource_id: str, payload: DurrAtomizerUpdate, db: Session = Depends(get_db)
) -> DurrRotaryAtomizer:
    resource = _required(db, DurrRotaryAtomizer, resource_id, "Dürr 旋杯")
    changes = payload.model_dump(exclude_unset=True)
    factory_id = changes.get("factory_id", resource.factory_id)
    _required(db, Factory, factory_id, "工厂")
    controller_id = changes.get("controller_id", resource.controller_id)
    if controller_id:
        controller = _required(db, DurrApplicationController, controller_id, "Dürr 应用控制器")
        if controller.factory_id != factory_id:
            raise HTTPException(status_code=422, detail="旋杯与控制器必须属于同一工厂")
    _unique_device(
        db,
        DurrRotaryAtomizer,
        factory_id,
        changes.get("code", resource.code),
        changes.get("serial_no", resource.serial_no),
        resource_id,
    )
    for field, value in changes.items():
        setattr(resource, field, value)
    return _save(db, resource)


@router.delete("/atomizers/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_atomizer(resource_id: str, db: Session = Depends(get_db)) -> Response:
    resource = _required(db, DurrRotaryAtomizer, resource_id, "Dürr 旋杯")
    check_delete_safe(db, ProgramDeviceConfiguration, ProgramDeviceConfiguration.atomizer_id, resource_id, "Dürr 旋杯")
    return _delete(db, resource, "Dürr 旋杯")


@router.get("/device-configurations", response_model=list[ProgramDeviceConfigurationRead])
def list_device_configurations(
    program_version_id: str | None = None, db: Session = Depends(get_db)
) -> list[ProgramDeviceConfiguration]:
    query = select(ProgramDeviceConfiguration)
    if program_version_id:
        query = query.where(ProgramDeviceConfiguration.program_version_id == program_version_id)
    return list(db.scalars(query.order_by(ProgramDeviceConfiguration.created_at.desc())))


@router.post(
    "/device-configurations",
    response_model=ProgramDeviceConfigurationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_device_configuration(
    payload: ProgramDeviceConfigurationCreate, db: Session = Depends(get_db)
) -> ProgramDeviceConfiguration:
    check_fk(db, SprayProgramVersion, payload.program_version_id, "喷涂程序版本")
    check_fk(db, DurrRobot, payload.robot_id, "Dürr 机器人")
    check_fk(db, DurrRotaryAtomizer, payload.atomizer_id, "Dürr 旋杯")
    check_fk(db, DurrApplicationController, payload.controller_id, "Dürr 应用控制器")
    values = payload.model_dump()
    _validate_device_configuration(db, values)
    if db.scalar(
        select(ProgramDeviceConfiguration).where(
            ProgramDeviceConfiguration.program_version_id == payload.program_version_id,
            ProgramDeviceConfiguration.configuration_version == payload.configuration_version,
        )
    ):
        raise HTTPException(status_code=409, detail="程序版本下设备配置版本已存在")
    resource = ProgramDeviceConfiguration(**values)
    db.add(resource)
    db.flush()
    _activate_single_version(
        db,
        ProgramDeviceConfiguration,
        resource,
        resource.status,
        ProgramDeviceConfiguration.program_version_id == resource.program_version_id,
    )
    db.commit()
    db.refresh(resource)
    return resource


@router.patch(
    "/device-configurations/{resource_id}", response_model=ProgramDeviceConfigurationRead
)
def update_device_configuration(
    resource_id: str,
    payload: ProgramDeviceConfigurationUpdate,
    db: Session = Depends(get_db),
) -> ProgramDeviceConfiguration:
    resource = _required(db, ProgramDeviceConfiguration, resource_id, "程序设备配置")
    changes = payload.model_dump(exclude_unset=True)
    values = {
        "program_version_id": resource.program_version_id,
        "robot_id": resource.robot_id,
        "atomizer_id": resource.atomizer_id,
        "controller_id": resource.controller_id,
        **changes,
    }
    _validate_device_configuration(db, values)
    if db.scalar(
        select(ProgramDeviceConfiguration).where(
            ProgramDeviceConfiguration.program_version_id == values["program_version_id"],
            ProgramDeviceConfiguration.configuration_version
            == changes.get("configuration_version", resource.configuration_version),
            ProgramDeviceConfiguration.id != resource_id,
        )
    ):
        raise HTTPException(status_code=409, detail="程序版本下设备配置版本已存在")
    for field, value in changes.items():
        setattr(resource, field, value)
    _activate_single_version(
        db,
        ProgramDeviceConfiguration,
        resource,
        resource.status,
        ProgramDeviceConfiguration.program_version_id == resource.program_version_id,
    )
    return _save(db, resource)


@router.delete("/device-configurations/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device_configuration(resource_id: str, db: Session = Depends(get_db)) -> Response:
    resource = _required(db, ProgramDeviceConfiguration, resource_id, "程序设备配置")
    check_delete_safe(db, ProductionDeviceExecution, ProductionDeviceExecution.device_configuration_id, resource_id, "程序设备配置")
    return _delete(db, resource, "程序设备配置")


@router.get("/trajectory-programs", response_model=list[TrajectoryProgramRead])
def list_trajectory_programs(
    program_version_id: str | None = None, db: Session = Depends(get_db)
) -> list[TrajectoryProgram]:
    query = select(TrajectoryProgram)
    if program_version_id:
        query = query.where(TrajectoryProgram.program_version_id == program_version_id)
    return list(db.scalars(query.order_by(TrajectoryProgram.created_at.desc())))


@router.post(
    "/trajectory-programs",
    response_model=TrajectoryProgramRead,
    status_code=status.HTTP_201_CREATED,
)
def create_trajectory_program(
    payload: TrajectoryProgramCreate, db: Session = Depends(get_db)
) -> TrajectoryProgram:
    check_fk(db, SprayProgramVersion, payload.program_version_id, "喷涂程序版本")
    _required(db, SprayProgramVersion, payload.program_version_id, "喷涂程序版本")
    if db.scalar(
        select(TrajectoryProgram).where(
            TrajectoryProgram.program_version_id == payload.program_version_id,
            TrajectoryProgram.trajectory_code == payload.trajectory_code,
            TrajectoryProgram.version == payload.version,
        )
    ):
        raise HTTPException(status_code=409, detail="轨迹程序代码与版本已存在")
    resource = TrajectoryProgram(**payload.model_dump())
    db.add(resource)
    db.flush()
    _activate_single_version(
        db,
        TrajectoryProgram,
        resource,
        resource.status,
        TrajectoryProgram.program_version_id == resource.program_version_id,
        TrajectoryProgram.trajectory_code == resource.trajectory_code,
    )
    db.commit()
    db.refresh(resource)
    return resource


@router.patch("/trajectory-programs/{resource_id}", response_model=TrajectoryProgramRead)
def update_trajectory_program(
    resource_id: str, payload: TrajectoryProgramUpdate, db: Session = Depends(get_db)
) -> TrajectoryProgram:
    resource = _required(db, TrajectoryProgram, resource_id, "轨迹程序")
    changes = payload.model_dump(exclude_unset=True)
    if changes.get("program_version_id"):
        _required(db, SprayProgramVersion, changes["program_version_id"], "喷涂程序版本")
    if db.scalar(
        select(TrajectoryProgram).where(
            TrajectoryProgram.program_version_id
            == changes.get("program_version_id", resource.program_version_id),
            TrajectoryProgram.trajectory_code
            == changes.get("trajectory_code", resource.trajectory_code),
            TrajectoryProgram.version == changes.get("version", resource.version),
            TrajectoryProgram.id != resource_id,
        )
    ):
        raise HTTPException(status_code=409, detail="轨迹程序代码与版本已存在")
    for field, value in changes.items():
        setattr(resource, field, value)
    _activate_single_version(
        db,
        TrajectoryProgram,
        resource,
        resource.status,
        TrajectoryProgram.program_version_id == resource.program_version_id,
        TrajectoryProgram.trajectory_code == resource.trajectory_code,
    )
    return _save(db, resource)


@router.delete("/trajectory-programs/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trajectory_program(resource_id: str, db: Session = Depends(get_db)) -> Response:
    resource = _required(db, TrajectoryProgram, resource_id, "轨迹程序")
    check_delete_safe(db, TrajectoryPathSegment, TrajectoryPathSegment.trajectory_program_id, resource_id, "轨迹程序")
    check_delete_safe(db, ProductionDeviceExecution, ProductionDeviceExecution.trajectory_program_id, resource_id, "轨迹程序")
    return _delete(db, resource, "轨迹程序")


@router.get(
    "/trajectory-programs/{trajectory_id}/segments",
    response_model=list[TrajectoryPathSegmentRead],
)
def list_path_segments(
    trajectory_id: str, db: Session = Depends(get_db)
) -> list[TrajectoryPathSegment]:
    _required(db, TrajectoryProgram, trajectory_id, "轨迹程序")
    return list(
        db.scalars(
            select(TrajectoryPathSegment)
            .where(TrajectoryPathSegment.trajectory_program_id == trajectory_id)
            .order_by(TrajectoryPathSegment.segment_no)
        )
    )


@router.get("/path-segments", response_model=list[TrajectoryPathSegmentRead])
def list_all_path_segments(
    trajectory_program_id: str | None = None, db: Session = Depends(get_db)
) -> list[TrajectoryPathSegment]:
    query = select(TrajectoryPathSegment)
    if trajectory_program_id:
        query = query.where(
            TrajectoryPathSegment.trajectory_program_id == trajectory_program_id
        )
    return list(
        db.scalars(
            query.order_by(
                TrajectoryPathSegment.trajectory_program_id,
                TrajectoryPathSegment.segment_no,
            )
        )
    )


@router.post(
    "/path-segments",
    response_model=TrajectoryPathSegmentRead,
    status_code=status.HTTP_201_CREATED,
)
def create_path_segment(
    payload: TrajectoryPathSegmentCreate, db: Session = Depends(get_db)
) -> TrajectoryPathSegment:
    check_fk(db, TrajectoryProgram, payload.trajectory_program_id, "轨迹程序")
    check_fk(db, Brush, payload.brush_id, "刷子")
    check_fk(db, Part, payload.part_id, "零件")
    trajectory = _required(db, TrajectoryProgram, payload.trajectory_program_id, "轨迹程序")
    if payload.brush_id:
        brush = _required(db, Brush, payload.brush_id, "刷子")
        if brush.program_version_id != trajectory.program_version_id:
            raise HTTPException(status_code=422, detail="路径段刷子不属于轨迹程序版本")
    if payload.part_id:
        _required(db, Part, payload.part_id, "零件")
    if db.scalar(
        select(TrajectoryPathSegment).where(
            TrajectoryPathSegment.trajectory_program_id == payload.trajectory_program_id,
            TrajectoryPathSegment.segment_no == payload.segment_no,
        )
    ):
        raise HTTPException(status_code=409, detail="轨迹程序下路径段序号已存在")
    return _save(db, TrajectoryPathSegment(**payload.model_dump()))


@router.patch("/path-segments/{resource_id}", response_model=TrajectoryPathSegmentRead)
def update_path_segment(
    resource_id: str, payload: TrajectoryPathSegmentUpdate, db: Session = Depends(get_db)
) -> TrajectoryPathSegment:
    resource = _required(db, TrajectoryPathSegment, resource_id, "路径段")
    changes = payload.model_dump(exclude_unset=True)
    trajectory_id = changes.get("trajectory_program_id", resource.trajectory_program_id)
    trajectory = _required(db, TrajectoryProgram, trajectory_id, "轨迹程序")
    brush_id = changes.get("brush_id", resource.brush_id)
    if brush_id:
        brush = _required(db, Brush, brush_id, "刷子")
        if brush.program_version_id != trajectory.program_version_id:
            raise HTTPException(status_code=422, detail="路径段刷子不属于轨迹程序版本")
    if changes.get("part_id"):
        _required(db, Part, changes["part_id"], "零件")
    if db.scalar(
        select(TrajectoryPathSegment).where(
            TrajectoryPathSegment.trajectory_program_id == trajectory_id,
            TrajectoryPathSegment.segment_no
            == changes.get("segment_no", resource.segment_no),
            TrajectoryPathSegment.id != resource_id,
        )
    ):
        raise HTTPException(status_code=409, detail="轨迹程序下路径段序号已存在")
    for field, value in changes.items():
        setattr(resource, field, value)
    return _save(db, resource)


@router.delete("/path-segments/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_path_segment(resource_id: str, db: Session = Depends(get_db)) -> Response:
    resource = _required(db, TrajectoryPathSegment, resource_id, "路径段")
    check_delete_safe(db, PointContributionEntry, PointContributionEntry.path_segment_id, resource_id, "路径段")
    check_delete_safe(db, PathSegmentExecution, PathSegmentExecution.path_segment_id, resource_id, "路径段")
    return _delete(db, resource, "路径段")


@router.get("/contribution-versions", response_model=list[PointContributionVersionRead])
def list_contribution_versions(
    program_version_id: str | None = None,
    target_family: str | None = None,
    db: Session = Depends(get_db),
) -> list[PointContributionVersion]:
    query = select(PointContributionVersion)
    if program_version_id:
        query = query.where(PointContributionVersion.program_version_id == program_version_id)
    if target_family:
        _validate_quality_type(target_family)
        query = query.where(PointContributionVersion.target_family == target_family)
    return list(db.scalars(query.order_by(PointContributionVersion.created_at.desc())))


@router.post(
    "/contribution-versions",
    response_model=PointContributionVersionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_contribution_version(
    payload: PointContributionVersionCreate, db: Session = Depends(get_db)
) -> PointContributionVersion:
    _validate_quality_type(payload.target_family)
    check_fk(db, SprayProgramVersion, payload.program_version_id, "喷涂程序版本")
    _required(db, SprayProgramVersion, payload.program_version_id, "喷涂程序版本")
    if db.scalar(
        select(PointContributionVersion).where(
            PointContributionVersion.program_version_id == payload.program_version_id,
            PointContributionVersion.target_family == payload.target_family,
            PointContributionVersion.version == payload.version,
        )
    ):
        raise HTTPException(status_code=409, detail="程序版本和目标族下贡献版本已存在")
    resource = PointContributionVersion(**payload.model_dump())
    db.add(resource)
    db.flush()
    _activate_single_version(
        db,
        PointContributionVersion,
        resource,
        resource.status,
        PointContributionVersion.program_version_id == resource.program_version_id,
        PointContributionVersion.target_family == resource.target_family,
    )
    db.commit()
    db.refresh(resource)
    return resource


@router.patch(
    "/contribution-versions/{resource_id}", response_model=PointContributionVersionRead
)
def update_contribution_version(
    resource_id: str,
    payload: PointContributionVersionUpdate,
    db: Session = Depends(get_db),
) -> PointContributionVersion:
    resource = _required(db, PointContributionVersion, resource_id, "点位贡献版本")
    changes = payload.model_dump(exclude_unset=True)
    _validate_quality_type(changes.get("target_family", resource.target_family))
    if changes.get("program_version_id"):
        _required(db, SprayProgramVersion, changes["program_version_id"], "喷涂程序版本")
    if db.scalar(
        select(PointContributionVersion).where(
            PointContributionVersion.program_version_id
            == changes.get("program_version_id", resource.program_version_id),
            PointContributionVersion.target_family
            == changes.get("target_family", resource.target_family),
            PointContributionVersion.version == changes.get("version", resource.version),
            PointContributionVersion.id != resource_id,
        )
    ):
        raise HTTPException(status_code=409, detail="程序版本和目标族下贡献版本已存在")
    for field, value in changes.items():
        setattr(resource, field, value)
    _activate_single_version(
        db,
        PointContributionVersion,
        resource,
        resource.status,
        PointContributionVersion.program_version_id == resource.program_version_id,
        PointContributionVersion.target_family == resource.target_family,
    )
    return _save(db, resource)


@router.delete("/contribution-versions/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contribution_version(resource_id: str, db: Session = Depends(get_db)) -> Response:
    resource = _required(db, PointContributionVersion, resource_id, "点位贡献版本")
    check_delete_safe(db, PointContributionEntry, PointContributionEntry.contribution_version_id, resource_id, "点位贡献版本")
    db.execute(
        delete(PointContributionEntry).where(
            PointContributionEntry.contribution_version_id == resource_id
        )
    )
    return _delete(db, resource, "点位贡献版本")


@router.get(
    "/contribution-versions/{version_id}/entries",
    response_model=list[PointContributionEntryRead],
)
def list_contribution_entries(
    version_id: str, db: Session = Depends(get_db)
) -> list[PointContributionEntry]:
    _required(db, PointContributionVersion, version_id, "点位贡献版本")
    return list(
        db.scalars(
            select(PointContributionEntry)
            .where(PointContributionEntry.contribution_version_id == version_id)
            .order_by(PointContributionEntry.measurement_point_id, PointContributionEntry.source_key)
        )
    )


@router.get("/contribution-entries", response_model=list[PointContributionEntryRead])
def list_all_contribution_entries(
    contribution_version_id: str | None = None, db: Session = Depends(get_db)
) -> list[PointContributionEntry]:
    query = select(PointContributionEntry)
    if contribution_version_id:
        query = query.where(
            PointContributionEntry.contribution_version_id == contribution_version_id
        )
    return list(
        db.scalars(
            query.order_by(
                PointContributionEntry.contribution_version_id,
                PointContributionEntry.measurement_point_id,
                PointContributionEntry.source_key,
            )
        )
    )


@router.post(
    "/contribution-entries",
    response_model=PointContributionEntryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_contribution_entry(
    payload: PointContributionEntryCreate, db: Session = Depends(get_db)
) -> PointContributionEntry:
    check_fk(db, PointContributionVersion, payload.contribution_version_id, "点位贡献版本")
    check_fk(db, MeasurementPoint, payload.measurement_point_id, "测量点")
    check_fk(db, Brush, payload.brush_id, "刷子")
    check_fk(db, TrajectoryPathSegment, payload.path_segment_id, "路径段")
    version = _required(
        db, PointContributionVersion, payload.contribution_version_id, "点位贡献版本"
    )
    _required(db, MeasurementPoint, payload.measurement_point_id, "测量点")
    source_key = _entry_source(db, version, payload.brush_id, payload.path_segment_id)
    if db.scalar(
        select(PointContributionEntry).where(
            PointContributionEntry.contribution_version_id == payload.contribution_version_id,
            PointContributionEntry.measurement_point_id == payload.measurement_point_id,
            PointContributionEntry.source_key == source_key,
        )
    ):
        raise HTTPException(status_code=409, detail="贡献版本下点位和来源组合已存在")
    return _save(
        db, PointContributionEntry(source_key=source_key, **payload.model_dump())
    )


@router.patch("/contribution-entries/{resource_id}", response_model=PointContributionEntryRead)
def update_contribution_entry(
    resource_id: str,
    payload: PointContributionEntryUpdate,
    db: Session = Depends(get_db),
) -> PointContributionEntry:
    resource = _required(db, PointContributionEntry, resource_id, "点位贡献条目")
    version = _required(
        db, PointContributionVersion, resource.contribution_version_id, "点位贡献版本"
    )
    changes = payload.model_dump(exclude_unset=True)
    point_id = changes.get("measurement_point_id", resource.measurement_point_id)
    _required(db, MeasurementPoint, point_id, "测量点")
    brush_id = changes.get("brush_id", resource.brush_id)
    path_segment_id = changes.get("path_segment_id", resource.path_segment_id)
    if "brush_id" in changes and changes["brush_id"]:
        path_segment_id = None
        changes["path_segment_id"] = None
    if "path_segment_id" in changes and changes["path_segment_id"]:
        brush_id = None
        changes["brush_id"] = None
    resource.source_key = _entry_source(db, version, brush_id, path_segment_id)
    if db.scalar(
        select(PointContributionEntry).where(
            PointContributionEntry.contribution_version_id
            == resource.contribution_version_id,
            PointContributionEntry.measurement_point_id == point_id,
            PointContributionEntry.source_key == resource.source_key,
            PointContributionEntry.id != resource_id,
        )
    ):
        raise HTTPException(status_code=409, detail="贡献版本下点位和来源组合已存在")
    for field, value in changes.items():
        setattr(resource, field, value)
    return _save(db, resource)


@router.delete("/contribution-entries/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contribution_entry(resource_id: str, db: Session = Depends(get_db)) -> Response:
    return _delete(
        db,
        _required(db, PointContributionEntry, resource_id, "点位贡献条目"),
        "点位贡献条目",
    )


def _validate_execution(db: Session, values: dict) -> tuple[TrajectoryProgram, str]:
    stage = _required(
        db, ProductionStageRun, values["production_stage_run_id"], "生产工序实绩"
    )
    configuration = _required(
        db, ProgramDeviceConfiguration, values["device_configuration_id"], "程序设备配置"
    )
    trajectory = _required(
        db, TrajectoryProgram, values["trajectory_program_id"], "轨迹程序"
    )
    if configuration.program_version_id != stage.program_version_id:
        raise HTTPException(status_code=422, detail="设备配置与生产工序程序版本不一致")
    if trajectory.program_version_id != stage.program_version_id:
        raise HTTPException(status_code=422, detail="轨迹程序与生产工序程序版本不一致")
    _validate_time_range(values.get("started_at"), values.get("completed_at"))
    execution_status = values.get("status", "COMPLETED")
    if values["executed_checksum"] != trajectory.checksum:
        execution_status = "CHECKSUM_MISMATCH"
    return trajectory, execution_status


@router.get("/device-executions", response_model=list[ProductionDeviceExecutionRead])
def list_device_executions(
    production_stage_run_id: str | None = None, db: Session = Depends(get_db)
) -> list[ProductionDeviceExecution]:
    query = select(ProductionDeviceExecution)
    if production_stage_run_id:
        query = query.where(
            ProductionDeviceExecution.production_stage_run_id == production_stage_run_id
        )
    return list(db.scalars(query.order_by(ProductionDeviceExecution.created_at.desc())))


@router.post(
    "/device-executions",
    response_model=ProductionDeviceExecutionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_device_execution(
    payload: ProductionDeviceExecutionCreate, db: Session = Depends(get_db)
) -> ProductionDeviceExecution:
    if db.scalar(
        select(ProductionDeviceExecution).where(
            ProductionDeviceExecution.production_stage_run_id
            == payload.production_stage_run_id
        )
    ):
        raise HTTPException(status_code=409, detail="生产工序已存在设备轨迹执行记录")
    values = payload.model_dump()
    _trajectory, values["status"] = _validate_execution(db, values)
    return _save(db, ProductionDeviceExecution(**values))


@router.patch("/device-executions/{resource_id}", response_model=ProductionDeviceExecutionRead)
def update_device_execution(
    resource_id: str,
    payload: ProductionDeviceExecutionUpdate,
    db: Session = Depends(get_db),
) -> ProductionDeviceExecution:
    resource = _required(db, ProductionDeviceExecution, resource_id, "设备轨迹执行")
    changes = payload.model_dump(exclude_unset=True)
    values = {
        "production_stage_run_id": resource.production_stage_run_id,
        "device_configuration_id": resource.device_configuration_id,
        "trajectory_program_id": resource.trajectory_program_id,
        "executed_checksum": resource.executed_checksum,
        "started_at": resource.started_at,
        "completed_at": resource.completed_at,
        "status": resource.status,
        **changes,
    }
    _trajectory, values["status"] = _validate_execution(db, values)
    changes["status"] = values["status"]
    for field, value in changes.items():
        setattr(resource, field, value)
    return _save(db, resource)


@router.delete("/device-executions/{resource_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_device_execution(resource_id: str, db: Session = Depends(get_db)) -> Response:
    resource = _required(db, ProductionDeviceExecution, resource_id, "设备轨迹执行")
    db.execute(
        delete(PathSegmentExecution).where(
            PathSegmentExecution.device_execution_id == resource_id
        )
    )
    return _delete(db, resource, "设备轨迹执行")


@router.get(
    "/device-executions/{execution_id}/segments",
    response_model=list[PathSegmentExecutionRead],
)
def list_path_segment_executions(
    execution_id: str, db: Session = Depends(get_db)
) -> list[PathSegmentExecution]:
    _required(db, ProductionDeviceExecution, execution_id, "设备轨迹执行")
    return list(
        db.scalars(
            select(PathSegmentExecution).where(
                PathSegmentExecution.device_execution_id == execution_id
            )
        )
    )


@router.post(
    "/device-executions/{execution_id}/segments",
    response_model=PathSegmentExecutionRead,
    status_code=status.HTTP_201_CREATED,
)
def create_path_segment_execution(
    execution_id: str,
    payload: PathSegmentExecutionCreate,
    db: Session = Depends(get_db),
) -> PathSegmentExecution:
    execution = _required(db, ProductionDeviceExecution, execution_id, "设备轨迹执行")
    segment = _required(db, TrajectoryPathSegment, payload.path_segment_id, "路径段")
    if segment.trajectory_program_id != execution.trajectory_program_id:
        raise HTTPException(status_code=422, detail="路径段不属于执行记录对应轨迹")
    if db.scalar(
        select(PathSegmentExecution).where(
            PathSegmentExecution.device_execution_id == execution_id,
            PathSegmentExecution.path_segment_id == payload.path_segment_id,
        )
    ):
        raise HTTPException(status_code=409, detail="路径段执行记录已存在")
    return _save(
        db, PathSegmentExecution(device_execution_id=execution_id, **payload.model_dump())
    )
