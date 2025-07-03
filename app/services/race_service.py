from sqlalchemy.orm import Session
from app.models.bull import Race
from app.schemas.bull_schema import RaceCreate
from typing import List, Optional

def get_race(db: Session, race_id: int) -> Optional[Race]:
    """Obtiene una raza por su ID"""
    return db.query(Race).filter(Race.id == race_id).first()

def get_race_by_code(db: Session, code: str) -> Optional[Race]:
    """Obtiene una raza por su código"""
    return db.query(Race).filter(Race.code == code).first()

def get_races(db: Session, skip: int = 0, limit: int = 100) -> List[Race]:
    """Obtiene una lista de razas"""
    return db.query(Race).offset(skip).limit(limit).all()

def create_race(db: Session, race: RaceCreate) -> Race:
    """Crea una nueva raza"""
    # Verificar si el código ya existe
    existing_race = get_race_by_code(db, race.code)
    if existing_race:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código de raza ya existe"
        )
    
    # Crear la nueva raza
    db_race = Race(
        name=race.name,
        description=race.description,
        code=race.code
    )
    
    # Guardar en la base de datos
    db.add(db_race)
    db.commit()
    db.refresh(db_race)
    return db_race

def update_race(db: Session, race_id: int, race_data: dict) -> Optional[Race]:
    """Actualiza una raza existente"""
    # Obtener la raza
    db_race = get_race(db, race_id)
    if not db_race:
        return None
    
    # Actualizar los campos
    for key, value in race_data.items():
        setattr(db_race, key, value)
    
    # Guardar los cambios
    db.commit()
    db.refresh(db_race)
    return db_race

def delete_race(db: Session, race_id: int) -> bool:
    """Elimina una raza"""
    db_race = get_race(db, race_id)
    if not db_race:
        return False
    
    # Verificar si hay toros asociados a esta raza
    from app.models.bull import Bull
    has_bulls = db.query(Bull).filter(Bull.race_id == race_id).first() is not None
    if has_bulls:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar la raza porque hay toros asociados a ella"
        )
    
    db.delete(db_race)
    db.commit()
    return True 