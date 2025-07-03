from passlib.context import CryptContext
from jose import JWTError, jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Callable
from decouple import config
from functools import wraps
from fastapi import HTTPException, status, Request, Depends, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import re

# Configuración del logger
logger = logging.getLogger(__name__)

# Configuración de seguridad
SECRET_KEY = config("SECRET_KEY", default="super_secret_key_change_this_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = int(config("ACCESS_TOKEN_EXPIRE_MINUTES", default="30"))

# Contexto de encriptación de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    """Verifica si la contraseña coincide con el hash"""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Genera un hash para la contraseña"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """Crea un token JWT con los datos especificados"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Decodifica un token JWT y retorna el payload sin lanzar excepciones.
    Si hay algún error retorna None.
    """
    try:
        # Intentar decodificar el token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        logger.error(f"Error al decodificar token JWT: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Error inesperado al decodificar token: {str(e)}")
        return None

def extract_token_from_header(authorization: str) -> Optional[str]:
    """
    Extrae el token JWT del encabezado de autorización.
    Maneja tanto el formato 'Bearer {token}' como directamente el token.
    
    Args:
        authorization: Encabezado de autorización
        
    Returns:
        El token JWT extraído o None si no se pudo extraer
    """
    if not authorization:
        return None
        
    # Extraer token del encabezado
    try:
        if authorization.lower().startswith("bearer "):
            # Formato estándar: "Bearer {token}"
            token = authorization.split("Bearer ", 1)[1].strip()
        else:
            # Si no tiene prefijo, usar directamente como token
            token = authorization.strip()
            
        # Verificar que el token no esté vacío
        if not token or token.lower() in ["undefined", "null"]:
            return None
            
        return token
    except Exception as e:
        logger.error(f"Error al extraer token: {str(e)}")
        return None

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware para manejar la autenticación en todas las rutas"""
    
    def __init__(self, app, exclude_paths: List[str] = None):
        super().__init__(app)
        self.exclude_paths = exclude_paths or [
            "/api/auth/login", 
            "/api/auth/register", 
            "/docs", 
            "/openapi.json", 
            "/", 
            "/favicon.ico",
            "/oauth2-redirect",
            "/static",
            "/_next"
        ]
        self.exclude_patterns = [re.compile(pattern) for pattern in [
            r"^/docs/.*", 
            r"^/redoc.*", 
            r"^/openapi\.json",
            r"^/static/.*",
            r"^/_next/.*"
        ]]
        self.security = HTTPBearer(auto_error=False)

    async def dispatch(self, request: Request, call_next: Callable):
        """Procesa la solicitud y verifica la autenticación"""
        path = request.url.path
        
        # Logging para depuración
        logger.info(f"Procesando solicitud a: {path}")
        
        # Verificar si la ruta está excluida
        if any(path.startswith(exclude) for exclude in self.exclude_paths) or \
           any(pattern.match(path) for pattern in self.exclude_patterns):
            logger.info(f"Ruta excluida de autenticación: {path}")
            return await call_next(request)

        # Obtener token de todas las fuentes posibles
        token = None
        
        # 1. Intentar obtener de encabezado Authorization
        auth_header = request.headers.get("Authorization")
        if auth_header:
            token = extract_token_from_header(auth_header)
            if token:
                logger.info(f"Token encontrado en encabezado: {token[:10]}...")
        
        # 2. Intentar obtener de cookies si no hay en encabezado
        if not token and "token" in request.cookies:
            token = request.cookies.get("token")
            logger.info(f"Token encontrado en cookies: {token[:10]}...")
            
        # 3. Intentar obtener de query params
        if not token and "token" in request.query_params:
            token = request.query_params["token"]
            logger.info(f"Token encontrado en query params: {token[:10]}...")
            
        # Si no hay token en ninguna fuente, continuar y dejar que el endpoint maneje la autenticación
        if not token:
            logger.info("No se encontró token, continuando sin autenticación")
            return await call_next(request)
            
        # Decodificar y validar el token
        payload = decode_token(token)
        if not payload:
            logger.warning("Token no válido")
            # Continuar y dejar que el endpoint maneje la autenticación
            return await call_next(request)
            
        # Agregar información del usuario al scope de la request
        request.state.user_id = payload.get("sub")
        logger.info(f"Usuario autenticado: {request.state.user_id}")
        
        # Permitir que la solicitud continúe
        response = await call_next(request)
        return response 