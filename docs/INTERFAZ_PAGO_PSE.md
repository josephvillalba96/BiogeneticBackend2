# Interfaz de Pago PSE - BioGenetic

## 📋 Descripción General

Este documento describe cómo debe implementarse la interfaz de usuario para procesar pagos PSE (Pagos Seguros en Línea) utilizando los servicios de pago existentes en BioGenetic. La interfaz debe permitir a los clientes seleccionar su banco y completar el proceso de pago de manera segura.

## 🏗️ Arquitectura de la Interfaz

### 1. **Flujo de Pago PSE**
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  1. Seleccionar │ -> │  2. Seleccionar │ -> │  3. Llenar      │
│     Factura     │    │     Banco       │    │     Datos       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         v                       v                       v
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  4. Confirmar   │ -> │  5. Redirigir   │ -> │  6. Monitorear  │
│     Pago        │    │     al Banco    │    │     Estado      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### 2. **Estados del Pago**
```
┌───────────┐    ┌─────────────┐    ┌─────────────┐
│ PENDIENTE │ -> │ PROCESANDO  │ -> │ COMPLETADO  │
└───────────┘    └─────────────┘    └─────────────┘
       │                │
       v                v
┌───────────┐    ┌───────────┐
│  FALLIDO  │    │ CANCELADO │
└───────────┘    └───────────┘
```

### 2. **Componentes de la Interfaz**
- **Selector de Factura**: Lista de facturas pendientes del cliente
- **Selector de Banco**: Lista de entidades bancarias disponibles
- **Formulario de Datos**: Información personal del pagador
- **Confirmación**: Resumen del pago antes de procesar
- **Redirección**: Envío al banco para completar el pago

## 🔌 Servicios Disponibles

### 1. **Obtener Entidades Bancarias**
```http
GET /api/pagos/banks
```

**Respuesta:**
```json
{
  "success": true,
  "banks": [
    {
      "id": "1007",
      "name": "BANCO DE BOGOTÁ",
      "code": "1007",
      "description": "Banco de Bogotá S.A."
    }
  ],
  "message": "Lista estática de entidades bancarias",
  "total": 10
}
```

### 2. **Crear Pago PSE**
```http
POST /api/pagos/pse/create
```

**Payload:**
```json
{
  "factura_id": 123,
  "city": "Bogotá",
  "address": "Calle 123 #45-67"
}
```

**Respuesta:**
```json
{
  "pago_id": 456,
  "ref_payco": "ref_123456789",
  "bank_url": "https://bank.example.com/pay",
  "bank_name": "BANCO DE BOGOTÁ",
  "status": "pendiente",
  "message": "Pago PSE creado exitosamente"
}
```

### 3. **Consultar Estado de Pago**
```http
GET /api/pagos/{pago_id}/status
```

**Respuesta:**
```json
{
  "pago_id": 456,
  "estado": "completado",
  "ref_payco": "ref_123456789",
  "response_code": "1",
  "response_message": "Aprobada",
  "bank_name": "BANCO DE BOGOTÁ",
  "bank_url": "https://bank.example.com/pay"
}
```

## 📝 Campos Requeridos del Cliente

### 1. **Información Personal (Automática)**
Estos campos se obtienen automáticamente del perfil del usuario logueado:

| Campo | Fuente | Descripción |
|-------|--------|-------------|
| `name` | `user.full_name` | Nombre completo del usuario |
| `email` | `user.email` | Email del usuario |
| `phone` | `user.phone` | Teléfono del usuario |
| `document` | `user.number_document` | Número de documento |
| `doc_type` | `user.type_document` | Tipo de documento (CC, CE, etc.) |

### 2. **Información de Pago (Manual)**
Estos campos deben ser llenados manualmente por el cliente:

