from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from app.database.base import get_db
from app.services import output_service
from app.services.auth_service import get_current_user_from_token
from app.models.user import User
from app.schemas.input_output_schema import OutputSchema, OutputCreate, OutputUpdate
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime

# Configurar logger
logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/outputs",
    tags=["outputs"],
    responses={404: {"description": "No encontrado"}},
)

@router.get("/", response_model=List[Dict[str, Any]])
async def read_outputs(
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
    Obtiene la lista de outputs con filtros opcionales.
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden ver outputs de sus propios inputs
    - Los administradores pueden ver todos los outputs
    """
    try:
        outputs = output_service.filter_outputs(
            db=db, 
            search_query=search_query,
            date_from=date_from,
            date_to=date_to,
            current_user=current_user,
            skip=skip, 
            limit=limit
        )
        
        return outputs
    except Exception as e:
        logger.error(f"Error al obtener outputs: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener outputs: {str(e)}"
        )

@router.get("/input/{input_id}", response_model=List[OutputSchema])
async def read_outputs_by_input(
    input_id: int,
    request: Request,
    skip: int = 0, 
    limit: int = 100, 
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtiene los outputs de un input específico.
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden ver outputs de sus propios inputs
    - Los administradores pueden ver los outputs de cualquier input
    """
    try:
        outputs = output_service.get_outputs_by_input(
            db=db, 
            input_id=input_id, 
            current_user=current_user,
            skip=skip, 
            limit=limit
        )
        
        return outputs
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al obtener outputs del input {input_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener outputs: {str(e)}"
        )

@router.get("/{output_id}", response_model=OutputSchema)
async def read_output(
    output_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtiene un output específico por su ID.
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden ver outputs de sus propios inputs
    - Los administradores pueden ver cualquier output
    """
    try:
        output = output_service.get_output(db=db, output_id=output_id, current_user=current_user)
        
        if not output:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Output no encontrado"
            )
        
        return output
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al obtener output {output_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener output: {str(e)}"
        )

@router.post("/input/{input_id}", response_model=OutputSchema)
async def create_output(
    input_id: int,
    output_data: OutputCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Crea un nuevo output para un input específico.
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden crear outputs para sus propios inputs
    - Los administradores pueden crear outputs para cualquier input
    
    Verificaciones:
    - La cantidad a tomar no puede exceder la cantidad disponible
    """
    try:
        output = output_service.create_output(
            db=db, 
            input_id=input_id, 
            output_data=output_data, 
            user_id=current_user.id, 
            current_user=current_user
        )
        
        return output
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al crear output para input {input_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear output: {str(e)}"
        )

@router.put("/{output_id}", response_model=OutputSchema)
async def update_output(
    output_id: int,
    output_data: OutputUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Actualiza un output existente.
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden actualizar outputs de sus propios inputs
    - Los administradores pueden actualizar cualquier output
    
    Verificaciones:
    - Si se modifica la cantidad, no puede exceder la cantidad disponible
    """
    try:
        output = output_service.update_output(
            db=db, 
            output_id=output_id, 
            output_data=output_data, 
            user_id=current_user.id, 
            current_user=current_user
        )
        
        if not output:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Output no encontrado"
            )
        
        return output
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al actualizar output {output_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar output: {str(e)}"
        )

@router.delete("/{output_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_output(
    output_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Elimina un output existente.
    
    Restricciones de acceso:
    - Los usuarios normales solo pueden eliminar outputs de sus propios inputs
    - Los administradores pueden eliminar cualquier output
    """
    try:
        success = output_service.delete_output(
            db=db, 
            output_id=output_id, 
            user_id=current_user.id, 
            current_user=current_user
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Output no encontrado"
            )
        
        return {"message": "Output eliminado correctamente"}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error al eliminar output {output_id}: {str(e)}")
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar output: {str(e)}"
        ) 