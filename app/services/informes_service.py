from sqlalchemy.orm import Session
from typing import Dict, Any, List, Optional
from jinja2 import Environment, FileSystemLoader, select_autoescape
import json
import os

from app.models.opus import ProduccionEmbrionaria, Opus
from app.models.bull import Bull
from app.models.user import User


def _get_templates_env() -> Environment:
    templates_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")
    env = Environment(
        loader=FileSystemLoader(templates_dir),
        autoescape=select_autoescape(["html", "xml"]),
        enable_async=False,
    )
    # Añadir filtro tojson para compatibilidad con plantilla
    env.filters["tojson"] = lambda obj: json.dumps(obj, ensure_ascii=False)
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
    production: Optional[ProduccionEmbrionaria] = (
        db.query(ProduccionEmbrionaria)
        .filter(ProduccionEmbrionaria.id == produccion_id)
        .first()
    )
    if production is None:
        raise ValueError("Producción embrionaria no encontrada")

    # Cargar registros Opus asociados
    opus_registros: List[Opus] = (
        db.query(Opus)
        .filter(Opus.produccion_embrionaria_id == produccion_id)
        # MySQL no soporta NULLS FIRST; emulación: NULL primero, luego valor, luego id
        .order_by((Opus.order == None).desc(), Opus.order.asc(), Opus.id.asc())
        .all()
    )

    # Construir mapa de toros por id para completar nombres faltantes
    toro_ids = {r.toro_id for r in opus_registros if getattr(r, "toro_id", None)}
    bull_by_id: Dict[int, Dict[str, Any]] = {}
    if toro_ids:
        for bid, bname, breg in (
            db.query(Bull.id, Bull.name, Bull.registration_number)
            .filter(Bull.id.in_(toro_ids))
            .all()
        ):
            bull_by_id[int(bid)] = {"name": bname or "", "registration_number": breg or ""}

    # Adaptar registros para la plantilla
    registros: List[Dict[str, Any]] = []
    totales: Dict[str, Any] = {
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

    for r in opus_registros:
        toro_nombre_val = (r.toro or "").strip()
        if not toro_nombre_val and getattr(r, "toro_id", None) in bull_by_id:
            toro_nombre_val = bull_by_id[r.toro_id]["name"]
        registros.append({
            "donante_code": r.donante_code,
            "race": r.race,
            "toro_nombre": toro_nombre_val,
            "gi": r.gi,
            "gii": r.gii,
            "giii": r.giii,
            "viables": r.viables,
            "otros": r.otros,
            "total_oocitos": r.total_oocitos,
            "ctv": r.ctv,
            "clivados": r.clivados,
            "porcentaje_cliv": r.porcentaje_cliv,
            "prevision": r.prevision,
            "porcentaje_prevision": r.porcentaje_prevision,
            "empaque": r.empaque,
            "porcentaje_empaque": r.porcentaje_empaque,
            "vt_dt": r.vt_dt or 0,
            "porcentaje_vtdt": r.porcentaje_vtdt or "0",
        })

        # Sumar totales
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

    # Derivar porcentajes agregados a partir de totales
    def pct(numer: int, denom: int) -> int:
        return int(round((numer * 100) / (denom if denom > 0 else 1)))

    totales["porcentaje_cliv"] = f"{pct(totales['clivados'], totales['ctv'])}%"
    totales["porcentaje_prevision"] = f"{pct(totales['prevision'], totales['ctv'])}%"
    totales["porcentaje_empaque"] = f"{pct(totales['empaque'], totales['ctv'])}%"
    totales["porcentaje_vtdt"] = f"{pct(totales['vt_dt'], totales['ctv'])}%"

    # Resumen de toros básico a partir de Opus
    resumen_toros: List[Dict[str, Any]] = []
    by_toro: Dict[str, Dict[str, Any]] = {}
    for r in opus_registros:
        key_val = (r.toro or "").strip()
        if not key_val and getattr(r, "toro_id", None) in bull_by_id:
            key_val = bull_by_id[r.toro_id]["name"]
        key = key_val
        if key not in by_toro:
            by_toro[key] = {
                "toro_nombre": key_val,
                "race": r.race,
                # Si existe registro del toro lo usamos, si no dejamos el donante_code
                "numero_registro": bull_by_id.get(getattr(r, "toro_id", None), {}).get("registration_number") or getattr(r, "donante_code", ""),
                "cantidad_semen_trabajada": 0.0,
                "total_donadoras": 0,
                "cantidad_total_ctv": 0.0,
                "produccion_total": 0,
                "porcentaje": 0.0,
            }
        by_toro[key]["total_donadoras"] += 1
        by_toro[key]["cantidad_total_ctv"] += r.ctv
        by_toro[key]["produccion_total"] += r.prevision
    for v in by_toro.values():
        v["porcentaje"] = pct(int(v["produccion_total"]), int(v["cantidad_total_ctv"]))
        resumen_toros.append(v)

    context: Dict[str, Any] = {
        "production": production,
        "current_user": current_user,
        "transfer_date": production.fecha_transferencia,
        "registros": registros,
        "totales": totales,
        "resumen_toros": resumen_toros,
        "muestra_info": None,  # Opcional; no siempre disponible
    }
    return context


def render_produccion_html(db: Session, produccion_id: int, current_user: Optional[User]) -> str:
    env = _get_templates_env()
    template = env.get_template("embrionary_production.html")
    ctx = fetch_produccion_context(db, produccion_id, current_user)
    html = template.render(**ctx)
    return html


