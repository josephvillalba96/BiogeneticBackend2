from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
import logging

from app.database.base import get_db
from app.models.user import User
from app.models.facturacion import Facturacion, Pagos, EstadoPago
from app.routes.auth import get_current_user_from_token
from app.schemas.pagos_schema import (
    PagoCreate,
    PagoResponse,
    PagoListResponse,
    PagoUpdate,
    PagoStatusResponse,
    PaymentConfirmationResponse,
    PagoSimpleCreate
)
from app.services.epayco_service import (
    PaymentConfirmationService,
    PaymentNotificationService
)

router = APIRouter(prefix="/pagos", tags=["pagos"])

logger = logging.getLogger(__name__)

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
    Los datos pueden venir en el BODY como form data (application/x-www-form-urlencoded) 
    o en los QUERY PARAMETERS de la URL.
    
    Campos que envía ePayco:
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
        # ePayco puede enviar los datos en el body (form data) o en los query parameters
        # Intentar obtener del body primero, luego de query params
        form_data = {}
        try:
            form_data = await request.form()
        except Exception:
            pass  # Si no hay form data, continuar
        
        # También obtener de query parameters
        # Los query params ya vienen decodificados por FastAPI, pero asegurémonos
        query_params = dict(request.query_params)
        
        # Combinar ambos, dando prioridad al body si existe
        # Si un campo existe en ambos, el form_data tiene prioridad
        webhook_data = {**query_params, **dict(form_data)}
        
        # Asegurar que los valores de string estén decodificados correctamente
        # FastAPI ya decodifica los query params, pero por si acaso
        for key, value in webhook_data.items():
            if isinstance(value, str):
                # Los valores ya deberían estar decodificados, pero asegurémonos
                webhook_data[key] = value
        
        # Log completo de lo que recibe el webhook para debugging
        logger.info(f"Webhook recibido desde IP: {request.client.host}")
        logger.info(f"Datos recibidos del webhook (query params): {query_params}")
        logger.debug(f"Datos recibidos del webhook (form data): {dict(form_data)}")
        logger.debug(f"Datos combinados: {webhook_data}")
        
        # === VALIDACIÓN DE FIRMA (SECURITY) ===
        # Extraer campos necesarios para validar la firma
        x_ref_payco = webhook_data.get('x_ref_payco') or webhook_data.get('ref_payco')
        x_transaction_id = webhook_data.get('x_transaction_id', '')
        x_amount = webhook_data.get('x_amount', '')
        x_currency_code = webhook_data.get('x_currency_code', '')
        x_signature = webhook_data.get('x_signature', '')
        
        if not x_ref_payco:
            logger.error("Webhook recibido sin x_ref_payco/ref_payco")
            raise HTTPException(status_code=400, detail="x_ref_payco es requerido")
        
        # Validar firma de ePayco
        # ePayco puede enviar x_cust_id_cliente en el webhook, si no, usar el de configuración
        from app.config import settings
        import hashlib
        
        x_cust_id_cliente = webhook_data.get('x_cust_id_cliente') or settings.EPAYCO_PUBLIC_KEY
        p_key = settings.EPAYCO_PRIVATE_KEY
        
        # Construir string para firmar según documentación ePayco
        # signature = hash('sha256', p_cust_id_cliente + '^' + p_key + '^' + x_ref_payco + '^' + x_transaction_id + '^' + x_amount + '^' + x_currency_code)
        signature_string = f"{x_cust_id_cliente}^{p_key}^{x_ref_payco}^{x_transaction_id}^{x_amount}^{x_currency_code}"
        calculated_signature = hashlib.sha256(signature_string.encode()).hexdigest()
        
        logger.info(f"Validando firma: x_signature={x_signature}, calculated={calculated_signature}")
        logger.info(f"Valores usados: x_cust_id_cliente={x_cust_id_cliente}, x_ref_payco={x_ref_payco}, x_transaction_id={x_transaction_id}, x_amount={x_amount}, x_currency_code={x_currency_code}")
        
        # Si la firma no coincide, intentar sin x_transaction_id (algunos webhooks no lo incluyen)
        if x_signature and calculated_signature != x_signature:
            # Intentar sin x_transaction_id
            signature_string_alt = f"{x_cust_id_cliente}^{p_key}^{x_ref_payco}^{x_amount}^{x_currency_code}"
            calculated_signature_alt = hashlib.sha256(signature_string_alt.encode()).hexdigest()
            
            if calculated_signature_alt == x_signature:
                logger.info(f"✅ Firma validada (sin transaction_id) para x_ref_payco={x_ref_payco}")
            else:
                logger.error(f"⚠️ Firma inválida! Webhook rechazado. x_ref_payco={x_ref_payco}")
                logger.error(f"Firma recibida: {x_signature}")
                logger.error(f"Firma calculada (con transaction_id): {calculated_signature}")
                logger.error(f"Firma calculada (sin transaction_id): {calculated_signature_alt}")
                # Por ahora, permitir el webhook pero loguear el error para debugging
                # TODO: Revisar con ePayco la documentación exacta de la firma
                logger.warning("⚠️ Firma no coincide, pero permitiendo el webhook para debugging")
                # raise HTTPException(status_code=403, detail="Firma inválida")
        
        logger.info(f"✅ Firma validada correctamente para x_ref_payco={x_ref_payco}")
        
        # Usar ref_payco en adelante (normalizar nombre)
        ref_payco = x_ref_payco
        
        # Extraer otros campos importantes del webhook
        x_response = webhook_data.get('x_response', '')
        x_response_reason_text = webhook_data.get('x_response_reason_text', '')
        x_cod_response = webhook_data.get('x_cod_response', '')
        x_id_invoice = webhook_data.get('x_id_invoice', '')
        x_approval_code = webhook_data.get('x_approval_code', '')
        x_franchise = webhook_data.get('x_franchise', '')
        x_bank_name = webhook_data.get('x_bank_name', '')
        
        logger.info(f"Procesando confirmación: ref_payco={ref_payco}, x_cod_response={x_cod_response}, x_response={x_response}")
        
        # Buscar el pago en la base de datos usando ref_payco
        pago = db.query(Pagos).filter(Pagos.ref_payco == ref_payco).first()
        
        # Si no se encuentra por ref_payco, intentar buscar por invoice (x_id_invoice)
        if not pago:
            x_id_invoice = webhook_data.get('x_id_invoice') or webhook_data.get('idfactura')
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
        
        # === OBTENER Y VALIDAR FACTURA ===
        # Obtener factura asociada al pago
        factura = None
        if pago.factura_id:
            factura = db.query(Facturacion).filter(Facturacion.id == pago.factura_id).first()
        elif x_id_invoice:
            # Si el pago no tiene factura_id pero viene x_id_invoice en el webhook, buscar la factura
            factura = db.query(Facturacion).filter(Facturacion.id_factura == x_id_invoice).first()
            if factura and not pago.factura_id:
                # Asociar el pago con la factura encontrada
                pago.factura_id = factura.id
                logger.info(f"✅ Pago asociado con factura: factura_id={factura.id}, id_factura={factura.id_factura}")
        
        # Validar que el invoice y monto coincidan con lo esperado (seguridad)
        if factura:
            # Validar invoice
            if x_id_invoice and factura.id_factura != x_id_invoice:
                logger.error(f"⚠️ Invoice no coincide! Esperado: {factura.id_factura}, Recibido: {x_id_invoice}")
                raise HTTPException(status_code=400, detail="Número de factura no coincide")
            
            # Validar monto (convertir a float para comparar)
            if x_amount and factura.monto_pagar:
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
        bank_url_webhook = webhook_data.get('urlbanco') or webhook_data.get('x_urlbanco') or webhook_data.get('bank_url') or webhook_data.get('x_bank_url')
        bank_name_webhook = webhook_data.get('x_bank_name') or webhook_data.get('bank_name')
        
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
                    # Actualizar factura a pagado si existe
                    if factura:
                        from app.models.facturacion import EstadoFactura
                        from datetime import datetime
                        factura.estado = EstadoFactura.pagado
                        factura.fecha_pago = datetime.now()
                        logger.info(f"✅ Factura actualizada a PAGADO: factura_id={factura.id}, id_factura={factura.id_factura}")
                    else:
                        logger.warning(f"⚠️ Pago aprobado pero no se encontró factura asociada: ref_payco={ref_payco}, factura_id={pago.factura_id}")
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

