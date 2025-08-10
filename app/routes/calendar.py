from fastapi import APIRouter, Depends, HTTPException, status, Query, File, UploadFile
from sqlalchemy.orm import Session
from app.database.base import get_db
from app.services import calendar_service
from app.services.auth_service import get_current_user_from_token, get_current_active_user
from app.schemas.calendar_schema import (
    CalendarTaskSchema, CalendarTaskCreate, CalendarTaskUpdate,
    CalendarTaskTypeSchema, CalendarTaskTypeCreate, CalendarTaskTypeUpdate,
    CalendarTemplateSchema, CalendarTemplateCreate, CalendarTemplateUpdate,
    CalendarTemplateTaskSchema, CalendarTemplateTaskCreate, CalendarTemplateTaskUpdate,
    CalendarTaskResponse, CalendarTaskListResponse,
    CalendarTaskTypeResponse, CalendarTaskTypeListResponse,
    CalendarTemplateResponse, CalendarTemplateListResponse,
    WeeklyTaskCreate, TaskToggleResponse, BulkDeleteRequest,
    BulkStatusUpdateRequest, TaskDuplicateRequest, CalendarStatsResponse,
    BulkOperationResponse
)
from app.models.user import User
from typing import List, Dict, Any, Optional
from datetime import date, datetime

router = APIRouter(
    prefix="/calendar",
    tags=["calendar"],
    responses={404: {"description": "No encontrado"}},
)

# ============================================================================
# RUTAS PARA CALENDAR TASK TYPE
# ============================================================================

