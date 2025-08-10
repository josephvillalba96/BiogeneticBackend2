from sqlalchemy.orm import Session, joinedload
from app.models.opus import Transferencia, ReportTransfer
from app.models.user import User
from app.schemas.transfer_schema import (
    TransferenciaCreate, TransferenciaUpdate, ReportTransferCreate, ReportTransferUpdate
)
from fastapi import HTTPException, status
from sqlalchemy import or_, func
from typing import List, Optional, Dict, Any

def create_transferencia(db: Session, transferencia_in: TransferenciaCreate) -> Transferencia:
    transferencia = Transferencia(
        fecha_transferencia=transferencia_in.fecha_transferencia,
        veterinario_responsable=transferencia_in.veterinario_responsable,
        fecha=transferencia_in.fecha,
        lugar=transferencia_in.lugar,
        finca=transferencia_in.finca,
        observacion=transferencia_in.observacion,
        produccion_embrionaria_id=transferencia_in.produccion_embrionaria_id,
        cliente_id=transferencia_in.cliente_id,
        initial_report=transferencia_in.initial_report if transferencia_in.initial_report is not None else True
    )
    db.add(transferencia)
    db.flush()  # Para obtener el id antes de agregar reportes
    
    if transferencia_in.reportes:
        for reporte_in in transferencia_in.reportes:
            # Solo crear reportes que tengan datos válidos (no vacíos)
            if (reporte_in.donadora and reporte_in.raza_donadora and 
                reporte_in.toro and reporte_in.toro_raza):
                reporte = ReportTransfer(
                    **reporte_in.dict(),
                    transferencia_id=transferencia.id
                )
                db.add(reporte)
    
    db.commit()
    db.refresh(transferencia)
    return transferencia

def get_transferencia(db: Session, transferencia_id: int) -> Optional[Transferencia]:
    return db.query(Transferencia).options(joinedload(Transferencia.cliente)).filter(Transferencia.id == transferencia_id).first()

def get_transferencias_by_produccion(db: Session, produccion_id: int) -> List[Dict[str, Any]]:
    """
    Obtiene transferencias por producción embrionaria con información del cliente
    """
    query = db.query(
        Transferencia,
        User.full_name.label('cliente_nombre'),
        User.number_document.label('cliente_documento'),
        User.email.label('cliente_correo')
    ).join(
        User, Transferencia.cliente_id == User.id
    ).options(
        joinedload(Transferencia.reportes)  # Cargar los reportes asociados
    ).filter(Transferencia.produccion_embrionaria_id == produccion_id)
    
    results = query.all()
    
    # Formatear resultados
    transferencias_list = []
    for row in results:
        transferencia = row[0]
        # Formatear los reportes
        reportes = []
        for reporte in transferencia.reportes:
            reportes.append({
                "id": reporte.id,
                "donadora": reporte.donadora,
                "raza_donadora": reporte.raza_donadora,
                "toro": reporte.toro,
                "toro_raza": reporte.toro_raza,
                "estado": reporte.estado,
                "receptora": reporte.receptora,
                "horario": reporte.horario,
                "dx": reporte.dx,
                "dxx": reporte.dxx,
                "dxxx": reporte.dxxx,
                "transferencia_id": reporte.transferencia_id,
                "created_at": reporte.created_at,
                "updated_at": reporte.updated_at
            })
            
        transferencia_data = {
            "id": transferencia.id,
            "fecha_transferencia": transferencia.fecha_transferencia,
            "veterinario_responsable": transferencia.veterinario_responsable,
            "fecha": transferencia.fecha,
            "lugar": transferencia.lugar,
            "finca": transferencia.finca,
            "observacion": transferencia.observacion,
            "produccion_embrionaria_id": transferencia.produccion_embrionaria_id,
            "cliente_id": transferencia.cliente_id,
            "initial_report": transferencia.initial_report,
            "cliente_nombre": row.cliente_nombre,
            "cliente_documento": row.cliente_documento,
            "cliente_correo": row.cliente_correo,
            "created_at": transferencia.created_at,
            "updated_at": transferencia.updated_at,
            "reportes": reportes  # Incluir la lista de reportes
        }
        transferencias_list.append(transferencia_data)
    
    return transferencias_list

