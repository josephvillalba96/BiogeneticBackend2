#!/usr/bin/env python3
"""
Script para poblar la base de datos con datos iniciales para el calendario
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.database.base import SessionLocal, engine
from app.models.calendar import CalendarTaskType, CalendarTemplate, CalendarTemplateTask
from app.models.base_model import Base

def create_tables():
    """Crear las tablas si no existen"""
    Base.metadata.create_all(bind=engine)

def seed_calendar_task_types(db: Session):
    """Poblar los tipos de tareas del calendario"""
task_types = [
        {
            "name": "OPU",
            "type_code": "opu",
            "day_offset": 0,
            "color_background": "#e3f2fd",
            "color_foreground": "#0d47a1",
            "description": "Procedimiento OPU (Ovum Pick Up)"
        },
        {
            "name": "FIV",
            "type_code": "fiv",
            "day_offset": 1,
            "color_background": "#f3e5f5",
            "color_foreground": "#4a148c",
            "description": "Fecundación In Vitro"
        },
        {
            "name": "CIV",
            "type_code": "civ",
            "day_offset": 2,
            "color_background": "#e8f5e8",
            "color_foreground": "#1b5e20",
            "description": "Cultivo In Vitro"
        },
        {
            "name": "Clivage",
            "type_code": "clivage",
            "day_offset": 3,
            "color_background": "#fff3e0",
            "color_foreground": "#e65100",
            "description": "Evaluación de clivaje"
        },
        {
            "name": "D4",
            "type_code": "d4",
            "day_offset": 4,
            "color_background": "#fce4ec",
            "color_foreground": "#880e4f",
            "description": "Evaluación de embriones día 4"
        },
        {
            "name": "D5",
            "type_code": "d5",
            "day_offset": 5,
            "color_background": "#f1f8e9",
            "color_foreground": "#33691e",
            "description": "Evaluación de embriones día 5"
        },
        {
            "name": "Previsión",
            "type_code": "prevision",
            "day_offset": 6,
            "color_background": "#f1f8e9",
            "color_foreground": "#33691e",
            "description": "Previsión de resultados"
        },
        {
            "name": "TE",
            "type_code": "TE",
            "day_offset": 7,
            "color_background": "#e0f2f1",
            "color_foreground": "#004d40",
            "description": "Transferencia Embrionaria"
        }
    ]
    
    for task_type_data in task_types:
        existing = db.query(CalendarTaskType).filter(
            CalendarTaskType.type_code == task_type_data["type_code"]
        ).first()
        
        if not existing:
            task_type = CalendarTaskType(**task_type_data)
            db.add(task_type)
            print(f"✅ Creado tipo de tarea: {task_type_data['name']}")
        else:
            print(f"⏭️  Tipo de tarea ya existe: {task_type_data['name']}")
    
    db.commit()

def seed_calendar_templates(db: Session):
    """Poblar los templates del calendario"""
    templates = [
        {
            "name": "Proceso Estándar OPU",
            "description": "Template para el proceso estándar de OPU con todas las etapas",
            "duration_days": 8,
            "is_active": True
        },
        {
            "name": "Proceso Acelerado",
            "description": "Template para procesos acelerados con menos días",
            "duration_days": 5,
            "is_active": True
        },
        {
            "name": "Solo Evaluación",
            "description": "Template para procesos que solo incluyen evaluaciones",
            "duration_days": 3,
            "is_active": True
        }
    ]
    
    for template_data in templates:
        existing = db.query(CalendarTemplate).filter(
            CalendarTemplate.name == template_data["name"]
        ).first()
        
        if not existing:
            template = CalendarTemplate(**template_data)
            db.add(template)
            print(f"✅ Creado template: {template_data['name']}")
        else:
            print(f"⏭️  Template ya existe: {template_data['name']}")
    
    db.commit()

def seed_calendar_template_tasks(db: Session):
    """Poblar las tareas de los templates"""
    # Obtener el template "Proceso Estándar OPU"
    standard_template = db.query(CalendarTemplate).filter(
        CalendarTemplate.name == "Proceso Estándar OPU"
    ).first()
    
    if not standard_template:
        print("❌ Template 'Proceso Estándar OPU' no encontrado")
        return
    
    # Obtener todos los tipos de tareas
    task_types = db.query(CalendarTaskType).all()
    task_types_dict = {tt.type_code: tt.id for tt in task_types}
    
# Definir las tareas para el template estándar
    template_tasks = [
        {"type_code": "opu", "day_offset": 0, "order_index": 1},
        {"type_code": "fiv", "day_offset": 1, "order_index": 2},
        {"type_code": "civ", "day_offset": 2, "order_index": 3},
        {"type_code": "clivage", "day_offset": 3, "order_index": 4},
        {"type_code": "d4", "day_offset": 4, "order_index": 5},
        {"type_code": "d5", "day_offset": 5, "order_index": 6},
        {"type_code": "prevision", "day_offset": 6, "order_index": 7},
        {"type_code": "TE", "day_offset": 7, "order_index": 8}
    ]
    
    # Verificar si ya existen tareas para este template
    existing_tasks = db.query(CalendarTemplateTask).filter(
        CalendarTemplateTask.template_id == standard_template.id
    ).count()
    
    if existing_tasks == 0:
        for task_data in template_tasks:
            if task_data["type_code"] in task_types_dict:
                template_task = CalendarTemplateTask(
                    template_id=standard_template.id,
                    task_type_id=task_types_dict[task_data["type_code"]],
                    day_offset=task_data["day_offset"],
                    order_index=task_data["order_index"]
                )
                db.add(template_task)
                print(f"✅ Creada tarea de template: {task_data['type_code']} - Día {task_data['day_offset']}")
        db.commit()
    else:
        print(f"⏭️  Las tareas del template ya existen")

def main():
    """Función principal"""
    print("🌱 Iniciando población de datos del calendario...")
    
    # Crear tablas
    create_tables()
    print("✅ Tablas creadas/verificadas")
    
    # Obtener sesión de base de datos
    db = SessionLocal()
    
    try:
        # Poblar tipos de tareas
        print("\n📋 Poblando tipos de tareas del calendario...")
        seed_calendar_task_types(db)
        
        # Poblar templates
        print("\n📋 Poblando templates del calendario...")
        seed_calendar_templates(db)
        
        # Poblar tareas de templates
        print("\n📋 Poblando tareas de templates...")
        seed_calendar_template_tasks(db)
        
        print("\n🎉 ¡Población de datos del calendario completada exitosamente!")
        
    except Exception as e:
        print(f"❌ Error durante la población de datos: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    main()
