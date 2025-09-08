from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from typing import List
from datetime import date, datetime
import logging

from app.database.base import get_db
from app.services import produccion_embrionaria_service
from app.services.auth_service import get_current_user_from_token
from app.schemas.produccion_embrionaria import (
    ProduccionEmbrionariaCreate,
    ProduccionEmbrionariaInDB,
    ProduccionEmbrionariaDetail,
    ProduccionEmbrionariaUpdate,
    ProduccionEmbrionariaResumenPorFecha
)
from typing import Optional

from app.models.user import User

router = APIRouter(
    prefix="/produccion-embrionaria",
    tags=["produccion-embrionaria"],
    responses={404: {"description": "No encontrado"}},
)

@router.post("/", response_model=ProduccionEmbrionariaDetail)
def create_produccion_embrionaria(
    produccion: ProduccionEmbrionariaCreate, 
    db: Session = Depends(get_db)
):
    return produccion_embrionaria_service.create(db=db, data=produccion)

@router.put("/{production_id}", response_model=ProduccionEmbrionariaUpdate, status_code=status.HTTP_200_OK)
async def create_produccion_embrionaria(
    production_id:int,
    data: ProduccionEmbrionariaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Crear una producción embrionaria para un cliente específico (solo admin).
    """
    try:
        if not produccion_embrionaria_service.role_service.is_admin(current_user):
            raise HTTPException(status_code=403, detail="No autorizado")

        return produccion_embrionaria_service.update(db, production_id, data)
    except Exception as e:
        logging.error(f"Error al crear producción embrionaria: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear producción embrionaria: {str(e)}"
        )
    


@router.get("/mis", response_model=List[ProduccionEmbrionariaDetail])
async def get_my_producciones_embrionarias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    skip: int = Query(default=0, ge=0, description="Número de registros a omitir (paginación)"),
    limit: int = Query(default=100, ge=1, le=1000, description="Número máximo de registros a devolver (paginación)")
):
    """
    Listar todas las producciones embrionarias del cliente autenticado.
    Incluye paginación con parámetros skip y limit.
    """
    try:
        return produccion_embrionaria_service.get_by_cliente(db, current_user.id, skip=skip, limit=limit)
    except Exception as e:
        logging.error(f"Error al obtener producciones embrionarias del cliente: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener producciones embrionarias: {str(e)}"
        )


@router.get("/", response_model=List[ProduccionEmbrionariaDetail])
def get_all_producciones_embrionarias(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    query: Optional[str] = Query(None, description="Buscar por nombre, documento o correo del cliente"),
    fecha_inicio: Optional[date] = Query(None, description="Fecha de inicio (YYYY-MM-DD)"),
    fecha_fin: Optional[date] = Query(None, description="Fecha de fin (YYYY-MM-DD)"),
    skip: int = Query(default=0, ge=0, description="Número de registros a omitir (paginación)"),
    limit: int = Query(default=100, ge=1, le=1000, description="Número máximo de registros a devolver (paginación)")
):
    """
    Lista todas las producciones embrionarias con filtros opcionales por cliente y rango de fechas.
    Incluye paginación con parámetros skip y limit.
    """
    return produccion_embrionaria_service.get_all(
        db=db,
        current_user=current_user,
        fecha_inicio=fecha_inicio,
        fecha_fin=fecha_fin,
        query=query,
        skip=skip,
        limit=limit
    )


@router.get("/{production_id}", response_model=ProduccionEmbrionariaDetail, status_code=status.HTTP_200_OK)
async def create_produccion_embrionaria(
    production_id:int,
    db: Session = Depends(get_db)
):
    """
    Crear una producción embrionaria para un cliente específico (solo admin).
    """
    try:
        # if not produccion_embrionaria_service.role_service.is_admin(current_user):
        #     raise HTTPException(status_code=403, detail="No autorizado")

        return produccion_embrionaria_service.get_by_id(db, production_id)
    except Exception as e:
        logging.error(f"Error al crear producción embrionaria: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear producción embrionaria: {str(e)}"
        )

@router.get("/{production_id}/bulls-summary", response_model=List[dict])
def get_bulls_summary(
    production_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    # Solo admin o el dueño pueden consultar
    # (Opcional: agregar lógica de permisos si es necesario)
    return produccion_embrionaria_service.get_bulls_summary_by_produccion(db, production_id)


@router.get("/cliente/{cliente_id}", response_model=List[ProduccionEmbrionariaDetail])
def get_producciones_by_cliente_id(
    cliente_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token),
    skip: int = Query(default=0, ge=0, description="Número de registros a omitir (paginación)"),
    limit: int = Query(default=100, ge=1, le=1000, description="Número máximo de registros a devolver (paginación)")
):
    """
    Obtiene todas las producciones embrionarias de un cliente específico por su ID.
    
    - **cliente_id**: ID del cliente del cual se desean obtener las producciones
    - **skip**: Número de registros a omitir para paginación (por defecto: 0)
    - **limit**: Número máximo de registros a devolver (por defecto: 100, máximo: 1000)
    
    Requiere autenticación. Solo administradores pueden consultar producciones de cualquier cliente.
    """
    try:
        # Verificar si es administrador
        if not produccion_embrionaria_service.role_service.is_admin(current_user):
            # Si no es admin, solo puede ver sus propias producciones
            if current_user.id != cliente_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN, 
                    detail="No autorizado para ver producciones de otros clientes"
                )
        
        return produccion_embrionaria_service.get_by_cliente_id(
            db=db, 
            cliente_id=cliente_id, 
            skip=skip, 
            limit=limit
        )
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error al obtener producciones embrionarias del cliente {cliente_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener producciones embrionarias: {str(e)}"
        )