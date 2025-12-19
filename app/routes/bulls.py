from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from app.database.base import get_db
from app.services import bull_service
from app.services.auth_service import get_current_user_from_token
from app.schemas.bull_schema import BullSchema, BullCreate, BullUpdate, BullStatus, BullDetailSchema, BullWithAvailableSamplesSchema
from app.models.user import User
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

router = APIRouter(
    prefix="/bulls",
    tags=["bulls"],
    responses={404: {"description": "No encontrado"}},
)

@router.get("/", response_model=List[BullDetailSchema])
async def read_bulls(
    request: Request,
    search_query: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None, 
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtiene la lista de toros con información detallada incluyendo datos del usuario que los registró.
    
    Parámetros:
    - search_query: Búsqueda general en nombre del toro, registro, documento o nombre del cliente
    - date_from: Fecha de inicio para filtrar por fecha de creación del toro
    - date_to: Fecha de fin para filtrar por fecha de creación del toro
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden ver sus propios toros
    - Los administradores pueden ver todos los toros
    """
    try:
        bulls_data = bull_service.get_bulls(
            db, 
            current_user=current_user, 
            search_query=search_query,
            date_from=date_from,
            date_to=date_to,
            skip=skip, 
            limit=limit
        )
        
        return bulls_data
    except Exception as e:
        # Registrar el error
        logger = logging.getLogger(__name__)
        logger.error(f"Error al obtener toros: {str(e)}")
        
        # Verificar si hay detalles del token en el error
        if hasattr(e, "detail") and "token" in str(e.detail).lower():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Problema con la autenticación. Por favor, asegúrate de enviar un token JWT válido.",
                headers={"WWW-Authenticate": "Bearer"},
            )
            
        # Re-lanzar la excepción original si no es un problema de token
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener toros: {str(e)}"
        )

@router.get("/my-bulls", response_model=List[BullSchema])
async def read_my_bulls(
    request: Request,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene los toros del usuario autenticado"""
    try:
        bulls = bull_service.get_bulls_by_user(db, user_id=current_user.id, skip=skip, limit=limit)
        
        # Convertir cada toro a esquema, ignorando los que no se puedan convertir
        bull_schemas = []
        for bull in bulls:
            try:
                schema = BullSchema.from_orm(bull)
                if schema:
                    bull_schemas.append(schema)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Error al convertir toro {bull.id} a esquema: {str(e)}")
                # Continuar con el siguiente toro
        
        return bull_schemas
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error al obtener toros del usuario: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener toros del usuario: {str(e)}"
        )

@router.get("/filter", response_model=List[BullSchema])
async def filter_bulls(
    request: Request,
    search_query: str = None,
    name: str = None,
    registration_number: str = None,
    race_id: int = None,
    sex_id: int = None,
    status: BullStatus = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Filtra toros por diversos criterios.
    
    Parámetros:
    - search_query: Búsqueda general (nombre del toro, registro, documento del cliente, nombre del cliente)
    - name: Filtrar específicamente por nombre del toro (coincidencia parcial)
    - registration_number: Filtrar específicamente por número de registro del toro (coincidencia parcial)
    - race_id: ID de la raza
    - sex_id: ID del sexo
    - status: Estado del toro (active/inactive)
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden ver sus propios toros
    - Los administradores pueden ver todos los toros
    """
    try:
        bulls = bull_service.filter_bulls(
            db, 
            current_user=current_user, 
            search_query=search_query,
            name=name,
            registration_number=registration_number,
            race_id=race_id,
            sex_id=sex_id,
            status=status,
            skip=skip, 
            limit=limit
        )
        
        # Convertir cada toro a esquema, ignorando los que no se puedan convertir
        bull_schemas = []
        for bull in bulls:
            try:
                schema = BullSchema.from_orm(bull)
                if schema:
                    bull_schemas.append(schema)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Error al convertir toro {bull.id} a esquema: {str(e)}")
                # Continuar con el siguiente toro
        
        return bull_schemas
    except Exception as e:
        # Registrar el error
        logger = logging.getLogger(__name__)
        logger.error(f"Error al filtrar toros: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al filtrar toros: {str(e)}"
        )

@router.get("/{bull_id}", response_model=BullSchema)
async def read_bull(
    bull_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtiene un toro por su ID.
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden ver sus propios toros
    - Los administradores pueden ver cualquier toro
    """
    try:
        db_bull = bull_service.get_bull(db, bull_id=bull_id, current_user=current_user)
        if not db_bull:
            raise HTTPException(status_code=404, detail="Toro no encontrado")
        
        schema = BullSchema.from_orm(db_bull)
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al convertir el toro a esquema"
            )
        
        return schema
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error al obtener toro {bull_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener toro: {str(e)}"
        )

@router.post("/", response_model=BullSchema, status_code=status.HTTP_201_CREATED)
async def create_bull(
    bull: BullCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Crea un nuevo toro"""
    try:
        new_bull = bull_service.create_bull(db=db, bull=bull, current_user=current_user)
        
        schema = BullSchema.from_orm(new_bull)
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al convertir el toro creado a esquema"
            )
        
        return schema
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error al crear toro: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear toro: {str(e)}"
        )

@router.put("/{bull_id}", response_model=BullSchema)
async def update_bull(
    bull_id: int, 
    bull: BullUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Actualiza un toro existente"""
    try:
        db_bull = bull_service.update_bull(db=db, bull_id=bull_id, bull=bull, current_user=current_user)
        if db_bull is None:
            raise HTTPException(status_code=404, detail="Toro no encontrado")
        
        schema = BullSchema.from_orm(db_bull)
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al convertir el toro actualizado a esquema"
            )
        
        return schema
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error al actualizar toro {bull_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar toro: {str(e)}"
        )

