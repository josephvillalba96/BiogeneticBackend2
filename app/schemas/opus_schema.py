from pydantic import BaseModel, Field
from datetime import date, datetime
from typing import Optional

# str = str  # Ajustado a tu uso actual

class OpusBase(BaseModel):
    cliente_id: int
    toro_id: int
    fecha: date
    toro: str
    lugar: Optional[str]
    finca: Optional[str]
    race: Optional[str]
    donante_code: Optional[str]
    order: Optional[int] = None

    gi: int = Field(ge=0)
    gii: int = Field(ge=0)
    giii: int = Field(ge=0)
    viables: int = Field(ge=0)
    otros: int = Field(ge=0)
    total_oocitos: int = Field(ge=0)
    ctv: int = Field(ge=0)
    clivados: int = Field(ge=0)
    porcentaje_cliv: str

    prevision: int = Field(ge=0)
    porcentaje_prevision: str

    empaque: int = Field(ge=0)
    porcentaje_empaque: str

    vt_dt: Optional[int] = Field(default=None, ge=0)
    porcentaje_vtdt: Optional[str] = None

    total_embriones: int = Field(ge=0)
    porcentaje_total_embriones: str
    produccion_embrionaria_id:int

class OpusCreate(OpusBase):
    pass

class OpusUpdate(BaseModel):
    fecha: Optional[date] = None
    toro: Optional[str] = None
    toro_id: Optional[int] = None
    lugar: Optional[str] = None
    finca: Optional[str] = None
    race: Optional[str] = None
    donante_code: Optional[str] = None
    order: Optional[int] = None

    gi: Optional[int] = Field(default=None, ge=0)
    gii: Optional[int] = Field(default=None, ge=0)
    giii: Optional[int] = Field(default=None, ge=0)
    viables: Optional[int] = Field(default=None, ge=0)
    otros: Optional[int] = Field(default=None, ge=0)
    total_oocitos: Optional[int] = Field(default=None, ge=0)
    ctv: Optional[int] = Field(default=None, ge=0)
    clivados: Optional[int] = Field(default=None, ge=0)
    porcentaje_cliv: Optional[str] = None

    prevision: Optional[int] = Field(default=None, ge=0)
    porcentaje_prevision: Optional[str] = None

    empaque: Optional[int] = Field(default=None, ge=0)
    porcentaje_empaque: Optional[str] = None

    vt_dt: Optional[int] = Field(default=None, ge=0)
    porcentaje_vtdt: Optional[str] = None

    total_embriones: Optional[int] = Field(default=None, ge=0)
    porcentaje_total_embriones: Optional[str] = None

class OpusInDB(OpusBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OpusDetail(OpusInDB):
    cliente_nombre: str
    toro_nombre: str

    class Config:
        orm_mode = True

class OpusDateSummary(BaseModel):
    fecha: date
    cliente_nombre: str
    total_registros: int
    total_oocitos: int
    total_embriones: int
    porcentaje_exito: str
    promedio_embriones: str

    class Config:
        from_attributes = True

class OpusDateDetail(OpusDetail):
    """Esquema para mostrar detalles de Opus por fecha"""
    pass
