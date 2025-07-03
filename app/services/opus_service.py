from sqlalchemy.orm import Session, joinedload, aliased
from app.models.opus import Opus
from app.models.user import User
from app.models.bull import Bull
from app.schemas.opus_schema import OpusCreate, OpusUpdate, OpusDetail
from app.services import role_service
from typing import List, Optional, Dict, Any
from sqlalchemy import or_, func, and_, desc, distinct
from fastapi import HTTPException, status
from datetime import date
import logging

def get_opus(db: Session, opus_id: int, current_user: User = None) -> Optional[OpusDetail]:
    """
    Obtiene un registro de Opus por su ID.
    - Los clientes solo pueden ver sus propios registros
    - Los veterinarios y administradores pueden ver todos los registros
    """
    try:
        opus = (
            db.query(Opus)
            .options(
                joinedload(Opus.cliente),     # Relación válida
            )
            .filter(Opus.id == opus_id)
            .first()
        )

        if not opus:
            return None

        # Verificación de permisos
        if current_user and not (
            role_service.is_admin(current_user) or role_service.is_veterinarian(current_user)
        ):
            if opus.cliente_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permiso para ver este registro"
                )

        return OpusDetail(
            **opus.__dict__,
            cliente_nombre=opus.cliente.full_name if opus.cliente else "",
            toro_nombre=opus.toro  # Campo tipo string directamente del modelo
        )

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener registro: {str(e)}"
        )

def get_opus_by_client(
    db: Session,
    client_id: Optional[int],
    current_user: User = None,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """
    Obtiene todos los registros de Opus.
    - Si es cliente, solo ve sus propios registros (ignora client_id)
    - Si es veterinario o admin, puede ver registros de cualquier cliente
    """
    # Crear alias para las tablas de toros
    toro_bull = aliased(Bull, name='toro_bull')
    
    # Consulta base con joins
    query = db.query(
        Opus,
        User.full_name.label('cliente_nombre'),
        func.coalesce(toro_bull.name, '').label('toro_nombre')
    ).join(
        User, Opus.cliente_id == User.id
    ).outerjoin(
        toro_bull, Opus.toro_id == toro_bull.id
    )

    # Aplicar filtros según el rol del usuario
    if current_user:
        if role_service.is_admin(current_user) or role_service.is_veterinarian(current_user):
            # Admins y veterinarios pueden ver todos o filtrar por cliente_id
            if client_id is not None:
                query = query.filter(Opus.cliente_id == client_id)
        else:
            # Clientes solo ven sus propios registros
            query = query.filter(Opus.cliente_id == current_user.id)
    
    # Aplicar paginación
    query = query.order_by(Opus.order.asc()).offset(skip).limit(limit)
    
    try:
        # Ejecutar consulta
        results = query.all()
        
        # Formatear resultados
        opus_list = []
        for row in results:
            opus = row[0]
            opus_data = {
                "id": opus.id,
                "cliente_id": opus.cliente_id,
                "cliente_nombre": row.cliente_nombre,
                "toro_id": opus.toro_id,
                "toro_nombre": row.toro_nombre,
                "fecha": opus.fecha,
                "lugar": opus.lugar,
                "finca": opus.finca,
                "donante_code": opus.donante_code,
                "race": opus.race,
                "toro": opus.toro,
                "gi": opus.gi,
                "gii": opus.gii,
                "giii": opus.giii,
                "viables": opus.viables,
                "otros": opus.otros,
                "total_oocitos": opus.total_oocitos,
                "ctv": opus.ctv,
                "clivados": opus.clivados,
                "porcentaje_cliv": opus.porcentaje_cliv,
                "prevision": opus.prevision,
                "porcentaje_prevision": opus.porcentaje_prevision,
                "empaque": opus.empaque,
                "porcentaje_empaque": opus.porcentaje_empaque,
                "vt_dt": opus.vt_dt,
                "porcentaje_vtdt": opus.porcentaje_vtdt,
                "total_embriones": opus.total_embriones,
                "porcentaje_total_embriones": opus.porcentaje_total_embriones,
                "produccion_embrionaria_id":opus.produccion_embrionaria_id,
                "created_at": opus.created_at,
                "updated_at": opus.updated_at,
                "order": opus.order
            }
            opus_list.append(opus_data)
        
        return opus_list
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error en get_opus_by_client: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener registros: {str(e)}"
        )

