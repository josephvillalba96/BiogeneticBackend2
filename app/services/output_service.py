from sqlalchemy.orm import Session
from app.models.input_output import Input, Output, InputStatus
from app.models.user import User
from app.models.bull import Bull
from app.schemas.input_output_schema import OutputCreate, OutputUpdate
from app.services import role_service
from fastapi import HTTPException, status
from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, date
from sqlalchemy import and_, or_, func, between, cast, String

# Configurar logger
logger = logging.getLogger(__name__)

def get_output(db: Session, output_id: int, current_user: Optional[User] = None) -> Optional[Output]:
    """
    Obtiene un output por su ID.
    Si se proporciona un usuario y no es administrador, verifica que le pertenezca a través del input.
    """
    output = db.query(Output).filter(Output.id == output_id).first()
    
    if not output:
        return None
    
    # Obtener el input asociado para verificar permisos
    input_obj = db.query(Input).filter(Input.id == output.input_id).first()
    
    # Si se proporciona un usuario y no es administrador, verificar que el input le pertenezca
    if current_user and not role_service.is_admin(current_user) and input_obj and input_obj.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver este output"
        )
    
    return output

def get_outputs(db: Session, current_user: Optional[User] = None, skip: int = 0, limit: int = 100) -> List[Output]:
    """
    Obtiene una lista de outputs.
    Si se proporciona un usuario y no es administrador, filtra por los outputs de sus inputs.
    """
    if current_user and not role_service.is_admin(current_user):
        # Subconsulta para obtener los inputs del usuario
        inputs_query = db.query(Input.id).filter(Input.user_id == current_user.id)
        
        # Consulta principal filtrando por los inputs del usuario
        return db.query(Output).filter(Output.input_id.in_(inputs_query)).offset(skip).limit(limit).all()
    else:
        return db.query(Output).offset(skip).limit(limit).all()

def get_outputs_by_input(db: Session, input_id: int, current_user: Optional[User] = None, skip: int = 0, limit: int = 100) -> List[Output]:
    """
    Obtiene los outputs de un input específico.
    Si se proporciona un usuario y no es administrador, verifica que el input le pertenezca.
    """
    # Verificar que el input exista
    input_obj = db.query(Input).filter(Input.id == input_id).first()
    if not input_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Input no encontrado"
        )
    
    # Si hay un usuario y no es administrador, verificar que el input le pertenezca
    if current_user and not role_service.is_admin(current_user) and input_obj.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver los outputs de este input"
        )
    
    return db.query(Output).filter(Output.input_id == input_id).offset(skip).limit(limit).all()

