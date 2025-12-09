from sqlalchemy.orm import Session
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation, getcontext
from app.models.input_output import Input, InputStatus, Output
from app.models.bull import Bull, Race
from app.models.user import User
from app.schemas.input_output_schema import InputCreate, InputUpdate, OutputCreate
from app.services import role_service
from fastapi import HTTPException, status
from typing import List, Optional, Dict, Any, Tuple
import logging
from datetime import datetime, date
from sqlalchemy import and_, or_, func, between, cast, String
from sqlalchemy.orm import joinedload

# Configurar logger
logger = logging.getLogger(__name__)

def get_input(db: Session, input_id: int, current_user: Optional[User] = None) -> Optional[Input]:
    """
    Obtiene un input por su ID.
    Si se proporciona un usuario y no es administrador, verifica que le pertenezca.
    """
    input_obj = db.query(Input).filter(Input.id == input_id).first()
    
    # Si se proporciona un usuario y no es administrador, verificar que le pertenezca
    if current_user and not role_service.is_admin(current_user) and input_obj and input_obj.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver este input"
        )
    
    return input_obj

def get_inputs(db: Session, current_user: Optional[User] = None, skip: int = 0, limit: int = 100) -> List[Input]:
    """
    Obtiene una lista de inputs.
    Si se proporciona un usuario y no es administrador, filtra por sus inputs.
    """
    query = db.query(Input)
    
    # Si hay un usuario y no es administrador, filtrar por sus inputs
    if current_user and not role_service.is_admin(current_user):
        query = query.filter(Input.user_id == current_user.id)
    
    return query.offset(skip).limit(limit).all()

def get_inputs_by_user(db: Session, user_id: int, current_user: Optional[User] = None, skip: int = 0, limit: int = 100) -> Tuple[List[Input], int]:
    """
    Obtiene los inputs de un usuario específico incluyendo información detallada del toro.
    Si se proporciona un usuario y no es administrador, verifica que sea el mismo usuario.
    """
    if limit is None or limit <= 0:
        limit = 1

    # Si hay un usuario y no es administrador, verificar que sea el mismo usuario
    if current_user and not role_service.is_admin(current_user) and current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver los inputs de este usuario"
        )

    query = db.query(Input).filter(Input.user_id == user_id).options(
        joinedload(Input.bull).joinedload(Bull.race)
    )

    total = query.count()

    inputs = query.order_by(Input.fv.desc(), Input.created_at.desc()).offset(skip).limit(limit).all()

    return inputs, total

def get_inputs_by_bull(db: Session, bull_id: int, current_user: Optional[User] = None, search_query: Optional[str] = None, skip: int = 0, limit: int = 100) -> List[Input]:
    """
    Obtiene los inputs de un toro específico.
    Si se proporciona un usuario y no es administrador, verifica que el toro le pertenezca.
    
    Args:
        db: Sesión de la base de datos
        bull_id: ID del toro
        current_user: Usuario actual para verificación de permisos
        search_query: Término de búsqueda para filtrar por lote, escalarilla u otros campos
        skip: Número de registros a omitir (paginación)
        limit: Número máximo de registros a devolver (paginación)
    
    Returns:
        Lista de inputs del toro filtrados según el parámetro search_query
    """
    # Verificar que el toro exista
    bull = db.query(Bull).filter(Bull.id == bull_id).first()
    if not bull:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Toro no encontrado"
        )
    
    # Si hay un usuario y no es administrador, verificar que el toro le pertenezca
    if current_user and not role_service.is_admin(current_user) and bull.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para ver los inputs de este toro"
        )
    
    # Consulta base filtrada por bull_id
    query = db.query(Input).filter(Input.bull_id == bull_id)
    
    # Aplicar filtro de búsqueda si se proporciona
    if search_query:
        search_term = f"%{search_query.lower()}%"
        query = query.filter(
            or_(
                func.lower(Input.lote).like(search_term),
                func.lower(Input.escalarilla).like(search_term),
                func.lower(cast(Input.quantity_received, String)).like(search_term),
                func.lower(cast(Input.quantity_taken, String)).like(search_term),
                func.lower(cast(Input.total, String)).like(search_term),
                func.lower(cast(Input.id, String)).like(search_term)
            )
        )
    
    return query.offset(skip).limit(limit).all()

