from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from datetime import timedelta
from app.services import role_service
from datetime import datetime

from app.models.opus import ProduccionEmbrionaria
from app.schemas.produccion_embrionaria import (
    ProduccionEmbrionariaCreate,
    ProduccionEmbrionariaUpdate,
)

from app.models.user import User
from sqlalchemy import or_
from app.models.input_output import Output



def get_all(
    db: Session,
    current_user: User,
    fecha_inicio: datetime = None,
    fecha_fin: datetime = None,
    query: str = None
):
    # 🔐 Verificar si es administrador
    if not role_service.is_admin(current_user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No autorizado")

    q = db.query(ProduccionEmbrionaria).join(ProduccionEmbrionaria.cliente)

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

    return q.all()



def get_by_id(db: Session, produccion_id: int):
    produccion = db.query(ProduccionEmbrionaria).filter(ProduccionEmbrionaria.id == produccion_id).first()
    if not produccion:
        raise HTTPException(status_code=404, detail="Producción no encontrada")
    return produccion


def get_by_cliente(db: Session, cliente_id: int):
    return db.query(ProduccionEmbrionaria).filter(ProduccionEmbrionaria.cliente_id == cliente_id).all()


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


def get_bulls_summary_by_produccion(db: Session, produccion_id: int):
    from app.models.bull import Bull
    from app.models.input_output import Output, Input
    from app.models.opus import Opus
    from sqlalchemy.orm import joinedload
    from sqlalchemy import func

    # Obtener la producción embrionaria con outputs y opus relacionados
    produccion = db.query(ProduccionEmbrionaria).options(
        joinedload(ProduccionEmbrionaria.outputs).joinedload(Output.input).joinedload(Input.bull),
        joinedload(ProduccionEmbrionaria.opus)
    ).filter(ProduccionEmbrionaria.id == produccion_id).first()
    if not produccion:
        raise HTTPException(status_code=404, detail="Producción embrionaria no encontrada")

    # Mapear outputs a toros
    toro_data = {}
    for output in produccion.outputs:
        bull = output.input.bull
        if not bull:
            continue
        bull_id = bull.id
        if bull_id not in toro_data:
            toro_data[bull_id] = {
                "nombre_toro": bull.name,
                "raza_toro": bull.race.name if bull.race else None,
                "numero_registro": bull.registration_number,
                "cantidad_semen_trabajada": 0,
                "cantidad_total_ctv": 0,
                "produccion_total":0,
                "donantes": set()
            }
        # 4. Suma de quantity_output
        toro_data[bull_id]["cantidad_semen_trabajada"] += float(output.quantity_output)

    # Mapear opus a toros para sumar ctv y donantes
    for opus in produccion.opus:
        bull_id = opus.toro_id
        if bull_id in toro_data:
            # 5. Suma de ctv
            toro_data[bull_id]["cantidad_total_ctv"] += opus.ctv
            toro_data[bull_id]["produccion_total"] += opus.prevision
            # 7. Donantes distintos
            toro_data[bull_id]["donantes"].add(opus.donante_code)

    # Construir el array de respuesta
    result = []
    for bull_id, data in toro_data.items():
        cantidad_semen = data["cantidad_semen_trabajada"]
        cantidad_ctv = data["cantidad_total_ctv"]
        produccion_total = data["produccion_total"]
        porcentaje = (produccion_total / cantidad_ctv * 100) if cantidad_ctv else 0
        result.append({
            "nombre_toro": data["nombre_toro"],
            "raza_toro": data["raza_toro"],
            "numero_registro": data["numero_registro"],
            "cantidad_semen_trabajada": cantidad_semen,
            "cantidad_total_ctv": cantidad_ctv,
            "produccion_total":produccion_total,
            "porcentaje": porcentaje,
            "total_donadoras": len(data["donantes"])
        })
    return result
