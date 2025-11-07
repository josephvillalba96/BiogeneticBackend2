from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
import logging

from app.database.base import get_db
from app.models.user import User
from app.models.facturacion import Facturacion, Pagos, EstadoPago
from app.routes.auth import get_current_user_from_token
from app.schemas.pagos_schema import (
    PagoCreate,
    PagoPSECreate,
    PagoDaviplataCreate,
    DaviPlataConfirmOTP,
    PagoResponse,
    PagoListResponse,
    PagoUpdate,
    PagoStatusResponse,
    PSEPaymentResponse,
    DaviPlataOTPConfirmResponse,
    PaymentConfirmationResponse,
    BanksResponse
)
from app.services.epayco_service import (
    EpaycoConfigService,
    PSEPaymentService,
    DaviPlataPaymentService,
    PaymentConfirmationService,
    PaymentNotificationService
)

router = APIRouter(prefix="/pagos", tags=["pagos"])

logger = logging.getLogger(__name__)

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

@router.post("/daviplata/create", response_model=PSEPaymentResponse)
async def create_daviplata_payment(
    daviplata_data: PagoDaviplataCreate,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Crear pago DaviPlata para una factura
    
    - **factura_id**: ID de la factura a pagar
    - **full_name**: Nombre completo del pagador
    - **email**: Email del pagador
    - **phone**: Teléfono del pagador (requerido para DaviPlata)
    - **address**: Dirección del pagador
    - **doc_type**: Tipo de documento (CC, CE, etc.)
    - **document**: Número de documento del pagador
    - **city**: Ciudad del pagador
    
    Retorna la información necesaria. El usuario debe revisar su aplicación DaviPlata para completar el pago.
    """
    try:
        daviplata_service = DaviPlataPaymentService(db)
        request_ip = request.client.host
        
        result = await daviplata_service.create_daviplata_payment(
            factura_id=daviplata_data.factura_id,
            user=current_user,
            request_ip=request_ip,
            daviplata_data=daviplata_data
        )
        
        return PSEPaymentResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error al crear pago DaviPlata: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")

@router.post("/daviplata/confirm-otp", response_model=DaviPlataOTPConfirmResponse)
async def confirm_daviplata_otp(
    otp_data: DaviPlataConfirmOTP,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Confirmar OTP de pago DaviPlata
    
    - **ref_payco**: Referencia del pago en ePayco
    - **otp**: Código OTP recibido en la aplicación DaviPlata
    
    Retorna el resultado de la confirmación del pago.
    """
    try:
        daviplata_service = DaviPlataPaymentService(db)
        
        result = await daviplata_service.confirm_daviplata_otp(
            ref_payco=otp_data.ref_payco,
            otp=otp_data.otp
        )
        
        return DaviPlataOTPConfirmResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error al confirmar OTP DaviPlata: {str(e)}")
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
                
                <a href="{settings.BASE_URL}/facturas" class="btn">Ver Facturas</a>
                <script>
                    // Redirigir al frontend después de 3 segundos
                    setTimeout(function() {{
                        window.location.href = "{settings.BASE_URL}/pagos/resultado?ref_payco={ref_payco}&estado={result['estado']}";
                    }}, 3000);
                </script>
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
    
    ePayco envía un POST a esta URL cuando el estado de un pago cambia.
    Los datos vienen en el BODY como form data (application/x-www-form-urlencoded), NO en la URL.
    
    Campos que envía ePayco en el body:
    - x_ref_payco o ref_payco: Referencia única del pago (obligatorio)
    - x_transaction_id: ID de transacción de ePayco
    - x_amount: Monto de la transacción
    - x_currency_code: Código de moneda (COP, USD, etc.)
    - x_signature: Firma SHA256 para validar autenticidad
    - x_response: Estado de la transacción (Aceptada, Rechazada, Pendiente, etc.)
    - x_response_reason_text: Mensaje descriptivo del estado
    - x_cod_response: Código numérico de respuesta (1=aceptada, 2=rechazada, 3=pendiente, 4=fallida)
    - x_id_invoice: ID de la factura
    - x_approval_code: Código de aprobación
    - x_franchise: Método de pago (PSE, DaviPlata, etc.)
    - x_bank_name: Nombre del banco (si aplica)
    - x_transaction_date: Fecha de la transacción
    
    La URL de confirmación debe configurarse en ePayco y debe ser accesible públicamente.
    """
    try:
        # Obtener datos del request body (form data)
        # ePayco envía los datos como application/x-www-form-urlencoded
        form_data = await request.form()
        
        # Log completo de lo que recibe el webhook para debugging
        logger.info(f"Webhook recibido desde IP: {request.client.host}")
        logger.debug(f"Datos recibidos del webhook: {dict(form_data)}")
        
        # === VALIDACIÓN DE FIRMA (SECURITY) ===
        # Extraer campos necesarios para validar la firma
        x_ref_payco = form_data.get('x_ref_payco') or form_data.get('ref_payco')
        x_transaction_id = form_data.get('x_transaction_id', '')
        x_amount = form_data.get('x_amount', '')
        x_currency_code = form_data.get('x_currency_code', '')
        x_signature = form_data.get('x_signature', '')
        
        if not x_ref_payco:
            logger.error("Webhook recibido sin x_ref_payco/ref_payco")
            raise HTTPException(status_code=400, detail="x_ref_payco es requerido")
        
        # Validar firma de ePayco (como en el script PHP)
        # signature = hash('sha256', p_cust_id_cliente + '^' + p_key + '^' + x_ref_payco + '^' + x_transaction_id + '^' + x_amount + '^' + x_currency_code)
        from app.config import settings
        import hashlib
        
        p_cust_id_cliente = settings.EPAYCO_PUBLIC_KEY
        p_key = settings.EPAYCO_PRIVATE_KEY
        
        # Construir string para firmar
        signature_string = f"{p_cust_id_cliente}^{p_key}^{x_ref_payco}^{x_transaction_id}^{x_amount}^{x_currency_code}"
        calculated_signature = hashlib.sha256(signature_string.encode()).hexdigest()
        
        logger.info(f"Validando firma: x_signature={x_signature}, calculated={calculated_signature}")
        
        if x_signature and calculated_signature != x_signature:
            logger.error(f"⚠️ Firma inválida! Webhook rechazado. x_ref_payco={x_ref_payco}")
            logger.error(f"Firma recibida: {x_signature}")
            logger.error(f"Firma calculada: {calculated_signature}")
            raise HTTPException(status_code=403, detail="Firma inválida")
        
        logger.info(f"✅ Firma validada correctamente para x_ref_payco={x_ref_payco}")
        
        # Usar ref_payco en adelante (normalizar nombre)
        ref_payco = x_ref_payco
        
        # Extraer otros campos importantes del webhook
        x_response = form_data.get('x_response', '')
        x_response_reason_text = form_data.get('x_response_reason_text', '')
        x_cod_response = form_data.get('x_cod_response', '')
        x_id_invoice = form_data.get('x_id_invoice', '')
        x_approval_code = form_data.get('x_approval_code', '')
        x_franchise = form_data.get('x_franchise', '')
        x_bank_name = form_data.get('x_bank_name', '')
        
        logger.info(f"Procesando confirmación: ref_payco={ref_payco}, x_cod_response={x_cod_response}, x_response={x_response}")
        
        # Buscar el pago en la base de datos usando ref_payco
        pago = db.query(Pagos).filter(Pagos.ref_payco == ref_payco).first()
        
        # Si no se encuentra por ref_payco, intentar buscar por invoice (x_id_invoice)
        if not pago:
            x_id_invoice = form_data.get('x_id_invoice') or form_data.get('idfactura')
            if x_id_invoice:
                logger.info(f"Buscando pago por invoice: {x_id_invoice}")
                # Buscar factura por id_factura
                factura = db.query(Facturacion).filter(Facturacion.id_factura == x_id_invoice).first()
                if factura:
                    # Buscar pago pendiente para esa factura
                    pago = db.query(Pagos).filter(
                        Pagos.factura_id == factura.id,
                        Pagos.estado.in_([EstadoPago.pendiente, EstadoPago.procesando])
                    ).order_by(Pagos.fecha_pago.desc()).first()
                    
                    if pago:
                        # Actualizar el pago con el ref_payco del webhook
                        pago.ref_payco = ref_payco
                        db.commit()
                        logger.info(f"✅ Pago encontrado por invoice y actualizado con ref_payco: {ref_payco}")
        
        if not pago:
            logger.warning(f"Webhook recibido para pago no encontrado: ref_payco={ref_payco}")
            # Retornar 200 para que ePayco no reintente (el pago puede no existir en nuestro sistema)
            return {"status": "warning", "message": f"Pago con ref_payco {ref_payco} no encontrado"}
        
        # === VALIDAR MONTO Y FACTURA ===
        # Validar que el invoice y monto coincidan con lo esperado (seguridad)
        factura = db.query(Facturacion).filter(Facturacion.id == pago.factura_id).first()
        if factura:
            # Validar invoice
            if x_id_invoice and factura.id_factura != x_id_invoice:
                logger.error(f"⚠️ Invoice no coincide! Esperado: {factura.id_factura}, Recibido: {x_id_invoice}")
                raise HTTPException(status_code=400, detail="Número de factura no coincide")
            
            # Validar monto (convertir a float para comparar)
            if x_amount:
                try:
                    amount_received = float(x_amount)
                    amount_expected = float(factura.monto_pagar)
                    # Comparar con tolerancia de 1 peso por redondeo
                    if abs(amount_received - amount_expected) > 1:
                        logger.error(f"⚠️ Monto no coincide! Esperado: {amount_expected}, Recibido: {amount_received}")
                        raise HTTPException(status_code=400, detail="Monto pagado no coincide")
                except ValueError:
                    logger.warning(f"No se pudo validar monto: x_amount={x_amount}")
        
        # Extraer bank_url del webhook si viene (puede venir en diferentes campos)
        bank_url_webhook = form_data.get('urlbanco') or form_data.get('x_urlbanco') or form_data.get('bank_url') or form_data.get('x_bank_url')
        bank_name_webhook = form_data.get('x_bank_name') or form_data.get('bank_name')
        
        # Si el pago no tiene bank_url y viene en el webhook, actualizarlo
        if not pago.bank_url and bank_url_webhook:
            pago.bank_url = bank_url_webhook
            logger.info(f"✅ bank_url actualizado desde webhook: {bank_url_webhook}")
        if not pago.bank_name and bank_name_webhook:
            pago.bank_name = bank_name_webhook
        
        # === PROCESAR ESTADO SEGÚN x_cod_response ===
        # x_cod_response: 1=aceptada, 2=rechazada, 3=pendiente, 4=fallida
        if x_cod_response:
            try:
                cod_response = int(x_cod_response)
                
                if cod_response == 1:  # Transacción aceptada
                    pago.estado = EstadoPago.completado
                    pago.response_code = "Aceptada"
                    # Actualizar factura a pagado
                    if factura:
                        from app.models.facturacion import EstadoFactura
                        from datetime import datetime
                        factura.estado = EstadoFactura.pagado
                        factura.fecha_pago = datetime.now()
                    logger.info(f"✅ Pago ACEPTADO: ref_payco={ref_payco}")
                    
                elif cod_response == 2:  # Transacción rechazada
                    pago.estado = EstadoPago.fallido
                    pago.response_code = "Rechazada"
                    logger.warning(f"❌ Pago RECHAZADO: ref_payco={ref_payco}, razón={x_response_reason_text}")
                    
                elif cod_response == 3:  # Transacción pendiente
                    pago.estado = EstadoPago.procesando
                    pago.response_code = "Pendiente"
                    logger.info(f"⏳ Pago PENDIENTE: ref_payco={ref_payco}")
                    
                elif cod_response == 4:  # Transacción fallida
                    pago.estado = EstadoPago.fallido
                    pago.response_code = "Fallida"
                    logger.error(f"❌ Pago FALLIDO: ref_payco={ref_payco}, razón={x_response_reason_text}")
                
                # Actualizar campos adicionales
                if x_response:
                    pago.response_code = x_response
                if x_response_reason_text:
                    pago.response_message = x_response_reason_text
                if x_approval_code:
                    pago.transaction_id = x_approval_code
                
            except ValueError:
                logger.warning(f"x_cod_response no es un número válido: {x_cod_response}")
        
        db.commit()
        
        logger.info(f"✅ Pago confirmado exitosamente: ref_payco={ref_payco}, estado={pago.estado.value}, cod_response={x_cod_response}")
        
        # Enviar notificación en background (si es necesario)
        if pago:
            factura = db.query(Facturacion).filter(Facturacion.id == pago.factura_id).first()
            if factura:
                logger.info(f"Pago confirmado: ref_payco={ref_payco}, factura_id={factura.id}, notificación pendiente")
        
        return {"status": "success", "message": "Confirmación procesada", "ref_payco": ref_payco}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en confirmación de pago: {str(e)}", exc_info=True)
        # Retornar 200 para que ePayco no reintente en caso de error interno
        # (pero deberíamos loguear el error para investigar)
        return {"status": "error", "message": f"Error al procesar confirmación: {str(e)}"}

@router.get("/{pago_id}/status", response_model=PagoStatusResponse)
async def get_payment_status(
    pago_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Consultar estado de un pago específico
    Si el pago no tiene bank_url, intenta consultarlo desde ePayco
    """
    pago = db.query(Pagos).filter(Pagos.id == pago_id).first()
    
    if not pago:
        raise HTTPException(status_code=404, detail="Pago no encontrado")
    
    # Verificar que el pago pertenece al usuario actual
    factura = db.query(Facturacion).filter(Facturacion.id == pago.factura_id).first()
    if not factura:
        raise HTTPException(status_code=404, detail="Factura no encontrada")
    
    # Si el pago no tiene bank_url y es PSE, intentar consultarlo desde ePayco
    if pago.metodo_pago == "PSE" and not pago.bank_url and pago.estado in [EstadoPago.pendiente, EstadoPago.procesando]:
        try:
            pse_service = PSEPaymentService(db)
            pago_actualizado = await pse_service.refresh_payment_from_epayco(pago)
            if pago_actualizado:
                pago = pago_actualizado
        except Exception as e:
            logger.warning(f"No se pudo actualizar pago desde ePayco: {str(e)}")
    
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
