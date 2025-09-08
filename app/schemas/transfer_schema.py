from pydantic import BaseModel, Field
from datetime import date
from typing import Optional, List

class ReportTransferBase(BaseModel):
    donadora: str
    raza_donadora: str
    toro: str
    toro_raza: str
    estado: str
    receptora: str
    horario: str
    dx: str
    dxx: str
    dxxx: str

class ReportTransferCreate(ReportTransferBase):
    pass

class ReportTransferUpdate(BaseModel):
    donadora: Optional[str] = None
    raza_donadora: Optional[str] = None
    toro: Optional[str] = None
    toro_raza: Optional[str] = None
    estado: Optional[str] = None
    receptora: Optional[str] = None
    horario: Optional[str] = None
    dx: Optional[str] = None
    dxx: Optional[str] = None
    dxxx: Optional[str] = None

class ReportTransferInDB(ReportTransferBase):
    id: int
    transferencia_id: int
    class Config:
        from_attributes = True

class TransferenciaBase(BaseModel):
    fecha_transferencia: date
    veterinario_responsable: str
    fecha: date
    lugar: str
    finca: str
    observacion: Optional[str] = None
    produccion_embrionaria_id: int
    cliente_id: int
    initial_report: Optional[bool] = True

class TransferenciaCreate(TransferenciaBase):
    reportes: Optional[List[ReportTransferCreate]] = None

class TransferenciaUpdate(BaseModel):
    fecha_transferencia: Optional[date] = None
    veterinario_responsable: Optional[str] = None
    fecha: Optional[date] = None
    lugar: Optional[str] = None
    finca: Optional[str] = None
    observacion: Optional[str] = None
    produccion_embrionaria_id: Optional[int] = None
    cliente_id: Optional[int] = None
    initial_report: Optional[bool] = None
    reportes: Optional[List[ReportTransferUpdate]] = None

class TransferenciaInDB(TransferenciaBase):
    id: int
    reportes: Optional[List[ReportTransferInDB]] = None
    class Config:
        from_attributes = True

class TransferenciaDetail(TransferenciaInDB):
    cliente_nombre: Optional[str] = None
    cliente_documento: Optional[str] = None
    cliente_correo: Optional[str] = None
    class Config:
        from_attributes = True 