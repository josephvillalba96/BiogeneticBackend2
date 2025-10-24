from pydantic import BaseModel, Field, EmailStr, field_validator
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.schemas.base_schema import BaseSchema

class FacturaItemBase(BaseModel):
    """Esquema base para items de factura"""
    nombre: str
    valor: Decimal = Field(..., description="Valor en pesos colombianos")
    
    @field_validator('valor')
    @classmethod
    def validate_decimal_places(cls, v):
        if v is not None:
            # Convertir int/float a Decimal si es necesario
            if isinstance(v, (int, float)):
                v = Decimal(str(v))
            # Redondear a 2 decimales
            return v.quantize(Decimal('0.01'))
        return v

class FacturaItemCreate(FacturaItemBase):
    """Esquema para crear un item de factura"""
    pass

class FacturaItemResponse(FacturaItemBase):
    """Esquema para respuesta de item de factura"""
    id: int
    
    class Config:
        from_attributes = True

class FacturacionBase(BaseModel):
    """Esquema base para facturación"""
    monto_pagar: Decimal = Field(..., description="Monto total a pagar en pesos colombianos")
    monto_base: Optional[Decimal] = Field(None, description="Monto base sin IVA")
    iva: Optional[Decimal] = Field(19.0, description="Porcentaje de IVA")
    valor_iva: Optional[Decimal] = Field(None, description="Valor del IVA calculado")
    descripcion: Optional[str] = Field(None, max_length=500, description="Descripción de la factura")
    fecha_vencimiento: Optional[datetime] = Field(None, description="Fecha límite de pago")
    cliente_id: int = Field(..., description="ID del cliente al que pertenece la factura")
    items: List[FacturaItemCreate] = Field(..., description="Lista de items de la factura")
    aplica_iva: bool = Field(True, description="Indica si aplica IVA a la factura")
    
    @field_validator('monto_pagar', 'monto_base', 'iva', 'valor_iva')
    @classmethod
    def validate_decimal_places(cls, v):
        if v is not None:
            return v.quantize(Decimal('0.01'))
        return v

class FacturacionCreate(BaseModel):
    """Esquema para crear una factura"""
    # Campos opcionales que se calculan automáticamente
    monto_pagar: Optional[Decimal] = Field(None, description="Monto total a pagar (se calcula automáticamente)")
    monto_base: Optional[Decimal] = Field(None, description="Monto base sin IVA (se calcula automáticamente)")
    iva: Optional[Decimal] = Field(19.0, description="Porcentaje de IVA")
    valor_iva: Optional[Decimal] = Field(None, description="Valor del IVA (se calcula automáticamente)")
    
    # Campos requeridos
    cliente_id: int = Field(..., description="ID del cliente al que pertenece la factura")
    items: List[FacturaItemCreate] = Field(..., description="Lista de items de la factura")
    aplica_iva: bool = Field(True, description="Indica si aplica IVA a la factura")
    
    # Campos opcionales
    descripcion: Optional[str] = Field(None, max_length=500, description="Descripción de la factura")
    fecha_vencimiento: Optional[datetime] = Field(None, description="Fecha límite de pago")
    
    @field_validator('monto_pagar', 'monto_base', 'iva', 'valor_iva')
    @classmethod
    def validate_decimal_places(cls, v):
        if v is not None:
            # Convertir int/float a Decimal si es necesario
            if isinstance(v, (int, float)):
                v = Decimal(str(v))
            return v.quantize(Decimal('0.01'))
        return v

class FacturacionUpdate(BaseModel):
    """Esquema para actualizar una factura"""
    monto_pagar: Optional[Decimal] = Field(None)
    monto_base: Optional[Decimal] = Field(None)
    iva: Optional[Decimal] = Field(None)
    valor_iva: Optional[Decimal] = Field(None)
    descripcion: Optional[str] = Field(None, max_length=500)
    estado: Optional[str] = Field(None, description="Estado: pendiente, vencido, pagado")
    fecha_pago: Optional[datetime] = None
    fecha_vencimiento: Optional[datetime] = Field(None, description="Fecha límite de pago")
    aplica_iva: Optional[bool] = None
    
    @field_validator('monto_pagar', 'monto_base', 'iva', 'valor_iva')
    @classmethod
    def validate_decimal_places(cls, v):
        if v is not None:
            return v.quantize(Decimal('0.01'))
        return v