| Campo | Tipo | Requerido | Descripción | Validación |
|-------|------|-----------|-------------|------------|
| `factura_id` | `integer` | ✅ | ID de la factura a pagar | Debe existir y pertenecer al cliente |
| `bank_id` | `string` | ✅ | ID del banco seleccionado | Debe estar en la lista de bancos disponibles |
| `city` | `string` | ✅ | Ciudad del pagador | Mínimo 2 caracteres |
| `address` | `string` | ✅ | Dirección del pagador | Mínimo 10 caracteres |

### 3. **Información del Sistema (Automática)**
Estos campos se generan automáticamente:

| Campo | Fuente | Descripción |
|-------|--------|-------------|
| `ip` | `request.client.host` | IP del cliente |
| `currency` | `"COP"` | Moneda (fija) |
| `country` | `"CO"` | País (fijo) |
| `ind_country` | `"57"` | Código país (fijo) |

## 🎨 Diseño de la Interfaz

### 0. **Estructura HTML Base**
```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pago PSE - BioGenetic</title>
    <link rel="stylesheet" href="styles/payment.css">
</head>
<body>
    <div class="payment-container">
        <header class="payment-header">
            <h1>Pago PSE</h1>
            <p>Pagos Seguros en Línea</p>
        </header>
        
        <main class="payment-steps">
            <!-- Pasos del pago -->
        </main>
        
        <footer class="payment-footer">
            <p>Powered by ePayco</p>
        </footer>
    </div>
    
    <script src="js/payment.js"></script>
</body>
</html>
```

### 1. **Estilos CSS Base**
```css
.payment-container {
    max-width: 800px;
    margin: 0 auto;
    padding: 20px;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

.payment-steps {
    display: grid;
    gap: 30px;
    margin: 30px 0;
}

.step {
    background: #fff;
    border: 1px solid #e0e0e0;
    border-radius: 8px;
    padding: 25px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.step.active {
    border-color: #007bff;
    box-shadow: 0 4px 8px rgba(0,123,255,0.2);
}

.bank-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
    gap: 15px;
    margin-top: 20px;
}

.bank-card {
    border: 2px solid #e0e0e0;
    border-radius: 8px;
    padding: 20px;
    text-align: center;
    cursor: pointer;
    transition: all 0.3s ease;
}

.bank-card:hover {
    border-color: #007bff;
    transform: translateY(-2px);
}

.bank-card.selected {
    border-color: #007bff;
    background-color: #f8f9ff;
}

.form-group {
    margin-bottom: 20px;
}

.form-group label {
    display: block;
    margin-bottom: 5px;
    font-weight: 600;
    color: #333;
}

.form-group input,
.form-group textarea,
.form-group select {
    width: 100%;
    padding: 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 16px;
}

.btn-primary {
    background-color: #007bff;
    color: white;
    padding: 12px 30px;
    border: none;
    border-radius: 4px;
    font-size: 16px;
    cursor: pointer;
    transition: background-color 0.3s ease;
}

.btn-primary:hover {
    background-color: #0056b3;
}

.btn-primary:disabled {
    background-color: #6c757d;
    cursor: not-allowed;
}
```

### 1. **Paso 1: Selección de Factura**
```html
<div class="factura-selector">
  <h3>Seleccione la factura a pagar</h3>
  <select id="factura_id" required>
    <option value="">Seleccione una factura</option>
    <!-- Cargar facturas pendientes del cliente -->
  </select>
  <div id="factura-details" class="hidden">
    <!-- Mostrar detalles de la factura seleccionada -->
  </div>
</div>
```

### 2. **Paso 2: Selección de Banco**
```html
<div class="bank-selector">
  <h3>Seleccione su banco</h3>
  <div class="bank-grid">
    <!-- Cargar bancos desde /api/pagos/banks -->
    <div class="bank-card" data-bank-id="1007">
      <img src="/images/banks/bogota.png" alt="Banco de Bogotá">
      <span>BANCO DE BOGOTÁ</span>
    </div>
  </div>
</div>
```

