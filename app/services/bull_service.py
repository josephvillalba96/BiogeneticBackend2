from sqlalchemy.orm import Session, joinedload
from app.models.bull import Bull
from app.schemas.bull_schema import BullCreate, BullUpdate, BullStatus
from app.models.user import User, Role
from app.models.bull import Race, Sex
from app.services import role_service
from typing import List, Optional, Dict, Any
from sqlalchemy import or_, func, and_
from fastapi import HTTPException, status
from datetime import datetime
import logging
from app.models.input_output import Input

def get_bull(db: Session, bull_id: int, current_user: User = None) -> Optional[Bull]:
    """Obtiene un toro por su ID"""
    bull = db.query(Bull).filter(Bull.id == bull_id).first()
    
    # Si se proporciona un usuario y no es administrador, verificar que le pertenezca
    # if current_user and not role_service.is_admin(current_user) and bull and bull.user_id != current_user.id:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="No tienes permiso para ver este toro"
    #     )
    
    return bull

def get_bull_by_register(db: Session, register: str) -> Optional[Bull]:
    """Obtiene un toro por su número de registro"""
    return db.query(Bull).filter(Bull.registration_number == register).first()

def get_bulls(
    db: Session, 
    current_user: User = None, 
    search_query: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    skip: int = 0, 
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Obtiene una lista de toros con información detallada, incluyendo datos del usuario que los registró.
    
    Parámetros:
    - current_user: Usuario actual para filtrado de permisos
    - search_query: Búsqueda general (toro, registro, documento o nombre del cliente)
    - date_from: Fecha de inicio para filtrar por fecha de creación
    - date_to: Fecha fin para filtrar por fecha de creación
    - skip: Número de registros a omitir (paginación)
    - limit: Número máximo de registros a devolver (paginación)
    
    Retorna una lista de diccionarios con toda la información de toros y usuarios.
    """
    # Consulta base con joins para incluir información del usuario, raza y sexo
    query = db.query(
        Bull,
        User.id.label('user_id'),
        User.full_name.label('user_full_name'),
        User.email.label('user_email'),
        User.number_document.label('user_document'),
        User.phone.label('user_phone'),
        User.type_document.label('user_type_document'),
        User.specialty.label('user_specialty')
    ).options(
        joinedload(Bull.race),
        joinedload(Bull.sex),
        joinedload(Bull.user)
    ).join(
        User, Bull.user_id == User.id
    )
    
    # Si hay un usuario y no es administrador, filtrar por sus toros
    if current_user and not role_service.is_admin(current_user):
        query = query.filter(Bull.user_id == current_user.id)
    
    # Aplicar filtro de búsqueda general
    if search_query:
        search_term = f"%{search_query.lower()}%"
        query = query.filter(
            or_(
                func.lower(Bull.name).like(search_term),
                func.lower(Bull.registration_number).like(search_term),
                func.lower(User.number_document).like(search_term),
                func.lower(User.full_name).like(search_term)
            )
        )
    
    # Aplicar filtro de fecha
    if date_from and date_to:
        query = query.filter(Bull.created_at.between(date_from, date_to))
    elif date_from:
        query = query.filter(Bull.created_at >= date_from)
    elif date_to:
        query = query.filter(Bull.created_at <= date_to)
    
    # Aplicar paginación
    query = query.order_by(Bull.created_at.desc()).offset(skip).limit(limit)
    
    # Ejecutar consulta
    results = query.all()
    
    # Formatear resultados
    bulls_data = []
    for row in results:
        try:
            bull = row[0]  # Obtener el objeto Bull de la primera columna
            
            # Obtener raza y sexo con manejo seguro de errores
            race_name = None
            sex_name = None
            try:
                race_name = bull.race.name if bull.race else None
            except Exception as e:
                logging.error(f"Error al obtener la raza del toro {bull.id}: {str(e)}")
            
            try:
                sex_name = bull.sex.name if bull.sex else None
            except Exception as e:
                logging.error(f"Error al obtener el sexo del toro {bull.id}: {str(e)}")
            
            # Crear diccionario con todos los datos
            bull_data = {
                "id": bull.id,
                "name": bull.name,
                "registration_number": bull.registration_number,
                "lote":bull.lote,
                "escalerilla":bull.escalerilla,
                "description":bull.description,
                "race_id": bull.race_id,
                "race_name": race_name,
                "sex_id": bull.sex_id,
                "sex_name": sex_name,
                "status": bull.status.value if bull.status else None,
                "created_at": bull.created_at,
                "updated_at": bull.updated_at,
                "user": {
                    "id": row.user_id,
                    "full_name": row.user_full_name,
                    "email": row.user_email,
                    "number_document": row.user_document,
                    "phone": row.user_phone,
                    "type_document": row.user_type_document.value if row.user_type_document else None,
                    "specialty": row.user_specialty
                }
            }
            
            bulls_data.append(bull_data)
        except Exception as e:
            logging.error(f"Error al procesar un toro en get_bulls: {str(e)}")
            # Continuar con el siguiente toro sin interrumpir el proceso
    
    return bulls_data

def get_bulls_by_race(db: Session, race_id: int, current_user: User = None, skip: int = 0, limit: int = 100) -> List[Bull]:
    """Obtiene toros por raza"""
    query = db.query(Bull).filter(Bull.race_id == race_id)
    
    # Si hay un usuario y no es administrador, filtrar por sus toros
    if current_user and not role_service.is_admin(current_user):
        query = query.filter(Bull.user_id == current_user.id)
    
    return query.offset(skip).limit(limit).all()

def get_bulls_by_sex(db: Session, sex_id: int, current_user: User = None, skip: int = 0, limit: int = 100) -> List[Bull]:
    """Obtiene toros por sexo"""
    query = db.query(Bull).filter(Bull.sex_id == sex_id)
    
    # Si hay un usuario y no es administrador, filtrar por sus toros
    if current_user and not role_service.is_admin(current_user):
        query = query.filter(Bull.user_id == current_user.id)
    
    return query.offset(skip).limit(limit).all()

def get_bulls_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Bull]:
    """Obtiene toros por usuario"""
    return db.query(Bull).filter(Bull.user_id == user_id).offset(skip).limit(limit).all()

def create_bull(db: Session, bull: BullCreate, current_user: User) -> Bull:
    """Crea un nuevo toro"""
    # Verificar si el registro ya existe (solo si se proporciona un número de registro)
    # if bull.registration_number:
    #     existing_bull = get_bull_by_register(db, bull.registration_number)
    #     if existing_bull:
    #         raise HTTPException(
    #             status_code=status.HTTP_400_BAD_REQUEST,
    #             detail="El número de registro ya existe"
    #         )
    
    # Convertir el estado del esquema al estado del modelo
    from app.models.bull import BullStatus as ModelBullStatus
    if bull.status == ModelBullStatus.active or bull.status == "active":
        model_status = ModelBullStatus.active
    elif bull.status == ModelBullStatus.inactive or bull.status == "inactive":
        model_status = ModelBullStatus.inactive
    else:
        model_status = ModelBullStatus.active
    
    # Crear el nuevo toro con el usuario autenticado
    db_bull = Bull(
        name=bull.name,
        registration_number=bull.registration_number,
        race_id=bull.race_id,
        sex_id=bull.sex_id,
        status=model_status,
        lote=bull.lote,
        escalerilla=bull.escalerilla,
        description=bull.description,
        user_id=current_user.id  # Usar el ID del usuario autenticado
    )
    
    # Guardar en la base de datos
    db.add(db_bull)
    db.commit()
    db.refresh(db_bull)
    return db_bull

def update_bull(db: Session, bull_id: int, bull: BullUpdate, current_user: User) -> Optional[Bull]:
    """Actualiza un toro existente"""
    # Obtener el toro
    db_bull = get_bull(db, bull_id)
    if not db_bull:
        return None

    # Verificar que el toro pertenezca al usuario actual o sea administrador
    if db_bull.user_id != current_user.id and not role_service.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para modificar este toro"
        )

    # Actualizar los campos
    update_data = bull.dict(exclude_unset=True, exclude={"status"}, by_alias=False)

    # Manejar específicamente el campo registration_number
    if "registration_number" in update_data:
        update_data["registration_number"] = update_data.pop("registration_number")

    # Actualizar los campos básicos
    for key, value in update_data.items():
        setattr(db_bull, key, value)

    # Manejar específicamente el campo status
    if bull.status is not None:
        # Convertir el estado del esquema al estado del modelo
        from app.models.bull import BullStatus as ModelBullStatus
        if bull.status == BullStatus.active:
            db_bull.status = ModelBullStatus.active
        elif bull.status == BullStatus.inactive:
            db_bull.status = ModelBullStatus.inactive

    # Guardar los cambios
    db.commit()
    db.refresh(db_bull)
    return db_bull

def delete_bull(db: Session, bull_id: int, current_user: User) -> bool:
    """Elimina un toro"""
    db_bull = get_bull(db, bull_id)
    if not db_bull:
        return False
        
    # Verificar que el toro pertenezca al usuario actual o sea administrador
    if db_bull.user_id != current_user.id and not role_service.is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar este toro"
        )
    
    db.delete(db_bull)
    db.commit()
    return True

def filter_bulls(
    db: Session, 
    current_user: User = None, 
    search_query: Optional[str] = None,
    name: Optional[str] = None,
    register: Optional[str] = None,
    race_id: Optional[int] = None,
    sex_id: Optional[int] = None,
    status: Optional[BullStatus] = None,
    skip: int = 0, 
    limit: int = 100
) -> List[Bull]:
    """
    Filtra toros por diversos criterios y respeta los permisos del usuario.
    
    Si el usuario es administrador, puede ver todos los toros.
    Si el usuario es un usuario normal, solo puede ver sus propios toros.
    
    Parámetros de filtrado:
    - search_query: Búsqueda general en nombre del toro, número de documento o nombre del propietario
    - name: Filtrar por nombre del toro (coincidencia parcial)
    - register: Filtrar por número de registro del toro (coincidencia parcial)
    - race_id: Filtrar por ID de raza
    - sex_id: Filtrar por ID de sexo
    - status: Filtrar por estado del toro
    """
    # Consulta base que incluye información del usuario
    query = db.query(Bull).options(joinedload(Bull.user), joinedload(Bull.race), joinedload(Bull.sex))
    
    # Si hay un usuario y no es administrador, filtrar por sus toros
    if current_user and not role_service.is_admin(current_user):
        query = query.filter(Bull.user_id == current_user.id)
    
    # Aplicar filtro de búsqueda general
    if search_query:
        # Convertir a minúsculas para búsqueda insensible a mayúsculas/minúsculas
        search_term = f"%{search_query.lower()}%"
        
        # Unirse a la tabla User para poder buscar en sus campos
        query = query.join(User, Bull.user_id == User.id)
        
        # Buscar en todos los campos relevantes usando LOWER() para comparación insensible a mayúsculas
        query = query.filter(
            or_(
                func.lower(Bull.name).like(search_term),
                func.lower(Bull.registration_number).like(search_term),
                func.lower(User.number_document).like(search_term),
                func.lower(User.full_name).like(search_term)
            )
        )
    
    # Filtrar por nombre específico si se proporciona
    if name:
        name_term = f"%{name.lower()}%"
        query = query.filter(func.lower(Bull.name).like(name_term))
    
    # Filtrar por número de registro específico si se proporciona
    if register:
        register_term = f"%{register.lower()}%"
        query = query.filter(func.lower(Bull.registration_number).like(register_term))
    
    # Aplicar filtros específicos si se proporcionan
    if race_id is not None:
        query = query.filter(Bull.race_id == race_id)
    
    if sex_id is not None:
        query = query.filter(Bull.sex_id == sex_id)
    
    if status is not None:
        # Convertir el estado del esquema al estado del modelo
        from app.models.bull import BullStatus as ModelBullStatus
        model_status = None
        
        if status == BullStatus.active:
            model_status = ModelBullStatus.active
        elif status == BullStatus.inactive:
            model_status = ModelBullStatus.inactive
        
        if model_status:
            query = query.filter(Bull.status == model_status)
    
    # Aplicar paginación
    query = query.offset(skip).limit(limit)
    
    # Ejecutar consulta
    return query.all()

def create_bull_for_client(
    db: Session, 
    bull: BullCreate, 
    client_id: int,
    current_user: User
) -> Bull:
    """
    Crea un nuevo toro para un cliente específico.
    Solo administradores y veterinarios pueden usar este servicio.
    
    Args:
        db: Sesión de la base de datos
        bull: Datos del toro a crear
        client_id: ID del cliente para quien se crea el toro
        current_user: Usuario que realiza la acción (debe ser admin o veterinario)
    
    Returns:
        Bull: El toro creado
        
    Raises:
        HTTPException: Si el usuario no tiene permisos o hay problemas con los datos
    """
    # Verificar que el usuario sea administrador o veterinario
    is_admin = role_service.is_admin(current_user)
    is_vet = any(role.name == "Veterinarian" for role in current_user.roles)
    
    if not (is_admin or is_vet):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores y veterinarios pueden crear toros para clientes"
        )
    
    # Verificar que el cliente exista
    client = db.query(User).filter(User.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )
    
    # Verificar que el usuario sea realmente un cliente
    is_client = any(role.name == "Client" for role in client.roles)
    if not is_client:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El usuario especificado no es un cliente"
        )
    
    # Convertir el estado del esquema al estado del modelo
    from app.models.bull import BullStatus as ModelBullStatus
    if bull.status == ModelBullStatus.active or bull.status == "active":
        model_status = ModelBullStatus.active
    elif bull.status == ModelBullStatus.inactive or bull.status == "inactive":
        model_status = ModelBullStatus.inactive
    else:
        model_status = ModelBullStatus.active
    
    # Crear el nuevo toro para el cliente
    db_bull = Bull(
        name=bull.name,
        registration_number=bull.registration_number,
        race_id=bull.race_id,
        sex_id=bull.sex_id,
        status=model_status,
        lote=bull.lote,
        escalerilla=bull.escalerilla,
        description=bull.description,
        user_id=client_id  # Usar el ID del cliente
    )
    
    try:
        # Guardar en la base de datos
        db.add(db_bull)
        db.commit()
        db.refresh(db_bull)
        
        # Registrar la acción
        logger = logging.getLogger(__name__)
        logger.info(
            f"Toro creado para el cliente {client_id} por el usuario {current_user.id} "
            f"({'admin' if is_admin else 'veterinario'})"
        )
        
        return db_bull
        
    except Exception as e:
        db.rollback()
        logger = logging.getLogger(__name__)
        logger.error(f"Error al crear toro para cliente {client_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el toro: {str(e)}"
        )

def get_bulls_by_client(
    db: Session,
    client_id: int,
    current_user: Optional[User] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Obtiene todos los toros de un cliente específico con información detallada.
    
    Args:
        db: Sesión de la base de datos
        client_id: ID del cliente cuyos toros se quieren obtener
        current_user: Usuario actual para verificación de permisos
        skip: Número de registros a omitir (paginación)
        limit: Número máximo de registros a devolver (paginación)
    
    Returns:
        Lista de diccionarios con información detallada de los toros
        
    Raises:
        HTTPException: Si el usuario no tiene permisos o el cliente no existe
    """
    # Verificar que el cliente exista
    client = db.query(User).filter(User.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )
    
    # Si hay un usuario y no es administrador, verificar que sea el mismo cliente
    # if current_user and not role_service.is_admin(current_user):
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="No tienes permiso para ver los toros de este cliente"
    #     )
    
    # Consulta base con joins para incluir información de raza y sexo
    query = db.query(
        Bull,
        Race.name.label('race_name'),
        Sex.name.label('sex_name')
    ).options(
        joinedload(Bull.race),
        joinedload(Bull.sex)
    ).join(
        Race, Bull.race_id == Race.id, isouter=True
    ).join(
        Sex, Bull.sex_id == Sex.id, isouter=True
    ).filter(
        Bull.user_id == client_id
    )
    
    # Aplicar paginación
    query = query.order_by(Bull.created_at.desc()).offset(skip).limit(limit)
    
    # Ejecutar consulta
    results = query.all()
    
    # Formatear resultados
    bulls_data = []
    for row in results:
        try:
            bull = row[0]  # Obtener el objeto Bull
            
            # Crear diccionario con todos los datos
            bull_data = {
                "id": bull.id,
                "name": bull.name,
                "registration_number": bull.registration_number,
                "lote": bull.lote,
                "escalerilla": bull.escalerilla,
                "description": bull.description,
                "race_id": bull.race_id,
                "race_name": row.race_name,
                "sex_id": bull.sex_id,
                "sex_name": row.sex_name,
                "status": bull.status.value if bull.status else None,
                "created_at": bull.created_at,
                "updated_at": bull.updated_at
            }
            
            bulls_data.append(bull_data)
        except Exception as e:
            logging.error(f"Error al procesar toro en get_bulls_by_client: {str(e)}")
            # Continuar con el siguiente toro sin interrumpir el proceso
    
    return bulls_data

def get_bulls_with_available_samples(
    db: Session,
    client_id: int,
    current_user: Optional[User] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Obtiene los toros de un cliente que tienen muestras disponibles (entradas con cantidad total > 0).
    
    Args:
        db: Sesión de la base de datos
        client_id: ID del cliente cuyos toros se quieren obtener
        current_user: Usuario actual para verificación de permisos
        skip: Número de registros a omitir (paginación)
        limit: Número máximo de registros a devolver (paginación)
    
    Returns:
        Lista de diccionarios con información detallada de los toros y cantidad total disponible
        
    Raises:
        HTTPException: Si el usuario no tiene permisos o el cliente no existe
    """
    # Verificar que el cliente exista
    client = db.query(User).filter(User.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )
    
    # Si hay un usuario y no es administrador, verificar que sea el mismo cliente
    # if current_user and not role_service.is_admin(current_user) and current_user.id != client_id:
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="No tienes permiso para ver los toros de este cliente"
    #     )
    
    # Consulta que obtiene toros con información de entradas y calcula la cantidad total disponible
    query = db.query(
        Bull,
        Race.name.label('race_name'),
        Sex.name.label('sex_name'),
        func.sum(Input.quantity_received - Input.quantity_taken).label('total_available')
    ).options(
        joinedload(Bull.race),
        joinedload(Bull.sex)
    ).join(
        Race, Bull.race_id == Race.id, isouter=True
    ).join(
        Sex, Bull.sex_id == Sex.id, isouter=True
    ).join(
        Input, Bull.id == Input.bull_id
    ).filter(
        Bull.user_id == client_id
    ).group_by(
        Bull.id,
        Race.name,
        Sex.name
    ).having(
        func.sum(Input.quantity_received - Input.quantity_taken) > 0
    )
    
    # Aplicar paginación
    query = query.order_by(Bull.created_at.desc()).offset(skip).limit(limit)
    
    # Ejecutar consulta
    results = query.all()
    
    # Formatear resultados
    bulls_data = []
    for row in results:
        try:
            bull = row[0]  # Obtener el objeto Bull
            total_available = row.total_available or 0
            
            # Crear diccionario con todos los datos
            bull_data = {
                "id": bull.id,
                "name": bull.name,
                "registration_number": bull.registration_number,
                "lote": bull.lote,
                "escalerilla": bull.escalerilla,
                "description": bull.description,
                "race_id": bull.race_id,
                "race_name": row.race_name,
                "sex_id": bull.sex_id,
                "sex_name": row.sex_name,
                "status": bull.status.value if bull.status else None,
                "created_at": bull.created_at,
                "updated_at": bull.updated_at,
                "total_available": float(total_available) if total_available else 0.0  # Cantidad total de muestras disponibles con precisión decimal
            }
            
            bulls_data.append(bull_data)
        except Exception as e:
            logging.error(f"Error al procesar toro en get_bulls_with_available_samples: {str(e)}")
            # Continuar con el siguiente toro sin interrumpir el proceso
    
    return bulls_data

def get_bulls_with_available_inputs(db, cliente_id: int):
    # Buscar toros del cliente con al menos una entrada disponible
    bulls = (
        db.query(Bull)
        .options(joinedload(Bull.race))
        .filter(Bull.user_id == cliente_id)
        .join(Input, Bull.id == Input.bull_id)
        .filter(Input.quantity_taken < Input.quantity_received)
        .distinct()
        .all()
    )
    return bulls 