def filter_inputs(db: Session, search_query: Optional[str] = None, date_from: Optional[datetime] = None, date_to: Optional[datetime] = None, status: Optional[str] = None, user_id: Optional[int] = None, current_user: Optional[User] = None, skip: int = 0, limit: int = 100) -> List[Dict[str, Any]]:
    """
    Filtra inputs usando un solo parámetro de búsqueda que puede ser número de documento, 
    nombre de usuario, nombre del toro o número de registro.
    También permite filtrar por rango de fechas y estado.
    
    Args:
        db: Sesión de la base de datos
        search_query: Término de búsqueda general
        date_from: Fecha inicial para filtrar
        date_to: Fecha final para filtrar
        status: Estado del input (pending, processing, completed, cancelled)
        user_id: ID del usuario para filtrar
        current_user: Usuario actual
        skip: Número de registros a saltar
        limit: Número máximo de registros a devolver
    
    Retorna una lista de diccionarios con la información completa:
    - Nombre del toro
    - Raza del toro
    - Nombre del cliente
    - Número de registro del toro
    - Documento del cliente
    - Datos del input
    """
    # Consulta base con joins necesarios para obtener todos los datos requeridos
    query = db.query(
        Input,
        Bull.name.label('bull_name'),
        Bull.registration_number.label('register_number'),
        Race.name.label('race_name'),
        User.full_name.label('client_name'),
        User.number_document.label('client_document')
    ).join(
        Bull, Input.bull_id == Bull.id
    ).join(
        User, Input.user_id == User.id
    ).join(
        Race, Bull.race_id == Race.id
    )
    
    # Aplicar filtro por usuario específico
    if user_id is not None:
        query = query.filter(Input.user_id == user_id)
    # Si hay un usuario y no es administrador, filtrar por sus inputs
    elif current_user and not role_service.is_admin(current_user):
        query = query.filter(Input.user_id == current_user.id)
    
    # Aplicar búsqueda general si se proporciona
    if search_query:
        # Convertir a minúsculas para búsqueda insensible a mayúsculas/minúsculas
        search_term = f"%{search_query.lower()}%"
        
        # Buscar en todos los campos relevantes usando LOWER() para comparación insensible a mayúsculas
        query = query.filter(
            or_(
                func.lower(User.number_document).like(search_term),
                func.lower(User.full_name).like(search_term),
                func.lower(Bull.name).like(search_term),
                func.lower(cast(Bull.registration_number, String)).like(search_term)
            )
        )
    
    # Aplicar filtro de rango de fechas
    if date_from and date_to:
        query = query.filter(Input.fv.between(date_from, date_to))
    elif date_from:
        query = query.filter(Input.fv >= date_from)
    elif date_to:
        query = query.filter(Input.fv <= date_to)
    
    # Aplicar filtro por estado si se proporciona
    if status:
        # Convertir el estado a la enumeración correcta
        try:
            model_status = None
            status_lower = status.lower()
            
            if status_lower == "pending":
                model_status = InputStatus.pending
            elif status_lower == "processing":
                model_status = InputStatus.processing
            elif status_lower == "completed":
                model_status = InputStatus.completed
            elif status_lower == "cancelled":
                model_status = InputStatus.cancelled
            
            if model_status:
                query = query.filter(Input.status_id == model_status)
        except Exception as e:
            logger.error(f"Error al filtrar por estado: {str(e)}")
            # Si hay un error con el estado, ignoramos este filtro
            pass
    
    # Ordenar y aplicar paginación
    query = query.order_by(Input.created_at.desc()).offset(skip).limit(limit)
    
    # Ejecutar consulta
    results = query.all()
    
    # Formatear resultados
    formatted_results = []
    for result in results:
        input_obj = result[0]
        formatted_results.append({
            "input_id": input_obj.id,
            "quantity_received": input_obj.quantity_received,
            "escalarilla": input_obj.escalarilla,
            "status_id": input_obj.status_id.value,
            "lote": input_obj.lote,
            "fv": input_obj.fv,
            "quantity_taken": input_obj.quantity_taken,
            "total": input_obj.total,
            "created_at": input_obj.created_at,
            "bull_name": result.bull_name,
            "register_number": result.register_number,
            "race_name": result.race_name,
            "client_name": result.client_name,
            "client_document": result.client_document
        })
    
    return formatted_results

