# Estados de Pago - BioGenetic

## 📋 Estados Disponibles

El sistema de pagos de BioGenetic maneja los siguientes estados para los pagos:

### 1. **PENDIENTE** 
- **Descripción**: Pago iniciado, esperando confirmación
- **Cuándo se usa**: 
  - Al crear un nuevo pago
  - Cuando el pago se ha enviado a ePayco pero aún no hay respuesta
- **Siguiente estado**: `procesando` o `fallido`

### 2. **PROCESANDO**
- **Descripción**: Pago en proceso en el banco
- **Cuándo se usa**:
  - Cuando ePayco confirma que el pago está siendo procesado por el banco
  - Durante la validación de datos bancarios
- **Siguiente estado**: `completado`, `fallido` o `cancelado`

### 3. **COMPLETADO**
- **Descripción**: Pago exitoso
- **Cuándo se usa**:
  - Cuando el banco confirma que el pago fue exitoso
  - Cuando ePayco retorna estado "Aceptada"
- **Siguiente estado**: Ninguno (estado final)

### 4. **FALLIDO**
- **Descripción**: Pago rechazado
- **Cuándo se usa**:
  - Cuando el banco rechaza el pago
  - Cuando ePayco retorna estado "Rechazada" o "Fallida"
  - Cuando hay errores de validación
- **Siguiente estado**: Ninguno (estado final)

### 5. **CANCELADO**
- **Descripción**: Pago cancelado por el usuario
- **Cuándo se usa**:
  - Cuando el usuario cancela el pago antes de completarlo
  - Cuando el usuario abandona el proceso de pago
- **Siguiente estado**: Ninguno (estado final)

## 🔄 Flujo de Estados

```
PENDIENTE → PROCESANDO → COMPLETADO
    ↓           ↓           ↓
  FALLIDO    FALLIDO    (FINAL)
    ↓           ↓
CANCELADO  CANCELADO
    ↓           ↓
  (FINAL)    (FINAL)
```

## 💻 Implementación Técnica

### En el Modelo (`app/models/facturacion.py`):
```python
class EstadoPago(str, enum.Enum):
    pendiente = "pendiente"
    procesando = "procesando"
    completado = "completado"
    fallido = "fallido"
    cancelado = "cancelado"
```

### En los Esquemas (`app/schemas/pagos_schema.py`):
```python
from app.models.facturacion import EstadoPago

class PagoResponse(BaseSchema):
    estado: EstadoPago
    # ... otros campos
```

### En los Servicios (`app/services/epayco_service.py`):
```python
# Mapeo de estados de ePayco a estados internos
estado_mapping = {
    'Aceptada': EstadoPago.completado,
    'Pendiente': EstadoPago.procesando,
    'Rechazada': EstadoPago.fallido,
    'Fallida': EstadoPago.fallido
}
```

## 📊 Casos de Uso

### Pago PSE Exitoso:
1. Usuario inicia pago → `PENDIENTE`
2. ePayco procesa → `PROCESANDO`
3. Banco confirma → `COMPLETADO`

### Pago PSE Fallido:
1. Usuario inicia pago → `PENDIENTE`
2. ePayco procesa → `PROCESANDO`
3. Banco rechaza → `FALLIDO`

### Pago Cancelado:
1. Usuario inicia pago → `PENDIENTE`
2. Usuario cancela → `CANCELADO`

## 🔍 Consultas Comunes

### Obtener pagos por estado:
```python
# Pagos pendientes
pagos_pendientes = db.query(Pagos).filter(Pagos.estado == EstadoPago.pendiente).all()

# Pagos completados
pagos_completados = db.query(Pagos).filter(Pagos.estado == EstadoPago.completado).all()
```

### Actualizar estado de pago:
```python
pago.estado = EstadoPago.completado
db.commit()
```

## ⚠️ Notas Importantes

1. **Estados Finales**: `completado`, `fallido`, y `cancelado` son estados finales
2. **Validación**: Siempre validar que las transiciones de estado sean válidas
3. **Logging**: Registrar todos los cambios de estado para auditoría
4. **Notificaciones**: Enviar notificaciones por email cuando el estado cambie a `completado` o `fallido`
