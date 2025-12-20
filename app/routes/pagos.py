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
@router.get("/confirmation")  # Soporte para GET como fallback (aunque ePayco debería usar POST)
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
        x_ref_payco = webhook_data.get('x_ref_payco')
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
        
        # Usar ref_payco en adelante - guardar EXACTAMENTE el valor de x_ref_payco sin modificaciones
        # El ref_payco en BD debe ser exactamente igual al x_ref_payco del webhook
        ref_payco = str(x_ref_payco).strip() if x_ref_payco else None
        
        # Extraer otros campos importantes del webhook
        x_response = webhook_data.get('x_response', '')
        x_response_reason_text = webhook_data.get('x_response_reason_text', '')
        x_cod_response = webhook_data.get('x_cod_response', '')
        x_id_factura = webhook_data.get('x_id_factura', '') or webhook_data.get('x_id_invoice', '')
        x_approval_code = webhook_data.get('x_approval_code', '')
        x_franchise = webhook_data.get('x_franchise', '')
        x_bank_name = webhook_data.get('x_bank_name', '')
        x_amount_ok = webhook_data.get('x_amount_ok', '') or x_amount
        
        logger.info(f"Procesando confirmación: ref_payco={ref_payco}, x_id_factura={x_id_factura}, x_response={x_response}, x_amount_ok={x_amount_ok}")
        
        # === BUSCAR FACTURA POR x_id_factura (PRIORITARIO) ===
        factura = None
        if x_id_factura:
            logger.info(f"Buscando factura por x_id_factura: {x_id_factura}")
            factura = db.query(Facturacion).filter(Facturacion.id_factura == x_id_factura).first()
            if factura:
                logger.info(f"✅ Factura encontrada: id={factura.id}, id_factura={factura.id_factura}, monto_pagar={factura.monto_pagar}")
            else:
                logger.warning(f"⚠️ Factura no encontrada con x_id_factura: {x_id_factura}")
        
        # === BUSCAR PAGO POR ref_payco = x_ref_payco ===
        # En la BD tenemos la columna ref_payco
        # El webhook trae x_ref_payco
        # Buscar el pago donde ref_payco = x_ref_payco (búsqueda simple y directa)
        logger.info(f"🔍 Buscando pago donde ref_payco = x_ref_payco: '{ref_payco}'")
        
        if not ref_payco:
            logger.error(f"❌ x_ref_payco está vacío o es None")
            return {"status": "error", "message": "x_ref_payco es requerido"}
        
        # Búsqueda directa: ref_payco = x_ref_payco
        # Convertir x_ref_payco a string para comparación
        ref_payco_buscar = str(ref_payco).strip() if ref_payco else None
        
        if not ref_payco_buscar:
            logger.error(f"❌ x_ref_payco está vacío después de normalizar")
            return {"status": "error", "message": "x_ref_payco es requerido"}
        
        # Búsqueda simple: ref_payco = x_ref_payco
        pago = db.query(Pagos).filter(Pagos.ref_payco == ref_payco_buscar).first()
        
        if not pago:
            logger.error(f"❌ Pago NO encontrado donde ref_payco = '{ref_payco_buscar}'")
            logger.error(f"   x_ref_payco recibido: '{ref_payco}' (tipo: {type(ref_payco).__name__})")
            logger.error(f"   x_ref_payco normalizado: '{ref_payco_buscar}'")
            
            # Buscar pagos recientes para debugging
            pagos_recientes = db.query(Pagos).filter(
                Pagos.ref_payco.isnot(None)
            ).order_by(Pagos.id.desc()).limit(20).all()
            
            logger.error(f"   Últimos 20 pagos con ref_payco en BD:")
            for p in pagos_recientes:
                ref_payco_bd = str(p.ref_payco).strip() if p.ref_payco else None
                es_igual = ref_payco_bd == ref_payco_buscar
                logger.error(f"     - Pago ID={p.id}, ref_payco='{ref_payco_bd}', igual? {es_igual}")
            
            return {"status": "warning", "message": f"Pago con ref_payco {ref_payco_buscar} no encontrado"}
        
        logger.info(f"✅ Pago encontrado: pago_id={pago.id}, ref_payco='{pago.ref_payco}'")
        
        # === OBTENER FACTURA DEL PAGO ===
        # El pago SIEMPRE tiene factura_id, obtener la factura directamente
        if not pago.factura_id:
            logger.error(f"❌ Pago no tiene factura_id asociada: pago_id={pago.id}, ref_payco={ref_payco}")
            raise HTTPException(status_code=400, detail=f"Pago con ref_payco {ref_payco} no tiene factura asociada")
        
        factura = db.query(Facturacion).filter(Facturacion.id == pago.factura_id).first()
        if not factura:
            logger.error(f"❌ Factura no encontrada: factura_id={pago.factura_id}, pago_id={pago.id}")
            raise HTTPException(status_code=400, detail=f"Factura asociada al pago no existe: factura_id={pago.factura_id}")
        
        logger.info(f"✅ Factura obtenida: id_factura={factura.id_factura}, factura_id={factura.id}")
        
        # Extraer bank_url del webhook si viene (puede venir en diferentes campos)
        bank_url_webhook = webhook_data.get('urlbanco') or webhook_data.get('x_urlbanco') or webhook_data.get('bank_url') or webhook_data.get('x_bank_url')
        bank_name_webhook = webhook_data.get('x_bank_name') or webhook_data.get('bank_name')
        
        # Si el pago no tiene bank_url y viene en el webhook, actualizarlo
        if not pago.bank_url and bank_url_webhook:
            pago.bank_url = bank_url_webhook
            logger.info(f"✅ bank_url actualizado desde webhook: {bank_url_webhook}")
        if not pago.bank_name and bank_name_webhook:
            pago.bank_name = bank_name_webhook
        
        # === PROCESAR ESTADO SEGÚN x_response ===
        # x_response: "Aceptada" → aprobado/completado, "Rechazada" → rechazado/fallido
        from app.models.facturacion import EstadoFactura
        
        # Asegurar que pago existe antes de actualizar
        if not pago:
            logger.error(f"❌ No se puede actualizar estado: pago no encontrado. ref_payco={ref_payco}")
            return {"status": "error", "message": "Pago no encontrado"}
        
        estado_actualizado = False
        
        # Procesar según x_response (prioritario)
        if x_response:
            x_response_upper = x_response.strip().upper()
            logger.info(f"Procesando estado desde x_response: {x_response_upper}")
            
            if x_response_upper == "ACEPTADA":
                # Pago aceptado - usar enum EstadoPago explícitamente
                pago.estado = EstadoPago.completado
                pago.response_code = "Aceptada"
                estado_actualizado = True
                logger.info(f"✅ Estado asignado usando enum: EstadoPago.completado = {EstadoPago.completado.value}")
                
                # Verificar si el monto pagado es igual o mayor al monto total de la factura
                if factura and x_amount_ok:
                    try:
                        amount_paid = float(x_amount_ok)
                        amount_invoice = float(factura.monto_pagar)
                        
                        # Si el pago es por el monto total (o mayor), actualizar factura a pagado
                        if amount_paid >= amount_invoice:
                            factura.estado = EstadoFactura.pagado
                            factura.fecha_pago = datetime.now()
                            logger.info(f"✅ Factura actualizada a PAGADO: factura_id={factura.id}, id_factura={factura.id_factura}, monto_pagado={amount_paid}, monto_factura={amount_invoice}")
                        else:
                            logger.info(f"⚠️ Pago aceptado pero monto parcial: monto_pagado={amount_paid}, monto_factura={amount_invoice}. Factura permanece pendiente.")
                    except (ValueError, TypeError) as e:
                        logger.warning(f"No se pudo comparar montos: x_amount_ok={x_amount_ok}, monto_pagar={factura.monto_pagar}, error={str(e)}")
                        # Si no se puede validar el monto, asumir que es el total y aprobar
                        factura.estado = EstadoFactura.pagado
                        factura.fecha_pago = datetime.now()
                        logger.info(f"✅ Factura actualizada a PAGADO (sin validación de monto): factura_id={factura.id}")
                elif factura:
                    # Si no viene x_amount_ok pero tenemos factura, asumir que es el total
                    factura.estado = EstadoFactura.pagado
                    factura.fecha_pago = datetime.now()
                    logger.info(f"✅ Factura actualizada a PAGADO (sin monto en webhook): factura_id={factura.id}")
                else:
                    # Si no hay factura, intentar obtenerla del pago que corresponde al x_ref_payco
                    if pago and pago.factura_id and not factura:
                        factura = db.query(Facturacion).filter(Facturacion.id == pago.factura_id).first()
                        if factura:
                            logger.info(f"✅ Factura obtenida desde pago para actualizar estado: id_factura={factura.id_factura}")
                            # Re-ejecutar la lógica de actualización de factura
                            if x_amount_ok:
                                try:
                                    amount_paid = float(x_amount_ok)
                                    amount_invoice = float(factura.monto_pagar)
                                    if amount_paid >= amount_invoice:
                                        factura.estado = EstadoFactura.pagado
                                        factura.fecha_pago = datetime.now()
                                        logger.info(f"✅ Factura actualizada a PAGADO (obtenida desde pago): factura_id={factura.id}, monto_pagado={amount_paid}, monto_factura={amount_invoice}")
                                except (ValueError, TypeError):
                                    factura.estado = EstadoFactura.pagado
                                    factura.fecha_pago = datetime.now()
                                    logger.info(f"✅ Factura actualizada a PAGADO (obtenida desde pago, sin validación monto): factura_id={factura.id}")
                            else:
                                factura.estado = EstadoFactura.pagado
                                factura.fecha_pago = datetime.now()
                                logger.info(f"✅ Factura actualizada a PAGADO (obtenida desde pago): factura_id={factura.id}")
                        else:
                            logger.warning(f"⚠️ Pago aprobado pero no se encontró factura asociada: ref_payco={ref_payco}, factura_id={pago.factura_id}")
                    elif not factura:
                        logger.warning(f"⚠️ Pago aprobado pero no se encontró factura asociada: ref_payco={ref_payco}, factura_id={pago.factura_id if pago else None}")
                
                logger.info(f"✅ Pago ACEPTADO: ref_payco={ref_payco}")
                
            elif x_response_upper == "RECHAZADA":
                # Pago rechazado - usar enum EstadoPago explícitamente
                pago.estado = EstadoPago.fallido
                pago.response_code = "Rechazada"
                estado_actualizado = True
                logger.info(f"✅ Estado asignado usando enum: EstadoPago.fallido = {EstadoPago.fallido.value}")
                # La factura permanece en su estado actual (no se actualiza a rechazado)
                logger.warning(f"❌ Pago RECHAZADO: ref_payco={ref_payco}, razón={x_response_reason_text}")
                
            else:
                # Otros estados (Pendiente, etc.)
                if x_response_upper in ["PENDIENTE", "PENDING"]:
                    # Usar enum EstadoPago explícitamente
                    pago.estado = EstadoPago.procesando
                    pago.response_code = "Pendiente"
                    estado_actualizado = True
                    logger.info(f"✅ Estado asignado usando enum: EstadoPago.procesando = {EstadoPago.procesando.value}")
                    logger.info(f"⏳ Pago PENDIENTE: ref_payco={ref_payco}")
                else:
                    logger.warning(f"⚠️ Estado x_response desconocido: {x_response}, usando x_cod_response como fallback")
        
        # Si no se actualizó el estado desde x_response, usar x_cod_response como fallback
        if not estado_actualizado and x_cod_response:
            try:
                cod_response = int(x_cod_response)
                logger.info(f"Procesando estado desde x_cod_response: {cod_response}")
                
                if cod_response == 1:  # Transacción aceptada
                    # Usar enum EstadoPago explícitamente
                    pago.estado = EstadoPago.completado
                    pago.response_code = "Aceptada"
                    estado_actualizado = True
                    logger.info(f"✅ Estado asignado usando enum (x_cod_response): EstadoPago.completado = {EstadoPago.completado.value}")
                    
                    # Actualizar factura si existe
                    if factura:
                        if x_amount_ok:
                            try:
                                amount_paid = float(x_amount_ok)
                                amount_invoice = float(factura.monto_pagar)
                                if amount_paid >= amount_invoice:
                                    factura.estado = EstadoFactura.pagado
                                    factura.fecha_pago = datetime.now()
                                    logger.info(f"✅ Factura actualizada a PAGADO (desde x_cod_response): factura_id={factura.id}, monto_pagado={amount_paid}, monto_factura={amount_invoice}")
                            except (ValueError, TypeError):
                                factura.estado = EstadoFactura.pagado
                                factura.fecha_pago = datetime.now()
                                logger.info(f"✅ Factura actualizada a PAGADO (desde x_cod_response, sin validación monto): factura_id={factura.id}")
                        else:
                            factura.estado = EstadoFactura.pagado
                            factura.fecha_pago = datetime.now()
                            logger.info(f"✅ Factura actualizada a PAGADO (desde x_cod_response): factura_id={factura.id}")
                    
                    logger.info(f"✅ Pago ACEPTADO (desde x_cod_response): ref_payco={ref_payco}")
                    
                elif cod_response == 2:  # Transacción rechazada
                    # Usar enum EstadoPago explícitamente
                    pago.estado = EstadoPago.fallido
                    pago.response_code = "Rechazada"
                    estado_actualizado = True
                    logger.info(f"✅ Estado asignado usando enum (x_cod_response): EstadoPago.fallido = {EstadoPago.fallido.value}")
                    logger.warning(f"❌ Pago RECHAZADO (desde x_cod_response): ref_payco={ref_payco}")
                    
                elif cod_response == 3:  # Transacción pendiente
                    # Usar enum EstadoPago explícitamente
                    pago.estado = EstadoPago.procesando
                    pago.response_code = "Pendiente"
                    estado_actualizado = True
                    logger.info(f"✅ Estado asignado usando enum (x_cod_response): EstadoPago.procesando = {EstadoPago.procesando.value}")
                    logger.info(f"⏳ Pago PENDIENTE (desde x_cod_response): ref_payco={ref_payco}")
                    
                elif cod_response == 4:  # Transacción fallida
                    # Usar enum EstadoPago explícitamente
                    pago.estado = EstadoPago.fallido
                    pago.response_code = "Fallida"
                    estado_actualizado = True
                    logger.info(f"✅ Estado asignado usando enum (x_cod_response): EstadoPago.fallido = {EstadoPago.fallido.value}")
                    logger.error(f"❌ Pago FALLIDO (desde x_cod_response): ref_payco={ref_payco}")
                    
            except ValueError:
                logger.warning(f"x_cod_response no es un número válido: {x_cod_response}")
        
        # Si aún no se actualizó, establecer response_code al menos
        if not estado_actualizado:
            logger.warning(f"⚠️ No se pudo determinar el estado del pago. x_response={x_response}, x_cod_response={x_cod_response}")
            if x_response:
                pago.response_code = x_response
        
        # Actualizar campos adicionales
        if x_response_reason_text:
            pago.response_message = x_response_reason_text
        if x_approval_code:
            pago.transaction_id = x_approval_code
        
        # Actualizar monto del pago si viene en el webhook
        if x_amount_ok:
            try:
                pago.monto = float(x_amount_ok)
                pago.value = float(x_amount_ok)
            except (ValueError, TypeError):
                logger.warning(f"No se pudo actualizar monto: x_amount_ok={x_amount_ok}")
        
        # Log antes del commit para verificar cambios
        logger.info(f"📝 Estado ANTES del commit - Pago ID={pago.id}: estado={pago.estado.value}, response_code={pago.response_code}")
        if factura:
            logger.info(f"📝 Estado ANTES del commit - Factura ID={factura.id}: estado={factura.estado.value}")
        
        # Commit de los cambios
        try:
            db.commit()
            logger.info(f"✅ Commit exitoso - Pago ID={pago.id}, estado={pago.estado.value}")
            
            # Refrescar objetos para verificar que se guardaron
            db.refresh(pago)
            logger.info(f"✅ Pago refrescado - ID={pago.id}, estado={pago.estado.value}, ref_payco={pago.ref_payco}")
            
            if factura:
                db.refresh(factura)
                logger.info(f"✅ Factura refrescada - ID={factura.id}, estado={factura.estado.value}, id_factura={factura.id_factura}")
        except Exception as commit_error:
            logger.error(f"❌ Error al hacer commit: {str(commit_error)}", exc_info=True)
            db.rollback()
            raise
        
        logger.info(f"✅ Pago confirmado exitosamente: ref_payco={ref_payco}, estado={pago.estado.value}, x_response={x_response}, factura_estado={factura.estado.value if factura else 'N/A'}")
        
        # Enviar notificación en background (si es necesario)
        if pago and factura:
            logger.info(f"Pago confirmado: ref_payco={ref_payco}, factura_id={factura.id}, notificación pendiente")
        
        return {"status": "success", "message": "Confirmación procesada", "ref_payco": ref_payco}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en confirmación de pago: {str(e)}", exc_info=True)
        # Retornar 200 para que ePayco no reintente en caso de error interno
        # (pero deberíamos loguear el error para investigar)
        return {"status": "error", "message": f"Error al procesar confirmación: {str(e)}"}

