from sqlalchemy import Column, String, DateTime, Numeric, Enum, ForeignKey, Integer, Text, Boolean
from sqlalchemy.orm import relationship
from app.models.base_model import Base, BaseModel
import enum
from datetime import datetime

class EstadoFactura(str, enum.Enum):
    pendiente = "pendiente"
    vencido = "vencido"
    pagado = "pagado"

class EstadoPago(str, enum.Enum):
    pendiente = "pendiente"
    procesando = "procesando"
    completado = "completado"
    fallido = "fallido"
    cancelado = "cancelado"

class Facturacion(Base, BaseModel):
    __tablename__ = "facturacion"
    
    # ID de factura generado: mmddyyyydddddddx
    # donde mmddyyyy es la fecha, ddddddd son los dígitos del documento del cliente, x es serial
    id_factura = Column(String(20), unique=True, index=True, nullable=False)
    
    # Fecha de generación de la factura
    fecha_generacion = Column(DateTime, nullable=False, default=datetime.now)
    
    # Fecha de pago (puede ser null si no se ha pagado)
    fecha_pago = Column(DateTime, nullable=True)
    
    # Fecha de vencimiento de la factura
    fecha_vencimiento = Column(DateTime, nullable=True, comment="Fecha límite de pago")
    
    # Monto a pagar
    monto_pagar = Column(Numeric(10, 2), nullable=False) # monto base + IVA
    monto_base = Column(Numeric(10, 2), nullable=True, default=0, comment="Valor base")
    
    # Estado de la factura
    estado = Column(Enum(EstadoFactura), nullable=False, default=EstadoFactura.pendiente)
    
    # Descripción de la factura
    descripcion = Column(String(500), nullable=True)
    
    # Porcentaje de IVA
    iva = Column(Numeric(5, 2), nullable=True, default=19.0, comment="Porcentaje de IVA")

    valor_iva = Column(Numeric(10, 2), nullable=True, default=0, comment="Valor del IVA")
    
    # Indica si aplica IVA a la factura
    aplica_iva = Column(Boolean, nullable=False, default=True, comment="Indica si aplica IVA a la factura")
    
    # Relación con Usuario/Cliente (muchos a uno)
    cliente_id = Column(ForeignKey("users.id"), nullable=False, comment="ID del cliente al que pertenece la factura")
    
    # Relación con FacturaDetalle (uno a muchos)
    detalles = relationship("FacturaDetalle", back_populates="factura", cascade="all, delete-orphan")
    
    # Relación con Pagos (uno a muchos)
    pagos = relationship("Pagos", back_populates="factura", cascade="all, delete-orphan")
    
    # Relación con Usuario/Cliente
    cliente = relationship("User", back_populates="facturas")
    
    def __repr__(self):
        return f"<Facturacion {self.id_factura}>"

class FacturaDetalle(Base, BaseModel):
    __tablename__ = "factura_detalle"
    
    # Relación con Facturacion (muchos a uno)
    factura_id = Column(ForeignKey("facturacion.id"), nullable=False)
    
    # Campos específicos de items de factura
    embrio_fresco = Column(Numeric(10, 2), nullable=True, default=0)
    embrio_congelado = Column(Numeric(10, 2), nullable=True, default=0)
    material_campo = Column(Numeric(10, 2), nullable=True, default=0)
    nitrogeno = Column(Numeric(10, 2), nullable=True, default=0)
    mensajeria = Column(Numeric(10, 2), nullable=True, default=0)
    pajilla_semen = Column(Numeric(10, 2), nullable=True, default=0)
    fundas_te = Column(Numeric(10, 2), nullable=True, default=0)
    
    # Campo IVA
    iva = Column(Numeric(5, 2), nullable=False, default=19.0, comment="Porcentaje de IVA")
    
    # Relación con la factura
    factura = relationship("Facturacion", back_populates="detalles")
    
    def __repr__(self):
        return f"<FacturaDetalle {self.id}>"

class Pagos(Base, BaseModel):
    __tablename__ = "pagos"
    
    # Relación con Facturacion (muchos a uno)
    factura_id = Column(ForeignKey("facturacion.id"), nullable=False)
    
    # Monto del pago
    monto = Column(Numeric(10, 2), nullable=False)
    
    # Fecha del pago
    fecha_pago = Column(DateTime, nullable=False, default=datetime.now)
    
    # Estado del pago
    estado = Column(Enum(EstadoPago), nullable=False, default=EstadoPago.pendiente)
    
    # Método de pago
    metodo_pago = Column(String(50), nullable=False, comment="Efectivo, Transferencia, Tarjeta, PSE, etc.")
    
    # Referencia o número de transacción
    referencia = Column(String(100), nullable=True, comment="Número de referencia del pago")
    
    # Observaciones adicionales
    observaciones = Column(Text, nullable=True, comment="Observaciones sobre el pago")
    
    # Campos específicos para PSE y ePayco
    doc_type = Column(String(10), nullable=True, comment="Tipo de documento (CC, CE, etc.)")
    document = Column(String(20), nullable=True, comment="Número de documento")
    name = Column(String(100), nullable=True, comment="Nombre del pagador")
    last_name = Column(String(100), nullable=True, comment="Apellido del pagador")
    email = Column(String(100), nullable=True, comment="Email del pagador")
    ind_country = Column(String(5), nullable=True, default="57", comment="Código país (57=Colombia)")
    phone = Column(String(20), nullable=True, comment="Teléfono del pagador")
    country = Column(String(5), nullable=True, default="CO", comment="Código país")
    city = Column(String(100), nullable=True, comment="Ciudad del pagador")
    address = Column(String(200), nullable=True, comment="Dirección del pagador")
    ip = Column(String(45), nullable=True, comment="IP del cliente")
    currency = Column(String(5), nullable=True, default="COP", comment="Moneda")
    description = Column(String(500), nullable=True, comment="Descripción del pago")
    value = Column(Numeric(10, 2), nullable=True, comment="Valor del pago")
    tax = Column(Numeric(10, 2), nullable=True, default=0, comment="Impuestos")
    ico = Column(Numeric(10, 2), nullable=True, default=0, comment="ICO")
    tax_base = Column(Numeric(10, 2), nullable=True, comment="Base imponible")
    url_response = Column(String(500), nullable=True, comment="URL de respuesta")
    url_confirmation = Column(String(500), nullable=True, comment="URL de confirmación")
    method_confirmation = Column(String(10), nullable=True, default="GET", comment="Método confirmación")
    ref_payco = Column(String(50), nullable=True, comment="Referencia de ePayco")
    transaction_id = Column(String(100), nullable=True, comment="ID de transacción")
    bank_name = Column(String(100), nullable=True, comment="Nombre del banco")
    bank_url = Column(String(500), nullable=True, comment="URL del banco")
    response_code = Column(String(10), nullable=True, comment="Código de respuesta")
    response_message = Column(String(500), nullable=True, comment="Mensaje de respuesta")
    
    # Relación con la factura
    factura = relationship("Facturacion", back_populates="pagos")
    
    def __repr__(self):
        return f"<Pagos {self.id} - {self.monto}>"
