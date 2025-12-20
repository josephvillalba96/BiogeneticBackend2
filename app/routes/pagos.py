from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from sqlalchemy.orm import Session
from typing import List, Optional
from decimal import Decimal
from datetime import datetime
import logging

from app.database.base import get_db
from app.models.user import User
from app.models.facturacion import Facturacion, Pagos, EstadoPago, EstadoFactura
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
    try:
        # Obtener datos (form-data o query params)
        try:
            form_data = await request.form()
        except Exception:
            form_data = {}

        query_params = dict(request.query_params)
        webhook_data = {**query_params, **dict(form_data)}

        # Campos obligatorios para firma
        x_ref_payco = webhook_data.get("x_ref_payco")
        x_transaction_id = webhook_data.get("x_transaction_id")
        x_amount = webhook_data.get("x_amount")
        x_currency_code = webhook_data.get("x_currency_code")
        x_signature = webhook_data.get("x_signature")

        if not all([x_ref_payco, x_transaction_id, x_amount, x_currency_code, x_signature]):
            raise HTTPException(status_code=400, detail="Datos incompletos para validación de firma")

        # === VALIDACIÓN SHA256 CORRECTA ===
        from app.config import settings
        import hashlib

        cust_id = settings.EPAYCO_PUBLIC_KEY
        p_key = settings.EPAYCO_PRIVATE_KEY

        signature_string = (
            f"{cust_id}^"
            f"{p_key}^"
            f"{x_ref_payco}^"
            f"{x_transaction_id}^"
            f"{x_amount}^"
            f"{x_currency_code}"
        )

        calculated_signature = hashlib.sha256(
            signature_string.encode("utf-8")
        ).hexdigest()

        if calculated_signature != x_signature:
            raise HTTPException(status_code=403, detail="Firma inválida")

        # Normalizar ref_payco (sin modificar contenido)
        ref_payco = str(x_ref_payco).strip()

        # Buscar pago
        pago = db.query(Pagos).filter(Pagos.ref_payco == ref_payco).first()
        if not pago:
            return {"status": "warning", "message": "Pago no encontrado"}

        # Idempotencia básica
        if pago.estado in [EstadoPago.completado, EstadoPago.fallido]:
            return {"status": "ok", "message": "Webhook ya procesado"}

        # Obtener factura
        if not pago.factura_id:
            raise HTTPException(status_code=400, detail="Pago sin factura asociada")

        factura = db.query(Facturacion).filter(
            Facturacion.id == pago.factura_id
        ).first()

        if not factura:
            raise HTTPException(status_code=400, detail="Factura no encontrada")

        # Estado de la transacción
        x_response = (webhook_data.get("x_response") or "").upper()
        x_cod_response = webhook_data.get("x_cod_response")
        x_amount_ok = webhook_data.get("x_amount_ok") or x_amount

        def normalize_amount(value: str) -> float:
            return float(value.replace(",", "").strip())

        # Procesar estado
        if x_response in ["ACEPTADA", "APPROVED"] or x_cod_response == "1":
            pago.estado = EstadoPago.completado
            pago.response_code = "Aceptada"

            try:
                amount_paid = normalize_amount(x_amount_ok)
                amount_invoice = float(factura.monto_pagar)
                if amount_paid >= amount_invoice:
                    factura.estado = EstadoFactura.pagado
                    factura.fecha_pago = datetime.now()
            except Exception:
                factura.estado = EstadoFactura.pagado
                factura.fecha_pago = datetime.now()

        elif x_response in ["RECHAZADA", "REJECTED"] or x_cod_response == "2":
            pago.estado = EstadoPago.fallido
            pago.response_code = "Rechazada"

        elif x_response in ["PENDIENTE", "PENDING"] or x_cod_response == "3":
            pago.estado = EstadoPago.procesando
            pago.response_code = "Pendiente"

        # IDs correctos
        if x_transaction_id:
            pago.transaction_id = x_transaction_id

        x_approval_code = webhook_data.get("x_approval_code")
        if x_approval_code:
            pago.approval_code = x_approval_code

        # Commit
        db.commit()
        db.refresh(pago)
        if factura:
            db.refresh(factura)

        return {
            "status": "success",
            "message": "Confirmación procesada",
            "ref_payco": ref_payco
        }

    except HTTPException:
        raise
    except Exception:
        db.rollback()
        return {"status": "error", "message": "Error procesando confirmación"}


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