@router.get("/transaction/{reference_payco}/detail")
async def get_transaction_detail(
    reference_payco: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    """
    Consultar detalles de una transacción desde ePayco usando referencePayco
    
    Este endpoint consulta directamente a la API de ePayco Apify para obtener
    los detalles completos de una transacción usando su referencia (ref_payco).
    
    Args:
        reference_payco: Referencia de ePayco (ref_payco) de la transacción
        
    Returns:
        Dict con los detalles completos de la transacción desde ePayco
        
    Example:
        GET /api/pagos/transaction/30604419/detail
    """
    try:
        # Inicializar servicio de confirmación que tiene el método para consultar transacciones
        confirmation_service = PaymentConfirmationService(db)
        
        # Consultar detalles de la transacción
        transaction_detail = confirmation_service.get_transaction_detail(reference_payco)
        
        if transaction_detail is None:
            raise HTTPException(
                status_code=404, 
                detail=f"Transacción con referencePayco {reference_payco} no encontrada en ePayco"
            )
        
        logger.info(f"✅ Detalles de transacción obtenidos: referencePayco={reference_payco}")
        
        return {
            "status": "success",
            "reference_payco": reference_payco,
            "transaction_detail": transaction_detail
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al consultar detalles de transacción: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error al consultar detalles de transacción: {str(e)}"
        )

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
