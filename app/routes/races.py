from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.base import get_db
from app.services import race_service
from app.services.auth_service import get_current_user_from_token
from app.schemas.bull_schema import RaceSchema, RaceCreate
from app.models.user import User
from typing import List, Dict, Any

router = APIRouter(
    prefix="/races",
    tags=["races"],
    responses={404: {"description": "No encontrado"}},
)

@router.get("/", response_model=List[RaceSchema])
async def read_races(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene la lista de razas"""
    races = race_service.get_races(db, skip=skip, limit=limit)
    return races

@router.get("/{race_id}", response_model=RaceSchema)
async def read_race(
    race_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene una raza por su ID"""
    db_race = race_service.get_race(db, race_id=race_id)
    if db_race is None:
        raise HTTPException(status_code=404, detail="Raza no encontrada")
    return db_race

@router.post("/", response_model=RaceSchema, status_code=status.HTTP_201_CREATED)
async def create_race(
    race: RaceCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Crea una nueva raza"""
    return race_service.create_race(db=db, race=race)

@router.put("/{race_id}", response_model=RaceSchema)
async def update_race(
    race_id: int, 
    race_data: Dict[str, Any], 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Actualiza una raza existente"""
    db_race = race_service.update_race(db=db, race_id=race_id, race_data=race_data)
    if db_race is None:
        raise HTTPException(status_code=404, detail="Raza no encontrada")
    return db_race

@router.delete("/{race_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_race(
    race_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Elimina una raza"""
    try:
        success = race_service.delete_race(db=db, race_id=race_id)
        if not success:
            raise HTTPException(status_code=404, detail="Raza no encontrada")
        return {"message": "Raza eliminada"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 