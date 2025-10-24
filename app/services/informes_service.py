from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
import json
import os
from datetime import datetime, timedelta, date
from fastapi import HTTPException

from app.models.opus import ProduccionEmbrionaria, Opus
from app.models.bull import Bull
from app.models.user import User
from app.models.input_output import Output, Input
from app.models.relationships import produccion_embrionaria_output
from app.schemas.opus_schema import OpusSchema


def _get_templates_env() -> Environment:
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml"]),
        enable_async=False,
    )
    # Añadir filtro tojson para compatibilidad con plantilla
    def json_serializer(obj):
        """Serializador personalizado para JSON que maneja objetos date y datetime"""
        if isinstance(obj, (date, datetime)):
            return obj.strftime('%d/%m/%Y')
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")
    
    env.filters["tojson"] = lambda obj: json.dumps(obj, ensure_ascii=False, default=json_serializer)
    return env


def fetch_produccion_context(
    db: Session,
    produccion_id: int,
    current_user: Optional[User] = None,
) -> Dict[str, Any]:
    """
    Obtiene la Producción Embrionaria y construye el contexto requerido por la plantilla
    embrionary_production.html (production, registros, totales, resumen_toros, muestra_info, transfer_date, current_user).
    """
    produccion_db = (
        db.query(ProduccionEmbrionaria)
        .filter(ProduccionEmbrionaria.id == produccion_id)
        .first()
    )
    if not produccion_db:
        raise HTTPException(status_code=404, detail="Producción no encontrada")

    cliente = produccion_db.cliente
    registros_orm = db.query(Opus).filter(Opus.produccion_embrionaria_id == produccion_id).order_by((Opus.order == None).desc(), Opus.order.asc()).all()

    registros_schema = [OpusSchema.from_orm(r) for r in registros_orm]

    for registro in registros_schema:
        if not registro.toro_nombre:
            toro_db = db.query(Bull).filter(Bull.id == registro.toro_id).first()
            if toro_db:
                registro.toro_nombre = toro_db.name
                registro.race = toro_db.race.name if toro_db.race else "N/A"

    # Inicializar resumen de toros con datos de Opus
    # Cada registro de Opus es una muestra diferente, no se agrupan
    resumen_toros = []
    for r in registros_schema:
        # Crear una entrada separada para cada registro (muestra)
        toro_entry = {
            'toro_nombre': r.toro_nombre,
            'race': r.race,
            'numero_registro': r.donante_code,
            'cantidad_semen_trabajada': 0.0,  # Se llenará con los outputs
            'total_donadoras': 1,  # Cada registro es una donante
            'cantidad_total_ctv': r.ctv,
            'produccion_total': r.prevision,
            'porcentaje': 0.0,  # Se calculará después
            'total_embriones': r.total_embriones,
            'total_oocitos': r.total_oocitos
        }
        resumen_toros.append(toro_entry)

    # Obtener los outputs directamente relacionados con esta producción embrionaria
    # usando la tabla intermedia produccion_embrionaria_output
    outputs_relacionados = db.query(Output).join(
        produccion_embrionaria_output, Output.id == produccion_embrionaria_output.c.output_id
    ).filter(
        produccion_embrionaria_output.c.produccion_embrionaria_id == produccion_id
    ).all()
    
    # Crear un diccionario para mapear outputs por toro
    outputs_por_toro = {}
    for output in outputs_relacionados:
        bull = output.input.bull
        if not bull:
            continue
            
        if bull.name not in outputs_por_toro:
            outputs_por_toro[bull.name] = []
        outputs_por_toro[bull.name].append(output)
    
    # Asignar outputs a las muestras correspondientes
    # Distribuir los outputs entre las muestras del mismo toro
    for toro_entry in resumen_toros:
        toro_nombre = toro_entry['toro_nombre']
        if toro_nombre in outputs_por_toro:
            outputs_toro = outputs_por_toro[toro_nombre]
            # Si hay múltiples outputs, distribuir entre las muestras
            if len(outputs_toro) > 0:
                # Por simplicidad, asignar el primer output disponible
                # En un caso real, esto debería basarse en alguna lógica de asociación
                toro_entry['cantidad_semen_trabajada'] = float(outputs_toro[0].quantity_output)
                # Remover el output usado para evitar duplicados
                outputs_toro.pop(0)

    # Calcular porcentajes para cada muestra
    # Fórmula: (Producción total × 100) / Cultivados
    for toro_data in resumen_toros:
        if toro_data['cantidad_total_ctv'] > 0:
            toro_data['porcentaje'] = round((toro_data['produccion_total'] * 100) / toro_data['cantidad_total_ctv'], 2)
        else:
            toro_data['porcentaje'] = 0.0
    
    # Calcular totales para la plantilla
    totales = {
        "gi": 0,
        "gii": 0,
        "giii": 0,
        "viables": 0,
        "otros": 0,
        "total_oocitos": 0,
        "ctv": 0,
        "clivados": 0,
        "prevision": 0,
        "empaque": 0,
        "vt_dt": 0,
    }
    
    for r in registros_schema:
        totales["gi"] += r.gi
        totales["gii"] += r.gii
        totales["giii"] += r.giii
        totales["viables"] += r.viables
        totales["otros"] += r.otros
        totales["total_oocitos"] += r.total_oocitos
        totales["ctv"] += r.ctv
        totales["clivados"] += r.clivados
        totales["prevision"] += r.prevision
        totales["empaque"] += r.empaque
        totales["vt_dt"] += (r.vt_dt or 0)
    
    # Calcular porcentajes agregados
    def pct(numer: int, denom: int) -> int:
        return int(round((numer * 100) / (denom if denom > 0 else 1)))
    
    totales["porcentaje_cliv"] = f"{pct(totales['clivados'], totales['ctv'])}%"
    totales["porcentaje_prevision"] = f"{pct(totales['prevision'], totales['ctv'])}%"
    totales["porcentaje_empaque"] = f"{pct(totales['empaque'], totales['ctv'])}%"
    totales["porcentaje_vtdt"] = f"{pct(totales['vt_dt'], totales['ctv'])}%"
    
    # Realizar cálculos adicionales para el resumen
    total_oocitos = sum(r.total_oocitos for r in registros_schema) if registros_schema else 0
    total_clivados = sum(r.clivados for r in registros_schema) if registros_schema else 0
    total_embriones = sum(r.total_embriones for r in registros_schema) if registros_schema else 0
    promedio_porcentaje_cliv = (total_clivados / total_oocitos * 100) if total_oocitos > 0 else 0
    promedio_porcentaje_total_embriones = (total_embriones / total_oocitos * 100) if total_oocitos > 0 else 0

    fecha_transferencia = None
    if produccion_db.fecha_opu:
        fecha_transferencia = produccion_db.fecha_opu + timedelta(days=8)

    context = {
        "production": produccion_db,
        "cliente": cliente,
        "registros": [r.model_dump() for r in registros_schema], # Ahora se convierte a dict
        "totales": totales,
        "resumen_toros": resumen_toros,
        "total_oocitos": total_oocitos,
        "total_clivados": total_clivados,
        "total_embriones": total_embriones,
        "promedio_porcentaje_cliv": f"{promedio_porcentaje_cliv:.2f}%",
        "promedio_porcentaje_total_embriones": f"{promedio_porcentaje_total_embriones:.2f}%",
        "current_date": datetime.now().strftime("%d/%m/%Y"),
        "fecha_transferencia": fecha_transferencia.strftime("%d/%m/%Y") if fecha_transferencia else "N/A",
    }
    
    return context


def render_produccion_html(db: Session, produccion_id: int, current_user: Optional[User]) -> str:
    env = _get_templates_env()
    template = env.get_template("embrionary_production.html")
    ctx = fetch_produccion_context(db, produccion_id, current_user)
    html = template.render(**ctx)
    return html


