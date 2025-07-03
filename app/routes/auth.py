from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Cookie
from sqlalchemy.orm import Session
from app.database.base import get_db
from app.services.auth_service import login_user, get_current_user, get_current_user_from_token
from app.services.user_service import create_user
from app.services.role_service import get_role_by_name, assign_role_to_user
from app.schemas.user_schema import UserLogin, UserSchema, Token, UserCreate
from app.models.user import User
from typing import Optional
import logging

# Configurar logger
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
    responses={401: {"description": "No autorizado"}},
)

@router.post("/login", response_model=Token)
async def login(response: Response, user_data: UserLogin, db: Session = Depends(get_db)):
    """Inicia sesión y genera un token JWT"""
    token_result = login_user(db, user_data)
    
    # Guardar el token en una cookie
    response.set_cookie(
        key="token",
        value=token_result.access_token,
        httponly=True,
        samesite="lax",
        max_age=86400,  # 24 horas
    )
    
    return token_result

@router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """Registra un nuevo usuario con rol de Cliente exclusivamente"""
    # Crear el usuario
    db_user = create_user(db=db, user=user)
    
    # Asegurar que el usuario tenga solamente el rol de Client
    # Si el servicio create_user ya asigna el rol, esta parte está de más
    # pero nos aseguramos que solo tenga el rol Client
    client_role = get_role_by_name(db, "Client")
    if not client_role:
        logger.error("No se encontró el rol de Cliente")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al asignar rol de Cliente"
        )
    
    # Limpiar cualquier otro rol que pudiera tener (por si acaso)
    db_user.roles = []
    # Asignar solo el rol de Cliente
    db_user.roles.append(client_role)
    db.commit()
    db.refresh(db_user)
    
    logger.info(f"Usuario registrado con rol de Cliente: {user.email}")
    return db_user

@router.get("/me", response_model=UserSchema)
async def get_me(current_user: User = Depends(get_current_user_from_token)):
    """Obtiene la información del usuario autenticado"""
    return current_user

@router.post("/token-to-cookie")
async def set_token_cookie(response: Response, token: str, redirect_url: Optional[str] = None):
    """
    Configura el token JWT como una cookie.
    Útil para clientes frontend o Swagger cuando hay problemas con la autorización.
    """
    logger.info(f"Guardando token en cookie: {token[:10]}...")
    
    # Guardar el token en una cookie
    response.set_cookie(
        key="token",
        value=token,
        httponly=True,
        samesite="lax",
        max_age=86400,  # 24 horas
    )
    
    if redirect_url:
        # Si hay URL de redirección, hacer un redirect
        return {"status": "success", "message": "Token guardado en cookie", "redirect": redirect_url}
    
    return {"status": "success", "message": "Token guardado en cookie"}

@router.post("/clear-token")
async def clear_token_cookie(response: Response):
    """Elimina la cookie de token"""
    response.delete_cookie(key="token")
    return {"status": "success", "message": "Token eliminado"} 