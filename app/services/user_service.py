from sqlalchemy.orm import Session
from app.models.user import User, Role
from app.schemas.user_schema import UserCreate, UserUpdate
from app.utils.security import get_password_hash, verify_password
from fastapi import HTTPException, status
from typing import List, Optional, Dict, Any
import logging
from sqlalchemy import func, or_
from app.services.s3_service import s3_service
import uuid

# Configurar logger
logger = logging.getLogger(__name__)

def get_user(db: Session, user_id: int) -> Optional[User]:
    """Obtiene un usuario por su ID"""
    return db.query(User).filter(User.id == user_id).first()

def get_user_by_email(db: Session, email: str) -> Optional[User]:
    """Obtiene un usuario por su email"""
    return db.query(User).filter(User.email == email).first()

def get_user_by_document(db: Session, number_document: str) -> Optional[User]:
    """Obtiene un usuario por su número de documento"""
    return db.query(User).filter(User.number_document == number_document).first()

def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    """Obtiene una lista de usuarios"""
    return db.query(User).offset(skip).limit(limit).all()

def filter_users(
    db: Session, 
    email: Optional[str] = None, 
    full_name: Optional[str] = None, 
    number_document: Optional[str] = None,
    role_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Filtra usuarios por email, nombre, número de documento y/o rol.
    Retorna una lista de diccionarios con información detallada del usuario.
    """
    # Crear consulta base con join a roles
    query = db.query(User).join(User.roles, isouter=True)
    
    # Aplicar filtros si se proporcionan
    if email:
        search_term = f"%{email.lower()}%"
        query = query.filter(func.lower(User.email).like(search_term))
    
    if full_name:
        search_term = f"%{full_name.lower()}%"
        query = query.filter(func.lower(User.full_name).like(search_term))
    
    if number_document:
        search_term = f"%{number_document.lower()}%"
        query = query.filter(func.lower(User.number_document).like(search_term))
    
    if role_id:
        query = query.filter(Role.id == role_id)
    
    # Aplicar paginación
    query = query.offset(skip).limit(limit).distinct()
    
    # Ejecutar consulta
    users = query.all()
    
    # Formatear resultados incluyendo los roles de cada usuario
    result = []
    for user in users:
        user_data = {
            "id": user.id,
            "number_document": user.number_document,
            "type_document": user.type_document,
            "specialty": user.specialty,
            "email": user.email,
            "phone": user.phone,
            "full_name": user.full_name,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "roles": [{"id": role.id, "name": role.name} for role in user.roles]
        }
        result.append(user_data)
    
    return result

def search_users(
    db: Session, 
    search_query: Optional[str] = None,
    role_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Busca usuarios con un criterio general que busca coincidencias en email, nombre o identificación.
    También permite filtrar por rol.
    Retorna una lista de diccionarios con información detallada del usuario.
    """
    # Crear consulta base con join a roles
    query = db.query(User).join(User.roles, isouter=True)
    
    # Aplicar búsqueda general si se proporciona
    if search_query:
        search_term = f"%{search_query.lower()}%"
        query = query.filter(
            or_(
                func.lower(User.email).like(search_term),
                func.lower(User.full_name).like(search_term),
                func.lower(User.number_document).like(search_term)
            )
        )
    
    # Filtrar por rol si se especifica
    if role_id:
        query = query.filter(Role.id == role_id)
    
    # Aplicar paginación
    query = query.offset(skip).limit(limit).distinct()
    
    # Ejecutar consulta
    users = query.all()
    
    # Formatear resultados incluyendo los roles de cada usuario
    result = []
    for user in users:
        user_data = {
            "id": user.id,
            "number_document": user.number_document,
            "type_document": user.type_document,
            "specialty": user.specialty,
            "email": user.email,
            "phone": user.phone,
            "full_name": user.full_name,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "roles": [{"id": role.id, "name": role.name} for role in user.roles]
        }
        result.append(user_data)
    
    return result

def create_user(db: Session, user: UserCreate) -> User:
    """
    Crea un nuevo usuario y le asigna el rol de Cliente por defecto.
    Solo los administradores pueden crear usuarios con otros roles.
    """
    # Verificar si el email ya existe
    if get_user_by_email(db, user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Verificar si el documento ya existe
    if get_user_by_document(db, user.number_document):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El número de documento ya está registrado"
        )
    
    # Crear el hash de la contraseña
    hashed_password = get_password_hash(user.password)
    
    # Crear el nuevo usuario
    db_user = User(
        number_document=user.number_document,
        specialty=user.specialty,
        email=user.email,
        phone=user.phone,
        full_name=user.full_name,
        type_document=user.type_document,
        pass_hash=hashed_password
    )
    
    # Guardar el usuario en la base de datos
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Asignar SOLO el rol de Cliente
    try:
        client_role = db.query(Role).filter(Role.name == "Client").first()
        if client_role:
            # Limpiar cualquier otro rol (por seguridad)
            db_user.roles = []
            # Asignar únicamente el rol Cliente
            db_user.roles.append(client_role)
            db.commit()
            db.refresh(db_user)
            logger.info(f"Rol de Cliente asignado al usuario: {user.email}")
        else:
            logger.warning("No se encontró el rol de Cliente para asignar al nuevo usuario")
    except Exception as e:
        logger.error(f"Error al asignar rol de Cliente: {str(e)}")
    
    return db_user

def update_user(db: Session, user_id: int, user: UserUpdate) -> Optional[User]:
    """Actualiza un usuario existente"""
    # Obtener el usuario
    db_user = get_user(db, user_id)
    if not db_user:
        return None
    
    # Actualizar los campos
    for key, value in user.dict(exclude_unset=True).items():
        if key == "password" and value:
            setattr(db_user, "pass_hash", get_password_hash(value))
        elif key != "password":
            setattr(db_user, key, value)
    
    # Guardar los cambios
    db.commit()
    db.refresh(db_user)
    return db_user

def delete_user(db: Session, user_id: int) -> bool:
    """Elimina un usuario"""
    db_user = get_user(db, user_id)
    if not db_user:
        return False
    
    db.delete(db_user)
    db.commit()
    return True

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Autentica un usuario"""
    user = get_user_by_email(db, email)
    if not user or not verify_password(password, user.pass_hash):
        return None
    return user

def create_user_by_admin(db: Session, user_data, role_ids: List[int]) -> User:
    """
    Crea un nuevo usuario con roles específicos. 
    Esta función solo debe ser utilizada por administradores.
    """
    # Verificar si el email ya existe
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El email ya está registrado"
        )
    
    # Verificar si el documento ya existe
    if get_user_by_document(db, user_data.number_document):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El número de documento ya está registrado"
        )
    
    # Crear el hash de la contraseña
    hashed_password = get_password_hash(user_data.password)
    
    # Crear el nuevo usuario
    db_user = User(
        number_document=user_data.number_document,
        specialty=user_data.specialty,
        email=user_data.email,
        phone=user_data.phone,
        full_name=user_data.full_name,
        type_document=user_data.type_document,
        pass_hash=hashed_password
    )
    
    # Guardar el usuario en la base de datos
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    # Asignar los roles especificados
    if role_ids:
        for role_id in role_ids:
            role = db.query(Role).filter(Role.id == role_id).first()
            if role:
                db_user.roles.append(role)
                logger.info(f"Rol '{role.name}' asignado al usuario: {user_data.email}")
            else:
                logger.warning(f"No se encontró el rol con ID {role_id}")
        
        db.commit()
        db.refresh(db_user)
    else:
        # Si no se especifican roles, asignar el rol de Cliente por defecto
        client_role = db.query(Role).filter(Role.name == "Client").first()
        if client_role:
            db_user.roles.append(client_role)
            db.commit()
            db.refresh(db_user)
            logger.info(f"Rol de Cliente asignado por defecto al usuario: {user_data.email}")
    
    return db_user

def upload_profile_picture(file, user_id):
    # Subir la nueva imagen
    file_extension = file.filename.split(".")[-1]
    object_name = f"profile-pictures/{user_id}/{uuid.uuid4()}.{file_extension}"
    file_url = s3_service.upload_file(file.file, object_name)
    if not file_url:
        raise HTTPException(status_code=500, detail="Could not upload file to S3")
    return file_url 