def create_input(db: Session, input_data: InputCreate, user_id: int, current_user: Optional[User] = None) -> Input:
    """
    Crea un nuevo input para un toro.
    Si el usuario actual es admin, puede crear inputs para cualquier usuario.
    Si no es admin, solo puede crear inputs para sí mismo.
    
    Args:
        db: Sesión de la base de datos
        input_data: Datos del input a crear
        user_id: ID del usuario al que se asignará el input (cliente seleccionado)
        current_user: Usuario que realiza la acción
    """
    # Verificar que el usuario al que se asignará el input exista
    target_user = db.query(User).filter(User.id == user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    # Verificar que el toro exista y pertenezca al usuario especificado
    bull = db.query(Bull).filter(Bull.id == input_data.bull_id).first()
    if not bull:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Toro no encontrado"
        )
    
    # Verificar que el toro pertenezca al usuario especificado
    if bull.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El toro no pertenece al usuario especificado"
        )
    
    # Si el usuario actual no es admin, solo puede crear inputs para sí mismo
    if current_user and not role_service.is_admin(current_user) and user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para crear inputs para otros usuarios"
        )
    
    # Verificar que quantity_taken no exceda quantity_received
    if input_data.quantity_taken > input_data.quantity_received:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La cantidad tomada ({input_data.quantity_taken}) no puede ser mayor que la cantidad recibida ({input_data.quantity_received})"
        )
    
    # Calcular el total (quantity_received - quantity_taken)
    total = input_data.quantity_received - input_data.quantity_taken
    
    # Establecer valores predeterminados para campos opcionales
    escalarilla = input_data.escalarilla or "Sin asignar"
    lote = input_data.lote or "Sin asignar"
    fv = input_data.fv or datetime.now()
    
    try:
        # Crear el input
        db_input = Input(
            quantity_received=input_data.quantity_received,
            escalarilla=escalarilla,
            bull_id=input_data.bull_id,
            status_id=InputStatus.pending,  # Por defecto es pendiente
            lote=lote,
            fv=fv,
            quantity_taken=input_data.quantity_taken,
            total=total,
            user_id=user_id  # Asignar al usuario especificado
        )
        
        # Guardar en la base de datos
        db.add(db_input)
        db.commit()
        db.refresh(db_input)
        
        logger.info(f"Input creado para el toro {input_data.bull_id} asignado al usuario {user_id}")
        return db_input
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error al crear input: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el input: {str(e)}"
        )

# Configurar precisión decimal
getcontext().prec = 10  # Suficiente para manejar ml con precisión

logger = logging.getLogger(__name__)

def is_approximately_equal(a: float, b: float, tolerance: float = 1e-6) -> bool:
    """Compara dos floats con una tolerancia para evitar errores de redondeo"""
    return abs(a - b) <= tolerance

def safe_decimal(value: float) -> Decimal:
    """Convierte un float a Decimal de manera segura evitando errores de precisión"""
    return Decimal(str(value))

# def update_input(db: Session, input_id: int, input_data: InputUpdate, user_id: int, 
#                 current_user: Optional[User] = None) -> Optional[Input]:
#     """
#     Actualiza un input existente con manejo seguro de decimales.
    
#     Args:
#         db: Sesión de base de datos
#         input_id: ID del input a actualizar
#         input_data: Datos de actualización
#         user_id: ID del usuario que realiza la actualización
#         current_user: Usuario actual (para verificación de permisos)
    
#     Returns:
#         El input actualizado o None si no se encontró
    
#     Raises:
#         HTTPException: Si hay problemas de permisos o validación
#     """
#     # Obtener el input
#     db_input = get_input(db, input_id, current_user)
#     if not db_input:
#         return None
    