### 3. **Paso 3: Formulario de Datos**
```html
<form id="pago-form">
  <div class="form-group">
    <label for="city">Ciudad *</label>
    <input type="text" id="city" name="city" required 
           placeholder="Ej: Bogotá" minlength="2">
  </div>
  
  <div class="form-group">
    <label for="address">Dirección *</label>
    <textarea id="address" name="address" required 
              placeholder="Ej: Calle 123 #45-67" minlength="10"></textarea>
  </div>
  
  <div class="form-group">
    <label>Información del Pagador</label>
    <div class="readonly-field">
      <span>Nombre: {{ user.full_name }}</span>
      <span>Email: {{ user.email }}</span>
      <span>Documento: {{ user.number_document }}</span>
    </div>
  </div>
</form>
```

### 4. **Paso 4: Confirmación**
```html
<div class="payment-summary">
  <h3>Resumen del Pago</h3>
  <div class="summary-item">
    <span>Factura:</span>
    <span id="summary-factura">#1023202556789011</span>
  </div>
  <div class="summary-item">
    <span>Banco:</span>
    <span id="summary-banco">BANCO DE BOGOTÁ</span>
  </div>
  <div class="summary-item">
    <span>Monto:</span>
    <span id="summary-monto">$1.578.178,00</span>
  </div>
  <button id="confirm-payment" class="btn-primary">
    Confirmar y Pagar
  </button>
</div>
```

## 💻 Implementación JavaScript

### 1. **Cargar Facturas Pendientes**
```javascript
async function loadPendingInvoices() {
  try {
    const response = await fetch('/api/facturacion/?estado=pendiente', {
      headers: {
        'Authorization': 'Bearer ' + localStorage.getItem('access_token')
      }
    });
    
    if (response.ok) {
      const data = await response.json();
      const select = document.getElementById('factura_id');
      
      data.facturas.forEach(factura => {
        const option = document.createElement('option');
        option.value = factura.id;
        option.textContent = `Factura ${factura.id_factura} - $${factura.monto_pagar}`;
        select.appendChild(option);
      });
    }
  } catch (error) {
    console.error('Error cargando facturas:', error);
  }
}
```

### 2. **Cargar Entidades Bancarias**
```javascript
async function loadBanks() {
  try {
    const response = await fetch('/api/pagos/banks');
    const data = await response.json();
    
    if (data.success) {
      const bankGrid = document.querySelector('.bank-grid');
      
      data.banks.forEach(bank => {
        const bankCard = document.createElement('div');
        bankCard.className = 'bank-card';
        bankCard.dataset.bankId = bank.id;
        bankCard.innerHTML = `
          <img src="/images/banks/${bank.id}.png" alt="${bank.name}">
          <span>${bank.name}</span>
        `;
        
        bankCard.addEventListener('click', () => selectBank(bank));
        bankGrid.appendChild(bankCard);
      });
    }
  } catch (error) {
    console.error('Error cargando bancos:', error);
  }
}
```

### 3. **Procesar Pago PSE**
```javascript
async function processPSEPayment() {
  const formData = new FormData(document.getElementById('pago-form'));
  const selectedBank = document.querySelector('.bank-card.selected');
  
  if (!selectedBank) {
    alert('Por favor seleccione un banco');
    return;
  }
  
  const paymentData = {
    factura_id: parseInt(document.getElementById('factura_id').value),
    city: formData.get('city'),
    address: formData.get('address')
  };
  
  try {
    const response = await fetch('/api/pagos/pse/create', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + localStorage.getItem('access_token')
      },
      body: JSON.stringify(paymentData)
    });
    
    if (response.ok) {
      const result = await response.json();
      
      // Mostrar mensaje de confirmación
      showPaymentConfirmation(result);
      
      // Redirigir al banco
      if (result.bank_url) {
        window.location.href = result.bank_url;
      }
    } else {
      const error = await response.json();
      alert('Error: ' + error.detail);
    }
  } catch (error) {
    console.error('Error procesando pago:', error);
    alert('Error al procesar el pago');
  }
}
```

