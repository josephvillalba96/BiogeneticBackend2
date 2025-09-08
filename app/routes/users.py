from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session
from app.database.base import get_db
from app.services import user_service, role_service
from app.services.auth_service import get_current_user_from_token, get_current_active_user, get_current_admin_user
from app.schemas.user_schema import (
    UserSchema, UserCreate, UserUpdate, RoleSchema, RoleCreate, UserCreateByAdmin
)
from app.models.user import User
from typing import List, Dict, Any, Optional

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "No encontrado"}},
)

# Verificar que el usuario sea administrador
def check_admin(current_user: User):
    if not role_service.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores pueden realizar esta acción"
        )
    return current_user

@router.get("/", response_model=List[UserSchema])
async def read_users(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene la lista de usuarios"""
    users = user_service.get_users(db, skip=skip, limit=limit)
    return users

@router.get("/filter", response_model=List[Dict[str, Any]])
async def filter_users(
    email: Optional[str] = None,
    full_name: Optional[str] = None,
    number_document: Optional[str] = None,
    role_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Filtra usuarios por email, nombre, número de documento y/o rol.
    
    Parámetros:
    - email: Filtrar por coincidencia parcial en email
    - full_name: Filtrar por coincidencia parcial en nombre completo
    - number_document: Filtrar por coincidencia parcial en número de documento
    - role_id: Filtrar por ID de rol exacto
    """
    users = user_service.filter_users(
        db=db, 
        email=email, 
        full_name=full_name, 
        number_document=number_document,
        role_id=role_id,
        skip=skip, 
        limit=limit
    )
    return users

@router.get("/search", response_model=List[Dict[str, Any]])
async def search_users(
    q: Optional[str] = None,
    role_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Busca usuarios por coincidencia en email, nombre o número de documento con un solo parámetro.
    Opcionalmente filtra por rol.
    
    Parámetros:
    - q: Texto a buscar en email, nombre o número de documento
    - role_id: Filtrar por ID de rol exacto
    """
    users = user_service.search_users(
        db=db, 
        search_query=q,
        role_id=role_id,
        skip=skip, 
        limit=limit
    )
    return users

@router.get("/{user_id}", response_model=UserSchema)
async def read_user(
    user_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene un usuario por su ID"""
    db_user = user_service.get_user(db, user_id=user_id)
    if db_user is None:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return db_user

@router.post("/", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user(
    user: UserCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Crea un nuevo usuario con rol Client por defecto"""
    return user_service.create_user(db=db, user=user)

@router.post("/admin/create", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def create_user_with_roles(
    user: UserCreateByAdmin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Crea un nuevo usuario con roles específicos.
    Solo los administradores pueden usar esta función.
    """
    # Verificar que el usuario sea administrador
    check_admin(current_user)
    
    # Llamar al servicio para crear usuario con roles específicos
    return user_service.create_user_by_admin(db=db, user_data=user, role_ids=user.roles)

@router.put("/{user_id}", response_model=UserSchema)
def update_user_route(
    user_id: int,
    user: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    # Solo admin puede actualizar a otros usuarios
    if not (current_user.id == user_id or current_user.is_admin):
        raise HTTPException(status_code=403, detail="No tienes permisos para actualizar este usuario")
    db_user = user_service.update_user(db, user_id, user)
    if db_user is None:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.post("/profile-picture", response_model=dict)
def upload_profile_picture(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
):
    url = user_service.upload_profile_picture(file=file, user_id=current_user.id)
    return {"url": url}

@router.delete("/{user_id}", response_model=UserSchema, dependencies=[Depends(get_current_admin_user)])
def delete_user_route(user_id: int, db: Session = Depends(get_db)):
    db_user = user_service.delete_user(db, user_id)
    if not db_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return {"message": "Usuario eliminado"}

# Rutas para roles
@router.get("/roles/", response_model=List[RoleSchema])
async def read_roles(
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene la lista de roles"""
    roles = role_service.get_roles(db, skip=skip, limit=limit)
    return roles

@router.post("/roles/", response_model=RoleSchema, status_code=status.HTTP_201_CREATED)
async def create_role(
    role: RoleCreate, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Crea un nuevo rol"""
    # Verificar que el usuario sea administrador
    check_admin(current_user)
    return role_service.create_role(db=db, name=role.name)

@router.put("/{user_id}/roles/{role_id}")
async def assign_role(
    user_id: int, 
    role_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Asigna un rol a un usuario"""
    # Verificar que el usuario sea administrador
    check_admin(current_user)
    success = role_service.assign_role_to_user(db=db, user_id=user_id, role_id=role_id)
    if not success:
        raise HTTPException(status_code=404, detail="Usuario o rol no encontrado")
    return {"message": "Rol asignado al usuario"}

@router.delete("/{user_id}/roles/{role_id}")
async def remove_role(
    user_id: int, 
    role_id: int, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Elimina un rol de un usuario"""
    # Verificar que el usuario sea administrador
    check_admin(current_user)
    success = role_service.remove_role_from_user(db=db, user_id=user_id, role_id=role_id)
    if not success:
        raise HTTPException(status_code=404, detail="Usuario o rol no encontrado o el usuario no tiene ese rol")
    return {"message": "Rol eliminado del usuario"} 