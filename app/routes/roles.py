from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.database.base import get_db
from app.services import role_service
from app.services.auth_service import get_current_user_from_token
from app.models.user import User, Role
from typing import List
from pydantic import BaseModel
import logging

# Configurar logger
logger = logging.getLogger(__name__)

# Modelos para solicitudes
class RoleCreate(BaseModel):
    name: str

class RoleUpdate(BaseModel):
    name: str

# Modelos para respuestas
class RoleSchema(BaseModel):
    id: int
    name: str
    
    class Config:
        orm_mode = True

class UserRoleSchema(BaseModel):
    user_id: int
    role_id: int

router = APIRouter(
    prefix="/roles",
    tags=["roles"],
    responses={404: {"description": "No encontrado"}},
)

# Verificar que el usuario sea administrador
def check_admin(current_user: User):
    if not role_service.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden gestionar roles"
        )
    return current_user

@router.get("/", response_model=List[RoleSchema])
async def read_roles(
    request: Request,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene la lista de roles"""
    # Verificar que el usuario sea administrador
    check_admin(current_user)
    
    roles = role_service.get_roles(db, skip=skip, limit=limit)
    return roles

@router.get("/{role_id}", response_model=RoleSchema)
async def read_role(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene un rol por su ID"""
    # Verificar que el usuario sea administrador
    check_admin(current_user)
    
    db_role = role_service.get_role(db, role_id=role_id)
    if db_role is None:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return db_role

@router.post("/", response_model=RoleSchema, status_code=status.HTTP_201_CREATED)
async def create_role(
    role: RoleCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Crea un nuevo rol"""
    # Verificar que el usuario sea administrador
    check_admin(current_user)
    
    return role_service.create_role(db=db, name=role.name)

@router.put("/{role_id}", response_model=RoleSchema)
async def update_role(
    role_id: int, 
    role: RoleUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Actualiza un rol existente"""
    # Verificar que el usuario sea administrador
    check_admin(current_user)
    
    db_role = role_service.update_role(db=db, role_id=role_id, name=role.name)
    if db_role is None:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return db_role

@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Elimina un rol"""
    # Verificar que el usuario sea administrador
    check_admin(current_user)
    
    success = role_service.delete_role(db=db, role_id=role_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rol no encontrado")
    return {"message": "Rol eliminado"}

@router.post("/assign", status_code=status.HTTP_200_OK)
async def assign_role(
    user_role: UserRoleSchema,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Asigna un rol a un usuario"""
    # Verificar que el usuario sea administrador
    check_admin(current_user)
    
    try:
        updated_user = role_service.assign_role_to_user(
            db=db, 
            user_id=user_role.user_id, 
            role_id=user_role.role_id
        )
        return {"message": "Rol asignado con éxito"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al asignar rol: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.post("/remove", status_code=status.HTTP_200_OK)
async def remove_role(
    user_role: UserRoleSchema,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Quita un rol a un usuario"""
    # Verificar que el usuario sea administrador
    check_admin(current_user)
    
    try:
        updated_user = role_service.remove_role_from_user(
            db=db, 
            user_id=user_role.user_id, 
            role_id=user_role.role_id
        )
        return {"message": "Rol eliminado con éxito"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al eliminar rol: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        ) 