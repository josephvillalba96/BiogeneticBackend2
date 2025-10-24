from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
from app.schemas.base_schema import BaseSchema
from app.models.facturacion import EstadoPago

class PagoBase(BaseModel):
    """Esquema base para pagos"""
    monto: Decimal = Field(..., decimal_places=2, description="Monto del pago")
    metodo_pago: str = Field(..., description="Método de pago (PSE, Tarjeta, Efectivo, etc.)")
    observaciones: Optional[str] = Field(None, description="Observaciones del pago")

class PagoCreate(PagoBase):
    """Esquema para crear un pago"""
    factura_id: int = Field(..., description="ID de la factura")
    doc_type: str = Field(..., description="Tipo de documento (CC, CE, etc.)")
    document: str = Field(..., description="Número de documento")
    name: str = Field(..., description="Nombre del pagador")
    last_name: Optional[str] = Field(None, description="Apellido del pagador")
    email: EmailStr = Field(..., description="Email del pagador")
    phone: str = Field(..., description="Teléfono del pagador")
    city: str = Field(..., description="Ciudad del pagador")
    address: Optional[str] = Field(None, description="Dirección del pagador")

class PagoPSECreate(BaseModel):
    """Esquema específico para crear pago PSE"""
    factura_id: int = Field(..., description="ID de la factura")
    city: Optional[str] = Field("Bogotá", description="Ciudad del pagador")
    address: Optional[str] = Field("Dirección no especificada", description="Dirección del pagador")

class PagoUpdate(BaseModel):
    """Esquema para actualizar un pago"""
    estado: Optional[EstadoPago] = Field(None, description="Estado del pago")
    observaciones: Optional[str] = Field(None, description="Observaciones del pago")
    response_code: Optional[str] = Field(None, description="Código de respuesta")
    response_message: Optional[str] = Field(None, description="Mensaje de respuesta")

class PagoResponse(BaseSchema):
    """Esquema para respuesta de pago"""
    monto: Decimal
    fecha_pago: datetime
    estado: EstadoPago
    metodo_pago: str
    referencia: Optional[str]
    observaciones: Optional[str]
    doc_type: Optional[str]
    document: Optional[str]
    name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    city: Optional[str]
    address: Optional[str]
    ip: Optional[str]
    currency: Optional[str]
    description: Optional[str]
    value: Optional[Decimal]
    tax: Optional[Decimal]
    tax_base: Optional[Decimal]
    ref_payco: Optional[str]
    transaction_id: Optional[str]
    bank_name: Optional[str]
    bank_url: Optional[str]
    response_code: Optional[str]
    response_message: Optional[str]
    factura_id: int

class PagoListResponse(BaseSchema):
    """Esquema para lista de pagos"""
    monto: Decimal
    fecha_pago: datetime
    estado: EstadoPago
    metodo_pago: str
    ref_payco: Optional[str]
    bank_name: Optional[str]
    response_code: Optional[str]

class PagoStatusResponse(BaseModel):
    """Esquema para consulta de estado de pago"""
    pago_id: int
    estado: EstadoPago
    ref_payco: Optional[str]
    response_code: Optional[str]
    response_message: Optional[str]
    bank_name: Optional[str]
    bank_url: Optional[str]

class PSEPaymentResponse(BaseModel):
    """Esquema para respuesta de pago PSE"""
    pago_id: int
    ref_payco: str
    bank_url: str
    bank_name: str
    status: str
    message: str

class PaymentConfirmationResponse(BaseModel):
    """Esquema para confirmación de pago"""
    pago_id: int
    estado: EstadoPago
    ref_payco: str
    response_code: str
    response_message: str
    factura_actualizada: bool

class EmailNotificationData(BaseModel):
    """Esquema para datos de notificación por email"""
    to_email: EmailStr
    subject: str
    template_name: str
    context: dict

class PaymentNotificationData(BaseModel):
    """Esquema para datos de notificación de pago"""
    pago_id: int
    factura_id: int
    user_email: EmailStr
    user_name: str
    monto: Decimal
    estado: EstadoPago
    ref_payco: Optional[str]
    bank_name: Optional[str]

class BankInfo(BaseModel):
    """Esquema para información de banco"""
    id: str = Field(..., description="ID del banco")
    name: str = Field(..., description="Nombre del banco")
    code: str = Field(..., description="Código del banco")
    description: str = Field(..., description="Descripción del banco")

class BanksResponse(BaseModel):
    """Esquema para respuesta de lista de bancos"""
    success: bool = Field(..., description="Indica si la operación fue exitosa")
    banks: List[BankInfo] = Field(..., description="Lista de entidades bancarias")
    message: str = Field(..., description="Mensaje descriptivo")
    total: int = Field(..., description="Total de bancos disponibles")