### 4. **Monitorear Estado del Pago**
```javascript
async function checkPaymentStatus(pagoId) {
  try {
    const response = await fetch(`/api/pagos/${pagoId}/status`, {
      headers: {
        'Authorization': 'Bearer ' + localStorage.getItem('access_token')
      }
    });
    
    if (response.ok) {
      const status = await response.json();
      
      switch (status.estado) {
        case 'completado':
          showSuccessMessage('Pago completado exitosamente');
          break;
        case 'fallido':
          showErrorMessage('El pago fue rechazado');
          break;
        case 'procesando':
          showInfoMessage('Pago en proceso...');
          setTimeout(() => checkPaymentStatus(pagoId), 5000);
          break;
        case 'pendiente':
          showInfoMessage('Esperando confirmación del banco...');
          setTimeout(() => checkPaymentStatus(pagoId), 5000);
          break;
      }
    }
  } catch (error) {
    console.error('Error verificando estado:', error);
  }
}
```

## 🎯 Estados de Pago

### 1. **Estados Disponibles**
- **`pendiente`**: Pago iniciado, esperando confirmación
- **`procesando`**: Pago en proceso en el banco
- **`completado`**: Pago exitoso
- **`fallido`**: Pago rechazado
- **`cancelado`**: Pago cancelado por el usuario

### 2. **Flujo de Estados**
```
pendiente → procesando → completado
    ↓           ↓
  fallido    fallido
    ↓           ↓
cancelado  cancelado
```

## 🔒 Consideraciones de Seguridad

### 1. **Validaciones del Cliente**
- Verificar que la factura pertenezca al usuario logueado
- Validar que la factura esté en estado "pendiente"
- Sanitizar todos los inputs del usuario
- Validar formato de ciudad y dirección

### 2. **Manejo de Errores**
- Mostrar mensajes de error claros al usuario
- Logear errores para debugging
- Manejar timeouts de red
- Validar respuestas de la API

### 3. **UX/UI**
- Mostrar indicadores de carga durante el proceso
- Confirmar antes de redirigir al banco
- Permitir cancelar el proceso
- Mostrar resumen claro del pago

## 📱 Responsive Design

### 1. **Mobile First**
- Formulario vertical en móviles
- Botones grandes para touch
- Grid de bancos adaptativo
- Navegación por pasos

### 2. **Desktop**
- Formulario en dos columnas
- Grid de bancos 4x3
- Sidebar con resumen
- Navegación con tabs

## 🧪 Testing

### 1. **Casos de Prueba**
- Pago exitoso con diferentes bancos
- Pago fallido por datos incorrectos
- Pago cancelado por el usuario
- Timeout de red
- Factura ya pagada
- Usuario no autorizado

### 2. **Datos de Prueba**
- Usar facturas de prueba
- Probar con diferentes tipos de documento
- Validar con bancos de la lista estática
- Probar con datos inválidos

## 📋 Checklist de Implementación

- [ ] Cargar facturas pendientes del usuario
- [ ] Cargar lista de entidades bancarias
- [ ] Implementar formulario de datos del pagador
- [ ] Validar todos los campos requeridos
- [ ] Implementar confirmación de pago
- [ ] Redirigir al banco después del pago
- [ ] Monitorear estado del pago
- [ ] Manejar todos los estados posibles
- [ ] Implementar responsive design
- [ ] Agregar indicadores de carga
- [ ] Implementar manejo de errores
- [ ] Probar con datos reales

## 📊 Ejemplos de Respuestas de API

### 1. **Respuesta Exitosa - Crear Pago PSE**
```json
{
  "pago_id": 456,
  "ref_payco": "ref_123456789",
  "bank_url": "https://secure.payco.co/checkout.php?ref_payco=ref_123456789",
  "bank_name": "BANCO DE BOGOTÁ",
  "status": "pendiente",
  "message": "Pago PSE creado exitosamente. Redirigir al banco para completar el pago."
}
```