#     # Verificar permisos
#     if current_user and not role_service.is_admin(current_user) and db_input.user_id != user_id:
#         raise HTTPException(
#             status_code=status.HTTP_403_FORBIDDEN,
#             detail="No tienes permiso para actualizar este input"
#         )
    
#     # Preparar datos de actualización
#     update_data = input_data.dict(exclude_unset=True, exclude={"status_id"})
    
#     # Manejo especial para cantidades con decimales
#     if "quantity_received" in update_data or "quantity_taken" in update_data:
#         try:
#             # Convertir a Decimal para cálculos precisos
#             quantity_received = safe_decimal(
#                 update_data.get("quantity_received", db_input.quantity_received)
#             )
#             quantity_taken = safe_decimal(
#                 update_data.get("quantity_taken", db_input.quantity_taken)
#             )
            
#             # Verificar outputs existentes
#             outputs_total = Decimal(str(db.query(func.sum(Output.quantity_output)))
#                                 .filter(Output.input_id == input_id)
#                                 .scalar() or 0.0)
            
#             # Validación 1: No permitir que lo tomado exceda lo recibido
#             if quantity_taken > quantity_received and not is_approximately_equal(
#                 float(quantity_taken), float(quantity_received)):
#                 raise HTTPException(
#                     status_code=status.HTTP_400_BAD_REQUEST,
#                     detail=f"La cantidad tomada ({float(quantity_taken):.2f}) no puede ser mayor que la recibida ({float(quantity_received):.2f})"
#                 )
            
#             # Validación 2: Si hay outputs, no permitir reducir cantidad recibida
#             if outputs_total > 0:
#                 if quantity_received < outputs_total and not is_approximately_equal(
#                     float(quantity_received), float(outputs_total)):
#                     raise HTTPException(
#                         status_code=status.HTTP_400_BAD_REQUEST,
#                         detail=f"No se puede reducir la cantidad recibida ({float(quantity_received):.2f}) "
#                               f"por debajo de las salidas registradas ({float(outputs_total):.2f})"
#                     )
                
#                 # Si hay outputs, usar esa cantidad como quantity_taken
#                 quantity_taken = outputs_total
            
#             # Calcular total disponible con precisión decimal
#             total_available = quantity_received - quantity_taken
            
#             # Actualizar datos con valores convertidos a float para la base de datos
#             update_data.update({
#                 "quantity_received": float(quantity_received),
#                 "quantity_taken": float(quantity_taken),
#                 "total": float(total_available)
#             })
            
#         except Exception as e:
#             logger.error(f"Error en cálculo de decimales: {str(e)}")
#             raise HTTPException(
#                 status_code=status.HTTP_400_BAD_REQUEST,
#                 detail="Error en los cálculos de cantidad. Verifique los valores."
#             )
    
#     # Aplicar actualizaciones
#     for key, value in update_data.items():
#         setattr(db_input, key, value)
    
#     # Manejar estado si está presente
#     if input_data.status_id is not None:
#         _update_input_status(db_input, input_data.status_id)
    
#     # Confirmar cambios
#     try:
#         db.commit()
#         db.refresh(db_input)
#         logger.info(f"Input {input_id} actualizado correctamente por usuario {user_id}")
#         return db_input
#     except Exception as e:
#         db.rollback()
#         logger.error(f"Error al guardar input {input_id}: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail="Error al guardar los cambios en la base de datos"
#         )

def to_decimal(val) -> Decimal:
    try:
        return Decimal(str(val)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError) as e:
        logger.error(f"Error al convertir a Decimal: {val} - {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Valor inválido para cantidad decimal."
        )

def is_approximately_equal(a: Decimal, b: Decimal, tolerance: Decimal = Decimal("0.0001")) -> bool:
    return abs(a - b) < tolerance

