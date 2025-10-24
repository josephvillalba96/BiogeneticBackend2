from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from decimal import Decimal
from datetime import datetime
import epaycosdk.epayco as epayco
from app.models.facturacion import Facturacion, Pagos, EstadoFactura, EstadoPago
from app.models.user import User, DocumentType
from app.schemas.pagos_schema import PagoPSECreate, PaymentNotificationData
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class EpaycoConfigService:
    """Servicio de configuración de ePayco"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'EPAYCO_PUBLIC_KEY', '')
        self.private_key = getattr(settings, 'EPAYCO_PRIVATE_KEY', '')
        self.test = getattr(settings, 'EPAYCO_TEST_MODE', True)
        self.language = "ES"
        
    def get_epayco_client(self):
        """Obtener cliente de ePayco configurado"""
        options = {
            "apiKey": self.api_key,
            "privateKey": self.private_key,
            "test": self.test,
            "lenguage": self.language
        }
        return epayco.Epayco(options)
    
    def get_pse_banks(self) -> Dict[str, Any]:
        """
        Obtener lista de entidades bancarias disponibles para PSE
        """
        try:
            client = self.get_epayco_client()
            
            # Intentar obtener bancos PSE
            try:
                banks_response = client.bank.pseBank()
                if banks_response and 'data' in banks_response:
                    return {
                        "success": True,
                        "banks": banks_response['data'],
                        "message": "Entidades bancarias obtenidas exitosamente"
                    }
            except Exception as e:
                logger.warning(f"Error al obtener bancos PSE: {str(e)}")
            
            # Si falla, devolver lista estática de bancos colombianos comunes
            static_banks = [
                {
                    "id": "1007",
                    "name": "BANCO DE BOGOTÁ",
                    "code": "1007",
                    "description": "Banco de Bogotá S.A."
                },
                {
                    "id": "1013",
                    "name": "BBVA COLOMBIA",
                    "code": "1013", 
                    "description": "BBVA Colombia S.A."
                },
                {
                    "id": "1019",
                    "name": "BANCO COLPATRIA",
                    "code": "1019",
                    "description": "Banco Colpatria S.A."
                },
                {
                    "id": "1023",
                    "name": "BANCO DAVIVIENDA",
                    "code": "1023",
                    "description": "Banco Davivienda S.A."
                },
                {
                    "id": "1031",
                    "name": "BANCO DE OCCIDENTE",
                    "code": "1031",
                    "description": "Banco de Occidente S.A."
                },
                {
                    "id": "1032",
                    "name": "BANCO POPULAR",
                    "code": "1032",
                    "description": "Banco Popular S.A."
                },
                {
                    "id": "1035",
                    "name": "BANCO AV VILLAS",
                    "code": "1035",
                    "description": "Banco AV Villas S.A."
                },
                {
                    "id": "1040",
                    "name": "ALIANZA FIDUCIARIA",
                    "code": "1040",
                    "description": "Alianza Fiduciaria S.A."
                },
                {
                    "id": "1052",
                    "name": "BANCO FALABELLA",
                    "code": "1052",
                    "description": "Banco Falabella S.A."
                },
                {
                    "id": "1066",
                    "name": "BANCO COOPERATIVO COOPCENTRAL",
                    "code": "1066",
                    "description": "Banco Cooperativo Coopcentral"
                }
            ]
            
            return {
                "success": True,
                "banks": static_banks,
                "message": "Lista estática de entidades bancarias (ePayco API no disponible)"
            }
            
        except Exception as e:
            logger.error(f"Error al obtener entidades bancarias: {str(e)}")
            return {
                "success": False,
                "banks": [],
                "message": f"Error al obtener entidades bancarias: {str(e)}"
            }

class PSEPaymentService:
    """Servicio para procesamiento de pagos PSE"""
    
    def __init__(self, db: Session):
        self.db = db
        self.epayco = EpaycoConfigService().get_epayco_client()
    
    async def create_pse_payment(self, factura_id: int, user: User, request_ip: str, pse_data: PagoPSECreate) -> Dict[str, Any]:
        """
        Crear pago PSE para una factura específica
        """
        try:
            # 1. Obtener factura
            factura = self.get_factura(factura_id)
            if not factura:
                raise ValueError(f"Factura con ID {factura_id} no encontrada")
            
            # 2. Verificar que la factura no esté pagada
            if factura.estado == EstadoFactura.pagado:
                raise ValueError("La factura ya está pagada")
            
            # 3. Preparar datos para ePayco
            payment_data = self.prepare_pse_data(factura, user, request_ip, pse_data)
            
            # 4. Crear pago en ePayco
            pse_response = self.epayco.cash.create('pse', payment_data)
            
            if not pse_response or 'ref_payco' not in pse_response:
                raise ValueError("Error al crear pago en ePayco")
            
            # 5. Guardar pago en base de datos
            pago = self.save_payment(factura, pse_response, payment_data, user)
            
            logger.info(f"Pago PSE creado exitosamente: {pago.id}, ref_payco: {pse_response.get('ref_payco')}")
            
            return {
                "pago_id": pago.id,
                "ref_payco": pse_response.get('ref_payco'),
                "bank_url": pse_response.get('bank_url'),
                "bank_name": pse_response.get('bank_name'),
                "status": pago.estado.value,
                "message": "Pago PSE creado exitosamente. Redirigir al banco para completar el pago."
            }
            
        except Exception as e:
            logger.error(f"Error al crear pago PSE: {str(e)}")
            raise ValueError(f"Error al procesar pago PSE: {str(e)}")
    
    def get_factura(self, factura_id: int) -> Optional[Facturacion]:
        """Obtener factura por ID"""
        return self.db.query(Facturacion).filter(Facturacion.id == factura_id).first()
    
    def prepare_pse_data(self, factura: Facturacion, user: User, request_ip: str, pse_data: PagoPSECreate) -> Dict[str, Any]:
        """
        Preparar datos para envío a ePayco PSE
        """
        # Usar los valores de IVA de la factura
        monto_base = factura.monto_base or Decimal('0')
        valor_iva = factura.valor_iva or Decimal('0')
        monto_total = factura.monto_pagar
        
        # Si no hay monto_base calculado, usar el total como base
        if monto_base == 0:
            monto_base = monto_total
            valor_iva = Decimal('0')
        
        return {
            "doc_type": self.map_document_type(user.type_document),
            "document": user.number_document,
            "name": user.full_name.split()[0] if user.full_name else "Cliente",
            "last_name": " ".join(user.full_name.split()[1:]) if len(user.full_name.split()) > 1 else "",
            "email": user.email,
            "ind_country": "57",  # Colombia
            "phone": user.phone,
            "country": "CO",
            "city": pse_data.city or "Bogotá",
            "address": pse_data.address or "Dirección no especificada",
            "ip": request_ip,
            "currency": "COP",
            "description": f"Pago factura {factura.id_factura} - {factura.descripcion or 'Servicios BioGenetic'}",
            "value": str(int(monto_total)),
            "tax": str(int(valor_iva)),
            "ico": "0",
            "tax_base": str(int(monto_base)),
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
        """Mapear tipo de documento interno a ePayco"""
        mapping = {
            DocumentType.identity_card: "CC",
            DocumentType.passport: "CE",
            DocumentType.other: "CC"
        }
        return mapping.get(doc_type, "CC")
    
    def save_payment(self, factura: Facturacion, pse_response: Dict[str, Any], payment_data: Dict[str, Any], user: User) -> Pagos:
        """Guardar pago en base de datos"""
        pago = Pagos(
            factura_id=factura.id,
            monto=factura.monto_pagar,
            metodo_pago="PSE",
            estado=EstadoPago.pendiente,
            ref_payco=pse_response.get('ref_payco'),
            bank_name=pse_response.get('bank_name'),
            bank_url=pse_response.get('bank_url'),
            doc_type=payment_data.get('doc_type'),
            document=payment_data.get('document'),
            name=payment_data.get('name'),
            last_name=payment_data.get('last_name'),
            email=payment_data.get('email'),
            phone=payment_data.get('phone'),
            city=payment_data.get('city'),
            address=payment_data.get('address'),
            ip=payment_data.get('ip'),
            currency=payment_data.get('currency'),
            description=payment_data.get('description'),
            value=factura.monto_pagar,
            tax=factura.valor_iva or Decimal('0'),
            tax_base=factura.monto_base or factura.monto_pagar,
            url_response=payment_data.get('url_response'),
            url_confirmation=payment_data.get('url_confirmation'),
            method_confirmation=payment_data.get('method_confirmation')
        )
        
        self.db.add(pago)
        self.db.commit()
        self.db.refresh(pago)
        
        return pago

class PaymentConfirmationService:
    """Servicio para confirmación de pagos"""
    
    def __init__(self, db: Session):
        self.db = db
        self.epayco = EpaycoConfigService().get_epayco_client()
    
    async def confirm_payment(self, ref_payco: str) -> Dict[str, Any]:
        """
        Confirmar estado de pago con ePayco
        """
        try:
            # 1. Consultar estado en ePayco
            payment_status = self.epayco.cash.get(ref_payco)
            
            if not payment_status:
                raise ValueError(f"No se pudo obtener el estado del pago {ref_payco}")
            
            # 2. Actualizar pago en base de datos
            pago = self.update_payment_status(ref_payco, payment_status)
            
            # 3. Actualizar estado de factura si es necesario
            factura_actualizada = False
            if payment_status.get('x_response') == 'Aceptada':
                factura_actualizada = self.update_factura_status(pago.factura_id, EstadoFactura.pagado)
            
            logger.info(f"Pago confirmado: {ref_payco}, estado: {payment_status.get('x_response')}")
            
            return {
                "pago_id": pago.id,
                "estado": pago.estado.value,
                "ref_payco": ref_payco,
                "response_code": payment_status.get('x_response'),
                "response_message": payment_status.get('x_response_reason_text'),
                "factura_actualizada": factura_actualizada
            }
            
        except Exception as e:
            logger.error(f"Error al confirmar pago {ref_payco}: {str(e)}")
            raise ValueError(f"Error al confirmar pago: {str(e)}")
    
    def update_payment_status(self, ref_payco: str, payment_status: Dict[str, Any]) -> Pagos:
        """Actualizar estado del pago basado en respuesta de ePayco"""
        pago = self.db.query(Pagos).filter(Pagos.ref_payco == ref_payco).first()
        
        if not pago:
            raise ValueError(f"Pago con ref_payco {ref_payco} no encontrado")
        
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
    
    def update_factura_status(self, factura_id: int, nuevo_estado: EstadoFactura) -> bool:
        """Actualizar estado de la factura"""
        try:
            factura = self.db.query(Facturacion).filter(Facturacion.id == factura_id).first()
            if factura:
                factura.estado = nuevo_estado
                if nuevo_estado == EstadoFactura.pagado:
                    factura.fecha_pago = datetime.now()
                self.db.commit()
                return True
            return False
        except Exception as e:
            logger.error(f"Error al actualizar factura {factura_id}: {str(e)}")
            return False

class PaymentNotificationService:
    """Servicio para notificaciones de pago por email"""
    
    def __init__(self, db: Session):
        self.db = db
    
    async def send_payment_notification(self, pago: Pagos, factura: Facturacion, user: User):
        """
        Enviar notificación de pago al usuario por email
        """
        try:
            from app.services.email_service import EmailService
            
            email_service = EmailService()
            
            # Preparar datos para el email
            notification_data = PaymentNotificationData(
                pago_id=pago.id,
                factura_id=factura.id,
                user_email=user.email,
                user_name=user.full_name,
                monto=pago.monto,
                estado=pago.estado.value,
                ref_payco=pago.ref_payco,
                bank_name=pago.bank_name
            )
            
            # Enviar email según el estado
            if pago.estado == EstadoPago.pendiente:
                await self.send_pending_payment_email(email_service, notification_data)
            elif pago.estado == EstadoPago.completado:
                await self.send_payment_confirmation_email(email_service, notification_data, factura)
            elif pago.estado == EstadoPago.fallido:
                await self.send_payment_failed_email(email_service, notification_data)
                
        except Exception as e:
            logger.error(f"Error al enviar notificación de pago: {str(e)}")
    
    async def send_pending_payment_email(self, email_service, data: PaymentNotificationData):
        """Enviar email de pago pendiente"""
        subject = f"Pago Pendiente - Factura #{data.factura_id}"
        template = "payment_pending.html"
        context = {
            "user_name": data.user_name,
            "factura_id": data.factura_id,
            "monto": data.monto,
            "ref_payco": data.ref_payco,
            "bank_name": data.bank_name
        }
        
        await email_service.send_email(
            to_email=data.user_email,
            subject=subject,
            template_name=template,
            context=context
        )
    
    async def send_payment_confirmation_email(self, email_service, data: PaymentNotificationData, factura: Facturacion):
        """Enviar email de confirmación de pago"""
        subject = f"Pago Confirmado - Factura #{data.factura_id}"
        template = "payment_confirmed.html"
        context = {
            "user_name": data.user_name,
            "factura_id": data.factura_id,
            "id_factura": factura.id_factura,
            "monto": data.monto,
            "fecha_pago": factura.fecha_pago.strftime("%d/%m/%Y %H:%M") if factura.fecha_pago else "N/A"
        }
        
        await email_service.send_email(
            to_email=data.user_email,
            subject=subject,
            template_name=template,
            context=context
        )
    
    async def send_payment_failed_email(self, email_service, data: PaymentNotificationData):
        """Enviar email de pago fallido"""
        subject = f"Pago Fallido - Factura #{data.factura_id}"
        template = "payment_failed.html"
        context = {
            "user_name": data.user_name,
            "factura_id": data.factura_id,
            "monto": data.monto,
            "ref_payco": data.ref_payco
        }
        
        await email_service.send_email(
            to_email=data.user_email,
            subject=subject,
            template_name=template,
            context=context
        )
