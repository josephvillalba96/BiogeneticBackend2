from sqlalchemy.orm import Session, selectinload
from app.models.calendar import CalendarTask, CalendarTaskType, CalendarTemplate, CalendarTemplateTask
from app.models.user import User
from app.schemas.calendar_schema import (
    CalendarTaskCreate, CalendarTaskUpdate,
    CalendarTaskTypeCreate, CalendarTaskTypeUpdate,
    CalendarTemplateCreate, CalendarTemplateUpdate,
    CalendarTemplateTaskCreate, CalendarTemplateTaskUpdate,
    WeeklyTaskCreate, TaskToggleResponse, BulkDeleteRequest, 
    BulkStatusUpdateRequest, TaskDuplicateRequest, CalendarStats
)
from fastapi import HTTPException, status
from typing import List, Optional, Dict, Any
import logging
from sqlalchemy import func, or_, and_
from datetime import date, datetime, time, timedelta

# Configurar logger
logger = logging.getLogger(__name__)

# ============================================================================
# SERVICIOS PARA CALENDAR TASK TYPE
# ============================================================================

def get_calendar_task_type(db: Session, task_type_id: int) -> Optional[CalendarTaskType]:
    """Obtiene un tipo de tarea del calendario por su ID"""
    return db.query(CalendarTaskType).filter(CalendarTaskType.id == task_type_id).first()

def get_calendar_task_types(db: Session, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[CalendarTaskType]:
    """Obtiene una lista de tipos de tareas del calendario"""
    query = db.query(CalendarTaskType)
    if active_only:
        query = query.filter(CalendarTaskType.is_active == True)
    return query.offset(skip).limit(limit).all()

def create_calendar_task_type(db: Session, task_type: CalendarTaskTypeCreate) -> CalendarTaskType:
    """Crea un nuevo tipo de tarea del calendario"""
    db_task_type = CalendarTaskType(**task_type.dict())
    db.add(db_task_type)
    db.commit()
    db.refresh(db_task_type)
    return db_task_type

def update_calendar_task_type(db: Session, task_type_id: int, task_type: CalendarTaskTypeUpdate) -> Optional[CalendarTaskType]:
    """Actualiza un tipo de tarea del calendario"""
    db_task_type = get_calendar_task_type(db, task_type_id)
    if not db_task_type:
        return None
    
    update_data = task_type.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_task_type, field, value)
    
    db.commit()
    db.refresh(db_task_type)
    return db_task_type

def delete_calendar_task_type(db: Session, task_type_id: int) -> bool:
    """Elimina un tipo de tarea del calendario"""
    db_task_type = get_calendar_task_type(db, task_type_id)
    if not db_task_type:
        return False
    
    db.delete(db_task_type)
    db.commit()
    return True

# ============================================================================
# SERVICIOS PARA CALENDAR TEMPLATE
# ============================================================================

def get_calendar_template(db: Session, template_id: int) -> Optional[CalendarTemplate]:
    """Obtiene un template del calendario por su ID"""
    return db.query(CalendarTemplate).filter(CalendarTemplate.id == template_id).first()

def get_calendar_templates(db: Session, skip: int = 0, limit: int = 100, active_only: bool = True) -> List[CalendarTemplate]:
    """Obtiene una lista de templates del calendario"""
    query = db.query(CalendarTemplate)
    if active_only:
        query = query.filter(CalendarTemplate.is_active == True)
    return query.offset(skip).limit(limit).all()

def create_calendar_template(db: Session, template: CalendarTemplateCreate) -> CalendarTemplate:
    """Crea un nuevo template del calendario"""
    db_template = CalendarTemplate(**template.dict())
    db.add(db_template)
    db.commit()
    db.refresh(db_template)
    return db_template

def update_calendar_template(db: Session, template_id: int, template: CalendarTemplateUpdate) -> Optional[CalendarTemplate]:
    """Actualiza un template del calendario"""
    db_template = get_calendar_template(db, template_id)
    if not db_template:
        return None
    
    update_data = template.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_template, field, value)
    
    db.commit()
    db.refresh(db_template)
    return db_template

def delete_calendar_template(db: Session, template_id: int) -> bool:
    """Elimina un template del calendario"""
    db_template = get_calendar_template(db, template_id)
    if not db_template:
        return False
    
    db.delete(db_template)
    db.commit()
    return True