@router.delete("/{bull_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bull(
    bull_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Elimina un toro"""
    try:
        success = bull_service.delete_bull(db=db, bull_id=bull_id, current_user=current_user)
        if not success:
            raise HTTPException(status_code=404, detail="Toro no encontrado")
        return {"message": "Toro eliminado"}
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )

@router.get("/race/{race_id}", response_model=List[BullSchema])
async def read_bulls_by_race(
    race_id: int,
    request: Request,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene toros por raza"""
    try:
        bulls = bull_service.get_bulls_by_race(db, race_id=race_id, current_user=current_user, skip=skip, limit=limit)
        
        # Convertir cada toro a esquema, ignorando los que no se puedan convertir
        bull_schemas = []
        for bull in bulls:
            try:
                schema = BullSchema.from_orm(bull)
                if schema:
                    bull_schemas.append(schema)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Error al convertir toro {bull.id} a esquema: {str(e)}")
                # Continuar con el siguiente toro
        
        return bull_schemas
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error al obtener toros por raza {race_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener toros por raza: {str(e)}"
        )

@router.get("/sex/{sex_id}", response_model=List[BullSchema])
async def read_bulls_by_sex(
    sex_id: int,
    request: Request,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene toros por sexo"""
    try:
        bulls = bull_service.get_bulls_by_sex(db, sex_id=sex_id, current_user=current_user, skip=skip, limit=limit)
        
        # Convertir cada toro a esquema, ignorando los que no se puedan convertir
        bull_schemas = []
        for bull in bulls:
            try:
                schema = BullSchema.from_orm(bull)
                if schema:
                    bull_schemas.append(schema)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Error al convertir toro {bull.id} a esquema: {str(e)}")
                # Continuar con el siguiente toro
        
        return bull_schemas
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error al obtener toros por sexo {sex_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener toros por sexo: {str(e)}"
        )


@router.post("/client/{client_id}", response_model=BullSchema, status_code=status.HTTP_201_CREATED)
async def create_bull_for_client(
    client_id: int,
    bull: BullCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Crea un nuevo toro para un cliente específico.
    
    Solo administradores y veterinarios pueden usar este endpoint.
    
    Args:
        client_id: ID del cliente para quien se creará el toro
        bull: Datos del toro a crear
    
    Returns:
        El toro creado
        
    Raises:
        HTTPException: Si el usuario no tiene permisos o hay problemas con los datos
    """
    try:
        new_bull = bull_service.create_bull_for_client(
            db=db, 
            bull=bull, 
            client_id=client_id,
            current_user=current_user
        )
        
        schema = BullSchema.from_orm(new_bull)
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al convertir el toro creado a esquema"
            )
        
        return schema
        
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error al crear toro para el cliente {client_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear toro: {str(e)}"
        )

@router.get("/client/{client_id}", response_model=List[Dict[str, Any]])
async def get_bulls_by_client(
    client_id: int,
    request: Request,
    search: Optional[str] = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtiene todos los toros de un cliente específico.
    
    Args:
        client_id: ID del cliente cuyos toros se quieren obtener
        search: Término de búsqueda para filtrar por nombre, registro, lote, escalerilla u otros campos del toro
        skip: Número de registros a omitir (paginación)
        limit: Número máximo de registros a devolver (paginación)
    
    Returns:
        Lista de toros con información detallada incluyendo totales de entradas (Recibida, Utilizada, Disponible)
        
    Raises:
        HTTPException: Si el usuario no tiene permisos o hay problemas con los datos
    """
    try:
        bulls = bull_service.get_bulls_by_client(
            db=db,
            client_id=client_id,
            current_user=current_user,
            search_query=search,
            skip=skip,
            limit=limit
        )
        return bulls
        
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error al obtener toros del cliente {client_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener toros: {str(e)}"
        )

@router.get("/disponibles/{cliente_id}", response_model=List[BullSchema])
def get_bulls_with_available_inputs(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    # Solo admin, veterinario o el propio cliente pueden consultar
    # (Opcional: agregar lógica de permisos si es necesario)
    bulls = bull_service.get_bulls_with_available_inputs(db, cliente_id)
    return bulls

@router.get("/client/{client_id}/available-samples", response_model=List[BullWithAvailableSamplesSchema])
async def get_bulls_with_available_samples(
    client_id: int,
    request: Request,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtiene los toros de un cliente que tienen muestras disponibles (entradas con cantidad total > 0).
    
    Parámetros:
    - client_id: ID del cliente cuyos toros se quieren obtener
    - skip: Número de registros a omitir (paginación)
    - limit: Número máximo de registros a devolver (paginación)
    
    Restricciones de acceso:
    - Solo el cliente dueño o un administrador pueden ver los toros
    - Solo se muestran toros que tengan muestras disponibles (total > 0)
    
    Returns:
        Lista de diccionarios con información detallada de los toros y cantidad total disponible
    """
    try:
        bulls_data = bull_service.get_bulls_with_available_samples(
            db, 
            client_id=client_id,
            current_user=current_user,
            skip=skip, 
            limit=limit
        )
        
        return bulls_data
    except HTTPException:
        # Re-lanzar excepciones HTTP (como 403, 404) sin modificar
        raise
    except Exception as e:
        # Registrar el error
        logger = logging.getLogger(__name__)
        logger.error(f"Error al obtener toros con muestras disponibles para cliente {client_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener toros con muestras disponibles: {str(e)}"
        ) 