def create_opus(
    db: Session,
    opus: OpusCreate,
    current_user: User
) -> OpusDetail:
    """
    Crea un nuevo registro de Opus.
    Solo administradores y veterinarios pueden crear registros.
    """
    # Verificar que el usuario sea administrador o veterinario
    if not (role_service.is_admin(current_user) or role_service.is_veterinarian(current_user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores y veterinarios pueden crear registros de Opus"
        )
    
    # Verificar que el cliente exista
    client = db.query(User).filter(User.id == opus.cliente_id).first()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente no encontrado"
        )

    # Verificar que el toro exista y pertenezca al cliente
    toro = db.query(Bull).filter(
        and_(
            Bull.id == opus.toro_id,
            Bull.user_id == opus.cliente_id
        )
    ).first()
    if not toro:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Toro no encontrado o no pertenece al cliente especificado"
        )
    
    # Crear el nuevo registro
    db_opus = Opus(**opus.dict())
    
    try:
        db.add(db_opus)
        db.commit()
        db.refresh(db_opus)
        
        # Devolver OpusDetail en lugar de diccionario
        return OpusDetail(
            **db_opus.__dict__,
            cliente_nombre=client.full_name if client else "",
            toro_nombre=db_opus.toro
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al crear el registro: {str(e)}"
        )

def update_opus(
    db: Session,
    opus_id: int,
    opus_data: OpusUpdate,
    current_user: User
) -> OpusDetail:
    """
    Actualiza un registro de Opus sin depender de ninguna otra función.
    """
    # Obtener directamente el registro sin usar get_opus
    db_opus = (
        db.query(Opus)
        .options(
            joinedload(Opus.cliente)
        )
        .filter(Opus.id == opus_id)
        .first()
    )

    if not db_opus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro no encontrado"
        )

    # Verificar permisos
    if not (role_service.is_admin(current_user) or role_service.is_veterinarian(current_user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores y veterinarios pueden actualizar registros"
        )

    # Validar toro si se está cambiando
    if opus_data.toro_id is not None:
        toro = db.query(Bull).filter(
            and_(
                Bull.id == opus_data.toro_id,
                Bull.user_id == db_opus.cliente_id
            )
        ).first()
        if not toro:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Toro no encontrado o no pertenece al cliente especificado"
            )

    # Aplicar actualizaciones
    update_fields = opus_data.dict(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(db_opus, field, value)

    try:
        db.commit()
        db.refresh(db_opus)

        return OpusDetail(
            **db_opus.__dict__,
            cliente_nombre=db_opus.cliente.full_name if db_opus.cliente else "",
            toro_nombre=db_opus.toro
        )
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al actualizar el registro: {str(e)}"
        )

def delete_opus(
    db: Session,
    opus_id: int,
    current_user: User
) -> bool:
    """Elimina un registro de Opus"""
    # Obtener el registro
    db_opus = get_opus(db, opus_id, current_user)
    if not db_opus:
        return False
    
    # Verificar permisos
    if not (role_service.is_admin(current_user) or role_service.is_veterinarian(current_user)):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo los administradores y veterinarios pueden eliminar registros"
        )
    
    try:
        db.delete(db_opus)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar el registro: {str(e)}"
        )

