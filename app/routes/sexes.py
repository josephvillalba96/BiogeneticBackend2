from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database.base import get_db
from app.services import sex_service
from app.services.auth_service import get_current_user_from_token
from app.schemas.bull_schema import SexSchema, SexCreate
from app.models.user import User
from typing import List, Dict, Any

router = APIRouter(
    prefix="/sexes",
    tags=["sexes"],
    responses={404: {"description": "No encontrado"}},
)

@router.get("/", response_model=List[SexSchema])
async def read_sexes(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene la lista de sexos"""
    sexes = sex_service.get_sexes(db, skip=skip, limit=limit)
    return sexes

@router.get("/{sex_id}", response_model=SexSchema)
async def read_sex(
    sex_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene un sexo por su ID"""
    db_sex = sex_service.get_sex(db, sex_id=sex_id)
    if db_sex is None:
        raise HTTPException(status_code=404, detail="Sexo no encontrado")
    return db_sex

@router.post("/", response_model=SexSchema, status_code=status.HTTP_201_CREATED)
async def create_sex(
    sex: SexCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Crea un nuevo sexo"""
    return sex_service.create_sex(db=db, sex=sex)

@router.put("/{sex_id}", response_model=SexSchema)
async def update_sex(
    sex_id: int, 
    sex_data: Dict[str, Any], 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Actualiza un sexo existente"""
    db_sex = sex_service.update_sex(db=db, sex_id=sex_id, sex_data=sex_data)
    if db_sex is None:
        raise HTTPException(status_code=404, detail="Sexo no encontrado")
    return db_sex

@router.delete("/{sex_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sex(
    sex_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Elimina un sexo"""
    try:
        success = sex_service.delete_sex(db=db, sex_id=sex_id)
        if not success:
            raise HTTPException(status_code=404, detail="Sexo no encontrado")
        return {"message": "Sexo eliminado"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 