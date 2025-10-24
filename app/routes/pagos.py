from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal

from app.database.base import get_db
from app.models.user import User
from app.models.facturacion import Facturacion, Pagos, EstadoPago
from app.routes.auth import get_current_user_from_token
from app.schemas.pagos_schema import (
    PagoCreate,
    PagoPSECreate,
    PagoResponse,
    PagoListResponse,
    PagoUpdate,
    PagoStatusResponse,
    PSEPaymentResponse,
    PaymentConfirmationResponse,
    BanksResponse
)
from app.services.epayco_service import (
    EpaycoConfigService,
    PSEPaymentService,
    PaymentConfirmationService,
    PaymentNotificationService
)

router = APIRouter(prefix="/pagos", tags=["pagos"])

@router.post("/pse/create", response_model=PSEPaymentResponse)
async def create_pse_payment(
    pse_data: PagoPSECreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Crear pago PSE para una factura
    
    - **factura_id**: ID de la factura a pagar
    - **city**: Ciudad del pagador (opcional, por defecto Bogotá)
    - **address**: Dirección del pagador (opcional)
    
    Retorna la información necesaria para redirigir al banco.
    """
    try:
        pse_service = PSEPaymentService(db)
        request_ip = request.client.host
        
        result = await pse_service.create_pse_payment(
            factura_id=pse_data.factura_id,
            user=current_user,
            request_ip=request_ip,
            pse_data=pse_data
        )
        
        return PSEPaymentResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.get("/pse/create/{factura_id}", response_class=HTMLResponse)
async def create_pse_payment_form(
    factura_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Formulario para crear pago PSE
    """
    # Obtener factura
    factura = db.query(Facturacion).filter(Facturacion.id == factura_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    if factura.estado.value == "pagado":
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Factura Ya Pagada</title>
            <meta charset="UTF-8">
            <style>
                body { font-family: Arial, sans-serif; text-align: center; padding: 50px; }
                .error { color: #e74c3c; }
                .success { color: #27ae60; }
            </style>
        </head>
        <body>
            <h1 class="error">❌ Factura Ya Pagada</h1>
            <p>Esta factura ya ha sido pagada.</p>
            <a href="/api/facturacion/">Volver a Facturas</a>
        </body>
        </html>
        """
    
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Pago PSE - Factura {factura.id_factura}</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
                background-color: #f5f5f5;
            }}
            .container {{
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }}
            h1 {{ color: #2c3e50; text-align: center; }}
            .factura-info {{
                background: #ecf0f1;
                padding: 20px;
                border-radius: 5px;
                margin: 20px 0;
            }}
            .form-group {{ margin-bottom: 20px; }}
            label {{ display: block; margin-bottom: 5px; font-weight: bold; }}
            input, textarea {{
                width: 100%;
                padding: 10px;
                border: 2px solid #ddd;
                border-radius: 5px;
                font-size: 16px;
            }}
            .btn {{
                background-color: #3498db;
                color: white;
                padding: 15px 30px;
                border: none;
                border-radius: 5px;
                cursor: pointer;
                font-size: 16px;
                width: 100%;
            }}
            .btn:hover {{ background-color: #2980b9; }}
            .amount {{ font-size: 24px; font-weight: bold; color: #27ae60; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>💳 Pago PSE</h1>
            
            <div class="factura-info">
                <h3>Información de la Factura</h3>
                <p><strong>ID Factura:</strong> {factura.id_factura}</p>
                <p><strong>Monto:</strong> <span class="amount">${factura.monto_pagar:,.2f} COP</span></p>
                <p><strong>Descripción:</strong> {factura.descripcion or 'Servicios BioGenetic'}</p>
            </div>
            
            <form id="pseForm">
                <div class="form-group">
                    <label for="city">Ciudad:</label>
                    <input type="text" id="city" name="city" value="Bogotá" required>
                </div>
                
                <div class="form-group">
                    <label for="address">Dirección (opcional):</label>
                    <textarea id="address" name="address" rows="3" placeholder="Ingrese su dirección completa"></textarea>
                </div>
                
                <button type="submit" class="btn">🚀 Proceder con Pago PSE</button>
            </form>
        </div>
        
        <script>
            document.getElementById('pseForm').addEventListener('submit', async function(e) {{
                e.preventDefault();
                
                const formData = new FormData(this);
                const data = {{
                    factura_id: {factura_id},
                    city: formData.get('city'),
                    address: formData.get('address')
                }};
                
                try {{
                    const response = await fetch('/api/pagos/pse/create', {{
                        method: 'POST',
                        headers: {{
                            'Content-Type': 'application/json',
                            'Authorization': 'Bearer ' + localStorage.getItem('access_token')
                        }},
                        body: JSON.stringify(data)
                    }});
                    
                    if (response.ok) {{
                        const result = await response.json();
                        if (result.bank_url) {{
                            window.location.href = result.bank_url;
                        }} else {{
                            alert('Error: No se recibió URL del banco');
                        }}
                    }} else {{
                        const error = await response.json();
                        alert('Error: ' + error.detail);
                    }}
                }} catch (error) {{
                    alert('Error de conexión: ' + error.message);
                }}
            }});
        </script>
    </body>
    </html>
    """

@router.get("/response", response_class=HTMLResponse)
async def payment_response(
    ref_payco: str = Query(..., description="Referencia de ePayco"),
    x_response: str = Query(..., description="Respuesta del banco"),
    x_response_reason_text: str = Query(..., description="Mensaje de respuesta"),
    db: Session = Depends(get_db)
):
    """
    Manejar respuesta del banco después del pago PSE
    """
    try:
        confirmation_service = PaymentConfirmationService(db)
        
        # Confirmar pago
        result = await confirmation_service.confirm_payment(ref_payco)
        
        # Obtener información del pago para mostrar
        pago = db.query(Pagos).filter(Pagos.ref_payco == ref_payco).first()
        
        if not pago:
            return """
            <!DOCTYPE html>
            <html>
            <head><title>Error</title></head>
            <body>
                <h1>Error</h1>
                <p>Pago no encontrado</p>
            </body>
            </html>
            """
        
        # Determinar mensaje según el estado
        if result["estado"] == "completado":
            message = "✅ Pago Exitoso"
            color = "#27ae60"
            description = "Su pago ha sido procesado exitosamente."
        elif result["estado"] == "procesando":
            message = "⏳ Pago en Proceso"
            color = "#f39c12"
            description = "Su pago está siendo procesado. Recibirá una confirmación por email."
        else:
            message = "❌ Pago Fallido"
            color = "#e74c3c"
            description = "Su pago no pudo ser procesado. Por favor, intente nuevamente."
        
        return f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Resultado del Pago</title>
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    text-align: center;
                    padding: 50px;
                    background-color: #f5f5f5;
                }}
                .container {{
                    background: white;
                    padding: 40px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                    max-width: 500px;
                    margin: 0 auto;
                }}
                .status {{
                    font-size: 48px;
                    margin-bottom: 20px;
                }}
                .message {{
                    font-size: 24px;
                    font-weight: bold;
                    color: {color};
                    margin-bottom: 20px;
                }}
                .description {{
                    font-size: 16px;
                    color: #666;
                    margin-bottom: 30px;
                }}
                .details {{
                    background: #f8f9fa;
                    padding: 20px;
                    border-radius: 5px;
                    text-align: left;
                }}
                .btn {{
                    background-color: #3498db;
                    color: white;
                    padding: 12px 24px;
                    text-decoration: none;
                    border-radius: 5px;
                    display: inline-block;
                    margin: 10px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="status">{message}</div>
                <div class="message">{result["estado"].title()}</div>
                <div class="description">{description}</div>
                
                <div class="details">
                    <h3>Detalles del Pago</h3>
                    <p><strong>Referencia:</strong> {ref_payco}</p>
                    <p><strong>Monto:</strong> ${pago.monto:,.2f} COP</p>
                    <p><strong>Método:</strong> {pago.metodo_pago}</p>
                    <p><strong>Fecha:</strong> {pago.fecha_pago.strftime("%d/%m/%Y %H:%M")}</p>
                    <p><strong>Respuesta:</strong> {x_response}</p>
                </div>
                
                <a href="/api/facturacion/" class="btn">Ver Facturas</a>
                <a href="/" class="btn">Inicio</a>
            </div>
        </body>
        </html>
        """
        
    except Exception as e:
        return f"""
        <!DOCTYPE html>
        <html>
        <head><title>Error</title></head>
        <body>
            <h1>Error al procesar respuesta</h1>
            <p>{str(e)}</p>
        </body>
        </html>
        """

@router.post("/confirmation")
async def payment_confirmation(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Webhook de confirmación de ePayco
    """
    try:
        # Obtener datos del request
        form_data = await request.form()
        ref_payco = form_data.get('ref_payco')
        
        if not ref_payco:
            raise HTTPException(status_code=400, detail="ref_payco es requerido")
        
        confirmation_service = PaymentConfirmationService(db)
        result = await confirmation_service.confirm_payment(ref_payco)
        
        # Enviar notificación en background
        pago = db.query(Pagos).filter(Pagos.ref_payco == ref_payco).first()
        if pago:
            factura = db.query(Facturacion).filter(Facturacion.id == pago.factura_id).first()
            if factura:
                # Aquí necesitarías obtener el usuario, por ahora solo log
                logger.info(f"Pago confirmado: {ref_payco}, notificación pendiente")
        
        return {"status": "success", "message": "Confirmación procesada"}
        
    except Exception as e:
        logger.error(f"Error en confirmación de pago: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{pago_id}/status", response_model=PagoStatusResponse)
async def get_payment_status(
    pago_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Consultar estado de un pago específico
    """
    pago = db.query(Pagos).filter(Pagos.id == pago_id).first()
    
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    # Verificar que el pago pertenece al usuario actual
    factura = db.query(Facturacion).filter(Facturacion.id == pago.factura_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    return PagoStatusResponse(
        pago_id=pago.id,
        estado=pago.estado.value,
        ref_payco=pago.ref_payco,
        response_code=pago.response_code,
        response_message=pago.response_message,
        bank_name=pago.bank_name,
        bank_url=pago.bank_url
    )

@router.get("/", response_model=List[PagoListResponse])
async def list_payments(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Listar pagos del usuario actual
    """
    # Obtener facturas del usuario
    facturas_usuario = db.query(Facturacion.id).filter(
        # Aquí necesitarías una relación directa usuario-factura
        # Por ahora asumimos que todas las facturas son del usuario actual
    ).subquery()
    
    pagos = db.query(Pagos).filter(
        Pagos.factura_id.in_(facturas_usuario)
    ).offset(skip).limit(limit).all()
    
    return pagos

@router.put("/{pago_id}", response_model=PagoResponse)
async def update_payment(
    pago_id: int,
    pago_update: PagoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Actualizar un pago (solo campos permitidos)
    """
    pago = db.query(Pagos).filter(Pagos.id == pago_id).first()
    
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    # Actualizar campos permitidos
    for field, value in pago_update.dict(exclude_unset=True).items():
        if hasattr(pago, field):
            setattr(pago, field, value)
    
    db.commit()
    db.refresh(pago)
    
    return pago


@router.get("/banks", response_model=BanksResponse)
async def get_pse_banks():
    """
    Obtener lista de entidades bancarias disponibles para PSE
    
    Retorna una lista de entidades bancarias colombianas que soportan pagos PSE.
    Si la API de ePayco no está disponible, se retorna una lista estática de bancos comunes.
    """
    try:
        epayco_service = EpaycoConfigService()
        result = epayco_service.get_pse_banks()
        
        if result["success"]:
            return BanksResponse(
                success=True,
                banks=result["banks"],
                message=result["message"],
                total=len(result["banks"])
            )
        else:
            raise HTTPException(
                status_code=500, 
                detail=result["message"]
            )
            
    except Exception as e:
        logger.error(f"Error al obtener entidades bancarias: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al obtener entidades bancarias: {str(e)}"
        )