# ============================================================================
# SERVICIOS PARA CALENDAR TEMPLATE TASK
# ============================================================================

def get_calendar_template_task(db: Session, template_task_id: int) -> Optional[CalendarTemplateTask]:
    """Obtiene una tarea de template por su ID"""
    return db.query(CalendarTemplateTask).filter(CalendarTemplateTask.id == template_task_id).first()

def get_calendar_template_tasks(db: Session, template_id: Optional[int] = None, skip: int = 0, limit: int = 100) -> List[CalendarTemplateTask]:
    """Obtiene una lista de tareas de template"""
    query = db.query(CalendarTemplateTask)
    if template_id:
        query = query.filter(CalendarTemplateTask.template_id == template_id)
    return query.order_by(CalendarTemplateTask.order_index).offset(skip).limit(limit).all()

def create_calendar_template_task(db: Session, template_task: CalendarTemplateTaskCreate) -> CalendarTemplateTask:
    """Crea una nueva tarea de template"""
    db_template_task = CalendarTemplateTask(**template_task.dict())
    db.add(db_template_task)
    db.commit()
    db.refresh(db_template_task)
    return db_template_task

def update_calendar_template_task(db: Session, template_task_id: int, template_task: CalendarTemplateTaskUpdate) -> Optional[CalendarTemplateTask]:
    """Actualiza una tarea de template"""
    db_template_task = get_calendar_template_task(db, template_task_id)
    if not db_template_task:
        return None
    
    update_data = template_task.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_template_task, field, value)
    
    db.commit()
    db.refresh(db_template_task)
    return db_template_task

def delete_calendar_template_task(db: Session, template_task_id: int) -> bool:
    """Elimina una tarea de template"""
    db_template_task = get_calendar_template_task(db, template_task_id)
    if not db_template_task:
        return False
    
    db.delete(db_template_task)
    db.commit()
    return True

# ============================================================================
# SERVICIOS PARA CALENDAR TASK
# ============================================================================

def get_calendar_task(db: Session, task_id: int) -> Optional[CalendarTask]:
    """Obtiene una tarea del calendario por su ID"""
    return (
        db.query(CalendarTask)
        .options(
            selectinload(CalendarTask.client),
            selectinload(CalendarTask.creator),
        )
        .filter(CalendarTask.id == task_id)
        .first()
    )

def get_calendar_tasks(
    db: Session, 
    skip: int = 0, 
    limit: int = 100,
    client_id: Optional[int] = None,
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    created_by: Optional[int] = None
) -> List[CalendarTask]:
    """Obtiene una lista de tareas del calendario con filtros opcionales"""
    query = (
        db.query(CalendarTask)
        .options(
            selectinload(CalendarTask.client),
            selectinload(CalendarTask.creator),
        )
    )
    
    if client_id:
        query = query.filter(CalendarTask.client_id == client_id)
    
    if task_type:
        query = query.filter(CalendarTask.task_type == task_type)
    
    if status:
        query = query.filter(CalendarTask.status == status)
    
    if start_date:
        query = query.filter(CalendarTask.start_date >= start_date)
    
    if end_date:
        query = query.filter(CalendarTask.end_date <= end_date)
    
    if created_by:
        query = query.filter(CalendarTask.created_by == created_by)
    
    return (
        query.order_by(CalendarTask.start_date, CalendarTask.start_time)
        .offset(skip)
        .limit(limit)
        .all()
    )

def get_calendar_tasks_by_date_range(
    db: Session,
    start_date: date,
    end_date: date,
    client_id: Optional[int] = None
) -> List[CalendarTask]:
    """Obtiene tareas del calendario en un rango de fechas específico"""
    query = (
        db.query(CalendarTask)
        .options(
            selectinload(CalendarTask.client),
            selectinload(CalendarTask.creator),
        )
        .filter(
        and_(
            CalendarTask.start_date <= end_date,
            CalendarTask.end_date >= start_date
        )
    ))
    
    if client_id:
        query = query.filter(CalendarTask.client_id == client_id)
    
    return query.order_by(CalendarTask.start_date, CalendarTask.start_time).all()