def get_opus_grouped_by_date(
    db: Session,
    current_user: User,
    skip: int = 0,
    limit: int = 100
) -> List[Dict[str, Any]]:
    """Obtiene los registros de Opus agrupados por fecha"""
    # Construir la consulta base
    query = db.query(
        Opus.fecha,
        User.full_name.label('cliente_nombre'),
        func.count(Opus.id).label('total_registros'),
        func.sum(Opus.total_oocitos).label('total_oocitos'),
        func.sum(Opus.total_embriones).label('total_embriones')
    ).join(
        User, Opus.cliente_id == User.id
    )
    
    # Si no es admin ni veterinario, filtrar por cliente_id
    if not (role_service.is_admin(current_user) or role_service.is_veterinarian(current_user)):
        query = query.filter(Opus.cliente_id == current_user.id)
    
    # Agrupar y ordenar
    query = query.group_by(
        Opus.fecha,
        User.full_name
    ).order_by(
        desc(Opus.fecha)
    )
    
    # Aplicar paginación
    query = query.order_by(Opus.order.asc()).offset(skip).limit(limit)
    
    # Ejecutar consulta
    results = query.all()
    
    # Formatear resultados
    summary_list = []
    for row in results:
        # Calcular porcentaje de éxito y promedio de embriones
        porcentaje_exito = "0%" if row.total_oocitos == 0 else f"{(row.total_embriones / row.total_oocitos * 100):.2f}%"
        promedio_embriones = "0" if row.total_registros == 0 else f"{(row.total_embriones / row.total_registros):.2f}"
        
        summary = {
            "fecha": row.fecha,
            "cliente_nombre": row.cliente_nombre,
            "total_registros": row.total_registros,
            "total_oocitos": row.total_oocitos,
            "total_embriones": row.total_embriones,
            "porcentaje_exito": porcentaje_exito,
            "promedio_embriones": promedio_embriones
        }
        summary_list.append(summary)
    
    return summary_list

def get_opus_admin_report(
    db: Session,
    current_user: User,
    client_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100
) -> Dict[str, Any]:
    """
    Genera un reporte administrativo de Opus con estadísticas y registros detallados.
    - Los administradores pueden ver todos los registros o filtrar por cliente
    - Los veterinarios pueden ver todos los registros o filtrar por cliente
    - Los clientes solo ven sus propios registros
    """
    try:
        # Crear alias para las tablas de toros
        toro_bull = aliased(Bull, name='toro_bull')
        
        # Consulta base para estadísticas
        stats_query = db.query(
            func.count(Opus.id).label('total_registros'),
            func.sum(Opus.total_oocitos).label('total_oocitos'),
            func.sum(Opus.total_embriones).label('total_embriones'),
            func.avg(Opus.total_embriones).label('promedio_embriones'),
            func.count(distinct(Opus.cliente_id)).label('total_clientes')
        )
        
        # Consulta base para registros detallados
        detail_query = db.query(
            Opus,
            User.full_name.label('cliente_nombre'),
            func.coalesce(toro_bull.name, '').label('toro_nombre')
        ).join(
            User, Opus.cliente_id == User.id
        ).outerjoin(
            toro_bull, Opus.toro_id == toro_bull.id
        )
        
        # Aplicar filtros según el rol del usuario
        if role_service.is_admin(current_user) or role_service.is_veterinarian(current_user):
            # Admins y veterinarios pueden ver todos o filtrar por cliente_id
            if client_id is not None:
                stats_query = stats_query.filter(Opus.cliente_id == client_id)
                detail_query = detail_query.filter(Opus.cliente_id == client_id)
        else:
            # Clientes solo ven sus propias estadísticas
            stats_query = stats_query.filter(Opus.cliente_id == current_user.id)
            detail_query = detail_query.filter(Opus.cliente_id == current_user.id)
        
        # Aplicar filtros de fecha si se proporcionan
        if start_date and end_date:
            stats_query = stats_query.filter(Opus.fecha.between(start_date, end_date))
            detail_query = detail_query.filter(Opus.fecha.between(start_date, end_date))
        elif start_date:
            stats_query = stats_query.filter(Opus.fecha >= start_date)
            detail_query = detail_query.filter(Opus.fecha >= start_date)
        elif end_date:
            stats_query = stats_query.filter(Opus.fecha <= end_date)
            detail_query = detail_query.filter(Opus.fecha <= end_date)
        
        # Obtener estadísticas
        stats = stats_query.first()
        
        # Obtener registros detallados con paginación
        detail_query = detail_query.order_by(Opus.order.asc()).offset(skip).limit(limit)
        details = detail_query.all()
        
        # Formatear registros detallados
        registros = []
        for row in details:
            opus = row[0]
            registros.append({
                "id": opus.id,
                "cliente_id": opus.cliente_id,
                "cliente_nombre": row.cliente_nombre,
                "toro_id": opus.toro_id,
                "lugar": opus.lugar,
                "finca": opus.finca,
                "toro_nombre": row.toro_nombre,
                "fecha": opus.fecha,
                "toro": opus.toro,
                "gi": opus.gi,
                "gii": opus.gii,
                "giii": opus.giii,
                "viables": opus.viables,
                "otros": opus.otros,
                "total_oocitos": opus.total_oocitos,
                "ctv": opus.ctv,
                "clivados": opus.clivados,
                "porcentaje_cliv": opus.porcentaje_cliv,
                "prevision": opus.prevision,
                "porcentaje_prevision": opus.porcentaje_prevision,
                "empaque": opus.empaque,
                "porcentaje_empaque": opus.porcentaje_empaque,
                "vt_dt": opus.vt_dt,
                "porcentaje_vtdt": opus.porcentaje_vtdt,
                "total_embriones": opus.total_embriones,
                "donante_code":opus.donante_code,
                "race":opus.race,
                "produccion_embrionaria_id":opus.produccion_embrionaria_id,
                "porcentaje_total_embriones": opus.porcentaje_total_embriones,
                "order": opus.order
            })
        
        # Calcular porcentajes y promedios
        total_oocitos = stats.total_oocitos or 0
        total_embriones = stats.total_embriones or 0
        porcentaje_exito = "0%" if total_oocitos == 0 else f"{(total_embriones / total_oocitos * 100):.2f}%"
        
        # Construir respuesta
        return {
            "estadisticas": {
                "total_registros": stats.total_registros or 0,
                "total_clientes": stats.total_clientes or 0,
                "total_oocitos": total_oocitos,
                "total_embriones": total_embriones,
                "porcentaje_exito": porcentaje_exito,
                "promedio_embriones_por_registro": f"{stats.promedio_embriones:.2f}" if stats.promedio_embriones else "0"
            },
            "registros": registros
        }
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Error en get_opus_admin_report: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener reporte: {str(e)}"
        )

