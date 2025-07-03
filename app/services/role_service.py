from sqlalchemy.orm import Session
from app.models.user import Role, User
from fastapi import HTTPException, status
from typing import List, Optional

def get_role(db: Session, role_id: int) -> Optional[Role]:
    """Obtiene un rol por su ID"""
    return db.query(Role).filter(Role.id == role_id).first()

def get_role_by_name(db: Session, name: str) -> Optional[Role]:
    """Obtiene un rol por su nombre"""
    return db.query(Role).filter(Role.name == name).first()

def get_roles(db: Session, skip: int = 0, limit: int = 100) -> List[Role]:
    """Obtiene una lista de roles"""
    return db.query(Role).offset(skip).limit(limit).all()

def create_role(db: Session, name: str) -> Role:
    """Crea un nuevo rol"""
    # Verificar si ya existe
    existing_role = get_role_by_name(db, name)
    if existing_role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El rol '{name}' ya existe"
        )
    
    # Crear el rol
    db_role = Role(name=name)
    db.add(db_role)
    db.commit()
    db.refresh(db_role)
    return db_role

def update_role(db: Session, role_id: int, name: str) -> Optional[Role]:
    """Actualiza un rol existente"""
    db_role = get_role(db, role_id)
    if not db_role:
        return None
    
    # Verificar que el nuevo nombre no exista
    if name != db_role.name:
        existing_role = get_role_by_name(db, name)
        if existing_role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"El rol '{name}' ya existe"
            )
    
    # Actualizar el rol
    db_role.name = name
    db.commit()
    db.refresh(db_role)
    return db_role

def delete_role(db: Session, role_id: int) -> bool:
    """Elimina un rol"""
    db_role = get_role(db, role_id)
    if not db_role:
        return False
    
    db.delete(db_role)
    db.commit()
    return True

def assign_role_to_user(db: Session, user_id: int, role_id: int) -> User:
    """Asigna un rol a un usuario"""
    # Obtener el usuario
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Obtener el rol
    role = get_role(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )
    
    # Verificar si ya tiene el rol
    if role in user.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El usuario ya tiene el rol '{role.name}'"
        )
    
    # Asignar el rol
    user.roles.append(role)
    db.commit()
    db.refresh(user)
    return user

def remove_role_from_user(db: Session, user_id: int, role_id: int) -> User:
    """Quita un rol a un usuario"""
    # Obtener el usuario
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )
    
    # Obtener el rol
    role = get_role(db, role_id)
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rol no encontrado"
        )
    
    # Verificar si tiene el rol
    if role not in user.roles:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"El usuario no tiene el rol '{role.name}'"
        )
    
    # Quitar el rol
    user.roles.remove(role)
    db.commit()
    db.refresh(user)
    return user

def has_role(user: User, role_name: str) -> bool:
    """Verifica si un usuario tiene un rol específico"""
    return any(role.name == role_name for role in user.roles)

def is_admin(user: User) -> bool:
    """Verifica si un usuario tiene el rol de administrador"""
    return has_role(user, "Admin")

def is_regular_user(user: User) -> bool:
    """Verifica si un usuario tiene el rol de usuario regular"""
    return has_role(user, "User")

def is_client(user: User) -> bool:
    """Verifica si un usuario tiene el rol de cliente"""
    return has_role(user, "Client")

def is_veterinarian(user: User) -> bool:
    """Verifica si un usuario tiene el rol de veterinario"""
    return has_role(user, "Veterinarian") 