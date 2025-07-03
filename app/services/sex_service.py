from sqlalchemy.orm import Session
from app.models.bull import Sex
from app.schemas.bull_schema import SexCreate
from typing import List, Optional

def get_sex(db: Session, sex_id: int) -> Optional[Sex]:
    """Obtiene un sexo por su ID"""
    return db.query(Sex).filter(Sex.id == sex_id).first()

def get_sex_by_code(db: Session, code: int) -> Optional[Sex]:
    """Obtiene un sexo por su código"""
    return db.query(Sex).filter(Sex.code == code).first()

def get_sexes(db: Session, skip: int = 0, limit: int = 100) -> List[Sex]:
    """Obtiene una lista de sexos"""
    return db.query(Sex).offset(skip).limit(limit).all()

def create_sex(db: Session, sex: SexCreate) -> Sex:
    """Crea un nuevo sexo"""
    # Verificar si el código ya existe
    existing_sex = get_sex_by_code(db, sex.code)
    if existing_sex:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El código de sexo ya existe"
        )
    
    # Crear el nuevo sexo
    db_sex = Sex(
        name=sex.name,
        code=sex.code
    )
    
    # Guardar en la base de datos
    db.add(db_sex)
    db.commit()
    db.refresh(db_sex)
    return db_sex

def update_sex(db: Session, sex_id: int, sex_data: dict) -> Optional[Sex]:
    """Actualiza un sexo existente"""
    # Obtener el sexo
    db_sex = get_sex(db, sex_id)
    if not db_sex:
        return None
    
    # Actualizar los campos
    for key, value in sex_data.items():
        setattr(db_sex, key, value)
    
    # Guardar los cambios
    db.commit()
    db.refresh(db_sex)
    return db_sex

def delete_sex(db: Session, sex_id: int) -> bool:
    """Elimina un sexo"""
    db_sex = get_sex(db, sex_id)
    if not db_sex:
        return False
    
    # Verificar si hay toros asociados a este sexo
    from app.models.bull import Bull
    has_bulls = db.query(Bull).filter(Bull.sex_id == sex_id).first() is not None
    if has_bulls:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede eliminar el sexo porque hay toros asociados a él"
        )
    
    db.delete(db_sex)
    db.commit()
    return True 