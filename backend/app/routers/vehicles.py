from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app import models, schemas

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


@router.get("/lookup", response_model=schemas.VehicleOut)
def lookup_vehicle(reg: str = Query(...), db: Session = Depends(get_db)):
    vehicle = db.query(models.Vehicle).filter(models.Vehicle.reg_number == reg).first()
    if not vehicle:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


@router.post("/", response_model=schemas.VehicleOut, status_code=201)
def create_vehicle(v: schemas.VehicleCreate, db: Session = Depends(get_db)):
    vehicle = models.Vehicle(**v.dict())
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    return vehicle
