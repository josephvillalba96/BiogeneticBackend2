from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from app.database.base import get_db
from app.services import input_service, role_service
from app.services.auth_service import get_current_user_from_token
from app.models.user import User
from app.models.input_output import InputStatus
from app.schemas.input_output_schema import (
    InputSchema, InputCreate, InputUpdate, 
    OutputSchema, OutputCreate, OutputUpdate,
    InputFilter, InputDetailSchema
)
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime
from app.models.bull import Bull

# Configurar logger
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/inputs",
    tags=["inputs"],
    responses={404: {"description": "No encontrado"}},
)

@router.get("/", response_model=List[InputSchema])
async def read_inputs(
    request: Request,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtiene la lista de inputs.
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden ver inputs de sus propios toros
    - Los administradores pueden ver todos los inputs de todos los toros
    """
    try:
        inputs = input_service.get_inputs(db, current_user=current_user, skip=skip, limit=limit)
        
        # Convertir cada input a esquema, ignorando los que no se puedan convertir
        input_schemas = []
        for input_obj in inputs:
            try:
                schema = InputSchema.from_orm(input_obj)
                if schema:
                    input_schemas.append(schema)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Error al convertir input {input_obj.id} a esquema: {str(e)}")
                # Continuar con el siguiente input
        
        return input_schemas
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error al obtener inputs: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener inputs: {str(e)}"
        )

@router.get("/filter", response_model=List[Dict[str, Any]])
async def filter_inputs(
    request: Request,
    search_query: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    status: Optional[str] = None,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Busca inputs usando un único parámetro de búsqueda que detecta automáticamente:
    - Número de documento del cliente
    - Nombre del cliente
    - Nombre del toro
    - Número de registro del toro
    
    También permite filtrar por:
    - Rango de fechas (date_from, date_to)
    - Estado del input (status: pending, processing, completed, cancelled)
    
    Retorna resultados detallados con información del toro y cliente.
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden ver inputs de sus propios toros
    - Los administradores pueden ver todos los inputs de todos los toros
    """
    try:
        inputs = input_service.filter_inputs(
            db=db, 
            search_query=search_query,
            date_from=date_from,
            date_to=date_to,
            status=status,
            current_user=current_user,
            skip=skip, 
            limit=limit
        )
        
        return inputs
    except Exception as e:
        logger.error(f"Error al filtrar inputs: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al filtrar inputs: {str(e)}"
        )

@router.get("/user/{user_id}", response_model=List[InputSchema])
async def read_user_inputs(
    user_id: int,
    request: Request,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtiene los inputs de un usuario específico.
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden ver sus propios inputs
    - Los administradores pueden ver los inputs de cualquier usuario
    """
    try:
        inputs = input_service.get_inputs_by_user(
            db, 
            user_id=user_id, 
            current_user=current_user,
            skip=skip, 
            limit=limit
        )
        
        # Convertir cada input a esquema, ignorando los que no se puedan convertir
        input_schemas = []
        for input_obj in inputs:
            try:
                schema = InputSchema.from_orm(input_obj)
                if schema:
                    input_schemas.append(schema)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Error al convertir input {input_obj.id} a esquema: {str(e)}")
                # Continuar con el siguiente input
        
        return input_schemas
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error al obtener inputs del usuario {user_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener inputs: {str(e)}"
        )

@router.get("/bull/{bull_id}", response_model=List[InputSchema])
async def read_bull_inputs(
    bull_id: int,
    request: Request,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtiene los inputs de un toro específico.
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden ver los inputs de sus propios toros
    - Los administradores pueden ver los inputs de todos los toros
    """
    try:
        inputs = input_service.get_inputs_by_bull(
            db, 
            bull_id=bull_id, 
            current_user=current_user,
            skip=skip, 
            limit=limit
        )
        
        # Convertir cada input a esquema, ignorando los que no se puedan convertir
        input_schemas = []
        for input_obj in inputs:
            try:
                schema = InputSchema.from_orm(input_obj)
                if schema:
                    input_schemas.append(schema)
            except Exception as e:
                logger = logging.getLogger(__name__)
                logger.error(f"Error al convertir input {input_obj.id} a esquema: {str(e)}")
                # Continuar con el siguiente input
        
        return input_schemas
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error al obtener inputs del toro {bull_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener inputs: {str(e)}"
        )

@router.get("/{input_id}", response_model=InputSchema)
async def read_input(
    input_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtiene un input por su ID.
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden ver sus propios inputs
    - Los administradores pueden ver cualquier input
    """
    try:
        input_obj = input_service.get_input(db, input_id=input_id, current_user=current_user)
        if not input_obj:
            raise HTTPException(status_code=404, detail="Input no encontrado")
        
        schema = InputSchema.from_orm(input_obj)
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al convertir el input a esquema"
            )
        
        return schema
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error al obtener input {input_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener input: {str(e)}"
        )

@router.post("/", response_model=InputSchema, status_code=status.HTTP_201_CREATED)
async def create_input(
    input_data: InputCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Crea un nuevo input.
    Si el usuario es admin, puede crear inputs para cualquier usuario.
    Si no es admin, solo puede crear inputs para sí mismo.
    
    El user_id en el input_data especifica a qué usuario se asignará el input.
    """
    try:
        # Verificar permisos
        if not role_service.is_admin(current_user) and input_data.user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tienes permiso para crear inputs para otros usuarios"
            )
        
        # Crear el input
        new_input = input_service.create_input(
            db=db,
            input_data=input_data,
            user_id=input_data.user_id,  # Usar el user_id del input_data
            current_user=current_user
        )
        
        return new_input
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al crear input: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear input: {str(e)}"
        )

@router.put("/{input_id}", response_model=InputSchema)
async def update_input(
    input_id: int,
    input_data: InputUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Actualiza un input existente.
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden actualizar sus propios inputs
    - Los administradores pueden actualizar cualquier input
    """
    try:
        updated_input = input_service.update_input(
            db=db, 
            input_id=input_id, 
            input_data=input_data, 
            user_id=current_user.id,
            current_user=current_user
        )
        
        if not updated_input:
            raise HTTPException(status_code=404, detail="Input no encontrado")
        
        schema = InputSchema.from_orm(updated_input)
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al convertir el input actualizado a esquema"
            )
        
        return schema
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error al actualizar input {input_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar input: {str(e)}"
        )

@router.delete("/{input_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_input(
    input_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Elimina un input.
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden eliminar sus propios inputs
    - Los administradores pueden eliminar cualquier input
    """
    success = input_service.delete_input(
        db=db, 
        input_id=input_id, 
        user_id=current_user.id,
        current_user=current_user
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Input no encontrado")
    
    return {"message": "Input eliminado"}

@router.put("/{input_id}/status/{status_name}")
async def change_input_status(
    input_id: int,
    status_name: InputStatus,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Cambia el estado de un input.
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden cambiar el estado de sus propios inputs
    - Los administradores pueden cambiar el estado de cualquier input
    """
    updated_input = input_service.change_input_status(
        db=db, 
        input_id=input_id, 
        status=status_name, 
        user_id=current_user.id,
        current_user=current_user
    )
    
    if not updated_input:
        raise HTTPException(status_code=404, detail="Input no encontrado")
    
    return {"message": f"Estado del input cambiado a {status_name}"}

@router.post("/{input_id}/outputs", response_model=OutputSchema)
async def add_output(
    input_id: int,
    output_data: OutputCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Añade un output a un input existente.
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden añadir outputs a sus propios inputs
    - Los administradores pueden añadir outputs a cualquier input
    """
    new_output = input_service.add_output_to_input(
        db=db, 
        input_id=input_id, 
        output_data=output_data, 
        user_id=current_user.id,
        current_user=current_user
    )
    
    return new_output

@router.post("/bull/{bull_id}", response_model=InputSchema, status_code=status.HTTP_201_CREATED)
async def create_input_for_bull(
    bull_id: int,
    input_data: InputCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Crea una nueva entrada/muestra para un toro específico.
    
    Solo administradores y veterinarios pueden usar este endpoint.
    
    Args:
        bull_id: ID del toro al que se le agregará la entrada
        input_data: Datos de la entrada a crear
    
    Returns:
        La entrada creada
        
    Raises:
        HTTPException: Si el usuario no tiene permisos o hay problemas con los datos
    """
    try:
        new_input = input_service.create_input_for_bull(
            db=db,
            bull_id=bull_id,
            input_data=input_data,
            current_user=current_user
        )
        
        # Convertir a esquema
        schema = InputSchema.from_orm(new_input)
        if not schema:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error al convertir la entrada creada a esquema"
            )
        
        return schema
        
    except HTTPException:
        raise
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error al crear entrada para el toro {bull_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear entrada: {str(e)}"
        ) 