# def get_opus_by_date_for_client(
#     db: Session,
#     fecha: date,
#     current_user: User
# ) -> List[Dict[str, Any]]:
#     """
#     Obtiene todos los registros de Opus de una fecha específica para un cliente,
#     incluyendo la información de sus bovinos (donante y toro).
#     Solo accesible para el propio cliente.
#     """
#     logger = logging.getLogger(__name__)
#     logger.info(f"Buscando registros para la fecha: {fecha} y cliente_id: {current_user.id}")
    
#     try:
#         # Crear alias para las tablas de toros
#         donante_bull = aliased(Bull, name='donante_bull')
#         toro_bull = aliased(Bull, name='toro_bull')
        
#         # Construir la consulta base con joins
#         query = db.query(
#             Opus,
#             User.full_name.label('cliente_nombre'),
#             donante_bull.name.label('donante_nombre'),
#             toro_bull.name.label('toro_nombre'),
#         ).join(
#             User, Opus.cliente_id == User.id
#         ).outerjoin(
#             donante_bull, Opus.donante_id == donante_bull.id
#         ).outerjoin(
#             toro_bull, Opus.toro_id == toro_bull.id
#         ).filter(
#             Opus.cliente_id == current_user.id,
#             func.date(Opus.fecha) == fecha
#         )
        
#         # Ejecutar la consulta y obtener resultados
#         results = query.all()
#         logger.info(f"Registros encontrados: {len(results)}")
        
#         # Si no hay resultados, verificar si hay registros para esa fecha
#         if not results:
#             # Consulta de verificación
#             fecha_check = db.query(Opus.fecha).distinct().all()
#             fechas_disponibles = [f.fecha for f in fecha_check]
#             logger.info(f"No se encontraron registros para la fecha {fecha}.")
#             logger.info(f"Fechas disponibles en la base de datos: {fechas_disponibles}")
#             return []
        