def update_input(
    db: Session,
    input_id: int,
    input_data,
    user_id: int,
    current_user: Optional["User"] = None
) -> Optional["Input"]:
    db_input = get_input(db, input_id, current_user)
    if not db_input:
        return None

    if current_user and not role_service.is_admin(current_user) and db_input.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para actualizar este input"
        )

    update_data = input_data.dict(exclude_unset=True, exclude={"status_id"})

    if "quantity_received" in update_data or "quantity_taken" in update_data:
        try:
            quantity_received = to_decimal(update_data.get("quantity_received", db_input.quantity_received))
            quantity_taken = to_decimal(update_data.get("quantity_taken", db_input.quantity_taken))

            outputs_raw = db.query(func.sum(Output.quantity_output)).filter(Output.input_id == input_id).scalar()
            outputs_total = to_decimal(outputs_raw or 0)

            if quantity_taken > quantity_received and not is_approximately_equal(quantity_taken, quantity_received):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"La cantidad tomada ({quantity_taken}) no puede ser mayor que la recibida ({quantity_received})"
                )

            if outputs_total > 0 and quantity_received < outputs_total and not is_approximately_equal(quantity_received, outputs_total):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"La cantidad de salida ({outputs_total}) excede la cantidad disponible ({quantity_received})"
                )

            if outputs_total > 0:
                quantity_taken = outputs_total

            total_available = (quantity_received - quantity_taken).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            update_data.update({
                "quantity_received": quantity_received,
                "quantity_taken": quantity_taken,
                "total": total_available
            })

        except HTTPException:
            raise
        except Exception as e:
            logger.exception("Error en los cálculos de cantidad")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Error en los cálculos de cantidad. Verifique los valores."
            )

    for key, value in update_data.items():
        setattr(db_input, key, value)

    if input_data.status_id is not None:
        _update_input_status(db_input, input_data.status_id)

    try:
        db.commit()
        db.refresh(db_input)
        logger.info(f"Input {input_id} actualizado correctamente por usuario {user_id}")
        return db_input
    except Exception as e:
        db.rollback()
        logger.error(f"Error al guardar input {input_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al guardar los cambios en la base de datos"
        )

def _update_input_status(db_input: Input, new_status_id: int):
    status_mapping = {
        1: InputStatus.pending,
        2: InputStatus.processing,
        3: InputStatus.completed,
        4: InputStatus.cancelled
    }

    if new_status_id in status_mapping:
        db_input.status_id = status_mapping[new_status_id]
    else:
        logger.warning(f"Intento de asignar estado inválido: {new_status_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado de input no válido"
        )

def _update_input_status(db_input: Input, new_status_id: int):
    """Actualiza el estado del input convirtiendo entre esquema y modelo"""
    status_mapping = {
        1: InputStatus.pending,    # pending
        2: InputStatus.processing, # processing
        3: InputStatus.completed,  # completed
        4: InputStatus.cancelled   # cancelled
    }
    
    if new_status_id in status_mapping:
        db_input.status_id = status_mapping[new_status_id]
    else:
        logger.warning(f"Intento de asignar estado inválido: {new_status_id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Estado de input no válido"
        )

def get_input(db: Session, input_id: int, current_user: Optional[User] = None) -> Optional[Input]:
    """Obtiene un input con verificación básica de permisos"""
    input = db.query(Input).filter(Input.id == input_id).first()
    
    if input and current_user and not role_service.is_admin(current_user) and input.user_id != current_user.id:
        return None
    
    return input
def delete_input(db: Session, input_id: int, user_id: int, current_user: Optional[User] = None) -> bool:
    """
    Elimina un input.
    Verifica que el input pertenezca al usuario que lo elimina.
    """
    # Obtener el input
    db_input = get_input(db, input_id, current_user)
    if not db_input:
        return False
    
    # Verificar que el input pertenezca al usuario (salvo que sea admin)
    if current_user and not role_service.is_admin(current_user) and db_input.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar este input"
        )
    
    # Eliminar el input
    db.delete(db_input)
    db.commit()
    
    logger.info(f"Input {input_id} eliminado por el usuario {user_id}")
    return True

