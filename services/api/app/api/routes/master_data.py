from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.domain import (
    BrushPointContribution,
    Color,
    Factory,
    FactoryVehicleModel,
    MeasurementGroup,
    MeasurementGroupPoint,
    MeasurementPoint,
    Part,
    VehicleModel,
    VehicleModelColor,
)
from app.schemas.master_data import (
    ColorCreate,
    ColorRead,
    ColorUpdate,
    FactoryVehicleModelCreate,
    FactoryVehicleModelRead,
    MasterDataSummary,
    MeasurementGroupCreate,
    MeasurementGroupPointCreate,
    MeasurementGroupPointBind,
    MeasurementGroupPointRead,
    MeasurementGroupRead,
    MeasurementGroupUpdate,
    MeasurementPointCreate,
    MeasurementPointRead,
    MeasurementPointUpdate,
    PartCreate,
    PartRead,
    PartUpdate,
    VehicleModelColorCreate,
    VehicleModelColorRead,
    VehicleModelCreate,
    VehicleModelRead,
    VehicleModelUpdate,
)

router = APIRouter(tags=["master-data"])


def _ensure_exists(db: Session, model: type, resource_id: str, label: str) -> None:
    if not db.get(model, resource_id):
        raise HTTPException(status_code=404, detail=f"{label}不存在")


def _create_unique(db: Session, model: type, payload: dict, filters: tuple, message: str):
    if db.scalar(select(model).where(*filters)):
        raise HTTPException(status_code=409, detail=message)
    resource = model(**payload)
    db.add(resource)
    db.commit()
    db.refresh(resource)
    return resource


def _get_resource(db: Session, model: type, resource_id: str, label: str):
    resource = db.get(model, resource_id)
    if not resource:
        raise HTTPException(status_code=404, detail=f"{label}不存在")
    return resource


def _update_resource(
    db: Session,
    model: type,
    resource_id: str,
    label: str,
    payload: dict,
    conflict_message: str,
):
    resource = _get_resource(db, model, resource_id, label)
    if "code" in payload:
        existing = db.scalar(
            select(model).where(model.code == payload["code"], model.id != resource_id)
        )
        if existing:
            raise HTTPException(status_code=409, detail=conflict_message)
    for field, value in payload.items():
        setattr(resource, field, value)
    db.commit()
    db.refresh(resource)
    return resource


def _delete_resource(db: Session, model: type, resource_id: str, label: str) -> Response:
    resource = _get_resource(db, model, resource_id, label)
    try:
        db.delete(resource)
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            status_code=409,
            detail=f"{label}已被业务数据引用，请先解除关联后再删除",
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/master-data/summary", response_model=MasterDataSummary)
def master_data_summary(db: Session = Depends(get_db)) -> dict:
    def count(model: type) -> int:
        return int(db.scalar(select(func.count()).select_from(model)) or 0)

    approved = int(
        db.scalar(
            select(func.count())
            .select_from(BrushPointContribution)
            .where(BrushPointContribution.is_approved.is_(True))
        )
        or 0
    )
    return {
        "factories": count(Factory),
        "vehicle_models": count(VehicleModel),
        "colors": count(Color),
        "parts": count(Part),
        "measurement_groups": count(MeasurementGroup),
        "measurement_points": count(MeasurementPoint),
        "approved_point_contributions": approved,
    }


@router.get("/vehicle-models", response_model=list[VehicleModelRead])
def list_vehicle_models(db: Session = Depends(get_db)) -> list[VehicleModel]:
    return list(db.scalars(select(VehicleModel).order_by(VehicleModel.code)))


@router.get("/vehicle-models/{vehicle_model_id}", response_model=VehicleModelRead)
def get_vehicle_model(vehicle_model_id: str, db: Session = Depends(get_db)) -> VehicleModel:
    return _get_resource(db, VehicleModel, vehicle_model_id, "车型")


@router.post("/vehicle-models", response_model=VehicleModelRead, status_code=status.HTTP_201_CREATED)
def create_vehicle_model(payload: VehicleModelCreate, db: Session = Depends(get_db)) -> VehicleModel:
    return _create_unique(
        db,
        VehicleModel,
        payload.model_dump(),
        (VehicleModel.code == payload.code,),
        "车型代码已存在",
    )


