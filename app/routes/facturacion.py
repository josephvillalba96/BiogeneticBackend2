from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import io
import traceback
import logging

from app.database.base import get_db
from app.models.user import User
from app.routes.auth import get_current_user_from_token
from app.schemas.facturacion_schema import (
    FacturacionCreate,
    FacturacionUpdate,
    FacturacionResponse,
    FacturacionListResponse,
    FacturaFormData,
    FacturaFormResponse
)
from app.services.facturacion_service import (
    create_factura_with_details,
    create_factura_from_form,
    get_factura_by_id,
    list_facturas,
    update_factura,
    delete_factura,
    get_factura_completa,
    get_factura_summary,
    get_factura_detalles
)
from app.services.factura_pdf_service import render_factura_html, html_to_pdf_bytes

router = APIRouter(prefix="/facturacion", tags=["facturación"])

@router.post("", response_model=FacturacionResponse)
async def create_factura(
    factura_data: FacturacionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Crear una nueva factura con sus detalles
    
    **Campos requeridos:**
    - **cliente_id**: ID del cliente al que pertenece la factura
    - **items**: Lista de items de la factura
    
    **Campos opcionales:**
    - **monto_pagar**: Monto total (se calcula automáticamente si no se proporciona)
    - **monto_base**: Monto base sin IVA (se calcula automáticamente)
    - **iva**: Porcentaje de IVA (default: 19.0)
    - **valor_iva**: Valor del IVA (se calcula automáticamente)
    - **descripcion**: Descripción de la factura
    - **fecha_vencimiento**: Fecha límite de pago
    - **aplica_iva**: Si aplica IVA a la factura (default: true)
    
    **Ejemplo de payload:**
    ```json
    {
        "cliente_id": 123,
        "items": [
            {"nombre": "Embrión fresco", "valor": 50000.00},
            {"nombre": "Nitrógeno", "valor": 25000.00}
        ],
        "descripcion": "Servicios BioGenetic",
        "fecha_vencimiento": "2024-02-15T23:59:59",
        "aplica_iva": true,
        "iva": 19.0
    }
    ```
    """
    try:
        factura = create_factura_with_details(db, factura_data, current_user)
        return factura
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Error de validación: {str(e)}")
    except Exception as e:
        import traceback
        error_detail = f"Error interno: {str(e)}\nTraceback: {traceback.format_exc()}"
        raise HTTPException(status_code=500, detail=error_detail)


@router.get("", response_model=List[FacturacionListResponse])
async def list_facturas_endpoint(
    skip: int = Query(0, ge=0, description="Número de registros a omitir"),
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de registros"),
    estado: Optional[str] = Query(None, description="Filtrar por estado"),
    fecha_desde: Optional[datetime] = Query(None, description="Fecha desde"),
    fecha_hasta: Optional[datetime] = Query(None, description="Fecha hasta"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Listar facturas con paginación y filtros
    
    - **skip**: Número de registros a omitir
    - **limit**: Número máximo de registros (máximo 1000)
    - **estado**: Filtrar por estado (pendiente, vencido, pagado)
    - **fecha_desde**: Filtrar desde fecha
    - **fecha_hasta**: Filtrar hasta fecha
    
    Los clientes solo ven sus propias facturas.
    Los administradores y veterinarios ven todas las facturas.
    """
    try:
        facturas, total = list_facturas(
            db=db,
            user=current_user,
            skip=skip,
            limit=limit,
            estado=estado,
            fecha_desde=fecha_desde,
            fecha_hasta=fecha_hasta
        )
        
        return facturas
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al listar facturas: {str(e)}")


@router.post("/from-form", response_model=FacturacionResponse)
async def create_factura_from_form_endpoint(
    form_data: FacturaFormData,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Crear factura desde formulario con items específicos
    """
    try:
        factura = create_factura_from_form(db, form_data, current_user)
        return factura
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")




@router.get("/form", response_class=HTMLResponse)
async def factura_form(request: Request):
    """
    Formulario para crear facturas con items específicos
    """
    return """
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Crear Factura - BioGenetic</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #2c3e50;
                text-align: center;
                margin-bottom: 30px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
                color: #34495e;
            }
            input[type="text"], input[type="number"], textarea, select {
                width: 100%;
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
                transition: border-color 0.3s;
            }
            input[type="text"]:focus, input[type="number"]:focus, textarea:focus, select:focus {
                outline: none;
                border-color: #3498db;
            }
            .item-row {
                display: flex;
                align-items: center;
                margin-bottom: 15px;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 5px;
                border-left: 4px solid #3498db;
            }
            .item-label {
                flex: 1;
                font-weight: bold;
                color: #2c3e50;
            }
            .item-input {
                flex: 0 0 200px;
                margin-left: 15px;
            }
            .total-section {
                background-color: #e8f5e8;
                padding: 20px;
                border-radius: 5px;
                margin-top: 20px;
                text-align: center;
            }
            .total-amount {
                font-size: 24px;
                font-weight: bold;
                color: #27ae60;
            }
            .btn {
                background-color: #3498db;
                color: white;
                padding: 12px 30px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                margin: 10px 5px;
                transition: background-color 0.3s;
            }
            .btn:hover {
                background-color: #2980b9;
            }
            .btn-success {
                background-color: #27ae60;
            }
            .btn-success:hover {
                background-color: #229954;
            }
            .currency {
                color: #7f8c8d;
                font-size: 14px;
            }
            .description-group {
                margin-top: 20px;
            }
            .description-group textarea {
                height: 80px;
                resize: vertical;
            }
            .iva-section {
                background-color: #fff3cd;
                padding: 15px;
                border-radius: 5px;
                margin: 20px 0;
                border-left: 4px solid #ffc107;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>💰 Crear Nueva Factura</h1>
            
            <form id="facturaForm">
                <h3>Items de Facturación</h3>
                
                <div class="item-row">
                    <div class="item-label">Embrión fresco</div>
                    <div class="item-input">
                        <input type="number" id="embrio_fresco" name="embrio_fresco" 
                               step="0.01" min="0" placeholder="0.00" oninput="calculateTotal()">
                        <span class="currency">COP</span>
                    </div>
                </div>

                <div class="item-row">
                    <div class="item-label">Embrión congelado</div>
                    <div class="item-input">
                        <input type="number" id="embrio_congelado" name="embrio_congelado" 
                               step="0.01" min="0" placeholder="0.00" oninput="calculateTotal()">
                        <span class="currency">COP</span>
                    </div>
                </div>

                <div class="item-row">
                    <div class="item-label">Material de campo</div>
                    <div class="item-input">
                        <input type="number" id="material_campo" name="material_campo" 
                               step="0.01" min="0" placeholder="0.00" oninput="calculateTotal()">
                        <span class="currency">COP</span>
                    </div>
                </div>

                <div class="item-row">
                    <div class="item-label">Nitrógeno</div>
                    <div class="item-input">
                        <input type="number" id="nitrogeno" name="nitrogeno" 
                               step="0.01" min="0" placeholder="0.00" oninput="calculateTotal()">
                        <span class="currency">COP</span>
                    </div>
                </div>

                <div class="item-row">
                    <div class="item-label">Mensajería</div>
                    <div class="item-input">
                        <input type="number" id="mensajeria" name="mensajeria" 
                               step="0.01" min="0" placeholder="0.00" oninput="calculateTotal()">
                        <span class="currency">COP</span>
                    </div>
                </div>

                <div class="item-row">
                    <div class="item-label">Pajilla de semen</div>
                    <div class="item-input">
                        <input type="number" id="pajilla_semen" name="pajilla_semen" 
                               step="0.01" min="0" placeholder="0.00" oninput="calculateTotal()">
                        <span class="currency">COP</span>
                    </div>
                </div>

                <div class="item-row">
                    <div class="item-label">Fundas T.E</div>
                    <div class="item-input">
                        <input type="number" id="fundas_te" name="fundas_te" 
                               step="0.01" min="0" placeholder="0.00" oninput="calculateTotal()">
                        <span class="currency">COP</span>
                    </div>
                </div>

                <div class="iva-section">
                    <h3>Configuración de IVA</h3>
                    <div class="form-group">
                        <label>
                            <input type="checkbox" id="aplica_iva" name="aplica_iva" checked onchange="calculateTotal()">
                            Aplicar IVA a esta factura
                        </label>
                    </div>
                    <div class="form-group">
                        <label for="iva_porcentaje">Porcentaje de IVA:</label>
                        <input type="number" id="iva_porcentaje" name="iva_porcentaje" 
                               step="0.01" min="0" max="100" value="19.00" oninput="calculateTotal()">
                    </div>
                </div>

                <div class="total-section">
                    <h3>Resumen de Facturación</h3>
                    <p><strong>Monto Base:</strong> <span id="montoBase">$0.00 COP</span></p>
                    <p><strong>IVA (<span id="ivaPorcentaje">19.00</span>%):</strong> <span id="valorIva">$0.00 COP</span></p>
                    <div class="total-amount" id="totalAmount">$0.00 COP</div>
                </div>

                <div class="description-group">
                    <label for="descripcion">Descripción adicional (opcional):</label>
                    <textarea id="descripcion" name="descripcion" 
                              placeholder="Agregue cualquier descripción adicional para la factura..."></textarea>
                </div>

                <div class="form-group">
                    <label for="fecha_vencimiento">Fecha de vencimiento (opcional):</label>
                    <input type="datetime-local" id="fecha_vencimiento" name="fecha_vencimiento">
                </div>

                <div class="form-group">
                    <label for="cliente_id">Cliente:</label>
                    <select id="cliente_id" name="cliente_id" required>
                        <option value="">Seleccione un cliente</option>
                    </select>
                </div>

                <div style="text-align: center; margin-top: 30px;">
                    <button type="button" class="btn" onclick="calculateTotal()">🔄 Recalcular Total</button>
                    <button type="submit" class="btn btn-success">💾 Crear Factura</button>
                </div>
            </form>
        </div>

        <script>
            function calculateTotal() {
                const items = [
                    'embrio_fresco', 'embrio_congelado', 'material_campo', 
                    'nitrogeno', 'mensajeria', 'pajilla_semen', 'fundas_te'
                ];
                
                let montoBase = 0;
                items.forEach(itemId => {
                    const input = document.getElementById(itemId);
                    const value = parseFloat(input.value) || 0;
                    montoBase += value;
                });
                
                const aplicaIva = document.getElementById('aplica_iva').checked;
                const ivaPorcentaje = parseFloat(document.getElementById('iva_porcentaje').value) || 0;
                
                let valorIva = 0;
                let total = montoBase;
                
                if (aplicaIva) {
                    valorIva = montoBase * (ivaPorcentaje / 100);
                    total = montoBase + valorIva;
                }
                
                // Actualizar display
                document.getElementById('montoBase').textContent = 
                    '$' + montoBase.toLocaleString('es-CO', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' COP';
                
                document.getElementById('valorIva').textContent = 
                    '$' + valorIva.toLocaleString('es-CO', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' COP';
                
                document.getElementById('ivaPorcentaje').textContent = ivaPorcentaje.toFixed(2);
                
                document.getElementById('totalAmount').textContent = 
                    '$' + total.toLocaleString('es-CO', {minimumFractionDigits: 2, maximumFractionDigits: 2}) + ' COP';
            }

            document.getElementById('facturaForm').addEventListener('submit', async function(e) {
                e.preventDefault();
                
                const formData = new FormData(this);
                const data = {
                    embrio_fresco: parseFloat(formData.get('embrio_fresco')) || 0,
                    embrio_congelado: parseFloat(formData.get('embrio_congelado')) || 0,
                    material_campo: parseFloat(formData.get('material_campo')) || 0,
                    nitrogeno: parseFloat(formData.get('nitrogeno')) || 0,
                    mensajeria: parseFloat(formData.get('mensajeria')) || 0,
                    pajilla_semen: parseFloat(formData.get('pajilla_semen')) || 0,
                    fundas_te: parseFloat(formData.get('fundas_te')) || 0,
                    descripcion: formData.get('descripcion'),
                    fecha_vencimiento: formData.get('fecha_vencimiento') ? new Date(formData.get('fecha_vencimiento')).toISOString() : null,
                    cliente_id: parseInt(formData.get('cliente_id')),
                    aplica_iva: document.getElementById('aplica_iva').checked,
                    iva_porcentaje: parseFloat(formData.get('iva_porcentaje')) || 19.0
                };

                try {
                    const response = await fetch('/api/facturacion/from-form', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + localStorage.getItem('access_token')
                        },
                        body: JSON.stringify(data)
                    });

                    if (response.ok) {
                        const result = await response.json();
                        alert('✅ Factura creada exitosamente!\\nID de Factura: ' + result.id_factura);
                        this.reset();
                        calculateTotal();
                    } else {
                        const error = await response.json();
                        alert('❌ Error: ' + error.detail);
                    }
                } catch (error) {
                    alert('❌ Error de conexión: ' + error.message);
                }
            });

            // Cargar clientes al inicializar
            loadClients();
            
            // Función para cargar clientes
            async function loadClients() {
                try {
                    const response = await fetch('/api/users/', {
                        headers: {
                            'Authorization': 'Bearer ' + localStorage.getItem('access_token')
                        }
                    });
                    
                    if (response.ok) {
                        const users = await response.json();
                        const select = document.getElementById('cliente_id');
                        
                        users.forEach(user => {
                            const option = document.createElement('option');
                            option.value = user.id;
                            option.textContent = `${user.full_name} (${user.email})`;
                            select.appendChild(option);
                        });
                    } else {
                        console.error('Error al cargar clientes');
                    }
                } catch (error) {
                    console.error('Error de conexión al cargar clientes:', error);
                }
            }
            
            // Calcular total inicial
            calculateTotal();
        </script>
    </body>
    </html>
    """


@router.get("/{factura_id}", response_model=FacturacionResponse)
async def get_factura(
    factura_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtener una factura específica por ID
    """
    try:
        factura = get_factura_by_id(db, factura_id, current_user)
        if not factura:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        return factura
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener factura: {str(e)}")

@router.get("/{factura_id}/completa")
async def get_factura_completa_endpoint(
    factura_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtener una factura completa con sus detalles y pagos
    """
    try:
        return get_factura_completa(db, factura_id, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener factura completa: {str(e)}")

@router.put("/{factura_id}", response_model=FacturacionResponse)
async def update_factura_endpoint(
    factura_id: int,
    factura_update: FacturacionUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Actualizar una factura existente
    
    Solo se pueden actualizar ciertos campos:
    - **descripcion**: Descripción de la factura
    - **estado**: Estado de la factura
    - **fecha_pago**: Fecha de pago
    - **fecha_vencimiento**: Fecha límite de pago
    """
    try:
        return update_factura(db, factura_id, factura_update, current_user)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al actualizar factura: {str(e)}")

@router.delete("/{factura_id}")
async def delete_factura_endpoint(
    factura_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Eliminar una factura
    
    Solo se pueden eliminar facturas pendientes.
    Solo administradores y veterinarios pueden eliminar facturas.
    """
    try:
        success = delete_factura(db, factura_id, current_user)
        if success:
            return {"message": "Factura eliminada exitosamente"}
        else:
            raise HTTPException(status_code=500, detail="Error al eliminar factura")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al eliminar factura: {str(e)}")

@router.get("/{factura_id}/resumen")
async def get_factura_resumen(
    factura_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtener resumen de una factura
    """
    try:
        factura = get_factura_by_id(db, factura_id, current_user)
        if not factura:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        return get_factura_summary(factura)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener resumen: {str(e)}")

@router.get("/{factura_id}/detalles")
async def get_factura_detalles_endpoint(
    factura_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Obtener detalles de una factura
    """
    try:
        factura = get_factura_by_id(db, factura_id, current_user)
        if not factura:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        return get_factura_detalles(factura)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al obtener detalles: {str(e)}")


@router.get("/{factura_id}/pdf")
def generar_factura_pdf(
    factura_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Genera un PDF de la factura usando el template factura.html
    """
    try:
        # Verificar que la factura existe y el usuario tiene acceso
        factura = get_factura_by_id(db, factura_id, current_user)
        if not factura:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        # Renderizar HTML
        html = render_factura_html(db, factura_id, current_user)
        
        # Convertir a PDF
        pdf_bytes = html_to_pdf_bytes(html)
        
        # Preparar respuesta
        filename = f"factura_{factura.id_factura}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"inline; filename={filename}",
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        tb = traceback.format_exc()
        logger = logging.getLogger(__name__)
        logger.error(f"Error generando PDF para factura_id={factura_id}: {tb}")
        raise HTTPException(status_code=500, detail=f"Error generando PDF: {str(e)}")


@router.get("/{factura_id}/html")
def previsualizar_factura_html(
    factura_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Previsualiza el HTML de la factura (para testing)
    """
    try:
        # Verificar que la factura existe y el usuario tiene acceso
        factura = get_factura_by_id(db, factura_id, current_user)
        if not factura:
            raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        # Renderizar HTML
        html = render_factura_html(db, factura_id, current_user)
        
        return HTMLResponse(content=html)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error renderizando HTML: {str(e)}")