def create_calendar_task(db: Session, task: CalendarTaskCreate) -> CalendarTask:
    """Crea una nueva tarea del calendario"""
    # Verificar que el cliente existe
    client = db.query(User).filter(User.id == task.client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )
    
    # Verificar que el creador existe
    creator = db.query(User).filter(User.id == task.created_by).first()
    if not creator:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario creador no encontrado"
        )
    
    db_task = CalendarTask(**task.model_dump())
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    return db_task

def update_calendar_task(db: Session, task_id: int, task: CalendarTaskUpdate) -> Optional[CalendarTask]:
    """Actualiza una tarea del calendario"""
    db_task = get_calendar_task(db, task_id)
    if not db_task:
        return None
    
    update_data = task.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_task, field, value)
    
    db.commit()
    db.refresh(db_task)
    return db_task

def delete_calendar_task(db: Session, task_id: int) -> bool:
    """Elimina una tarea del calendario"""
    db_task = get_calendar_task(db, task_id)
    if not db_task:
        return False
    
    db.delete(db_task)
    db.commit()
    return True

def create_tasks_from_template(
    db: Session,
    template_id: int,
    client_id: int,
    start_date: date,
    created_by: int
) -> List[CalendarTask]:
    """Crea tareas del calendario basadas en un template"""
    # Obtener el template
    template = get_calendar_template(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template no encontrado"
        )
    
    # Obtener el cliente
    client = db.query(User).filter(User.id == client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )
    
    # Obtener las tareas del template
    template_tasks = get_calendar_template_tasks(db, template_id)
    if not template_tasks:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El template no tiene tareas configuradas"
        )
    
    # Generar un identificador único para el grupo de tareas
    import uuid
    task_group_id = str(uuid.uuid4())
    
    created_tasks = []
    for template_task in template_tasks:
        # Lógica de fecha corregida
        task_date = start_date + timedelta(days=template_task.day_offset)
        
        # Obtener el tipo de tarea
        task_type = get_calendar_task_type(db, template_task.task_type_id)
        if not task_type:
            continue
        
        # Lógica de nombre corregida
        if template_task.day_offset == 0:
            # El día 0 es la tarea OPUS
            summary = task_type.name
        else:
            # Los días siguientes se numeran como Día 0, Día 1, etc.
            # day_offset de 1 se convierte en Día 0
            summary = f"{task_type.name} - Día {template_task.day_offset - 1}"
            
        # Crear la tarea
        task_data = CalendarTaskCreate(
            client_id=client_id,
            client_name=client.full_name,
            task_name=task_type.name,
            task_type=task_type.type_code,
            summary=summary,
            description=task_type.description,
            start_date=task_date,
            end_date=task_date,
            created_by=created_by,
            task_group_id=task_group_id,
            color_background=task_type.color_background,
            color_foreground=task_type.color_foreground
        )
        
        created_task = create_calendar_task(db, task_data)
        created_tasks.append(created_task)
    
    # Recargar con relaciones para respuesta
    if created_tasks:
        created_ids = [t.id for t in created_tasks]
        tasks_with_rels = (
            db.query(CalendarTask)
            .options(
                selectinload(CalendarTask.client),
                selectinload(CalendarTask.creator),
            )
            .filter(CalendarTask.id.in_(created_ids))
            .all()
        )
        return tasks_with_rels

    return created_tasks

