from sqlalchemy.orm import Session
from sqlalchemy import text, func
from app.models.bull import Bull, Race
from app.models.opus import Opus
from app.models.user import User
from typing import List, Dict, Any, Optional
import logging

# Configurar logger
logger = logging.getLogger(__name__)

def get_bull_performance(
    db: Session,
    client_id: Optional[int] = None,
    query: Optional[str] = None,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Obtiene el rendimiento de los toros basado en la consulta SQL proporcionada.
    
    Parámetros:
    - client_id: ID del cliente para filtrar toros
    - query: Búsqueda general por lote, nombre del toro o número de registro
    - skip: Número de registros a omitir (paginación)
    - limit: Número máximo de registros a devolver (paginación)
    
    Retorna una lista de diccionarios con el rendimiento de cada toro.
    """
    
    # Construir la consulta base
    base_query = """
    SELECT 
        t.name AS toro,
        r.name AS raza,
        t.registration_number AS registro,
        t.lote,
        COUNT(o.id) AS donantes_fertilizadas,
        SUM(o.total_oocitos) AS ovocitos_civ,
        ROUND(
            (SUM(o.prevision) * 100.0 / NULLIF(SUM(o.ctv),0)), 
            2
        ) AS porcentaje_produccion
    FROM opus o
    JOIN bulls t ON t.id = o.toro_id
    JOIN races r ON t.race_id = r.id
    """
    
    # Agregar filtros WHERE
    where_conditions = []
    params = {}
    
    if client_id is not None:
        where_conditions.append("t.user_id = :client_id")
        params["client_id"] = client_id
    
    if query is not None:
        # Búsqueda general en lote, nombre del toro o número de registro
        where_conditions.append("""
            (t.lote LIKE :query OR 
             t.name LIKE :query OR 
             t.registration_number LIKE :query)
        """)
        params["query"] = f"%{query}%"
    
    # Agregar condiciones WHERE si existen
    if where_conditions:
        base_query += " WHERE " + " AND ".join(where_conditions)
    
    # Agregar GROUP BY y ORDER BY
    base_query += """
    GROUP BY t.name, t.race_id, t.lote, t.registration_number
    ORDER BY t.registration_number, t.lote
    """
    
    # Agregar paginación
    base_query += " LIMIT :limit OFFSET :skip"
    params["limit"] = limit
    params["skip"] = skip
    
    try:
        # Ejecutar la consulta
        result = db.execute(text(base_query), params)
        
        # Convertir resultados a lista de diccionarios
        performance_data = []
        for row in result:
            performance_data.append({
                "toro": row.toro,
                "raza": row.raza,
                "registro": row.registro,
                "lote": row.lote,
                "donantes_fertilizadas": row.donantes_fertilizadas,
                "ovocitos_civ": row.ovocitos_civ,
                "porcentaje_produccion": float(row.porcentaje_produccion) if row.porcentaje_produccion is not None else 0.0
            })
        
        logger.info(f"Consulta de rendimiento de toros ejecutada exitosamente. {len(performance_data)} registros encontrados.")
        return performance_data
        
    except Exception as e:
        logger.error(f"Error al ejecutar consulta de rendimiento de toros: {str(e)}")
        raise e

def get_bull_performance_summary(
    db: Session,
    client_id: Optional[int] = None,
    query: Optional[str] = None
) -> Dict[str, Any]:
    """
    Obtiene un resumen del rendimiento de toros.
    
    Parámetros:
    - client_id: ID del cliente para filtrar toros
    - query: Búsqueda general por lote, nombre del toro o número de registro
    
    Retorna estadísticas generales como total de toros, promedio de producción, etc.
    """
    
    # Consulta para obtener estadísticas generales
    summary_query = """
    SELECT 
        COUNT(DISTINCT t.id) AS total_toros,
        COUNT(o.id) AS total_donantes_fertilizadas,
        SUM(o.total_oocitos) AS total_ovocitos_civ,
        ROUND(
            (SUM(o.prevision) * 100.0 / NULLIF(SUM(o.ctv),0)), 
            2
        ) AS promedio_porcentaje_produccion
    FROM opus o
    JOIN bulls t ON t.id = o.toro_id
    JOIN races r ON t.race_id = r.id
    """
    
    # Agregar filtros WHERE
    where_conditions = []
    params = {}
    
    if client_id is not None:
        where_conditions.append("t.user_id = :client_id")
        params["client_id"] = client_id
    
    if query is not None:
        # Búsqueda general en lote, nombre del toro o número de registro
        where_conditions.append("""
            (t.lote LIKE :query OR 
             t.name LIKE :query OR 
             t.registration_number LIKE :query)
        """)
        params["query"] = f"%{query}%"
    
    # Agregar condiciones WHERE si existen
    if where_conditions:
        summary_query += " WHERE " + " AND ".join(where_conditions)
    
    try:
        # Ejecutar la consulta de resumen
        result = db.execute(text(summary_query), params)
        row = result.fetchone()
        
        if not row or row.total_toros == 0:
            return {
                "total_toros": 0,
                "total_donantes_fertilizadas": 0,
                "total_ovocitos_civ": 0,
                "promedio_porcentaje_produccion": 0.0,
                "promedio_donantes_por_toro": 0.0,
                "promedio_ovocitos_por_toro": 0.0
            }
        
        # Calcular promedios
        total_toros = row.total_toros
        total_donantes = row.total_donantes_fertilizadas
        total_ovocitos = row.total_ovocitos_civ
        promedio_porcentaje = float(row.promedio_porcentaje_produccion) if row.promedio_porcentaje_produccion is not None else 0.0
        promedio_donantes = total_donantes / total_toros if total_toros > 0 else 0
        promedio_ovocitos = total_ovocitos / total_toros if total_toros > 0 else 0
        
        return {
            "total_toros": total_toros,
            "total_donantes_fertilizadas": total_donantes,
            "total_ovocitos_civ": total_ovocitos,
            "promedio_porcentaje_produccion": round(promedio_porcentaje, 2),
            "promedio_donantes_por_toro": round(promedio_donantes, 2),
            "promedio_ovocitos_por_toro": round(promedio_ovocitos, 2)
        }
        
    except Exception as e:
        logger.error(f"Error al ejecutar consulta de resumen de rendimiento: {str(e)}")
        raise e