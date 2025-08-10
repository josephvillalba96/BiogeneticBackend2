from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database.base import get_db
from app.services import transfer_service
from app.schemas.transfer_schema import (
    TransferenciaCreate, TransferenciaUpdate, TransferenciaInDB, TransferenciaDetail,
    ReportTransferCreate, ReportTransferUpdate, ReportTransferInDB
)
from typing import List, Dict, Any, Optional

router = APIRouter(
    prefix="/transferencias",
    tags=["transferencias"],
    responses={404: {"description": "No encontrado"}},
)

@router.get("/", response_model=Dict[str, Any])
def get_transferencias_paginated(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=1000),
    search: Optional[str] = Query(default=None, description="Búsqueda por documento, nombre o correo del cliente"),
    db: Session = Depends(get_db)
):
    """
    Obtiene transferencias paginadas con búsqueda opcional por documento, nombre o correo del cliente.
    Retorna:
    - total: número total de registros
    - items: lista de transferencias en la página actual
    - page: número de página actual
    - pages: número total de páginas
    """
    return transfer_service.get_transferencias_paginated(db, skip, limit, search)

@router.post("/", response_model=TransferenciaInDB, status_code=status.HTTP_201_CREATED)
def create_transferencia(transferencia: TransferenciaCreate, db: Session = Depends(get_db)):
    return transfer_service.create_transferencia(db, transferencia)

@router.get("/{transferencia_id}", response_model=TransferenciaInDB)
def get_transferencia(transferencia_id: int, db: Session = Depends(get_db)):
    transferencia = transfer_service.get_transferencia(db, transferencia_id)
    if not transferencia:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")
    return transferencia

@router.get("/by-produccion/{produccion_id}", response_model=List[Dict[str, Any]])
def get_transferencias_by_produccion(produccion_id: int, db: Session = Depends(get_db)):
    return transfer_service.get_transferencias_by_produccion(db, produccion_id)

@router.put("/{transferencia_id}", response_model=TransferenciaInDB)
def update_transferencia(transferencia_id: int, transferencia: TransferenciaUpdate, db: Session = Depends(get_db)):
    updated = transfer_service.update_transferencia(db, transferencia_id, transferencia)
    if not updated:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")
    return updated

@router.delete("/{transferencia_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transferencia(transferencia_id: int, db: Session = Depends(get_db)):
    success = transfer_service.delete_transferencia(db, transferencia_id)
    if not success:
        raise HTTPException(status_code=404, detail="Transferencia no encontrada")
    return {"message": "Transferencia eliminada"}

# ReportTransfer endpoints
@router.post("/{transferencia_id}/reportes", response_model=ReportTransferInDB, status_code=status.HTTP_201_CREATED)
def create_report_transfer(transferencia_id: int, reporte: ReportTransferCreate, db: Session = Depends(get_db)):
    return transfer_service.create_report_transfer(db, transferencia_id, reporte)

@router.put("/reportes/{reporte_id}", response_model=ReportTransferInDB)
def update_report_transfer(reporte_id: int, reporte: ReportTransferUpdate, db: Session = Depends(get_db)):
    updated = transfer_service.update_report_transfer(db, reporte_id, reporte)
    if not updated:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return updated

@router.delete("/reportes/{reporte_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_report_transfer(reporte_id: int, db: Session = Depends(get_db)):
    success = transfer_service.delete_report_transfer(db, reporte_id)
    if not success:
        raise HTTPException(status_code=404, detail="Reporte no encontrado")
    return {"message": "Reporte eliminado"} 