class FacturacionResponse(BaseSchema):
    """Esquema para respuesta de facturación"""
    id_factura: str
    fecha_generacion: datetime
    fecha_pago: Optional[datetime]
    fecha_vencimiento: Optional[datetime]
    monto_pagar: Decimal
    monto_base: Optional[Decimal]
    iva: Optional[Decimal]
    valor_iva: Optional[Decimal]
    estado: str
    descripcion: Optional[str]
    aplica_iva: bool
    cliente_id: int
    items: List[FacturaItemResponse] = []

class FacturacionListResponse(BaseSchema):
    """Esquema para lista de facturas"""
    id_factura: str
    fecha_generacion: datetime
    fecha_pago: Optional[datetime]
    fecha_vencimiento: Optional[datetime]
    monto_pagar: Decimal
    monto_base: Optional[Decimal]
    iva: Optional[Decimal]
    valor_iva: Optional[Decimal]
    estado: str
    descripcion: Optional[str]
    aplica_iva: bool
    cliente_id: int

# Esquemas específicos para el formulario de creación
class FacturaFormData(BaseModel):
    """Esquema para los datos del formulario de factura"""
    embrio_fresco: Optional[Decimal] = Field(0, description="Embrión fresco (COP)")
    embrio_congelado: Optional[Decimal] = Field(0, description="Embrión congelado (COP)")
    material_campo: Optional[Decimal] = Field(0, description="Material de campo (COP)")
    nitrogeno: Optional[Decimal] = Field(0, description="Nitrógeno (COP)")
    mensajeria: Optional[Decimal] = Field(0, description="Mensajería (COP)")
    pajilla_semen: Optional[Decimal] = Field(0, description="Pajilla de semen (COP)")
    fundas_te: Optional[Decimal] = Field(0, description="Fundas T.E (COP)")
    descripcion: Optional[str] = Field(None, max_length=500, description="Descripción adicional")
    fecha_vencimiento: Optional[datetime] = Field(None, description="Fecha límite de pago")
    cliente_id: int = Field(..., description="ID del cliente al que pertenece la factura")
    aplica_iva: bool = Field(True, description="Aplicar IVA a la factura")
    iva_porcentaje: Optional[Decimal] = Field(19.0, description="Porcentaje de IVA")
    
    @field_validator('embrio_fresco', 'embrio_congelado', 'material_campo', 'nitrogeno', 
                     'mensajeria', 'pajilla_semen', 'fundas_te', 'iva_porcentaje')
    @classmethod
    def validate_decimal_places(cls, v):
        if v is not None:
            # Convertir int/float a Decimal si es necesario
            if isinstance(v, (int, float)):
                v = Decimal(str(v))
            return v.quantize(Decimal('0.01'))
        return v

class FacturaFormResponse(BaseModel):
    """Esquema para respuesta del formulario"""
    total: Decimal = Field(..., description="Total calculado")
    monto_base: Decimal = Field(..., description="Monto base sin IVA")
    valor_iva: Decimal = Field(..., description="Valor del IVA")
    items: List[FacturaItemResponse] = Field(..., description="Items procesados")
    id_factura: Optional[str] = Field(None, description="ID de factura generado")
    aplica_iva: bool = Field(True, description="Si aplica IVA")
    
    @field_validator('total', 'monto_base', 'valor_iva')
    @classmethod
    def validate_decimal_places(cls, v):
        if v is not None:
            # Convertir int/float a Decimal si es necesario
            if isinstance(v, (int, float)):
                v = Decimal(str(v))
            return v.quantize(Decimal('0.01'))
        return v
