from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.schemas.base_schema import BaseSchema
from app.schemas.user_schema import UserSchema
from datetime import date, time, datetime
from enum import Enum

class TaskStatus(str, Enum):
    pending = "pending"
    completed = "completed"
    cancelled = "cancelled"

class TaskType(str, Enum):
    opus = "opus"
    fiv = "fiv"
    civ = "civ"
    d3 = "d3"
    d5 = "d5"
    prevision = "prevision"
    informe = "informe"

# Esquemas para CalendarTaskType
class CalendarTaskTypeBase(BaseModel):
    name: str = Field(..., description="Nombre del tipo de tarea")
    type_code: str = Field(..., description="Código del tipo de tarea")
    day_offset: int = Field(..., description="Día relativo al inicio del proceso")
    color_background: Optional[str] = Field(default="#e3f2fd", description="Color de fondo")
    color_foreground: Optional[str] = Field(default="#0d47a1", description="Color de texto")
    description: Optional[str] = Field(None, description="Descripción del tipo de tarea")
    is_active: Optional[bool] = Field(default=True, description="Si el tipo está activo")

class CalendarTaskTypeCreate(CalendarTaskTypeBase):
    pass

class CalendarTaskTypeUpdate(BaseModel):
    name: Optional[str] = None
    type_code: Optional[str] = None
    day_offset: Optional[int] = None
    color_background: Optional[str] = None
    color_foreground: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class CalendarTaskTypeSchema(CalendarTaskTypeBase, BaseSchema):
    class Config:
        from_attributes = True

# Esquemas para CalendarTemplate
class CalendarTemplateBase(BaseModel):
    name: str = Field(..., description="Nombre del template")
    description: Optional[str] = Field(None, description="Descripción del template")
    duration_days: Optional[int] = Field(default=8, description="Duración en días")
    is_active: Optional[bool] = Field(default=True, description="Si el template está activo")

class CalendarTemplateCreate(CalendarTemplateBase):
    pass

class CalendarTemplateUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    duration_days: Optional[int] = None
    is_active: Optional[bool] = None

class CalendarTemplateSchema(CalendarTemplateBase, BaseSchema):
    tasks: Optional[List[Dict[str, Any]]] = Field(default=[], description="Tareas del template")
    
    class Config:
        from_attributes = True

# Esquemas para CalendarTemplateTask
class CalendarTemplateTaskBase(BaseModel):
    template_id: int = Field(..., description="ID del template")
    task_type_id: int = Field(..., description="ID del tipo de tarea")
    day_offset: int = Field(..., description="Día relativo al inicio del proceso")
    order_index: int = Field(..., description="Orden de la tarea en el template")

class CalendarTemplateTaskCreate(CalendarTemplateTaskBase):
    pass

class CalendarTemplateTaskUpdate(BaseModel):
    template_id: Optional[int] = None
    task_type_id: Optional[int] = None
    day_offset: Optional[int] = None
    order_index: Optional[int] = None

class CalendarTemplateTaskSchema(CalendarTemplateTaskBase, BaseSchema):
    template: Optional[CalendarTemplateSchema] = None
    task_type: Optional[CalendarTaskTypeSchema] = None
    
    class Config:
        from_attributes = True

# Esquemas para CalendarTask
class CalendarTaskBase(BaseModel):
    client_id: int = Field(..., description="ID del cliente")
    client_name: str = Field(..., description="Nombre del cliente")
    task_name: str = Field(..., description="Nombre de la tarea")
    task_type: str = Field(..., description="Tipo de tarea")
    summary: str = Field(..., description="Resumen de la tarea")
    description: Optional[str] = Field(None, description="Descripción detallada")
    
    # Fechas y horarios
    start_date: date = Field(..., description="Fecha de inicio")
    start_time: Optional[time] = Field(default=time(9, 0, 0), description="Hora de inicio")
    end_date: date = Field(..., description="Fecha de fin")
    end_time: Optional[time] = Field(default=time(17, 0, 0), description="Hora de fin")
    
    # Información del proceso
    veterinarian: Optional[str] = Field(None, description="Veterinario responsable")
    location: Optional[str] = Field(None, description="Ubicación")
    status: Optional[str] = Field(default="pending", description="Estado de la tarea")
    
    # Identificadores únicos
    suffix: Optional[str] = Field(None, description="Identificador único para grupo de tareas")
    task_group_id: Optional[str] = Field(None, description="Para agrupar tareas relacionadas")
    
    # Colores personalizados
    color_background: Optional[str] = Field(default="#e3f2fd", description="Color de fondo")
    color_foreground: Optional[str] = Field(default="#0d47a1", description="Color de texto")