@router.patch("/vehicle-models/{vehicle_model_id}", response_model=VehicleModelRead)
def update_vehicle_model(
    vehicle_model_id: str, payload: VehicleModelUpdate, db: Session = Depends(get_db)
) -> VehicleModel:
    return _update_resource(
        db,
        VehicleModel,
        vehicle_model_id,
        "车型",
        payload.model_dump(exclude_unset=True),
        "车型代码已存在",
    )


@router.delete("/vehicle-models/{vehicle_model_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle_model(vehicle_model_id: str, db: Session = Depends(get_db)) -> Response:
    return _delete_resource(db, VehicleModel, vehicle_model_id, "车型")


@router.get("/colors", response_model=list[ColorRead])
def list_colors(db: Session = Depends(get_db)) -> list[Color]:
    return list(db.scalars(select(Color).order_by(Color.code)))


@router.get("/colors/{color_id}", response_model=ColorRead)
def get_color(color_id: str, db: Session = Depends(get_db)) -> Color:
    return _get_resource(db, Color, color_id, "颜色")


@router.post("/colors", response_model=ColorRead, status_code=status.HTTP_201_CREATED)
def create_color(payload: ColorCreate, db: Session = Depends(get_db)) -> Color:
    return _create_unique(db, Color, payload.model_dump(), (Color.code == payload.code,), "颜色代码已存在")


@router.patch("/colors/{color_id}", response_model=ColorRead)
def update_color(color_id: str, payload: ColorUpdate, db: Session = Depends(get_db)) -> Color:
    return _update_resource(
        db,
        Color,
        color_id,
        "颜色",
        payload.model_dump(exclude_unset=True),
        "颜色代码已存在",
    )


@router.delete("/colors/{color_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_color(color_id: str, db: Session = Depends(get_db)) -> Response:
    return _delete_resource(db, Color, color_id, "颜色")


@router.get("/parts", response_model=list[PartRead])
def list_parts(db: Session = Depends(get_db)) -> list[Part]:
    return list(db.scalars(select(Part).order_by(Part.code)))


@router.get("/parts/{part_id}", response_model=PartRead)
def get_part(part_id: str, db: Session = Depends(get_db)) -> Part:
    return _get_resource(db, Part, part_id, "零件")


@router.post("/parts", response_model=PartRead, status_code=status.HTTP_201_CREATED)
def create_part(payload: PartCreate, db: Session = Depends(get_db)) -> Part:
    return _create_unique(db, Part, payload.model_dump(), (Part.code == payload.code,), "零件代码已存在")


@router.patch("/parts/{part_id}", response_model=PartRead)
def update_part(part_id: str, payload: PartUpdate, db: Session = Depends(get_db)) -> Part:
    return _update_resource(
        db,
        Part,
        part_id,
        "零件",
        payload.model_dump(exclude_unset=True),
        "零件代码已存在",
    )


@router.delete("/parts/{part_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_part(part_id: str, db: Session = Depends(get_db)) -> Response:
    return _delete_resource(db, Part, part_id, "零件")


@router.post(
    "/factory-vehicle-models",
    response_model=FactoryVehicleModelRead,
    status_code=status.HTTP_201_CREATED,
)
def bind_factory_vehicle_model(
    payload: FactoryVehicleModelCreate, db: Session = Depends(get_db)
) -> FactoryVehicleModel:
    _ensure_exists(db, Factory, payload.factory_id, "工厂")
    _ensure_exists(db, VehicleModel, payload.vehicle_model_id, "车型")
    return _create_unique(
        db,
        FactoryVehicleModel,
        payload.model_dump(),
        (
            FactoryVehicleModel.factory_id == payload.factory_id,
            FactoryVehicleModel.vehicle_model_id == payload.vehicle_model_id,
        ),
        "工厂与车型关系已存在",
    )


@router.get("/factory-vehicle-models", response_model=list[FactoryVehicleModelRead])
def list_factory_vehicle_models(db: Session = Depends(get_db)) -> list[FactoryVehicleModel]:
    return list(
        db.scalars(
            select(FactoryVehicleModel).order_by(
                FactoryVehicleModel.factory_id,
                FactoryVehicleModel.vehicle_model_id,
            )
        )
    )


@router.delete("/factory-vehicle-models/{relation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_factory_vehicle_model(relation_id: str, db: Session = Depends(get_db)) -> Response:
    return _delete_resource(db, FactoryVehicleModel, relation_id, "工厂车型关系")


@router.post(
    "/vehicle-model-colors",
    response_model=VehicleModelColorRead,
    status_code=status.HTTP_201_CREATED,
)
def bind_vehicle_model_color(
    payload: VehicleModelColorCreate, db: Session = Depends(get_db)
) -> VehicleModelColor:
    _ensure_exists(db, VehicleModel, payload.vehicle_model_id, "车型")
    _ensure_exists(db, Color, payload.color_id, "颜色")
    return _create_unique(
        db,
        VehicleModelColor,
        payload.model_dump(),
        (
            VehicleModelColor.vehicle_model_id == payload.vehicle_model_id,
            VehicleModelColor.color_id == payload.color_id,
        ),
        "车型与颜色关系已存在",
    )


@router.get("/vehicle-model-colors", response_model=list[VehicleModelColorRead])
def list_vehicle_model_colors(db: Session = Depends(get_db)) -> list[VehicleModelColor]:
    return list(
        db.scalars(
            select(VehicleModelColor).order_by(
                VehicleModelColor.vehicle_model_id,
                VehicleModelColor.color_id,
            )
        )
    )


@router.delete("/vehicle-model-colors/{relation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle_model_color(relation_id: str, db: Session = Depends(get_db)) -> Response:
    return _delete_resource(db, VehicleModelColor, relation_id, "车型颜色关系")


@router.get("/measurement-groups", response_model=list[MeasurementGroupRead])
def list_measurement_groups(db: Session = Depends(get_db)) -> list[MeasurementGroup]:
    return list(db.scalars(select(MeasurementGroup).order_by(MeasurementGroup.code)))


@router.get("/measurement-groups/{measurement_group_id}", response_model=MeasurementGroupRead)
def get_measurement_group(
    measurement_group_id: str, db: Session = Depends(get_db)
) -> MeasurementGroup:
    return _get_resource(db, MeasurementGroup, measurement_group_id, "测量编组")


@router.post(
    "/measurement-groups",
    response_model=MeasurementGroupRead,
    status_code=status.HTTP_201_CREATED,
)
def create_measurement_group(
    payload: MeasurementGroupCreate, db: Session = Depends(get_db)
) -> MeasurementGroup:
    _ensure_exists(db, VehicleModel, payload.vehicle_model_id, "车型")
    return _create_unique(
        db,
        MeasurementGroup,
        payload.model_dump(),
        (
            MeasurementGroup.vehicle_model_id == payload.vehicle_model_id,
            MeasurementGroup.code == payload.code,
        ),
        "车型下测量编组代码已存在",
    )


@router.patch("/measurement-groups/{measurement_group_id}", response_model=MeasurementGroupRead)
def update_measurement_group(
    measurement_group_id: str,
    payload: MeasurementGroupUpdate,
    db: Session = Depends(get_db),
) -> MeasurementGroup:
    group = _get_resource(db, MeasurementGroup, measurement_group_id, "测量编组")
    changes = payload.model_dump(exclude_unset=True)
    vehicle_model_id = changes.get("vehicle_model_id", group.vehicle_model_id)
    code = changes.get("code", group.code)
    _ensure_exists(db, VehicleModel, vehicle_model_id, "车型")
    duplicate = db.scalar(
        select(MeasurementGroup).where(
            MeasurementGroup.vehicle_model_id == vehicle_model_id,
            MeasurementGroup.code == code,
            MeasurementGroup.id != measurement_group_id,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="车型下测量编组代码已存在")
    for field, value in changes.items():
        setattr(group, field, value)
    db.commit()
    db.refresh(group)
    return group


@router.delete(
    "/measurement-groups/{measurement_group_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_measurement_group(
    measurement_group_id: str, db: Session = Depends(get_db)
) -> Response:
    return _delete_resource(db, MeasurementGroup, measurement_group_id, "测量编组")


@router.get("/measurement-points", response_model=list[MeasurementPointRead])
def list_measurement_points(db: Session = Depends(get_db)) -> list[MeasurementPoint]:
    return list(db.scalars(select(MeasurementPoint).order_by(MeasurementPoint.code)))


@router.get("/measurement-points/{measurement_point_id}", response_model=MeasurementPointRead)
def get_measurement_point(
    measurement_point_id: str, db: Session = Depends(get_db)
) -> MeasurementPoint:
    return _get_resource(db, MeasurementPoint, measurement_point_id, "测量点")


@router.post(
    "/measurement-points",
    response_model=MeasurementPointRead,
    status_code=status.HTTP_201_CREATED,
)
def create_measurement_point(
    payload: MeasurementPointCreate, db: Session = Depends(get_db)
) -> MeasurementPoint:
    _ensure_exists(db, VehicleModel, payload.vehicle_model_id, "车型")
    _ensure_exists(db, Part, payload.part_id, "零件")
    return _create_unique(
        db,
        MeasurementPoint,
        payload.model_dump(),
        (
            MeasurementPoint.vehicle_model_id == payload.vehicle_model_id,
            MeasurementPoint.code == payload.code,
        ),
        "车型下测量点代码已存在",
    )


@router.patch("/measurement-points/{measurement_point_id}", response_model=MeasurementPointRead)
def update_measurement_point(
    measurement_point_id: str,
    payload: MeasurementPointUpdate,
    db: Session = Depends(get_db),
) -> MeasurementPoint:
    point = _get_resource(db, MeasurementPoint, measurement_point_id, "测量点")
    changes = payload.model_dump(exclude_unset=True)
    vehicle_model_id = changes.get("vehicle_model_id", point.vehicle_model_id)
    part_id = changes.get("part_id", point.part_id)
    code = changes.get("code", point.code)
    _ensure_exists(db, VehicleModel, vehicle_model_id, "车型")
    _ensure_exists(db, Part, part_id, "零件")
    duplicate = db.scalar(
        select(MeasurementPoint).where(
            MeasurementPoint.vehicle_model_id == vehicle_model_id,
            MeasurementPoint.code == code,
            MeasurementPoint.id != measurement_point_id,
        )
    )
    if duplicate:
        raise HTTPException(status_code=409, detail="车型下测量点代码已存在")
    for field, value in changes.items():
        setattr(point, field, value)
    db.commit()
    db.refresh(point)
    return point


@router.delete(
    "/measurement-points/{measurement_point_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_measurement_point(
    measurement_point_id: str, db: Session = Depends(get_db)
) -> Response:
    return _delete_resource(db, MeasurementPoint, measurement_point_id, "测量点")


@router.post(
    "/measurement-groups/{group_id}/points",
    response_model=MeasurementGroupPointRead,
    status_code=status.HTTP_201_CREATED,
)
def add_measurement_group_point(
    group_id: str, payload: MeasurementGroupPointCreate, db: Session = Depends(get_db)
) -> MeasurementGroupPoint:
    _ensure_exists(db, MeasurementGroup, group_id, "测量编组")
    _ensure_exists(db, MeasurementPoint, payload.measurement_point_id, "测量点")
    return _create_unique(
        db,
        MeasurementGroupPoint,
        {"measurement_group_id": group_id, **payload.model_dump()},
        (
            MeasurementGroupPoint.measurement_group_id == group_id,
            MeasurementGroupPoint.measurement_point_id == payload.measurement_point_id,
        ),
        "测量点已加入该编组",
    )


@router.get("/measurement-group-points", response_model=list[MeasurementGroupPointRead])
def list_measurement_group_points(db: Session = Depends(get_db)) -> list[MeasurementGroupPoint]:
    return list(
        db.scalars(
            select(MeasurementGroupPoint).order_by(
                MeasurementGroupPoint.measurement_group_id,
                MeasurementGroupPoint.sequence_no,
            )
        )
    )


@router.post(
    "/measurement-group-points",
    response_model=MeasurementGroupPointRead,
    status_code=status.HTTP_201_CREATED,
)
def bind_measurement_group_point(
    payload: MeasurementGroupPointBind, db: Session = Depends(get_db)
) -> MeasurementGroupPoint:
    return add_measurement_group_point(
        payload.measurement_group_id,
        MeasurementGroupPointCreate(
            measurement_point_id=payload.measurement_point_id,
            sequence_no=payload.sequence_no,
        ),
        db,
    )


@router.delete("/measurement-group-points/{relation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_measurement_group_point(relation_id: str, db: Session = Depends(get_db)) -> Response:
    return _delete_resource(db, MeasurementGroupPoint, relation_id, "编组点位关系")