def get_transferencias_paginated(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None
) -> Dict[str, Any]:
    """
    Obtiene transferencias paginadas con búsqueda por documento, nombre o correo del cliente
    """
    # Consulta base simple de transferencias
    base_query = db.query(Transferencia)
    
    # Si hay búsqueda, filtrar por cliente
    if search:
        # Buscar cliente que coincida con el término de búsqueda
        clientes_ids = db.query(User.id).filter(
            or_(
                User.number_document.like(f"%{search}%"),
                User.full_name.like(f"%{search}%"),
                User.email.like(f"%{search}%")
            )
        ).subquery()
        
        base_query = base_query.filter(Transferencia.cliente_id.in_(clientes_ids))
    
    # Contar total
    total_count = base_query.count()
    
    # Aplicar paginación y ordenamiento
    transferencias = base_query.order_by(Transferencia.fecha_transferencia.desc()).offset(skip).limit(limit).all()
    
    # Formatear resultados - solo datos básicos de transferencia
    transferencias_list = []
    for transferencia in transferencias:
        # Obtener información del cliente
        cliente = db.query(User).filter(User.id == transferencia.cliente_id).first()
        
        transferencia_data = {
            "id": transferencia.id,
            "fecha_transferencia": transferencia.fecha_transferencia,
            "veterinario_responsable": transferencia.veterinario_responsable,
            "fecha": transferencia.fecha,
            "lugar": transferencia.lugar,
            "finca": transferencia.finca,
            "observacion": transferencia.observacion,
            "produccion_embrionaria_id": transferencia.produccion_embrionaria_id,
            "cliente_id": transferencia.cliente_id,
            "initial_report": transferencia.initial_report,
            "cliente_nombre": cliente.full_name if cliente else "",
            "cliente_documento": cliente.number_document if cliente else "",
            "cliente_correo": cliente.email if cliente else "",
            "created_at": transferencia.created_at,
            "updated_at": transferencia.updated_at
        }
        transferencias_list.append(transferencia_data)
    
    return {
        "total": total_count,
        "items": transferencias_list,
        "page": skip // limit + 1 if limit else 1,
        "pages": (total_count + limit - 1) // limit if limit else 1
    }

def update_transferencia(db: Session, transferencia_id: int, transferencia_in: TransferenciaUpdate) -> Optional[Transferencia]:
    transferencia = db.query(Transferencia).filter(Transferencia.id == transferencia_id).first()
    if not transferencia:
        return None
    
    # Actualizar campos de la transferencia (excepto reportes)
    update_data = transferencia_in.dict(exclude_unset=True, exclude={'reportes'})
    for field, value in update_data.items():
        setattr(transferencia, field, value)
    
    # Manejar actualización de reportes si se proporcionan
    if transferencia_in.reportes is not None:
        # Eliminar todos los reportes existentes de esta transferencia
        db.query(ReportTransfer).filter(ReportTransfer.transferencia_id == transferencia_id).delete()
        
        # Crear los nuevos reportes
        for reporte_data in transferencia_in.reportes:
            # Solo crear reportes que tengan datos válidos (no vacíos)
            if (reporte_data.donadora and reporte_data.raza_donadora and 
                reporte_data.toro and reporte_data.toro_raza):
                nuevo_reporte = ReportTransfer(
                    **reporte_data.dict(),
                    transferencia_id=transferencia_id
                )
                db.add(nuevo_reporte)
    
    db.commit()
    db.refresh(transferencia)
    return transferencia

def delete_transferencia(db: Session, transferencia_id: int) -> bool:
    transferencia = db.query(Transferencia).filter(Transferencia.id == transferencia_id).first()
    if not transferencia:
        return False
    db.delete(transferencia)
    db.commit()
    return True

def create_report_transfer(db: Session, transferencia_id: int, reporte_in: ReportTransferCreate) -> ReportTransfer:
    reporte = ReportTransfer(**reporte_in.dict(), transferencia_id=transferencia_id)
    db.add(reporte)
    db.commit()
    db.refresh(reporte)
    return reporte

def update_report_transfer(db: Session, reporte_id: int, reporte_in: ReportTransferUpdate) -> Optional[ReportTransfer]:
    reporte = db.query(ReportTransfer).filter(ReportTransfer.id == reporte_id).first()
    if not reporte:
        return None
    for field, value in reporte_in.dict(exclude_unset=True).items():
        setattr(reporte, field, value)
    db.commit()
    db.refresh(reporte)
    return reporte

def delete_report_transfer(db: Session, reporte_id: int) -> bool:
    reporte = db.query(ReportTransfer).filter(ReportTransfer.id == reporte_id).first()
    if not reporte:
        return False
    db.delete(reporte)
    db.commit()
    return True 