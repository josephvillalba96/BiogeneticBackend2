from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import timedelta
from app.services import role_service
from datetime import datetime

from app.models.opus import ProduccionEmbrionaria, Opus
from app.schemas.produccion_embrionaria import (
    ProduccionEmbrionariaCreate,
    ProduccionEmbrionariaUpdate,
)

from app.models.user import User
from sqlalchemy import or_, func
from app.models.input_output import Output, Input, InputStatus
from app.models.relationships import produccion_embrionaria_output
import logging


def _process_produccion_with_opus(produccion, total_opus):
    """
    Función auxiliar para procesar una producción embrionaria y agregar el conteo de opus.
    
    Args:
        produccion: Objeto ProduccionEmbrionaria
        total_opus: Número total de opus relacionados
    
    Returns:
        Dict con los datos de la producción incluyendo total_opus
    """
    return {
        'id': produccion.id,
        'cliente_id': produccion.cliente_id,
        'fecha_opu': produccion.fecha_opu,
        'lugar': produccion.lugar,
        'finca': produccion.finca,
        'hora_inicio': produccion.hora_inicio,
        'hora_final': produccion.hora_final,
        'envase': produccion.envase,
        'fecha_transferencia': produccion.fecha_transferencia,
        'observacion': produccion.observacion,
        'created_at': produccion.created_at,
        'updated_at': produccion.updated_at,
        'total_opus': total_opus,
        'cliente_nombre': produccion.cliente.full_name if produccion.cliente else None,
        'outputs': []
    }



def get_all(
    db: Session,
    current_user: User,
    fecha_inicio: datetime = None,
    fecha_fin: datetime = None,
    query: str = None,
    skip: int = 0,
    limit: int = 100
):
    # 🔐 Verificar si es administrador
    if not role_service.is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    from sqlalchemy import func

    # Construir query con conteo de opus
    q = db.query(
        ProduccionEmbrionaria,
        func.count(ProduccionEmbrionaria.opus).label('total_opus')
    ).join(ProduccionEmbrionaria.cliente).outerjoin(
        ProduccionEmbrionaria.opus
    )

    # 🗓️ Filtros por fecha
    if fecha_inicio:
        q = q.filter(ProduccionEmbrionaria.fecha_opu >= fecha_inicio)
    if fecha_fin:
        q = q.filter(ProduccionEmbrionaria.fecha_opu <= fecha_fin)

    # 🔍 Filtro por nombre o documento
    if query:
        q = q.filter(
            or_(
                ProduccionEmbrionaria.cliente.has(User.full_name.ilike(f"%{query}%")),
                ProduccionEmbrionaria.cliente.has(User.number_document.ilike(f"%{query}%")),
                ProduccionEmbrionaria.cliente.has(User.email.ilike(f"%{query}%"))
            )
        )

    # 📄 Aplicar paginación y ordenamiento
    q = q.group_by(ProduccionEmbrionaria.id).order_by(ProduccionEmbrionaria.created_at.desc()).offset(skip).limit(limit)

    # Procesar resultados para incluir total_opus
    results = q.all()
    result = []
    for produccion, total_opus in results:
        result.append(_process_produccion_with_opus(produccion, total_opus))
    
    return result



def get_by_id(db: Session, produccion_id: int):
    produccion = db.query(ProduccionEmbrionaria).filter(ProduccionEmbrionaria.id == produccion_id).first()
    if not produccion:
        raise HTTPException(status_code=404, detail="Producción no encontrada")
    return produccion