@router.get("/task-types/", response_model=CalendarTaskTypeListResponse)
async def get_calendar_task_types(
    skip: int = 0, 
    limit: int = 100,
    active_only: bool = Query(True, description="Solo tipos activos"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene la lista de tipos de tareas del calendario"""
    task_types = calendar_service.get_calendar_task_types(
        db, skip=skip, limit=limit, active_only=active_only
    )
    total = len(task_types)  # En una implementación real, contar total sin limit
    return CalendarTaskTypeListResponse(
        data=task_types,
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/task-types/{task_type_id}", response_model=CalendarTaskTypeSchema)
async def get_calendar_task_type(
    task_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene un tipo de tarea específico del calendario"""
    task_type = calendar_service.get_calendar_task_type(db, task_type_id)
    if not task_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de tarea no encontrado"
        )
    return task_type

@router.post("/task-types/", response_model=CalendarTaskTypeSchema, status_code=status.HTTP_201_CREATED)
async def create_calendar_task_type(
    task_type: CalendarTaskTypeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Crea un nuevo tipo de tarea del calendario"""
    return calendar_service.create_calendar_task_type(db, task_type)

@router.put("/task-types/{task_type_id}", response_model=CalendarTaskTypeSchema)
async def update_calendar_task_type(
    task_type_id: int,
    task_type: CalendarTaskTypeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Actualiza un tipo de tarea del calendario"""
    updated_task_type = calendar_service.update_calendar_task_type(db, task_type_id, task_type)
    if not updated_task_type:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de tarea no encontrado"
        )
    return updated_task_type

@router.delete("/task-types/{task_type_id}")
async def delete_calendar_task_type(
    task_type_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Elimina un tipo de tarea del calendario"""
    success = calendar_service.delete_calendar_task_type(db, task_type_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tipo de tarea no encontrado"
        )
    return {"message": "Tipo de tarea eliminado exitosamente"}

# ============================================================================
# RUTAS PARA CALENDAR TEMPLATE
# ============================================================================

@router.get("/templates/", response_model=CalendarTemplateListResponse)
async def get_calendar_templates(
    skip: int = 0, 
    limit: int = 100,
    active_only: bool = Query(True, description="Solo templates activos"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene la lista de templates del calendario"""
    templates = calendar_service.get_calendar_templates(
        db, skip=skip, limit=limit, active_only=active_only
    )
    
    # Agregar tareas a cada template
    for template in templates:
        template_tasks = calendar_service.get_calendar_template_tasks(db, template_id=template.id)
        tasks_data = []
        for template_task in template_tasks:
            task_data = {
                "task_type_id": template_task.task_type_id,
                "day_offset": template_task.day_offset,
                "order_index": template_task.order_index
            }
            tasks_data.append(task_data)
        template.tasks = tasks_data
    
    total = len(templates)  # En una implementación real, contar total sin limit
    return CalendarTemplateListResponse(
        data=templates,
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/templates/{template_id}", response_model=CalendarTemplateSchema)
async def get_calendar_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene un template específico del calendario con sus tareas"""
    template = calendar_service.get_template_with_tasks(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template no encontrado"
        )
    return template

@router.post("/templates/", response_model=CalendarTemplateSchema, status_code=status.HTTP_201_CREATED)
async def create_calendar_template(
    template: CalendarTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Crea un nuevo template del calendario"""
    return calendar_service.create_calendar_template(db, template)

@router.put("/templates/{template_id}", response_model=CalendarTemplateSchema)
async def update_calendar_template(
    template_id: int,
    template: CalendarTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Actualiza un template del calendario"""
    updated_template = calendar_service.update_calendar_template(db, template_id, template)
    if not updated_template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template no encontrado"
        )
    return updated_template

@router.delete("/templates/{template_id}")
async def delete_calendar_template(
    template_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Elimina un template del calendario"""
    success = calendar_service.delete_calendar_template(db, template_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Template no encontrado"
        )
    return {"message": "Template eliminado exitosamente"}

# ============================================================================
# RUTAS PARA CALENDAR TEMPLATE TASK
# ============================================================================

@router.get("/template-tasks/", response_model=List[CalendarTemplateTaskSchema])
async def get_calendar_template_tasks(
    template_id: Optional[int] = None,
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene la lista de tareas de template"""
    template_tasks = calendar_service.get_calendar_template_tasks(
        db, template_id=template_id, skip=skip, limit=limit
    )
    return template_tasks

@router.get("/template-tasks/{template_task_id}", response_model=CalendarTemplateTaskSchema)
async def get_calendar_template_task(
    template_task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene una tarea de template específica"""
    template_task = calendar_service.get_calendar_template_task(db, template_task_id)
    if not template_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea de template no encontrada"
        )
    return template_task

@router.post("/template-tasks/", response_model=CalendarTemplateTaskSchema, status_code=status.HTTP_201_CREATED)
async def create_calendar_template_task(
    template_task: CalendarTemplateTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Crea una nueva tarea de template"""
    return calendar_service.create_calendar_template_task(db, template_task)

@router.put("/template-tasks/{template_task_id}", response_model=CalendarTemplateTaskSchema)
async def update_calendar_template_task(
    template_task_id: int,
    template_task: CalendarTemplateTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Actualiza una tarea de template"""
    updated_template_task = calendar_service.update_calendar_template_task(db, template_task_id, template_task)
    if not updated_template_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea de template no encontrada"
        )
    return updated_template_task

@router.delete("/template-tasks/{template_task_id}")
async def delete_calendar_template_task(
    template_task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Elimina una tarea de template"""
    success = calendar_service.delete_calendar_template_task(db, template_task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea de template no encontrada"
        )
    return {"message": "Tarea de template eliminada exitosamente"}

# ============================================================================
# RUTAS PARA CALENDAR TASK
# ============================================================================

@router.get("/tasks/", response_model=CalendarTaskListResponse)
async def get_calendar_tasks(
    skip: int = 0, 
    limit: int = 100,
    client_id: Optional[int] = None,
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    created_by: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene la lista de tareas del calendario con filtros opcionales"""
    tasks = calendar_service.get_calendar_tasks(
        db, 
        skip=skip, 
        limit=limit,
        client_id=client_id,
        task_type=task_type,
        status=status,
        start_date=start_date,
        end_date=end_date,
        created_by=created_by
    )
    total = len(tasks)  # En una implementación real, contar total sin limit
    return CalendarTaskListResponse(
        data=tasks,
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/tasks/client/{client_id}", response_model=List[CalendarTaskSchema])
async def get_calendar_tasks_by_client(
    client_id: int,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene tareas de un cliente específico"""
    tasks = calendar_service.get_calendar_tasks_by_client(
        db, client_id, start_date, end_date
    )
    return tasks

@router.get("/tasks/date/{date}", response_model=List[CalendarTaskSchema])
async def get_calendar_tasks_by_date(
    date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene tareas para una fecha específica"""
    tasks = calendar_service.get_calendar_tasks_by_date(db, date)
    return tasks

@router.get("/tasks/date-range/", response_model=List[CalendarTaskSchema])
async def get_calendar_tasks_by_date_range(
    start_date: date,
    end_date: date,
    client_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene tareas del calendario en un rango de fechas específico"""
    tasks = calendar_service.get_calendar_tasks_by_date_range(
        db, start_date, end_date, client_id
    )
    return tasks

@router.get("/tasks/search/", response_model=CalendarTaskListResponse)
async def search_calendar_tasks(
    q: Optional[str] = None,
    client_id: Optional[int] = None,
    task_type: Optional[str] = None,
    status: Optional[str] = None,
    skip: int = 0, 
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Busca tareas del calendario con criterios de búsqueda"""
    tasks_data = calendar_service.search_calendar_tasks(
        db, 
        search_query=q,
        client_id=client_id,
        task_type=task_type,
        status=status,
        skip=skip, 
        limit=limit
    )
    
    # Convertir a CalendarTaskSchema
    tasks = []
    for task_data in tasks_data:
        task = CalendarTaskSchema(**task_data)
        tasks.append(task)
    
    total = len(tasks)  # En una implementación real, contar total sin limit
    return CalendarTaskListResponse(
        data=tasks,
        total=total,
        skip=skip,
        limit=limit
    )

@router.get("/tasks/{task_id}", response_model=CalendarTaskSchema)
async def get_calendar_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene una tarea específica del calendario"""
    task = calendar_service.get_calendar_task(db, task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada"
        )
    return task

@router.post("/tasks/", response_model=CalendarTaskSchema, status_code=status.HTTP_201_CREATED)
async def create_calendar_task(
    task: CalendarTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Crea una nueva tarea del calendario"""
    return calendar_service.create_calendar_task(db, task)

@router.post("/tasks/weekly", response_model=List[CalendarTaskSchema], status_code=status.HTTP_201_CREATED)
async def create_weekly_tasks(
    weekly_data: WeeklyTaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Crea tareas semanales automáticas basadas en un template"""
    try:
        tasks = calendar_service.create_weekly_tasks(db, weekly_data)
        return tasks
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear tareas semanales: {str(e)}"
        )

@router.put("/tasks/{task_id}", response_model=CalendarTaskSchema)
async def update_calendar_task(
    task_id: int,
    task: CalendarTaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Actualiza una tarea del calendario"""
    updated_task = calendar_service.update_calendar_task(db, task_id, task)
    if not updated_task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada"
        )
    return updated_task

@router.patch("/tasks/{task_id}/toggle-status", response_model=TaskToggleResponse)
async def toggle_task_status(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Cambia el estado de una tarea (pending ↔ completed)"""
    result = calendar_service.toggle_task_status(db, task_id)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada"
        )
    return result

@router.delete("/tasks/{task_id}")
async def delete_calendar_task(
    task_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Elimina una tarea del calendario"""
    success = calendar_service.delete_calendar_task(db, task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tarea no encontrada"
        )
    return {"message": "Tarea eliminada exitosamente", "deleted_id": task_id}

# ============================================================================
# RUTAS ESPECIALES
# ============================================================================

@router.post("/tasks/from-template/", response_model=List[CalendarTaskSchema], status_code=status.HTTP_201_CREATED)
async def create_tasks_from_template(
    template_id: int,
    client_id: int,
    start_date: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Crea tareas del calendario basadas en un template"""
    try:
        tasks = calendar_service.create_tasks_from_template(
            db, template_id, client_id, start_date, current_user.id
        )
        return tasks
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear tareas desde template: {str(e)}"
        )

# ============================================================================
# NUEVOS ENDPOINTS ESPECÍFICOS
# ============================================================================

@router.get("/stats", response_model=CalendarStatsResponse)
async def get_calendar_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Obtiene estadísticas del calendario"""
    stats = calendar_service.get_calendar_stats(db, start_date, end_date)
    return CalendarStatsResponse(data=stats)

@router.delete("/tasks/bulk", response_model=BulkOperationResponse)
async def bulk_delete_tasks(
    request: BulkDeleteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Elimina múltiples tareas"""
    result = calendar_service.bulk_delete_tasks(db, request.task_ids)
    return BulkOperationResponse(
        message=result["message"],
        deleted_count=result["deleted_count"]
    )

@router.patch("/tasks/bulk-status", response_model=BulkOperationResponse)
async def bulk_update_task_status(
    request: BulkStatusUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Actualiza el estado de múltiples tareas"""
    result = calendar_service.bulk_update_task_status(
        db, request.task_ids, request.status
    )
    return BulkOperationResponse(
        message=result["message"],
        updated_count=result["updated_count"]
    )

@router.post("/tasks/duplicate", response_model=List[CalendarTaskSchema])
async def duplicate_tasks(
    request: TaskDuplicateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Duplica tareas de un cliente a otro"""
    try:
        tasks = calendar_service.duplicate_tasks_for_client(
            db, request.source_client_id, request.target_client_id, request.start_date
        )
        return tasks
    except HTTPException as e:
        raise e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al duplicar tareas: {str(e)}"
        )

@router.get("/tasks/export/csv")
async def export_tasks_to_csv(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    client_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Exporta tareas a CSV"""
    # Implementación básica - en producción usaría una librería como pandas
    tasks = calendar_service.get_calendar_tasks_by_date_range(
        db, start_date or date.today(), end_date or date.today(), client_id
    )
    
    # Crear CSV básico
    csv_content = "ID,Cliente,Tarea,Tipo,Estado,Fecha Inicio,Hora Inicio,Fecha Fin,Hora Fin,Veterinario,Ubicación\n"
    for task in tasks:
        csv_content += f"{task.id},{task.client_name},{task.task_name},{task.task_type},{task.status},{task.start_date},{task.start_time},{task.end_date},{task.end_time},{task.veterinarian or ''},{task.location or ''}\n"
    
    from fastapi.responses import Response
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=calendar_tasks.csv"}
    )

@router.post("/tasks/import/csv", response_model=BulkOperationResponse)
async def import_tasks_from_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """Importa tareas desde CSV"""
    # Implementación básica - en producción usaría pandas
    try:
        content = await file.read()
        csv_content = content.decode('utf-8')
        
        lines = csv_content.strip().split('\n')[1:]  # Saltar header
        imported_count = 0
        errors = []
        
        for i, line in enumerate(lines, 1):
            try:
                # Parsear línea CSV básico
                fields = line.split(',')
                if len(fields) >= 6:
                    # Crear tarea básica
                    task_data = CalendarTaskCreate(
                        client_id=1,  # Default - en producción se buscaría por nombre
                        client_name=fields[1],
                        task_name=fields[2],
                        task_type=fields[3],
                        summary=fields[2],
                        start_date=datetime.strptime(fields[5], '%Y-%m-%d').date(),
                        end_date=datetime.strptime(fields[7], '%Y-%m-%d').date(),
                        status=fields[4],
                        veterinarian=fields[9] if len(fields) > 9 else None,
                        location=fields[10] if len(fields) > 10 else None,
                        created_by=current_user.id
                    )
                    
                    calendar_service.create_calendar_task(db, task_data)
                    imported_count += 1
                else:
                    errors.append(f"Línea {i}: Formato inválido")
            except Exception as e:
                errors.append(f"Línea {i}: {str(e)}")
        
        return BulkOperationResponse(
            message="Importación completada",
            imported_count=imported_count,
            errors=errors
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error al procesar archivo CSV: {str(e)}"
        )
