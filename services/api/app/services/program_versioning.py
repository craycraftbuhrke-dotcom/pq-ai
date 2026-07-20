from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.domain import (
    Brush,
    BrushParameter,
    BrushPointContribution,
    ProgramColor,
    ProgramVehicleModel,
    SprayProgramVersion,
)


def derive_complete_program_version(
    db: Session,
    base_version_id: str,
    new_version: str,
    edits: list,
) -> dict:
    base = db.get(SprayProgramVersion, base_version_id)
    if not base:
        raise HTTPException(status_code=404, detail="原喷涂程序版本不存在")
    if db.scalar(
        select(SprayProgramVersion).where(
            SprayProgramVersion.spray_program_id == base.spray_program_id,
            SprayProgramVersion.version == new_version,
        )
    ):
        raise HTTPException(status_code=409, detail="新版本号已经存在")

    edit_map: dict[tuple[str, str], float] = {}
    for edit in edits:
        key = (edit.brush_no, edit.parameter_code)
        if key in edit_map:
            raise HTTPException(
                status_code=422,
                detail=f"刷子 {edit.brush_no} 的参数 {edit.parameter_code} 重复填写",
            )
        edit_map[key] = edit.new_value

    base_brushes = list(
        db.scalars(
            select(Brush)
            .where(Brush.program_version_id == base.id)
            .order_by(Brush.brush_no)
        )
    )
    if not base_brushes:
        raise HTTPException(status_code=422, detail="原版本没有刷子表数据，不能派生新版本")
    available_keys: set[tuple[str, str]] = set()
    parameter_rows: dict[str, list[BrushParameter]] = {}
    for brush in base_brushes:
        parameters = list(
            db.scalars(
                select(BrushParameter)
                .where(BrushParameter.brush_id == brush.id)
                .order_by(BrushParameter.parameter_code)
            )
        )
        parameter_rows[brush.id] = parameters
        available_keys.update((brush.brush_no, item.parameter_code) for item in parameters)
    unknown = sorted(set(edit_map) - available_keys)
    if unknown:
        brush_no, parameter_code = unknown[0]
        raise HTTPException(
            status_code=422,
            detail=f"原版本中找不到刷子 {brush_no} 的参数 {parameter_code}",
        )

    derived = SprayProgramVersion(
        spray_program_id=base.spray_program_id,
        version=new_version,
        status="DRAFT",
        source_type="CONTROLLED_REMOTE_EDIT",
        is_master_sample=False,
    )
    db.add(derived)
    db.flush()
    for model_id in db.scalars(
        select(ProgramVehicleModel.vehicle_model_id).where(
            ProgramVehicleModel.program_version_id == base.id
        )
    ):
        db.add(ProgramVehicleModel(program_version_id=derived.id, vehicle_model_id=model_id))
    for color_id in db.scalars(
        select(ProgramColor.color_id).where(ProgramColor.program_version_id == base.id)
    ):
        db.add(ProgramColor(program_version_id=derived.id, color_id=color_id))

    parameter_count = 0
    contribution_count = 0
    for base_brush in base_brushes:
        new_brush = Brush(
            program_version_id=derived.id,
            brush_no=base_brush.brush_no,
            brush_table_no=base_brush.brush_table_no,
            spray_position=base_brush.spray_position,
            part_id=base_brush.part_id,
            remark=base_brush.remark,
        )
        db.add(new_brush)
        db.flush()
        for source in parameter_rows[base_brush.id]:
            value = edit_map.get(
                (base_brush.brush_no, source.parameter_code), source.configured_value
            )
            if source.hard_min is not None and value < source.hard_min:
                raise HTTPException(
                    status_code=422,
                    detail=f"刷子 {base_brush.brush_no} 的 {source.parameter_name} 低于硬下限",
                )
            if source.hard_max is not None and value > source.hard_max:
                raise HTTPException(
                    status_code=422,
                    detail=f"刷子 {base_brush.brush_no} 的 {source.parameter_name} 高于硬上限",
                )
            db.add(
                BrushParameter(
                    brush_id=new_brush.id,
                    parameter_definition_id=source.parameter_definition_id,
                    parameter_code=source.parameter_code,
                    parameter_name=source.parameter_name,
                    configured_value=value,
                    unit=source.unit,
                    soft_min=source.soft_min,
                    soft_max=source.soft_max,
                    hard_min=source.hard_min,
                    hard_max=source.hard_max,
                    is_recommendable=source.is_recommendable,
                )
            )
            parameter_count += 1
        contributions = list(
            db.scalars(
                select(BrushPointContribution).where(
                    BrushPointContribution.brush_id == base_brush.id
                )
            )
        )
        for source in contributions:
            db.add(
                BrushPointContribution(
                    brush_id=new_brush.id,
                    measurement_point_id=source.measurement_point_id,
                    overlap_ratio=source.overlap_ratio,
                    contribution_weight=source.contribution_weight,
                    source=source.source,
                    version=source.version,
                    is_approved=source.is_approved,
                )
            )
            contribution_count += 1
    db.commit()
    return {
        "program_version_id": derived.id,
        "version": derived.version,
        "status": derived.status,
        "brush_count": len(base_brushes),
        "parameter_count": parameter_count,
        "contribution_count": contribution_count,
        "changed_parameter_count": len(edit_map),
    }