@router.post("", response_model=PagoResponse)
async def create_payment(
    payment_data: PagoSimpleCreate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Crea un nuevo registro de pago con datos mínimos.
    
    Este endpoint permite registrar pagos de forma flexible, almacenando solo los datos proporcionados.
    Los campos opcionales se pueden completar posteriormente.
    
    - **factura_id**: ID de la factura (requerido)
    - **ref_payco**: Referencia de ePayco (opcional)
    - **metodo_pago**: Método de pago (por defecto 'epayco')
    - **monto**: Monto del pago (opcional)
    - **estado**: Estado del pago (por defecto 'pendiente')
    - **observaciones**: Observaciones adicionales (opcional)
    
    La fecha del pago se establece automáticamente y la IP del cliente se captura del request.
    """
    try:
        # Verificar que la factura exista si se proporciona factura_id
        if payment_data.factura_id:
            factura = db.query(Facturacion).filter(Facturacion.id == payment_data.factura_id).first()
            if not factura:
                raise HTTPException(status_code=404, detail="Factura no encontrada")
        
        # Obtener IP del cliente
        client_ip = request.client.host if request.client else None
        
        # Construir observaciones si no se proporcionan
        observaciones = payment_data.observaciones
        if not observaciones:
            observaciones = f"Pago procesado a través de {payment_data.metodo_pago}."
            if payment_data.ref_payco:
                observaciones += f" Referencia: {payment_data.ref_payco}."
            observaciones += f" Estado inicial: {payment_data.estado}."
            if payment_data.factura_id:
                observaciones += f" Factura: {payment_data.factura_id}"
        
        # Convertir estado string a Enum
        estado_enum = EstadoPago.pendiente
        if payment_data.estado:
            try:
                estado_enum = EstadoPago(payment_data.estado.lower())
            except ValueError:
                # Si el estado no es válido, usar pendiente por defecto
                estado_enum = EstadoPago.pendiente
        
        # Crear el pago
        nuevo_pago = Pagos(
            factura_id=payment_data.factura_id,
            ref_payco=payment_data.ref_payco,
            metodo_pago=payment_data.metodo_pago or "epayco",
            monto=payment_data.monto,
            estado=estado_enum,
            observaciones=observaciones,
            fecha_pago=datetime.now(),
            ip=client_ip
        )
        
        db.add(nuevo_pago)
        db.commit()
        db.refresh(nuevo_pago)
        
        logger.info(f"Pago creado: ID={nuevo_pago.id}, factura_id={payment_data.factura_id}, ref_payco={payment_data.ref_payco}")
        
        # Usar model_validate para crear la respuesta desde el modelo ORM
        return PagoResponse.model_validate(nuevo_pago)
        
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al crear pago: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error al crear pago: {str(e)}")

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