### 2. **Respuesta de Error - Factura No Encontrada**
```json
{
  "detail": "Factura con ID 999 no encontrada"
}
```

### 3. **Respuesta de Error - Factura Ya Pagada**
```json
{
  "detail": "La factura ya está pagada"
}
```

### 4. **Estado de Pago - Completado**
```json
{
  "pago_id": 456,
  "estado": "completado",
  "ref_payco": "ref_123456789",
  "response_code": "1",
  "response_message": "Aprobada",
  "bank_name": "BANCO DE BOGOTÁ",
  "bank_url": "https://secure.payco.co/checkout.php?ref_payco=ref_123456789"
}
```

## 🧪 Casos de Uso de Prueba

### 1. **Caso Exitoso**
```javascript
// Datos de prueba para pago exitoso
const testData = {
  factura_id: 1,
  city: "Bogotá",
  address: "Calle 123 #45-67"
};

// Resultado esperado: Redirección al banco
```

### 2. **Caso de Error - Datos Inválidos**
```javascript
// Datos inválidos
const invalidData = {
  factura_id: 999, // No existe
  city: "", // Vacío
  address: "Calle" // Muy corto
};

// Resultado esperado: Mensajes de error específicos
```

### 3. **Caso de Error - Factura Ya Pagada**
```javascript
// Factura ya pagada
const paidInvoiceData = {
  factura_id: 2, // Ya pagada
  city: "Bogotá",
  address: "Calle 123 #45-67"
};

// Resultado esperado: "La factura ya está pagada"
```

## 🔧 Configuración del Entorno

### 1. **Variables de Entorno Requeridas**
```bash
# ePayco Configuration
EPAYCO_PUBLIC_KEY=your_public_key
EPAYCO_PRIVATE_KEY=your_private_key
EPAYCO_TEST_MODE=true
EPAYCO_MERCHANT_ID=your_merchant_id

# URLs
BASE_URL=https://api.biogenetic.com.co/
PAYMENT_RESPONSE_URL=https://api.biogenetic.com.co/api/pagos/response
PAYMENT_CONFIRMATION_URL=https://api.biogenetic.com.co/api/pagos/confirmation
```

### 2. **Configuración de CORS**
```python
# En main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://biogenetic.com.co"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## 📱 Integración con Frontend

### 1. **React/Vue/Angular**
```javascript
// Ejemplo de integración con React
import { useState, useEffect } from 'react';

function PaymentInterface() {
  const [facturas, setFacturas] = useState([]);
  const [bancos, setBancos] = useState([]);
  const [selectedFactura, setSelectedFactura] = useState(null);
  const [selectedBanco, setSelectedBanco] = useState(null);
  
  useEffect(() => {
    loadFacturas();
    loadBancos();
  }, []);
  
  // ... resto de la implementación
}
```

### 2. **Vanilla JavaScript**
```javascript
// Ejemplo de integración con JavaScript puro
class PaymentInterface {
  constructor() {
    this.facturas = [];
    this.bancos = [];
    this.selectedFactura = null;
    this.selectedBanco = null;
  }
  
  async init() {
    await this.loadFacturas();
    await this.loadBancos();
    this.setupEventListeners();
  }
  
  // ... resto de la implementación
}
```

## 🔗 URLs de Referencia

- **API de Bancos**: `GET /api/pagos/banks`
- **Crear Pago PSE**: `POST /api/pagos/pse/create`
- **Estado de Pago**: `GET /api/pagos/{pago_id}/status`
- **Lista de Facturas**: `GET /api/facturacion/?estado=pendiente`
- **Documentación Swagger**: `http://localhost:8000/docs`
- **ePayco Documentation**: `https://docs.epayco.com/`
- **PSE Colombia**: `https://www.pse.com.co/`