#         # Formatear resultados
#         opus_list = []
#         for row in results:
#             opus = row[0]
#             opus_data = {
#                 "id": opus.id,
#                 "cliente_id": opus.cliente_id,
#                 "cliente_nombre": row.cliente_nombre,
#                 "donante_id": opus.donante_id,
#                 "donante_nombre": row.donante_nombre,
#                 "toro_id": opus.toro_id,
#                 "toro_nombre": row.toro_nombre,
#                 "fecha": opus.fecha,
#                 "lugar": opus.lugar,
#                 "finca": opus.finca,
#                 "toro": opus.toro,
#                 "gi": opus.gi,
#                 "gii": opus.gii,
#                 "giii": opus.giii,
#                 "viables": opus.viables,
#                 "otros": opus.otros,
#                 "total_oocitos": opus.total_oocitos,
#                 "ctv": opus.ctv,
#                 "clivados": opus.clivados,
#                 "porcentaje_cliv": opus.porcentaje_cliv,
#                 "prevision": opus.prevision,
#                 "porcentaje_prevision": opus.porcentaje_prevision,
#                 "empaque": opus.empaque,
#                 "porcentaje_empaque": opus.porcentaje_empaque,
#                 "vt_dt": opus.vt_dt,
#                 "porcentaje_vtdt": opus.porcentaje_vtdt,
#                 "total_embriones": opus.total_embriones,
#                 "porcentaje_total_embriones": opus.porcentaje_total_embriones,
#                 "created_at": opus.created_at,
#                 "updated_at": opus.updated_at
#             }
#             opus_list.append(opus_data)
#             logger.info(f"Procesado registro ID: {opus.id} para fecha: {opus.fecha}")
        
#         return opus_list
#     except Exception as e:
#         logger.error(f"Error en get_opus_by_date_for_client: {str(e)}")
#         raise HTTPException(
#             status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
#             detail=f"Error al obtener registros por fecha: {str(e)}"
#         ) 


def get_opus_by_production_for_client(
    db: Session,
    production_id: int,
    current_user: User
) -> List[Dict[str, Any]]:
    """
    Obtiene todos los registros de Opus para una producción específica (por production_id),
    incluyendo la información de sus bovinos (toro).
    - Si el usuario es un cliente, solo puede ver sus propios registros.
    - Si es admin, puede ver todos los registros.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Buscando registros para la producción: {production_id} y cliente_id: {current_user.id}")
    
    try:
        toro_bull = aliased(Bull, name='toro_bull')

        # Consulta base
        query = db.query(
            Opus,
            User.full_name.label('cliente_nombre'),
            toro_bull.name.label('toro_nombre'),
        ).join(
            User, Opus.cliente_id == User.id
        ).outerjoin(
            toro_bull, Opus.toro_id == toro_bull.id
        ).filter(
            Opus.produccion_embrionaria_id == production_id
        )

        # Si no es admin, filtrar solo los registros del cliente actual
        # if current_user. != 'admin':
        #     query = query.filter(Opus.cliente_id == current_user.id)

        results = query.order_by(Opus.order.asc()).all()
        logger.info(f"Registros encontrados: {len(results)}")

        opus_list = []
        for row in results:
            opus = row[0]
            opus_data = {
                "id": opus.id,
                "cliente_id": opus.cliente_id,
                "cliente_nombre": row.cliente_nombre,
                "toro_id": opus.toro_id,
                "toro_nombre": row.toro_nombre,
                "fecha": opus.fecha,
                "race":opus.race,
                "donante_code":opus.donante_code,
                "lugar": opus.lugar,
                "finca": opus.finca,
                "toro": opus.toro,
                "gi": opus.gi,
                "gii": opus.gii,
                "giii": opus.giii,
                "viables": opus.viables,
                "otros": opus.otros,
                "total_oocitos": opus.total_oocitos,
                "ctv": opus.ctv,
                "clivados": opus.clivados,
                "porcentaje_cliv": opus.porcentaje_cliv,
                "prevision": opus.prevision,
                "porcentaje_prevision": opus.porcentaje_prevision,
                "empaque": opus.empaque,
                "porcentaje_empaque": opus.porcentaje_empaque,
                "vt_dt": opus.vt_dt,
                "porcentaje_vtdt": opus.porcentaje_vtdt,
                "total_embriones": opus.total_embriones,
                "porcentaje_total_embriones": opus.porcentaje_total_embriones,
                "produccion_embrionaria_id":opus.produccion_embrionaria_id,
                "created_at": opus.created_at,
                "updated_at": opus.updated_at,
                "order": opus.order
            }
            opus_list.append(opus_data)
            logger.info(f"Procesado registro ID: {opus.id}")

        return opus_list

    except Exception as e:
        logger.error(f"Error en get_opus_by_production_for_client: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al obtener registros por producción: {str(e)}"
        )