def search_calendar_tasks(
    db: Session,
    search_query: Optional[str] = None,
    client_id: Optional[int] = None,
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Busca tareas del calendario con criterios de búsqueda"""
    query = db.query(CalendarTask)
    
    if search_query:
        search_term = f"%{search_query.lower()}%"
        query = query.filter(
            or_(
                func.lower(CalendarTask.task_name).like(search_term),
                func.lower(CalendarTask.client_name).like(search_term),
                func.lower(CalendarTask.summary).like(search_term),
                func.lower(CalendarTask.description).like(search_term),
                func.lower(CalendarTask.veterinarian).like(search_term),
                func.lower(CalendarTask.location).like(search_term)
            )
        )
    
    if client_id:
        query = query.filter(CalendarTask.client_id == client_id)
    
    if task_type:
        query = query.filter(CalendarTask.task_type == task_type)
    
    if status:
        query = query.filter(CalendarTask.status == status)
    
    tasks = (
        query.options(
            selectinload(CalendarTask.client),
            selectinload(CalendarTask.creator),
        )
        .order_by(CalendarTask.start_date.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    # Formatear resultados
    result = []
    for task in tasks:
        task_data = {
            "id": task.id,
            "client_id": task.client_id,
            "client_name": task.client_name,
            "task_name": task.task_name,
            "task_type": task.task_type,
            "summary": task.summary,
            "description": task.description,
            "start_date": task.start_date,
            "start_time": task.start_time,
            "end_date": task.end_date,
            "end_time": task.end_time,
            "veterinarian": task.veterinarian,
            "location": task.location,
            "status": task.status,
            "suffix": task.suffix,
            "task_group_id": task.task_group_id,
            "color_background": task.color_background,
            "color_foreground": task.color_foreground,
            "created_by": task.created_by,
            "created_at": task.created_at,
            "updated_at": task.updated_at
        }
        result.append(task_data)
    
    return result

# ============================================================================
# NUEVAS FUNCIONES PARA ENDPOINTS ESPECÍFICOS
# ============================================================================

def get_calendar_tasks_by_client(
    db: Session,
    client_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> List[CalendarTask]:
    """Obtiene tareas de un cliente específico"""
    query = db.query(CalendarTask).filter(CalendarTask.client_id == client_id)
    
    if start_date:
        query = query.filter(CalendarTask.start_date >= start_date)
    
    if end_date:
        query = query.filter(CalendarTask.end_date <= end_date)
    
    return query.order_by(CalendarTask.start_date).all()

def get_calendar_tasks_by_date(
    db: Session,
    target_date: date
) -> List[CalendarTask]:
    """Obtiene tareas para una fecha específica"""
    return (
        db.query(CalendarTask)
        .options(
            selectinload(CalendarTask.client),
            selectinload(CalendarTask.creator),
        )
        .filter(CalendarTask.start_date == target_date)
        .order_by(CalendarTask.start_time)
        .all()
    )

def toggle_task_status(
    db: Session,
    task_id: int
) -> Optional[TaskToggleResponse]:
    """Cambia el estado de una tarea (pending ↔ completed)"""
    task = get_calendar_task(db, task_id)
    if not task:
        return None
    
    # Cambiar estado
    if task.status == "pending":
        task.status = "completed"
    elif task.status == "completed":
        task.status = "pending"
    # Si está cancelled, no cambia
    
    db.commit()
    db.refresh(task)
    
    return TaskToggleResponse(
        id=task.id,
        status=task.status,
        updated_at=task.updated_at
    )

def bulk_delete_tasks(
    db: Session,
    task_ids: List[int]
) -> Dict[str, Any]:
    """Elimina múltiples tareas"""
    deleted_count = 0
    for task_id in task_ids:
        if delete_calendar_task(db, task_id):
            deleted_count += 1
    
    return {
        "message": f"{deleted_count} tareas eliminadas exitosamente",
        "deleted_count": deleted_count
    }

def bulk_update_task_status(
    db: Session,
    task_ids: List[int],
    new_status: str
) -> Dict[str, Any]:
    """Actualiza el estado de múltiples tareas"""
    updated_count = 0
    for task_id in task_ids:
        task = get_calendar_task(db, task_id)
        if task:
            task.status = new_status
            updated_count += 1
    
    db.commit()
    
    return {
        "message": f"{updated_count} tareas actualizadas exitosamente",
        "updated_count": updated_count
    }

def duplicate_tasks_for_client(
    db: Session,
    source_client_id: int,
    target_client_id: int,
    new_start_date: date
) -> List[CalendarTask]:
    """Duplica tareas de un cliente a otro con nueva fecha de inicio"""
    # Obtener tareas del cliente origen
    source_tasks = get_calendar_tasks_by_client(db, source_client_id)
    
    if not source_tasks:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No se encontraron tareas para el cliente origen"
        )
    
    # Obtener cliente destino
    target_client = db.query(User).filter(User.id == target_client_id).first()
    if not target_client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente destino no encontrado"
        )
    
    # Calcular diferencia de días
    if source_tasks:
        original_start_date = source_tasks[0].start_date
        days_difference = (new_start_date - original_start_date).days
    else:
        days_difference = 0
    
    duplicated_tasks = []
    import uuid
    new_task_group_id = str(uuid.uuid4())
    
    for source_task in source_tasks:
        # Crear nueva tarea
        new_task_data = CalendarTaskCreate(
            client_id=target_client_id,
            client_name=target_client.full_name,
            task_name=source_task.task_name,
            task_type=source_task.task_type,
            summary=source_task.summary,
            description=source_task.description,
            start_date=source_task.start_date + timedelta(days=days_difference),
            start_time=source_task.start_time,
            end_date=source_task.end_date + timedelta(days=days_difference),
            end_time=source_task.end_time,
            veterinarian=source_task.veterinarian,
            location=source_task.location,
            status="pending",  # Nueva tarea siempre pendiente
            suffix=source_task.suffix,
            task_group_id=new_task_group_id,
            color_background=source_task.color_background,
            color_foreground=source_task.color_foreground,
            created_by=source_task.created_by
        )
        
        new_task = create_calendar_task(db, new_task_data)
        duplicated_tasks.append(new_task)
    
    if duplicated_tasks:
        duplicated_ids = [t.id for t in duplicated_tasks]
        tasks_with_rels = (
            db.query(CalendarTask)
            .options(
                selectinload(CalendarTask.client),
                selectinload(CalendarTask.creator),
            )
            .filter(CalendarTask.id.in_(duplicated_ids))
            .all()
        )
        return tasks_with_rels

    return duplicated_tasks

def get_calendar_stats(
    db: Session,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None
) -> CalendarStats:
    """Obtiene estadísticas del calendario"""
    query = db.query(CalendarTask)
    
    if start_date:
        query = query.filter(CalendarTask.start_date >= start_date)
    
    if end_date:
        query = query.filter(CalendarTask.end_date <= end_date)
    
    all_tasks = query.all()
    
    # Contar por estado
    total_tasks = len(all_tasks)
    pending_tasks = len([t for t in all_tasks if t.status == "pending"])
    completed_tasks = len([t for t in all_tasks if t.status == "completed"])
    cancelled_tasks = len([t for t in all_tasks if t.status == "cancelled"])
    
    # Contar por tipo
    tasks_by_type = {}
    for task in all_tasks:
        task_type = task.task_type
        tasks_by_type[task_type] = tasks_by_type.get(task_type, 0) + 1
    
    # Contar por cliente
    tasks_by_client = {}
    for task in all_tasks:
        client_id = str(task.client_id)
        tasks_by_client[client_id] = tasks_by_client.get(client_id, 0) + 1
    
    return CalendarStats(
        total_tasks=total_tasks,
        pending_tasks=pending_tasks,
        completed_tasks=completed_tasks,
        cancelled_tasks=cancelled_tasks,
        tasks_by_type=tasks_by_type,
        tasks_by_client=tasks_by_client
    )

def get_template_with_tasks(
    db: Session,
    template_id: int
) -> Optional[CalendarTemplate]:
    """Obtiene un template con sus tareas configuradas"""
    template = get_calendar_template(db, template_id)
    if not template:
        return None
    
    # Obtener tareas del template
    template_tasks = get_calendar_template_tasks(db, template_id=template_id)
    
    # Convertir a formato de respuesta
    tasks_data = []
    for template_task in template_tasks:
        task_data = {
            "task_type_id": template_task.task_type_id,
            "day_offset": template_task.day_offset,
            "order_index": template_task.order_index
        }
        tasks_data.append(task_data)
    
    # Agregar tareas al template
    template.tasks = tasks_data
    
    return template

def create_weekly_tasks(
    db: Session,
    weekly_data: WeeklyTaskCreate
) -> List[CalendarTask]:
    """Crea tareas semanales automáticas basadas en un template"""
    # Verificar que el cliente existe
    client = db.query(User).filter(User.id == weekly_data.client_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )
    
    # Verificar que el template existe
    template = get_calendar_template(db, weekly_data.template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template no encontrado"
        )
    
    # Crear tareas usando el template
    return create_tasks_from_template(
        db=db,
        template_id=weekly_data.template_id,
        client_id=weekly_data.client_id,
        start_date=weekly_data.start_date,
        created_by=weekly_data.created_by
    )
