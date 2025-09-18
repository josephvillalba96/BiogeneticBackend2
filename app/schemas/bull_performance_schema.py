from typing import List, Optional
from pydantic import BaseModel, Field

class BullPerformanceItem(BaseModel):
    """Esquema para un item de rendimiento de toro"""
    toro: str = Field(..., description="Nombre del toro")
    raza: str = Field(..., description="Raza del toro")
    registro: Optional[str] = Field(None, description="Número de registro del toro")
    lote: Optional[str] = Field(None, description="Número de lote del toro")
    donantes_fertilizadas: int = Field(..., description="Número de donantes fertilizadas")
    ovocitos_civ: int = Field(..., description="Total de ovocitos CIV")
    porcentaje_produccion: float = Field(..., description="Porcentaje de producción")

class BullPerformanceSummary(BaseModel):
    """Esquema para el resumen de rendimiento de toros"""
    total_toros: int = Field(..., description="Total de toros")
    total_donantes_fertilizadas: int = Field(..., description="Total de donantes fertilizadas")
    total_ovocitos_civ: int = Field(..., description="Total de ovocitos CIV")
    promedio_porcentaje_produccion: float = Field(..., description="Promedio del porcentaje de producción")
    promedio_donantes_por_toro: float = Field(..., description="Promedio de donantes por toro")
    promedio_ovocitos_por_toro: float = Field(..., description="Promedio de ovocitos por toro")

class BullPerformanceResponse(BaseModel):
    """Esquema para la respuesta completa del servicio de rendimiento"""
    data: List[BullPerformanceItem] = Field(..., description="Lista de rendimiento de toros")
    summary: BullPerformanceSummary = Field(..., description="Resumen estadístico")
    total_records: int = Field(..., description="Total de registros devueltos")
    page: int = Field(..., description="Página actual")
    page_size: int = Field(..., description="Tamaño de página")