def get_by_cliente(db: Session, cliente_id: int, skip: int = 0, limit: int = 100):
    """
    Obtiene todas las producciones embrionarias de un cliente específico por su ID.
    Incluye el conteo de opus relacionados para cada producción.
    
    Args:
        db: Sesión de base de datos
        cliente_id: ID del cliente
        skip: Número de registros a omitir (paginación)
        limit: Número máximo de registros a devolver (paginación)
    
    Returns:
        Lista de producciones embrionarias del cliente con total_opus calculado
    """
    from sqlalchemy import func
    
    # Obtener producciones con conteo de opus
    producciones = db.query(
        ProduccionEmbrionaria,
        func.count(ProduccionEmbrionaria.opus).label('total_opus')
    ).outerjoin(
        ProduccionEmbrionaria.opus
    ).filter(
        ProduccionEmbrionaria.cliente_id == cliente_id
    ).group_by(
        ProduccionEmbrionaria.id
    ).order_by(
        ProduccionEmbrionaria.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    # Procesar resultados para incluir total_opus
    result = []
    for produccion, total_opus in producciones:
        result.append(_process_produccion_with_opus(produccion, total_opus))
    
    return result


def get_by_cliente_id(db: Session, cliente_id: int, skip: int = 0, limit: int = 100):
    """
    Obtiene todas las producciones embrionarias de un cliente específico por su ID.
    Incluye el conteo de opus relacionados para cada producción.
    
    Args:
        db: Sesión de base de datos
        cliente_id: ID del cliente
        skip: Número de registros a omitir (paginación)
        limit: Número máximo de registros a devolver (paginación)
    
    Returns:
        Lista de producciones embrionarias del cliente con total_opus calculado
    """
    from sqlalchemy.orm import joinedload
    from sqlalchemy import func
    
    # Obtener producciones con conteo de opus
    producciones = db.query(
        ProduccionEmbrionaria,
        func.count(ProduccionEmbrionaria.opus).label('total_opus')
    ).outerjoin(
        ProduccionEmbrionaria.opus
    ).filter(
        ProduccionEmbrionaria.cliente_id == cliente_id
    ).group_by(
        ProduccionEmbrionaria.id
    ).order_by(
        ProduccionEmbrionaria.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    # Procesar resultados para incluir total_opus
    result = []
    for produccion, total_opus in producciones:
        result.append(_process_produccion_with_opus(produccion, total_opus))
    
    return result


def create(db: Session, data: ProduccionEmbrionariaCreate):
    # Calcular fecha_transferencia
    fecha_transferencia = data.fecha_opu + timedelta(days=7)

    nueva_produccion = ProduccionEmbrionaria(
        cliente_id=data.cliente_id,
        fecha_opu=data.fecha_opu,
        lugar=data.lugar,
        finca=data.finca,
        hora_inicio=data.hora_inicio,
        hora_final=data.hora_final,
        envase=data.envase,
        fecha_transferencia=fecha_transferencia,
        observacion=data.observacion
    )

    if data.output_ids:
        outputs = db.query(Output).filter(Output.id.in_(data.output_ids)).all()
        if len(outputs) != len(data.output_ids):
            raise HTTPException(status_code=404, detail="One or more outputs not found")
        nueva_produccion.outputs.extend(outputs)

    db.add(nueva_produccion)
    db.commit()
    db.refresh(nueva_produccion)
    return nueva_produccion


def update(db: Session, produccion_id: int, data: ProduccionEmbrionariaUpdate):

    produccion = get_by_id(db, produccion_id)

    if "output_ids" in data.dict(exclude_unset=True):
        output_ids = data.dict(exclude_unset=True).pop("output_ids")
        if output_ids is not None:
            # Obtener los outputs actuales
            current_outputs = {output.id for output in produccion.outputs}
            # Filtrar los nuevos outputs que no están ya asociados
            new_output_ids = set(output_ids) - current_outputs
            if new_output_ids:
                new_outputs = db.query(Output).filter(Output.id.in_(new_output_ids)).all()
                if len(new_outputs) != len(new_output_ids):
                    raise HTTPException(status_code=404, detail="One or more outputs not found")
                produccion.outputs.extend(new_outputs)
            # No eliminamos los existentes, solo agregamos los nuevos
        # Si output_ids es una lista vacía, no hacemos nada (no borramos)

    for field, value in data.dict(exclude_unset=True).items():
        setattr(produccion, field, value)

    # Si se actualiza fecha_opu, recalcular fecha_transferencia si no fue pasada explícitamente
    if "fecha_opu" in data.dict(exclude_unset=True) and "fecha_transferencia" not in data.dict(exclude_unset=True):
        produccion.fecha_transferencia = produccion.fecha_opu + timedelta(days=7)

    db.commit()
    db.refresh(produccion)
    return produccion


def delete(db: Session, produccion_id: int):
    produccion = get_by_id(db, produccion_id)
    db.delete(produccion)
    db.commit()
    return {"ok": True}


def delete_with_rollback(db: Session, produccion_id: int):
    """
    Elimina una producción embrionaria restaurando todas las cantidades de inputs afectados.
    
    Este proceso realiza las siguientes acciones en orden:
    1. Obtiene todos los outputs relacionados a la producción embrionaria
    2. Restaura las cantidades tomadas de las distintas entradas que fueron afectadas
    3. Elimina todos los registros opus relacionados a la producción
    4. Elimina la producción embrionaria
    
    Args:
        db: Sesión de base de datos
        produccion_id: ID de la producción embrionaria a eliminar
    
    Returns:
        dict con status ok y mensaje de confirmación
    
    Raises:
        HTTPException: Si la producción no se encuentra o hay un error en el proceso
    """
    logger = logging.getLogger(__name__)
    
    try:
        # 1. Obtener la producción embrionaria
        produccion = db.query(ProduccionEmbrionaria).filter(
            ProduccionEmbrionaria.id == produccion_id
        ).first()
        
        if not produccion:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producción embrionaria no encontrada"
            )
        
        logger.info(f"Iniciando eliminación de producción embrionaria {produccion_id}")
        
        # 2. Obtener todos los outputs relacionados a esta producción
        outputs_query = db.query(Output).join(
            produccion_embrionaria_output,
            Output.id == produccion_embrionaria_output.c.output_id
        ).filter(
            produccion_embrionaria_output.c.produccion_embrionaria_id == produccion_id
        )
        
        outputs = outputs_query.all()
        logger.info(f"Outputs encontrados relacionados: {len(outputs)}")
        
        # 3. Restaurar las cantidades de los inputs
        inputs_to_update = {}
        
        for output in outputs:
            input_obj = output.input
            
            # Agrupar por input_id para evitar actualizaciones duplicadas
            if input_obj.id not in inputs_to_update:
                inputs_to_update[input_obj.id] = {
                    'input': input_obj,
                    'quantity_to_restore': 0
                }
            
            # Restar la cantidad del output de la cantidad tomada
            inputs_to_update[input_obj.id]['quantity_to_restore'] += float(output.quantity_output)
        
        # Actualizar cada input
        for input_id, data in inputs_to_update.items():
            input_obj = data['input']
            quantity_to_restore = data['quantity_to_restore']
            
            # Restar la cantidad tomada
            current_taken = float(input_obj.quantity_taken)
            new_taken = max(0, current_taken - quantity_to_restore)  # No puede ser negativo
            
            input_obj.quantity_taken = new_taken
            input_obj.total = float(input_obj.quantity_received) - new_taken
            
            # Actualizar el estado del input
            if new_taken >= float(input_obj.quantity_received):
                input_obj.status_id = InputStatus.completed
            elif new_taken > 0:
                input_obj.status_id = InputStatus.processing
            else:
                input_obj.status_id = InputStatus.pending
            
            logger.info(
                f"Input {input_id} actualizado: "
                f"quantity_taken={current_taken} -> {new_taken}, "
                f"total={input_obj.total}, status={input_obj.status_id.value}"
            )
        
        # 4. Eliminar las relaciones en la tabla intermedia produccion_embrionaria_output
        relaciones_eliminadas = db.execute(
            produccion_embrionaria_output.delete().where(
                produccion_embrionaria_output.c.produccion_embrionaria_id == produccion_id
            )
        ).rowcount
        
        logger.info(f"Relaciones eliminadas de produccion_embrionaria_output: {relaciones_eliminadas}")
        
        # 5. Eliminar los outputs de la base de datos
        output_ids = [output.id for output in outputs]
        outputs_deleted = db.query(Output).filter(Output.id.in_(output_ids)).delete(synchronize_session=False)
        
        logger.info(f"Outputs eliminados: {outputs_deleted}")
        
        # 6. Eliminar los registros opus relacionados
        opus_deleted = db.query(Opus).filter(
            Opus.produccion_embrionaria_id == produccion_id
        ).delete()
        
        logger.info(f"Registros OPUS eliminados: {opus_deleted}")
        
        # 7. Eliminar la producción embrionaria
        db.delete(produccion)
        
        # Commit todos los cambios
        db.commit()
        
        logger.info(f"Producción embrionaria {produccion_id} eliminada exitosamente")
        
        return {
            "ok": True,
            "message": f"Producción embrionaria eliminada exitosamente. "
                       f"Outputs eliminados: {outputs_deleted}, "
                       f"Inputs actualizados: {len(inputs_to_update)}, "
                       f"Registros OPUS eliminados: {opus_deleted}, "
                       f"Relaciones eliminadas: {relaciones_eliminadas}"
        }
        
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al eliminar producción embrionaria {produccion_id}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al eliminar la producción embrionaria: {str(e)}"
        )


