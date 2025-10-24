# Implementación de Pagos PSE con ePayco SDK

## Descripción General

Este documento describe la implementación del procesamiento de pagos PSE (Pagos Seguros en Línea) utilizando el SDK de ePayco para el sistema de facturación de BioGenetic. La integración permitirá procesar pagos de facturas de manera segura y eficiente.

## Análisis del SDK ePayco

Basado en la documentación de [ePayco Python SDK](https://github.com/epayco/epayco-python), el SDK proporciona:

- **Creación de tokens** para tarjetas de crédito/débito
- **Gestión de clientes** (crear, obtener, listar)
- **Procesamiento de pagos** con tarjeta, efectivo y PSE
- **Pagos con Daviplata** y Safetypay
- **Split payments** para pagos distribuidos
- **Confirmación de transacciones**

## Campos Requeridos para PSE

### Información del Cliente (desde modelo User)
- `full_name` - Nombre completo
- `email` - Correo electrónico
- `phone` - Teléfono
- `number_document` - Número de documento
- `type_document` - Tipo de documento (CC, CE, etc.)

### Información de la Factura (desde modelo Facturacion)
- `id_factura` - ID único de la factura
- `monto_pagar` - Monto total a pagar
- `descripcion` - Descripción de la factura
- `fecha_generacion` - Fecha de generación

### Información del Pago (desde modelo Pagos)
- `monto` - Monto del pago
- `metodo_pago` - Método de pago (PSE)
- `estado` - Estado del pago
- `referencia` - Referencia de ePayco

## Campos Adicionales Requeridos para PSE

Para procesar pagos PSE, necesitamos agregar los siguientes campos al modelo `Pagos`:

```python
# Campos específicos para PSE
doc_type = Column(String(10), nullable=False, comment="Tipo de documento (CC, CE, etc.)")
document = Column(String(20), nullable=False, comment="Número de documento")
name = Column(String(100), nullable=False, comment="Nombre del pagador")
last_name = Column(String(100), nullable=True, comment="Apellido del pagador")
email = Column(String(100), nullable=False, comment="Email del pagador")
ind_country = Column(String(5), nullable=False, default="57", comment="Código país (57=Colombia)")
phone = Column(String(20), nullable=False, comment="Teléfono del pagador")
country = Column(String(5), nullable=False, default="CO", comment="Código país")
city = Column(String(100), nullable=False, comment="Ciudad del pagador")
address = Column(String(200), nullable=True, comment="Dirección del pagador")
ip = Column(String(45), nullable=False, comment="IP del cliente")
currency = Column(String(5), nullable=False, default="COP", comment="Moneda")
description = Column(String(500), nullable=False, comment="Descripción del pago")
value = Column(Numeric(10, 2), nullable=False, comment="Valor del pago")
tax = Column(Numeric(10, 2), nullable=False, default=0, comment="Impuestos")
ico = Column(Numeric(10, 2), nullable=False, default=0, comment="ICO")
tax_base = Column(Numeric(10, 2), nullable=False, comment="Base imponible")
url_response = Column(String(500), nullable=False, comment="URL de respuesta")
url_confirmation = Column(String(500), nullable=False, comment="URL de confirmación")
method_confirmation = Column(String(10), nullable=False, default="GET", comment="Método confirmación")
ref_payco = Column(String(50), nullable=True, comment="Referencia de ePayco")
transaction_id = Column(String(100), nullable=True, comment="ID de transacción")
bank_name = Column(String(100), nullable=True, comment="Nombre del banco")
bank_url = Column(String(500), nullable=True, comment="URL del banco")
response_code = Column(String(10), nullable=True, comment="Código de respuesta")
response_message = Column(String(500), nullable=True, comment="Mensaje de respuesta")
```

## Servicios Requeridos

### 1. Servicio de Configuración ePayco

```python
class EpaycoConfigService:
    def __init__(self):
        self.api_key = settings.EPAYCO_PUBLIC_KEY
        self.private_key = settings.EPAYCO_PRIVATE_KEY
        self.test = settings.EPAYCO_TEST_MODE
        self.language = "ES"
        
    def get_epayco_client(self):
        options = {
            "apiKey": self.api_key,
            "privateKey": self.private_key,
            "test": self.test,
            "lenguage": self.language
        }
        return epayco.Epayco(options)
```

### 2. Servicio de Procesamiento de Pagos PSE

```python
class PSEPaymentService:
    def __init__(self, db: Session):
        self.db = db
        self.epayco = EpaycoConfigService().get_epayco_client()
    
    async def create_pse_payment(self, factura_id: str, user: User, request_ip: str) -> dict:
        """
        Crear pago PSE para una factura específica
        """
        # 1. Obtener factura
        factura = self.get_factura(factura_id)
        
        # 2. Preparar datos para ePayco
        payment_data = self.prepare_pse_data(factura, user, request_ip)
        
        # 3. Crear pago en ePayco
        pse_response = self.epayco.cash.create('pse', payment_data)
        
        # 4. Guardar pago en base de datos
        pago = self.save_payment(factura, pse_response, payment_data)
        
        return {
            "pago_id": pago.id,
            "ref_payco": pse_response.get('ref_payco'),
            "bank_url": pse_response.get('bank_url'),
            "bank_name": pse_response.get('bank_name'),
            "status": pago.estado
        }
    
    def prepare_pse_data(self, factura: Facturacion, user: User, request_ip: str) -> dict:
        """
        Preparar datos para envío a ePayco PSE
        """
        # Calcular impuestos
        iva = factura.monto_pagar * Decimal('0.19')  # 19% IVA
        base_iva = factura.monto_pagar - iva
        
        return {
            "doc_type": self.map_document_type(user.type_document),
            "document": user.number_document,
            "name": user.full_name.split()[0] if user.full_name else "Cliente",
            "last_name": " ".join(user.full_name.split()[1:]) if len(user.full_name.split()) > 1 else "",
            "email": user.email,
            "ind_country": "57",  # Colombia
            "phone": user.phone,
            "country": "CO",
            "city": "Bogotá",  # Por defecto, se puede personalizar
            "address": "Dirección no especificada",  # Se puede personalizar
            "ip": request_ip,
            "currency": "COP",
            "description": f"Pago factura {factura.id_factura} - {factura.descripcion or 'Servicios BioGenetic'}",
            "value": str(int(factura.monto_pagar)),
            "tax": str(int(iva)),
            "ico": "0",
            "tax_base": str(int(base_iva)),
            "url_response": f"{settings.BASE_URL}/api/pagos/response",
            "url_confirmation": f"{settings.BASE_URL}/api/pagos/confirmation",
            "method_confirmation": "POST",
            "extra1": factura.id_factura,
            "extra2": str(factura.id),
            "extra3": str(user.id),
            "extra4": "",
            "extra5": "",
            "extra6": "",
            "extra7": ""
        }
    
    def map_document_type(self, doc_type: DocumentType) -> str:
        """
        Mapear tipo de documento interno a ePayco
        """
        mapping = {
            DocumentType.identity_card: "CC",
            DocumentType.passport: "CE",
            DocumentType.other: "CC"
        }
        return mapping.get(doc_type, "CC")
```

### 3. Servicio de Confirmación de Pagos

```python
class PaymentConfirmationService:
    def __init__(self, db: Session):
        self.db = db
        self.epayco = EpaycoConfigService().get_epayco_client()
    
    async def confirm_payment(self, ref_payco: str) -> dict:
        """
        Confirmar estado de pago con ePayco
        """
        # 1. Consultar estado en ePayco
        payment_status = self.epayco.cash.get(ref_payco)
        
        # 2. Actualizar pago en base de datos
        pago = self.update_payment_status(ref_payco, payment_status)
        
        # 3. Actualizar estado de factura si es necesario
        if payment_status.get('x_response') == 'Aceptada':
            self.update_factura_status(pago.factura_id, EstadoFactura.pagado)
        
        return {
            "pago_id": pago.id,
            "estado": pago.estado,
            "ref_payco": ref_payco,
            "response_code": payment_status.get('x_response'),
            "response_message": payment_status.get('x_response_reason_text')
        }
    
    def update_payment_status(self, ref_payco: str, payment_status: dict) -> Pagos:
        """
        Actualizar estado del pago basado en respuesta de ePayco
        """
        pago = self.db.query(Pagos).filter(Pagos.ref_payco == ref_payco).first()
        
        if not pago:
            raise HTTPException(status_code=404, detail="Pago no encontrado")
        
        # Mapear estado de ePayco a estado interno
        epayco_status = payment_status.get('x_response')
        estado_mapping = {
            'Aceptada': EstadoPago.completado,
            'Pendiente': EstadoPago.procesando,
            'Rechazada': EstadoPago.fallido,
            'Fallida': EstadoPago.fallido
        }
        
        pago.estado = estado_mapping.get(epayco_status, EstadoPago.pendiente)
        pago.response_code = payment_status.get('x_response')
        pago.response_message = payment_status.get('x_response_reason_text')
        pago.transaction_id = payment_status.get('transaction_id')
        
        self.db.commit()
        self.db.refresh(pago)
        
        return pago
```

### 4. Servicio de Notificaciones

```python
class PaymentNotificationService:
    def __init__(self, db: Session):
        self.db = db
    
    async def send_payment_notification(self, pago: Pagos, factura: Facturacion, user: User):
        """
        Enviar notificación de pago al usuario
        """
        # Implementar envío de email/SMS
        # Usar servicios de notificación existentes
        pass
    
    async def send_payment_confirmation(self, pago: Pagos, factura: Facturacion, user: User):
        """
        Enviar confirmación de pago exitoso
        """
        # Implementar envío de confirmación
        pass
```

## Flujo de Procesamiento de Pagos PSE

### 1. Iniciar Pago
```
Cliente → Selecciona PSE → Servicio PSE → ePayco → Banco
```

### 2. Procesamiento
```
Banco → ePayco → Webhook/Confirmation → Actualizar BD → Notificar Cliente
```

### 3. Estados del Pago
- `pendiente` - Pago iniciado, esperando confirmación
- `procesando` - Pago en proceso en el banco
- `completado` - Pago exitoso
- `fallido` - Pago rechazado
- `cancelado` - Pago cancelado por el usuario

## Endpoints API Requeridos

### 1. Crear Pago PSE
```
POST /api/pagos/pse/create
{
    "factura_id": "1022202512345671",
    "metodo_pago": "PSE"
}
```

### 2. Respuesta del Banco
```
POST /api/pagos/response
GET /api/pagos/response?ref_payco=123456&x_response=Aceptada
```

### 3. Confirmación de ePayco
```
POST /api/pagos/confirmation
```

### 4. Consultar Estado
```
GET /api/pagos/{pago_id}/status
```

## Configuración de Variables de Entorno

```env
# ePayco Configuration
EPAYCO_PUBLIC_KEY=your_public_key
EPAYCO_PRIVATE_KEY=your_private_key
EPAYCO_TEST_MODE=true
EPAYCO_MERCHANT_ID=your_merchant_id

# URLs
BASE_URL=https://yourdomain.com
PAYMENT_RESPONSE_URL=https://yourdomain.com/api/pagos/response
PAYMENT_CONFIRMATION_URL=https://yourdomain.com/api/pagos/confirmation
```

## Consideraciones de Seguridad

1. **Validación de IP**: Verificar que las notificaciones vengan de ePayco
2. **Firma de notificaciones**: Validar firma de ePayco en webhooks
3. **HTTPS obligatorio**: Todas las comunicaciones deben ser seguras
4. **Logs de auditoría**: Registrar todas las transacciones
5. **Validación de montos**: Verificar que los montos coincidan

## Próximos Pasos

1. **Actualizar modelo Pagos** con campos PSE
2. **Crear migración** de base de datos
3. **Implementar servicios** de pago
4. **Crear endpoints** API
5. **Implementar webhooks** de confirmación
6. **Crear formulario** de pago PSE
7. **Implementar notificaciones**
8. **Pruebas** en modo test
9. **Despliegue** en producción

## Referencias

- [ePayco Python SDK](https://github.com/epayco/epayco-python)
- [Documentación ePayco PSE](https://docs.epayco.co/payments/pse)
- [Webhooks ePayco](https://docs.epayco.co/webhooks)