class CalendarTaskCreate(CalendarTaskBase):
    created_by: int = Field(..., description="ID del usuario que crea la tarea")

class CalendarTaskUpdate(BaseModel):
    client_id: Optional[int] = None
    client_name: Optional[str] = None
    task_name: Optional[str] = None
    task_type: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    start_date: Optional[date] = None
    start_time: Optional[time] = None
    end_date: Optional[date] = None
    end_time: Optional[time] = None
    veterinarian: Optional[str] = None
    location: Optional[str] = None
    status: Optional[str] = None
    suffix: Optional[str] = None
    task_group_id: Optional[str] = None
    color_background: Optional[str] = None
    color_foreground: Optional[str] = None

class CalendarTaskSchema(CalendarTaskBase, BaseSchema):
    created_by: int
    client: Optional[UserSchema] = None
    creator: Optional[UserSchema] = None
    
    class Config:
        from_attributes = True

# Nuevos schemas para endpoints específicos
class WeeklyTaskCreate(BaseModel):
    client_id: int = Field(..., description="ID del cliente")
    client_name: str = Field(..., description="Nombre del cliente")
    start_date: date = Field(..., description="Fecha de inicio")
    veterinarian: Optional[str] = Field(None, description="Veterinario responsable")
    location: Optional[str] = Field(None, description="Ubicación")
    description: Optional[str] = Field(None, description="Descripción del proceso")
    template_id: int = Field(..., description="ID del template a usar")
    created_by: int = Field(..., description="ID del usuario que crea las tareas")

class TaskToggleResponse(BaseModel):
    id: int
    status: str
    updated_at: datetime

class BulkDeleteRequest(BaseModel):
    task_ids: List[int] = Field(..., description="Lista de IDs de tareas a eliminar")

class BulkStatusUpdateRequest(BaseModel):
    task_ids: List[int] = Field(..., description="Lista de IDs de tareas")
    status: str = Field(..., description="Nuevo estado para las tareas")

class TaskDuplicateRequest(BaseModel):
    source_client_id: int = Field(..., description="ID del cliente origen")
    target_client_id: int = Field(..., description="ID del cliente destino")
    start_date: date = Field(..., description="Nueva fecha de inicio")

class CalendarStats(BaseModel):
    total_tasks: int
    pending_tasks: int
    completed_tasks: int
    cancelled_tasks: int
    tasks_by_type: Dict[str, int]
    tasks_by_client: Dict[str, int]

# Esquemas para respuestas de API
class CalendarTaskResponse(BaseModel):
    success: bool
    message: str
    data: Optional[CalendarTaskSchema] = None

class CalendarTaskListResponse(BaseModel):
    data: List[CalendarTaskSchema] = []
    total: int = 0
    skip: int = 0
    limit: int = 100

class CalendarTaskTypeResponse(BaseModel):
    success: bool
    message: str
    data: Optional[CalendarTaskTypeSchema] = None

class CalendarTaskTypeListResponse(BaseModel):
    data: List[CalendarTaskTypeSchema] = []
    total: int = 0
    skip: int = 0
    limit: int = 100

class CalendarTemplateResponse(BaseModel):
    success: bool
    message: str
    data: Optional[CalendarTemplateSchema] = None

class CalendarTemplateListResponse(BaseModel):
    data: List[CalendarTemplateSchema] = []
    total: int = 0
    skip: int = 0
    limit: int = 100

class CalendarStatsResponse(BaseModel):
    data: CalendarStats

class BulkOperationResponse(BaseModel):
    message: str
    deleted_count: Optional[int] = None
    updated_count: Optional[int] = None
    imported_count: Optional[int] = None
    errors: Optional[List[str]] = None