def filter_outputs(db: Session, search_query: Optional[str] = None, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, current_user: Optional[User] = None, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Filtra outputs por fecha y/o texto de búsqueda.
    Retorna outputs con información detallada del input, toro asociado y cliente.
    """
    # Consulta base con joins para obtener información completa
    query = db.query(
        Output,
        Input.quantity_received,
        Input.escalarilla,
        Input.lote,
        Input.bull_id,
        Input.user_id,
        User.full_name.label('client_name'),
        User.number_document.label('client_document'),
        Bull.name.label('bull_name'),
        Bull.registration_number.label('bull_register')
    ).join(
        Input, Output.input_id == Input.id
    ).join(
        User, Input.user_id == User.id
    ).join(
        Bull, Input.bull_id == Bull.id
    )
    
    # Si hay un usuario y no es administrador, filtrar por sus inputs
    if current_user and not role_service.is_admin(current_user):
        query = query.filter(Input.user_id == current_user.id)
    
    # Aplicar filtro de búsqueda si se proporciona
    if search_query:
        search_term = f"%{search_query.lower()}%"
        query = query.filter(
            or_(
                func.lower(Input.lote).like(search_term),
                func.lower(Input.escalarilla).like(search_term),
                func.lower(cast(Output.remark, String)).like(search_term),
                func.lower(User.full_name).like(search_term),
                func.lower(User.number_document).like(search_term),
                func.lower(Bull.name).like(search_term),
                func.lower(cast(Bull.registration_number, String)).like(search_term)
            )
        )
    
    # Aplicar filtro de rango de fechas
    if date_from and date_to:
        query = query.filter(Output.output_date.between(date_from, date_to))
    elif date_from:
        query = query.filter(Output.output_date >= date_from)
    elif date_to:
        query = query.filter(Output.output_date <= date_to)
    
    # Ordenar y aplicar paginación
    query = query.order_by(Output.output_date.desc()).offset(skip).limit(limit)
    
    # Ejecutar consulta
    results = query.all()
    
    # Formatear resultados
    formatted_results = []
    for result in results:
        output = result[0]
        formatted_results.append({
            "output_id": output.id,
            "input_id": output.input_id,
            "output_date": output.output_date,
            "quantity_output": output.quantity_output,
            "remark": output.remark,
            "escalarilla": result.escalarilla,
            "lote": result.lote,
            "quantity_received": result.quantity_received,
            "bull_id": result.bull_id,
            "bull_name": result.bull_name,
            "bull_register": result.bull_register,
            "user_id": result.user_id,
            "client_name": result.client_name,
            "client_document": result.client_document,
            "created_at": output.created_at,
            "updated_at": output.updated_at
        })
    
    return formatted_results

def create_output(db: Session, input_id: int, output_data: OutputCreate, user_id: int, current_user: Optional[User] = None) -> Output:
    """
    Crea un nuevo output para un input existente y actualiza la cantidad disponible del input.
    Verifica que la cantidad de salida no exceda la cantidad disponible.
    """
    # Obtener el input
    input_obj = db.query(Input).filter(Input.id == input_id).first()
    if not input_obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Input no encontrado"
        )
    
    # Verificar que el input pertenezca al usuario (salvo que sea admin)
    if current_user and not role_service.is_admin(current_user) and input_obj.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para crear outputs para este input"
        )
    
    # Calcular la cantidad total ya tomada a través de outputs existentes
    existing_outputs_total = db.query(func.sum(Output.quantity_output)).filter(Output.input_id == input_id).scalar() or 0
    
    # Calcular la cantidad disponible (quantity_received - cantidad ya tomada en outputs)
    available_quantity = input_obj.quantity_received - existing_outputs_total
    
    # Verificar que la cantidad de salida no exceda la cantidad disponible
    if output_data.quantity_output > available_quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La cantidad de salida ({output_data.quantity_output}) excede la cantidad disponible ({available_quantity})"
        )
    
    # Crear el output
    db_output = Output(
        input_id=input_id,
        output_date=output_data.output_date or datetime.now(),
        quantity_output=output_data.quantity_output,
        remark=output_data.remark
    )
    
    # Guardar el output en la base de datos
    db.add(db_output)
    
    # Actualizar la cantidad tomada y el total restante en el input
    input_obj.quantity_taken = existing_outputs_total + output_data.quantity_output
    input_obj.total = input_obj.quantity_received - input_obj.quantity_taken
    
    # Si la cantidad tomada es igual a la recibida, marcar como completed
    if input_obj.quantity_taken >= input_obj.quantity_received:
        input_obj.status_id = InputStatus.completed
    # Si hay alguna cantidad tomada pero no toda, marcar como processing
    elif input_obj.quantity_taken > 0:
        input_obj.status_id = InputStatus.processing
    
    # Guardar cambios
    db.commit()
    db.refresh(db_output)
    
    logger.info(f"Output creado para el input {input_id} por el usuario {user_id}")
    return db_output

def update_output(db: Session, output_id: int, output_data: OutputUpdate, user_id: int, current_user: Optional[User] = None) -> Optional[Output]:
    """
    Actualiza un output existente y ajusta la cantidad tomada del input asociado.
    Verifica que la nueva cantidad no exceda la cantidad disponible.
    """
    # Obtener el output
    output = get_output(db, output_id, current_user)
    if not output:
        return None
    
    # Obtener el input asociado
    input_obj = db.query(Input).filter(Input.id == output.input_id).first()
    
    # Verificar que el input pertenezca al usuario (salvo que sea admin)
    if current_user and not role_service.is_admin(current_user) and input_obj and input_obj.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para actualizar este output"
        )
    
    # Si se va a cambiar la cantidad, verificar disponibilidad
    if output_data.quantity_output is not None and output_data.quantity_output != output.quantity_output:
        # Calcular la cantidad total tomada de otros outputs (excluyendo el actual)
        other_outputs_total = db.query(func.sum(Output.quantity_output)).filter(
            and_(Output.input_id == output.input_id, Output.id != output_id)
        ).scalar() or 0
        
        # Calcular la cantidad disponible (quantity_received - cantidad tomada por otros outputs)
        available_quantity = input_obj.quantity_received - other_outputs_total
        
        # Verificar que la nueva cantidad no exceda la disponible
        if output_data.quantity_output > available_quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"La cantidad de salida ({output_data.quantity_output}) excede la cantidad disponible ({available_quantity})"
            )
        
        # Guardar la cantidad original para calcular el ajuste después
        original_quantity = output.quantity_output
    
    # Actualizar los campos del output
    update_data = output_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(output, key, value)
    
    # Si se cambió la cantidad, actualizar el input
    if output_data.quantity_output is not None and output_data.quantity_output != original_quantity:
        # Recalcular la cantidad tomada total
        new_total_taken = db.query(func.sum(Output.quantity_output)).filter(
            Output.input_id == output.input_id
        ).scalar() or 0
        
        # Actualizar input
        input_obj.quantity_taken = new_total_taken
        input_obj.total = input_obj.quantity_received - input_obj.quantity_taken
        
        # Actualizar el estado del input según la cantidad tomada
        if input_obj.quantity_taken >= input_obj.quantity_received:
            input_obj.status_id = InputStatus.completed
        elif input_obj.quantity_taken > 0:
            input_obj.status_id = InputStatus.processing
        else:
            input_obj.status_id = InputStatus.pending
    
    # Guardar cambios
    db.commit()
    db.refresh(output)
    
    logger.info(f"Output {output_id} actualizado por el usuario {user_id}")
    return output

def delete_output(db: Session, output_id: int, user_id: int, current_user: Optional[User] = None) -> bool:
    """
    Elimina un output y actualiza la cantidad tomada del input asociado.
    """
    # Obtener el output
    output = get_output(db, output_id, current_user)
    if not output:
        return False
    
    # Obtener el input asociado
    input_obj = db.query(Input).filter(Input.id == output.input_id).first()
    
    # Verificar que el input pertenezca al usuario (salvo que sea admin)
    if current_user and not role_service.is_admin(current_user) and input_obj and input_obj.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar este output"
        )
    
    # Guardar la cantidad del output a eliminar
    deleted_quantity = output.quantity_output
    
    # Eliminar el output
    db.delete(output)
    
    # Recalcular la cantidad tomada total (ahora sin el output eliminado)
    new_total_taken = db.query(func.sum(Output.quantity_output)).filter(
        Output.input_id == input_obj.id
    ).scalar() or 0
    
    # Actualizar input
    input_obj.quantity_taken = new_total_taken
    input_obj.total = input_obj.quantity_received - input_obj.quantity_taken
    
    # Actualizar el estado del input según la cantidad tomada
    if input_obj.quantity_taken >= input_obj.quantity_received:
        input_obj.status_id = InputStatus.completed
    elif input_obj.quantity_taken > 0:
        input_obj.status_id = InputStatus.processing
    else:
        input_obj.status_id = InputStatus.pending
    
    # Guardar cambios
    db.commit()
    
    logger.info(f"Output {output_id} eliminado por el usuario {user_id}")
    return True 