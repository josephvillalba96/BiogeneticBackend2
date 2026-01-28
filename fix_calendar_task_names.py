#!/usr/bin/env python3
"""
Script para corregir los nombres de tareas que tienen "Día X" en lugar de los nombres correctos
de calendar_task_types (opus, fiv, civ, d3, d5, prevision, informe).
"""

from sqlalchemy.orm import Session
from app.database.base import engine, SessionLocal
from app.models.calendar import CalendarTask, CalendarTaskType
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_calendar_task_names():
    """Corrige los task_name y task_type de las tareas existentes"""
    db = SessionLocal()
    
    try:
        logger.info("🔧 Iniciando corrección de nombres de tareas del calendario...")
        
        # Obtener todos los tipos de tareas disponibles
        task_types = db.query(CalendarTaskType).all()
        task_type_dict = {tt.type_code: tt for tt in task_types}
        
        logger.info(f"📋 Tipos de tareas encontrados: {len(task_types)}")
        for tt in task_types:
            logger.info(f"   - {tt.name} (code: {tt.type_code})")
        
        # Obtener todas las tareas del calendario
        all_tasks = db.query(CalendarTask).all()
        logger.info(f"📅 Total de tareas a verificar: {len(all_tasks)}")
        
        updated_count = 0
        
        for task in all_tasks:
            updated = False
            
            # Verificar si task_name tiene el formato "Día X"
            if task.task_name.startswith("Día "):
                # Intentar mapear a un task_type existente
                if task.task_type in task_type_dict:
                    correct_name = task_type_dict[task.task_type].name
                    task.task_name = correct_name
                    updated = True
                    logger.info(f"✅ Corregido task_name: '{task.task_name}' -> '{correct_name}'")
                else:
                    logger.warning(f"⚠️  task_type '{task.task_type}' no encontrado en calendar_task_types")
            
            # Verificar si summary tiene el formato "Día X" o "Nombre - Día X"
            if task.summary.startswith("Día ") or " - Día " in task.summary:
                # Intentar mapear a un task_type existente
                if task.task_type in task_type_dict:
                    correct_name = task_type_dict[task.task_type].name
                    task.summary = correct_name
                    updated = True
                    logger.info(f"✅ Corregido summary: '{task.summary}' -> '{correct_name}'")
            
            # También corregir la descripción si contiene "Día X para"
            if task.description and "Día " in task.description and " para " in task.description:
                if task.task_type in task_type_dict:
                    correct_name = task_type_dict[task.task_type].name
                    client_part = task.description.split(" para ", 1)[1] if " para " in task.description else ""
                    task.description = f"{correct_name} para {client_part}"
                    updated = True
                    logger.info(f"✅ Corregido description: '{task.description}'")
            
            if updated:
                updated_count += 1
        
        # Guardar cambios
        if updated_count > 0:
            db.commit()
            logger.info(f"🎉 Se corrigieron {updated_count} tareas exitosamente")
        else:
            logger.info("ℹ️  No se encontraron tareas que necesiten corrección")
            
        # Verificación final
        logger.info("\n🔍 Verificación final:")
        remaining_issues = db.query(CalendarTask).filter(
            CalendarTask.task_name.like("Día %")
        ).count()
        if remaining_issues > 0:
            logger.warning(f"⚠️  Aún quedan {remaining_issues} tareas con nombres 'Día X'")
        else:
            logger.info("✅ Todas las tareas tienen nombres correctos")
            
    except Exception as e:
        db.rollback()
        logger.error(f"❌ Error durante la corrección: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    fix_calendar_task_names()