def get_bulls_summary_by_produccion(db: Session, produccion_id: int):
    """
    Obtiene un resumen de toros para una producción embrionaria específica.
    Calcula la cantidad de semen trabajada SOLO de los outputs asociados a esta producción
    usando la tabla intermedia produccion_embrionaria_output.
    
    Args:
        db: Sesión de base de datos
        produccion_id: ID de la producción embrionaria
    
    Returns:
        Lista de resúmenes de toros con datos específicos de esta producción
    """
    from app.models.bull import Bull
    from app.models.input_output import Output, Input
    from app.models.opus import Opus
    from app.models.relationships import produccion_embrionaria_output
    from sqlalchemy.orm import joinedload
    from sqlalchemy import func

    # Verificar que la producción existe
    produccion = db.query(ProduccionEmbrionaria).filter(ProduccionEmbrionaria.id == produccion_id).first()
    if not produccion:
        raise HTTPException(status_code=404, detail="Producción embrionaria no encontrada")

    # Inicializar diccionario para agrupar datos por toro
    toro_data = {}

    # 1. Obtener OUTPUTS asociados a esta producción específica usando la tabla intermedia
    outputs_query = db.query(Output).join(
        produccion_embrionaria_output,
        Output.id == produccion_embrionaria_output.c.output_id
    ).join(
        Input, Output.input_id == Input.id
    ).join(
        Bull, Input.bull_id == Bull.id
    ).filter(
        produccion_embrionaria_output.c.produccion_embrionaria_id == produccion_id
    )

    for output in outputs_query.all():
        bull = output.input.bull
        if not bull:
            continue
            
        bull_id = bull.id
        if bull_id not in toro_data:
            toro_data[bull_id] = {
                "nombre_toro": bull.name,
                "raza_toro": bull.race.name if bull.race else None,
                "numero_registro": bull.registration_number,
                "cantidad_semen_trabajada": 0.0,  # Solo de esta producción
                "cantidad_total_ctv": 0,
                "produccion_total": 0,
                "donantes": set()
            }
        
        # Sumar SOLO la cantidad de semen de los outputs asociados a esta producción
        toro_data[bull_id]["cantidad_semen_trabajada"] += float(output.quantity_output)

    # 2. Procesar OPUS asociados a esta producción específica
    opus_query = db.query(Opus).filter(Opus.produccion_embrionaria_id == produccion_id)
    
    for opus in opus_query.all():
        bull_id = opus.toro_id
        bull = db.query(Bull).filter(Bull.id == bull_id).first()
        if not bull:
            continue
            
        if bull_id not in toro_data:
            toro_data[bull_id] = {
                "nombre_toro": bull.name,
                "raza_toro": bull.race.name if bull.race else None,
                "numero_registro": bull.registration_number,
                "cantidad_semen_trabajada": 0.0,  # Puede ser 0 si no hay outputs
                "cantidad_total_ctv": 0,
                "produccion_total": 0,
                "donantes": set()
            }
        
        # Sumar datos de opus específicos de esta producción
        toro_data[bull_id]["cantidad_total_ctv"] += opus.ctv
        toro_data[bull_id]["produccion_total"] += opus.prevision
        toro_data[bull_id]["donantes"].add(opus.donante_code)

    # 3. Construir respuesta final
    result = []
    for bull_id, data in toro_data.items():
        cantidad_semen = data["cantidad_semen_trabajada"]
        cantidad_ctv = data["cantidad_total_ctv"]
        produccion_total = data["produccion_total"]
        
        # Calcular porcentaje basado en CTV de esta producción específica
        porcentaje = (produccion_total / cantidad_ctv * 100) if cantidad_ctv > 0 else 0
        
        result.append({
            "nombre_toro": data["nombre_toro"],
            "raza_toro": data["raza_toro"],
            "numero_registro": data["numero_registro"],
            "cantidad_semen_trabajada": round(cantidad_semen, 2),  # Redondear a 2 decimales
            "cantidad_total_ctv": cantidad_ctv,
            "produccion_total": produccion_total,
            "porcentaje": round(porcentaje, 2),
            "total_donadoras": len(data["donantes"])
        })
    
    return result
