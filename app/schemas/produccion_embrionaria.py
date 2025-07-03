from pydantic import BaseModel, Field
from datetime import date, time, datetime
from typing import Optional, List
from .input_output_schema import OutputSchema

# Base para crear y reutilizar
class ProduccionEmbrionariaBase(BaseModel):
    cliente_id: int
    fecha_opu: date
    lugar: str
    finca: str
    hora_inicio: Optional[time] = None
    hora_final: Optional[time] = None
    output_ids: Optional[List[int]] = []
    envase: str
    fecha_transferencia: date  # Calculado como fecha_opu + 7 días

# Crear una nueva producción embrionaria
class ProduccionEmbrionariaCreate(ProduccionEmbrionariaBase):
    pass

# Actualizar producción embrionaria
class ProduccionEmbrionariaUpdate(BaseModel):
    fecha_opu: Optional[date] = None
    lugar: Optional[str] = None
    finca: Optional[str] = None
    hora_inicio: Optional[time] = None
    hora_final: Optional[time] = None
    envase: Optional[str] = None
    output_ids: Optional[List[int]] = None
    fecha_transferencia: Optional[date] = None

    class Config:
        orm_mode = True

# Datos internos del modelo (incluye ID y timestamps)
class ProduccionEmbrionariaInDB(ProduccionEmbrionariaBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        orm_mode=True
        from_attributes = True
        

# Vista detallada de la producción embrionaria (con nombres de entidades relacionadas)
class ProduccionEmbrionariaDetail(ProduccionEmbrionariaInDB):
    cliente_nombre: Optional[str] = None
    total_opus: Optional[int] = None
    outputs: List[OutputSchema] = []

    class Config:
        orm_mode = True
        from_attributes = True

# Resumen por fecha
class ProduccionEmbrionariaResumenPorFecha(BaseModel):
    fecha_opu: date
    cliente_nombre: str
    total_producciones: int
    total_opus: int

    class Config:
        from_attributes = True

# Detalle de la producción embrionaria con lista de opus asociados (opcional si lo necesitas)
from .opus_schema import OpusInDB

class ProduccionEmbrionariaWithOpus(ProduccionEmbrionariaDetail):
    opus: List[OpusInDB]
