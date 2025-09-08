from sqlalchemy.orm import Session
from app.models.user import User
from app.utils.security import create_access_token, verify_password, decode_token, extract_token_from_header
from app.schemas.user_schema import UserLogin, Token
from fastapi import HTTPException, status, Depends, Header, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from app.utils.security import SECRET_KEY, ALGORITHM
from app.services.user_service import get_user_by_email, get_user
from typing import Optional
from datetime import timedelta
from app.database.base import get_db
import logging

# Configurar logger
logger = logging.getLogger(__name__)

# Definir el esquema de autenticación OAuth2
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login", auto_error=False)

def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    """Autentica un usuario"""
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.pass_hash):
        return None
    return user

def login_user(db: Session, user_data: UserLogin) -> Token:
    """Login de usuario y generación de token JWT"""
    user = authenticate_user(db, user_data.email, user_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Generar token JWT
    access_token_expires = timedelta(minutes=1440)  # 24 horas
    access_token = create_access_token(
        data={"sub": str(user.id)}, expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")

async def get_current_user_from_token(request: Request = None, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    """
    Obtiene el usuario actual a partir del token JWT, con múltiples fuentes posibles:
    1. Primero intenta usar el token proporcionado por FastAPI Depends
    2. Luego intenta obtenerlo del encabezado Authorization
    3. Finalmente intenta obtenerlo de los cookies o query params
    """
    # Configurar logging avanzado
    logger.info("Iniciando proceso de autenticación")
    if token:
        logger.info(f"Token recibido por Depends: {token[:10]}...")
    
    # 1. Intentar obtener token del mecanismo de dependencies de FastAPI
    final_token = token
    
    try:
        # 2. Si no hay token o está en Request, intentar obtenerlo del encabezado
        if request and (not final_token or final_token == ""):
            auth_header = request.headers.get("Authorization")
            if auth_header:
                header_token = extract_token_from_header(auth_header)
                if header_token:
                    logger.info(f"Token obtenido del encabezado: {header_token[:10]}...")
                    final_token = header_token
            
            # 3. Intentar obtener de cookies o query params si aún no hay token
            if not final_token or final_token == "":
                # Intentar de cookies
                if "token" in request.cookies:
                    final_token = request.cookies.get("token")
                    logger.info(f"Token obtenido de cookies: {final_token[:10]}...")
                # Intentar de query params
                elif "token" in request.query_params:
                    final_token = request.query_params["token"]
                    logger.info(f"Token obtenido de query params: {final_token[:10]}...")
        
        # Si después de todo no hay token, lanzar excepción
        if not final_token or final_token == "":
            logger.warning("No se encontró token en ninguna fuente")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="No se proporcionó token de autenticación",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        # Procesar el token final
        user = await _process_token(final_token, db)
        logger.info(f"Usuario autenticado correctamente: {user.email}")
        return user
    except Exception as e:
        logger.error(f"Error en autenticación: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error en autenticación: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(authorization: Optional[str] = Header(None), db: Session = Depends(get_db)) -> User:
    """Obtiene el usuario actual a partir del encabezado de autorización"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se proporcionó token de autenticación",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Extraer el token del encabezado
    token = extract_token_from_header(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Formato de autorización incorrecto",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Procesar el token
    return await _process_token(token, db)

async def _process_token(token: str, db: Session) -> User:
    """Procesa el token JWT y devuelve el usuario"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decodificar el token usando la función auxiliar
        payload = decode_token(token)
        if not payload:
            logger.error("Token no válido o expirado")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token no válido o expirado",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        logger.info("Token decodificado correctamente")
            
        user_id = payload.get("sub")
        if user_id is None:
            logger.error("Token no contiene campo 'sub'")
            raise credentials_exception
                
        logger.info(f"ID de usuario extraído: {user_id}")
        
        # Obtener el usuario
        try:
            user = get_user(db, int(user_id))
            if user is None:
                logger.error(f"Usuario con ID {user_id} no encontrado")
                raise credentials_exception
                
            logger.info(f"Usuario encontrado: {user.email}")
            return user
        except Exception as e:
            logger.error(f"Error al obtener usuario: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Error al obtener usuario: {str(e)}",
                headers={"WWW-Authenticate": "Bearer"},
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error no manejado: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Error en autenticación: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) 

async def get_current_active_user(current_user: User = Depends(get_current_user_from_token)) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_current_admin_user(current_user: User = Depends(get_current_active_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges",
        )
    return current_user 