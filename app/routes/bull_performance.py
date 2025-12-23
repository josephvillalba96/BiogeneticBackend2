from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.base import get_db
from app.models.user import User
from app.services.auth_service import get_current_user_from_token
from app.services.bull_performance_service import get_bull_performance, get_bull_performance_summary
from app.schemas.bull_performance_schema import BullPerformanceResponse, BullPerformanceItem, BullPerformanceSummary
import logging

# Configurar logger
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/bull-performance", tags=["Bull Performance"])

@router.get("/", response_model=BullPerformanceResponse)
async def get_bull_performance_data(
    client_id: Optional[int] = Query(default=None, description="ID del cliente para filtrar toros"),
    raza_id: Optional[int] = Query(default=None, description="ID de la raza para filtrar toros"),
    query: Optional[str] = Query(default=None, description="Búsqueda general por lote, nombre del toro, número de registro o ID de raza"),
    page: int = Query(default=1, ge=1, description="Número de página"),
    page_size: int = Query(default=100, ge=1, le=1000, description="Tamaño de página"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtiene el rendimiento de los toros basado en los filtros proporcionados.
    
    Filtros disponibles:
    - client_id: Filtrar por ID de cliente
    - raza_id: Filtrar por ID de raza de toro
    - query: Búsqueda general por lote, nombre del toro, número de registro o ID de raza (búsqueda parcial)
    
    Si el usuario no es administrador, solo podrá ver sus propios toros.
    """
    
    try:
        # Si el usuario no es administrador, filtrar por su ID
        if not current_user.is_admin:
            client_id = current_user.id
        
        # Calcular offset para paginación
        skip = (page - 1) * page_size
        
        # Obtener datos de rendimiento
        performance_data = get_bull_performance(
            db=db,
            client_id=client_id,
            raza_id=raza_id,
            query=query,
            skip=skip,
            limit=page_size
        )
        
        # Obtener resumen estadístico
        summary_data = get_bull_performance_summary(
            db=db,
            client_id=client_id,
            raza_id=raza_id,
            query=query
        )
        
        # Convertir datos a esquemas
        performance_items = [
            BullPerformanceItem(**item) for item in performance_data
        ]
        
        summary = BullPerformanceSummary(**summary_data)
        
        # Crear respuesta
        response = BullPerformanceResponse(
            data=performance_items,
            summary=summary,
            total_records=len(performance_items),
            page=page,
            page_size=page_size
        )
        
        logger.info(f"Consulta de rendimiento de toros ejecutada para usuario {current_user.email}. {len(performance_items)} registros devueltos.")
        
        return response
        
    except Exception as e:
        logger.error(f"Error en endpoint de rendimiento de toros: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener datos de rendimiento: {str(e)}"
        )

@router.get("/summary", response_model=BullPerformanceSummary)
async def get_bull_performance_summary_only(
    client_id: Optional[int] = Query(default=None, description="ID del cliente para filtrar toros"),
    raza_id: Optional[int] = Query(default=None, description="ID de la raza para filtrar toros"),
    query: Optional[str] = Query(default=None, description="Búsqueda general por lote, nombre del toro, número de registro o ID de raza"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtiene solo el resumen estadístico del rendimiento de toros.
    
    Útil para obtener estadísticas generales sin los datos detallados.
    
    Filtros disponibles:
    - client_id: Filtrar por ID de cliente
    - raza_id: Filtrar por ID de raza de toro
    - query: Búsqueda general por lote, nombre del toro, número de registro, nombre de raza o ID de raza
    """
    
    try:
        # Si el usuario no es administrador, filtrar por su ID
        if not current_user.is_admin:
            client_id = current_user.id
        
        # Obtener resumen estadístico
        summary_data = get_bull_performance_summary(
            db=db,
            client_id=client_id,
            raza_id=raza_id,
            query=query
        )
        
        summary = BullPerformanceSummary(**summary_data)
        
        logger.info(f"Resumen de rendimiento de toros obtenido para usuario {current_user.email}.")
        
        return summary
        
    except Exception as e:
        logger.error(f"Error en endpoint de resumen de rendimiento: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener resumen de rendimiento: {str(e)}"
        )