def change_input_status(db: Session, input_id: int, status: InputStatus, user_id: int, current_user: Optional[User] = None) -> Optional[Input]:
    """
    Cambia el estado de un input.
    Verifica que el input pertenezca al usuario que cambia el estado.
    """
    # Obtener el input
    db_input = get_input(db, input_id, current_user)
    if not db_input:
        return None
    
    # Verificar que el input pertenezca al usuario (salvo que sea admin)
    if current_user and not role_service.is_admin(current_user) and db_input.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para cambiar el estado de este input"
        )
    
    # Convertir el estado del esquema al estado del modelo
    model_status = None
    
    from app.schemas.input_output_schema import InputStatus as SchemaInputStatus
    if status == SchemaInputStatus.pending:
        model_status = InputStatus.pending
    elif status == SchemaInputStatus.processing:
        model_status = InputStatus.processing
    elif status == SchemaInputStatus.completed:
        model_status = InputStatus.completed
    elif status == SchemaInputStatus.cancelled:
        model_status = InputStatus.cancelled
    
    if not model_status:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Estado no válido: {status}"
        )
    
    # Cambiar el estado
    db_input.status_id = model_status
    db.commit()
    db.refresh(db_input)
    
    logger.info(f"Estado del input {input_id} cambiado a {status} por el usuario {user_id}")
    return db_input

def add_output_to_input(db: Session, input_id: int, output_data: OutputCreate, user_id: int, current_user: Optional[User] = None) -> Output:
    """
    Añade un output a un input existente.
    Verifica que el input pertenezca al usuario que añade el output.
    Esta función está deprecada, usar output_service.create_output en su lugar.
    """
    from app.services import output_service
    return output_service.create_output(db, input_id, output_data, user_id, current_user)

def create_input_for_bull(
    db: Session,
    bull_id: int,
    input_data: InputCreate,
    current_user: User
) -> Input:
    """
    Crea una nueva entrada/muestra para un toro específico.
    Solo administradores y veterinarios pueden usar este servicio.
    
    Args:
        db: Sesión de la base de datos
        bull_id: ID del toro al que se le agregará la entrada
        input_data: Datos de la entrada a crear
        current_user: Usuario que realiza la acción (debe ser admin o veterinario)
    
    Returns:
        Input: La entrada creada
        
    Raises:
        HTTPException: Si el usuario no tiene permisos o hay problemas con los datos
    """
    # Verificar que el usuario sea administrador o veterinario
    is_admin = role_service.is_admin(current_user)
    is_vet = any(role.name == "Veterinarian" for role in current_user.roles)
    
    if not (is_admin or is_vet):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores y veterinarios pueden crear entradas para toros"
        )
    
    # Verificar que el toro exista
    bull = db.query(Bull).filter(Bull.id == bull_id).first()
    if not bull:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Toro no encontrado"
        )
    
    # Verificar que quantity_taken no exceda quantity_received
    if input_data.quantity_taken > input_data.quantity_received:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"La cantidad tomada ({input_data.quantity_taken}) no puede ser mayor que la cantidad recibida ({input_data.quantity_received})"
        )
    
    # Calcular el total (quantity_received - quantity_taken)
    total = input_data.quantity_received - input_data.quantity_taken
    
    # Establecer valores predeterminados para campos opcionales
    escalarilla = input_data.escalarilla or "Sin asignar"
    lote = input_data.lote or "Sin asignar"
    fv = input_data.fv or datetime.now()
    
    try:
        # Crear la entrada
        db_input = Input(
            quantity_received=input_data.quantity_received,
            escalarilla=escalarilla,
            bull_id=bull_id,
            status_id=InputStatus.pending,  # Por defecto es pendiente
            lote=lote,
            fv=fv,
            quantity_taken=input_data.quantity_taken,
            total=total,
            user_id=bull.user_id  # Usar el ID del dueño del toro
        )
        
        # Guardar en la base de datos
        db.add(db_input)
        db.commit()
        db.refresh(db_input)
        
        # Registrar la acción
        logger.info(
            f"Entrada creada para el toro {bull_id} por el usuario {current_user.id} "
            f"({'admin' if is_admin else 'veterinario'})"
        )
        
        return db_input
        
    except Exception as e:
        db.rollback()
        logger.error(f"Error al crear entrada para el toro {bull_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear la entrada: {str(e)}"
        ) 