from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.delete_policy import reject_physical_delete
from app.db.session import get_db
from app.models.domain import Factory, FactoryVehicleModel, SprayProgram
from app.schemas.common import FactoryCreate, FactoryRead, FactoryUpdate

router = APIRouter(prefix="/factories", tags=["master-data"])


@router.get("", response_model=list[FactoryRead])
def list_factories(db: Session = Depends(get_db)) -> list[Factory]:
    return list(db.scalars(select(Factory).order_by(Factory.code)))


@router.get("/{factory_id}", response_model=FactoryRead)
def get_factory(factory_id: str, db: Session = Depends(get_db)) -> Factory:
    factory = db.get(Factory, factory_id)
    if not factory:
        raise HTTPException(status_code=404, detail="工厂不存在")
    return factory


@router.post("", response_model=FactoryRead, status_code=status.HTTP_201_CREATED)
def create_factory(payload: FactoryCreate, db: Session = Depends(get_db)) -> Factory:
    existing = db.scalar(select(Factory).where(Factory.code == payload.code))
    if existing:
        raise HTTPException(status_code=409, detail="工厂代码已存在")
    factory = Factory(**payload.model_dump())
    db.add(factory)
    db.commit()
    db.refresh(factory)
    return factory


@router.patch("/{factory_id}", response_model=FactoryRead)
def update_factory(
    factory_id: str, payload: FactoryUpdate, db: Session = Depends(get_db)
) -> Factory:
    factory = get_factory(factory_id, db)
    changes = payload.model_dump(exclude_unset=True)
    if "code" in changes:
        existing = db.scalar(
            select(Factory).where(Factory.code == changes["code"], Factory.id != factory_id)
        )
        if existing:
            raise HTTPException(status_code=409, detail="工厂代码已存在")
    for field, value in changes.items():
        setattr(factory, field, value)
    db.commit()
    db.refresh(factory)
    return factory


@router.delete("/{factory_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_factory(factory_id: str, db: Session = Depends(get_db)) -> Response:
    get_factory(factory_id, db)
    reject_physical_delete("工厂")
