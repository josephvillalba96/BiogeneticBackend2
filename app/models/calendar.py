from sqlalchemy import Column, Integer, String, Text, Date, Time, Boolean, ForeignKey, VARCHAR
from sqlalchemy.orm import relationship
from app.models.base_model import Base, BaseModel
from datetime import datetime, date, time

class CalendarTaskType(Base, BaseModel):
    __tablename__ = "calendar_task_types"
    
    name = Column(String(100), nullable=False)  # 'Opus', 'FIV', 'CIV', 'D3', 'D5', 'Previsión', 'Informe'
    type_code = Column(String(50), nullable=False)  # 'opus', 'fiv', 'civ', 'd3', 'd5', 'prevision', 'informe'
    day_offset = Column(Integer, nullable=False)  # Día relativo al inicio del proceso
    color_background = Column(VARCHAR(7), default='#e3f2fd')
    color_foreground = Column(VARCHAR(7), default='#0d47a1')
    description = Column(Text)
    is_active = Column(Boolean, default=True)
    
    # Relaciones
    template_tasks = relationship("CalendarTemplateTask", back_populates="task_type")
    
    def __repr__(self):
        return f"<CalendarTaskType {self.name}>"

class CalendarTemplate(Base, BaseModel):
    __tablename__ = "calendar_templates"
    
    name = Column(String(255), nullable=False)
    description = Column(Text)
    duration_days = Column(Integer, default=8)
    is_active = Column(Boolean, default=True)
    
    # Relaciones
    template_tasks = relationship("CalendarTemplateTask", back_populates="template")
    
    def __repr__(self):
        return f"<CalendarTemplate {self.name}>"

class CalendarTemplateTask(Base, BaseModel):
    __tablename__ = "calendar_template_tasks"
    
    template_id = Column(Integer, ForeignKey("calendar_templates.id"), nullable=False)
    task_type_id = Column(Integer, ForeignKey("calendar_task_types.id"), nullable=False)
    day_offset = Column(Integer, nullable=False)
    order_index = Column(Integer, nullable=False)
    
    # Relaciones
    template = relationship("CalendarTemplate", back_populates="template_tasks")
    task_type = relationship("CalendarTaskType", back_populates="template_tasks")
    
    def __repr__(self):
        return f"<CalendarTemplateTask template_id={self.template_id} task_type_id={self.task_type_id}>"

class CalendarTask(Base, BaseModel):
    __tablename__ = "calendar_tasks"
    
    client_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    client_name = Column(String(255), nullable=False)
    task_name = Column(String(100), nullable=False)
    task_type = Column(String(50), nullable=False)  # 'opus', 'fiv', 'civ', 'd3', 'd5', 'prevision', 'informe'
    summary = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Fechas y horarios
    start_date = Column(Date, nullable=False)
    start_time = Column(Time, default=time(9, 0, 0))  # 09:00:00
    end_date = Column(Date, nullable=False)
    end_time = Column(Time, default=time(17, 0, 0))  # 17:00:00
    
    # Información del proceso
    veterinarian = Column(String(255))
    location = Column(String(255))
    status = Column(String(50), default='pending')  # 'pending', 'completed', 'cancelled'
    
    # Identificadores únicos
    suffix = Column(String(100))  # Identificador único para grupo de tareas
    task_group_id = Column(String(100))  # Para agrupar tareas relacionadas
    
    # Colores personalizados
    color_background = Column(VARCHAR(7), default='#e3f2fd')
    color_foreground = Column(VARCHAR(7), default='#0d47a1')
    
    # Relaciones
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Relaciones con otros modelos
    client = relationship("User", foreign_keys=[client_id])
    creator = relationship("User", foreign_keys=[created_by])
    
    def __repr__(self):
        return f"<CalendarTask {self.task_name} - {self.client_name}>"
