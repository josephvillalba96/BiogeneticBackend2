from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from app.database.base import get_db
from app.services import opus_service
from app.services.auth_service import get_current_user_from_token
from app.schemas.opus_schema import OpusCreate, OpusUpdate, OpusSchema, OpusDetail, OpusDateSummary, OpusDateDetail
from app.models.user import User
from typing import List, Dict, Any
import logging
from datetime import date

router = APIRouter(
    prefix="/opus",
    tags=["opus"],
    responses={404: {"description": "No encontrado"}},
)

@router.get("/", response_model=List[OpusDetail])
async def read_opus_list(
    request: Request,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtiene la lista de registros Opus.
    Si el usuario es cliente, solo verá sus propios registros.
    Si es admin o veterinario, verá todos los registros.
    """
    try:
        # Si el usuario es cliente, obtener solo sus registros
        if not (opus_service.role_service.is_admin(current_user) or opus_service.role_service.is_veterinarian(current_user)):
            return opus_service.get_opus_by_client(db, current_user.id, current_user, skip, limit)
        
        # Para admin y veterinarios, obtener todos los registros
        return opus_service.get_opus_by_client(db, None, current_user, skip, limit)
    except Exception as e:
        logging.error(f"Error al obtener registros Opus: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener registros: {str(e)}"
        )

@router.get("/{opus_id}", response_model=OpusDetail)
async def read_opus(
    opus_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene un registro Opus específico por su ID"""
    try:
        opus = opus_service.get_opus(db, opus_id, current_user)
        if not opus:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro no encontrado"
            )
        return opus
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error al obtener registro Opus {opus_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener registro: {str(e)}"
        )

@router.post("/", response_model=OpusDetail, status_code=status.HTTP_201_CREATED)
async def create_opus(
    opus: OpusCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Crea un nuevo registro Opus.
    Solo disponible para administradores y veterinarios.
    """
    try:
        return opus_service.create_opus(db, opus, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error al crear registro Opus: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear registro: {str(e)}"
        )

@router.put("/{opus_id}", response_model=OpusDetail)
async def update_opus(
    opus_id: int,
    opus: OpusUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Actualiza un registro Opus existente.
    Solo disponible para administradores y veterinarios.
    """
    try:
        updated_opus = opus_service.update_opus(db, opus_id, opus, current_user)
        if not updated_opus:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro no encontrado"
            )
        return updated_opus
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error al actualizar registro Opus {opus_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar registro: {str(e)}"
        )

@router.delete("/{opus_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_opus(
    opus_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Elimina un registro Opus.
    Solo disponible para administradores y veterinarios.
    """
    try:
        success = opus_service.delete_opus(db, opus_id, current_user)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Registro no encontrado"
            )
        return {"message": "Registro eliminado exitosamente"}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error al eliminar registro Opus {opus_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar registro: {str(e)}"
        )

@router.get("/client/{client_id}", response_model=List[OpusDetail])
async def read_opus_by_client(
    client_id: int,
    request: Request,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtiene todos los registros Opus de un cliente específico.
    - Si es cliente, solo puede ver sus propios registros
    - Si es veterinario o admin, puede ver los registros de cualquier cliente
    """
    try:
        # Si es cliente, solo puede ver sus propios registros
        if not (opus_service.role_service.is_admin(current_user) or opus_service.role_service.is_veterinarian(current_user)):
            if current_user.id != client_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para ver los registros de otros clientes"
                )
        
        return opus_service.get_opus_by_client(db, client_id, current_user, skip, limit)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error al obtener registros Opus del cliente {client_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener registros: {str(e)}"
        )

@router.get("/by-production/{prduction_id}", response_model=List[OpusDateDetail])
async def read_opus_by_date(
    prduction_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtiene todos los registros de Opus de una fecha específica para el cliente actual.
    Solo accesible para el propio cliente.
    Incluye información detallada de los bovinos (donante y toro).
    """
    try:
        # Verificar que el usuario sea cliente
        # if not opus_service.role_service.is_client(current_user):
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Esta ruta solo está disponible para clientes"
        #     )
        
        return opus_service.get_opus_by_production_for_client(db, prduction_id, current_user)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error al obtener registros Opus de la producción {prduction_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener registros: {str(e)}"
        )

@router.get("/summary/by-date", response_model=List[OpusDateSummary])
async def get_opus_summary_by_date(
    request: Request,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtiene un resumen de los registros Opus agrupados por fecha.
    Para cada fecha muestra:
    - Nombre del cliente
    - Total de registros
    - Total de oocitos
    - Total de embriones
    - Porcentaje de éxito
    - Promedio de embriones por registro
    
    Si el usuario es cliente, solo verá sus propios registros.
    Si es admin o veterinario, verá todos los registros.
    """
    try:
        return opus_service.get_opus_grouped_by_date(db, current_user, skip, limit)
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error al obtener resumen de Opus por fecha: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener resumen: {str(e)}"
        ) 